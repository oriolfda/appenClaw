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
    base = tempfile.mkdtemp(prefix=f"{prefix}-dh-step-smoke-")
    os.environ[f"{prefix}_E2EE_KEYSTORE"] = os.path.join(base, "keys.json")
    os.environ[f"{prefix}_E2EE_RATCHET_STORE"] = os.path.join(base, "ratchet.json")
    os.environ[f"{prefix}_E2EE_OTK_STORE"] = os.path.join(base, "otk.json")

    m = load_mod(module_path, f"bridge_{prefix.lower()}_dh")
    sid = "dh-step-smoke"

    # Prime both recv/send chains so DH-step reset behavior is observable.
    m._ratchet_mix_chain_key(sid, b"recv-base", "c2s", 1)
    out = m._ratchet_next_out_counter(sid)
    m._ratchet_mix_chain_key(sid, b"send-base", "s2c", out)

    st0 = m._load_ratchet_store()["sessions"][sid]
    pre_recv_counter = int(st0["recv"].get("chainCounter", 0))
    pre_send_counter = int(st0["send"].get("chainCounter", 0))
    pre_recv_seed = st0.get("recvChainSeed", "")
    pre_send_seed = st0.get("sendChainSeed", "")

    step1 = m._ratchet_apply_peer_pub(sid, "peer-ratchet-A", mix_material=b"mix-A")
    st1 = m._load_ratchet_store()["sessions"][sid]
    root1 = st1.get("rootKeySeed", "")

    # Same peer pub must not advance ratchet step or mutate root key.
    step_same = m._ratchet_apply_peer_pub(sid, "peer-ratchet-A", mix_material=b"mix-A-ignored")
    st_same = m._load_ratchet_store()["sessions"][sid]
    root_same = st_same.get("rootKeySeed", "")

    # Re-prime then rotate peer ratchet pub to enforce second controlled re-seed.
    m._ratchet_mix_chain_key(sid, b"recv-base-2", "c2s", 1)
    out2 = m._ratchet_next_out_counter(sid)
    m._ratchet_mix_chain_key(sid, b"send-base-2", "s2c", out2)

    step2 = m._ratchet_apply_peer_pub(sid, "peer-ratchet-B", mix_material=b"mix-B")
    st2 = m._load_ratchet_store()["sessions"][sid]
    root2 = st2.get("rootKeySeed", "")

    ok = (
        pre_recv_counter >= 1 and
        pre_send_counter >= 1 and
        bool(pre_recv_seed) and
        bool(pre_send_seed) and
        step1 == 1 and
        int(st1["recv"].get("chainCounter", 0)) == 0 and
        int(st1["send"].get("chainCounter", 0)) == 0 and
        st1.get("recvChainSeed", "") == "" and
        st1.get("sendChainSeed", "") == "" and
        bool(root1) and
        step_same == 1 and
        root_same == root1 and
        step2 == 2 and
        int(st2["recv"].get("chainCounter", 0)) == 0 and
        int(st2["send"].get("chainCounter", 0)) == 0 and
        st2.get("recvChainSeed", "") == "" and
        st2.get("sendChainSeed", "") == "" and
        bool(root2) and
        root2 != root1
    )

    print(json.dumps({
        "ok": ok,
        "step1": step1,
        "stepSame": step_same,
        "step2": step2,
        "preRecvCounter": pre_recv_counter,
        "preSendCounter": pre_send_counter,
        "outCounterBeforeStep2": out2,
    }))
    return 0 if ok else 1


if __name__ == "__main__":
    import sys
    if len(sys.argv) != 3:
        print("usage: e2ee_dh_step_smoke.py <bridge.py> <APPENCLAW_APP|appenClaw_APP>")
        sys.exit(2)
    raise SystemExit(run(sys.argv[1], sys.argv[2]))
