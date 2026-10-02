import { existsSync, mkdirSync, readFileSync, renameSync, writeFileSync } from "node:fs";
import { dirname } from "node:path";
import { ARQUIVO_ESTADO } from "./config.js";

// Estado persistido em disco: quem já conversou, quem pediu para sair, histórico de envios.
const vazio = () => ({ contatos: {}, optOut: {}, envios: [], vistos: [] });

export function carregar(arquivo = ARQUIVO_ESTADO) {
  if (!existsSync(arquivo)) return vazio();
  try {
    return { ...vazio(), ...JSON.parse(readFileSync(arquivo, "utf8")) };
  } catch {
    // Nunca apaga um estado corrompido: guarda uma cópia e começa do zero.
    renameSync(arquivo, `${arquivo}.corrompido-${Date.now()}`);
    return vazio();
  }
}

export function salvar(estado, arquivo = ARQUIVO_ESTADO) {
  mkdirSync(dirname(arquivo), { recursive: true });
  const dia = 24 * 60 * 60 * 1000;
  estado.envios = estado.envios.filter((e) => Date.now() - e.em < dia);
  estado.vistos = estado.vistos.slice(-1000);
  // Grava em arquivo temporário e renomeia: não corrompe se o processo cair no meio.
  writeFileSync(`${arquivo}.tmp`, JSON.stringify(estado, null, 2));
  renameSync(`${arquivo}.tmp`, arquivo);
}
