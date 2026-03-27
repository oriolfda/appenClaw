# APP UX & Conversations Plan

Objectiu: implementar tres línies de treball a `aigor-app` sobre `main`, sense ampliar scope fora del que està definit aquí.

## Regles de governança
- El watchdog només pot executar tasques definides en aquest fitxer.
- El watchdog té prohibit afegir, inventar, dividir, expandir o redefinir tasques.
- Si detecta una necessitat nova no prevista, ha de deixar-la com a observació al report, però **no** la pot incorporar al planning.
- Si no hi ha cap tasca activa, ha d'executar la següent tasca pendent en ordre.
- Cada execució ha d'actualitzar un fitxer de resultat amb:
  - tasques executades
  - tasques pendents
  - % de completat
  - evidència resumida

## FASE 1 — Còpia de contingut dins del xat

### Tasca 1.1
Descripció: Revisar l'estat actual de `ChatAdapter`, `RichTextRenderer` i els layouts dels missatges per identificar el millor punt d'entrada per a còpia de missatge complet, text seleccionable i blocs de codi.
Done quan:
- hi ha una auditoria curta escrita al report
- s'ha triat l'estratègia concreta d'implementació sense tocar scope

### Tasca 1.2
Descripció: Implementar còpia de missatge complet amb una acció robusta i coherent a la UI.
Done quan:
- es pot copiar un missatge complet de forma fiable
- funciona almenys en missatges user/assistant de text
- queda evidència al report

### Tasca 1.3
Descripció: Fer el text seleccionable on sigui viable sense trencar la UX existent.
Done quan:
- el text es pot seleccionar en els casos suportats
- no es trenca la interacció principal dels missatges
- queda evidència al report

### Tasca 1.4
Descripció: Detectar blocs de codi o fragments clarament copiables i oferir una via raonable de còpia.
Done quan:
- hi ha una estratègia implementada per còpia de codi o fragments multilínia
- queda evidència al report

## FASE 2 — Nou xat = nou context

### Tasca 2.1
Descripció: Definir i implementar el model local mínim de conversa/thread (`threadId`, `sessionId`, metadades bàsiques, conversa activa).
Done quan:
- existeix model local persistent mínim
- hi ha conversa activa i identificació estable
- queda evidència al report

### Tasca 2.2
Descripció: Implementar acció visible de "Nou xat" que creï un context nou i canviï la conversa activa.
Done quan:
- l'usuari pot iniciar un xat nou des de la UI
- es genera `sessionId` nou
- la conversa activa canvia correctament
- queda evidència al report

### Tasca 2.3
Descripció: Garantir que el flux de missatgeria i E2EE reutilitza el `sessionId` de la conversa activa i no un valor fix global.
Done quan:
- el codi d'enviament/transcripció usa el `sessionId` actiu
- no queda dependència funcional d'un únic `aigor-app-chat` fix per a totes les converses
- queda evidència al report

## FASE 3 — Historial i recuperació de context

### Tasca 3.1
Descripció: Persistir l'historial local de converses i missatges associats a cada conversa.
Done quan:
- les converses sobreviuen a reinicis
- cada conversa conserva els seus missatges locals
- queda evidència al report

### Tasca 3.2
Descripció: Implementar UI per veure converses anteriors i seleccionar-ne una.
Done quan:
- hi ha una vista o selector de converses
- es pot obrir una conversa existent
- queda evidència al report

### Tasca 3.3
Descripció: Recuperar correctament el context en reobrir una conversa i continuar sobre el seu `sessionId`.
Done quan:
- reobrir conversa restaura missatges
- nous enviaments continuen sobre el `sessionId` correcte
- queda evidència al report

## BACKLOG PENDENT DESPRÉS DEL TANCAMENT DE FASES

### Tasca B1
Descripció: Reintroduir de forma segura un botó flotant per anar al final del xat quan l'usuari està més amunt de la conversa.
Done quan:
- no provoca crash en obrir l'app
- només apareix quan té sentit
- fa scroll al final correctament
- queda verificat amb build release

## Estat inicial
- Tasques totals: 11
- Tasques completades: 10
- Tasques pendents: 1
- Percentatge completat: 90.9%
