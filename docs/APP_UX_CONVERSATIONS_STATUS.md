# APP UX & Conversations Status

Last updated: 2026-03-27 20:58 UTC

## Governança
- Font autoritativa de tasques: `docs/APP_UX_CONVERSATIONS_PLAN.md`
- El watchdog no pot afegir ni redefinir tasques.
- Si no hi ha cap tasca activa, ha d'executar la següent tasca pendent del planning.

## Estat global
- Tasques totals: 10
- Tasques completades: 1
- Tasques pendents: 9
- Percentatge completat: 10%

## Tasques executades
- ✅ **1.1 Revisió de l'estat actual de còpia/selecció/codi**
  - Auditoria curta:
    - `ChatAdapter` ja té punt d'entrada de còpia de missatge complet a `MessageVH` via `setOnLongClickListener` sobre `messageText` (clipboard + toast), però només cobreix aquest tipus de cel·la.
    - `RichTextRenderer.bind()` ja activa `setTextIsSelectable(true)` tant en codi com en text normal, i aplica format monospace + scroll horitzontal quan detecta codi.
    - Layouts `item_message_user.xml` i `item_message_bot.xml` comparteixen `TextView@messageText`, que és el punt més estable per unificar UX de còpia/selecció en text user/assistant.
    - `item_message_html.xml` usa `WebView` (`htmlWeb`), així que la còpia directa des de text no segueix el mateix camí que `messageText`.
  - Estratègia concreta triada (sense ampliar scope):
    1) **Tasca 1.2**: consolidar la còpia de missatge complet al binding de `MessageVH` (user/assistant text), mantenint long-press com a acció robusta i coherent.
    2) **Tasca 1.3**: ajustar selectabilitat perquè sigui viable sense trencar interacció principal (tap de missatge/àudio), partint de `RichTextRenderer` + `messageText`.
    3) **Tasca 1.4**: aprofitar detecció existent de codi a `RichTextRenderer` (`codeFenceRegex`/`looksLikeCode`) per oferir via raonable de còpia en fragments multilínia.

## Tasques pendents
- 1.2 Còpia de missatge complet
- 1.3 Text seleccionable
- 1.4 Còpia de blocs de codi o fragments multilínia
- 2.1 Model local mínim de conversa/thread
- 2.2 Acció visible de "Nou xat"
- 2.3 Reutilitzar `sessionId` de conversa activa en missatgeria/E2EE
- 3.1 Persistència local d'historial de converses i missatges
- 3.2 UI per veure converses anteriors
- 3.3 Recuperació de context i continuació sobre `sessionId` correcte

## Evidència resumida
- Revisats fitxers:
  - `app/src/main/java/com/aigor/app/ChatAdapter.kt`
  - `app/src/main/java/com/aigor/app/RichTextRenderer.kt`
  - `app/src/main/res/layout/item_message_user.xml`
  - `app/src/main/res/layout/item_message_bot.xml`
  - `app/src/main/res/layout/item_message_html.xml`
  - `app/src/main/res/layout/item_message_audio.xml`
  - `app/src/main/res/layout/item_message_image_user.xml`
- Confirmat punt d'entrada existent i estratègia d'implementació per les tasques 1.2–1.4 dins del scope congelat.
- Observació (no convertida en tasca): la còpia en missatges renderitzats com HTML via `WebView` pot requerir tractament específic si es vol paritat UX completa més endavant.