import { LIMITES, NUMERO_NAIA, NUMERO_TESTE } from "./config.js";

const MIN = 60 * 1000;
const HORA = 60 * MIN;
const DIA = 24 * HORA;

export const PALAVRAS_SAIR = ["sair", "parar", "pare", "stop", "cancelar", "descadastrar"];

export const ehPedidoDeSaida = (texto = "") =>
  PALAVRAS_SAIR.includes(texto.trim().toLowerCase().normalize("NFD").replace(/[̀-ͯ]/g, ""));

const conhecido = (estado, numero) =>
  Boolean(estado.contatos[numero]) || numero === NUMERO_NAIA || numero === NUMERO_TESTE;

// Decide se pode enviar agora. Retorna { ok: true } ou { ok: false, motivo, esperarMs? }.
export function podeEnviar(estado, numero, agora = Date.now(), limites = LIMITES, { ignorarOptOut = false } = {}) {
  if (estado.optOut[numero] && !ignorarOptOut) return { ok: false, motivo: "contato pediu para não receber mensagens" };

  const desde = (ms) => estado.envios.filter((e) => agora - e.em < ms);
  if (desde(MIN).length >= limites.porMinuto) return { ok: false, motivo: "limite por minuto", esperarMs: MIN };
  if (desde(HORA).length >= limites.porHora) return { ok: false, motivo: "limite por hora", esperarMs: HORA };
  if (desde(DIA).length >= limites.porDia) return { ok: false, motivo: "limite diário" };

  if (!conhecido(estado, numero)) {
    const novos = desde(DIA).filter((e) => e.novo).length;
    if (novos >= limites.novosPorDia) {
      return { ok: false, motivo: "limite diário de contatos novos (quem nunca falou com a Naia)" };
    }
  }

  const ultimo = estado.envios.at(-1);
  if (ultimo && agora - ultimo.em < limites.intervaloMinMs) {
    return { ok: false, motivo: "intervalo mínimo entre mensagens", esperarMs: limites.intervaloMinMs - (agora - ultimo.em) };
  }
  return { ok: true };
}

export function registrarEnvio(estado, numero, agora = Date.now()) {
  estado.envios.push({ para: numero, em: agora, novo: !conhecido(estado, numero) });
}

// Tempo de "digitando..." proporcional ao texto, com variação, para não parecer robô.
export function tempoDigitando(texto, limites = LIMITES) {
  const base = Math.min(texto.length * 40, 6000);
  const extra = limites.intervaloMinMs + Math.random() * (limites.intervaloMaxMs - limites.intervaloMinMs);
  return Math.round(Math.max(1200, base + extra / 4));
}
