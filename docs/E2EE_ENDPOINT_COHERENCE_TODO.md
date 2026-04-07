# E2EE Endpoint Coherence TODO — appenclaw-app

Last updated: 2026-04-03 19:27 UTC
Branch target: `main`
Status: IN PROGRESS

## Objectiu
Estendre la lògica E2EE ja corregida perquè sigui coherent a tots els endpoints/subfluxos rellevants d'`appenclaw-app`, incloent text, àudio/transcripció, attachments i qualsevol resposta E2EE associada, evitant `BAD_DECRYPT` parcials per endpoint.

## Diagnòstic congelat
- El bloc P1→P6 ha resolt el cas real principal de persistència/rehidratació del ratchet a l'app per al flux principal.
- Oriol reporta que, en provar un àudio, el flux principal ha respost OK però la transcripció d'àudio no funciona i al log apareix també `BAD_DECRYPT` en aquesta crida.
- Hipòtesi congelada: existeixen endpoints/subfluxos que encara no reutilitzen exactament la mateixa lògica de persistència/rehidratació/derivació E2EE que el flux principal resolt.

## Regles inamovibles
- Aquest bloc és finit i immutable.
- Només es poden executar les tasques definides aquí (E1→E6).
- Prohibit afegir, dividir, fusionar, redefinir o inventar tasques noves sense autorització explícita d'Oriol.
- Si manca granularitat, reportar blocker i aturar-se.
- No tocar `appenclaw-app`.
- No modificar `strictCases=100` sense justificació tècnica explícita.

## Tasques (ordre obligatori)

### E1 — Diagnòstic d'endpoints/subfluxos afectats
Done quan:
- queda identificat quins endpoints o subfluxos encara fallen o divergeixen (text, àudio/transcripció, attachments, altres),
- queda clar per a cada cas si comparteix o no el mateix camí E2EE del flux principal.

### E2 — Inventari de punts de xifrat/desxifrat i estat compartit
Done quan:
- queda mapejat on es deriva, persisteix, rehidrata i consumeix estat E2EE a cada endpoint/subflux,
- es documenten divergències reals respecte el flux principal corregit.

### E3 — Unificació de la lògica E2EE entre endpoints
Done quan:
- els endpoints/subfluxos afectats reutilitzen la mateixa lògica correcta de persistència/rehidratació/derivació per `sessionId`,
- no queden camins paral·lels inconsistents per al mateix tipus de resposta E2EE.

### E4 — Revalidació real multi-endpoint
Done quan:
- text OK,
- àudio + transcripció OK,
- attachments OK si afecten,
- sense `BAD_DECRYPT` als endpoints coberts en proves reals i/o smokes dirigits.

### E5 — Gate complet i regressió
Done quan:
- `python3 scripts/e2ee_full_matrix_smoke.py` => PASS,
- `python3 scripts/e2ee_release_gate_smoke.py` => PASS,
- `./gradlew :app:assembleRelease` => PASS,
- `strictCases=100` preservat.

### E6 — APK final, validació i DONE
Done quan:
- APK release copiat a `/mnt/appenclaw/appenclaw-app/appenclaw-app-release.apk`,
- checkpoint + web sincronitzats,
- validació final real dels endpoints coberts sense `BAD_DECRYPT` residual.

## Criteri global de DONE
Només quan E1, E2, E3, E4, E5 i E6 estan en DONE.
