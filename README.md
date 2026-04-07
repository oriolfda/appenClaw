# appenClaw

> **Avís important sobre el desenvolupament i la implementació E2EE:** aquesta app ha estat desenvolupada íntegrament o principalment per un assistent AI sota supervisió i indicacions humanes. La implementació E2EE del projecte tampoc no està certificada, auditada ni validada per cap entitat externa independent. No s'ha de presentar com una implementació canònica o certificada de Signal. Qualsevol ús del projecte, de l'APK o de les seves funcions criptogràfiques es fa sota el risc i responsabilitat de qui decideixi utilitzar-lo.

**appenClaw** és una app Android per connectar-se a un agent OpenClaw per text, àudio, imatges i vídeo.

Aquest repositori suporta **dos modes d'ús**:

1. **Fer servir appenClaw tal com és**
   - descarregar una APK ja compilada
   - instal·lar-la
   - configurar endpoint + token
   - usar-la amb el bridge base
2. **Crear una assistant-app personalitzada**
   - rebrand de nom, icona, idioma, tema i detalls del bridge
   - compilació d'un APK propi per a l'agent de cada usuari

---

## Què inclou l'app

- xat de text per comunicar-se amb el teu agent OpenClaw
- gravació i enviament d'àudio
- adjunts d'imatge i vídeo
- reproducció d'àudio al xat
- xifrat d'extrem a extrem (E2EE) per a missatges i adjunts, amb implementació pròpia basada en el model de Signal (**vegeu l'avís inicial**)
- render HTML/codi
- temes visuals
- localització UI
- suport de bridge amb endpoint + token

---

## Ruta A — Fer servir appenClaw as-is

### Missatge que l'humà ha de donar al seu OpenClaw

Copia i enganxa una instrucció com aquesta:

> "Vull fer servir appenClaw tal com és, sense personalitzar-la ni recompilar-la. Fes servir com a referència canònica `https://github.com/oriolfda/appenClaw` i segueix estrictament `docs/APPENCLAW_AI_REPLICA.md` en mode AS-IS. No facis rebrand ni rebuild de l'APK si no és necessari. Abans d'instal·lar o crear cap servei, verifica si el bridge d'appenClaw ja existeix o ja està corrent en aquesta màquina i, si és així, reutilitza'l o adapta'l en lloc de duplicar-lo. Si jo no especifico el port, pots decidir tu un port adequat que no entri en conflicte i m'ho has d'indicar explícitament. Prepara el bridge, deixa'm un endpoint + token funcionals, explica'm si cal nginx/firewall/domini per accés extern, i indica'm com descarregar i configurar l'APK `appenClaw-release.apk`."

### Què fa l'humà

#### 1) Descarregar i instal·lar l'APK
No cal Android SDK ni compilació local.

L'humà només ha de:
- descarregar `appenClaw-release.apk`
- instal·lar-la al mòbil
- obrir **Settings**
- posar:
  - endpoint del bridge
  - token
  - idioma d'interfície si ho vol canviar

#### 2) Decidir com s'hi accedirà
- **Només LAN**
  - el mòbil i el servidor han d'estar a la mateixa xarxa
  - usa la IP local del servidor
- **Accés des d'internet**
  - cal domini o subdomini
  - `nginx` o reverse proxy equivalent
  - TLS/HTTPS
  - ports oberts a firewall/router

#### 3) Decidir el port del bridge
L'humà pot:
- indicar un port concret, o
- deixar que l'agent AI triï un port lliure adequat

Si l'AI tria el port, ha de:
- comprovar que no entri en conflicte amb serveis existents
- documentar quin port ha escollit
- dir clarament a l'humà quin endpoint final ha d'usar

#### 4) Configurar xarxa i publicació
Si el bridge serà accessible des de fora de la LAN:
- apunta el domini/subdomini a la IP pública
- obre el port al router/firewall
- posa `nginx` davant del bridge si vols TLS i una URL pública neta
- mantén sempre actiu el token del bridge

#### 5) Permisos que ha de tenir l'assistent OpenClaw
Si vols que l'assistent pugui deixar el bridge instal·lat i persistent, ha de tenir permisos suficients per fer les accions necessàries al host, per exemple:
- crear o editar fitxers de configuració del bridge
- crear o editar un servei `systemd` (user o system)
- arrencar, aturar, reiniciar i consultar l'estat del servei
- llegir o reservar un port lliure
- si cal accés extern: tocar configuració de `nginx` i/o explicar exactament què has de fer tu manualment
- si cal obrir ports al firewall, tenir permisos per fer-ho o bé deixar-te la instrucció exacta

Si l'assistent no té aquests permisos, almenys ha de poder:
- preparar tots els fitxers
- indicar les comandes exactes que has d'executar tu
- explicar què falta per completar el desplegament

#### 6) Provar flux bàsic
- xat text
- enviament d'àudio
- reproducció d'àudio
- imatge/vídeo
- estat/context

### Què ha de fer l'agent AI
L'agent ha de seguir:
- `docs/APPENCLAW_AI_REPLICA.md`

Per al mode **as-is**, l'agent **no necessita Android toolchain** si no s'ha de recompilar res.

Només ha de:
1. preparar l'entorn host del bridge
2. crear o adaptar el bridge base `scripts/appenclaw_chat_bridge.py`
3. generar fitxer d'entorn del bridge
4. configurar servei persistent (`systemd` recomanat)
5. indicar a l'humà endpoint + token finals
6. validar text, adjunts i àudio

---

## Ruta B — Crear una assistant-app personalitzada a partir de appenClaw

### Missatge que l'humà ha de donar al seu OpenClaw

Copia i enganxa una instrucció com aquesta:

> "Vull crear una assistant-app personalitzada a partir de appenClaw. Fes servir com a referència canònica `https://github.com/oriolfda/appenClaw` i segueix estrictament `docs/APPENCLAW_AI_REPLICA.md` en mode personalitzat. Fes intake interactiu del nom, icona, idioma, tema, preferències STT/TTS, agent objectiu, port del bridge i model de desplegament. Després personalitza un repo de treball adequat, compila una APK release, prepara el bridge específic i deixa'm instruccions clares per instal·lar-la i fer-la servir."

### Què fa l'humà

#### 1) Preparar GitHub
Recomanació: que el repo sigui **de l'usuari humà**, no de l'assistent.

Flux recomanat:
1. crea un repo propi a GitHub
2. afegeix una **deploy key**
3. si l'agent ha de fer `push`, activa **Allow write access**
4. comparteix amb l'agent:
   - URL del repo
   - ubicació de la clau SSH al host

#### 2) Preparar la informació de personalització
Abans de donar feina a l'agent, l'humà hauria de tenir clar:
- nom visible de l'app
- icona (PNG quadrat, idealment 1024x1024)
- idioma UI per defecte
- tema de colors
- si vol mostrar o no transcripcions STT
- política TTS:
  - automàtica per idioma
  - o veu fixa específica
- agent objectiu
- port del bridge
- si serà només LAN o internet-accessible
- si vol domini/subdomini + `nginx`

#### 3) Preparar entorn de publicació si cal
Si es vol accés extern:
- domini/subdomini
- `nginx` o reverse proxy equivalent
- TLS/HTTPS
- ports oberts a firewall/router
- validació mínima de seguretat abans d'exposar el bridge

#### 4) Provar l'APK personalitzat
Quan l'agent et doni l'APK:
- instal·la'l
- comprova nom + icona
- configura endpoint + token
- prova text, àudio, imatge, vídeo
- reporta incidències visuals o funcionals

### Què ha de fer l'agent AI
L'agent ha de seguir:
- `docs/APPENCLAW_AI_REPLICA.md`

En el mode **personalitzat**, l'agent sí que ha de:
1. fer intake interactiu amb l'humà
2. preparar entorn Android si cal buildar
3. personalitzar nom, icona, tema, idioma i bridge
4. configurar STT/TTS segons preferències exactes
5. compilar APK release
6. validar funcionalment el resultat
7. deixar instruccions finals d'instal·lació i manteniment

---

## Resum ràpid: qui fa què

### Humans
- descarreguen l'APK prebuilt en mode as-is
- creen repo propi si volen assistant-app personalitzada
- decideixen branding, política d'àudio i publicació
- gestionen domini, `nginx`, firewall i accessos externs si cal
- proven l'APK i donen feedback

### Agent AI
- prepara bridge i servei persistent
- demana les dades mínimes necessàries
- personalitza la marca si l'usuari ho vol
- només prepara Android SDK/JDK si cal recompilar
- compila i valida l'APK quan hi ha mode personalitzat

---

## Idiomes inicials suportats (UI)

- Català (`ca-ES`)
- Español (`es-ES`)
- English UK (`en-GB`)
- English US (`en-US`)
- Galego (`gl-ES`)
- Euskara (`eu-ES`)

---

## Documents útils

- `docs/APPENCLAW_AI_REPLICA.md` → guia operativa per a l'agent AI
- `docs/LOCALIZATION.md` → afegir o traduir idiomes UI
- `docs/templates/ui-locale-template.json` → plantilla de traduccions

---

## Avís legal bàsic

appenClaw és una interfície de comunicació per a agents AI. La configuració, desplegament, exposició de xarxa i ús final són responsabilitat de qui la desplega i la fa servir.

Les persones autores o contribuïdores del repositori no es fan responsables de mals usos, pèrdua de dades, incidències de seguretat o danys derivats de la instal·lació, configuració o ús.

---

## En una frase

**Pots descarregar i fer servir appenClaw tal com és, o usar-la com a base per crear la teva pròpia assistant-app connectada a un agent OpenClaw.**
