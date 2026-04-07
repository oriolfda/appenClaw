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
    base = tempfile.mkdtemp(prefix=f"{prefix}-window-eviction-smoke-")
    os.environ[f"{prefix}_E2EE_KEYSTORE"] = os.path.join(base, "keys.json")
    os.environ[f"{prefix}_E2EE_RATCHET_STORE"] = os.path.join(base, "ratchet.json")
    os.environ[f"{prefix}_E2EE_OTK_STORE"] = os.path.join(base, "otk.json")

    sid = "window-eviction-smoke"
    hid = "H-EVICT"
    wrong_hid = "H-WRONG"

    m1 = load_mod(module_path, f"bridge_{prefix.lower()}_window_1")

    # Open window and force many skipped counters.
    a1 = m1._ratchet_check_and_advance(sid, 1, hid)
    a70 = m1._ratchet_check_and_advance(sid, 70, hid)

    # Simulate restart and validate compacted persisted state.
    m2 = load_mod(module_path, f"bridge_{prefix.lower()}_window_2")
    st2 = m2._load_ratchet_store()["sessions"][sid]
    recv2 = st2["recv"]
    skipped_h = recv2.get("skippedByHeader", {}).get(hid, [])

    # floor=max-window=70-64=6 so 2..5 should be evicted.
    has_floor = (len(skipped_h) > 0 and min(skipped_h) == 6)
    has_top = (len(skipped_h) > 0 and max(skipped_h) == 69)

    old_reject = m2._ratchet_check_and_advance(sid, 5, hid)
    in_window_accept = m2._ratchet_check_and_advance(sid, 6, hid)
    wrong_header_reject = m2._ratchet_check_and_advance(sid, 7, wrong_hid)
    proper_header_accept = m2._ratchet_check_and_advance(sid, 7, hid)
    replay_reject = m2._ratchet_check_and_advance(sid, 7, hid)

    ok = (
        a1 is True and
        a70 is True and
        int(recv2.get("maxIn", 0)) == 70 and
        has_floor and
        has_top and
        old_reject is False and
        in_window_accept is True and
        wrong_header_reject is False and
        proper_header_accept is True and
        replay_reject is False
    )

    print(json.dumps({
        "ok": ok,
        "a1": a1,
        "a70": a70,
        "maxIn": int(recv2.get("maxIn", 0)),
        "minSkipped": min(skipped_h) if skipped_h else None,
        "maxSkipped": max(skipped_h) if skipped_h else None,
        "oldReject": old_reject,
        "inWindowAccept": in_window_accept,
        "wrongHeaderReject": wrong_header_reject,
        "properHeaderAccept": proper_header_accept,
        "replayReject": replay_reject,
    }))
    return 0 if ok else 1


if __name__ == "__main__":
    import sys
    if len(sys.argv) != 3:
        print("usage: e2ee_window_eviction_smoke.py <bridge.py> <APPENCLAW_APP|appenClaw_APP>")
        sys.exit(2)
    raise SystemExit(run(sys.argv[1], sys.argv[2]))
