# OpenClaw AI Replica Guide

Guia per a un assistent OpenClaw que hagi de replicar/personalitzar aquesta app per al seu humà.

## 1) Requisits host
- Linux
- Java 17
- Android SDK CLI
- OpenClaw CLI operatiu
- Python 3
- (Opcional) edge-tts per respostes d'àudio

## 2) Setup Android
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

## 3) Build APK
```bash
git clone <fork-url> aigor-app
cd aigor-app
cat > local.properties <<EOF
sdk.dir=$HOME/Android/Sdk
EOF
./gradlew assembleRelease
```

## 4) Bridge
Script: `scripts/aigor_chat_bridge.py`
- `POST /chat`
- `GET /status`
- `GET /media/<file>`

Variables recomanades:
- `AIGOR_BRIDGE_HOST`
- `AIGOR_BRIDGE_PORT`
- `AIGOR_BRIDGE_TOKEN`
- `AIGOR_BRIDGE_PUBLIC_BASE_URL`
- `AIGOR_BRIDGE_MEDIA_DIR`
- `AIGOR_BRIDGE_EDGE_TTS`

## 5) TTS (opcional)
```bash
python3 -m venv ~/.openclaw/venvs/aigor-tts
~/.openclaw/venvs/aigor-tts/bin/pip install --upgrade pip
~/.openclaw/venvs/aigor-tts/bin/pip install edge-tts
```

## 6) Personalització
- Nom: `app_name` a `strings.xml`
- Tema: `ThemeManager.kt` + drawables
- Icona: recursos launcher
- Idiomes UI: `values-xx-rYY/strings.xml`

## 7) Validació
- text ok
- imatge/vídeo ok
- àudio enviar/reproduir ok
- estat context ok
- canvi tema i idioma UI ok
