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


def session_state(mod, sid: str):
    store = mod._load_ratchet_store()
    st = store.setdefault("sessions", {}).setdefault(sid, {})
    st = mod._ensure_session_chains(st)
    recv = st.get("recv", {})
    send = st.get("send", {})
    return {
        "recvChainSeed": st.get("recvChainSeed", ""),
        "sendChainSeed": st.get("sendChainSeed", ""),
        "rootKeySeed": st.get("rootKeySeed", ""),
        "recvChainCounter": int(recv.get("chainCounter", 0)),
        "sendChainCounter": int(send.get("chainCounter", 0)),
        "ratchetStep": int(recv.get("ratchetStep", 0)),
        "lastPeerRatchetPub": str(recv.get("lastPeerRatchetPub", "") or ""),
        "maxIn": int(recv.get("maxIn", 0)),
        "seenIn": list(recv.get("seenIn", []) or []),
        "skippedIn": list(recv.get("skippedIn", []) or []),
    }


def main():
    import sys

    script_path = Path(sys.argv[1]) if len(sys.argv) > 1 else Path(__file__).with_name("aigor_chat_bridge.py")
    env_prefix = (sys.argv[2] if len(sys.argv) > 2 else "AIGOR_APP").upper()

    tmp = Path(tempfile.mkdtemp(prefix="e2ee-failed-decrypt-dh-step-rollback-smoke-"))
    os.environ[f"{env_prefix}_E2EE_KEYSTORE"] = str(tmp / "keys.json")
    os.environ[f"{env_prefix}_E2EE_RATCHET_STORE"] = str(tmp / "ratchet.json")
    os.environ[f"{env_prefix}_E2EE_OTK_STORE"] = str(tmp / "otk.json")

    mod = load_bridge(script_path, "bridge_dh_step_rollback")
    sid = "failed-decrypt-dh-step-rollback"

    # Seed state with existing chain progression before introducing new ratchetPub.
    mod._ratchet_mix_chain_key(sid, os.urandom(32), "c2s", 1)
    mod._ratchet_mix_chain_key(sid, os.urandom(32), "s2c", 1)

    eph_priv = x25519.X25519PrivateKey.generate()
    eph_pub_b64 = base64.b64encode(
        eph_priv.public_key().public_bytes(
            encoding=serialization.Encoding.DER,
            format=serialization.PublicFormat.SubjectPublicKeyInfo,
        )
    ).decode("ascii")

    new_ratchet_priv = x25519.X25519PrivateKey.generate()
    new_ratchet_pub_b64 = base64.b64encode(
        new_ratchet_priv.public_key().public_bytes(
            encoding=serialization.Encoding.DER,
            format=serialization.PublicFormat.SubjectPublicKeyInfo,
        )
    ).decode("ascii")

    env = {
        "ephemeralPub": eph_pub_b64,
        "ratchetPub": new_ratchet_pub_b64,
        "salt": base64.b64encode(os.urandom(16)).decode("ascii"),
        "iv": base64.b64encode(os.urandom(12)).decode("ascii"),
        "ciphertext": base64.b64encode(os.urandom(48)).decode("ascii"),
        "ad": "failed-decrypt-dh-step-rollback-smoke",
        "counter": 2,
        "headerId": "hdr-dh-rollback",
    }

    before = session_state(mod, sid)

    snap = mod._ratchet_snapshot_recv(sid)
    precheck_ok = mod._ratchet_check_and_advance(sid, 2, "hdr-dh-rollback")

    failed = False
    try:
        mod.decrypt_real_envelope(env, sid)
    except Exception:
        failed = True
        mod._ratchet_restore_recv(sid, snap)

    after = session_state(mod, sid)
    accepted_after_restore = mod._ratchet_check_and_advance(sid, 2, "hdr-dh-rollback")
    replay_reject_after_accept = not mod._ratchet_check_and_advance(sid, 2, "hdr-dh-rollback")

    rollback_ok = before == after
    ok = precheck_ok and failed and rollback_ok and accepted_after_restore and replay_reject_after_accept

    print(json.dumps({
        "ok": ok,
        "precheckOk": precheck_ok,
        "failedDecrypt": failed,
        "rollbackOk": rollback_ok,
        "acceptedAfterRestore": accepted_after_restore,
        "replayRejectAfterAccept": replay_reject_after_accept,
        "before": before,
        "after": after,
    }))
    raise SystemExit(0 if ok else 1)


if __name__ == "__main__":
    main()
