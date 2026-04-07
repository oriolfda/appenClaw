#!/usr/bin/env python3
import importlib.util
import json
import os
import tempfile


def load_mod(path: str, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def b64(s: str) -> bytes:
    import base64
    return base64.b64decode(s) if s else b""


def run(module_path: str, prefix: str):
    base = tempfile.mkdtemp(prefix=f"{prefix}-seed-smoke-")
    os.environ[f"{prefix}_E2EE_KEYSTORE"] = os.path.join(base, "keys.json")
    os.environ[f"{prefix}_E2EE_RATCHET_STORE"] = os.path.join(base, "ratchet.json")
    os.environ[f"{prefix}_E2EE_OTK_STORE"] = os.path.join(base, "otk.json")

    m = load_mod(module_path, f"bridge_{prefix.lower()}_a")
    sid = "seed-smoke"

    # Inbound seed must rotate per message.
    r1 = m._ratchet_mix_chain_key(sid, b"base-r", "c2s", 1)
    r2 = m._ratchet_mix_chain_key(sid, b"base-r", "c2s", 2)

    # Outbound seed must rotate per message and survive restart.
    out1 = m._ratchet_next_out_counter(sid)
    s1 = m._ratchet_mix_chain_key(sid, b"base-s", "s2c", out1)

    m2 = load_mod(module_path, f"bridge_{prefix.lower()}_b")
    out2 = m2._ratchet_next_out_counter(sid)
    s2 = m2._ratchet_mix_chain_key(sid, b"base-s", "s2c", out2)

    st = m2._load_ratchet_store()["sessions"][sid]
    recv_seed = b64(st.get("recvChainSeed", ""))
    send_seed = b64(st.get("sendChainSeed", ""))

    ok = (
        r1 != r2 and
        s1 != s2 and
        out1 == 1 and out2 == 2 and
        recv_seed == r2 and
        send_seed == s2 and
        int(st["recv"].get("chainCounter", 0)) >= 2 and
        int(st["send"].get("chainCounter", 0)) >= 2
    )

    print(json.dumps({
        "ok": ok,
        "outCounters": [out1, out2],
        "recvChainCounter": st["recv"].get("chainCounter", 0),
        "sendChainCounter": st["send"].get("chainCounter", 0),
    }))
    return 0 if ok else 1


if __name__ == "__main__":
    import sys
    if len(sys.argv) != 3:
        print("usage: e2ee_seed_progress_smoke.py <bridge.py> <APPENCLAW_APP|appenClaw_APP>")
        sys.exit(2)
    raise SystemExit(run(sys.argv[1], sys.argv[2]))
