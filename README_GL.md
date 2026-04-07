# appenClaw

> **AVISO:** Esta app está en construción activa. Úsaa baixo a túa propia responsabilidade.
>
> **Aviso importante sobre o desenvolvemento e a implementación E2EE:** esta app foi desenvolvida integramente ou principalmente por un asistente AI baixo supervisión e indicacións humanas. A implementación E2EE do proxecto tampouco foi certificada, auditada nin validada por ningunha entidade externa independente. Non debe presentarse como unha implementación canónica ou certificada de Signal. Calquera uso do proxecto, do APK ou das súas funcións criptográficas realízase baixo o risco e responsabilidade de quen decida utilizalo.

**appenClaw** é unha app Android para conectarse a un axente OpenClaw mediante texto, audio, imaxes e vídeo.

Este repositorio soporta **dous modos de uso**:

1. **Usar appenClaw tal como está**
   - descargar un APK xa compilado
   - instalalo
   - configurar endpoint + token
   - usalo co bridge base
2. **Crear unha assistant-app personalizada**
   - rebrand de nome, icona, idioma, tema e detalles do bridge
   - compilación dun APK propio para o axente de cada usuario

---

## Que inclúe a app

- chat de texto para comunicarse co teu axente OpenClaw
- gravación e envío de audio
- adxuntos de imaxe e vídeo
- reprodución de audio no chat
- cifrado de extremo a extremo (E2EE) para mensaxes e adxuntos, cunha implementación propia baseada no modelo de Signal (**véxase o aviso inicial**)
- render HTML/código
- temas visuais
- localización UI
- soporte de bridge con endpoint + token

---

## Ruta A — Usar appenClaw as-is

### Mensaxe que a persoa debe darlle ao seu OpenClaw

Copia e pega unha instrución coma esta:

> "Quero usar appenClaw tal como está, sen personalizala nin recompilala. Usa como referencia canónica `https://github.com/oriolfda/appenClaw` e segue estritamente `docs/APPENCLAW_AI_REPLICA.md` en modo AS-IS. Non fagas rebrand nin rebuild do APK se non é necesario. Antes de instalar ou crear ningún servizo, verifica se o bridge de appenClaw xa existe ou xa está correndo nesta máquina e, se é así, reutilízao ou adápao no canto de duplicalo. Se eu non especifico o porto, podes decidir ti un porto axeitado que non entre en conflito e debes indicarmo explicitamente. Prepara o bridge, déixame un endpoint + token funcionais, explícame se fai falta nginx/firewall/dominio para acceso externo, e indícame como descargar e configurar o APK `appenClaw-release.apk`."

### Que fai a persoa humana

#### 1) Descargar e instalar o APK
Non fai falta Android SDK nin compilación local.

A persoa só ten que:
- descargar `appenClaw-release.apk`
- instalalo no móbil
- abrir **Settings**
- poñer:
  - endpoint do bridge
  - token
  - idioma de interface se o quere cambiar

#### 2) Decidir como se accederá
- **Só LAN**
  - o móbil e o servidor deben estar na mesma rede
  - usa a IP local do servidor
- **Acceso desde internet**
  - fai falta dominio ou subdominio
  - `nginx` ou reverse proxy equivalente
  - TLS/HTTPS
  - portos abertos en firewall/router

#### 3) Decidir o porto do bridge
A persoa pode:
- indicar un porto concreto, ou
- deixar que o axente AI escolla un porto libre axeitado

Se o AI escolle o porto, debe:
- comprobar que non entre en conflito con servizos existentes
- documentar que porto escolleu
- dicirlle claramente á persoa cal é o endpoint final que debe usar

#### 4) Configurar rede e publicación
Se o bridge vai ser accesible desde fóra da LAN:
- apunta o dominio/subdominio á IP pública
- abre o porto no router/firewall
- coloca `nginx` diante do bridge se queres TLS e unha URL pública limpa
- mantén sempre activo o token do bridge

#### 5) Permisos que debe ter o asistente OpenClaw
Se queres que o asistente deixe o bridge instalado e persistente, debe ter permisos suficientes para facer as accións necesarias no host, por exemplo:
- crear ou editar ficheiros de configuración do bridge
- crear ou editar un servizo `systemd` (user ou system)
- arrancar, parar, reiniciar e consultar o estado do servizo
- ler ou reservar un porto libre
- se fai falta acceso externo: tocar configuración de `nginx` e/ou explicarte exactamente que debes facer ti manualmente
- se fai falta abrir portos no firewall, ter permisos para facelo ou deixarche a instrución exacta

Se o asistente non ten eses permisos, polo menos debe poder:
- preparar todos os ficheiros
- indicar os comandos exactos que debes executar ti
- explicar que falta para completar o despregamento

#### 6) Probar fluxo básico
- chat de texto
- envío de audio
- reprodución de audio
- imaxe/vídeo
- estado/contexto

### Que debe facer o axente AI
O axente debe seguir:
- `docs/APPENCLAW_AI_REPLICA.md`

Para o modo **as-is**, o axente **non necesita Android toolchain** se non hai que recompilar nada.

Só debe:
1. preparar o entorno host do bridge
2. crear ou adaptar o bridge base `scripts/appenclaw_chat_bridge.py`
3. xerar o ficheiro de entorno do bridge
4. configurar servizo persistente (`systemd` recomendado)
5. indicar á persoa endpoint + token finais
6. validar texto, adxuntos e audio

---

## Ruta B — Crear unha assistant-app personalizada a partir de appenClaw

### Mensaxe que a persoa debe darlle ao seu OpenClaw

Copia e pega unha instrución coma esta:

> "Quero crear unha assistant-app personalizada a partir de appenClaw. Usa como referencia canónica `https://github.com/oriolfda/appenClaw` e segue estritamente `docs/APPENCLAW_AI_REPLICA.md` en modo personalizado. Fai intake interactivo do nome, icona, idioma, tema, preferencias STT/TTS, axente obxectivo, porto do bridge e modelo de despregamento. Despois personaliza un repositorio de traballo axeitado, compila un APK release, prepara o bridge específico e déixame instrucións claras para instalala e usala."

### Que fai a persoa humana

#### 1) Preparar GitHub
Recomendación: que o repo sexa **da persoa humana**, non do asistente.

Fluxo recomendado:
1. crea un repo propio en GitHub
2. engade unha **deploy key**
3. se o axente debe facer `push`, activa **Allow write access**
4. comparte co axente:
   - URL do repo
   - localización da clave SSH no host

#### 2) Preparar a información de personalización
Antes de darlle traballo ao axente, a persoa debería ter claro:
- nome visible da app
- icona (PNG cadrado, idealmente 1024x1024)
- idioma UI por defecto
- tema de cores
- se quere mostrar ou non transcricións STT
- política TTS:
  - automática por idioma
  - ou voz fixa específica
- axente obxectivo
- porto do bridge
- se será só LAN ou accesible desde internet
- se quere dominio/subdominio + `nginx`

#### 3) Preparar entorno de publicación se fai falta
Se se quere acceso externo:
- dominio/subdominio
- `nginx` ou reverse proxy equivalente
- TLS/HTTPS
- portos abertos en firewall/router
- validación mínima de seguridade antes de expoñer o bridge

#### 4) Probar o APK personalizado
Cando o axente che entregue o APK:
- instálao
- comproba nome + icona
- configura endpoint + token
- proba texto, audio, imaxe, vídeo
- reporta incidencias visuais ou funcionais

### Que debe facer o axente AI
O axente debe seguir:
- `docs/APPENCLAW_AI_REPLICA.md`

En modo **personalizado**, o axente si debe:
1. facer intake interactivo coa persoa
2. preparar entorno Android se hai que buildar
3. personalizar nome, icona, tema, idioma e bridge
4. configurar STT/TTS segundo as preferencias exactas
5. compilar APK release
6. validar funcionalmente o resultado
7. deixar instrucións finais de instalación e mantemento

---

## Resumo rápido: quen fai que

### Humanos
- descargan o APK prebuilt en modo as-is
- crean repo propio se queren assistant-app personalizada
- deciden branding, política de audio e publicación
- xestionan dominio, `nginx`, firewall e accesos externos se fai falta
- proban o APK e dan feedback

### Axente AI
- prepara bridge e servizo persistente
- pide os datos mínimos necesarios
- personaliza a marca se o usuario o quere
- só prepara Android SDK/JDK se hai que recompilar
- compila e valida o APK cando hai modo personalizado

---

## Idiomas iniciais soportados (UI)

- Català (`ca-ES`)
- Español (`es-ES`)
- English UK (`en-GB`)
- English US (`en-US`)
- Galego (`gl-ES`)
- Euskara (`eu-ES`)

---

## Documentos útiles

- `docs/APPENCLAW_AI_REPLICA.md` → guía operativa para o axente AI
- `docs/LOCALIZATION.md` → engadir ou traducir idiomas UI
- `docs/templates/ui-locale-template.json` → plantilla de traducións

---

## Aviso legal básico

appenClaw é unha interface de comunicación para axentes AI. A configuración, despregamento, exposición de rede e uso final son responsabilidade de quen a desprega e a usa.

As persoas autoras ou contribuidoras do repositorio non se fan responsables de malos usos, perda de datos, incidencias de seguridade ou danos derivados da instalación, configuración ou uso.

---

## Nunha frase

**Podes descargar e usar appenClaw tal como está, ou usala como base para crear a túa propia assistant-app conectada a un axente OpenClaw.**
