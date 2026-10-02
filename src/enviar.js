import { exigir, NUMERO_TESTE } from "./config.js";
import { enviarProtegido } from "./mensageiro.js";

exigir("EVO_URL", "EVO_TOKEN");

// Uso: npm run enviar -- [numero] [texto]
const [numero = NUMERO_TESTE, ...resto] = process.argv.slice(2);
const texto = resto.join(" ") || "Oi! Aqui é a Naia.";

try {
  const res = await enviarProtegido(numero, texto);
  console.log(`Enviado para ${numero}: "${texto}" (id ${res.key?.id ?? "?"})`);
} catch (e) {
  console.error(e.message);
  process.exit(1);
}
