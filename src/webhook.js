import { createServer } from "node:http";
import { PORT, WEBHOOK_SECRET } from "./config.js";
import { carregar, salvar } from "./estado.js";
import { ehConversaPrivada, normalizar } from "./numero.js";
import { ehPedidoDeSaida } from "./protecao.js";
import { enviarProtegido } from "./mensageiro.js";
import { responder } from "./responder.js";

// Extrai o texto das variações de mensagem mais comuns do WhatsApp.
export function textoDa(msg = {}) {
  return (
    msg.conversation ||
    msg.extendedTextMessage?.text ||
    msg.imageMessage?.caption ||
    msg.videoMessage?.caption ||
    ""
  );
}

// Processa um evento. `enviar` é injetável para testes.
export async function tratarEvento(evento, { enviar = enviarProtegido } = {}) {
  const tipo = String(evento.event || "").toLowerCase().replace(/_/g, ".");

  if (tipo === "connection.update") {
    const st = evento.data?.state;
    if (st === "close") console.error(`⚠ [${evento.instance}] WhatsApp DESCONECTADO. Rode: npm run status`);
    else console.log(`[${evento.instance}] conexão: ${st}`);
    return null;
  }
  if (tipo !== "messages.upsert") return null;

  const d = evento.data || {};
  const jid = d.key?.remoteJid || "";
  if (d.key?.fromMe || !ehConversaPrivada(jid)) return null;

  let de;
  try { de = normalizar(d.key?.remoteJidAlt || jid); } catch { de = jid.split("@")[0]; }
  const texto = textoDa(d.message);
  const estado = carregar();

  // Webhooks podem chegar repetidos: ignora mensagem já processada.
  if (d.key?.id) {
    if (estado.vistos.includes(d.key.id)) return null;
    estado.vistos.push(d.key.id);
  }

  const primeiraVez = !estado.contatos[de];
  estado.contatos[de] = { nome: d.pushName, ultimaMensagem: Date.now() };
  console.log(`[${evento.instance}] ${d.pushName || de} (${de}): ${texto}`);

  let resposta;
  if (ehPedidoDeSaida(texto)) {
    estado.optOut[de] = Date.now();
    resposta = "Pronto, você não vai mais receber mensagens da Naia.";
  } else if (!estado.optOut[de]) {
    resposta = await responder({ de, nome: d.pushName, texto, primeiraVez });
  }
  salvar(estado);

  if (resposta) {
    // A confirmação de saída é a única mensagem que passa por cima do opt-out.
    const opcoes = { esperar: true, ignorarOptOut: ehPedidoDeSaida(texto) };
    await enviar(de, resposta, opcoes).catch((e) => console.error(`Não respondi ${de}: ${e.message}`));
  }
  return { de, nome: d.pushName, texto, resposta };
}

const servidor = createServer((req, res) => {
  const url = new URL(req.url, "http://x");
  if (req.method !== "POST" || url.pathname !== "/webhook") {
    res.writeHead(404).end();
    return;
  }
  if (WEBHOOK_SECRET && url.searchParams.get("token") !== WEBHOOK_SECRET) {
    res.writeHead(401).end();
    return;
  }
  let corpo = "";
  req.on("data", (c) => (corpo += c));
  req.on("end", () => {
    // Responde 200 na hora; processa depois (a Evolution não fica esperando).
    res.writeHead(200, { "Content-Type": "application/json" }).end('{"ok":true}');
    let evento;
    try { evento = JSON.parse(corpo); } catch { return console.error("Payload inválido"); }
    tratarEvento(evento).catch((e) => console.error("Erro no webhook:", e.message));
  });
});

if (import.meta.url === `file://${process.argv[1]}`) {
  servidor.listen(PORT, () => console.log(`Webhook ouvindo em http://localhost:${PORT}/webhook`));
}

export default servidor;
