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
    base = tempfile.mkdtemp(prefix=f"{prefix}-large-gap-header-scope-smoke-")
    os.environ[f"{prefix}_E2EE_KEYSTORE"] = os.path.join(base, "keys.json")
    os.environ[f"{prefix}_E2EE_RATCHET_STORE"] = os.path.join(base, "ratchet.json")
    os.environ[f"{prefix}_E2EE_OTK_STORE"] = os.path.join(base, "otk.json")

    sid = "large-gap-header-scope-smoke"
    hid_a = "H-A"
    hid_b = "H-B"

    m1 = load_mod(module_path, f"bridge_{prefix.lower()}_large_gap_scope_1")

    # Establish baseline then jump far with header A.
    a1 = m1._ratchet_check_and_advance(sid, 1, hid_a)
    huge_counter = 1_000_000
    a_huge = m1._ratchet_check_and_advance(sid, huge_counter, hid_a)

    # Restart and verify header-scoped acceptance.
    m2 = load_mod(module_path, f"bridge_{prefix.lower()}_large_gap_scope_2")
    expected_floor = huge_counter - 64

    wrong_header_reject = m2._ratchet_check_and_advance(sid, expected_floor, hid_b)
    proper_header_accept = m2._ratchet_check_and_advance(sid, expected_floor, hid_a)
    proper_header_replay_reject = m2._ratchet_check_and_advance(sid, expected_floor, hid_a)

    ok = (
        a1 is True
        and a_huge is True
        and wrong_header_reject is False
        and proper_header_accept is True
        and proper_header_replay_reject is False
    )

    print(json.dumps({
        "ok": ok,
        "hugeCounter": huge_counter,
        "expectedFloor": expected_floor,
        "a1": a1,
        "aHuge": a_huge,
        "wrongHeaderReject": wrong_header_reject,
        "properHeaderAccept": proper_header_accept,
        "properHeaderReplayReject": proper_header_replay_reject,
    }))
    return 0 if ok else 1


if __name__ == "__main__":
    import sys
    if len(sys.argv) != 3:
        print("usage: e2ee_large_gap_header_scope_smoke.py <bridge.py> <OPENCLAW_APP|AIGOR_APP>")
        sys.exit(2)
    raise SystemExit(run(sys.argv[1], sys.argv[2]))
