# E2EE AEAD BAD_DECRYPT Remediation TODO — appenclaw-app

Last updated: 2026-04-03 17:48 UTC
Branch target: `main`
Status: IN PROGRESS

## Objectiu
Resoldre l'error reportat a l'app a `/mnt/appenclaw/appenclaw-app/error.jpg`:
- `[E2EE] Error desencriptant resposta: AEADBadTagException ... BAD_DECRYPT`

## Hipòtesis de causa (congelades per a aquest bloc)
1. **Desalineació de direcció al ratchet mix chain a l'app**
   - `DevE2ee.decryptWithKey(...)` demana clau `ratchetMixChainKey(sessionId, baseKey, "s2c", counter)`.
   - Dins `ratchetMixChainKey(...)`, `isRecv = direction == "c2s"`, de manera que `"s2c"` entra pel camí de `sendChainSeed` en lloc de `recvChainSeed`.
   - Això és una causa probable directa de clau incorrecta i `AEADBadTagException`.
2. **Retorn de chain key en lloc de message key a l'app**
   - `kdfCk(...)` retorna `(chainNext, messageKey)` però `ratchetMixChainKey(...)` retorna `chainNext` i no `messageKey`.
   - Si el bridge xifra amb una clau derivada equivalent a message key/next chain diferent del que usa l'app, el tag GCM fallarà.
3. **Persistència/avanç de counters i seeds inconsistent entre bridge i app**
   - el bridge prioritza `sendChainSeed` persistent i fa `_ratchet_mix_chain_key(session_id, reply_key, "s2c", out_counter)` abans de xifrar.
   - l'app incrementa `sendChainCounter/recvChainCounter` però no fa servir aquests comptadors per validar alineació amb la clau retornada.
4. **Inconsistència d'AD/sessionId al camí real**
   - `decryptWithKey(...)` usa `ad` com a `sessionId` efectiu si hi és, i si no mira `sessionId`.
   - Si l'AD rebut no coincideix exactament amb el que el bridge usa a l'envelope, AES-GCM donarà `BAD_DECRYPT`.

## Regles inamovibles
- Aquest bloc és **finit i immutable**.
- Només es poden executar les tasques definides aquí (A1→A6).
- Prohibit afegir, dividir, fusionar, redefinir o inventar tasques noves sense autorització explícita d'Oriol.
- Si manca granularitat, reportar blocker i aturar-se.
- No tocar `appenclaw-app`.
- No modificar `strictCases=100` sense justificació tècnica explícita.

## Tasques (ordre obligatori)

### A1 — Reproducció controlada i aïllament del camí fallit
Done quan:
- es reprodueix el `BAD_DECRYPT` en un smoke o escenari controlat equivalent,
- queda identificat si el cas fallit és per direcció, message key vs chain key, AD/sessionId, o persistència,
- s'escriu evidència mínima reproduïble al checkpoint.

### A2 — Instrumentació diagnòstica mínima bridge+app
Done quan:
- s'afegeix instrumentació temporal mínima als punts de derivació/decrypt rellevants,
- la instrumentació no altera el contracte criptogràfic ni el baseline `strictCases=100`,
- permet comparar de manera explícita direcció, counter, sessionId/ad i tipus de clau derivada.

### A3 — Fix mínim coherent del camí s2c de decrypt a l'app
Done quan:
- es corregeix la causa arrel confirmada a `DevE2ee.kt` i/o codi estrictament relacionat,
- el camí `s2c` usa la semàntica correcta de recepció i la clau correcta per desencriptar,
- no s'introdueixen desviacions de scope fora del bug AEAD.

### A4 — Revalidació dirigida del bug reportat
Done quan:
- el cas reproduït a A1 deixa de fallar,
- desapareix el `AEADBadTagException` a l'escenari objectiu,
- passen els smokes dirigits relacionats amb `next_counter`, `dh_step`, attachments o AD/header si són rellevants.

### A5 — Gate complet de regressió i release
Done quan:
- `python3 scripts/e2ee_full_matrix_smoke.py` => PASS,
- `python3 scripts/e2ee_release_gate_smoke.py` => PASS,
- `./gradlew :app:assembleRelease` => PASS,
- baseline `strictCases=100` preservat.

### A6 — Tancament, APK i declaració DONE
Done quan:
- checkpoint + web queden sincronitzats amb A1..A5,
- l'APK release queda copiat a `/mnt/appenclaw/appenclaw-app/appenclaw-app-release.apk`,
- s'envia notificació per Telegram amb estat final i evidència resumida.

## Criteri global de DONE
Només quan A1, A2, A3, A4, A5 i A6 estan en DONE.
