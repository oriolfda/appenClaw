# AIGOR Web UI

Interfície web separada de l'app Android, amb el mateix canal de comunicació cap al bridge (`/chat`, `/status`).

## Executar en local

```bash
cd web
python3 -m http.server 8088
```

Obre: `http://localhost:8088`

## Què inclou

- Xat text
- Adjunt d'imatge/àudio/vídeo com `attachment.dataBase64`
- Configuració endpoint/token/session/prefs en `localStorage`
- Comprovació d'estat (`/status`)
- Reproducció de `mediaUrl` de resposta

## Notes

- És una base funcional separada del client Android.
- El look & feel segueix el tema fosc vermell de l'app (`#0B1018`, `#FF5C5C`, bombolles fosques).
