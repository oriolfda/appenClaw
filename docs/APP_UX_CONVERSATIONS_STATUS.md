# APP UX & Conversations Status

Last updated: 2026-03-27 21:30 UTC

## Governança
- Font autoritativa de tasques: `docs/APP_UX_CONVERSATIONS_PLAN.md`
- El watchdog no pot afegir ni redefinir tasques.
- Si no hi ha cap tasca activa, ha d'executar la següent tasca pendent del planning.

## Estat global
- Tasques totals: 10
- Tasques completades: 10
- Tasques pendents: 0
- Percentatge completat: 100%

## Execució actual (watchdog)
- No s'ha executat cap tasca nova perquè el planning ja està completat (10/10).
- Ordre de prioritat respectat: no hi ha tasques pendents a continuar.

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

- ✅ **2.2 Acció visible de "Nou xat"**
  - Implementació:
    - Nou item visible `menu_new_chat` al menú overflow (`main_overflow_menu.xml`) amb cadenes localitzades.
    - `ConversationStore` incorpora `createNewAndActivate(context)` per crear un `threadId`/`sessionId` nou i activar-lo immediatament.
    - `MainActivity` incorpora `startNewChat()` i, en clicar "Nou xat", canvia la conversa activa, neteja la vista actual i deixa estat de confirmació.
  - Cobertura del criteri “done”:
    - L'usuari pot iniciar un xat nou des de la UI.
    - Es genera `sessionId` nou per a la conversa creada.
    - La conversa activa canvia correctament al nou context.

- ✅ **2.3 Reutilitzar `sessionId` de conversa activa en missatgeria/E2EE**
  - Implementació:
    - `MainActivity` deixa d'usar el valor fix `aigor-app-chat` en els fluxos de `sendToOpenClaw()` i `requestTranscription()`; ara usa `activeConversation.sessionId`.
    - `DevE2ee.encryptAttachment(...)` rep també el `sessionId` actiu en lloc d'un identificador global fix.
    - El comptador de sortida E2EE passa a ser per conversa (`e2ee_send_counter_<sessionId>`) tant en missatgeria com en transcripció.
    - `acceptIncomingCounter(...)` passa a requerir explícitament `sessionId`, evitant fallback implícit a un id global.
  - Cobertura del criteri “done”:
    - El codi d'enviament/transcripció usa el `sessionId` actiu de la conversa.
    - S'elimina la dependència funcional d'un únic `aigor-app-chat` fix per a totes les converses.

- ✅ **3.1 Persistència local d'historial de converses i missatges**
  - Implementació:
    - `ConversationStore` incorpora persistència d'historial per conversa amb claus per `threadId` (`chat_history_thread_<threadId>`).
    - `MainActivity.loadHistory()` i `MainActivity.saveHistory()` passen a carregar/desar contra la conversa activa (`activeConversation.threadId`) en lloc d'una clau global única.
    - Migració compatible: si no existeix historial per thread però sí l'històric legacy `chat_history`, es reutilitza i es copia a la clau del thread actiu.
    - `ConversationStore.saveHistoryJson(...)` actualitza `updatedAt` del thread quan canvia l'historial.
  - Cobertura del criteri “done”:
    - Les converses i els seus missatges locals queden persistits per conversa i sobreviuen a reinicis.
    - Cada conversa conserva el seu historial sense sobreescriure globalment la resta.

- ✅ **3.2 UI per veure converses anteriors i seleccionar-ne una**
  - Implementació:
    - Nou item visible `menu_conversations` a `main_overflow_menu.xml` per obrir el selector de converses.
    - `MainActivity` incorpora `showConversationsSelector()` amb un diàleg (`AlertDialog`) que llista les converses persistides, ordenades per `updatedAt`, i marca la conversa activa.
    - `MainActivity` incorpora `switchToConversation(threadId)` per activar una conversa existent, carregar el seu historial i refrescar l'estat del composer.
    - `ConversationStore` incorpora `activateThread(context, threadId)` per canviar la conversa activa de manera persistent.
  - Cobertura del criteri “done”:
    - Hi ha un selector visible per veure converses anteriors.
    - Es pot obrir una conversa existent i carregar-ne l'historial local.

- ✅ **3.3 Recuperació de context i continuació sobre `sessionId` correcte**
  - Implementació:
    - `sendToOpenClaw(...)` rep ara una instantània explícita de la conversa origen (`ConversationThread`) i envia sempre amb el `sessionId` d'aquella conversa, evitant desalineacions si l'usuari canvia de conversa mentre la resposta és en vol.
    - Quan arriba una resposta i la conversa activa ja és una altra, `MainActivity` no toca la UI de la conversa actual: persisteix la resposta al thread origen amb `persistAssistantReplyForThread(...)`, substituint el `typing` pendent o afegint el missatge final segons calgui.
    - El mateix comportament de persistència s'aplica en errors de xarxa per no perdre continuïtat de context al thread original.
  - Cobertura del criteri “done”:
    - Reobrir una conversa restaura el seu historial amb les respostes associades al thread correcte.
    - Els nous enviaments continuen sobre el `sessionId` correcte de la conversa seleccionada.

## Tasques pendents
- Cap (planning completat)

## Evidència resumida
- Canvis de codi aplicats a:
  - `app/src/main/java/com/aigor/app/ConversationStore.kt`
    - Nova API `activateThread(context, threadId)` per canviar i persistir la conversa activa.
  - `app/src/main/java/com/aigor/app/MainActivity.kt`
    - `sendToOpenClaw(...)` ara treballa amb instantània de conversa origen i session routing estable per thread.
    - Nou helper `persistAssistantReplyForThread(...)` per persistir respostes/errors al thread correcte quan l'usuari canvia de conversa durant una resposta en vol.
    - Nou flux `showConversationsSelector()` + `switchToConversation(threadId)` per llistar i obrir converses existents.
    - Integració del nou selector dins del menú overflow.
  - `app/src/main/res/menu/main_overflow_menu.xml`
    - Nou item visible `menu_conversations`.
  - `app/src/main/res/values*/strings.xml`
    - Noves cadenes UI/estat per al selector i canvi de conversa.
- Verificació:
  - `./gradlew assembleRelease` ✅ (BUILD SUCCESSFUL)
- Pendent UX: reintroduir amb seguretat un botó flotant per anar al final del xat; l'intent actual s'ha revertit perquè provocava crash en obrir l'app.
