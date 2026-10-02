import { existsSync, readFileSync } from "node:fs";

// Lê o .env sem depender de pacote de terceiro.
if (existsSync(".env")) {
  for (const linha of readFileSync(".env", "utf8").split("\n")) {
    const m = linha.match(/^\s*([A-Z_][A-Z0-9_]*)\s*=\s*(.*)\s*$/);
    if (m && process.env[m[1]] === undefined) process.env[m[1]] = m[2].replace(/^["']|["']$/g, "");
  }
}

const num = (nome, padrao) => Number(process.env[nome] ?? padrao);

export const BASE = (process.env.EVO_URL || "").replace(/\/$/, "");
export const TOKEN = process.env.EVO_TOKEN;
export const INSTANCIA = process.env.EVO_INSTANCIA || "naia";
export const WEBHOOK_URL = process.env.WEBHOOK_URL;
export const WEBHOOK_SECRET = process.env.WEBHOOK_SECRET || "";
export const PORT = num("PORT", 3000);

// O número do chip conectado na Naia. É o número que estamos protegendo.
export const NUMERO_NAIA = process.env.NUMERO_NAIA || "5521965250104";
export const NUMERO_TESTE = process.env.NUMERO_TESTE || NUMERO_NAIA;

// Limites anti-banimento. Os padrões são conservadores de propósito.
export const LIMITES = {
  porMinuto: num("LIMITE_POR_MINUTO", 6),
  porHora: num("LIMITE_POR_HORA", 60),
  porDia: num("LIMITE_POR_DIA", 200),
  // Mensagens para contatos que nunca falaram com a Naia (o maior risco de ban).
  novosPorDia: num("LIMITE_NOVOS_POR_DIA", 10),
  intervaloMinMs: num("INTERVALO_MIN_MS", 3000),
  intervaloMaxMs: num("INTERVALO_MAX_MS", 8000),
};

export const ARQUIVO_ESTADO = process.env.ARQUIVO_ESTADO || "data/estado.json";

export function exigir(...nomes) {
  const faltando = nomes.filter((n) => !process.env[n]);
  if (faltando.length) {
    console.error(`Faltam variáveis no .env: ${faltando.join(", ")} (veja .env.example)`);
    process.exit(1);
  }
}
