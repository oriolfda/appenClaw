# APP UX & Conversations Status

Last updated: 2026-03-27 21:01 UTC

## Governança
- Font autoritativa de tasques: `docs/APP_UX_CONVERSATIONS_PLAN.md`
- El watchdog no pot afegir ni redefinir tasques.
- Si no hi ha cap tasca activa, ha d'executar la següent tasca pendent del planning.

## Estat global
- Tasques totals: 10
- Tasques completades: 2
- Tasques pendents: 8
- Percentatge completat: 20%

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

## Tasques pendents
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
- Canvi de codi aplicat a:
  - `app/src/main/java/com/aigor/app/ChatAdapter.kt` (helper de còpia + ús des de long-press de `MessageVH`).
- Observació (no convertida en tasca): la còpia en missatges HTML renderitzats amb `WebView` no comparteix el mateix flux de còpia de `messageText`.