#!/usr/bin/env python3
import json
import os
import subprocess
import sys
import tempfile
import time
import urllib.request


def post(url: str, token: str, payload: dict):
    req = urllib.request.Request(
        url,
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {token}",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=10) as r:
            return r.getcode(), json.loads(r.read().decode("utf-8") or "{}")
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8") if e.fp else "{}"
        try:
            obj = json.loads(body or "{}")
        except Exception:
            obj = {"raw": body}
        return e.code, obj


def wait_ready(url: str, token: str, timeout_s: int = 12):
    start = time.time()
    while time.time() - start < timeout_s:
        try:
            req = urllib.request.Request(
                url.replace("/chat", "/e2ee/status"),
                headers={"Authorization": f"Bearer {token}"},
                method="GET",
            )
            with urllib.request.urlopen(req, timeout=2) as r:
                if r.getcode() == 200:
                    return True
        except Exception:
            pass
        time.sleep(0.3)
    return False


def main():
    if len(sys.argv) < 3:
        print("usage: e2ee_strict_mode_smoke.py <bridge_script.py> <ENV_PREFIX>", file=sys.stderr)
        sys.exit(2)

    bridge_script = os.path.abspath(sys.argv[1])
    env_prefix = sys.argv[2].strip().upper()

    port = 18989
    token = "strict-smoke-token"

    tmpdir = tempfile.mkdtemp(prefix="e2ee-strict-smoke-")
    env = os.environ.copy()
    bridge_prefix = "OPENCLAW_APP" if env_prefix == "OPENCLAW_APP" else "AIGOR"
    env[f"{bridge_prefix}_BRIDGE_HOST"] = "127.0.0.1"
    env[f"{bridge_prefix}_BRIDGE_PORT"] = str(port)
    env[f"{bridge_prefix}_BRIDGE_TOKEN"] = token
    env[f"{env_prefix}_E2EE_REQUIRED"] = "true"
    env[f"{env_prefix}_E2EE_KEYSTORE"] = os.path.join(tmpdir, "keystore.json")
    env[f"{env_prefix}_E2EE_RATCHET_STORE"] = os.path.join(tmpdir, "ratchet.json")
    env[f"{env_prefix}_E2EE_OTK_STORE"] = os.path.join(tmpdir, "otk.json")

    proc = subprocess.Popen([sys.executable, bridge_script], env=env, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    try:
        url = f"http://127.0.0.1:{port}/chat"
        if not wait_ready(url, token):
            raise RuntimeError("bridge did not become ready")

        cases = []

        # 1) no e2ee envelope
        c1 = post(url, token, {"sessionId": "smoke", "message": "hola"})
        cases.append(("missing_e2ee", c1[0] == 400 and c1[1].get("error") == "e2ee_required", c1))

        # 2) envelope without ciphertext
        c2 = post(url, token, {"sessionId": "smoke", "message": "hola", "e2ee": {}})
        cases.append(("missing_ciphertext", c2[0] == 400 and c2[1].get("error") == "e2ee_ciphertext_required", c2))

        # 3) clear attachment without e2eeAttachment
        c3 = post(
            url,
            token,
            {
                "sessionId": "smoke",
                "e2ee": {"ciphertext": "x"},
                "attachment": {"name": "a.txt", "mime": "text/plain", "dataBase64": "YQ=="},
            },
        )
        cases.append(("clear_attachment", c3[0] == 400 and c3[1].get("error") == "e2ee_attachment_required", c3))

        ok = all(x[1] for x in cases)
        out = {
            "ok": ok,
            "cases": [
                {
                    "name": name,
                    "pass": passed,
                    "status": data[0],
                    "error": data[1].get("error"),
                }
                for name, passed, data in cases
            ],
        }
        print(json.dumps(out, ensure_ascii=False), flush=True)
        sys.exit(0 if ok else 1)
    finally:
        proc.terminate()
        try:
            proc.wait(timeout=3)
        except Exception:
            proc.kill()
