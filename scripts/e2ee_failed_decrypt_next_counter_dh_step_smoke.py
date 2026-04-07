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

    if ratchet_pub_b64:
        ratchet_pub = mod._decode_pubkey_spki(ratchet_pub_b64)
        ratchet_shared = mod._BRIDGE_PRIVKEY.exchange(ratchet_pub)
        import hashlib
        mix_salt = hashlib.sha256(base64.b64decode(ratchet_pub_b64)).digest()[:16]
        base_key = mod._hkdf_key(base_key + ratchet_shared, mix_salt)
        mod._ratchet_apply_peer_pub(sid, ratchet_pub_b64, mix_material=base_key + ratchet_shared)

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


def _session_recv(mod, sid: str):
    st = mod._ensure_session_chains(mod._load_ratchet_store().setdefault("sessions", {}).setdefault(sid, {}))
    recv = st.get("recv", {})
    return {
        "step": int(recv.get("ratchetStep", 0)),
        "lastPeer": str(recv.get("lastPeerRatchetPub", "") or ""),
    }


def main():
    import sys

    script_path = Path(sys.argv[1]) if len(sys.argv) > 1 else Path(__file__).with_name("appenclaw_chat_bridge.py")
    env_prefix = (sys.argv[2] if len(sys.argv) > 2 else "appenClaw_APP").upper()

    tmp = Path(tempfile.mkdtemp(prefix="e2ee-failed-decrypt-next-counter-dh-step-smoke-"))
    os.environ[f"{env_prefix}_E2EE_KEYSTORE"] = str(tmp / "keys.json")
    os.environ[f"{env_prefix}_E2EE_RATCHET_STORE"] = str(tmp / "ratchet.json")
    os.environ[f"{env_prefix}_E2EE_OTK_STORE"] = str(tmp / "otk.json")

    mod = load_bridge(script_path, "bridge_failed_next_counter_dh_step")
    sid = "failed-decrypt-next-counter-dh-step"
    header = "hdr-next-counter-dh"

    mod._ratchet_mix_chain_key(sid, os.urandom(32), "c2s", 1)

    ratchet_priv = x25519.X25519PrivateKey.generate()
    ratchet_pub_b64 = base64.b64encode(
        ratchet_priv.public_key().public_bytes(
            encoding=serialization.Encoding.DER,
            format=serialization.PublicFormat.SubjectPublicKeyInfo,
        )
    ).decode("ascii")

    before = _session_recv(mod, sid)

    snap = mod._ratchet_snapshot_recv(sid)
    precheck_n = mod._ratchet_check_and_advance(sid, 2, header)

    failed_n = False
    try:
        mod.decrypt_real_envelope({
            "ephemeralPub": ratchet_pub_b64,
            "ratchetPub": ratchet_pub_b64,
            "salt": base64.b64encode(os.urandom(16)).decode("ascii"),
            "iv": base64.b64encode(os.urandom(12)).decode("ascii"),
            "ciphertext": base64.b64encode(os.urandom(48)).decode("ascii"),
            "ad": "failed-counter-n-dh-step",
            "counter": 2,
            "headerId": header,
        }, sid)
    except Exception:
        failed_n = True
        mod._ratchet_restore_recv(sid, snap)

    after_restore = _session_recv(mod, sid)

    env_n_plus_1 = _build_valid_env(
        mod,
        sid,
        counter=3,
        header_id=header,
        ratchet_pub_b64=ratchet_pub_b64,
        ad="success-counter-n-plus-1-dh-step",
        plaintext="ok-n-plus-1-dh",
    )
    pt, _, _, out_counter = mod.decrypt_real_envelope(env_n_plus_1, sid)

    after_success = _session_recv(mod, sid)

    previously_failed_n_still_accepted = mod._ratchet_check_and_advance(sid, 2, header)
    replay_n_reject_after_accept = not mod._ratchet_check_and_advance(sid, 2, header)

    ok = (
        precheck_n
        and failed_n
        and before == after_restore
        and pt == "ok-n-plus-1-dh"
        and out_counter == 3
        and after_success["step"] == before["step"] + 1
        and bool(after_success["lastPeer"])
        and previously_failed_n_still_accepted
        and replay_n_reject_after_accept
    )

    print(json.dumps({
        "ok": ok,
        "precheckN": precheck_n,
        "failedDecryptN": failed_n,
        "rollbackOk": before == after_restore,
        "nextCounterAccepted": pt == "ok-n-plus-1-dh" and out_counter == 3,
        "dhStepAdvancedOnNPlus1": after_success["step"] == before["step"] + 1,
        "counterNStillAcceptedAfterNPlus1": previously_failed_n_still_accepted,
        "counterNReplayRejectedAfterAccept": replay_n_reject_after_accept,
    }))
    raise SystemExit(0 if ok else 1)


if __name__ == "__main__":
    main()
