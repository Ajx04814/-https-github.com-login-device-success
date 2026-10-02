import { exigir, INSTANCIA, NUMERO_NAIA } from "./config.js";
import { dadosInstancia, estadoConexao } from "./evolution.js";
import { carregar } from "./estado.js";

exigir("EVO_URL", "EVO_TOKEN");

const estado = (await estadoConexao()).instance?.state;
console.log(`Instância ${INSTANCIA}: ${estado}`);

const info = await dadosInstancia().catch(() => null);
const conectado = String(info?.ownerJid || info?.owner || "").split("@")[0];
if (conectado) {
  const ok = conectado === NUMERO_NAIA;
  console.log(`Número conectado: ${conectado} ${ok ? "(correto)" : `⚠ esperado ${NUMERO_NAIA}`}`);
}

const local = carregar();
const dia = 24 * 60 * 60 * 1000;
const hoje = local.envios.filter((e) => Date.now() - e.em < dia);
console.log(`Envios nas últimas 24h: ${hoje.length} (${hoje.filter((e) => e.novo).length} para contatos novos)`);
console.log(`Contatos: ${Object.keys(local.contatos).length} · pediram para sair: ${Object.keys(local.optOut).length}`);
if (estado !== "open") process.exit(1);
