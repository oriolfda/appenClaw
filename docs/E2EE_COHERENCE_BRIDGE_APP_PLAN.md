# E2EE Coherence Plan (Bridge + App) — appenclaw-app

Last updated: 2026-04-03 06:50 UTC
Branch target: `main`
Status: IN PROGRESS

## Objectiu
Implementar de manera **coherent i simultània** el hardening pendent entre bridge i app per al camí `s2c`, sense ampliar scope.

## Regles inamovibles
- Aquest pla és **finit i inamovible**.
- Només es poden executar les tasques definides aquí (C1→C6).
- Prohibit afegir, dividir, fusionar, redefinir o inventar tasques noves.
- Si manca granularitat, reportar blocker i aturar-se.
- No tocar `appenclaw-app`.
- No modificar `minimStrictCases` ni recrear strict cases per inèrcia.

## Tasques (ordre obligatori)

### C1 — Especificació congelada del `ratchet_mix_chain` simètric (s2c)
Done quan:
- queda documentat contracte únic (inputs, outputs, labels/KDF, invariants)
- el contracte és explícitament idèntic per bridge i app

### C2 — Implementació bridge (`scripts/appenclaw_chat_bridge.py`)
Done quan:
- el bridge aplica `ratchet_mix_chain` segons contracte C1 al camí `s2c`
- no hi ha desviacions no documentades respecte C1

### C3 — Implementació app (`DevE2ee.kt` i codi relacionat)
Done quan:
- l’app aplica el mateix `ratchet_mix_chain` segons C1 al camí `s2c`
- no hi ha desviacions no documentades respecte C1

### C4 — Revalidació d’interoperabilitat bridge↔app
Done quan:
- handshake + missatgeria E2EE real bridge↔app passen amb el model nou
- no hi ha regressions funcionals crítiques

### C5 — Gate de seguretat i regressió
Done quan:
- `python3 scripts/e2ee_full_matrix_smoke.py` => PASS
- `python3 scripts/e2ee_release_gate_smoke.py` => PASS
- `./gradlew :app:assembleRelease` => PASS
- baseline `strictCases=100` preservat (o canvi justificat explícitament)

### C6 — Tancament i declaració DONE
Done quan:
- C1..C5 estan en DONE amb evidència
- checkpoint i web d’estat sincronitzats
- report final lliurat

## Criteri global de DONE
Només quan C1, C2, C3, C4, C5 i C6 estan en DONE.
