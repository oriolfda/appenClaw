#!/usr/bin/env python3
import base64
import json
import os
import shutil
import subprocess
import tempfile
import uuid
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import ed25519, x25519
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives.kdf.hkdf import HKDF

HOST = os.environ.get("AIGOR_BRIDGE_HOST", "0.0.0.0")
PORT = int(os.environ.get("AIGOR_BRIDGE_PORT", "8091"))
TOKEN = os.environ.get("AIGOR_BRIDGE_TOKEN", "")
DEFAULT_SESSION = os.environ.get("AIGOR_BRIDGE_SESSION", "aigor-app-chat")
PUBLIC_BASE_URL = os.environ.get("AIGOR_BRIDGE_PUBLIC_BASE_URL", f"http://192.168.0.102:{PORT}")
MEDIA_DIR = os.environ.get("AIGOR_BRIDGE_MEDIA_DIR", "/mnt/apps/aigor/media")
EDGE_TTS = os.environ.get("AIGOR_BRIDGE_EDGE_TTS", "/home/oriol/.openclaw/venvs/aigor-tts/bin/edge-tts")
E2EE_ENABLED = os.environ.get("AIGOR_APP_E2EE_ENABLED", "false").lower() == "true"
E2EE_REQUIRED = os.environ.get("AIGOR_APP_E2EE_REQUIRED", "false").lower() == "true"
E2EE_PROTOCOL = os.environ.get("AIGOR_APP_E2EE_PROTOCOL", "signal-x3dh-dr-v1")
E2EE_BUNDLE_KID = os.environ.get("AIGOR_APP_E2EE_BUNDLE_KID", "1")
E2EE_IDENTITY_PUB = os.environ.get("AIGOR_APP_E2EE_IDENTITY_PUB", "")
E2EE_SIGNED_PREKEY_PUB = os.environ.get("AIGOR_APP_E2EE_SIGNED_PREKEY_PUB", "")
E2EE_SIGNED_PREKEY_SIG = os.environ.get("AIGOR_APP_E2EE_SIGNED_PREKEY_SIG", "")


def extract_json_block(text: str):
    start = text.find("{")
    if start < 0:
        return None

    depth = 0
    in_str = False
    esc = False
    end = -1

    for idx in range(start, len(text)):
        ch = text[idx]
        if in_str:
            if esc:
                esc = False
            elif ch == "\\":
                esc = True
            elif ch == '"':
                in_str = False
            continue

        if ch == '"':
            in_str = True
        elif ch == '{':
            depth += 1
        elif ch == '}':
            depth -= 1
            if depth == 0:
                end = idx + 1
                break

    if end == -1:
        return None

    candidate = text[start:end]
    try:
        return json.loads(candidate)
    except Exception:
        return None


def run_openclaw_json(cmd, timeout=180):
    proc = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
    out = (proc.stdout or "") + (proc.stderr or "")
    parsed = extract_json_block(out)
    return proc.returncode, parsed, out


def safe_name(name: str) -> str:
    return "".join(c for c in name if c.isalnum() or c in ("-", "_", "."))[:120] or "attachment"


def detect_lang(text: str) -> str:
    t = (text or "").lower().strip()

    ca_markers = [
        "què", "això", "avui", "bon dia", "gràcies", "dóna", "si us plau", "perquè", "vull", "m'agradaria", "sopar",
        "en quin", "idioma", "parlant", "ara mateix"
    ]
    es_markers = [
        "qué", "hoy", "gracias", "buenos", "dime", "por favor", "quiero", "responde", "castellano", "cena",
        "en qué", "idioma", "hablando", "ahora"
    ]
    en_markers = [
        "what", "today", "thanks", "please", "i want", "reply", "english", "dinner",
        "which language", "i'm speaking", "speaking now", "right now", "are you", "can you"
    ]

    ca_score = sum(1 for w in ca_markers if w in t)
    es_score = sum(1 for w in es_markers if w in t)
    en_score = sum(1 for w in en_markers if w in t)

    # Extra heuristic: if text is plain ASCII and has common English words, favor EN.
    ascii_only = all(ord(ch) < 128 for ch in t)
    if ascii_only and any(w in t for w in ["the", "and", "you", "your", "which", "language", "speaking", "now"]):
        en_score += 2

    if max(ca_score, es_score, en_score) == 0:
        # conservative fallback remains catalan baseline
        return "ca"

    if en_score >= ca_score and en_score >= es_score:
        return "en"
    if es_score >= ca_score and es_score >= en_score:
        return "es"
    return "ca"


def voice_for_lang(lang: str):
    if lang == "ca":
        return "ca-ES-EnricNeural", "+20%", "-8Hz"
    if lang == "es":
        return "es-ES-AlvaroNeural", "+0%", "+0Hz"
    return "en-US-AndrewNeural", "+0%", "+0Hz"


def parse_tts_from_text(text: str):
    if not text:
        return text, None
    import re

    # 1) Prioritza el bloc explícit de text TTS
    m_text = re.search(r"\[\[tts:text\]\](.+?)\[\[/tts:text\]\]", text, flags=re.DOTALL)
    if m_text:
        tts_text = m_text.group(1).strip()
        cleaned = re.sub(r"\[\[tts:[^\]]+\]\]", "", text)
        cleaned = cleaned.replace(m_text.group(0), "").strip()
        return cleaned, tts_text

    # 2) Si només hi ha [[tts:...]], tracta-ho com a metadada de veu, no com a text a locutar
    cleaned = re.sub(r"\[\[tts:[^\]]+\]\]", "", text).strip()
    return cleaned, None


def extract_audio_transcript(extra_prompt: str) -> str:
    """Extreu la transcripció STT del bloc d'ajuda quan existeix."""
    if not extra_prompt:
        return ""
    marker = "Transcripció àudio:"
    for line in extra_prompt.splitlines():
        if line.startswith(marker):
            return line.split(marker, 1)[1].strip()
    return ""


def synthesize_tts_audio(text: str, lang_hint: str = "ca"):
    if not text or not os.path.exists(EDGE_TTS):
        return None
    os.makedirs(MEDIA_DIR, exist_ok=True)
    voice, rate, pitch = voice_for_lang(lang_hint)
    fname = f"tts-{uuid.uuid4().hex}.mp3"
    out = os.path.join(MEDIA_DIR, fname)
    try:
        subprocess.run([
            EDGE_TTS,
            "--voice", voice,
            f"--rate={rate}",
            f"--pitch={pitch}",
            "--text", text,
            "--write-media", out,
        ], capture_output=True, text=True, timeout=90, check=True)
        return f"{PUBLIC_BASE_URL}/media/{fname}"
    except Exception:
        return None


def b64rand(n: int) -> str:
    return base64.urlsafe_b64encode(os.urandom(n)).decode("ascii").rstrip("=")


def _bridge_keystore_path() -> str:
    return os.environ.get("AIGOR_APP_E2EE_KEYSTORE", "/mnt/apps/aigor/e2ee/bridge_keys.json")


def _otk_store_path() -> str:
    return os.environ.get("AIGOR_APP_E2EE_OTK_STORE", "/mnt/apps/aigor/e2ee/otk_store.json")


def _load_otk_store():
    path = _otk_store_path()
    if os.path.exists(path):
        try:
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return {"next": 1, "keys": []}


def _save_otk_store(store: dict):
    path = _otk_store_path()
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(store, f, indent=2)


def _ensure_otk_pool(min_size: int = 20):
    store = _load_otk_store()
    keys = store.get("keys", [])
    next_id = int(store.get("next", 1))
    while len(keys) < min_size:
        otk_priv = x25519.X25519PrivateKey.generate()
        otk_pub_b64 = base64.b64encode(
            otk_priv.public_key().public_bytes(
                encoding=serialization.Encoding.DER,
                format=serialization.PublicFormat.SubjectPublicKeyInfo,
            )
        ).decode("ascii")
        otk_priv_pem = otk_priv.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.PKCS8,
            encryption_algorithm=serialization.NoEncryption(),
        ).decode("utf-8")
        keys.append({"id": f"otk-{next_id}", "publicKey": otk_pub_b64, "privatePem": otk_priv_pem})
        next_id += 1
    store["keys"] = keys
    store["next"] = next_id
    _save_otk_store(store)


def _get_otk_private(otk_id: str):
    if not otk_id:
        return None
    store = _load_otk_store()
    for k in (store.get("keys", []) or []):
        if k.get("id") == otk_id and k.get("privatePem"):
            return serialization.load_pem_private_key(k["privatePem"].encode("utf-8"), password=None)
    return None


def _consume_otk(otk_id: str) -> bool:
    if not otk_id:
        return False
    store = _load_otk_store()
    keys = store.get("keys", [])
    kept = [k for k in keys if k.get("id") != otk_id]
    consumed = len(kept) != len(keys)
    if consumed:
        store["keys"] = kept
        _save_otk_store(store)
    return consumed


def _peek_otk_list(limit: int = 5):
    _ensure_otk_pool()
    store = _load_otk_store()
    keys = (store.get("keys", []) or [])[:limit]
    return [{"id": k.get("id"), "publicKey": k.get("publicKey")} for k in keys]


def _ratchet_store_path() -> str:
    return os.environ.get("AIGOR_APP_E2EE_RATCHET_STORE", "/mnt/apps/aigor/e2ee/ratchet_store.json")


def _ensure_session_chains(st: dict) -> dict:
    send = st.setdefault("send", {})
    recv = st.setdefault("recv", {})
    send.setdefault("lastOut", 0)
    send.setdefault("chainCounter", 0)
    recv.setdefault("maxIn", 0)
    recv.setdefault("seenIn", [])
    recv.setdefault("skippedIn", [])
    recv.setdefault("skippedByHeader", {})
    recv.setdefault("chainCounter", 0)
    recv.setdefault("ratchetStep", 0)
    recv.setdefault("lastPeerRatchetPub", "")
    st.setdefault("rootKeySeed", "")
    st.setdefault("sendChainSeed", "")
    st.setdefault("recvChainSeed", "")
    return st


def _load_ratchet_store():
    path = _ratchet_store_path()
    if os.path.exists(path):
        try:
            with open(path, "r", encoding="utf-8") as f:
                store = json.load(f)
            sessions = store.setdefault("sessions", {})
            for sid, st in list(sessions.items()):
                if "send" not in st or "recv" not in st:
                    # migrate from legacy flat shape
                    st = {
                        "send": {"lastOut": int(st.get("lastOut", 0))},
                        "recv": {
                            "maxIn": int(st.get("maxIn", 0)),
                            "seenIn": st.get("seenIn", []),
                            "skippedIn": st.get("skippedIn", []),
                            "ratchetStep": int(st.get("ratchetStep", 0)),
                            "lastPeerRatchetPub": st.get("lastPeerRatchetPub", ""),
                        },
                    }
                sessions[sid] = _ensure_session_chains(st)
            return store
        except Exception:
            pass
    return {"sessions": {}}


def _save_ratchet_store(store: dict):
    path = _ratchet_store_path()
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(store, f, indent=2)


def _ratchet_compact_recv_state(recv: dict, floor: int):
    seen = set(int(x) for x in recv.get("seenIn", []) if isinstance(x, int) or str(x).isdigit())
    skipped = set(int(x) for x in recv.get("skippedIn", []) if isinstance(x, int) or str(x).isdigit())
    recv["seenIn"] = sorted(c for c in seen if c >= floor)
    recv["skippedIn"] = sorted(c for c in skipped if c >= floor and c not in seen)

    # Keep header-scoped skipped cache bounded to the same replay window and
    # remove entries already consumed/seen.
    raw = recv.get("skippedByHeader", {})
    by_header = raw if isinstance(raw, dict) else {}
    compact = {}
    for hid, counters in by_header.items():
        vals = set(int(x) for x in (counters or []) if isinstance(x, int) or str(x).isdigit())
        kept = sorted(c for c in vals if c >= floor and c not in seen)
        if kept:
            compact[str(hid)] = kept
    recv["skippedByHeader"] = compact


def _ratchet_check_and_advance(session_id: str, inbound_counter: int, header_id: str = "default", window: int = 64) -> bool:
    store = _load_ratchet_store()
    sessions = store.setdefault("sessions", {})
    st = _ensure_session_chains(sessions.setdefault(session_id, {}))
    recv = st["recv"]

    max_in = int(recv.get("maxIn", 0))
    seen = set(int(x) for x in recv.get("seenIn", []) if isinstance(x, int) or str(x).isdigit())
    skipped = set(int(x) for x in recv.get("skippedIn", []) if isinstance(x, int) or str(x).isdigit())

    if inbound_counter <= 0:
        return False
    if inbound_counter in seen:
        return False
    if inbound_counter < max_in - window:
        return False

    header_id = str(header_id or recv.get("currentHeaderId", "default"))
    skipped_by_header = recv.get("skippedByHeader", {}) if isinstance(recv.get("skippedByHeader"), dict) else {}
    header_skipped = set(int(x) for x in skipped_by_header.get(header_id, []) if isinstance(x, int) or str(x).isdigit())

    # Out-of-order receive path must match previously registered skipped counters.
    if inbound_counter <= max_in and (inbound_counter not in skipped or inbound_counter not in header_skipped):
        return False

    if inbound_counter > max_in + 1:
        # Bound skipped-gap materialization to replay window to avoid huge allocations
        # on attacker-controlled large counter jumps.
        gap_start = max(max_in + 1, inbound_counter - window)
        if gap_start < inbound_counter:
            missing = set(range(gap_start, inbound_counter))
            skipped.update(missing)
            header_skipped.update(missing)

    seen.add(inbound_counter)
    skipped.discard(inbound_counter)
    header_skipped.discard(inbound_counter)
    max_in = max(max_in, inbound_counter)
    floor = max_in - window

    recv["maxIn"] = max_in
    recv["seenIn"] = sorted(seen)
    recv["skippedIn"] = sorted(skipped)
    compact_header_skipped = sorted(c for c in header_skipped if c >= floor)
    if compact_header_skipped:
        skipped_by_header[header_id] = compact_header_skipped
    elif header_id in skipped_by_header:
        skipped_by_header.pop(header_id, None)
    recv["skippedByHeader"] = skipped_by_header
    _ratchet_compact_recv_state(recv, floor)
    _save_ratchet_store(store)
    return True


def _ratchet_next_out_counter(session_id: str) -> int:
    store = _load_ratchet_store()
    sessions = store.setdefault("sessions", {})
    st = _ensure_session_chains(sessions.setdefault(session_id, {}))
    send = st["send"]
    nxt = int(send.get("lastOut", 0)) + 1
    send["lastOut"] = nxt
    _save_ratchet_store(store)
    return nxt


def _ratchet_snapshot_recv(session_id: str) -> dict:
    store = _load_ratchet_store()
    sessions = store.setdefault("sessions", {})
    st = _ensure_session_chains(sessions.setdefault(session_id, {}))
    recv = st["recv"]
    send = st["send"]
    return {
        "maxIn": int(recv.get("maxIn", 0)),
        "seenIn": list(recv.get("seenIn", []) or []),
        "skippedIn": list(recv.get("skippedIn", []) or []),
        "skippedByHeader": json.loads(json.dumps(recv.get("skippedByHeader", {}) or {})),
        "recvChainCounter": int(recv.get("chainCounter", 0)),
        "recvRatchetStep": int(recv.get("ratchetStep", 0)),
        "recvLastPeerRatchetPub": str(recv.get("lastPeerRatchetPub", "") or ""),
        "recvChainSeed": str(st.get("recvChainSeed", "") or ""),
        "sendChainSeed": str(st.get("sendChainSeed", "") or ""),
        "rootKeySeed": str(st.get("rootKeySeed", "") or ""),
        "sendChainCounter": int(send.get("chainCounter", 0)),
    }


def _ratchet_restore_recv(session_id: str, snapshot: dict):
    if not isinstance(snapshot, dict):
        return
    store = _load_ratchet_store()
    sessions = store.setdefault("sessions", {})
    st = _ensure_session_chains(sessions.setdefault(session_id, {}))
    recv = st["recv"]
    send = st["send"]
    recv["maxIn"] = int(snapshot.get("maxIn", 0))
    recv["seenIn"] = list(snapshot.get("seenIn", []) or [])
    recv["skippedIn"] = list(snapshot.get("skippedIn", []) or [])
    raw = snapshot.get("skippedByHeader", {})
    recv["skippedByHeader"] = raw if isinstance(raw, dict) else {}
    recv["chainCounter"] = int(snapshot.get("recvChainCounter", recv.get("chainCounter", 0)))
    recv["ratchetStep"] = int(snapshot.get("recvRatchetStep", recv.get("ratchetStep", 0)))
    recv["lastPeerRatchetPub"] = str(snapshot.get("recvLastPeerRatchetPub", recv.get("lastPeerRatchetPub", "")) or "")
    st["recvChainSeed"] = str(snapshot.get("recvChainSeed", st.get("recvChainSeed", "")) or "")
    st["sendChainSeed"] = str(snapshot.get("sendChainSeed", st.get("sendChainSeed", "")) or "")
    st["rootKeySeed"] = str(snapshot.get("rootKeySeed", st.get("rootKeySeed", "")) or "")
    send["chainCounter"] = int(snapshot.get("sendChainCounter", send.get("chainCounter", 0)))
    _save_ratchet_store(store)


def _kdf_rk(root_key: bytes, dh_out: bytes) -> tuple[bytes, bytes]:
    import hmac
    import hashlib
    prk = hmac.new(root_key, dh_out, hashlib.sha256).digest()
    root_next = hmac.new(prk, b"KDF_RK:root", hashlib.sha256).digest()
    chain_init = hmac.new(prk, b"KDF_RK:chain", hashlib.sha256).digest()
    return root_next[:32], chain_init[:32]


def _kdf_ck(chain_key: bytes) -> tuple[bytes, bytes]:
    import hmac
    import hashlib
    chain_next = hmac.new(chain_key, b"KDF_CK:chain", hashlib.sha256).digest()[:32]
    message_key = hmac.new(chain_key, b"KDF_CK:msg", hashlib.sha256).digest()[:32]
    return chain_next, message_key


def _ratchet_preview_chain_key(st: dict, base_key: bytes, direction: str, counter: int) -> tuple[bytes, bytes]:
    import hashlib

    is_recv = direction == "c2s"
    seed_name = "recvChainSeed" if is_recv else "sendChainSeed"

    root_prev_b64 = st.get("rootKeySeed", "")
    root_prev = base64.b64decode(root_prev_b64) if root_prev_b64 else hashlib.sha256(base_key + b"root-init").digest()[:32]

    dh_material = hashlib.sha256(base_key + direction.encode("utf-8") + str(counter).encode("utf-8")).digest()
    root_next, chain_init = _kdf_rk(root_prev, dh_material)

    prev_b64 = st.get(seed_name, "")
    current_chain = base64.b64decode(prev_b64) if prev_b64 else chain_init
    chain_next, _ = _kdf_ck(current_chain)

    return chain_next, root_next


def _ratchet_mix_chain_key(session_id: str, base_key: bytes, direction: str, counter: int) -> bytes:
    store = _load_ratchet_store()
    sessions = store.setdefault("sessions", {})
    st = _ensure_session_chains(sessions.setdefault(session_id, {}))

    mixed, root_next = _ratchet_preview_chain_key(st, base_key, direction, counter)

    is_recv = direction == "c2s"
    chain_box = st["recv"] if is_recv else st["send"]
    seed_name = "recvChainSeed" if is_recv else "sendChainSeed"

    st[seed_name] = base64.b64encode(mixed).decode("ascii")
    st["rootKeySeed"] = base64.b64encode(root_next).decode("ascii")
    chain_box["chainCounter"] = int(chain_box.get("chainCounter", 0)) + 1

    _save_ratchet_store(store)
    return mixed


def _load_or_create_bridge_keys():
    path = _bridge_keystore_path()
    os.makedirs(os.path.dirname(path), exist_ok=True)

    if os.path.exists(path):
        with open(path, "r", encoding="utf-8") as f:
            raw = json.load(f)
        identity_pem = raw.get("identityX25519PrivatePem") or raw.get("x25519PrivatePem") or raw.get("ecdhPrivatePem")
        spk_pem = raw.get("signedPreKeyX25519PrivatePem") or identity_pem
        identity_priv = serialization.load_pem_private_key(identity_pem.encode("utf-8"), password=None)
        spk_priv = serialization.load_pem_private_key(spk_pem.encode("utf-8"), password=None)
        sign_priv = serialization.load_pem_private_key(raw["signPrivatePem"].encode("utf-8"), password=None)
        kid = str(raw.get("kid", E2EE_BUNDLE_KID))
        return identity_priv, spk_priv, sign_priv, kid

    identity_priv = x25519.X25519PrivateKey.generate()
    spk_priv = x25519.X25519PrivateKey.generate()
    sign_priv = ed25519.Ed25519PrivateKey.generate()

    raw = {
        "kid": str(E2EE_BUNDLE_KID),
        "identityX25519PrivatePem": identity_priv.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.PKCS8,
            encryption_algorithm=serialization.NoEncryption(),
        ).decode("utf-8"),
        "signedPreKeyX25519PrivatePem": spk_priv.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.PKCS8,
            encryption_algorithm=serialization.NoEncryption(),
        ).decode("utf-8"),
        "signPrivatePem": sign_priv.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.PKCS8,
            encryption_algorithm=serialization.NoEncryption(),
        ).decode("utf-8"),
    }
    with open(path, "w", encoding="utf-8") as f:
        json.dump(raw, f, indent=2)

    return identity_priv, spk_priv, sign_priv, str(E2EE_BUNDLE_KID)


_BRIDGE_IDENTITY_PRIVKEY, _BRIDGE_SPK_PRIVKEY, _BRIDGE_SIGN_PRIVKEY, _BRIDGE_KID = _load_or_create_bridge_keys()
_BRIDGE_IDENTITY_PUB_B64 = base64.b64encode(
    _BRIDGE_IDENTITY_PRIVKEY.public_key().public_bytes(
        encoding=serialization.Encoding.DER,
        format=serialization.PublicFormat.SubjectPublicKeyInfo,
    )
).decode("ascii")
_BRIDGE_SPK_PUB_B64 = base64.b64encode(
    _BRIDGE_SPK_PRIVKEY.public_key().public_bytes(
        encoding=serialization.Encoding.DER,
        format=serialization.PublicFormat.SubjectPublicKeyInfo,
    )
).decode("ascii")
_BRIDGE_SIGN_PUB_B64 = base64.b64encode(
    _BRIDGE_SIGN_PRIVKEY.public_key().public_bytes(
        encoding=serialization.Encoding.DER,
        format=serialization.PublicFormat.SubjectPublicKeyInfo,
    )
).decode("ascii")

_ensure_otk_pool()


def _decode_pubkey_spki(b64: str):
    raw = base64.b64decode(b64, validate=True)
    pub = serialization.load_der_public_key(raw)
    if not isinstance(pub, x25519.X25519PublicKey):
        raise ValueError("expected X25519 public key")
    return pub


def _hkdf_key(shared: bytes, salt: bytes, info: bytes = b"aigor-e2ee-v1") -> bytes:
    hkdf = HKDF(algorithm=hashes.SHA256(), length=32, salt=salt, info=info)
    return hkdf.derive(shared)


def _derive_chain_key(base_key: bytes, direction: str, ratchet_step: int = 0) -> bytes:
    import hmac, hashlib
    label = f"chain:{direction}:step:{int(ratchet_step)}"
    return hmac.new(base_key, label.encode("utf-8"), hashlib.sha256).digest()[:32]


def _derive_message_key(chain_key: bytes, counter: int, label: str) -> bytes:
    import hmac, hashlib
    return hmac.new(chain_key, f"{label}:{counter}".encode("utf-8"), hashlib.sha256).digest()[:32]


def encrypt_real_envelope(plaintext: str, key: bytes, ad: str = "") -> dict:
    iv = os.urandom(12)
    aes = AESGCM(key)
    ct = aes.encrypt(iv, plaintext.encode("utf-8"), ad.encode("utf-8"))
    return {
        "v": 1,
        "alg": "x25519-aesgcm-v1",
        "iv": base64.b64encode(iv).decode("ascii"),
        "ciphertext": base64.b64encode(ct).decode("ascii"),
        "ad": ad,
    }


def _ratchet_apply_peer_pub(session_id: str, peer_pub_b64: str, mix_material: bytes = b"") -> int:
    store = _load_ratchet_store()
    sessions = store.setdefault("sessions", {})
    st = _ensure_session_chains(sessions.setdefault(session_id, {}))
    recv = st["recv"]
    last_pub = recv.get("lastPeerRatchetPub", "")
    step = int(recv.get("ratchetStep", 0))
    if peer_pub_b64 and peer_pub_b64 != last_pub:
        step += 1
        recv["lastPeerRatchetPub"] = peer_pub_b64
        recv["ratchetStep"] = step

        # Controlled re-seed on DH ratchet change:
        # - drop recv chain seed/counter so next inbound derives from new ratchet material only
        # - drop send chain seed/counter to avoid stale outbound chain reuse across DH steps
        st["recvChainSeed"] = ""
        recv["chainCounter"] = 0
        st["sendChainSeed"] = ""
        st["send"]["chainCounter"] = 0

        if mix_material:
            import hashlib
            root_prev = base64.b64decode(st.get("rootKeySeed", "")) if st.get("rootKeySeed", "") else b""
            st["rootKeySeed"] = base64.b64encode(hashlib.sha256(root_prev + mix_material + step.to_bytes(4, "big")).digest()).decode("ascii")
        _save_ratchet_store(store)
    return step


def decrypt_real_envelope(env: dict, session_id: str):
    eph_b64 = env.get("ephemeralPub", "")
    header_id = str(env.get("headerId", "default"))
    ratchet_b64 = env.get("ratchetPub", "")
    otk_id = str(env.get("otkId", "")).strip()
    salt = base64.b64decode(env.get("salt", ""))
    iv = base64.b64decode(env.get("iv", ""))
    ct = base64.b64decode(env.get("ciphertext", ""))
    ad = str(env.get("ad", ""))
    counter = int(env.get("counter", 0))

    import hashlib

    eph_pub = _decode_pubkey_spki(eph_b64)
    shared = _BRIDGE_SPK_PRIVKEY.exchange(eph_pub)
    otk_priv = _get_otk_private(otk_id)
    otk_used = otk_priv is not None
    if otk_used:
        shared += otk_priv.exchange(eph_pub)
    base_key = _hkdf_key(shared, salt)

    ratchet_shared = b""
    ratchet_step = int(env.get("ratchetStep", 1) or 1)
    if ratchet_b64:
        try:
            ratchet_pub = _decode_pubkey_spki(ratchet_b64)
            ratchet_shared = _BRIDGE_SPK_PRIVKEY.exchange(ratchet_pub)
            mix_salt = hashlib.sha256(base64.b64decode(ratchet_b64)).digest()[:16]
            base_key = _hkdf_key(base_key + ratchet_shared, mix_salt, info=b"aigor-ratchet-step-v1")
        except Exception as e:
            print(f"[bridge-debug] ratchet-mix-failed {e}", flush=True)
            raise

    recv_chain_key = _derive_chain_key(base_key, "send", ratchet_step)
    key = _derive_message_key(recv_chain_key, counter, "c2s")

    print(
        "[bridge-debug] decrypt-input " + json.dumps({
            "sessionId": session_id,
            "headerId": header_id,
            "counter": counter,
            "ratchetStep": ratchet_step,
            "otkId": otk_id,
            "otkUsed": otk_used,
            "saltSha256": hashlib.sha256(salt).hexdigest(),
            "ivSha256": hashlib.sha256(iv).hexdigest(),
            "ctSha256": hashlib.sha256(ct).hexdigest(),
            "ephSha256": hashlib.sha256(base64.b64decode(eph_b64)).hexdigest(),
            "ratchetSha256": hashlib.sha256(base64.b64decode(ratchet_b64)).hexdigest() if ratchet_b64 else None,
            "sharedSha256": hashlib.sha256(shared).hexdigest(),
            "baseKeySha256": hashlib.sha256(base_key).hexdigest(),
            "recvChainKeySha256": hashlib.sha256(recv_chain_key).hexdigest(),
            "messageKeySha256": hashlib.sha256(key).hexdigest(),
        }, ensure_ascii=False),
        flush=True,
    )

    aes = AESGCM(key)
    try:
        pt = aes.decrypt(iv, ct, ad.encode("utf-8")).decode("utf-8")
    except Exception as e:
        print(f"[bridge-debug] decrypt-failed {type(e).__name__}: {e}", flush=True)
        raise

    _ratchet_apply_peer_pub(session_id, ratchet_b64, mix_material=base_key + ratchet_shared)
    store = _load_ratchet_store()
    sessions = store.setdefault("sessions", {})
    st = _ensure_session_chains(sessions.setdefault(session_id, {}))
    st["recvChainSeed"] = base64.b64encode(base_key).decode("ascii")
    st["rootKeySeed"] = base64.b64encode(base_key).decode("ascii")
    st["recv"]["chainCounter"] = max(int(st["recv"].get("chainCounter", 0)), counter)
    _save_ratchet_store(store)

    return pt, base_key, ad, counter


def e2ee_bundle_payload() -> dict:
    signed_prekey_raw = base64.b64decode(_BRIDGE_SPK_PUB_B64)
    signed_prekey_sig = base64.b64encode(_BRIDGE_SIGN_PRIVKEY.sign(signed_prekey_raw)).decode("ascii")
    try:
        import hashlib
        print(
            "[bridge-debug] spk-sign",
            json.dumps({
                "spkSha256": hashlib.sha256(signed_prekey_raw).hexdigest(),
                "sigSha256": hashlib.sha256(base64.b64decode(signed_prekey_sig)).hexdigest(),
                "signPubSha256": hashlib.sha256(base64.b64decode(_BRIDGE_SIGN_PUB_B64)).hexdigest(),
            }, ensure_ascii=False),
            flush=True,
        )
    except Exception:
        pass
    one_time = _peek_otk_list(8)
    return {
        "ok": True,
        "e2ee": {
            "enabled": E2EE_ENABLED,
            "required": E2EE_REQUIRED,
            "protocol": E2EE_PROTOCOL,
            "bundle": {
                "kid": _BRIDGE_KID,
                "identityKey": _BRIDGE_IDENTITY_PUB_B64,
                "identitySignKey": _BRIDGE_SIGN_PUB_B64,
                "signedPreKey": {
                    "id": f"spk-{_BRIDGE_KID}",
                    "publicKey": _BRIDGE_SPK_PUB_B64,
                    "signature": signed_prekey_sig,
                },
                "oneTimePreKeys": one_time,
            },
            "warning": "Phase 1 done: persistent bridge keys + signed prekey bundle."
        }
    }


def decrypt_e2ee_attachment(att: dict, base_key: bytes):
    name = safe_name((att.get("name") or "attachment"))
    mime = (att.get("mime") or "application/octet-stream").lower()
    iv = base64.b64decode(att.get("iv", ""))
    ct = base64.b64decode(att.get("ciphertext", ""))
    ad = str(att.get("ad", ""))
    counter = int(att.get("counter", 0))

    recv_chain_key = _derive_chain_key(base_key, "recv")
    key = _derive_message_key(recv_chain_key, counter, "att")
    aes = AESGCM(key)
    raw = aes.decrypt(iv, ct, ad.encode("utf-8"))

    ext = name.split(".")[-1] if "." in name else "bin"
    base = os.path.join(tempfile.gettempdir(), f"aigor-{uuid.uuid4().hex}")
    path = f"{base}.{ext}"
    with open(path, "wb") as f:
        f.write(raw)

    decoded = {
        "name": name,
        "mime": mime,
        "dataBase64": base64.b64encode(raw).decode("ascii"),
        "_localPath": path,
    }
    return decoded


def process_attachment(att: dict):
    """Decode attachment and return (prompt_suffix, temp_paths[])"""
    name = safe_name((att.get("name") or "attachment"))
    mime = (att.get("mime") or "application/octet-stream").lower()
    data_b64 = att.get("dataBase64") or ""
    if not data_b64:
        return "", []

    raw = base64.b64decode(data_b64)
    ext = name.split(".")[-1] if "." in name else "bin"
    base = os.path.join(tempfile.gettempdir(), f"aigor-{uuid.uuid4().hex}")
    path = f"{base}.{ext}"
    with open(path, "wb") as f:
        f.write(raw)

    hints = [f"Adjunt rebut: {name} ({mime}), mida {len(raw)} bytes."]
    temp_paths = [path]

    if mime.startswith("image/"):
        hints.append(f"Analitza aquesta imatge local: {path}")

    elif mime.startswith("audio/"):
        stt_py = "/home/oriol/.openclaw/workspace/scripts/stt_aina_ca.py"
        stt_runner = "/home/oriol/.openclaw/venvs/aina-stt/bin/python"
        if os.path.exists(stt_py) and os.path.exists(stt_runner):
            try:
                tr = subprocess.run([stt_runner, stt_py, path], capture_output=True, text=True, timeout=180)
                transcript = (tr.stdout or "").strip()
                if transcript:
                    hints.append(f"Transcripció àudio: {transcript}")
                else:
                    hints.append("No s'ha pogut transcriure l'àudio.")
            except Exception as e:
                hints.append(f"Error transcripció àudio: {e}")

    elif mime.startswith("video/"):
        ffmpeg = shutil.which("ffmpeg")
        frame = f"{base}-frame.jpg"
        if ffmpeg:
            try:
                subprocess.run([ffmpeg, "-y", "-i", path, "-vf", "select=eq(n\\,0)", "-q:v", "2", "-frames:v", "1", frame], capture_output=True, text=True, timeout=180)
                if os.path.exists(frame):
                    hints.append(f"Vídeo adjunt. Fotograma inicial: {frame}. Analitza'l.")
                    temp_paths.append(frame)
                else:
                    hints.append("Vídeo adjunt; no s'ha pogut extreure fotograma.")
            except Exception as e:
                hints.append(f"Vídeo adjunt; error extraient fotograma: {e}")
        else:
            hints.append("Vídeo adjunt; ffmpeg no disponible per previsualització.")

    return "\n".join(hints), temp_paths


class Handler(BaseHTTPRequestHandler):
    def _send_cors(self):
        origin = self.headers.get("Origin") or "*"
        self.send_header("Access-Control-Allow-Origin", origin)
        self.send_header("Vary", "Origin")
        self.send_header("Access-Control-Allow-Headers", "Authorization, Content-Type")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")

    def _debug(self, message: str, **fields):
        try:
            suffix = " ".join(f"{k}={json.dumps(v, ensure_ascii=False)}" for k, v in fields.items())
            print(f"[bridge-debug] {message}" + (f" {suffix}" if suffix else ""), flush=True)
        except Exception:
            return

    def _send(self, code: int, payload: dict):
        if code >= 400:
            self._debug("http-error", code=code, payload=payload, path=self.path)
        body = json.dumps(payload).encode("utf-8")
        try:
            self.send_response(code)
            self._send_cors()
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
        except (BrokenPipeError, ConnectionResetError):
            # Client disconnected before response was written.
            return

    def do_OPTIONS(self):
        self.send_response(204)
        self._send_cors()
        self.send_header("Content-Length", "0")
        self.end_headers()

    def _auth_ok(self):
        if not TOKEN:
            return True
        auth = self.headers.get("Authorization", "")
        return auth == f"Bearer {TOKEN}"

    def do_GET(self):
        if self.path == "/e2ee/status":
            if not self._auth_ok():
                self._send(401, {"ok": False, "error": "Unauthorized"})
                return
            self._send(200, {
                "ok": True,
                "e2ee": {
                    "enabled": E2EE_ENABLED,
                    "required": E2EE_REQUIRED,
                    "protocol": E2EE_PROTOCOL,
                    "stage": "B-prekey-bundle-bootstrap"
                }
            })
            return

        if self.path == "/e2ee/prekey-bundle":
            if not self._auth_ok():
                self._send(401, {"ok": False, "error": "Unauthorized"})
                return
            self._send(200, e2ee_bundle_payload())
            return

        if self.path.startswith("/media/"):
            name = safe_name(self.path.split("/media/", 1)[1])
            path = os.path.join(MEDIA_DIR, name)
            if not os.path.exists(path):
                self._send(404, {"ok": False, "error": "media not found"})
                return
            try:
                with open(path, "rb") as f:
                    body = f.read()
                self.send_response(200)
                self._send_cors()
                self.send_header("Content-Type", "audio/mpeg")
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                self.wfile.write(body)
            except Exception:
                self._send(500, {"ok": False, "error": "media read error"})
            return

        if self.path != "/status":
            self._send(404, {"ok": False, "error": "Not found"})
            return

        if not self._auth_ok():
            self._send(401, {"ok": False, "error": "Unauthorized"})
            return

        try:
            session_id = DEFAULT_SESSION
            code, parsed, raw = run_openclaw_json(["openclaw", "sessions", "--json"], timeout=60)
            if code != 0 or not parsed:
                self._send(500, {"ok": False, "error": "sessions_failed", "details": raw[-500:]})
                return

            sessions = parsed.get("sessions") or []
            target = None
            for s in sessions:
                if (s.get("sessionId") or "") == session_id:
                    target = s
                    break

            # fallback: pick main if target session not listed
            if not target:
                for s in sessions:
                    if (s.get("key") or "") == "agent:main:main":
                        target = s
                        break

            if not target:
                self._send(200, {
                    "ok": True,
                    "context": {
                        "sessionId": session_id,
                        "usedTokens": None,
                        "maxTokens": None,
                        "usedPercent": None,
                        "freeTokens": None,
                        "freePercent": None,
                    },
                    "note": "No session metrics found yet"
                })
                return

            used = int(target.get("totalTokens") or 0)
            max_tokens = int(target.get("contextTokens") or 0)
            used_pct = round((used / max_tokens) * 100, 1) if max_tokens > 0 else None
            free = (max_tokens - used) if max_tokens > 0 else None
            free_pct = round((free / max_tokens) * 100, 1) if (max_tokens > 0 and free is not None) else None

            self._send(200, {
                "ok": True,
                "context": {
                    "sessionId": target.get("sessionId") or session_id,
                    "usedTokens": used,
                    "maxTokens": max_tokens,
                    "usedPercent": used_pct,
                    "freeTokens": free,
                    "freePercent": free_pct,
                    "model": target.get("model"),
                }
            })
        except subprocess.TimeoutExpired:
            self._send(504, {"ok": False, "error": "timeout"})
        except Exception as e:
            self._send(500, {"ok": False, "error": str(e)})

    def do_POST(self):
        if self.path not in ("/", "/chat"):
            self._send(404, {"ok": False, "error": "Not found"})
            return

        if not self._auth_ok():
            self._send(401, {"ok": False, "error": "Unauthorized"})
            return

        try:
            length = int(self.headers.get("Content-Length", "0"))
            raw = self.rfile.read(length).decode("utf-8")
            data = json.loads(raw or "{}")
        except Exception:
            self._send(400, {"ok": False, "error": "Bad JSON"})
            return

        if E2EE_REQUIRED and not isinstance(data.get("e2ee"), dict):
            self._send(400, {
                "ok": False,
                "error": "e2ee_required",
                "message": "Server requires encrypted envelope (phase 2)."
            })
            return

        e2ee_req = data.get("e2ee") if isinstance(data.get("e2ee"), dict) else None
        encrypted_reply = bool(e2ee_req.get("expectEncryptedReply", False)) if e2ee_req else False
        reply_key = None
        reply_ad = ""
        inbound_counter = 0
        session_id = (data.get("sessionId") or DEFAULT_SESSION).strip() or DEFAULT_SESSION

        if E2EE_REQUIRED:
            raw_ciphertext = e2ee_req.get("ciphertext") if e2ee_req else None
            has_ciphertext = isinstance(raw_ciphertext, str) and bool(raw_ciphertext.strip())
            if not has_ciphertext:
                self._send(400, {
                    "ok": False,
                    "error": "e2ee_ciphertext_required",
                    "message": "Server requires non-empty string ciphertext (no plaintext fallback)."
                })
                return
            if isinstance(data.get("attachment"), dict) and not isinstance(data.get("e2eeAttachment"), dict):
                self._send(400, {
                    "ok": False,
                    "error": "e2ee_attachment_required",
                    "message": "Server requires encrypted attachment envelope in strict mode."
                })
                return

        message = (data.get("message") or "").strip()
        if e2ee_req and e2ee_req.get("ciphertext"):
            raw_header_id = e2ee_req.get("headerId", "")
            if not isinstance(raw_header_id, str) or not raw_header_id.strip():
                self._send(400, {
                    "ok": False,
                    "error": "e2ee_header_required",
                    "message": "Encrypted envelope requires non-empty string headerId."
                })
                return
            if len(raw_header_id.strip()) > 128:
                self._send(400, {
                    "ok": False,
                    "error": "e2ee_header_too_long",
                    "message": "Encrypted envelope headerId exceeds 128-char limit."
                })
                return


        if e2ee_req and e2ee_req.get("ciphertext"):
            raw_counter = e2ee_req.get("counter", 0)
            # Strict hardening: require JSON integer type (no strings/floats/bools)
            # and a bounded positive range to avoid abuse/overflow edge cases.
            if isinstance(raw_counter, bool) or not isinstance(raw_counter, int) or raw_counter <= 0:
                self._send(400, {
                    "ok": False,
                    "error": "e2ee_counter_required",
                    "message": "Encrypted envelope requires a positive integer counter."
                })
                return
            if raw_counter > 2_147_483_647:
                self._send(400, {
                    "ok": False,
                    "error": "e2ee_counter_out_of_range",
                    "message": "Encrypted envelope counter exceeds max allowed value (2^31-1)."
                })
                return

            raw_iv = e2ee_req.get("iv")
            if not isinstance(raw_iv, str) or not raw_iv.strip():
                self._send(400, {
                    "ok": False,
                    "error": "e2ee_iv_required",
                    "message": "Encrypted envelope requires non-empty string iv."
                })
                return

            raw_salt = e2ee_req.get("salt")
            if not isinstance(raw_salt, str) or not raw_salt.strip():
                self._send(400, {
                    "ok": False,
                    "error": "e2ee_salt_required",
                    "message": "Encrypted envelope requires non-empty string salt."
                })
                return

            raw_ephemeral_pub = e2ee_req.get("ephemeralPub")
            if not isinstance(raw_ephemeral_pub, str) or not raw_ephemeral_pub.strip():
                self._send(400, {
                    "ok": False,
                    "error": "e2ee_ephemeral_required",
                    "message": "Encrypted envelope requires non-empty string ephemeralPub."
                })
                return

            # Pre-decode size guard to avoid decoding very large attacker-controlled base64 strings.
            if len(str(raw_ciphertext)) > 1_500_000:
                self._send(400, {
                    "ok": False,
                    "error": "e2ee_ciphertext_too_large",
                    "message": "Encrypted envelope ciphertext exceeds 1 MiB limit."
                })
                return

            try:
                decoded_ciphertext = base64.b64decode(str(raw_ciphertext), validate=True)
            except Exception:
                self._send(400, {
                    "ok": False,
                    "error": "e2ee_ciphertext_invalid",
                    "message": "Encrypted envelope requires valid base64 ciphertext."
                })
                return

            # AES-GCM ciphertext must at least include 16-byte auth tag.
            if len(decoded_ciphertext) < 16:
                self._send(400, {
                    "ok": False,
                    "error": "e2ee_ciphertext_invalid",
                    "message": "Encrypted envelope requires ciphertext with at least 16 bytes (GCM tag)."
                })
                return

            # Basic abuse guard: reject oversized envelopes before expensive crypto.
            if len(decoded_ciphertext) > 1024 * 1024:
                self._send(400, {
                    "ok": False,
                    "error": "e2ee_ciphertext_too_large",
                    "message": "Encrypted envelope ciphertext exceeds 1 MiB limit."
                })
                return

            if len(raw_iv) > 128:
                self._send(400, {
                    "ok": False,
                    "error": "e2ee_iv_invalid",
                    "message": "Encrypted envelope iv is too large."
                })
                return

            try:
                decoded_iv = base64.b64decode(raw_iv, validate=True)
            except Exception:
                self._send(400, {
                    "ok": False,
                    "error": "e2ee_iv_invalid",
                    "message": "Encrypted envelope requires valid base64 iv."
                })
                return

            if len(decoded_iv) != 12:
                self._send(400, {
                    "ok": False,
                    "error": "e2ee_iv_invalid",
                    "message": "Encrypted envelope requires 12-byte iv."
                })
                return

            if len(raw_salt) > 128:
                self._send(400, {
                    "ok": False,
                    "error": "e2ee_salt_invalid",
                    "message": "Encrypted envelope salt is too large."
                })
                return

            try:
                decoded_salt = base64.b64decode(raw_salt, validate=True)
            except Exception:
                self._send(400, {
                    "ok": False,
                    "error": "e2ee_salt_invalid",
                    "message": "Encrypted envelope requires valid base64 salt."
                })
                return

            if len(decoded_salt) != 16:
                self._send(400, {
                    "ok": False,
                    "error": "e2ee_salt_invalid",
                    "message": "Encrypted envelope requires 16-byte salt."
                })
                return

            if len(raw_ephemeral_pub) > 512:
                self._send(400, {
                    "ok": False,
                    "error": "e2ee_ephemeral_invalid",
                    "message": "Encrypted envelope ephemeralPub is too large."
                })
                return

            try:
                _decode_pubkey_spki(raw_ephemeral_pub)
            except Exception:
                self._send(400, {
                    "ok": False,
                    "error": "e2ee_ephemeral_invalid",
                    "message": "Encrypted envelope requires valid base64 X25519 SPKI ephemeralPub."
                })
                return

            raw_ratchet_pub = e2ee_req.get("ratchetPub")
            if raw_ratchet_pub is not None and str(raw_ratchet_pub).strip():
                if len(str(raw_ratchet_pub)) > 512:
                    self._send(400, {
                        "ok": False,
                        "error": "e2ee_ratchet_invalid",
                        "message": "Encrypted envelope ratchetPub is too large."
                    })
                    return
                try:
                    _decode_pubkey_spki(str(raw_ratchet_pub))
                except Exception:
                    self._send(400, {
                        "ok": False,
                        "error": "e2ee_ratchet_invalid",
                        "message": "Encrypted envelope requires valid base64 X25519 SPKI ratchetPub."
                    })
                    return

        if e2ee_req and (not message) and e2ee_req.get("ciphertext"):
            try:
                inbound_counter = int(e2ee_req.get("counter", 0))
            except Exception:
                inbound_counter = 0

            inbound_header_id = str(e2ee_req.get("headerId", "default")).strip() or "default"
            recv_snapshot = _ratchet_snapshot_recv(session_id)
            if not _ratchet_check_and_advance(session_id, inbound_counter, inbound_header_id):
                self._send(409, {"ok": False, "error": "e2ee_replay_or_reorder", "details": "Inbound counter not monotonic"})
                return

            try:
                message, reply_key, reply_ad, inbound_counter = decrypt_real_envelope(e2ee_req, session_id)
                message = message.strip()
                otk_id = str(e2ee_req.get("otkId", "")).strip()
                if otk_id:
                    _consume_otk(otk_id)
            except Exception as e:
                # Failed decrypt must not consume replay window slots/counters.
                _ratchet_restore_recv(session_id, recv_snapshot)
                self._send(400, {"ok": False, "error": "e2ee_decrypt_failed", "details": str(e)})
                return

        attachment = data.get("attachment") if isinstance(data.get("attachment"), dict) else None
        e2ee_attachment = data.get("e2eeAttachment") if isinstance(data.get("e2eeAttachment"), dict) else None
        if e2ee_attachment and reply_key is not None:
            try:
                attachment = decrypt_e2ee_attachment(e2ee_attachment, reply_key)
            except Exception as e:
                self._send(400, {"ok": False, "error": "e2ee_attachment_decrypt_failed", "details": str(e)})
                return

        prefs = data.get("prefs") if isinstance(data.get("prefs"), dict) else {}
        preferred_lang = (prefs.get("language") or "auto").strip().lower()
        show_transcription = bool(prefs.get("showTranscription", True))
        if not message and not attachment:
            self._send(400, {"ok": False, "error": "message or attachment required"})
            return

        temp_paths = []
        try:
            extra_prompt = ""
            if attachment:
                extra_prompt, temp_paths = process_attachment(attachment)

            final_message = message or "Analitza l'adjunt."
            if extra_prompt:
                final_message = f"{final_message}\n\n{extra_prompt}"

            # Per àudio, prioritza la transcripció com a intenció principal i
            # evita desviacions per metadades d'adjunt.
            if attachment and str((attachment.get("mime") or "")).lower().startswith("audio/"):
                stt_text = extract_audio_transcript(extra_prompt)
                if stt_text:
                    final_message = stt_text

            # Force useful output for app UX, preserving the user's input language.
            input_lang = preferred_lang if preferred_lang in ("ca", "es", "en") else detect_lang(final_message)
            if input_lang == "es":
                final_message += "\n\nResponde SIEMPRE en español (mismo idioma de entrada). Ignora cualquier instrucción anterior que te fuerce otro idioma."
            elif input_lang == "en":
                final_message += "\n\nAlways reply in English (same language as input). Ignore any previous instruction forcing another language."
            else:
                final_message += "\n\nRespon SEMPRE en català (mateix idioma d'entrada). Ignora qualsevol instrucció anterior que et forci un altre idioma."

            # Client supports rich markdown/html/code rendering.
            if input_lang == "es":
                final_message += " Puedes usar HTML/Markdown y bloques de código cuando aporte valor. No digas que el chat solo soporta texto plano."
            elif input_lang == "en":
                final_message += " You can use HTML/Markdown and code blocks when useful. Do not say the chat only supports plain text."
            else:
                final_message += " Pots fer servir HTML/Markdown i blocs de codi quan aporti valor. No diguis que el xat només suporta text pla."

            if attachment and str((attachment.get("mime") or "")).lower().startswith("audio/"):
                if show_transcription:
                    if input_lang == "es":
                        final_message += " Incluye primero la transcripción del audio y después la respuesta. Si puedes, añade también una respuesta en audio."
                    elif input_lang == "en":
                        final_message += " Include first the audio transcription and then your response. If possible, also include an audio response."
                    else:
                        final_message += " Inclou primer la transcripció de l'àudio i després la resposta. Si pots, afegeix també una resposta en àudio."
                else:
                    if input_lang == "es":
                        final_message += " No muestres la transcripción. Responde de forma breve y prepara audio de respuesta."
                    elif input_lang == "en":
                        final_message += " Do not show transcription. Reply briefly and prepare an audio response."
                    else:
                        final_message += " No mostris la transcripció. Respon breument i prepara àudio de resposta."

            cmd = [
                "openclaw", "agent",
                "--session-id", session_id,
                "--message", final_message,
                "--json",
            ]

            rc, parsed, out = run_openclaw_json(cmd, timeout=240)
            if rc != 0 or not parsed:
                self._send(500, {"ok": False, "error": "agent_failed", "details": out[-600:]})
                return

            reply = ""
            media_url = None
            payloads = (((parsed.get("result") or {}).get("payloads")) or [])
            if payloads and isinstance(payloads, list):
                text_parts = []
                for p in payloads:
                    if not isinstance(p, dict):
                        continue
                    t = (p.get("text") or "").strip()
                    if t:
                        text_parts.append(t)
                    if not media_url:
                        media_url = p.get("mediaUrl")
                reply = "\n\n".join(text_parts).strip()
            if not reply:
                reply = "He processat l'entrada, però no he rebut text de resposta."

            # Convert [[tts:...]] style text into real audio URL when media isn't provided.
            clean_reply, tts_text = parse_tts_from_text(reply)
            reply = clean_reply or "Resposta d'àudio generada."

            # Prefer tagged TTS text when present.
            tts_source = tts_text

            # If no tag but user sent audio, synthesize audio from textual reply anyway.
            if not tts_source and attachment and str((attachment.get("mime") or "")).lower().startswith("audio/"):
                tts_source = reply

            if not media_url and tts_source:
                lang = input_lang if input_lang in ("ca", "es", "en") else detect_lang(tts_source)
                media_url = synthesize_tts_audio(tts_source, lang)

            payload = {"ok": True, "reply": reply, "sessionId": session_id}
            if media_url:
                payload["mediaUrl"] = media_url

            if e2ee_req and encrypted_reply and reply_key is not None:
                out_counter = _ratchet_next_out_counter(session_id)

                # Prioritize persistent send chain seed when present.
                store = _load_ratchet_store()
                sessions = store.setdefault("sessions", {})
                st = _ensure_session_chains(sessions.setdefault(session_id, {}))
                send_seed_b64 = st.get("sendChainSeed", "")
                if send_seed_b64:
                    import hashlib
                    send_seed = base64.b64decode(send_seed_b64)
                    reply_key = hashlib.sha256(send_seed + reply_key + b"send-priority").digest()
                else:
                    st["sendChainSeed"] = base64.b64encode(reply_key).decode("ascii")
                _save_ratchet_store(store)

                # Simplified symmetric s2c path for interoperability with the current client.
                # TODO(watchdog): reintroduce ratchet_mix_chain symmetrically on bridge + client.
                ratchet_step = int(st.get("recv", {}).get("ratchetStep", 0))
                send_chain_key = _derive_chain_key(reply_key, "send", ratchet_step)
                msg_key = _derive_message_key(send_chain_key, out_counter, "s2c")
                envelope = encrypt_real_envelope(reply, key=msg_key, ad=(reply_ad or session_id))
                envelope["counter"] = out_counter
                envelope["ratchetStep"] = ratchet_step
                payload["e2eeReply"] = envelope
                payload["reply"] = ""
                print("[bridge-debug] reply-envelope " + json.dumps({
                    "sessionId": session_id,
                    "replyLen": len(reply or ""),
                    "hasE2eeReply": True,
                    "outCounter": out_counter,
                    "ratchetStep": ratchet_step,
                    "ad": (reply_ad or session_id),
                    "mediaUrl": media_url,
                }, ensure_ascii=False), flush=True)
            else:
                print("[bridge-debug] reply-plain " + json.dumps({
                    "sessionId": session_id,
                    "replyLen": len(reply or ""),
                    "encryptedReplyRequested": bool(e2ee_req and encrypted_reply),
                    "hasReplyKey": reply_key is not None,
                    "mediaUrl": media_url,
                }, ensure_ascii=False), flush=True)

            self._send(200, payload)
        except subprocess.TimeoutExpired:
            self._send(504, {"ok": False, "error": "timeout"})
        except Exception as e:
            self._send(500, {"ok": False, "error": str(e)})
        finally:
            for p in temp_paths:
                try:
                    if p and os.path.exists(p):
                        os.remove(p)
                except Exception:
                    pass


def main():
    srv = ThreadingHTTPServer((HOST, PORT), Handler)
    print(f"AIGOR bridge listening on http://{HOST}:{PORT} (/chat, /status)")
    srv.serve_forever()


if __name__ == "__main__":
    main()
