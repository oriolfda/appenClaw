#!/usr/bin/env python3
import base64
import json
import os
import subprocess
import sys
import tempfile
import time
import urllib.request
import socket


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
    env_prefix = sys.argv[2].strip().upper().replace("-", "_")

    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("127.0.0.1", 0))
        port = s.getsockname()[1]
    token = "strict-smoke-token"

    tmpdir = tempfile.mkdtemp(prefix="e2ee-strict-smoke-")
    env = os.environ.copy()
    if env_prefix in ("APPENCLAW_APP", "APPENCLAW"):
        bridge_prefix = "APPENCLAW_APP"
        e2ee_prefix = "APPENCLAW_APP"
    elif env_prefix in ("appenClaw_APP", "appenClaw"):
        bridge_prefix = "appenClaw"
        e2ee_prefix = "appenClaw_APP"
    else:
        raise RuntimeError(f"unsupported ENV_PREFIX={env_prefix} (expected APPENCLAW_APP/APPENCLAW or appenClaw_APP/appenClaw)")

    env[f"{bridge_prefix}_BRIDGE_HOST"] = "127.0.0.1"
    env[f"{bridge_prefix}_BRIDGE_PORT"] = str(port)
    env[f"{bridge_prefix}_BRIDGE_TOKEN"] = token
    env[f"{e2ee_prefix}_E2EE_REQUIRED"] = "true"
    env[f"{e2ee_prefix}_E2EE_KEYSTORE"] = os.path.join(tmpdir, "keystore.json")
    env[f"{e2ee_prefix}_E2EE_RATCHET_STORE"] = os.path.join(tmpdir, "ratchet.json")
    env[f"{e2ee_prefix}_E2EE_OTK_STORE"] = os.path.join(tmpdir, "otk.json")

    proc = subprocess.Popen([sys.executable, bridge_script], env=env, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    try:
        url = f"http://127.0.0.1:{port}/chat"
        if not wait_ready(url, token):
            err = ""
            try:
                err = (proc.stderr.read() or b"").decode("utf-8", errors="ignore") if proc.stderr else ""
            except Exception:
                err = ""
            raise RuntimeError(f"bridge did not become ready on port {port}. stderr={err[-400:]}")

        cases = []
        valid_ephemeral_pub = "AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA="
        valid_iv_12 = "YWJjZGVmZ2hpamts"
        valid_salt_16 = "MDEyMzQ1Njc4OWFiY2RlZg=="

        # 1) no e2ee envelope
        c1 = post(url, token, {"sessionId": "smoke", "message": "hola"})
        cases.append(("missing_e2ee", c1[0] == 400 and c1[1].get("error") == "e2ee_required", c1))

        # 1a) null e2ee envelope (must be rejected as required)
        c1a = post(url, token, {"sessionId": "smoke", "e2ee": None})
        cases.append(("null_e2ee_rejected", c1a[0] == 400 and c1a[1].get("error") == "e2ee_required", c1a))

        # 1b) invalid e2ee envelope type (must be object)
        c1b = post(url, token, {"sessionId": "smoke", "e2ee": []})
        cases.append(("invalid_e2ee_type", c1b[0] == 400 and c1b[1].get("error") == "e2ee_required", c1b))

        # 1c) bool(true) e2ee envelope (must still be rejected as non-object)
        c1c = post(url, token, {"sessionId": "smoke", "e2ee": True})
        cases.append(("bool_e2ee_rejected", c1c[0] == 400 and c1c[1].get("error") == "e2ee_required", c1c))

        # 1c2) bool(false) e2ee envelope (must still be rejected as non-object)
        c1c2 = post(url, token, {"sessionId": "smoke", "e2ee": False})
        cases.append(("bool_false_e2ee_rejected", c1c2[0] == 400 and c1c2[1].get("error") == "e2ee_required", c1c2))

        # 1d) string e2ee envelope (must still be rejected as non-object)
        c1d = post(url, token, {"sessionId": "smoke", "e2ee": "true"})
        cases.append(("string_e2ee_rejected", c1d[0] == 400 and c1d[1].get("error") == "e2ee_required", c1d))

        # 1e) numeric e2ee envelope (must still be rejected as non-object)
        c1e = post(url, token, {"sessionId": "smoke", "e2ee": 1})
        cases.append(("number_e2ee_rejected", c1e[0] == 400 and c1e[1].get("error") == "e2ee_required", c1e))

        # 1f) float e2ee envelope (must still be rejected as non-object)
        c1f = post(url, token, {"sessionId": "smoke", "e2ee": 1.5})
        cases.append(("float_e2ee_rejected", c1f[0] == 400 and c1f[1].get("error") == "e2ee_required", c1f))

        # 1g) whitespace-only string e2ee envelope (must still be rejected as non-object)
        c1g = post(url, token, {"sessionId": "smoke", "e2ee": "   "})
        cases.append(("blank_string_e2ee_rejected", c1g[0] == 400 and c1g[1].get("error") == "e2ee_required", c1g))

        # 2) envelope without ciphertext
        c2 = post(url, token, {"sessionId": "smoke", "message": "hola", "e2ee": {}})
        cases.append(("missing_ciphertext", c2[0] == 400 and c2[1].get("error") == "e2ee_ciphertext_required", c2))

        # 2b) envelope with blank ciphertext (must be rejected)
        c2b = post(url, token, {"sessionId": "smoke", "e2ee": {"ciphertext": "   "}})
        cases.append(("blank_ciphertext", c2b[0] == 400 and c2b[1].get("error") == "e2ee_ciphertext_required", c2b))

        # 2c) envelope with non-string ciphertext (must be rejected)
        c2c = post(url, token, {"sessionId": "smoke", "e2ee": {"ciphertext": 123}})
        cases.append(("invalid_ciphertext_type", c2c[0] == 400 and c2c[1].get("error") == "e2ee_ciphertext_required", c2c))

        # 2d) envelope with null ciphertext (must be rejected as required)
        c2d = post(url, token, {"sessionId": "smoke", "e2ee": {"ciphertext": None}})
        cases.append(("null_ciphertext_rejected", c2d[0] == 400 and c2d[1].get("error") == "e2ee_ciphertext_required", c2d))

        # 3) encrypted envelope missing headerId
        c3 = post(url, token, {"sessionId": "smoke", "e2ee": {"ciphertext": "x"}})
        cases.append(("missing_header", c3[0] == 400 and c3[1].get("error") == "e2ee_header_required", c3))

        # 4) encrypted envelope with non-string headerId (must be rejected)
        c4 = post(url, token, {"sessionId": "smoke", "e2ee": {"ciphertext": "x", "headerId": 123}})
        cases.append(("invalid_header_type", c4[0] == 400 and c4[1].get("error") == "e2ee_header_required", c4))

        # 4b) encrypted envelope with null headerId (must be rejected)
        c4b = post(url, token, {"sessionId": "smoke", "e2ee": {"ciphertext": "x", "headerId": None}})
        cases.append(("null_header_rejected", c4b[0] == 400 and c4b[1].get("error") == "e2ee_header_required", c4b))

        # 5) encrypted envelope with blank-string headerId (must be rejected)
        c5 = post(url, token, {"sessionId": "smoke", "e2ee": {"ciphertext": "x", "headerId": "   "}})
        cases.append(("blank_header", c5[0] == 400 and c5[1].get("error") == "e2ee_header_required", c5))

        # 5b) encrypted envelope with oversized headerId (anti-abuse cap)
        c5b = post(url, token, {"sessionId": "smoke", "e2ee": {"ciphertext": "x", "headerId": "h" * 129}})
        cases.append(("oversized_header_rejected", c5b[0] == 400 and c5b[1].get("error") == "e2ee_header_too_long", c5b))

        # 5c) oversized headerId with surrounding spaces must still be rejected after trim
        c5c = post(url, token, {"sessionId": "smoke", "e2ee": {"ciphertext": "x", "headerId": "  " + ("h" * 129) + "  "}})
        cases.append(("oversized_header_trimmed_rejected", c5c[0] == 400 and c5c[1].get("error") == "e2ee_header_too_long", c5c))

        # 5d) max-size headerId boundary (128 chars) must not be rejected as too long
        c5d = post(url, token, {"sessionId": "smoke", "e2ee": {"ciphertext": "x", "headerId": "h" * 128, "counter": 1, "iv": valid_iv_12, "salt": valid_salt_16, "ephemeralPub": valid_ephemeral_pub}})
        cases.append(("max_header_boundary_accepted", c5d[1].get("error") not in ("e2ee_header_required", "e2ee_header_too_long"), c5d))

        # 5e) max-size headerId amb espais al voltant (trim) també ha de quedar acceptat
        c5e = post(url, token, {"sessionId": "smoke", "e2ee": {"ciphertext": "x", "headerId": "  " + ("h" * 128) + "  ", "counter": 1, "iv": valid_iv_12, "salt": valid_salt_16, "ephemeralPub": valid_ephemeral_pub}})
        cases.append(("max_header_trimmed_boundary_accepted", c5e[1].get("error") not in ("e2ee_header_required", "e2ee_header_too_long"), c5e))

        # 6) encrypted envelope missing positive counter
        c6 = post(url, token, {"sessionId": "smoke", "e2ee": {"ciphertext": "x", "headerId": "h-1"}})
        cases.append(("missing_counter", c6[0] == 400 and c6[1].get("error") == "e2ee_counter_required", c6))

        # 7) encrypted envelope with non-integer counter
        c6 = post(url, token, {"sessionId": "smoke", "e2ee": {"ciphertext": "x", "headerId": "h-1", "counter": "abc"}})
        cases.append(("invalid_counter_type", c6[0] == 400 and c6[1].get("error") == "e2ee_counter_required", c6))

        # 7b) encrypted envelope with null counter (must be rejected)
        c6b = post(url, token, {"sessionId": "smoke", "e2ee": {"ciphertext": "x", "headerId": "h-1", "counter": None}})
        cases.append(("null_counter_rejected", c6b[0] == 400 and c6b[1].get("error") == "e2ee_counter_required", c6b))

        # 8) encrypted envelope with numeric-string counter (must be rejected in strict mode)
        c7 = post(url, token, {"sessionId": "smoke", "e2ee": {"ciphertext": "x", "headerId": "h-1", "counter": "1"}})
        cases.append(("string_counter_rejected", c7[0] == 400 and c7[1].get("error") == "e2ee_counter_required", c7))

        # 8a) encrypted envelope with whitespace numeric-string counter (must also be rejected)
        c7a = post(url, token, {"sessionId": "smoke", "e2ee": {"ciphertext": "x", "headerId": "h-1", "counter": " 1 "}})
        cases.append(("string_spaced_counter_rejected", c7a[0] == 400 and c7a[1].get("error") == "e2ee_counter_required", c7a))

        # 8a2) encrypted envelope with plus-prefixed numeric-string counter (must also be rejected)
        c7a2 = post(url, token, {"sessionId": "smoke", "e2ee": {"ciphertext": "x", "headerId": "h-1", "counter": "+1"}})
        cases.append(("string_plus_counter_rejected", c7a2[0] == 400 and c7a2[1].get("error") == "e2ee_counter_required", c7a2))

        # 8a3) encrypted envelope with leading-zero numeric-string counter (must also be rejected)
        c7a3 = post(url, token, {"sessionId": "smoke", "e2ee": {"ciphertext": "x", "headerId": "h-1", "counter": "01"}})
        cases.append(("string_leading_zero_counter_rejected", c7a3[0] == 400 and c7a3[1].get("error") == "e2ee_counter_required", c7a3))

        # 8a4) encrypted envelope with scientific-notation numeric-string counter (must also be rejected)
        c7a4 = post(url, token, {"sessionId": "smoke", "e2ee": {"ciphertext": "x", "headerId": "h-1", "counter": "1e2"}})
        cases.append(("string_scientific_counter_rejected", c7a4[0] == 400 and c7a4[1].get("error") == "e2ee_counter_required", c7a4))

        # 8a5) encrypted envelope with hex-like numeric-string counter (must also be rejected)
        c7a5 = post(url, token, {"sessionId": "smoke", "e2ee": {"ciphertext": "x", "headerId": "h-1", "counter": "0x10"}})
        cases.append(("string_hex_counter_rejected", c7a5[0] == 400 and c7a5[1].get("error") == "e2ee_counter_required", c7a5))

        # 8a6) encrypted envelope with underscore-formatted numeric-string counter (must also be rejected)
        c7a6 = post(url, token, {"sessionId": "smoke", "e2ee": {"ciphertext": "x", "headerId": "h-1", "counter": "1_0"}})
        cases.append(("string_underscore_counter_rejected", c7a6[0] == 400 and c7a6[1].get("error") == "e2ee_counter_required", c7a6))

        # 8a7) encrypted envelope with internal-space numeric-string counter (must also be rejected)
        c7a7 = post(url, token, {"sessionId": "smoke", "e2ee": {"ciphertext": "x", "headerId": "h-1", "counter": "1 0"}})
        cases.append(("string_internal_space_counter_rejected", c7a7[0] == 400 and c7a7[1].get("error") == "e2ee_counter_required", c7a7))

        # 8a8) encrypted envelope with internal-tab numeric-string counter (must also be rejected)
        c7a8 = post(url, token, {"sessionId": "smoke", "e2ee": {"ciphertext": "x", "headerId": "h-1", "counter": "1\t0"}})
        cases.append(("string_internal_tab_counter_rejected", c7a8[0] == 400 and c7a8[1].get("error") == "e2ee_counter_required", c7a8))

        # 8a9) encrypted envelope with internal-carriage-return numeric-string counter (must also be rejected)
        c7a9 = post(url, token, {"sessionId": "smoke", "e2ee": {"ciphertext": "x", "headerId": "h-1", "counter": "1\r0"}})
        cases.append(("string_internal_cr_counter_rejected", c7a9[0] == 400 and c7a9[1].get("error") == "e2ee_counter_required", c7a9))

        # 8a10) encrypted envelope with internal-newline numeric-string counter (must also be rejected)
        c7a10 = post(url, token, {"sessionId": "smoke", "e2ee": {"ciphertext": "x", "headerId": "h-1", "counter": "1\n0"}})
        cases.append(("string_internal_lf_counter_rejected", c7a10[0] == 400 and c7a10[1].get("error") == "e2ee_counter_required", c7a10))

        # 8a11) encrypted envelope with internal-form-feed numeric-string counter (must also be rejected)
        c7a11 = post(url, token, {"sessionId": "smoke", "e2ee": {"ciphertext": "x", "headerId": "h-1", "counter": "1\f0"}})
        cases.append(("string_internal_ff_counter_rejected", c7a11[0] == 400 and c7a11[1].get("error") == "e2ee_counter_required", c7a11))

        # 8a12) encrypted envelope with internal-vertical-tab numeric-string counter (must also be rejected)
        c7a12 = post(url, token, {"sessionId": "smoke", "e2ee": {"ciphertext": "x", "headerId": "h-1", "counter": "1\v0"}})
        cases.append(("string_internal_vtab_counter_rejected", c7a12[0] == 400 and c7a12[1].get("error") == "e2ee_counter_required", c7a12))

        # 8a13) encrypted envelope with internal-nbsp numeric-string counter (must also be rejected)
        c7a13 = post(url, token, {"sessionId": "smoke", "e2ee": {"ciphertext": "x", "headerId": "h-1", "counter": "1\u00A00"}})
        cases.append(("string_internal_nbsp_counter_rejected", c7a13[0] == 400 and c7a13[1].get("error") == "e2ee_counter_required", c7a13))

        # 8a14) encrypted envelope with internal-thin-space numeric-string counter (must also be rejected)
        c7a14 = post(url, token, {"sessionId": "smoke", "e2ee": {"ciphertext": "x", "headerId": "h-1", "counter": "1\u20090"}})
        cases.append(("string_internal_thin_space_counter_rejected", c7a14[0] == 400 and c7a14[1].get("error") == "e2ee_counter_required", c7a14))

        # 8a15) encrypted envelope with internal-narrow-no-break-space numeric-string counter (must also be rejected)
        c7a15 = post(url, token, {"sessionId": "smoke", "e2ee": {"ciphertext": "x", "headerId": "h-1", "counter": "1\u202F0"}})
        cases.append(("string_internal_nnbsp_counter_rejected", c7a15[0] == 400 and c7a15[1].get("error") == "e2ee_counter_required", c7a15))

        # 8a16) encrypted envelope with internal-punctuation-space numeric-string counter (must also be rejected)
        c7a16 = post(url, token, {"sessionId": "smoke", "e2ee": {"ciphertext": "x", "headerId": "h-1", "counter": "1\u20080"}})
        cases.append(("string_internal_punctuation_space_counter_rejected", c7a16[0] == 400 and c7a16[1].get("error") == "e2ee_counter_required", c7a16))

        # 8a17) encrypted envelope with internal-figure-space numeric-string counter (must also be rejected)
        c7a17 = post(url, token, {"sessionId": "smoke", "e2ee": {"ciphertext": "x", "headerId": "h-1", "counter": "1\u20070"}})
        cases.append(("string_internal_figure_space_counter_rejected", c7a17[0] == 400 and c7a17[1].get("error") == "e2ee_counter_required", c7a17))

        # 8a18) encrypted envelope with internal-hair-space numeric-string counter (must also be rejected)
        c7a18 = post(url, token, {"sessionId": "smoke", "e2ee": {"ciphertext": "x", "headerId": "h-1", "counter": "1\u200A0"}})
        cases.append(("string_internal_hair_space_counter_rejected", c7a18[0] == 400 and c7a18[1].get("error") == "e2ee_counter_required", c7a18))

        # 8a19) encrypted envelope with internal-medium-mathematical-space numeric-string counter (must also be rejected)
        c7a19 = post(url, token, {"sessionId": "smoke", "e2ee": {"ciphertext": "x", "headerId": "h-1", "counter": "1\u205F0"}})
        cases.append(("string_internal_medium_math_space_counter_rejected", c7a19[0] == 400 and c7a19[1].get("error") == "e2ee_counter_required", c7a19))

        # 8a20) encrypted envelope with internal-ideographic-space numeric-string counter (must also be rejected)
        c7a20 = post(url, token, {"sessionId": "smoke", "e2ee": {"ciphertext": "x", "headerId": "h-1", "counter": "1\u30000"}})
        cases.append(("string_internal_ideographic_space_counter_rejected", c7a20[0] == 400 and c7a20[1].get("error") == "e2ee_counter_required", c7a20))

        # 8a21) encrypted envelope with internal-ogham-space-mark numeric-string counter (must also be rejected)
        c7a21 = post(url, token, {"sessionId": "smoke", "e2ee": {"ciphertext": "x", "headerId": "h-1", "counter": "1\u16800"}})
        cases.append(("string_internal_ogham_space_mark_counter_rejected", c7a21[0] == 400 and c7a21[1].get("error") == "e2ee_counter_required", c7a21))

        # 8a22) encrypted envelope with internal-six-per-em-space numeric-string counter (must also be rejected)
        c7a22 = post(url, token, {"sessionId": "smoke", "e2ee": {"ciphertext": "x", "headerId": "h-1", "counter": "1\u20060"}})
        cases.append(("string_internal_six_per_em_space_counter_rejected", c7a22[0] == 400 and c7a22[1].get("error") == "e2ee_counter_required", c7a22))

        # 8a23) encrypted envelope with internal-four-per-em-space numeric-string counter (must also be rejected)
        c7a23 = post(url, token, {"sessionId": "smoke", "e2ee": {"ciphertext": "x", "headerId": "h-1", "counter": "1\u20050"}})
        cases.append(("string_internal_four_per_em_space_counter_rejected", c7a23[0] == 400 and c7a23[1].get("error") == "e2ee_counter_required", c7a23))

        # 8a24) encrypted envelope with internal-three-per-em-space numeric-string counter (must also be rejected)
        c7a24 = post(url, token, {"sessionId": "smoke", "e2ee": {"ciphertext": "x", "headerId": "h-1", "counter": "1\u20040"}})
        cases.append(("string_internal_three_per_em_space_counter_rejected", c7a24[0] == 400 and c7a24[1].get("error") == "e2ee_counter_required", c7a24))

        # 8a25) encrypted envelope with internal-en-space numeric-string counter (must also be rejected)
        c7a25 = post(url, token, {"sessionId": "smoke", "e2ee": {"ciphertext": "x", "headerId": "h-1", "counter": "1\u20020"}})
        cases.append(("string_internal_en_space_counter_rejected", c7a25[0] == 400 and c7a25[1].get("error") == "e2ee_counter_required", c7a25))

        # 8a26) encrypted envelope with internal-em-space numeric-string counter (must also be rejected)
        c7a26 = post(url, token, {"sessionId": "smoke", "e2ee": {"ciphertext": "x", "headerId": "h-1", "counter": "1\u20030"}})
        cases.append(("string_internal_em_space_counter_rejected", c7a26[0] == 400 and c7a26[1].get("error") == "e2ee_counter_required", c7a26))

        # 8a27) encrypted envelope with internal-em-quad-space numeric-string counter (must also be rejected)
        c7a27 = post(url, token, {"sessionId": "smoke", "e2ee": {"ciphertext": "x", "headerId": "h-1", "counter": "1\u20010"}})
        cases.append(("string_internal_em_quad_space_counter_rejected", c7a27[0] == 400 and c7a27[1].get("error") == "e2ee_counter_required", c7a27))

        # 8a28) encrypted envelope with internal-en-quad-space numeric-string counter (must also be rejected)
        c7a28 = post(url, token, {"sessionId": "smoke", "e2ee": {"ciphertext": "x", "headerId": "h-1", "counter": "1\u20000"}})
        cases.append(("string_internal_en_quad_space_counter_rejected", c7a28[0] == 400 and c7a28[1].get("error") == "e2ee_counter_required", c7a28))

        # 8a29) encrypted envelope with internal-zero-width-space numeric-string counter (must also be rejected)
        c7a29 = post(url, token, {"sessionId": "smoke", "e2ee": {"ciphertext": "x", "headerId": "h-1", "counter": "1\u200B0"}})
        cases.append(("string_internal_zero_width_space_counter_rejected", c7a29[0] == 400 and c7a29[1].get("error") == "e2ee_counter_required", c7a29))

        # 8a30) encrypted envelope with internal-zero-width-non-joiner numeric-string counter (must also be rejected)
        c7a30 = post(url, token, {"sessionId": "smoke", "e2ee": {"ciphertext": "x", "headerId": "h-1", "counter": "1\u200C0"}})
        cases.append(("string_internal_zero_width_non_joiner_counter_rejected", c7a30[0] == 400 and c7a30[1].get("error") == "e2ee_counter_required", c7a30))

        # 8a31) encrypted envelope with internal-zero-width-joiner numeric-string counter (must also be rejected)
        c7a31 = post(url, token, {"sessionId": "smoke", "e2ee": {"ciphertext": "x", "headerId": "h-1", "counter": "1\u200D0"}})
        cases.append(("string_internal_zero_width_joiner_counter_rejected", c7a31[0] == 400 and c7a31[1].get("error") == "e2ee_counter_required", c7a31))

        # 8a32) encrypted envelope with internal-word-joiner numeric-string counter (must also be rejected)
        c7a32 = post(url, token, {"sessionId": "smoke", "e2ee": {"ciphertext": "x", "headerId": "h-1", "counter": "1\u20600"}})
        cases.append(("string_internal_word_joiner_counter_rejected", c7a32[0] == 400 and c7a32[1].get("error") == "e2ee_counter_required", c7a32))

        # 8a33) encrypted envelope with internal-word-joiner-like invisible-separator numeric-string counter (must also be rejected)
        c7a33 = post(url, token, {"sessionId": "smoke", "e2ee": {"ciphertext": "x", "headerId": "h-1", "counter": "1\u20630"}})
        cases.append(("string_internal_invisible_separator_counter_rejected", c7a33[0] == 400 and c7a33[1].get("error") == "e2ee_counter_required", c7a33))

        # 8a34) encrypted envelope with internal-zero-width-no-break-space (BOM) numeric-string counter (must also be rejected)
        c7a34 = post(url, token, {"sessionId": "smoke", "e2ee": {"ciphertext": "x", "headerId": "h-1", "counter": "1\uFEFF0"}})
        cases.append(("string_internal_zero_width_nbsp_counter_rejected", c7a34[0] == 400 and c7a34[1].get("error") == "e2ee_counter_required", c7a34))

        # 8a35) encrypted envelope with internal-invisible-plus numeric-string counter (must also be rejected)
        c7a35 = post(url, token, {"sessionId": "smoke", "e2ee": {"ciphertext": "x", "headerId": "h-1", "counter": "1\u20640"}})
        cases.append(("string_internal_invisible_plus_counter_rejected", c7a35[0] == 400 and c7a35[1].get("error") == "e2ee_counter_required", c7a35))

        # 8) encrypted envelope with bool counter (bool is int subclass in Python, must still be rejected)
        c8 = post(url, token, {"sessionId": "smoke", "e2ee": {"ciphertext": "x", "headerId": "h-1", "counter": True}})
        cases.append(("bool_counter_rejected", c8[0] == 400 and c8[1].get("error") == "e2ee_counter_required", c8))

        # 8b) encrypted envelope with bool(false) counter must also be rejected
        c8b = post(url, token, {"sessionId": "smoke", "e2ee": {"ciphertext": "x", "headerId": "h-1", "counter": False}})
        cases.append(("bool_false_counter_rejected", c8b[0] == 400 and c8b[1].get("error") == "e2ee_counter_required", c8b))

        # 9) encrypted envelope with zero counter (must be positive)
        c9 = post(url, token, {"sessionId": "smoke", "e2ee": {"ciphertext": "x", "headerId": "h-1", "counter": 0}})
        cases.append(("zero_counter_rejected", c9[0] == 400 and c9[1].get("error") == "e2ee_counter_required", c9))

        # 10) encrypted envelope with negative counter (must be positive)
        c10 = post(url, token, {"sessionId": "smoke", "e2ee": {"ciphertext": "x", "headerId": "h-1", "counter": -1}})
        cases.append(("negative_counter_rejected", c10[0] == 400 and c10[1].get("error") == "e2ee_counter_required", c10))

        # 11) encrypted envelope with float counter (must be integer)
        c11 = post(url, token, {"sessionId": "smoke", "e2ee": {"ciphertext": "x", "headerId": "h-1", "counter": 1.5}})
        cases.append(("float_counter_rejected", c11[0] == 400 and c11[1].get("error") == "e2ee_counter_required", c11))

        # 11b) encrypted envelope with oversized counter (must be bounded)
        c11b = post(url, token, {"sessionId": "smoke", "e2ee": {"ciphertext": "x", "headerId": "h-1", "counter": 2147483648}})
        cases.append(("oversized_counter_rejected", c11b[0] == 400 and c11b[1].get("error") == "e2ee_counter_out_of_range", c11b))

        # 11c) minimum positive counter boundary (1) must not be rejected by counter guards
        c11c = post(url, token, {"sessionId": "smoke", "e2ee": {"ciphertext": "x", "headerId": "h-1", "counter": 1, "iv": valid_iv_12, "salt": valid_salt_16, "ephemeralPub": valid_ephemeral_pub}})
        cases.append(("min_counter_boundary_accepted", c11c[1].get("error") not in ("e2ee_counter_required", "e2ee_counter_out_of_range"), c11c))

        # 12) encrypted envelope missing iv
        c12 = post(url, token, {"sessionId": "smoke", "e2ee": {"ciphertext": "x", "headerId": "h-1", "counter": 1, "salt": "c2FsdA==", "ephemeralPub": "eA=="}})
        cases.append(("missing_iv", c12[0] == 400 and c12[1].get("error") == "e2ee_iv_required", c12))

        # 12b) encrypted envelope with blank iv
        c12b = post(url, token, {"sessionId": "smoke", "e2ee": {"ciphertext": "x", "headerId": "h-1", "counter": 1, "iv": "   ", "salt": "c2FsdA==", "ephemeralPub": "eA=="}})
        cases.append(("blank_iv", c12b[0] == 400 and c12b[1].get("error") == "e2ee_iv_required", c12b))

        # 12c) encrypted envelope with null iv (must be rejected)
        c12c = post(url, token, {"sessionId": "smoke", "e2ee": {"ciphertext": "x", "headerId": "h-1", "counter": 1, "iv": None, "salt": "c2FsdA==", "ephemeralPub": "eA=="}})
        cases.append(("null_iv_rejected", c12c[0] == 400 and c12c[1].get("error") == "e2ee_iv_required", c12c))

        # 12d) encrypted envelope with invalid iv type
        c12d = post(url, token, {"sessionId": "smoke", "e2ee": {"ciphertext": "x", "headerId": "h-1", "counter": 1, "iv": 123, "salt": "c2FsdA==", "ephemeralPub": "eA=="}})
        cases.append(("invalid_iv_type", c12d[0] == 400 and c12d[1].get("error") == "e2ee_iv_required", c12d))

        # 13) encrypted envelope missing salt
        c13 = post(url, token, {"sessionId": "smoke", "e2ee": {"ciphertext": "x", "headerId": "h-1", "counter": 1, "iv": "aXY=", "ephemeralPub": "eA=="}})
        cases.append(("missing_salt", c13[0] == 400 and c13[1].get("error") == "e2ee_salt_required", c13))

        # 13b) encrypted envelope with blank salt
        c13b = post(url, token, {"sessionId": "smoke", "e2ee": {"ciphertext": "x", "headerId": "h-1", "counter": 1, "iv": "aXY=", "salt": "   ", "ephemeralPub": "eA=="}})
        cases.append(("blank_salt", c13b[0] == 400 and c13b[1].get("error") == "e2ee_salt_required", c13b))

        # 13c) encrypted envelope with invalid salt type
        c13c = post(url, token, {"sessionId": "smoke", "e2ee": {"ciphertext": "x", "headerId": "h-1", "counter": 1, "iv": "aXY=", "salt": 123, "ephemeralPub": "eA=="}})
        cases.append(("invalid_salt_type", c13c[0] == 400 and c13c[1].get("error") == "e2ee_salt_required", c13c))

        # 13d) encrypted envelope with null salt (must be rejected)
        c13d = post(url, token, {"sessionId": "smoke", "e2ee": {"ciphertext": "x", "headerId": "h-1", "counter": 1, "iv": "aXY=", "salt": None, "ephemeralPub": "eA=="}})
        cases.append(("null_salt_rejected", c13d[0] == 400 and c13d[1].get("error") == "e2ee_salt_required", c13d))

        # 14) encrypted envelope missing ephemeralPub
        c14 = post(url, token, {"sessionId": "smoke", "e2ee": {"ciphertext": "x", "headerId": "h-1", "counter": 1, "iv": "aXY=", "salt": "c2FsdA=="}})
        cases.append(("missing_ephemeral_pub", c14[0] == 400 and c14[1].get("error") == "e2ee_ephemeral_required", c14))

        # 14b) encrypted envelope with blank ephemeralPub
        c14b = post(url, token, {"sessionId": "smoke", "e2ee": {"ciphertext": "x", "headerId": "h-1", "counter": 1, "iv": "aXY=", "salt": "c2FsdA==", "ephemeralPub": "   "}})
        cases.append(("blank_ephemeral_pub", c14b[0] == 400 and c14b[1].get("error") == "e2ee_ephemeral_required", c14b))

        # 14c) encrypted envelope with invalid ephemeralPub type
        c14c = post(url, token, {"sessionId": "smoke", "e2ee": {"ciphertext": "x", "headerId": "h-1", "counter": 1, "iv": "aXY=", "salt": "c2FsdA==", "ephemeralPub": 123}})
        cases.append(("invalid_ephemeral_pub_type", c14c[0] == 400 and c14c[1].get("error") == "e2ee_ephemeral_required", c14c))

        # 14d) encrypted envelope with null ephemeralPub (must be rejected)
        c14d = post(url, token, {"sessionId": "smoke", "e2ee": {"ciphertext": "x", "headerId": "h-1", "counter": 1, "iv": "aXY=", "salt": "c2FsdA==", "ephemeralPub": None}})
        cases.append(("null_ephemeral_pub_rejected", c14d[0] == 400 and c14d[1].get("error") == "e2ee_ephemeral_required", c14d))

        # 15) encrypted envelope with invalid base64 ciphertext
        c15 = post(url, token, {"sessionId": "smoke", "e2ee": {"ciphertext": "***", "headerId": "h-1", "counter": 1, "iv": valid_iv_12, "salt": valid_salt_16, "ephemeralPub": valid_ephemeral_pub}})
        cases.append(("invalid_ciphertext_base64", c15[0] == 400 and c15[1].get("error") == "e2ee_ciphertext_invalid", c15))

        # 15b) encrypted envelope with too-short decoded ciphertext (<16 bytes GCM tag)
        c15b = post(url, token, {"sessionId": "smoke", "e2ee": {"ciphertext": "eA==", "headerId": "h-1", "counter": 1, "iv": valid_iv_12, "salt": valid_salt_16, "ephemeralPub": valid_ephemeral_pub}})
        cases.append(("invalid_ciphertext_length", c15b[0] == 400 and c15b[1].get("error") == "e2ee_ciphertext_invalid", c15b))

        # 15c) encrypted envelope with oversized decoded ciphertext (>1 MiB)
        huge_ciphertext_b64 = base64.b64encode(b"A" * (1024 * 1024 + 1)).decode("ascii")
        c15c = post(url, token, {"sessionId": "smoke", "e2ee": {"ciphertext": huge_ciphertext_b64, "headerId": "h-1", "counter": 1, "iv": valid_iv_12, "salt": valid_salt_16, "ephemeralPub": valid_ephemeral_pub}})
        cases.append(("oversized_ciphertext_rejected", c15c[0] == 400 and c15c[1].get("error") == "e2ee_ciphertext_too_large", c15c))

        # 15c2) max-size decoded ciphertext boundary (exactly 1 MiB) must not be rejected as too large
        max_ciphertext_b64 = base64.b64encode(b"A" * (1024 * 1024)).decode("ascii")
        c15c2 = post(url, token, {"sessionId": "smoke", "e2ee": {"ciphertext": max_ciphertext_b64, "headerId": "h-1", "counter": 1, "iv": valid_iv_12, "salt": valid_salt_16, "ephemeralPub": valid_ephemeral_pub}})
        cases.append(("max_ciphertext_boundary_accepted", c15c2[1].get("error") != "e2ee_ciphertext_too_large", c15c2))

        # 15d) encrypted envelope with oversized raw ciphertext base64 input (pre-decode guard)
        huge_ciphertext_raw = "A" * 1_500_001
        c15d = post(url, token, {"sessionId": "smoke", "e2ee": {"ciphertext": huge_ciphertext_raw, "headerId": "h-1", "counter": 1, "iv": valid_iv_12, "salt": valid_salt_16, "ephemeralPub": valid_ephemeral_pub}})
        cases.append(("oversized_ciphertext_raw_rejected", c15d[0] == 400 and c15d[1].get("error") == "e2ee_ciphertext_too_large", c15d))

        # 15d2) raw ciphertext just below guard boundary (1_499_999 chars) should not be rejected as too large
        near_max_ciphertext_raw = "A" * 1_499_999
        c15d1 = post(url, token, {"sessionId": "smoke", "e2ee": {"ciphertext": near_max_ciphertext_raw, "headerId": "h-1", "counter": 1, "iv": valid_iv_12, "salt": valid_salt_16, "ephemeralPub": valid_ephemeral_pub}})
        cases.append(("near_max_ciphertext_raw_boundary_accepted", c15d1[1].get("error") != "e2ee_ciphertext_too_large", c15d1))

        # 15d3) raw ciphertext at guard boundary (1_500_000 chars) is currently rejected
        #       Keep this explicit to freeze behavior and detect accidental guard shifts.
        max_ciphertext_raw = "A" * 1_500_000
        c15d2 = post(url, token, {"sessionId": "smoke", "e2ee": {"ciphertext": max_ciphertext_raw, "headerId": "h-1", "counter": 1, "iv": valid_iv_12, "salt": valid_salt_16, "ephemeralPub": valid_ephemeral_pub}})
        cases.append(("max_ciphertext_raw_boundary_rejected", c15d2[0] == 400 and c15d2[1].get("error") == "e2ee_ciphertext_too_large", c15d2))

        # 16) encrypted envelope with invalid base64 iv
        c16 = post(url, token, {"sessionId": "smoke", "e2ee": {"ciphertext": "QUFBQUFBQUFBQUFBQUFBQQ==", "headerId": "h-1", "counter": 1, "iv": "***", "salt": "c2FsdA==", "ephemeralPub": "eA=="}})
        cases.append(("invalid_iv_base64", c16[0] == 400 and c16[1].get("error") == "e2ee_iv_invalid", c16))

        # 16b) encrypted envelope with wrong iv length (must be 12 bytes decoded)
        c16b = post(url, token, {"sessionId": "smoke", "e2ee": {"ciphertext": "QUFBQUFBQUFBQUFBQUFBQQ==", "headerId": "h-1", "counter": 1, "iv": "aXY=", "salt": "c2FsdA==", "ephemeralPub": "eA=="}})
        cases.append(("invalid_iv_length", c16b[0] == 400 and c16b[1].get("error") == "e2ee_iv_invalid", c16b))

        # 16c) encrypted envelope with oversized iv raw input
        c16c = post(url, token, {"sessionId": "smoke", "e2ee": {"ciphertext": "QUFBQUFBQUFBQUFBQUFBQQ==", "headerId": "h-1", "counter": 1, "iv": "A" * 129, "salt": "c2FsdA==", "ephemeralPub": "eA=="}})
        cases.append(("oversized_iv_raw_rejected", c16c[0] == 400 and c16c[1].get("error") == "e2ee_iv_invalid", c16c))

        # 16d) max iv raw length boundary (128 chars) must not trigger raw-size rejection
        c16d = post(url, token, {"sessionId": "smoke", "e2ee": {"ciphertext": "QUFBQUFBQUFBQUFBQUFBQQ==", "headerId": "h-1", "counter": 1, "iv": "A" * 128, "salt": "c2FsdA==", "ephemeralPub": "eA=="}})
        cases.append(("max_iv_raw_boundary_accepted", c16d[1].get("message") != "Encrypted envelope iv is too large.", c16d))

        # 17) encrypted envelope with invalid base64 salt
        c17 = post(url, token, {"sessionId": "smoke", "e2ee": {"ciphertext": "QUFBQUFBQUFBQUFBQUFBQQ==", "headerId": "h-1", "counter": 1, "iv": valid_iv_12, "salt": "***", "ephemeralPub": valid_ephemeral_pub}})
        cases.append(("invalid_salt_base64", c17[0] == 400 and c17[1].get("error") == "e2ee_salt_invalid", c17))

        # 17b) encrypted envelope with wrong salt length (must be 16 bytes decoded)
        c17b = post(url, token, {"sessionId": "smoke", "e2ee": {"ciphertext": "QUFBQUFBQUFBQUFBQUFBQQ==", "headerId": "h-1", "counter": 1, "iv": "YWJjZGVmZ2hpamts", "salt": "aXY=", "ephemeralPub": "eA=="}})
        cases.append(("invalid_salt_length", c17b[0] == 400 and c17b[1].get("error") == "e2ee_salt_invalid", c17b))

        # 17c) encrypted envelope with oversized salt raw input
        c17c = post(url, token, {"sessionId": "smoke", "e2ee": {"ciphertext": "QUFBQUFBQUFBQUFBQUFBQQ==", "headerId": "h-1", "counter": 1, "iv": valid_iv_12, "salt": "A" * 129, "ephemeralPub": "eA=="}})
        cases.append(("oversized_salt_raw_rejected", c17c[0] == 400 and c17c[1].get("error") == "e2ee_salt_invalid", c17c))

        # 17d) max salt raw length boundary (128 chars) must not trigger raw-size rejection
        c17d = post(url, token, {"sessionId": "smoke", "e2ee": {"ciphertext": "QUFBQUFBQUFBQUFBQUFBQQ==", "headerId": "h-1", "counter": 1, "iv": valid_iv_12, "salt": "A" * 128, "ephemeralPub": "eA=="}})
        cases.append(("max_salt_raw_boundary_accepted", c17d[1].get("message") != "Encrypted envelope salt is too large.", c17d))

        # 18) encrypted envelope with invalid base64 ephemeralPub
        c18 = post(url, token, {"sessionId": "smoke", "e2ee": {"ciphertext": "QUFBQUFBQUFBQUFBQUFBQQ==", "headerId": "h-1", "counter": 1, "iv": valid_iv_12, "salt": valid_salt_16, "ephemeralPub": "***"}})
        cases.append(("invalid_ephemeral_pub_base64", c18[0] == 400 and c18[1].get("error") == "e2ee_ephemeral_invalid", c18))

        # 18b) encrypted envelope with wrong-length ephemeralPub (must be 32 bytes decoded)
        c18b = post(url, token, {"sessionId": "smoke", "e2ee": {"ciphertext": "QUFBQUFBQUFBQUFBQUFBQQ==", "headerId": "h-1", "counter": 1, "iv": valid_iv_12, "salt": valid_salt_16, "ephemeralPub": "eA=="}})
        cases.append(("invalid_ephemeral_pub_length", c18b[0] == 400 and c18b[1].get("error") == "e2ee_ephemeral_invalid", c18b))

        # 18c) encrypted envelope with oversized ephemeralPub raw input
        c18c = post(url, token, {"sessionId": "smoke", "e2ee": {"ciphertext": "QUFBQUFBQUFBQUFBQUFBQQ==", "headerId": "h-1", "counter": 1, "iv": valid_iv_12, "salt": valid_salt_16, "ephemeralPub": "A" * 257}})
        cases.append(("oversized_ephemeral_pub_raw_rejected", c18c[0] == 400 and c18c[1].get("error") == "e2ee_ephemeral_invalid", c18c))

        # 18c2) max ephemeralPub raw length boundary (256 chars) must not trigger raw-size rejection
        c18c2 = post(url, token, {"sessionId": "smoke", "e2ee": {"ciphertext": "QUFBQUFBQUFBQUFBQUFBQQ==", "headerId": "h-1", "counter": 1, "iv": valid_iv_12, "salt": valid_salt_16, "ephemeralPub": "A" * 256}})
        cases.append(("max_ephemeral_pub_raw_boundary_accepted", c18c2[1].get("message") != "Encrypted envelope ephemeralPub is too large.", c18c2))

        # 18d) max allowed counter should pass strict range validation (not rejected as out-of-range)
        c18d = post(
            url,
            token,
            {
                "sessionId": "smoke",
                "e2ee": {
                    "ciphertext": "QUFBQUFBQUFBQUFBQUFBQQ==",
                    "headerId": "h-max",
                    "counter": 2147483647,
                    "iv": valid_iv_12,
                    "salt": valid_salt_16,
                    "ephemeralPub": valid_ephemeral_pub,
                },
            },
        )
        cases.append((
            "max_counter_boundary_accepted",
            c18d[1].get("error") not in ("e2ee_counter_required", "e2ee_counter_out_of_range"),
            c18d,
        ))

        # 19) clear attachment without e2eeAttachment
        c19 = post(
            url,
            token,
            {
                "sessionId": "smoke",
                "e2ee": {"ciphertext": "x", "headerId": "h-1", "counter": 1, "iv": valid_iv_12, "salt": valid_salt_16, "ephemeralPub": valid_ephemeral_pub},
                "attachment": {"name": "a.txt", "mime": "text/plain", "dataBase64": "YQ=="},
            },
        )
        cases.append(("clear_attachment", c19[0] == 400 and c19[1].get("error") == "e2ee_attachment_required", c19))

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


if __name__ == "__main__":
    main()
