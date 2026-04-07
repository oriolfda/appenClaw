#!/usr/bin/env python3
import base64
import importlib.util
import json
import os
import tempfile
from pathlib import Path

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import x25519


def load_bridge(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, str(path))
    mod = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    spec.loader.exec_module(mod)
    return mod


def _build_valid_env(mod, sid: str, *, counter: int, header_id: str, ratchet_pub_b64: str, ad: str, plaintext: str):
    eph_priv = x25519.X25519PrivateKey.generate()
    eph_pub_b64 = base64.b64encode(
        eph_priv.public_key().public_bytes(
            encoding=serialization.Encoding.DER,
            format=serialization.PublicFormat.SubjectPublicKeyInfo,
        )
    ).decode("ascii")

    bridge_pub = mod._decode_pubkey_spki(mod._BRIDGE_PUB_B64)
    shared = eph_priv.exchange(bridge_pub)

    salt = os.urandom(16)
    base_key = mod._hkdf_key(shared, salt)

    ratchet_shared = b""
    if ratchet_pub_b64:
        ratchet_pub = mod._decode_pubkey_spki(ratchet_pub_b64)
        ratchet_shared = eph_priv.exchange(ratchet_pub)
        import hashlib
        mix_salt = hashlib.sha256(base64.b64decode(ratchet_pub_b64)).digest()[:16]
        base_key = mod._hkdf_key(base_key + ratchet_shared, mix_salt)

    store = mod._load_ratchet_store()
    st = mod._ensure_session_chains(store.setdefault("sessions", {}).setdefault(sid, {}))
    recv_seed_b64 = st.get("recvChainSeed", "")
    if recv_seed_b64:
        import hashlib
        recv_seed = base64.b64decode(recv_seed_b64)
        base_key = hashlib.sha256(recv_seed + base_key + b"recv-priority").digest()

    mixed_key, _ = mod._ratchet_preview_chain_key(st, base_key, "c2s", counter)
    recv_chain_key = mod._derive_chain_key(mixed_key, "recv")
    key = mod._derive_message_key(recv_chain_key, counter, "c2s")

    env_enc = mod.encrypt_real_envelope(plaintext, key, ad)
    return {
        "ephemeralPub": eph_pub_b64,
        "ratchetPub": ratchet_pub_b64,
        "salt": base64.b64encode(salt).decode("ascii"),
        "iv": env_enc["iv"],
        "ciphertext": env_enc["ciphertext"],
        "ad": ad,
        "counter": counter,
        "headerId": header_id,
    }


def session_view(mod, sid: str):
    st = mod._ensure_session_chains(mod._load_ratchet_store().setdefault("sessions", {}).setdefault(sid, {}))
    recv = st.get("recv", {})
    return {
        "recvChainSeed": st.get("recvChainSeed", ""),
        "sendChainSeed": st.get("sendChainSeed", ""),
        "rootKeySeed": st.get("rootKeySeed", ""),
        "recvChainCounter": int(recv.get("chainCounter", 0)),
        "ratchetStep": int(recv.get("ratchetStep", 0)),
        "lastPeerRatchetPub": str(recv.get("lastPeerRatchetPub", "") or ""),
    }


def main():
    import sys

    script_path = Path(sys.argv[1]) if len(sys.argv) > 1 else Path(__file__).with_name("appenclaw_chat_bridge.py")
    env_prefix = (sys.argv[2] if len(sys.argv) > 2 else "appenClaw_APP").upper()

    tmp = Path(tempfile.mkdtemp(prefix="e2ee-dh-step-failed-then-success-smoke-"))
    os.environ[f"{env_prefix}_E2EE_KEYSTORE"] = str(tmp / "keys.json")
    os.environ[f"{env_prefix}_E2EE_RATCHET_STORE"] = str(tmp / "ratchet.json")
    os.environ[f"{env_prefix}_E2EE_OTK_STORE"] = str(tmp / "otk.json")

    mod = load_bridge(script_path, "bridge_dh_step_failed_then_success")
    sid = "dh-step-failed-then-success"

    # Pre-seed to make rollback checks meaningful.
    mod._ratchet_mix_chain_key(sid, os.urandom(32), "c2s", 1)

    ratchet_priv = x25519.X25519PrivateKey.generate()
    ratchet_pub_b64 = base64.b64encode(
        ratchet_priv.public_key().public_bytes(
            encoding=serialization.Encoding.DER,
            format=serialization.PublicFormat.SubjectPublicKeyInfo,
        )
    ).decode("ascii")

    before = session_view(mod, sid)

    snap = mod._ratchet_snapshot_recv(sid)
    precheck_fail_path = mod._ratchet_check_and_advance(sid, 2, "hdr-dh-fail-then-ok")
    failed = False
    try:
        mod.decrypt_real_envelope({
            "ephemeralPub": ratchet_pub_b64,
            "ratchetPub": ratchet_pub_b64,
            "salt": base64.b64encode(os.urandom(16)).decode("ascii"),
            "iv": base64.b64encode(os.urandom(12)).decode("ascii"),
            "ciphertext": base64.b64encode(os.urandom(48)).decode("ascii"),
            "ad": "dh-fail-path",
            "counter": 2,
            "headerId": "hdr-dh-fail-then-ok",
        }, sid)
    except Exception:
        failed = True
        mod._ratchet_restore_recv(sid, snap)

    after_restore = session_view(mod, sid)

    precheck_success_path = mod._ratchet_check_and_advance(sid, 2, "hdr-dh-fail-then-ok")
    env_ok = _build_valid_env(
        mod,
        sid,
        counter=2,
        header_id="hdr-dh-fail-then-ok",
        ratchet_pub_b64="",
        ad="dh-success-path",
        plaintext="hola",
    )
    pt, _, _, out_counter = mod.decrypt_real_envelope(env_ok, sid)
    after_success = session_view(mod, sid)

    replay_reject = not mod._ratchet_check_and_advance(sid, 2, "hdr-dh-fail-then-ok")

    rollback_ok = before == after_restore
    success_ok = (
        pt == "hola" and
        out_counter == 2 and
        after_success["ratchetStep"] == before["ratchetStep"] and
        after_success["lastPeerRatchetPub"] == before["lastPeerRatchetPub"] and
        after_success["recvChainCounter"] >= before["recvChainCounter"] + 1
    )

    ok = precheck_fail_path and failed and rollback_ok and precheck_success_path and success_ok and replay_reject

    print(json.dumps({
        "ok": ok,
        "precheckFailPath": precheck_fail_path,
        "failedDecrypt": failed,
        "rollbackOk": rollback_ok,
        "precheckSuccessPath": precheck_success_path,
        "successOk": success_ok,
        "replayReject": replay_reject,
        "before": before,
        "afterRestore": after_restore,
        "afterSuccess": {
            "recvChainCounter": after_success["recvChainCounter"],
            "ratchetStep": after_success["ratchetStep"],
            "lastPeerRatchetPub": bool(after_success["lastPeerRatchetPub"]),
        },
    }))
    raise SystemExit(0 if ok else 1)


if __name__ == "__main__":
    main()
