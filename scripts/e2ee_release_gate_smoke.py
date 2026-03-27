#!/usr/bin/env python3
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path


def run(cmd):
    p = subprocess.run(cmd, capture_output=True, text=True)
    return {
        "cmd": " ".join(cmd),
        "exit": p.returncode,
        "stdout": p.stdout.strip(),
        "stderr": p.stderr.strip(),
    }


def _strict_mode_cases_meta(stdout):
    try:
        payload = json.loads(stdout or "{}")
    except Exception:
        return None, None, None
    cases = payload.get("cases")
    if not isinstance(cases, list):
        return None, None, None
    names = [c.get("name") for c in cases if isinstance(c, dict)]
    if len(names) != len(cases):
        return len(cases), None, None
    unique_names = len(set(names))
    return len(cases), unique_names, names


def _full_matrix_meta(stdout):
    try:
        payload = json.loads(stdout or "{}")
    except Exception:
        return None, None, None
    results = payload.get("results")
    if not isinstance(results, list):
        return None, None, None
    scripts = [r.get("script") for r in results if isinstance(r, dict)]
    if len(scripts) != len(results):
        return len(results), None, None
    unique_scripts = len(set(scripts))
    return len(results), unique_scripts, scripts


REQUIRED_FULL_MATRIX_SCRIPTS_ORDERED = [
    "e2ee_headerid_smoke.py",
    "e2ee_seed_progress_smoke.py",
    "e2ee_strict_mode_smoke.py",
    "e2ee_attachment_smoke.py",
    "e2ee_dh_step_smoke.py",
    "e2ee_state_lifecycle_smoke.py",
    "e2ee_skipped_cache_lifecycle_smoke.py",
    "e2ee_window_eviction_smoke.py",
    "e2ee_large_gap_window_cap_smoke.py",
    "e2ee_large_gap_header_scope_smoke.py",
    "e2ee_failed_decrypt_no_drift_smoke.py",
    "e2ee_failed_decrypt_replay_slot_smoke.py",
    "e2ee_failed_decrypt_dh_step_rollback_smoke.py",
    "e2ee_dh_step_failed_then_success_smoke.py",
    "e2ee_failed_decrypt_same_counter_success_smoke.py",
    "e2ee_failed_decrypt_next_counter_smoke.py",
    "e2ee_failed_decrypt_next_counter_dh_step_smoke.py",
    "e2ee_failed_decrypt_next_counter_dh_step_header_norm_smoke.py",
    "e2ee_header_normalization_smoke.py",
]
REQUIRED_FULL_MATRIX_SCRIPTS = set(REQUIRED_FULL_MATRIX_SCRIPTS_ORDERED)

REQUIRED_STRICT_CASE_NAMES_ORDERED = [
    "missing_e2ee",
    "null_e2ee_rejected",
    "invalid_e2ee_type",
    "bool_e2ee_rejected",
    "bool_false_e2ee_rejected",
    "string_e2ee_rejected",
    "number_e2ee_rejected",
    "float_e2ee_rejected",
    "blank_string_e2ee_rejected",
    "missing_ciphertext",
    "blank_ciphertext",
    "invalid_ciphertext_type",
    "null_ciphertext_rejected",
    "missing_header",
    "invalid_header_type",
    "null_header_rejected",
    "blank_header",
    "oversized_header_rejected",
    "oversized_header_trimmed_rejected",
    "max_header_boundary_accepted",
    "max_header_trimmed_boundary_accepted",
    "missing_counter",
    "invalid_counter_type",
    "null_counter_rejected",
    "string_counter_rejected",
    "string_spaced_counter_rejected",
    "string_plus_counter_rejected",
    "string_leading_zero_counter_rejected",
    "string_scientific_counter_rejected",
    "string_hex_counter_rejected",
    "string_underscore_counter_rejected",
    "string_internal_space_counter_rejected",
    "string_internal_tab_counter_rejected",
    "string_internal_cr_counter_rejected",
    "string_internal_lf_counter_rejected",
    "string_internal_ff_counter_rejected",
    "string_internal_vtab_counter_rejected",
    "string_internal_nbsp_counter_rejected",
    "string_internal_thin_space_counter_rejected",
    "string_internal_nnbsp_counter_rejected",
    "string_internal_punctuation_space_counter_rejected",
    "string_internal_figure_space_counter_rejected",
    "string_internal_hair_space_counter_rejected",
    "string_internal_medium_math_space_counter_rejected",
    "string_internal_ideographic_space_counter_rejected",
    "string_internal_ogham_space_mark_counter_rejected",
    "string_internal_six_per_em_space_counter_rejected",
    "string_internal_four_per_em_space_counter_rejected",
    "string_internal_three_per_em_space_counter_rejected",
    "string_internal_en_space_counter_rejected",
    "string_internal_em_space_counter_rejected",
    "string_internal_em_quad_space_counter_rejected",
    "string_internal_en_quad_space_counter_rejected",
    "string_internal_zero_width_space_counter_rejected",
    "string_internal_zero_width_non_joiner_counter_rejected",
    "string_internal_zero_width_joiner_counter_rejected",
    "string_internal_word_joiner_counter_rejected",
    "string_internal_invisible_separator_counter_rejected",
    "string_internal_zero_width_nbsp_counter_rejected",
    "string_internal_invisible_plus_counter_rejected",
    "bool_counter_rejected",
    "bool_false_counter_rejected",
    "zero_counter_rejected",
    "negative_counter_rejected",
    "float_counter_rejected",
    "oversized_counter_rejected",
    "min_counter_boundary_accepted",
    "missing_iv",
    "blank_iv",
    "null_iv_rejected",
    "invalid_iv_type",
    "missing_salt",
    "blank_salt",
    "invalid_salt_type",
    "null_salt_rejected",
    "missing_ephemeral_pub",
    "blank_ephemeral_pub",
    "invalid_ephemeral_pub_type",
    "null_ephemeral_pub_rejected",
    "invalid_ciphertext_base64",
    "invalid_ciphertext_length",
    "oversized_ciphertext_rejected",
    "max_ciphertext_boundary_accepted",
    "oversized_ciphertext_raw_rejected",
    "near_max_ciphertext_raw_boundary_accepted",
    "max_ciphertext_raw_boundary_rejected",
    "invalid_iv_base64",
    "invalid_iv_length",
    "oversized_iv_raw_rejected",
    "max_iv_raw_boundary_accepted",
    "invalid_salt_base64",
    "invalid_salt_length",
    "oversized_salt_raw_rejected",
    "max_salt_raw_boundary_accepted",
    "invalid_ephemeral_pub_base64",
    "invalid_ephemeral_pub_length",
    "oversized_ephemeral_pub_raw_rejected",
    "max_ephemeral_pub_raw_boundary_accepted",
    "max_counter_boundary_accepted",
    "clear_attachment",
]
REQUIRED_STRICT_CASE_NAMES = set(REQUIRED_STRICT_CASE_NAMES_ORDERED)


def main():
    started = datetime.now(timezone.utc).isoformat()
    checks = []

    def add_check(name, cmd, optional=False):
        checks.append({"name": name, "cmd": cmd, "optional": optional})

    add_check("fullMatrix", ["python3", "scripts/e2ee_full_matrix_smoke.py"])
    add_check(
        "strictModeAigor",
        ["python3", "scripts/e2ee_strict_mode_smoke.py", "scripts/aigor_chat_bridge.py", "AIGOR_APP"],
    )

    openclaw_bridge = Path("scripts/openclaw_chat_bridge.py")
    if openclaw_bridge.exists():
        add_check(
            "strictModeOpenclaw",
            ["python3", "scripts/e2ee_strict_mode_smoke.py", str(openclaw_bridge), "OPENCLAW_APP"],
        )
    else:
        add_check(
            "strictModeOpenclaw",
            ["python3", "scripts/e2ee_strict_mode_smoke.py", str(openclaw_bridge), "OPENCLAW_APP"],
            optional=True,
        )

    add_check("assembleRelease", ["./gradlew", ":app:assembleRelease"])

    executed = []
    for c in checks:
        if c["optional"]:
            executed.append(
                {
                    "name": c["name"],
                    "cmd": " ".join(c["cmd"]),
                    "exit": None,
                    "ok": True,
                    "skipped": True,
                    "reason": "bridge script not present in this repository",
                }
            )
            continue
        r = run(c["cmd"])
        check_ok = r["exit"] == 0
        strict_cases = None
        strict_unique_case_names = None
        strict_missing_required = None
        strict_unexpected_cases = None
        full_matrix_scripts = None
        full_matrix_unique_scripts = None
        full_matrix_missing_required = None
        full_matrix_unexpected_scripts = None
        if c["name"] in {"strictModeAigor", "strictModeOpenclaw"}:
            strict_cases, strict_unique_case_names, strict_case_names = _strict_mode_cases_meta(r["stdout"])
            min_strict_cases = 100
            if strict_cases is None or strict_cases < min_strict_cases:
                check_ok = False
                if not r["stderr"]:
                    r["stderr"] = f"strict-mode output missing/invalid or cases < {min_strict_cases}"
            if strict_unique_case_names is None or strict_unique_case_names != strict_cases:
                check_ok = False
                msg = "strict-mode output has non-unique or invalid case names"
                r["stderr"] = f"{r['stderr']}\n{msg}".strip() if r["stderr"] else msg
            if strict_case_names is not None:
                strict_name_set = set(strict_case_names)
                strict_missing_required = sorted(REQUIRED_STRICT_CASE_NAMES - strict_name_set)
                strict_unexpected_cases = sorted(strict_name_set - REQUIRED_STRICT_CASE_NAMES)
                if strict_missing_required:
                    check_ok = False
                    msg = f"strict-mode output missing required cases: {', '.join(strict_missing_required)}"
                    r["stderr"] = f"{r['stderr']}\n{msg}".strip() if r["stderr"] else msg
                if strict_unexpected_cases:
                    check_ok = False
                    msg = f"strict-mode output has unexpected cases: {', '.join(strict_unexpected_cases)}"
                    r["stderr"] = f"{r['stderr']}\n{msg}".strip() if r["stderr"] else msg
                if strict_case_names != REQUIRED_STRICT_CASE_NAMES_ORDERED:
                    check_ok = False
                    msg = "strict-mode output case order differs from required canonical order"
                    r["stderr"] = f"{r['stderr']}\n{msg}".strip() if r["stderr"] else msg
            else:
                strict_missing_required = None
                strict_unexpected_cases = None
        if c["name"] == "fullMatrix":
            full_matrix_scripts, full_matrix_unique_scripts, full_matrix_script_names = _full_matrix_meta(r["stdout"])
            min_full_matrix_scripts = 19
            if full_matrix_scripts is None or full_matrix_scripts < min_full_matrix_scripts:
                check_ok = False
                msg = f"full-matrix output missing/invalid or scripts < {min_full_matrix_scripts}"
                r["stderr"] = f"{r['stderr']}\n{msg}".strip() if r["stderr"] else msg
            if full_matrix_unique_scripts is None or full_matrix_unique_scripts != full_matrix_scripts:
                check_ok = False
                msg = "full-matrix output has duplicate or invalid script names"
                r["stderr"] = f"{r['stderr']}\n{msg}".strip() if r["stderr"] else msg
            if full_matrix_script_names is not None:
                full_matrix_name_set = set(full_matrix_script_names)
                full_matrix_missing_required = sorted(REQUIRED_FULL_MATRIX_SCRIPTS - full_matrix_name_set)
                full_matrix_unexpected_scripts = sorted(full_matrix_name_set - REQUIRED_FULL_MATRIX_SCRIPTS)
                if full_matrix_missing_required:
                    check_ok = False
                    msg = f"full-matrix output missing required scripts: {', '.join(full_matrix_missing_required)}"
                    r["stderr"] = f"{r['stderr']}\n{msg}".strip() if r["stderr"] else msg
                if full_matrix_unexpected_scripts:
                    check_ok = False
                    msg = f"full-matrix output has unexpected scripts: {', '.join(full_matrix_unexpected_scripts)}"
                    r["stderr"] = f"{r['stderr']}\n{msg}".strip() if r["stderr"] else msg
                if full_matrix_script_names != REQUIRED_FULL_MATRIX_SCRIPTS_ORDERED:
                    check_ok = False
                    msg = "full-matrix script order differs from required canonical order"
                    r["stderr"] = f"{r['stderr']}\n{msg}".strip() if r["stderr"] else msg

        executed.append(
            {
                "name": c["name"],
                "cmd": r["cmd"],
                "exit": r["exit"],
                "ok": check_ok,
                "skipped": False,
                "stdout": r["stdout"],
                "stderr": r["stderr"],
                **({"strictCases": strict_cases} if strict_cases is not None else {}),
                **({"strictUniqueCaseNames": strict_unique_case_names} if strict_unique_case_names is not None else {}),
                **({"strictMissingRequired": strict_missing_required} if strict_missing_required is not None else {}),
                **({"strictUnexpectedCases": strict_unexpected_cases} if strict_unexpected_cases is not None else {}),
                **({"fullMatrixScripts": full_matrix_scripts} if full_matrix_scripts is not None else {}),
                **({"fullMatrixUniqueScripts": full_matrix_unique_scripts} if full_matrix_unique_scripts is not None else {}),
                **({"fullMatrixMissingRequired": full_matrix_missing_required} if full_matrix_missing_required is not None else {}),
                **({"fullMatrixUnexpectedScripts": full_matrix_unexpected_scripts} if full_matrix_unexpected_scripts is not None else {}),
            }
        )

    ok = all(item["ok"] for item in executed)
    result = {
        "ok": ok,
        "startedAtUtc": started,
        "finishedAtUtc": datetime.now(timezone.utc).isoformat(),
        "checks": [
            {
                "name": item["name"],
                "cmd": item["cmd"],
                "exit": item["exit"],
                "ok": item["ok"],
                "skipped": item["skipped"],
                **({"reason": item["reason"]} if item.get("reason") else {}),
                **({"strictCases": item["strictCases"]} if item.get("strictCases") is not None else {}),
                **({"strictUniqueCaseNames": item["strictUniqueCaseNames"]} if item.get("strictUniqueCaseNames") is not None else {}),
                **({"strictMissingRequired": item["strictMissingRequired"]} if item.get("strictMissingRequired") is not None else {}),
                **({"strictUnexpectedCases": item["strictUnexpectedCases"]} if item.get("strictUnexpectedCases") is not None else {}),
                **({"fullMatrixScripts": item["fullMatrixScripts"]} if item.get("fullMatrixScripts") is not None else {}),
                **({"fullMatrixUniqueScripts": item["fullMatrixUniqueScripts"]} if item.get("fullMatrixUniqueScripts") is not None else {}),
                **({"fullMatrixMissingRequired": item["fullMatrixMissingRequired"]} if item.get("fullMatrixMissingRequired") is not None else {}),
                **({"fullMatrixUnexpectedScripts": item["fullMatrixUnexpectedScripts"]} if item.get("fullMatrixUnexpectedScripts") is not None else {}),
            }
            for item in executed
        ],
    }

    print(json.dumps(result, ensure_ascii=False))
    if not ok:
        for item in executed:
            if not item["ok"] and not item["skipped"]:
                if item.get("stdout"):
                    print(item["stdout"], file=sys.stderr)
                if item.get("stderr"):
                    print(item["stderr"], file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
