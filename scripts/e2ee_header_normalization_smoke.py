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


def run(module_path: str, prefix: str):
    base = tempfile.mkdtemp(prefix=f"{prefix}-header-normalization-smoke-")
    os.environ[f"{prefix}_E2EE_KEYSTORE"] = os.path.join(base, "keys.json")
    os.environ[f"{prefix}_E2EE_RATCHET_STORE"] = os.path.join(base, "ratchet.json")
    os.environ[f"{prefix}_E2EE_OTK_STORE"] = os.path.join(base, "otk.json")

    m = load_mod(module_path, f"bridge_{prefix.lower()}_header_norm")
    sid = "header-normalization-smoke"

    # Simula normalització a l'entrada HTTP (strip + fallback default)
    norm = lambda h: str(h).strip() or "default"

    first = m._ratchet_check_and_advance(sid, 1, norm("  hA  "))
    replay_trimmed = m._ratchet_check_and_advance(sid, 1, norm("hA"))
    next_trimmed = m._ratchet_check_and_advance(sid, 2, norm("hA"))
    replay_spaced = m._ratchet_check_and_advance(sid, 2, norm("   hA   "))

    ok = first and (not replay_trimmed) and next_trimmed and (not replay_spaced)

    print(json.dumps({
        "ok": ok,
        "first": first,
        "replayTrimmed": replay_trimmed,
        "nextTrimmed": next_trimmed,
        "replaySpaced": replay_spaced,
    }))
    return 0 if ok else 1


if __name__ == "__main__":
    import sys
    if len(sys.argv) != 3:
        print("usage: e2ee_header_normalization_smoke.py <bridge.py> <APPENCLAW_APP|appenClaw_APP>")
        sys.exit(2)
    raise SystemExit(run(sys.argv[1], sys.argv[2]))
