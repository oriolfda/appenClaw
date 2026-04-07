#!/usr/bin/env python3
"""HeaderId isolation smoke test for inbound skipped-counter validation.
Expected sequence result: T,T,F,T,F for A1,A3,B2,A2,A2(replay)
"""
import importlib.util
import os
import tempfile


def load_mod(path):
    spec = importlib.util.spec_from_file_location("bridge_mod", path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def run(path, prefix):
    base = tempfile.mkdtemp(prefix=f"{prefix}-")
    os.environ[f"{prefix}_E2EE_KEYSTORE"] = os.path.join(base, "keystore.json")
    os.environ[f"{prefix}_E2EE_RATCHET_STORE"] = os.path.join(base, "ratchet.json")
    os.environ[f"{prefix}_E2EE_OTK_STORE"] = os.path.join(base, "otk.json")
    m = load_mod(path)
    sid = "smoke-header"
    out = [
        m._ratchet_check_and_advance(sid, 1, "hA"),
        m._ratchet_check_and_advance(sid, 3, "hA"),
        m._ratchet_check_and_advance(sid, 2, "hB"),
        m._ratchet_check_and_advance(sid, 2, "hA"),
        m._ratchet_check_and_advance(sid, 2, "hA"),
    ]
    print("result:", ",".join("T" if x else "F" for x in out))
    ok = out == [True, True, False, True, False]
    print("ok:", ok)
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(run(
        "/home/oriol/.appenclaw/workspace/appenclaw-app/scripts/appenclaw_chat_bridge.py",
        "appenClaw_APP",
    ))
