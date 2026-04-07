# appenClaw App

> **Avís important sobre la branca E2EE:** la implementació E2EE d'aquesta branca ha estat realitzada íntegrament o principalment per un assistent AI durant el procés de desenvolupament. No està certificada, auditada ni validada per cap entitat externa independent. No s'ha de presentar com una implementació canònica o certificada de Signal. Qualsevol ús del projecte, de l'APK o de les seves funcions criptogràfiques es fa sota el risc i responsabilitat de qui decideixi utilitzar-lo.

**appenClaw App és una app Android per comunicar-te amb el teu assistent appenClaw** de forma natural: text, àudio, imatges i vídeo, amb una interfície de xat moderna.

Aquest repositori està pensat perquè qualsevol persona (encara que no sigui tècnica) pugui:

1. Entendre què és l’app i què fa.
2. Preparar el mínim necessari com a humà.
3. Donar instruccions al seu assistent appenClaw perquè construeixi i personalitzi l’APK.

---

## Què has de fer TU (com a humà)

### Pas 1 — Decideix com vols la teva app
Abans de res, pensa aquests punts:

- **Nom de l’app** (ex: “Aina Assistant”)
- **Icona** (png quadrat, idealment 1024x1024)
- **Idioma d’interfície per defecte**
- **Tema de colors** (fosc vermell, blau, verd, clar...)
- **Àudio**:
  - si vols **transcripció STT** visible al xat
  - per al **TTS**, tria el tractament:
    - **auto** (veu segons idioma)
    - **veu específica** (una veu fixa)
  - si tries **auto**, defineix:
    - quins idiomes vols cobrir
    - quina veu s’ha d’usar a cada idioma (per preparar bé el bridge-TTS)
  - si tries **veu específica**, indica la veu exacta i en quins casos s’ha d’aplicar
  - recomanat: provar 3-5 veus i triar per claredat + naturalitat
- **Com publicar-la si la vols usar arreu** (fora de la LAN):
  - domini/subdomini cap a la IP pública de la teva app
  - exemple gratuït: **DuckDNS + nginx**
- **Signatura Android (keystore/token)**:
  - és clau per poder desplegar actualitzacions de la mateixa app
  - guarda credencials i fitxers de signatura de forma segura
- **Carpeta compartida humà ↔ assistent AI**:
  - crea una carpeta compartida de treball/comunicació (APK, captures, logs, errors)
  - és molt útil per descarregar APK des del mòbil i reportar incidències de prova

### Pas 2 — Crea TU el repo i dona accés segur a l’assistent
Recomanació: que el **repo sigui teu** (GitHub de l’humà) i no de l’assistent.

Flux recomanat:
1. Crea un repo nou (p. ex. `appenclaw-app` o el nom que vulguis)
2. Afegeix una **deploy key** (preferiblement amb escriptura si l’assistent ha de fer push)
3. Comparteix amb l’assistent:
   - URL del repo
   - ruta/localització de la clau SSH (al host on treballa l’assistent)

Exemple breu (GitHub):
- Repository → **Settings** → **Deploy keys** → **Add deploy key**
- Enganxa la clau pública (`*.pub`) i activa **Allow write access** si vols que l’assistent pugi canvis.

### Pas 3 — Dona aquest repo al teu assistent appenClaw
Passa-li l’enllaç del repo i digues-li:

> “Vull una rèplica personalitzada de l’appenClaw App. Segueix la guia `docs/APPENCLAW_AI_REPLICA.md`, canvia nom+icona+tema+idioma, compila APK release i deixa’m el fitxer llest per instal·lar.”

### Pas 4 — Prova l’APK i dona feedback
Quan l’assistent et passi l’APK:

- instal·la-la al mòbil
- obre Settings i posa endpoint+token del bridge
- prova text, àudio, imatge, vídeo
- si vols canvis visuals/funcionals, torna-li feedback

---

## Què farà el teu assistent appenClaw

El teu assistent (no tu manualment) farà:

- recollida **interactiva** de la informació necessària (nom, icona, idioma, tema, STT/TTS, etc.)
- instal·lació de requisits Android (JDK/SDK)
- configuració del bridge appenClaw
- configuració de STT/TTS segons preferències humanes (incloent veus triades)
- compilació APK release
- personalització (marca, tema, idioma)
- validació funcional

Guia completa per a l’assistent:

➡️ `docs/APPENCLAW_AI_REPLICA.md`

---

## Què inclou l’app

- Xat text
- Gravació i enviament d’àudio
- Adjunt d’imatge i vídeo
- Reproducció d’àudio al xat
- Render de contingut HTML/codi
- Temes i localització de la interfície

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

- `docs/APPENCLAW_AI_REPLICA.md` → guia operativa per l’assistent appenClaw
- `docs/LOCALIZATION.md` → com afegir/traduir idiomes de la interfície
- `docs/templates/ui-locale-template.json` → plantilla de traduccions

---

## En una frase

**Tu decideixes com vols l’app. El teu assistent appenClaw la construeix i la personalitza per tu.**
