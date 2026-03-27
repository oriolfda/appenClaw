# APP UX & Conversations Status

Last updated: 2026-03-27 21:06 UTC

## Governança
- Font autoritativa de tasques: `docs/APP_UX_CONVERSATIONS_PLAN.md`
- El watchdog no pot afegir ni redefinir tasques.
- Si no hi ha cap tasca activa, ha d'executar la següent tasca pendent del planning.

## Estat global
- Tasques totals: 10
- Tasques completades: 5
- Tasques pendents: 5
- Percentatge completat: 50%

## Tasques executades
- ✅ **1.1 Revisió de l'estat actual de còpia/selecció/codi**
  - Auditoria curta:
    - `ChatAdapter` té punt d'entrada de còpia a `MessageVH` via long-press sobre `messageText`.
    - `RichTextRenderer.bind()` activa `setTextIsSelectable(true)` en text i codi, i aplica estil monospace quan detecta codi.
    - `item_message_user.xml` i `item_message_bot.xml` comparteixen `TextView@messageText` com a punt principal per còpia/selecció.
    - `item_message_html.xml` usa `WebView`, fora del flux directe de `messageText`.
  - Estratègia triada (sense ampliar scope): 1.2 sobre `MessageVH`, 1.3 sobre selectabilitat de `messageText`, 1.4 aprofitant detecció de codi existent a `RichTextRenderer`.

- ✅ **1.2 Còpia de missatge complet**
  - Implementació:
    - Refactor de la còpia a helper dedicat `copyMessageToClipboard(context, text)` dins `ChatAdapter`.
    - `MessageVH` (user/assistant de text) continua amb long-press coherent i ara reutilitza aquest helper.
    - Robustesa: evita copiar missatges buits (`isBlank`) i normalitza final de línia (`trimEnd`) abans de portar al portaretalls.
  - Cobertura del criteri “done”:
    - Còpia fiable de missatge complet per missatges de text user/assistant.
    - Evidència deixada en aquest report.

- ✅ **1.3 Text seleccionable**
  - Implementació:
    - `RichTextRenderer.bind()` ara admet paràmetre `selectable` (per defecte `true`) per controlar selectabilitat segons context d'ús.
    - En missatges de text (sense àudio), `ChatAdapter` força `selectable = true` i manté el long-press de còpia retornant `false` perquè la selecció nativa pugui continuar.
    - En missatges amb àudio, `ChatAdapter` força `selectable = false` per no interferir amb la interacció principal de reproducció (`onClick`) i mantenir còpia ràpida per long-press.
  - Cobertura del criteri “done”:
    - El text és seleccionable en els casos suportats (missatges text user/assistant).
    - No es trenca la interacció principal en missatges amb àudio.

- ✅ **1.4 Còpia de blocs de codi o fragments multilínia**
  - Implementació:
    - `RichTextRenderer` incorpora `extractCopyableCode(raw)` per detectar i extreure codi copiable a partir de blocs fenced (` ```...``` `) o text amb patró clar de codi/indentació.
    - `ChatAdapter` (missatges text sense àudio) ara detecta codi en long-press i, si n'hi ha, copia el fragment de codi (label de clipboard `aigor-code`) en lloc del missatge complet.
    - Si no hi ha codi detectable, es manté el comportament existent de còpia completa del missatge.
  - Cobertura del criteri “done”:
    - Hi ha una via raonable i implementada per copiar codi/fragments multilínia.
    - El flux continua coherent amb la UX de selecció existent.

- ✅ **2.1 Model local mínim de conversa/thread**
  - Implementació:
    - Nou model local persistent a `ConversationStore` amb `ConversationThread(threadId, sessionId, createdAt, updatedAt)`.
    - Persistència via `SharedPreferences` (`chat_threads`, `chat_active_thread_id`) i normalització automàtica d'estat a l'arrencada (`ensureState`).
    - `MainActivity` inicialitza i fixa conversa activa estable (`activeConversation`) des de l'estat persistent.
  - Cobertura del criteri “done”:
    - Existeix model local persistent mínim de conversa/thread.
    - Hi ha conversa activa i identificació estable (`threadId`/`sessionId`) carregada a l'app.

## Tasques pendents
- 2.2 Acció visible de "Nou xat"
- 2.3 Reutilitzar `sessionId` de conversa activa en missatgeria/E2EE
- 3.1 Persistència local d'historial de converses i missatges
- 3.2 UI per veure converses anteriors
- 3.3 Recuperació de context i continuació sobre `sessionId` correcte

## Evidència resumida
- Canvis de codi aplicats a:
  - `app/src/main/java/com/aigor/app/ConversationStore.kt` (nou store/model local de converses amb conversa activa persistent)
  - `app/src/main/java/com/aigor/app/MainActivity.kt` (inicialització de conversa activa persistent)
- Verificació:
  - `./gradlew assembleRelease` ✅ (BUILD SUCCESSFUL)
- Observació (no convertida en tasca): el flux de missatgeria encara usa `sessionId` fix en diversos punts; queda cobert explícitament per la tasca 2.3 del planning.
