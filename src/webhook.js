import { createServer } from "node:http";
import { PORT } from "./config.js";

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

export function tratarEvento(evento) {
  const tipo = String(evento.event || "").toLowerCase().replace(/_/g, ".");
  if (tipo === "messages.upsert") {
    const d = evento.data || {};
    if (d.key?.fromMe) return null;
    const de = (d.key?.remoteJid || "").split("@")[0];
    const texto = textoDa(d.message);
    console.log(`[${evento.instance}] ${d.pushName || de} (${de}): ${texto}`);
    return { de, nome: d.pushName, texto };
  }
  if (tipo === "connection.update") {
    console.log(`[${evento.instance}] conexão: ${evento.data?.state}`);
  }
  return null;
}

const servidor = createServer((req, res) => {
  if (req.method !== "POST" || !req.url.startsWith("/webhook")) {
    res.writeHead(404).end();
    return;
  }
  let corpo = "";
  req.on("data", (c) => (corpo += c));
  req.on("end", () => {
    try {
      tratarEvento(JSON.parse(corpo));
    } catch (e) {
      console.error("Payload inválido:", e.message);
    }
    res.writeHead(200, { "Content-Type": "application/json" }).end('{"ok":true}');
  });
});

if (import.meta.url === `file://${process.argv[1]}`) {
  servidor.listen(PORT, () => console.log(`Webhook ouvindo em http://localhost:${PORT}/webhook`));
}

export default servidor;
