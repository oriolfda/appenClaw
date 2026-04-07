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
    return {
        "recvChainSeed": st.get("recvChainSeed", ""),
        "rootKeySeed": st.get("rootKeySeed", ""),
        "recvChainCounter": int(st.get("recv", {}).get("chainCounter", 0)),
        "sendChainCounter": int(st.get("send", {}).get("chainCounter", 0)),
    }


def main():
    import sys

    script_path = Path(sys.argv[1]) if len(sys.argv) > 1 else Path(__file__).with_name("appenclaw_chat_bridge.py")
    env_prefix = (sys.argv[2] if len(sys.argv) > 2 else "appenClaw_APP").upper()

    tmp = Path(tempfile.mkdtemp(prefix="e2ee-failed-decrypt-no-drift-smoke-"))
    os.environ[f"{env_prefix}_E2EE_KEYSTORE"] = str(tmp / "keys.json")
    os.environ[f"{env_prefix}_E2EE_RATCHET_STORE"] = str(tmp / "ratchet.json")
    os.environ[f"{env_prefix}_E2EE_OTK_STORE"] = str(tmp / "otk.json")

    mod = load_bridge(script_path, "bridge_no_drift")
    sid = "failed-decrypt-no-drift"

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
        "ad": "failed-decrypt-smoke",
        "counter": 2,
        "headerId": "hdr-failed",
    }

    # Case A: existing recv/root state must remain unchanged after failed decrypt.
    mod._ratchet_mix_chain_key(sid, os.urandom(32), "c2s", 1)
    before_seeded = session_state(mod, sid)
    failed_seeded = False
    try:
        mod.decrypt_real_envelope(env, sid)
    except Exception:
        failed_seeded = True
    after_seeded = session_state(mod, sid)

    # Case B: empty initial state must not be initialized by failed decrypt.
    sid_empty = "failed-decrypt-no-drift-empty"
    before_empty = session_state(mod, sid_empty)
    failed_empty = False
    try:
        mod.decrypt_real_envelope(env, sid_empty)
    except Exception:
        failed_empty = True
    after_empty = session_state(mod, sid_empty)

    ok_seeded = (
        failed_seeded
        and before_seeded["recvChainSeed"] == after_seeded["recvChainSeed"]
        and before_seeded["rootKeySeed"] == after_seeded["rootKeySeed"]
        and before_seeded["recvChainCounter"] == after_seeded["recvChainCounter"]
        and before_seeded["sendChainCounter"] == after_seeded["sendChainCounter"]
    )
    ok_empty = (
        failed_empty
        and before_empty["recvChainSeed"] == after_empty["recvChainSeed"]
        and before_empty["rootKeySeed"] == after_empty["rootKeySeed"]
        and before_empty["recvChainCounter"] == after_empty["recvChainCounter"]
        and before_empty["sendChainCounter"] == after_empty["sendChainCounter"]
    )
    ok = ok_seeded and ok_empty

    print(json.dumps({
        "ok": ok,
        "seeded": {"failedDecrypt": failed_seeded, "before": before_seeded, "after": after_seeded},
        "empty": {"failedDecrypt": failed_empty, "before": before_empty, "after": after_empty},
    }))
    raise SystemExit(0 if ok else 1)


if __name__ == "__main__":
    main()
