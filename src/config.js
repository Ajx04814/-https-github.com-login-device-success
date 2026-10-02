import { existsSync, readFileSync } from "node:fs";

// Lê o .env sem depender de pacote de terceiro.
if (existsSync(".env")) {
  for (const linha of readFileSync(".env", "utf8").split("\n")) {
    const m = linha.match(/^\s*([A-Z_][A-Z0-9_]*)\s*=\s*(.*)\s*$/);
    if (m && process.env[m[1]] === undefined) process.env[m[1]] = m[2].replace(/^["']|["']$/g, "");
  }
}

export const BASE = (process.env.EVO_URL || "").replace(/\/$/, "");
export const TOKEN = process.env.EVO_TOKEN;
export const INSTANCIA = process.env.EVO_INSTANCIA || "naia";
export const WEBHOOK_URL = process.env.WEBHOOK_URL;
export const PORT = Number(process.env.PORT || 3000);
export const NUMERO_TESTE = process.env.NUMERO_TESTE || "5521965250104";

export function exigir(...nomes) {
  const faltando = nomes.filter((n) => !process.env[n]);
  if (faltando.length) {
    console.error(`Faltam variáveis no .env: ${faltando.join(", ")} (veja .env.example)`);
    process.exit(1);
  }
}
