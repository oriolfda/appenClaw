#!/usr/bin/env python3
import base64
import importlib.util
import json
import os
import tempfile
import uuid
from pathlib import Path
from cryptography.hazmat.primitives.ciphers.aead import AESGCM


def load_bridge(path: Path):
    spec = importlib.util.spec_from_file_location("bridge_mod", str(path))
    mod = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    spec.loader.exec_module(mod)
    return mod


def main():
    import sys

    script_path = Path(sys.argv[1]) if len(sys.argv) > 1 else Path(__file__).with_name("appenclaw_chat_bridge.py")
    env_prefix = (sys.argv[2] if len(sys.argv) > 2 else "appenClaw_APP").upper()

    tmp = Path(tempfile.mkdtemp(prefix="e2ee-attachment-smoke-"))
    os.environ[f"{env_prefix}_E2EE_KEYSTORE"] = str(tmp / "keys.json")
    os.environ[f"{env_prefix}_E2EE_RATCHET_STORE"] = str(tmp / "ratchet.json")
    os.environ[f"{env_prefix}_E2EE_OTK_STORE"] = str(tmp / "otk.json")

    mod = load_bridge(script_path)

    payload = f"hello-attachment-{uuid.uuid4().hex}".encode("utf-8")
    ad = "smoke-session"
    counter = 7
    base_key = os.urandom(32)

    recv_chain = mod._derive_chain_key(base_key, "recv")
    att_key = mod._derive_message_key(recv_chain, counter, "att")
    iv = os.urandom(12)
    ct = AESGCM(att_key).encrypt(iv, payload, ad.encode("utf-8"))

    att = {
        "name": "sample.txt",
        "mime": "text/plain",
        "iv": base64.b64encode(iv).decode("ascii"),
        "ciphertext": base64.b64encode(ct).decode("ascii"),
        "ad": ad,
        "counter": counter,
    }

    decoded = mod.decrypt_e2ee_attachment(att, base_key)
    recovered = base64.b64decode(decoded["dataBase64"])

    ok = recovered == payload and decoded.get("mime") == "text/plain"
    print(json.dumps({
        "ok": ok,
        "name": decoded.get("name"),
        "mime": decoded.get("mime"),
        "bytes": len(recovered),
    }))
    raise SystemExit(0 if ok else 1)


if __name__ == "__main__":
    main()



if __name__ == "__main__":
    main()
