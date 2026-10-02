import { writeFileSync } from "node:fs";
import { exigir, INSTANCIA, NUMERO_NAIA, WEBHOOK_SECRET, WEBHOOK_URL } from "./config.js";
import { criarInstancia, conectarInstancia, dadosInstancia, estadoConexao, configurarWebhook } from "./evolution.js";

exigir("EVO_URL", "EVO_TOKEN");

function salvarQr(base64) {
  if (!base64) return false;
  writeFileSync("qrcode.png", Buffer.from(base64.replace(/^data:image\/\w+;base64,/, ""), "base64"));
  return true;
}

async function conferirNumero() {
  const info = await dadosInstancia().catch(() => null);
  const conectado = String(info?.ownerJid || info?.owner || "").split("@")[0];
  if (!conectado) return;
  if (conectado === NUMERO_NAIA) console.log(`● Número conectado: ${conectado} (correto)`);
  else console.error(`⚠ Número conectado é ${conectado}, mas NUMERO_NAIA é ${NUMERO_NAIA}. Confira o celular usado no QR.`);
}

// 1. Cria a instância (se já existir, reaproveita a sessão: nunca apaga).
let qr;
try {
  const criada = await criarInstancia();
  console.log(`● POST /instance/create        ok (${INSTANCIA})`);
  qr = criada.qrcode?.base64;
} catch (e) {
  if (e.status !== 403 && e.status !== 409) throw e;
  console.log(`● Instância "${INSTANCIA}" já existe, reaproveitando`);
}

// 2. QR code (só se ainda não estiver conectado).
const estado = (await estadoConexao()).instance?.state;
if (estado === "open") {
  console.log("● WhatsApp já está conectado");
} else {
  if (!qr) qr = (await conectarInstancia()).base64;
  if (salvarQr(qr)) console.log(`● QR code salvo em qrcode.png. Leia com o celular do número ${NUMERO_NAIA} (Aparelhos conectados > Conectar)`);
  else console.log("● Não veio QR code; confira a instância no painel da Evolution API");
}

// 3. Webhook (com token, para ninguém de fora injetar mensagens falsas).
if (WEBHOOK_URL) {
  const url = new URL(WEBHOOK_URL);
  if (WEBHOOK_SECRET) url.searchParams.set("token", WEBHOOK_SECRET);
  await configurarWebhook(url.toString());
  console.log(`● Webhook configurado -> ${WEBHOOK_URL}${WEBHOOK_SECRET ? " (com token)" : ""}`);
} else {
  console.log("● WEBHOOK_URL vazio no .env; webhook não configurado");
}

// 4. Espera o pareamento (até 2 minutos).
if (estado !== "open") {
  process.stdout.write("Aguardando leitura do QR code");
  let ok = false;
  for (let i = 0; i < 60 && !ok; i++) {
    await new Promise((r) => setTimeout(r, 2000));
    ok = (await estadoConexao()).instance?.state === "open";
    if (!ok) process.stdout.write(".");
  }
  console.log("");
  if (!ok) {
    console.log("Ainda não conectou. Rode de novo para gerar um QR novo.");
    process.exit(1);
  }
}
await conferirNumero();
console.log("Conectado. Manda uma mensagem pra testar: npm run enviar");
