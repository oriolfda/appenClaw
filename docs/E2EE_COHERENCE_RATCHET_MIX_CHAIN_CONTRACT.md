# C1 Contracte congelat — `ratchet_mix_chain` simètric (s2c)

Last updated: 2026-04-03 06:55 UTC
Status: FROZEN (C1)
Scope: `s2c` (sense ampliar scope)

## Objectiu
Definir un contracte únic i explícit perquè **bridge** i **app** calculin exactament el mateix `ratchet_mix_chain` al camí `s2c`.

## Contracte únic (normatiu)

### Inputs obligatoris
- `session_id: string`
- `base_key: bytes[32]` (material base de cadena existent)
- `direction: "s2c" | "c2s"` (per C1, focus d'execució: `s2c`)
- `counter: int >= 1`
- Estat persistent de sessió:
  - `rootKeySeed: bytes[32]` (si no existeix, init determinista)
  - `sendChainSeed: bytes[32]` / `recvChainSeed: bytes[32]` (segons direcció)
  - `send.chainCounter` / `recv.chainCounter`

### Derivació (ordre canònic)
1. `root_prev`:
   - si existeix `rootKeySeed`: usar-lo
   - si no existeix: `SHA256(base_key || "root-init")[:32]`
2. `dh_material = SHA256(base_key || direction || ascii(counter))`
3. `(root_next, chain_init) = KDF_RK(root_prev, dh_material)`
4. `current_chain`:
   - si existeix `*ChainSeed` de la direcció: usar-lo
   - altrament: `chain_init`
5. `(chain_next, _message_key_unused) = KDF_CK(current_chain)`
6. Persistència:
   - `*ChainSeed(direction) = chain_next`
   - `rootKeySeed = root_next`
   - `chainCounter(direction) += 1`
7. Output de la funció: `mixed_key = chain_next`

### KDFs i etiquetes
- `KDF_RK` i `KDF_CK` = primitives ja existents al model actual (HMAC-SHA256-based) amb mateix format a ambdós costats.
- No s'introdueixen labels noves fora del que queda aquí especificat.
- `direction` ha de formar part del càlcul de `dh_material` exactament com a string UTF-8 (`"s2c"` / `"c2s"`).

## Invariants (obligatoris)
1. Mateixos inputs + mateix estat inicial ⇒ mateix `mixed_key` i mateix estat final a bridge i app.
2. `s2c` actualitza **només** la branca `send` (`sendChainSeed` + `send.chainCounter`).
3. `c2s` actualitza **només** la branca `recv` (`recvChainSeed` + `recv.chainCounter`).
4. `rootKeySeed` sempre avança a `root_next` a cada invocació vàlida.
5. Cap desviació silenciosa de labels, encoding o ordre de derivació.

## Mapeig explícit bridge/app
- Bridge referència actual: `scripts/appenclaw_chat_bridge.py::_ratchet_mix_chain_key` + `_ratchet_preview_chain_key`.
- App objectiu obligatori per C3: implementar la mateixa seqüència i invariants a `app/src/main/java/com/appenclaw/app/DevE2ee.kt` (i codi relacionat) per `s2c`.

## Fora de scope C1
- No modifica codi de runtime.
- No altera `strictCases` (baseline 100 intacte).
- No amplia casos ni cobreix nous blocs fora C1→C6.
