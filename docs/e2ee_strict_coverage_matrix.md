# E2EE Strict Coverage Matrix

Last updated (UTC): 2026-03-27 10:41
Governance mode: STRICT E2EE GOVERNANCE MODE
minimStrictCases baseline: **100 (FROZEN, unchanged)**

| ID | Category | Invariant | Type (REQUIRED / REGRESSION / CANDIDATE) | Required (yes/no) | Regression (yes/no) | Status (PASS / FAIL / MISSING / CANDIDATE) | Scope | Notes |
|---|---|---|---|---|---|---|---|---|
| REQ-001 | session_init | Sessió E2EE inicialitzable amb estat persistent vàlid | REQUIRED | yes | no | PASS | appenclaw-app | Flux base operatiu |
| REQ-002 | send_message | Enviament xifrat incrementa comptador de sortida correctament | REQUIRED | yes | no | PASS | appenclaw-app | Cobert per `e2ee_seed_progress_smoke.py` |
| REQ-003 | receive_message | Recepció xifrada només accepta payload vàlid desencriptable | REQUIRED | yes | no | PASS | appenclaw-app | Cobert per full matrix |
| REQ-004 | out_of_order | Missatges fora d'ordre dins finestra acceptats; replay rebutjat | REQUIRED | yes | no | PASS | appenclaw-app | Cobert per `e2ee_headerid_smoke.py` |
| REQ-005 | skipped_key_recovery | Claus skipped es recuperen/consumeixen sense contaminació entre headers | REQUIRED | yes | no | PASS | appenclaw-app | Cobertura funcional present |
| REQ-006 | replay_protection | Reutilització de counter no processa missatge repetit | REQUIRED | yes | no | PASS | appenclaw-app | Smokes de replay PASS |
| REQ-007 | counter_enforcement | Counter obligatori, positiu i dins rang segur | REQUIRED | yes | no | PASS | appenclaw-app | Cobertura strict present |
| REQ-008 | restart_persistence | Estat persisteix després de restart sense regressions | REQUIRED | yes | no | PASS | appenclaw-app | Cobertura de lifecycle |
| REQ-009 | lifecycle_management | Mutacions d'estat només en camins vàlids/commit controlat | REQUIRED | yes | no | PASS | appenclaw-app | Rollback/no-drift cobert |
| REQ-010 | window_eviction | Finestra limita memòria i rebutja fora de finestra | REQUIRED | yes | no | PASS | appenclaw-app | Window eviction cobert |
| REQ-011 | malformed_input | Envelope malformat rebutjat de forma determinista | REQUIRED | yes | no | PASS | appenclaw-app | Cobertura strict present |
| REQ-012 | dh_ratchet_step | DH ratchet avança només quan toca i reseteja cadenes | REQUIRED | yes | no | PASS | appenclaw-app | DH-step cobert |
| REQ-013 | state_consistency | Fallades decrypt no causen drift ni consumeixen slots replay | REQUIRED | yes | no | PASS | appenclaw-app | Failed-decrypt rollback PASS |
| REQ-014 | attachments_path | Adjunt xifrat manté flux funcional correcte | REQUIRED | yes | no | PASS | appenclaw-app | Attachment smoke PASS |
| REG-001 | replay_protection | Bug real: reutilització de counter | REGRESSION | no | yes | PASS | appenclaw-app | No regressió detectada |
| REG-002 | lifecycle_management | Bug real: drift d'estat després decrypt fallit | REGRESSION | no | yes | PASS | appenclaw-app | Cobert per rollback/no-drift |
| REG-003 | window_eviction | Bug real: DoS per gaps grans | REGRESSION | no | yes | PASS | appenclaw-app | Gap capat a finestra |

## Coverage gaps crítics
Cap gap crític extern de sincronització. Només s'han de considerar gaps reals que afectin el comportament funcional d'`appenclaw-app`.

## Regles de governança aplicades en aquesta execució
- minimStrictCases **no modificat**.
- **0** nous REQUIRED.
- **0** nous REGRESSION.
- No s'usa cap paritat amb altres repos com a criteri de DONE.
