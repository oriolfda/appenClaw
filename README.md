# appenClaw

> **Avís important sobre la branca E2EE:** la implementació E2EE d'aquesta branca ha estat realitzada íntegrament o principalment per un assistent AI durant el procés de desenvolupament. No està certificada, auditada ni validada per cap entitat externa independent. No s'ha de presentar com una implementació canònica o certificada de Signal. Qualsevol ús del projecte, de l'APK o de les seves funcions criptogràfiques es fa sota el risc i responsabilitat de qui decideixi utilitzar-lo.

**appenClaw** és una app Android per connectar-se a un agent OpenClaw per text, àudio, imatges i vídeo.

Aquest repositori suporta **dos modes d'ús**:

1. **Fer servir appenClaw tal com és**
   - instal·lar l'APK base
   - configurar endpoint + token
   - connectar-la al bridge
2. **Crear una assistant-app personalitzada**
   - rebrand de nom, icona, idioma, tema i detalls del bridge
   - compilació d'un APK propi per a l'agent de cada usuari

---

## Ruta A — Fer servir appenClaw as-is

### Què fa l'humà

#### 1) Preparar el bridge
Cal un host Linux amb:
- OpenClaw CLI funcional
- Python 3
- accés de xarxa des del mòbil
- opcionalment `edge-tts` si vols àudio de resposta servit pel bridge

#### 2) Decidir com s'hi accedirà
- **Només LAN**
  - posa el mòbil i el servidor a la mateixa xarxa
  - usa la IP local del servidor
- **Accés des d'internet**
  - domini o subdomini
  - reverse proxy (`nginx` recomanat)
  - TLS/HTTPS
  - obertura del port necessari al firewall/router

#### 3) Configurar xarxa i publicació
Si el bridge serà accessible des de fora de la LAN:
- apunta el domini/subdomini a la IP pública
- obre el port al router/firewall
- posa `nginx` davant del bridge si vols TLS, domini net i capes addicionals de control
- mantén **sempre** el token del bridge actiu

#### 4) Instal·lar l'APK
- instal·la l'APK de `appenClaw`
- obre **Settings**
- configura:
  - endpoint del bridge
  - token
  - idioma d'interfície
  - preferències bàsiques d'àudio

#### 5) Provar flux bàsic
- xat text
- enviament d'àudio
- reproducció d'àudio
- imatge/vídeo
- `/status` o estat de context

### Què ha de fer l'agent AI
L'agent ha de seguir la guia operativa:
- `docs/APPENCLAW_AI_REPLICA.md`

Per al mode **as-is**, l'agent ha de:
1. preparar l'entorn host
2. crear o adaptar el bridge base `scripts/appenclaw_chat_bridge.py`
3. generar fitxer d'entorn del bridge
4. configurar servei persistent (`systemd` recomanat)
5. indicar a l'humà l'endpoint i token finals
6. validar text, adjunts i àudio

---

## Ruta B — Crear una assistant-app personalitzada a partir de appenClaw

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
- nom intern del projecte/repo si vol canviar-lo
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
- validació de seguretat mínima abans d'exposar el bridge

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

En el mode **personalitzat**, l'agent ha de:
1. fer intake interactiu amb l'humà
2. preparar repo, branding i configuració
3. personalitzar nom, icona, tema, idioma i bridge
4. configurar STT/TTS segons preferències exactes
5. compilar APK release
6. validar funcionalment el resultat
7. deixar instruccions finals d'instal·lació i manteniment

---

## Resum ràpid: qui fa què

### Humans
- creen repo propi si volen assistant-app personalitzada
- decideixen branding, política d'àudio i publicació
- gestionen domini, `nginx`, firewall i accessos externs si cal
- proven l'APK i donen feedback

### Agent AI
- prepara Android toolchain i bridge
- demana les dades mínimes necessàries
- configura servei persistent del bridge
- personalitza la marca si l'usuari ho vol
- compila i valida l'APK

---

## Què inclou l'app

- xat text
- gravació i enviament d'àudio
- adjunts d'imatge i vídeo
- reproducció d'àudio al xat
- render HTML/codi
- temes visuals
- localització UI
- suport de bridge amb endpoint + token

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

**Pots fer servir appenClaw tal com és, o usar-la com a base per crear la teva pròpia assistant-app connectada a un agent OpenClaw.**
