#!/usr/bin/env python3
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
PY = sys.executable

BRIDGE = str(ROOT / "aigor_chat_bridge.py")

SCRIPTS = [
    ["e2ee_headerid_smoke.py"],
    ["e2ee_seed_progress_smoke.py", BRIDGE, "AIGOR_APP"],
    ["e2ee_strict_mode_smoke.py", BRIDGE, "AIGOR_APP"],
    ["e2ee_attachment_smoke.py", BRIDGE, "AIGOR_APP"],
]


def run_one(args):
    cmd = [PY, str(ROOT / args[0]), *args[1:]]
    p = subprocess.run(cmd, capture_output=True, text=True)
    out = (p.stdout or p.stderr or "").strip()
    return {
        "script": args[0],
        "exit": p.returncode,
        "ok": p.returncode == 0,
        "output": out,
    }


def main():
    results = [run_one(s) for s in SCRIPTS]
    ok = all(r["ok"] for r in results)
    print(json.dumps({"ok": ok, "results": results}, ensure_ascii=False))
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
