# appenClaw

> **OHARRA:** App hau eraikuntza aktiboan dago. Erabili zure ardurapean.
>
> **E2EE inplementazioari buruzko ohar garrantzitsua:** proiektu honetako E2EE inplementazioa AI laguntzaile batek garatu du osorik edo nagusiki garapen prozesuan zehar. Ez du kanpo entitate independente baten ziurtapenik, auditoriarik edo balidaziorik. Ez da aurkeztu behar Signal-en inplementazio kanoniko edo ziurtatu gisa. Proiektuaren, APKaren edo haren funtzio kriptografikoen edozein erabilera erabiltzea erabakitzen duenaren arrisku eta erantzukizunpean egiten da.

**appenClaw** Android aplikazioa da OpenClaw agente batera testu, audio, irudi eta bideo bidez konektatzeko.

Biltegi honek **bi erabilera modu** ditu:

1. **appenClaw bere horretan erabiltzea**
   - aurrez konpilatutako APK bat deskargatzea
   - instalatzea
   - endpoint + token konfiguratzea
   - oinarrizko bridge-arekin erabiltzea
2. **assistant-app pertsonalizatu bat sortzea**
   - izena, ikonoa, hizkuntza, gaia eta bridge xehetasunak moldatzea
   - erabiltzaile bakoitzaren agenterako APK propioa konpilatzea

---

## A bidea — appenClaw as-is erabiltzea

### Gizakiak bere OpenClaw-ari eman behar dion mezua

Kopiatu eta itsatsi honelako instrukzio bat:

> "appenClaw bere horretan erabili nahi dut, pertsonalizatu edo berriz konpilatu gabe. Erabili `https://github.com/oriolfda/appenClaw` erreferentzia kanoniko gisa eta jarraitu zorrotz `docs/APPENCLAW_AI_REPLICA.md` AS-IS moduan. Ez egin rebrandik edo APK rebuildik beharrezkoa ez bada. Zerbitzurik instalatu edo sortu aurretik, egiaztatu appenClaw bridge-a makina honetan lehendik badagoen edo martxan dagoen, eta hala bada, berrerabili edo egokitu ezazu bikoiztu beharrean. Nik portua zehazten ez badut, zuk portu egoki eta libre bat aukeratu dezakezu, eta argi adierazi behar didazu. Prestatu bridge-a, utzi endpoint + token funtzionalak, azaldu nginx/firewall/domeinua behar den kanpo sarbiderako, eta esan nola deskargatu eta konfiguratu `appenClaw-release.apk` APK-a."

### Zer egiten du gizakiak

#### 1) APK deskargatu eta instalatu
Ez da behar Android SDKrik ez tokiko konpilaziorik.

Gizakiak honakoa besterik ez du egin behar:
- `appenClaw-release.apk` deskargatu
- mugikorrean instalatu
- **Settings** ireki
- honakoak sartu:
  - bridge endpoint-a
  - token-a
  - interfazearen hizkuntza, aldatu nahi badu

#### 2) Sarbidea nola egingo den erabaki
- **LAN bakarrik**
  - mugikorra eta zerbitzaria sare berean egon behar dira
  - zerbitzariaren IP lokala erabili
- **Internetetik sarbidea**
  - domeinua edo azpidomeinua behar da
  - `nginx` edo reverse proxy baliokidea
  - TLS/HTTPS
  - portuak irekita firewall/routerrean

#### 3) Bridge-aren portua erabaki
Gizakiak bi aukera ditu:
- portu zehatz bat adierazi, edo
- AI agenteari portu libre egoki bat aukeratzen utzi

AIak portua aukeratzen badu, honek egin behar du:
- dagoeneko badauden zerbitzuekin gatazkarik ez dagoela egiaztatu
- aukeratutako portua dokumentatu
- gizakiari argi esan zein den erabili behar duen azken endpoint-a

#### 4) Sarea eta publikazioa konfiguratu
Bridge-a LANetik kanpo erabilgarri egongo bada:
- domeinua/azpidomeinua IP publikora apuntatu
- portua ireki routerrean/firewallean
- jarri `nginx` bridge-aren aurrean TLS eta URL publiko txukun bat nahi baduzu
- mantendu bridge token-a beti aktibo

#### 5) OpenClaw laguntzaileak izan behar dituen baimenak
Laguntzaileak bridge-a instalatuta eta iraunkor utz dezan nahi baduzu, hostean beharrezko ekintzak egiteko baimen nahikoak izan behar ditu, adibidez:
- bridge konfigurazio fitxategiak sortu edo editatu
- `systemd` zerbitzu bat sortu edo editatu (user edo system)
- zerbitzua abiatu, gelditu, berrabiarazi eta egoera kontsultatu
- portu libre bat irakurri edo erreserbatu
- kanpo sarbidea behar bada: `nginx` konfigurazioa ukitu edo zuk eskuz egin behar duzuna zehazki azaldu
- firewall-ean portuak ireki behar badira, hori egiteko baimena izan edo instrukzio zehatza utzi

Laguntzaileak baimen horiek ez baditu, gutxienez egin ahal izan behar du:
- fitxategi guztiak prestatu
- zuk exekutatu behar dituzun komando zehatzak utzi
- zer falta den azaldu, deploy-a osatzeko

#### 6) Oinarrizko fluxua probatu
- testu txata
- audio bidalketa
- audio erreprodukzioa
- irudia/bideoa
- egoera/testuingurua

### Zer egin behar du AI agenteak
Agenteak hau jarraitu behar du:
- `docs/APPENCLAW_AI_REPLICA.md`

**as-is** moduan, agenteak **ez du Android toolchain-a behar** ezer berriz konpilatu behar ez bada.

Honakoa besterik ez du egin behar:
1. bridge host ingurunea prestatu
2. `scripts/appenclaw_chat_bridge.py` oinarrizko bridge-a sortu edo egokitu
3. bridge ingurune fitxategia sortu
4. zerbitzu iraunkorra konfiguratu (`systemd` gomendatua)
5. gizakiari azken endpoint + token-a eman
6. testua, eranskinak eta audioa balidatu

---

## B bidea — appenClaw-etik abiatuta assistant-app pertsonalizatua sortzea

### Gizakiak bere OpenClaw-ari eman behar dion mezua

Kopiatu eta itsatsi honelako instrukzio bat:

> "appenClaw-etik abiatuta assistant-app pertsonalizatu bat sortu nahi dut. Erabili `https://github.com/oriolfda/appenClaw` erreferentzia kanoniko gisa eta jarraitu zorrotz `docs/APPENCLAW_AI_REPLICA.md` modu pertsonalizatuan. Egin izenaren, ikonoaren, hizkuntzaren, gaiaren, STT/TTS hobespenen, helburuko agentearen, bridge portuaren eta deploy ereduaren intake interaktiboa. Ondoren, pertsonalizatu laneko biltegi egoki bat, konpilatu release APK bat, prestatu bridge espezifikoa eta utzi instalatzeko eta erabiltzeko argibide argiak."

### Zer egiten du gizakiak

#### 1) GitHub prestatu
Gomendioa: repo-a **gizakiarena** izatea, ez laguntzailearena.

Gomendatutako fluxua:
1. sortu repo propio bat GitHub-en
2. gehitu **deploy key** bat
3. agenteak `push` egin behar badu, aktibatu **Allow write access**
4. partekatu agentearekin:
   - repo-aren URL-a
   - SSH gakoaren kokapena hostean

#### 2) Pertsonalizazio informazioa prestatu
Agenteari lana eman aurretik, gizakiak argi izan beharko luke:
- app-aren izen ikusgaia
- ikonoa (PNG karratua, idealki 1024x1024)
- UI hizkuntza lehenetsia
- kolore gaia
- STT transkripzioak erakutsi nahi dituen ala ez
- TTS politika:
  - hizkuntzaren araberako automatikoa
  - edo ahots finko espezifikoa
- helburuko agentea
- bridge portua
- LAN bakarrik edo internetetik eskuragarri izango den
- domeinua/azpidomeinua + `nginx` nahi duen ala ez

#### 3) Publikazio ingurunea prestatu behar bada
Kanpo sarbidea nahi bada:
- domeinua/azpidomeinua
- `nginx` edo reverse proxy baliokidea
- TLS/HTTPS
- firewall/routerrean irekitako portuak
- bridge-a publikoki jarri aurretik gutxieneko segurtasun balidazioa

#### 4) APK pertsonalizatua probatu
Agenteak APK-a ematen dizunean:
- instalatu
- izena + ikonoa egiaztatu
- endpoint + token-a konfiguratu
- testua, audioa, irudia eta bideoa probatu
- arazo bisual edo funtzionalak jakinarazi

### Zer egin behar du AI agenteak
Agenteak hau jarraitu behar du:
- `docs/APPENCLAW_AI_REPLICA.md`

**pertsonalizatu** moduan, agenteak bai egin behar du:
1. intake interaktiboa egin gizakiarekin
2. Android ingurunea prestatu build-a behar bada
3. izena, ikonoa, gaia, hizkuntza eta bridge-a pertsonalizatu
4. STT/TTS konfiguratu eskatutako hobespen zehatzen arabera
5. release APK-a konpilatu
6. emaitza funtzionalki balidatu
7. azken instalazio eta mantentze argibideak utzi

---

## Laburpen azkarra: nork zer egiten du

### Gizakiak
- prebuilt APK-a deskargatzen du as-is moduan
- repo propioa sortzen du assistant-app pertsonalizatua nahi badu
- branding-a, audio politika eta publikazio eredua erabakitzen ditu
- domeinua, `nginx`, firewall-a eta kanpo sarbidea kudeatzen ditu beharrezkoa bada
- APK-a probatzen du eta feedback-a ematen du

### AI agentea
- bridge-a eta zerbitzu iraunkorra prestatzen ditu
- beharrezko gutxieneko datuak eskatzen ditu
- marka pertsonalizatzen du erabiltzaileak hala nahi badu
- Android SDK/JDK prestatu bakarrik berriz konpilatu behar bada
- APK-a konpilatu eta balidatzen du pertsonalizazio moduan

---

## Aplikazioak zer dauka

- testu txata
- audio grabazioa eta bidalketa
- irudi eta bideo eranskinak
- txateko audio erreprodukzioa
- HTML/kode errenderizazioa
- ikusizko gaiak
- UI lokalizazioa
- bridge laguntza endpoint + token bidez

---

## Hasierako UI hizkuntzak

- Català (`ca-ES`)
- Español (`es-ES`)
- English UK (`en-GB`)
- English US (`en-US`)
- Galego (`gl-ES`)
- Euskara (`eu-ES`)

---

## Dokumentu erabilgarriak

- `docs/APPENCLAW_AI_REPLICA.md` → AI agentearentzako gida operatiboa
- `docs/LOCALIZATION.md` → UI hizkuntzak gehitu edo itzuli
- `docs/templates/ui-locale-template.json` → itzulpen txantiloia

---

## Oinarrizko lege-oharra

appenClaw AI agenteentzako komunikazio interfazea da. Konfigurazioa, deploy-a, sare esposizioa eta azken erabilera hura hedatzen eta erabiltzen duenaren erantzukizuna dira.

Biltegiaren egile edo laguntzaileek ez dute erantzukizunik erabilera okerren, datu galeraren, segurtasun arazoen edo instalazio, konfigurazio edo erabileratik eratorritako kalteen aurrean.

---

## Esaldi batean

**appenClaw bere horretan deskargatu eta erabil dezakezu, edo OpenClaw agente batera konektatutako zure assistant-app propioa sortzeko oinarri gisa erabili.**
