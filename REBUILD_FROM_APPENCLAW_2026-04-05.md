# appenClaw App rebuild from APPENCLAW App — 2026-04-05

## Objectiu
Reconstruir `appenclaw-app` a partir de `appenclaw-app` com a base funcional sincronitzada amb l'E2EE finalitzada, eliminant rastres de marca APPENCLAW i preparant un bridge exclusiu per provar amb agent `dobby`.

## Procés executat
1. Eliminat completament `appenclaw-app` anterior.
2. Copiat `appenclaw-app` -> `appenclaw-app`.
3. Reanomenat el bridge principal a `scripts/appenclaw_chat_bridge.py`.
4. Rebrand textual massiu de referències:
   - `APPENCLAW` -> `appenClaw`
   - `appenclaw-app` -> `appenclaw-app`
   - `appenclaw-app-chat` -> `appenclaw-app-chat`
   - `appenclaw_prefs` -> `appenclaw_prefs`
   - `appenclaw_app_e2ee` -> `appenclaw_app_e2ee`
   - `APPENCLAW_BRIDGE_*` -> `APPENCLAW_BRIDGE_*`
   - `APPENCLAW_APP_*` -> `APPENCLAW_APP_*`
   - package `com.appenclaw.app` -> `ai.appenclaw.app`
5. Mogut el codi Android de `app/src/main/java/com/appenclaw/app` a `app/src/main/java/ai/appenclaw/app`.
6. Creat entorn exclusiu del bridge a `.env.appenclaw-bridge`.
7. Creat servei user systemd `appenclaw-app-bridge.service`.
8. Build release executada amb `./gradlew assembleRelease`.
9. APK release copiada a `/mnt/apps/appenclaw/apk/appenclaw-app-release.apk`.

## Bridge exclusiu
- Servei: `~/.config/systemd/user/appenclaw-app-bridge.service`
- Port: `8197`
- Session: `appenclaw-app-chat`
- Agent: `dobby`
- Env file: `/home/oriol/.appenclaw/workspace/appenclaw-app/.env.appenclaw-bridge`

## Sortides
- APK: `/mnt/apps/appenclaw/apk/appenclaw-app-release.apk`
- Bridge script: `/home/oriol/.appenclaw/workspace/appenclaw-app/scripts/appenclaw_chat_bridge.py`
- Servei systemd: `/home/oriol/.config/systemd/user/appenclaw-app-bridge.service`

## Nota
Aquesta reconstrucció parteix de la base funcional d'`appenclaw-app`; poden quedar encara referències residuals en documentació històrica o assets no crítics, però el nou objectiu és que `appenclaw-app` sigui la línia viva i provable com a fork net.
