# Naia: WhatsApp com Evolution API

Sem SDK mágico e sem pacote de terceiro. Só Node 18+ e `fetch`.
Número da Naia: **+55 21 96525-0104** (`NUMERO_NAIA=5521965250104`).

## 🛡️ Proteção do número (leia antes de tudo)

A Evolution API conecta pelo WhatsApp Web (não é a API oficial da Meta). O WhatsApp pode **banir o número**
se ele parecer robô ou receber denúncias. Por isso o código tem uma camada de proteção, e você precisa fazer
a sua parte no celular.

### O que você faz no celular (uma vez)

- [ ] **Ative a verificação em duas etapas** (WhatsApp > Configurações > Conta > Confirmação em duas etapas) e guarde o PIN.
      Sem ela, alguém com acesso ao seu chip pode registrar o número em outro aparelho.
- [ ] Coloque **e-mail de recuperação** nessa mesma tela.
- [ ] Use, de preferência, o **WhatsApp Business**, com nome, foto e descrição preenchidos.
- [ ] Mantenha o **chip ativo** (recarga, se for pré-pago) e o celular ligado à internet de vez em quando:
      a conexão do "Aparelho conectado" cai se o celular principal ficar uns 14 dias sem abrir o WhatsApp.
- [ ] Ative o **backup** das conversas (Google Drive ou iCloud).
- [ ] Se o número for novo, faça **aquecimento**: use o WhatsApp normalmente por 1 ou 2 semanas antes de automatizar,
      e comece com `LIMITE_NOVOS_POR_DIA=5`.

### O que o código já faz

| Proteção | Onde |
|---|---|
| Toda mensagem passa por `enviarProtegido()`; nada chama a API de envio direto | `src/mensageiro.js` |
| Limite por minuto, hora e dia, mais um intervalo mínimo entre mensagens | `src/protecao.js` |
| Limite diário para contatos que **nunca falaram** com a Naia (o maior risco de ban) | `src/protecao.js` |
| "Digitando..." antes de cada mensagem, com tempo proporcional ao texto e variado | `tempoDigitando()` |
| Confere se o número tem WhatsApp antes de mandar para contato novo | `temWhatsApp()` |
| Quem responde **SAIR / PARAR** nunca mais recebe mensagem (evita denúncia) | `src/webhook.js` |
| Nunca responde em grupos, status ou listas de transmissão | `ehConversaPrivada()` |
| Ignora webhooks duplicados (não responde duas vezes) | `estado.vistos` |
| Webhook protegido por token (`WEBHOOK_SECRET`) | `src/webhook.js` |
| O código **não** tem logout nem delete da instância: a sessão não cai por engano | `src/evolution.js` |
| Confere se o número pareado é mesmo o `NUMERO_NAIA` | `npm run conectar` / `npm run status` |
| Alerta no log quando o WhatsApp desconecta | evento `CONNECTION_UPDATE` |
| Sessão guardada em volumes (Postgres, Redis e instâncias): reiniciar não pede QR de novo | `docker-compose.yml` |

### O que **não** fazer

- Mandar mensagem em massa para lista comprada ou para quem não pediu.
- Mandar sempre o mesmo texto para muita gente.
- Aumentar os limites do `.env` sem motivo.
- Conectar o mesmo número em duas Evolution API ao mesmo tempo.

## 1. Subir a Evolution API (se ainda não tiver uma)

```bash
cp .env.example .env      # preencha EVO_TOKEN, POSTGRES_PASSWORD, WEBHOOK_URL e WEBHOOK_SECRET
docker compose up -d      # Evolution API em http://localhost:8080
```

## 2. Conectar

```bash
npm run conectar
```

1. Cria a instância `naia`. Se ela já existir, reaproveita: nunca apaga.
2. Salva o QR code em `qrcode.png`. No celular do número da Naia: **Aparelhos conectados > Conectar**.
3. Configura o webhook (`MESSAGES_UPSERT` e `CONNECTION_UPDATE`), com o token.
4. Espera conectar e confere se o número pareado é o `NUMERO_NAIA`.

## 3. Enviar

```bash
npm run enviar                                    # "Oi! Aqui é a Naia." para NUMERO_TESTE
npm run enviar -- "(21) 98888-7777" "Olá, tudo bem?"
```

## 4. Receber e responder

```bash
npm run webhook   # http://localhost:3000/webhook
```

A resposta automática fica em `src/responder.js`. Hoje a Naia só dá boas-vindas na primeira mensagem de cada contato.
É ali que entram as regras do negócio ou uma IA.
Para a Evolution API alcançar sua máquina, exponha a porta (ex.: `ngrok http 3000`) e use essa URL em `WEBHOOK_URL`.

## 5. Acompanhar

```bash
npm run status    # conexão, número pareado, envios nas últimas 24h, contatos e opt-outs
npm test          # testes da proteção e do webhook
```

O estado (contatos, opt-outs, envios) fica em `data/estado.json`. Faça backup desse arquivo.

Referência dos endpoints: [docs/evolution-api.md](docs/evolution-api.md).
