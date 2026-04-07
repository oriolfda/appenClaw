# appenClaw AI Replica Guide

This guide is for an AI agent that must either:
1. deploy **appenClaw as-is**, or
2. create a **personalized assistant-app** starting from appenClaw.

> AI-facing instructions are intentionally written in English so they are easy to audit by humans.

---

## 0) First decide which mode applies
Before changing code or preparing infrastructure, ask the human which path applies:

- **Mode A — appenClaw as-is**
  - keep name/icon/branding as provided
  - only configure and deploy the bridge + APK usage
- **Mode B — personalized assistant-app**
  - customize name, icon, theme, locale, and bridge details
  - build a dedicated APK for the human's own agent/personality

Do not assume personalization when the human only wants a working base app.

---

## 1) Interactive intake (ask first, then implement)
Ask in a short checklist format and wait for answers.

### Minimum intake for Mode A — appenClaw as-is
1. Will the app be used on **LAN only** or exposed to the **internet**?
2. Which host will run the bridge?
3. Which OpenClaw agent/session should the bridge target?
4. Which bridge port should be used?
5. Is TTS needed for bridge-served voice replies?
6. Should STT transcripts be shown in the app?
7. Will a reverse proxy (`nginx`) be used?
8. Does the human already have domain/subdomain + firewall access if internet exposure is required?

### Minimum intake for Mode B — personalized assistant-app
1. Visible app name
2. App icon (path/file)
3. Default UI locale
4. Color theme preference
5. Target OpenClaw agent/session
6. Bridge endpoint + token strategy
7. Bridge port
8. Audio preferences:
   - STT transcription visible in chat? (yes/no)
   - TTS enabled for assistant replies? (yes/no)
   - TTS mode: `auto` or `specific-voice`
   - If `auto`: which languages and which voice per language?
   - If `specific-voice`: exact voice id/name and forcing rules
9. Deployment preference:
   - LAN only, or internet-accessible?
   - If internet-accessible: domain/subdomain plan, reverse proxy plan, TLS plan
10. GitHub repo details:
   - repo URL
   - deploy key availability
   - whether push access is expected

If information is missing, ask follow-up questions instead of guessing.

---

## 2) Host requirements
Minimum host requirements:
- Linux
- Java 17
- Android SDK CLI (only if building APK on this host)
- OpenClaw CLI available and authenticated/usable
- Python 3
- optional `edge-tts` for server-side spoken replies
- optional `nginx` when reverse proxying the bridge

---

## 3) Android toolchain setup (only when building APKs)
```bash
sudo apt-get update
sudo apt-get install -y openjdk-17-jdk unzip
mkdir -p ~/Android/Sdk/cmdline-tools
cd ~/Android/Sdk/cmdline-tools
curl -fL -o commandlinetools-linux.zip https://dl.google.com/android/repository/commandlinetools-linux-11076708_latest.zip
unzip -q commandlinetools-linux.zip
mv cmdline-tools latest
export ANDROID_SDK_ROOT=~/Android/Sdk
export PATH=$ANDROID_SDK_ROOT/cmdline-tools/latest/bin:$ANDROID_SDK_ROOT/platform-tools:$PATH
yes | sdkmanager --licenses
sdkmanager "platform-tools" "platforms;android-34" "build-tools;34.0.0"
```

Create `local.properties` before building:
```bash
cat > local.properties <<EOF
sdk.dir=$HOME/Android/Sdk
EOF
```

---

## 4) Mode A workflow — appenClaw as-is

### What to do
1. Keep app branding unchanged.
2. Prepare the bridge host.
3. Create/configure bridge env file.
4. Set up persistent bridge execution (`systemd` recommended).
5. Provide endpoint + token to the human.
6. Validate baseline functionality.

### Bridge script
Use:
- `scripts/appenclaw_chat_bridge.py`

### Core bridge endpoints
- `POST /chat`
- `GET /status`
- `GET /media/<file>`
- `GET /e2ee/status` (optional / phase 2)
- `GET /e2ee/prekey-bundle` (optional / phase 2 bootstrap)

### Recommended bridge environment variables
- `APPENCLAW_BRIDGE_HOST`
- `APPENCLAW_BRIDGE_PORT`
- `APPENCLAW_BRIDGE_TOKEN`
- `APPENCLAW_BRIDGE_SESSION`
- `APPENCLAW_BRIDGE_AGENT`
- `APPENCLAW_BRIDGE_PUBLIC_BASE_URL`
- `APPENCLAW_BRIDGE_MEDIA_DIR`
- `APPENCLAW_BRIDGE_EDGE_TTS`
- `APPENCLAW_APP_E2EE_ENABLED` (optional)
- `APPENCLAW_APP_E2EE_REQUIRED` (optional)
- `APPENCLAW_APP_E2EE_PROTOCOL` (default: `signal-x3dh-dr-v1`)

### Suggested systemd approach
Create a user service or system service that:
- loads the bridge env file
- runs `python3 scripts/appenclaw_chat_bridge.py`
- restarts on failure
- starts on boot/login as appropriate

### Validation checklist for Mode A
- text chat works
- image/video upload works
- audio send/playback works
- context/status works
- token auth is enforced
- public URL works if internet exposure was requested

---

## 5) Mode B workflow — personalized assistant-app

### What to do
1. Run interactive intake.
2. Clone or prepare the human-owned repo.
3. Update name, icon, locale, theme, and bridge defaults.
4. Configure STT/TTS according to human requirements.
5. Build the release APK.
6. Deliver the APK and final config notes.
7. Push commits if the repo/deploy key allows it.

### Personalization targets
Typical files/areas to update:
- visible name: `app_name` strings
- icon assets: launcher/icon drawable resources
- package/app identity if explicitly requested
- theme colors/drawables
- locale defaults and translations
- bridge env defaults
- README / setup instructions if the repo is a dedicated personalized fork

### Build APK
```bash
git clone <fork-url> appenclaw-app
cd appenclaw-app
cat > local.properties <<EOF
sdk.dir=$HOME/Android/Sdk
EOF
./gradlew assembleRelease
```

### Signing / keystore (critical)
For release signing, Android keystore material is mandatory.

Rules:
- keep `.jks` and `keystore.properties` secure
- never publish private passwords or private signing material in public repos
- if the keystore is lost, updates to already-installed packages may require a new app identity
- confirm whether the human wants a fresh signing identity or continuation of an existing one

### Validation checklist for Mode B
- name and icon are correct
- theme and locale match the request
- endpoint + token flow works
- text/audio/image/video work
- STT/TTS behavior matches the requested policy
- final APK is installable on device

---

## 6) TTS/STT guidance

### STT transcription
- If enabled, show transcript text in chat.
- If disabled, keep the UX minimal and privacy-oriented.

### TTS enablement
Always ask which mode the human wants:
- `auto`
- `specific-voice`

If `auto`:
- collect exact language list
- collect exact language → voice mapping
- define fallback voice explicitly

If `specific-voice`:
- collect exact voice id/name
- collect forcing scope/rules

Honor the human-selected configuration exactly.

### Human-facing advice when choosing voices
Recommend testing 3–5 voices and comparing:
1. naturalness
2. clarity
3. pronunciation quality
4. fatigue over long listening sessions
5. latency/response speed

---

## 7) Internet exposure guidance
If the human wants remote access outside the LAN:
- use domain/subdomain pointing to the bridge public IP
- use `nginx` or equivalent reverse proxy
- add HTTPS/TLS before exposing production traffic
- open only the required ports in firewall/router
- keep token auth active
- verify that public exposure is intentional and understood by the human

Minimum items to mention to the human:
- DNS/domain
- firewall/router rules
- reverse proxy
- TLS certificates
- token/auth model

---

## 8) GitHub workflow guidance
If the human wants a personalized fork:
- recommend a repo owned by the human
- use deploy keys instead of personal broad credentials when possible
- if push access is required, confirm write access is enabled
- commit meaningful checkpoints
- keep secrets out of git history

---

## 9) Final delivery checklist
Before declaring done, give the human:
1. APK path
2. endpoint value
3. token value or token delivery method
4. whether the bridge is LAN-only or public
5. service name/location if a persistent service was installed
6. notes about domain/nginx/firewall if applicable
7. known limitations or follow-up recommendations

---

## 10) Success criteria
Done means:
- the correct mode (as-is vs customized) was respected
- the human has the required instructions for their role
- the bridge is configured and validated
- the APK works for the requested use case
- network exposure steps were explained when relevant
- repo state is committed/pushed when requested and authorized
