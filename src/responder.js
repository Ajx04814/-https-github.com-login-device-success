// Cérebro da Naia. Recebe a mensagem e devolve o texto da resposta (ou null para não responder).
// Troque por regras de negócio ou por uma IA quando quiser.
export async function responder({ nome, texto, primeiraVez }) {
  if (primeiraVez) {
    return `Oi${nome ? `, ${nome}` : ""}! Aqui é a Naia. Como posso ajudar? (Se não quiser mais receber mensagens, responda SAIR.)`;
  }
  return null;
}
