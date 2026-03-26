# E2EE Strict Coverage Matrix — aigor-app (WATCHDOG RESET)

Last updated (UTC): 2026-03-26 17:17
Governance mode: AIGOR-ONLY STRICT TRACKING

| ID | Category | Type | Status | Notes |
|---|---|---|---|---|
| REQ-001 | session_init | REQUIRED | PASS | Inicialització i persistència de sessió validades |
| REQ-002 | send_message | REQUIRED | PASS | Comptador de sortida i xifrat en flux normal |
| REQ-003 | receive_message | REQUIRED | PASS | Decrypt vàlid i validació de sobre xifrat |
| REQ-004 | out_of_order | REQUIRED | PASS | Finestra reorder i anti-replay correctes |
| REQ-005 | skipped_key_recovery | REQUIRED | PASS | Recuperació/consum segur de claus skipped |
| REQ-006 | replay_protection | REQUIRED | PASS | Repeticions bloquejades |
| REQ-007 | counter_enforcement | REQUIRED | PASS | Counter obligatori i rang validat |
| REQ-008 | restart_persistence | REQUIRED | PASS | Estat recuperable després de restart |
| REQ-009 | lifecycle_management | REQUIRED | PASS | Mutacions només en camins vàlids |
| REQ-010 | window_eviction | REQUIRED | PASS | Evicció i límits de finestra estables |
| REQ-011 | malformed_input | REQUIRED | PASS | Rebuig determinista d’entrada malformada |
| REQ-012 | dh_ratchet_step | REQUIRED | PASS | Pas DH i cadenes coherents |
| REQ-013 | state_consistency | REQUIRED | PASS | Sense drift després de fallades de decrypt |
| REG-001 | replay_counter_reuse | REGRESSION | PASS | Regressió replay coberta |
| REG-002 | failed_decrypt_state_drift | REGRESSION | PASS | Regressió de drift coberta |
| REG-003 | large_gap_dos | REGRESSION | PASS | Regressió de gap gran coberta |

## Resum
- Required PASS: **13**
- Required FAIL: **0**
- Regression PASS: **3**
- Regression FAIL: **0**

## Coverage gaps (aigor-app)
1. Formalitzar criteri de tancament de fase com a gate explícit en pipeline.
2. Unificar traça d’evidència per execució watchdog (format canònic únic).
3. Checklist final de fase pendent de marcatge definitiu.
