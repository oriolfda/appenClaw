# appenClaw

> **AVISO:** Esta app está en construcción activa. Úsala bajo tu propia responsabilidad.
>
> **Aviso importante sobre la rama E2EE:** la implementación E2EE de esta rama ha sido desarrollada íntegramente o principalmente por un asistente AI durante el proceso de desarrollo. No ha sido certificada, auditada ni validada por ninguna entidad externa independiente. No debe presentarse como una implementación canónica o certificada de Signal. Cualquier uso del proyecto, del APK o de sus funciones criptográficas se realiza bajo el riesgo y responsabilidad de quien decida utilizarlo.

**appenClaw** es una app Android para conectarse a un agente OpenClaw por texto, audio, imágenes y vídeo.

Este repositorio soporta **dos modos de uso**:

1. **Usar appenClaw tal cual**
   - descargar una APK ya compilada
   - instalarla
   - configurar endpoint + token
   - usarla con el bridge base
2. **Crear una assistant-app personalizada**
   - rebrand de nombre, icono, idioma, tema y detalles del bridge
   - compilación de un APK propio para el agente de cada usuario

---

## Ruta A — Usar appenClaw as-is

### Mensaje que la persona debe dar a su OpenClaw

Copia y pega una instrucción como esta:

> "Quiero usar appenClaw tal como está, sin personalizarla ni recompilarla. Usa como referencia canónica `https://github.com/oriolfda/appenClaw` y sigue estrictamente `docs/APPENCLAW_AI_REPLICA.md` en modo AS-IS. No hagas rebrand ni rebuild del APK si no es necesario. Antes de instalar o crear ningún servicio, verifica si el bridge de appenClaw ya existe o ya está corriendo en esta máquina y, si es así, reutilízalo o adáptalo en lugar de duplicarlo. Si no especifico el puerto, puedes decidir tú un puerto adecuado que no entre en conflicto y debes indicármelo explícitamente. Prepara el bridge, déjame un endpoint + token funcionales, explícame si hace falta nginx/firewall/dominio para acceso externo, e indícame cómo descargar y configurar el APK `appenClaw-release.apk`."

### Qué hace la persona humana

#### 1) Descargar e instalar el APK
No hace falta Android SDK ni compilación local.

La persona solo tiene que:
- descargar `appenClaw-release.apk`
- instalarlo en el móvil
- abrir **Settings**
- poner:
  - endpoint del bridge
  - token
  - idioma de interfaz si quiere cambiarlo

#### 2) Decidir cómo se accederá
- **Solo LAN**
  - el móvil y el servidor deben estar en la misma red
  - usa la IP local del servidor
- **Acceso desde internet**
  - hace falta dominio o subdominio
  - `nginx` o reverse proxy equivalente
  - TLS/HTTPS
  - puertos abiertos en firewall/router

#### 3) Decidir el puerto del bridge
La persona puede:
- indicar un puerto concreto, o
- dejar que el agente AI elija un puerto libre adecuado

Si el AI elige el puerto, debe:
- comprobar que no entre en conflicto con servicios existentes
- documentar qué puerto ha escogido
- decir claramente cuál es el endpoint final que debe usar la persona

#### 4) Configurar red y publicación
Si el bridge va a ser accesible desde fuera de la LAN:
- apunta el dominio/subdominio a la IP pública
- abre el puerto en el router/firewall
- coloca `nginx` delante del bridge si quieres TLS y una URL pública limpia
- mantén siempre activo el token del bridge

#### 5) Permisos que debe tener el asistente OpenClaw
Si quieres que el asistente deje el bridge instalado y persistente, debe tener permisos suficientes para hacer las acciones necesarias en el host, por ejemplo:
- crear o editar archivos de configuración del bridge
- crear o editar un servicio `systemd` (user o system)
- arrancar, parar, reiniciar y consultar el estado del servicio
- leer o reservar un puerto libre
- si hace falta acceso externo: tocar configuración de `nginx` y/o explicarte exactamente qué debes hacer tú manualmente
- si hace falta abrir puertos en el firewall, tener permisos para hacerlo o dejarte la instrucción exacta

Si el asistente no tiene esos permisos, al menos debe poder:
- preparar todos los archivos
- indicar los comandos exactos que debes ejecutar tú
- explicar qué falta para completar el despliegue

#### 6) Probar flujo básico
- chat de texto
- envío de audio
- reproducción de audio
- imagen/vídeo
- estado/contexto

### Qué debe hacer el agente AI
El agente debe seguir:
- `docs/APPENCLAW_AI_REPLICA.md`

Para el modo **as-is**, el agente **no necesita Android toolchain** si no hay que recompilar nada.

Solo debe:
1. preparar el entorno host del bridge
2. crear o adaptar el bridge base `scripts/appenclaw_chat_bridge.py`
3. generar el archivo de entorno del bridge
4. configurar servicio persistente (`systemd` recomendado)
5. indicar a la persona endpoint + token finales
6. validar texto, adjuntos y audio

---

## Ruta B — Crear una assistant-app personalizada a partir de appenClaw

### Mensaje que la persona debe dar a su OpenClaw

Copia y pega una instrucción como esta:

> "Quiero crear una assistant-app personalizada a partir de appenClaw. Usa como referencia canónica `https://github.com/oriolfda/appenClaw` y sigue estrictamente `docs/APPENCLAW_AI_REPLICA.md` en modo personalizado. Haz intake interactivo del nombre, icono, idioma, tema, preferencias STT/TTS, agente objetivo, puerto del bridge y modelo de despliegue. Después personaliza un repositorio de trabajo adecuado, compila un APK release, prepara el bridge específico y déjame instrucciones claras para instalarla y usarla."

### Qué hace la persona humana

#### 1) Preparar GitHub
Recomendación: que el repo sea **de la persona humana**, no del asistente.

Flujo recomendado:
1. crea un repo propio en GitHub
2. añade una **deploy key**
3. si el agente debe hacer `push`, activa **Allow write access**
4. comparte con el agente:
   - URL del repo
   - ubicación de la clave SSH en el host

#### 2) Preparar la información de personalización
Antes de dar trabajo al agente, la persona debería tener claro:
- nombre visible de la app
- icono (PNG cuadrado, idealmente 1024x1024)
- idioma UI por defecto
- tema de colores
- si quiere mostrar o no transcripciones STT
- política TTS:
  - automática por idioma
  - o voz fija específica
- agente objetivo
- puerto del bridge
- si será solo LAN o accesible desde internet
- si quiere dominio/subdominio + `nginx`

#### 3) Preparar entorno de publicación si hace falta
Si se quiere acceso externo:
- dominio/subdominio
- `nginx` o reverse proxy equivalente
- TLS/HTTPS
- puertos abiertos en firewall/router
- validación mínima de seguridad antes de exponer el bridge

#### 4) Probar el APK personalizado
Cuando el agente te entregue el APK:
- instálalo
- comprueba nombre + icono
- configura endpoint + token
- prueba texto, audio, imagen, vídeo
- reporta incidencias visuales o funcionales

### Qué debe hacer el agente AI
El agente debe seguir:
- `docs/APPENCLAW_AI_REPLICA.md`

En modo **personalizado**, el agente sí debe:
1. hacer intake interactivo con la persona
2. preparar entorno Android si hay que buildar
3. personalizar nombre, icono, tema, idioma y bridge
4. configurar STT/TTS según preferencias exactas
5. compilar APK release
6. validar funcionalmente el resultado
7. dejar instrucciones finales de instalación y mantenimiento

---

## Resumen rápido: quién hace qué

### Humanos
- descargan el APK prebuilt en modo as-is
- crean repo propio si quieren assistant-app personalizada
- deciden branding, política de audio y publicación
- gestionan dominio, `nginx`, firewall y accesos externos si hace falta
- prueban el APK y dan feedback

### Agente AI
- prepara bridge y servicio persistente
- pide los datos mínimos necesarios
- personaliza la marca si el usuario lo quiere
- solo prepara Android SDK/JDK si hay que recompilar
- compila y valida el APK cuando hay modo personalizado

---

## Qué incluye la app

- chat de texto
- grabación y envío de audio
- adjuntos de imagen y vídeo
- reproducción de audio en el chat
- render HTML/código
- temas visuales
- localización UI
- soporte de bridge con endpoint + token

---

## Idiomas iniciales soportados (UI)

- Català (`ca-ES`)
- Español (`es-ES`)
- English UK (`en-GB`)
- English US (`en-US`)
- Galego (`gl-ES`)
- Euskara (`eu-ES`)

---

## Documentos útiles

- `docs/APPENCLAW_AI_REPLICA.md` → guía operativa para el agente AI
- `docs/LOCALIZATION.md` → añadir o traducir idiomas UI
- `docs/templates/ui-locale-template.json` → plantilla de traducciones

---

## Aviso legal básico

appenClaw es una interfaz de comunicación para agentes AI. La configuración, despliegue, exposición de red y uso final son responsabilidad de quien la despliega y la utiliza.

Las personas autoras o contribuidoras del repositorio no se hacen responsables de malos usos, pérdida de datos, incidencias de seguridad o daños derivados de la instalación, configuración o uso.

---

## En una frase

**Puedes descargar y usar appenClaw tal como está, o usarla como base para crear tu propia assistant-app conectada a un agente OpenClaw.**
