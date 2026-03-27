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


def main():
    import sys

    script_path = Path(sys.argv[1]) if len(sys.argv) > 1 else Path(__file__).with_name("aigor_chat_bridge.py")
    env_prefix = (sys.argv[2] if len(sys.argv) > 2 else "AIGOR_APP").upper()

    tmp = Path(tempfile.mkdtemp(prefix="e2ee-failed-decrypt-replay-slot-smoke-"))
    os.environ[f"{env_prefix}_E2EE_KEYSTORE"] = str(tmp / "keys.json")
    os.environ[f"{env_prefix}_E2EE_RATCHET_STORE"] = str(tmp / "ratchet.json")
    os.environ[f"{env_prefix}_E2EE_OTK_STORE"] = str(tmp / "otk.json")

    mod = load_bridge(script_path, "bridge_replay_slot")
    sid = "failed-decrypt-replay-slot"

    # Seed ratchet once so decrypt path has stable state to operate on.
    mod._ratchet_mix_chain_key(sid, os.urandom(32), "c2s", 1)

    eph_priv = x25519.X25519PrivateKey.generate()
    eph_pub_b64 = base64.b64encode(
        eph_priv.public_key().public_bytes(
            encoding=serialization.Encoding.DER,
            format=serialization.PublicFormat.SubjectPublicKeyInfo,
        )
    ).decode("ascii")

    env = {
        "ephemeralPub": eph_pub_b64,
        "salt": base64.b64encode(os.urandom(16)).decode("ascii"),
        "iv": base64.b64encode(os.urandom(12)).decode("ascii"),
        "ciphertext": base64.b64encode(os.urandom(48)).decode("ascii"),
        "ad": "failed-decrypt-replay-slot-smoke",
        "counter": 2,
        "headerId": "hdr-slot",
    }

    # Simulate server flow: pre-check consumes slot, decrypt fails, then restore snapshot.
    snap = mod._ratchet_snapshot_recv(sid)
    precheck_ok = mod._ratchet_check_and_advance(sid, 2, "hdr-slot")

    failed = False
    try:
        mod.decrypt_real_envelope(env, sid)
    except Exception:
        failed = True
        mod._ratchet_restore_recv(sid, snap)

    # After restore, same inbound should still be accepted once.
    accepted_after_restore = mod._ratchet_check_and_advance(sid, 2, "hdr-slot")
    replay_reject_after_accept = not mod._ratchet_check_and_advance(sid, 2, "hdr-slot")

    ok = precheck_ok and failed and accepted_after_restore and replay_reject_after_accept

    print(json.dumps({
        "ok": ok,
        "precheckOk": precheck_ok,
        "failedDecrypt": failed,
        "acceptedAfterRestore": accepted_after_restore,
        "replayRejectAfterAccept": replay_reject_after_accept,
    }))
    raise SystemExit(0 if ok else 1)


if __name__ == "__main__":
    main()
