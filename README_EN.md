# appenClaw

> **WARNING:** This app is under active construction. Use it at your own risk.
>
> **Important E2EE branch notice:** the E2EE implementation in this branch has been developed entirely or primarily by an AI assistant during the development process. It has not been certified, audited, or validated by any independent external entity. It must not be presented as a certified or canonical Signal implementation. Any use of the project, APK, or its cryptographic features is entirely at the risk and responsibility of the person choosing to use it.

**appenClaw** is an Android app for connecting to an OpenClaw agent using text, audio, images, and video.

This repository supports **two usage modes**:

1. **Use appenClaw as-is**
   - download a prebuilt APK
   - install it
   - configure endpoint + token
   - use it with the base bridge
2. **Create a personalized assistant-app from appenClaw**
   - rebrand name, icon, locale, theme, and bridge details
   - build a dedicated APK for a specific agent/personality

---

## Path A — Use appenClaw as-is

### Message the human should give to their OpenClaw

Copy/paste something like this:

> "I want to use appenClaw as-is, without rebranding or rebuilding it. Follow `docs/APPENCLAW_AI_REPLICA.md` strictly in AS-IS mode. Do not rebrand or rebuild the APK unless necessary. Prepare the bridge, give me a working endpoint + token, explain whether nginx/firewall/domain setup is needed for external access, and tell me how to download and configure the `appenClaw-release.apk`."

### What the human does

#### 1) Download and install the APK
No Android SDK or local build is required.

The human only needs to:
- download `appenClaw-release.apk`
- install it on the phone
- open **Settings**
- enter:
  - bridge endpoint
  - token
  - UI language if they want to change it

#### 2) Decide access mode
- **LAN only**
  - keep phone and server on the same network
  - use the server private IP
- **Internet-accessible**
  - require domain or subdomain
  - `nginx` or equivalent reverse proxy
  - TLS/HTTPS
  - open ports in firewall/router

#### 3) Configure network/public exposure
If the bridge will be reachable from outside the LAN:
- point domain/subdomain to the public IP
- open the required port in firewall/router
- put `nginx` in front if you want TLS and cleaner public routing
- keep bridge token auth enabled at all times

#### 4) Test baseline flow
- text chat
- audio send
- audio playback
- image/video
- status/context

### What the AI agent must do
The AI agent should follow:
- `docs/APPENCLAW_AI_REPLICA.md`

For the **as-is** mode, the AI agent **does not need Android toolchain** unless something must be rebuilt.

It only needs to:
1. prepare the bridge host environment
2. create or adapt the base bridge `scripts/appenclaw_chat_bridge.py`
3. generate the bridge environment file
4. configure a persistent service (`systemd` recommended)
5. provide the final endpoint and token to the human
6. validate text, attachments, and audio flow

---

## Path B — Create a personalized assistant-app from appenClaw

### Message the human should give to their OpenClaw

Copy/paste something like this:

> "I want to create a personalized assistant-app starting from appenClaw. Follow `docs/APPENCLAW_AI_REPLICA.md` strictly in personalized mode. Run interactive intake for name, icon, locale, theme, STT/TTS preferences, target agent, bridge port, and deployment model. Then personalize the repo, build a release APK, prepare the dedicated bridge, and leave me clear install/use instructions."

### What the human does

#### 1) Prepare GitHub
Recommended: the repository should belong to the human user, not the assistant.

Recommended flow:
1. create a personal GitHub repo
2. add a **deploy key**
3. if the AI agent must push changes, enable **Allow write access**
4. share with the AI agent:
   - repo URL
   - SSH key location on the host

#### 2) Prepare personalization inputs
Before asking the AI agent to work, the human should define:
- visible app name
- icon (square PNG, ideally 1024x1024)
- default UI locale
- color theme
- whether STT transcriptions should be shown
- TTS policy:
  - automatic by language
  - or one fixed voice
- target agent
- bridge port
- LAN-only or internet-accessible deployment
- whether domain/subdomain + `nginx` are required

#### 3) Prepare publishing environment if needed
For internet access:
- domain/subdomain
- `nginx` or equivalent reverse proxy
- TLS/HTTPS
- firewall/router port opening
- minimum exposure/security validation before publishing the bridge

#### 4) Test the custom APK
Once the AI agent delivers the APK:
- install it
- verify name + icon
- configure endpoint + token
- test text, audio, image, video
- report visual or functional issues

### What the AI agent must do
The AI agent should follow:
- `docs/APPENCLAW_AI_REPLICA.md`

In the **customized** mode, the AI agent does need to:
1. run interactive intake with the human
2. prepare Android environment if a build is required
3. personalize name, icon, theme, locale, and bridge
4. configure STT/TTS exactly as requested
5. build the release APK
6. run functional validation
7. deliver final install and maintenance instructions

---

## Quick responsibility split

### Humans
- download the prebuilt APK in as-is mode
- create their own repo if they want a personalized assistant-app
- decide branding, audio policy, and publication model
- manage domain, `nginx`, firewall, and internet exposure if needed
- test the APK and provide feedback

### AI agent
- prepares bridge and persistent service
- asks for the minimum required data
- personalizes branding if requested
- only prepares Android SDK/JDK when rebuild is needed
- builds and validates the APK when customization is requested

---

## What the app includes

- text chat
- audio recording and sending
- image/video attachments
- in-chat audio playback
- HTML/code rendering
- visual themes
- UI localization
- bridge support with endpoint + token

---

## Initial UI languages

- Catalan (`ca-ES`)
- Spanish (`es-ES`)
- English UK (`en-GB`)
- English US (`en-US`)
- Galician (`gl-ES`)
- Basque (`eu-ES`)

---

## Useful documents

- `docs/APPENCLAW_AI_REPLICA.md` → operational guide for the AI agent
- `docs/LOCALIZATION.md` → add or translate UI languages
- `docs/templates/ui-locale-template.json` → translation template

---

## Basic legal notice

appenClaw is a communication interface for AI agents. Configuration, deployment, network exposure, and end usage are the responsibility of the person deploying and using it.

Repository authors/contributors are not liable for misuse, data loss, security incidents, or damages derived from installation, configuration, or use.

---

## In one sentence

**You can download and use appenClaw as-is, or use it as the base for building your own assistant-app connected to an OpenClaw agent.**
