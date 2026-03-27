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
    base = tempfile.mkdtemp(prefix=f"{prefix}-large-gap-window-cap-smoke-")
    os.environ[f"{prefix}_E2EE_KEYSTORE"] = os.path.join(base, "keys.json")
    os.environ[f"{prefix}_E2EE_RATCHET_STORE"] = os.path.join(base, "ratchet.json")
    os.environ[f"{prefix}_E2EE_OTK_STORE"] = os.path.join(base, "otk.json")

    sid = "large-gap-window-cap-smoke"
    hid = "H-LARGE-GAP"

    m1 = load_mod(module_path, f"bridge_{prefix.lower()}_large_gap_1")

    # Baseline receive.
    a1 = m1._ratchet_check_and_advance(sid, 1, hid)

    # Very large in-range gap; skipped materialization must stay window-bounded.
    huge_counter = 1_000_000
    a_huge = m1._ratchet_check_and_advance(sid, huge_counter, hid)

    # Simulate restart and inspect persisted window.
    m2 = load_mod(module_path, f"bridge_{prefix.lower()}_large_gap_2")
    st2 = m2._load_ratchet_store()["sessions"][sid]
    recv2 = st2["recv"]
    skipped_h = recv2.get("skippedByHeader", {}).get(hid, [])

    expected_floor = huge_counter - 64
    expected_top = huge_counter - 1

    # Validate that only window-sized skipped counters are persisted.
    bounded_window = len(skipped_h) <= 64
    floor_ok = (min(skipped_h) == expected_floor) if skipped_h else False
    top_ok = (max(skipped_h) == expected_top) if skipped_h else False

    # Old counters below floor must be rejected.
    old_reject = m2._ratchet_check_and_advance(sid, expected_floor - 1, hid)
    # Floor is still within window and should be accepted exactly once.
    floor_accept = m2._ratchet_check_and_advance(sid, expected_floor, hid)
    floor_replay_reject = m2._ratchet_check_and_advance(sid, expected_floor, hid)

    ok = (
        a1 is True
        and a_huge is True
        and int(recv2.get("maxIn", 0)) == huge_counter
        and bounded_window
        and floor_ok
        and top_ok
        and old_reject is False
        and floor_accept is True
        and floor_replay_reject is False
    )

    print(json.dumps({
        "ok": ok,
        "a1": a1,
        "aHuge": a_huge,
        "hugeCounter": huge_counter,
        "maxIn": int(recv2.get("maxIn", 0)),
        "skippedCount": len(skipped_h),
        "minSkipped": min(skipped_h) if skipped_h else None,
        "maxSkipped": max(skipped_h) if skipped_h else None,
        "expectedFloor": expected_floor,
        "expectedTop": expected_top,
        "oldReject": old_reject,
        "floorAccept": floor_accept,
        "floorReplayReject": floor_replay_reject,
    }))
    return 0 if ok else 1


if __name__ == "__main__":
    import sys
    if len(sys.argv) != 3:
        print("usage: e2ee_large_gap_window_cap_smoke.py <bridge.py> <OPENCLAW_APP|AIGOR_APP>")
        sys.exit(2)
    raise SystemExit(run(sys.argv[1], sys.argv[2]))
