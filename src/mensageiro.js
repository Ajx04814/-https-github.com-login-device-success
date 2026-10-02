import { carregar, salvar } from "./estado.js";
import { normalizar } from "./numero.js";
import { podeEnviar, registrarEnvio, tempoDigitando } from "./protecao.js";
import { enviarTexto, temWhatsApp } from "./evolution.js";

// Toda mensagem da Naia passa por aqui. Nunca chame enviarTexto() direto.
export async function enviarProtegido(destino, texto, { esperar = true, ignorarOptOut = false } = {}) {
  const numero = normalizar(destino);
  let estado = carregar();

  for (;;) {
    const decisao = podeEnviar(estado, numero, Date.now(), undefined, { ignorarOptOut });
    if (decisao.ok) break;
    if (!esperar || !decisao.esperarMs) throw new Error(`Bloqueado pela proteção: ${decisao.motivo}`);
    console.log(`Aguardando ${Math.ceil(decisao.esperarMs / 1000)}s (${decisao.motivo})...`);
    await new Promise((r) => setTimeout(r, decisao.esperarMs));
    estado = carregar();
  }

  if (!estado.contatos[numero] && !(await temWhatsApp(numero))) {
    throw new Error(`${numero} não tem WhatsApp; envio cancelado`);
  }

  const res = await enviarTexto(numero, texto, tempoDigitando(texto));
  estado = carregar();
  registrarEnvio(estado, numero);
  salvar(estado);
  return res;
}
