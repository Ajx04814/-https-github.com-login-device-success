# Evolution API (v2): endpoints usados pela Naia

Toda chamada leva o header `apikey: <EVO_TOKEN>`.

| Passo | Método | Rota | Corpo |
|---|---|---|---|
| Criar instância | POST | `/instance/create` | `{ "instanceName": "naia", "qrcode": true, "integration": "WHATSAPP-BAILEYS" }` |
| Pedir QR code | GET | `/instance/connect/naia` | resposta: `{ "base64": "data:image/png;base64,..." }` |
| Estado da conexão | GET | `/instance/connectionState/naia` | resposta: `{ "instance": { "state": "open" } }` |
| Webhook | POST | `/webhook/set/naia` | `{ "webhook": { "enabled": true, "url": "...", "events": ["MESSAGES_UPSERT"] } }` |
| Dados da instância | GET | `/instance/fetchInstances?instanceName=naia` | resposta: `[{ "ownerJid": "5521965250104@s.whatsapp.net", ... }]` |
| Número tem WhatsApp? | POST | `/chat/whatsappNumbers/naia` | `{ "numbers": ["5521965250104"] }` → `[{ "exists": true }]` |
| Enviar texto | POST | `/message/sendText/naia` | `{ "number": "5521965250104", "text": "Oi!", "delay": 2000 }` (`delay` = ms "digitando...") |

Rotas que a Naia **não** usa de propósito: `DELETE /instance/logout/naia` e `DELETE /instance/delete/naia`.
Elas derrubam a sessão e obrigam a ler o QR de novo.

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
