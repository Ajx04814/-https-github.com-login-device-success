// Normaliza número brasileiro para o formato do WhatsApp: 55 + DDD + número.
// Aceita "(21) 96525-0104", "21965250104", "+55 21 96525-0104", "5521965250104@s.whatsapp.net".
export function normalizar(entrada) {
  let d = String(entrada || "").split("@")[0].replace(/\D/g, "");
  if (d.length === 10 || d.length === 11) d = "55" + d;
  if (!/^55[1-9]{2}\d{8,9}$/.test(d)) {
    throw new Error(`Número inválido: "${entrada}". Use DDD + número, ex.: 21965250104`);
  }
  return d;
}

// Grupos, listas de transmissão e status: a Naia nunca responde nesses.
export function ehConversaPrivada(remoteJid = "") {
  return remoteJid.endsWith("@s.whatsapp.net") || remoteJid.endsWith("@lid");
}
