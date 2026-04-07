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
    base = tempfile.mkdtemp(prefix=f"{prefix}-state-lifecycle-smoke-")
    os.environ[f"{prefix}_E2EE_KEYSTORE"] = os.path.join(base, "keys.json")
    os.environ[f"{prefix}_E2EE_RATCHET_STORE"] = os.path.join(base, "ratchet.json")
    os.environ[f"{prefix}_E2EE_OTK_STORE"] = os.path.join(base, "otk.json")

    sid = "state-lifecycle-smoke"

    m1 = load_mod(module_path, f"bridge_{prefix.lower()}_state_1")

    recv_ok = m1._ratchet_check_and_advance(sid, 1, "H1")
    out1 = m1._ratchet_next_out_counter(sid)
    m1._ratchet_mix_chain_key(sid, b"recv-pre", "c2s", 1)
    m1._ratchet_mix_chain_key(sid, b"send-pre", "s2c", out1)

    step1 = m1._ratchet_apply_peer_pub(sid, "peer-ratchet-A", mix_material=b"mix-A")
    m1._ratchet_mix_chain_key(sid, b"recv-post-step1", "c2s", 1)
    out2 = m1._ratchet_next_out_counter(sid)
    m1._ratchet_mix_chain_key(sid, b"send-post-step1", "s2c", out2)

    # Simulate restart: fresh module import must recover persisted session state.
    m2 = load_mod(module_path, f"bridge_{prefix.lower()}_state_2")
    st2 = m2._load_ratchet_store()["sessions"][sid]
    root_after_restart = st2.get("rootKeySeed", "")

    step_same = m2._ratchet_apply_peer_pub(sid, "peer-ratchet-A", mix_material=b"ignored")
    step2 = m2._ratchet_apply_peer_pub(sid, "peer-ratchet-B", mix_material=b"mix-B")

    # Simulate second restart after DH-step rotation.
    m3 = load_mod(module_path, f"bridge_{prefix.lower()}_state_3")
    st3 = m3._load_ratchet_store()["sessions"][sid]
    root_after_step2 = st3.get("rootKeySeed", "")

    ok = (
        recv_ok is True and
        out1 == 1 and
        step1 == 1 and
        int(st2["recv"].get("chainCounter", 0)) == 1 and
        int(st2["send"].get("chainCounter", 0)) == 1 and
        int(st2["send"].get("lastOut", 0)) == 2 and
        bool(st2.get("recvChainSeed", "")) and
        bool(st2.get("sendChainSeed", "")) and
        bool(root_after_restart) and
        step_same == 1 and
        step2 == 2 and
        int(st3["recv"].get("chainCounter", 0)) == 0 and
        int(st3["send"].get("chainCounter", 0)) == 0 and
        st3.get("recvChainSeed", "") == "" and
        st3.get("sendChainSeed", "") == "" and
        st3["recv"].get("lastPeerRatchetPub", "") == "peer-ratchet-B" and
        bool(root_after_step2) and
        root_after_step2 != root_after_restart
    )

    print(json.dumps({
        "ok": ok,
        "recvAccepted": recv_ok,
        "out1": out1,
        "out2": out2,
        "step1": step1,
        "stepSame": step_same,
        "step2": step2,
        "postRestartRecvCounter": int(st2["recv"].get("chainCounter", 0)),
        "postRestartSendCounter": int(st2["send"].get("chainCounter", 0)),
        "postRestartLastOut": int(st2["send"].get("lastOut", 0)),
        "postStep2RecvCounter": int(st3["recv"].get("chainCounter", 0)),
        "postStep2SendCounter": int(st3["send"].get("chainCounter", 0)),
    }))
    return 0 if ok else 1


if __name__ == "__main__":
    import sys
    if len(sys.argv) != 3:
        print("usage: e2ee_state_lifecycle_smoke.py <bridge.py> <APPENCLAW_APP|appenClaw_APP>")
        sys.exit(2)
    raise SystemExit(run(sys.argv[1], sys.argv[2]))
