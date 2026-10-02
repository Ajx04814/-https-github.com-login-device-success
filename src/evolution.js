import { BASE, TOKEN, INSTANCIA } from "./config.js";

async function chamar(metodo, caminho, corpo) {
  const res = await fetch(BASE + caminho, {
    method: metodo,
    headers: { apikey: TOKEN, "Content-Type": "application/json" },
    body: corpo ? JSON.stringify(corpo) : undefined,
  });
  const texto = await res.text();
  let dados;
  try { dados = JSON.parse(texto); } catch { dados = texto; }
  if (!res.ok) {
    const erro = new Error(`${metodo} ${caminho} -> ${res.status}: ${typeof dados === "string" ? dados : JSON.stringify(dados)}`);
    erro.status = res.status;
    erro.dados = dados;
    throw erro;
  }
  return dados;
}

export const criarInstancia = () =>
  chamar("POST", "/instance/create", {
    instanceName: INSTANCIA,
    qrcode: true,
    integration: "WHATSAPP-BAILEYS",
  });

export const conectarInstancia = () => chamar("GET", `/instance/connect/${INSTANCIA}`);

export const estadoConexao = () => chamar("GET", `/instance/connectionState/${INSTANCIA}`);

export const configurarWebhook = (url) =>
  chamar("POST", `/webhook/set/${INSTANCIA}`, {
    webhook: {
      enabled: true,
      url,
      webhookByEvents: false,
      webhookBase64: false,
      events: ["MESSAGES_UPSERT", "CONNECTION_UPDATE"],
    },
  });

export const enviarTexto = (number, text) =>
  chamar("POST", `/message/sendText/${INSTANCIA}`, { number, text });
