# E2EE App Ratchet Persistence TODO — appenclaw-app

Last updated: 2026-04-03 18:59 UTC
Branch target: `main`
Status: IN PROGRESS

## Objectiu
Resoldre el `AEADBadTagException / BAD_DECRYPT` real observat a l'app quan el bridge continua amb una cadena `s2c` viva però l'app entra a decryptar amb estat de ratchet buit o no rehidratat.

## Diagnòstic congelat
Evidència real recollida:
- App: en un `s2c counter` avançat, `hasSendSeed=false`, `hasRecvSeed=false`, `sendCtr=0`, `recvCtr=0`.
- Bridge: per la mateixa sessió i respostes avançades, `hasRecvSeed=true`, `hasSendSeed=true` i `mixedKeyFp` coherent amb cadena ja avançada.

Conclusió congelada per a aquest bloc:
- la causa arrel més probable és **manca de persistència/rehidratació del ratchet state per sessió a l'app**.

## Regles inamovibles
- Aquest bloc és finit i immutable.
- Només es poden executar les tasques definides aquí (P1→P6).
- Prohibit afegir, dividir, fusionar, redefinir o inventar tasques noves sense autorització explícita d'Oriol.
- Si manca granularitat, reportar blocker i aturar-se.
- No tocar `appenclaw-app`.
- No modificar `strictCases=100` sense justificació tècnica explícita.

## Tasques (ordre obligatori)

### P1 — Especificació de persistència i bootstrap de sessió
Done quan:
- queda definit on i com es persisteix `rootKeySeed`, `recvChainSeed`, `sendChainSeed`, `recvChainCounter`, `sendChainCounter` per `sessionId`,
- queda definit el comportament de bootstrap només per primer ús real de sessió,
- queda documentat quan es rehidrata i quan es reseteja estat.

### P1_SPEC_OUTPUT (2026-04-03 19:01 UTC)
Especificació executable i congelada per a P1 (sense implementar encara codi de P2):

- **Store de persistència per sessió (`sessionId`)**
  - Clau lògica: `ratchet_state::<sessionId>`.
  - Camps obligatoris persistits:
    - `rootKeySeed` (Base64)
    - `recvChainSeed` (Base64)
    - `sendChainSeed` (Base64)
    - `recvChainCounter` (int >= 0)
    - `sendChainCounter` (int >= 0)
    - `updatedAtMs` (long, telemetria)
  - Si no existeix registre per `sessionId`, es considera sessió no bootstrapada.

- **Bootstrap (només primer ús real de sessió)**
  - Condició d'entrada: no existeix `ratchet_state::<sessionId>`.
  - En primer decrypt/encrypt vàlid de sessió, inicialitzar estat amb el contracte coherent actual:
    - `rootKeySeed` derivat del primer `KDF_RK` aplicable al flux real.
    - `recvChainSeed` i/o `sendChainSeed` segons direcció usada al primer missatge real.
    - counters inicialitzats al primer valor coherent processat (no forçar reset a 0 si el missatge processat ja implica avanç).
  - Després del primer cicle exitós, persistència immediata atòmica de l'estat.

- **Rehidratació (abans de decrypt `s2c`)**
  - A cada entrada de decrypt amb `sessionId`, carregar primer l'estat persistent de `ratchet_state::<sessionId>`.
  - Si existeix estat, queda prohibit entrar al camí amb `hasRecvSeed=false` i `recvCtr=0`.
  - La derivació de `messageKey/chainNext` s'ha de fer des de seeds/counters rehidratats, no des d'estat buit.

- **Reset d'estat (condicions permeses)**
  - Només en invalidació explícita de sessió (`sessionId` nou/rotat, logout/clear-state explícit, o corrupció detectable de registre).
  - En reset, eliminar completament `ratchet_state::<sessionId>` i registrar motiu diagnòstic.
  - Prohibit reset implícit silenciós en errors transitoris de decrypt.

- **Traça diagnòstica mínima exigida per P2/P3**
  - Log a cada decrypt `s2c`: `sessionId`, `hasPersistentState`, `hasRecvSeed`, `recvCtr`, `hasSendSeed`, `sendCtr`.
  - Objectiu de validació: en sessió avançada amb estat existent, no tornar a observar estat buit.

### P2 — Implementació de persistència/rehidratació a l'app
Done quan:
- l'app persisteix l'estat de ratchet per `sessionId`,
- l'app rehidrata l'estat abans de decryptar `s2c`,
- els logs diagnòstics permeten verificar que una sessió avançada no entra amb estat buit si ja existeix estat persistent.

### P3 — Revalidació real amb traça diagnòstica
Done quan:
- el cas real deixa de mostrar `hasRecvSeed=false/recvCtr=0` en una sessió avançada on hi havia estat,
- desapareix el `BAD_DECRYPT` en la prova real objectiu o es redueix a un altre blocker clarament identificat,
- hi ha evidència creuada app + bridge del mateix `sessionId/counter`.

### P4 — Smokes dirigits i regressió del flux de sessió
Done quan:
- passen els smokes dirigits rellevants de `s2c`, `next_counter`, `dh_step` i qualsevol smoke específic de persistència/restart si existeix o s'afegeix dins l'scope,
- `strictCases=100` es manté intacte.

### P5 — Gate complet i build release
Done quan:
- `python3 scripts/e2ee_full_matrix_smoke.py` => PASS,
- `python3 scripts/e2ee_release_gate_smoke.py` => PASS,
- `./gradlew :app:assembleRelease` => PASS.

### P6 — APK, validació final i declaració DONE
Done quan:
- l'APK release queda copiat a `/mnt/appenclaw/appenclaw-app/appenclaw-app-release.apk`,
- checkpoint + web sincronitzats amb P1..P5,
- validació final real confirmada sobre el dispositiu sense `BAD_DECRYPT` en el cas objectiu.

## Criteri global de DONE
Només quan P1, P2, P3, P4, P5 i P6 estan en DONE.
