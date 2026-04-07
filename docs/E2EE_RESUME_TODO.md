# E2EE Resume TODO (safe stop point)

Last updated: 2026-03-27 10:37 UTC
Branch: `feature/signal-e2ee-phase2`

## Safe-stop status
- El focus actual és exclusivament `appenclaw-app`.
- No s'ha de perseguir sincronització ni paritat amb `appenclaw-app`.
- L'objectiu és tancar desenvolupament funcional i criteri de DONE d'`appenclaw-app`.

## Estat resumit
1. Release gate d'`appenclaw-app` — PASS
2. Full matrix d'`appenclaw-app` — PASS
3. Strict coverage d'`appenclaw-app` — PASS (`strictCases=100`)
4. Build release d'`appenclaw-app` — PASS
5. Documentació — necessita neteja final perquè no arrossegui instruccions antigues de sincronització externa

## Pending tasks (next exact order)
1) Revisar `docs/SIGNAL_E2EE_PHASE2.md` i `docs/e2ee_strict_coverage_matrix.md` perquè reflecteixin només el tancament funcional d'`appenclaw-app`.
2) Verificar que el watchdog i els reports no forcen treball sobre `appenclaw-app`.
3) Executar una passada final de validació funcional sobre el flux real E2EE d'`appenclaw-app`.
4) Determinar si el criteri de DONE ja es pot declarar sense ampliar scope.

## Regles actives
- No crear treball nou només per paritat entre repos.
- No expandir strict coverage amb variants redundants.
- No modificar `minimStrictCases`.
- Només compta com a progrés el que acosta `appenclaw-app` a DONE funcional.

## Resume checklist
- Confirm branch: `feature/signal-e2ee-phase2`
- Començar per validació i neteja de docs
- Si es toca codi, fer-ho en commits petits i justificats
- Validar amb `python3 scripts/e2ee_release_gate_smoke.py`
- Validar build amb `./gradlew :app:assembleRelease`
