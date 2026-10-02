import { writeFileSync } from "node:fs";
import { exigir, INSTANCIA, WEBHOOK_URL } from "./config.js";
import { criarInstancia, conectarInstancia, estadoConexao, configurarWebhook } from "./evolution.js";

exigir("EVO_URL", "EVO_TOKEN");

function salvarQr(base64) {
  if (!base64) return false;
  writeFileSync("qrcode.png", Buffer.from(base64.replace(/^data:image\/\w+;base64,/, ""), "base64"));
  return true;
}

// 1. Cria a instância (se já existir, só pede um QR novo).
let qr;
try {
  const criada = await criarInstancia();
  console.log(`● POST /instance/create        ok (${INSTANCIA})`);
  qr = criada.qrcode?.base64;
} catch (e) {
  if (e.status !== 403 && e.status !== 409) throw e;
  console.log(`● Instância "${INSTANCIA}" já existe, reaproveitando`);
}

// 2. QR code.
const estado = (await estadoConexao()).instance?.state;
if (estado === "open") {
  console.log("● WhatsApp já está conectado");
} else {
  if (!qr) qr = (await conectarInstancia()).base64;
  if (salvarQr(qr)) console.log("● QR code salvo em qrcode.png (WhatsApp > Aparelhos conectados > Conectar)");
  else console.log("● Não veio QR code; confira a instância no painel da Evolution API");
}

// 3. Webhook.
if (WEBHOOK_URL) {
  await configurarWebhook(WEBHOOK_URL);
  console.log(`● Webhook configurado -> ${WEBHOOK_URL}`);
} else {
  console.log("● WEBHOOK_URL vazio no .env; webhook não configurado");
}

// 4. Espera o pareamento (até 2 minutos).
if (estado !== "open") {
  process.stdout.write("Aguardando leitura do QR code");
  for (let i = 0; i < 60; i++) {
    await new Promise((r) => setTimeout(r, 2000));
    if ((await estadoConexao()).instance?.state === "open") {
      console.log("\nConectado. Manda uma mensagem pra testar: npm run enviar");
      process.exit(0);
    }
    process.stdout.write(".");
  }
  console.log("\nAinda não conectou. Rode de novo para gerar um QR novo.");
  process.exit(1);
}
console.log("Conectado. Manda uma mensagem pra testar: npm run enviar");
