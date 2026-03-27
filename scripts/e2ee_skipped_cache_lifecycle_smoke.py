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
    base = tempfile.mkdtemp(prefix=f"{prefix}-skipped-lifecycle-smoke-")
    os.environ[f"{prefix}_E2EE_KEYSTORE"] = os.path.join(base, "keys.json")
    os.environ[f"{prefix}_E2EE_RATCHET_STORE"] = os.path.join(base, "ratchet.json")
    os.environ[f"{prefix}_E2EE_OTK_STORE"] = os.path.join(base, "otk.json")

    sid = "skipped-cache-lifecycle-smoke"
    m1 = load_mod(module_path, f"bridge_{prefix.lower()}_sk_1")

    # Header A opens a gap (2,3) then consumes 2.
    a1 = m1._ratchet_check_and_advance(sid, 1, "hA")
    a4 = m1._ratchet_check_and_advance(sid, 4, "hA")
    b2_wrong = m1._ratchet_check_and_advance(sid, 2, "hB")
    a2 = m1._ratchet_check_and_advance(sid, 2, "hA")

    # Restart: skipped header cache and seen set must persist.
    m2 = load_mod(module_path, f"bridge_{prefix.lower()}_sk_2")
    st2 = m2._load_ratchet_store()["sessions"][sid]
    recv2 = st2["recv"]

    # Header B opens its own gap (5) and must not consume A's missing counter (3).
    b6 = m2._ratchet_check_and_advance(sid, 6, "hB")
    b3_wrong = m2._ratchet_check_and_advance(sid, 3, "hB")
    a3 = m2._ratchet_check_and_advance(sid, 3, "hA")

    # Restart again: ensure remaining skipped key is only B:5, then consume/replay check.
    m3 = load_mod(module_path, f"bridge_{prefix.lower()}_sk_3")
    st3 = m3._load_ratchet_store()["sessions"][sid]
    recv3 = st3["recv"]
    b5 = m3._ratchet_check_and_advance(sid, 5, "hB")
    b5_replay = m3._ratchet_check_and_advance(sid, 5, "hB")

    skipped2 = recv2.get("skippedByHeader", {}) if isinstance(recv2.get("skippedByHeader"), dict) else {}
    skipped3 = recv3.get("skippedByHeader", {}) if isinstance(recv3.get("skippedByHeader"), dict) else {}

    ok = (
        a1 is True and
        a4 is True and
        b2_wrong is False and
        a2 is True and
        int(recv2.get("maxIn", 0)) == 4 and
        int(recv2.get("seenIn", [])[-1]) == 4 and
        3 in set(int(x) for x in recv2.get("skippedIn", []) if isinstance(x, int) or str(x).isdigit()) and
        skipped2.get("hA", []) == [3] and
        b6 is True and
        b3_wrong is False and
        a3 is True and
        int(recv3.get("maxIn", 0)) == 6 and
        skipped3.get("hA") is None and
        skipped3.get("hB", []) == [5] and
        b5 is True and
        b5_replay is False
    )

    print(json.dumps({
        "ok": ok,
        "a1": a1,
        "a4": a4,
        "b2Wrong": b2_wrong,
        "a2": a2,
        "maxInAfterRestart1": int(recv2.get("maxIn", 0)),
        "skippedAfterRestart1": recv2.get("skippedByHeader", {}),
        "b6": b6,
        "b3Wrong": b3_wrong,
        "a3": a3,
        "maxInAfterRestart2": int(recv3.get("maxIn", 0)),
        "skippedAfterRestart2": recv3.get("skippedByHeader", {}),
        "b5": b5,
        "b5Replay": b5_replay,
    }))
    return 0 if ok else 1


if __name__ == "__main__":
    import sys
    if len(sys.argv) != 3:
        print("usage: e2ee_skipped_cache_lifecycle_smoke.py <bridge.py> <OPENCLAW_APP|AIGOR_APP>")
        sys.exit(2)
    raise SystemExit(run(sys.argv[1], sys.argv[2]))
