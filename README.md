# aigor-app

Android app per comunicar-se amb un assistent OpenClaw.

## Quick start
1. Clona el repo
2. Configura Android SDK/JDK17
3. `./gradlew assembleRelease`
4. Instal·la APK (`app/build/outputs/apk/release/app-release.apk`)
5. A Settings posa endpoint + token del bridge

## Documentació completa
- `docs/OPENCLAW_AI_REPLICA.md` — guia pas a pas per assistents OpenClaw AI
- `docs/LOCALIZATION.md` — localització de la interfície
- `docs/templates/ui-locale-template.json` — plantilla per afegir idiomes

## Funcionalitats
- Xat text
- Àudio (gravar/enviar/reproduir)
- Imatge i vídeo adjunts amb preview
- Render HTML/codi
- Temes i idiomes UI
