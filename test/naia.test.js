import { test } from "node:test";
import assert from "node:assert/strict";
import { mkdtempSync } from "node:fs";
import { tmpdir } from "node:os";
import { join } from "node:path";

process.env.ARQUIVO_ESTADO = join(mkdtempSync(join(tmpdir(), "naia-")), "estado.json");
process.env.NUMERO_NAIA = "5521965250104";

const { normalizar, ehConversaPrivada } = await import("../src/numero.js");
const { podeEnviar, registrarEnvio, ehPedidoDeSaida } = await import("../src/protecao.js");
const { tratarEvento } = await import("../src/webhook.js");
const { carregar } = await import("../src/estado.js");

const LIM = { porMinuto: 3, porHora: 10, porDia: 20, novosPorDia: 2, intervaloMinMs: 1000, intervaloMaxMs: 2000 };
const vazio = () => ({ contatos: {}, optOut: {}, envios: [], vistos: [] });

test("normaliza o número da Naia em qualquer formato", () => {
  for (const n of ["21965250104", "(21) 96525-0104", "+55 21 96525-0104", "5521965250104@s.whatsapp.net"]) {
    assert.equal(normalizar(n), "5521965250104");
  }
  assert.throws(() => normalizar("12345"));
});

test("ignora grupos e status", () => {
  assert.equal(ehConversaPrivada("5521965250104@s.whatsapp.net"), true);
  assert.equal(ehConversaPrivada("123@g.us"), false);
  assert.equal(ehConversaPrivada("status@broadcast"), false);
});

test("respeita intervalo mínimo e limite por minuto", () => {
  const e = vazio();
  e.contatos["5521999999999"] = {};
  const t = 1_000_000;
  registrarEnvio(e, "5521999999999", t);
  assert.equal(podeEnviar(e, "5521999999999", t + 500, LIM).ok, false);
  registrarEnvio(e, "5521999999999", t + 1500);
  registrarEnvio(e, "5521999999999", t + 3000);
  const d = podeEnviar(e, "5521999999999", t + 5000, LIM);
  assert.equal(d.ok, false);
  assert.match(d.motivo, /minuto/);
});

test("limita mensagens para contatos que nunca falaram com a Naia", () => {
  const e = vazio();
  registrarEnvio(e, "5511900000001", 0);
  registrarEnvio(e, "5511900000002", 100_000);
  const d = podeEnviar(e, "5511900000003", 200_000, LIM);
  assert.equal(d.ok, false);
  assert.match(d.motivo, /novos/);
  // O próprio número da Naia e contatos conhecidos não contam como novos.
  assert.equal(podeEnviar(e, "5521965250104", 200_000, LIM).ok, true);
});

test("opt-out bloqueia envios", () => {
  const e = vazio();
  e.optOut["5521988887777"] = 1;
  assert.equal(podeEnviar(e, "5521988887777", 0, LIM).ok, false);
  assert.equal(podeEnviar(e, "5521988887777", 0, LIM, { ignorarOptOut: true }).ok, true);
  assert.equal(ehPedidoDeSaida(" Parar "), true);
  assert.equal(ehPedidoDeSaida("quero parar de pagar caro"), false);
});

const msg = (id, texto, extra = {}) => ({
  event: "messages.upsert",
  instance: "naia",
  data: { key: { id, remoteJid: "5521977776666@s.whatsapp.net", fromMe: false, ...extra }, pushName: "Ana", message: { conversation: texto } },
});

test("webhook: registra contato, responde a primeira vez, ignora duplicado e grupo", async () => {
  const enviados = [];
  const enviar = async (de, texto, op) => enviados.push({ de, texto, op });

  const r = await tratarEvento(msg("A1", "oi"), { enviar });
  assert.equal(r.de, "5521977776666");
  assert.equal(enviados.length, 1);
  assert.ok(carregar().contatos["5521977776666"]);

  assert.equal(await tratarEvento(msg("A1", "oi"), { enviar }), null);
  assert.equal(await tratarEvento(msg("G1", "oi", { remoteJid: "123@g.us" }), { enviar }), null);
  assert.equal(await tratarEvento(msg("F1", "oi", { fromMe: true }), { enviar }), null);

  await tratarEvento(msg("A2", "tudo bem?"), { enviar });
  assert.equal(enviados.length, 1, "não responde de novo fora da primeira vez");
});

test("webhook: SAIR marca opt-out e manda só a confirmação", async () => {
  const enviados = [];
  const enviar = async (de, texto, op) => enviados.push({ de, texto, op });
  await tratarEvento(msg("S1", "SAIR"), { enviar });
  assert.ok(carregar().optOut["5521977776666"]);
  assert.equal(enviados.length, 1);
  assert.equal(enviados[0].op.ignorarOptOut, true);
});
