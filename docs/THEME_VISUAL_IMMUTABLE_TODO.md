# THEME_VISUAL_IMMUTABLE_TODO

Creat: 2026-04-04 16:25 UTC
Governança: bloc tancat i immutable. No es poden afegir, dividir, fusionar ni redefinir tasques fora d'aquest llistat sense ordre explícita d'Oriol.
Projecte: aigor-app
Objectiu final: aplicar les millores visuals demanades, generar APK release i copiar-la a `/mnt/aigor/aigor-app/aigor-app-release.apk`.

## Estat global
- STATUS: DONE
- CURRENT_TASK: T9
- PROGRESS: 9/9

## Tasques immutables
- [x] T1 — About: integrar `about.jpg` a la pantalla About amb estil més pro.
- [x] T2 — About: sincronitzar la versió mostrada amb la versió real de l'app.
- [x] T3 — LIGHT conversations: corregir `bgConversations.jpg` amb criteri global neutre/coherent.
- [x] T4 — LIGHT dropdown items: corregir `bgItems.jpg` amb criteri global neutre/coherent.
- [x] T5 — Menu background: fer `bgMenu.jpg` coherent amb light/dark + accent, no gris fix.
- [x] T6 — DARK dropdown items: corregir `darkBgItems.jpg` coherent amb el tema/accent o base fosca comuna.
- [x] T7 — DARK conversations: corregir `darkConversation.jpg` perquè no seleccionats siguin coherents.
- [x] T8 — Build release APK.
- [x] T9 — Copiar APK final a `/mnt/aigor/aigor-app/aigor-app-release.apk` i deixar estat DONE.

## Regles del watchdog
1. Revisar aquest fitxer cada 2 minuts.
2. Validar que `CURRENT_TASK` sempre pertany a T1→T9.
3. Executar només la següent tasca pendent.
4. No afegir noves tasques ni modificar l'abast.
5. Actualitzar aquest fitxer, el log i `/mnt/apps/web/themeStatus.html` a cada execució.
6. Si hi ha blocker, registrar-lo sense inventar accions noves.
