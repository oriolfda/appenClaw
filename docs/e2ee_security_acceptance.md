# E2EE Security Acceptance Criteria — appenclaw-app

Last updated: 2026-03-27 14:14 UTC
Status: **ACTIVE**

## Rule 0 — baseline preservation
- `strictCases=100` es considera baseline vàlid.
- No s'han de recrear des de zero.
- No s'han d'expandir sense invariant nou justificat.

## Signal-grade blocking criteria
No es pot declarar `DONE` mentre falli algun d'aquests punts:

1. **Primitives finals realment implementades**
- X25519 per DH principal
- Ed25519 per signatures
- HKDF-SHA256
- AES-GCM o AEAD equivalent documentat

2. **Handshake final coherent i verificat**
- identity / signed prekey / one-time prekey / ephemeral
- verificació real de signatura SPK
- abort si la verificació falla
- consum correcte de l'OTK

3. **Double Ratchet canònic o equivalent fort**
- model explícit de `KDF_RK / KDF_CK / rootKey / sendChainKey / recvChainKey / messageKey`
- evolució clara per missatge i per DH step
- ja no classificat com `CUSTOM-HARDENED` sense equivalència forta justificada

4. **No reutilització de message keys**
- `messageKey` única per direcció/counter/ratchetStep

5. **Replay / out-of-order / rollback / restart persistence**
- invariants forts PASS

6. **Custòdia forta de claus al client**
- Android Keystore / model final aprovat

7. **Docs i codi alineats**
- cap contradicció entre stack decidit i stack implementat

8. **Evidència final repetible**
- release gate PASS
- build release PASS
- verificació final manual coherent amb el codi

## AEAD BAD_DECRYPT acceptance addendum
Aquest addendum és obligatori per al bloc de remediació AEAD.

No es pot declarar resolt el bug reportat a `error.jpg` mentre no es compleixi tot això:
- el cas reproduït del `AEADBadTagException / BAD_DECRYPT` queda identificat i deixa de fallar,
- queda evidència de la causa arrel triada entre: direcció incorrecta, message key vs chain key, persistència/counters o AD/sessionId,
- el camí nominal `s2c` no produeix `AEADBadTagException` en la revalidació dirigida,
- `python3 scripts/e2ee_full_matrix_smoke.py` => PASS,
- `python3 scripts/e2ee_release_gate_smoke.py` => PASS,
- `./gradlew :app:assembleRelease` => PASS,
- `strictCases=100` es preserva.

## Change control
Qualsevol canvi en strict cases ha d'indicar explícitament:
- invariant afectat
- motiu del canvi
- evidència
- impacte sobre baseline
