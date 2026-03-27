# E2EE Hardening Plan — aigor-app

Last updated: 2026-03-27 14:14 UTC
Branch: `feature/signal-e2ee-phase2`
Status: **IN PROGRESS (Signal-grade blockers active)**

## Purpose
Tancar els blockers reals que encara impedeixen afirmar honestament que l'E2EE d'`aigor-app` és Signal-grade.

## Signal-grade blockers actius
### BLOCKER 1 — Primitives finals no implementades
Els docs congelen X25519 + Ed25519 + HKDF-SHA256 + AES-GCM, però el codi verificat encara mostra P-256/ECDH.

### BLOCKER 2 — Double Ratchet no canònic
El model actual continua classificat com `CUSTOM-HARDENED`; per tant encara no es pot afirmar equivalència forta amb Double Ratchet tipus Signal.

## No-scope
- cap treball de sincronització amb `openclaw-app`
- no augmentar `minimStrictCases` per inèrcia
- no recrear els `strictCases=100`
- no obrir tasques noves fora de les definides aquí

## Regla sobre strict cases actuals
Els `strictCases=100` es consideren baseline vàlid.
Només es poden tocar si cal cobrir un invariant nou real dels blocs següents i amb justificació explícita.

## Llista exacta de blocs i tasques

### BLOC_1_IMPLEMENT_FINAL_PRIMITIVES
Status: **PENDING**

#### Tasca 1.1
Descripció: Auditar tots els punts del codi on encara hi ha P-256/ECDH i inventariar la migració requerida.
Fitxers objectiu:
- `app/src/main/java/com/aigor/app/DevE2ee.kt`
- `app/src/main/java/com/aigor/app/E2eeKeyManager.kt`
- `scripts/aigor_chat_bridge.py`
Done quan:
- queda escrit un inventari exhaustiu de punts a migrar a X25519
- queda clar què es manté en Ed25519/HKDF/AES-GCM

#### Tasca 1.2
Descripció: Migrar el client (`DevE2ee.kt` i codi relacionat) de P-256/ECDH a X25519.
Done quan:
- el client ja no usa `EC`/`ECDH`/P-256 per DH principal
- l'handshake i el flux E2EE del client funcionen amb X25519

#### Tasca 1.3
Descripció: Migrar el bridge a X25519 per al mateix flux.
Done quan:
- `scripts/aigor_chat_bridge.py` ja no usa `SECP256R1` per DH principal del protocol
- el bundle/handshake/derivació inicial queden alineats amb la decisió final de primitives

#### Tasca 1.4
Descripció: Verificar alineació docs ↔ codi del stack final.
Done quan:
- docs i codi diuen el mateix stack final
- ja no hi ha contradicció entre X25519 decidit i P-256 implementat

### BLOC_2_DOUBLE_RATCHET_CANONICALIZATION
Status: **PENDING**

#### Tasca 2.1
Descripció: Auditar el model actual i llistar exactament les diferències amb un Double Ratchet canònic.
Done quan:
- hi ha una taula explícita `actual vs objectiu`
- es llisten les parts custom que impedeixen afirmar equivalència canònica

#### Tasca 2.2
Descripció: Definir model final explícit de `KDF_RK`, `KDF_CK`, `rootKey`, `sendChainKey`, `recvChainKey`, `messageKey`.
Done quan:
- hi ha una definició escrita inequívoca del model final
- queda clar com evolucionen claus per missatge i per DH step

#### Tasca 2.3
Descripció: Implementar/refinar el ratchet perquè deixi de ser `CUSTOM-HARDENED` i passi a model canònic o equivalent fortament justificat.
Done quan:
- el codi reflecteix el model definit a 2.2
- les parts crítiques ja no depenen d'estructura/KDF ad hoc sense justificació

#### Tasca 2.4
Descripció: Revalidar replay, skipped keys, rollback i restart persistence sobre el model final del ratchet.
Done quan:
- els invariants forts continuen PASS
- el baseline de proves es manté o s'ajusta només amb justificació explícita

### BLOC_3_FINAL_SIGNAL_GRADE_VALIDATION
Status: **PENDING**

#### Tasca 3.1
Descripció: Verificar els punts crítics de Signal-grade sobre codi real.
Checklist obligatòria:
1. X25519 real implementat
2. handshake final coherent i verificat
3. Double Ratchet canònic o equivalent fort justificat
4. no reutilització de `messageKey`
5. replay/out-of-order/rollback/restart persistence correctes
6. custòdia forta de claus al client
7. docs i codi alineats
8. evidència final repetible
Done quan:
- els 8 punts es poden marcar com a complerts amb evidència

#### Tasca 3.2
Descripció: Executar gate final i declarar DONE.
Done quan:
- `python3 scripts/e2ee_release_gate_smoke.py` => PASS
- build release => PASS
- no hi ha blockers crítics oberts
- es pot afirmar honestament Signal-grade

## Criteri global de DONE
Només es pot declarar quan:
- BLOC_1 = DONE
- BLOC_2 = DONE
- BLOC_3 = DONE
- `strictCases=100` es manté o qualsevol canvi queda justificat
- no hi ha contradicció entre docs i codi
