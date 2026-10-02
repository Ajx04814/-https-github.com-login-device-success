# Naia: WhatsApp com Evolution API

Sem SDK mágico e sem pacote de terceiro. Só Node 18+ e `fetch`.

## 1. Configurar

```bash
cp .env.example .env   # preencha EVO_URL, EVO_TOKEN e WEBHOOK_URL
```

## 2. Conectar

```bash
npm run conectar
```

1. Cria a instância `naia` (`POST /instance/create`).
2. Salva o QR code em `qrcode.png`. Abra o WhatsApp, vá em **Aparelhos conectados**, toque em **Conectar** e leia o QR.
3. Configura o webhook (`MESSAGES_UPSERT`) para `WEBHOOK_URL`.
4. Fica esperando até a conexão abrir.

## 3. Enviar

```bash
npm run enviar                                  # manda "Oi! Aqui é a Naia." para NUMERO_TESTE
npm run enviar -- 5521965250104 "Olá, tudo bem?"
```

O envio inteiro é uma chamada (`src/evolution.js`):

```js
await fetch(BASE + "/message/sendText/" + INSTANCIA, {
  method: "POST",
  headers: { apikey: process.env.EVO_TOKEN, "Content-Type": "application/json" },
  body: JSON.stringify({ number: "5521965250104", text: "Oi! Aqui é a Naia." }),
});
```

## 4. Receber

```bash
npm run webhook   # ouve em http://localhost:3000/webhook
```

O evento `MESSAGES_UPSERT` chega nessa rota e é tratado em `tratarEvento()` (`src/webhook.js`).
Para a Evolution API alcançar sua máquina, exponha a porta (ex.: `ngrok http 3000`) e use essa URL em `WEBHOOK_URL`.

Referência dos endpoints: [docs/evolution-api.md](docs/evolution-api.md).
