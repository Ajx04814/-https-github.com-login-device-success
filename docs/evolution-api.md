# Evolution API (v2): endpoints usados pela Naia

Toda chamada leva o header `apikey: <EVO_TOKEN>`.

| Passo | Método | Rota | Corpo |
|---|---|---|---|
| Criar instância | POST | `/instance/create` | `{ "instanceName": "naia", "qrcode": true, "integration": "WHATSAPP-BAILEYS" }` |
| Pedir QR code | GET | `/instance/connect/naia` | resposta: `{ "base64": "data:image/png;base64,..." }` |
| Estado da conexão | GET | `/instance/connectionState/naia` | resposta: `{ "instance": { "state": "open" } }` |
| Webhook | POST | `/webhook/set/naia` | `{ "webhook": { "enabled": true, "url": "...", "events": ["MESSAGES_UPSERT"] } }` |
| Enviar texto | POST | `/message/sendText/naia` | `{ "number": "5521965250104", "text": "Oi!" }` |

## Evento recebido (MESSAGES_UPSERT)

```json
{
  "event": "messages.upsert",
  "instance": "naia",
  "data": {
    "key": { "remoteJid": "5521965250104@s.whatsapp.net", "fromMe": false, "id": "..." },
    "pushName": "Fulano",
    "message": { "conversation": "Oi Naia" }
  }
}
```

O texto pode vir em `message.conversation` ou `message.extendedTextMessage.text`.
