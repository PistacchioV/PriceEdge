/* Alternância de tema claro/escuro.
 *
 * A escolha fica em localStorage e é aplicada por um script inline no <head>,
 * antes da primeira pintura — aqui só cuidamos do clique e do ícone. Sem
 * preferência salva, segue o `prefers-color-scheme` do sistema. */

(function () {
  const raiz = document.documentElement;
  const botao = document.getElementById("btn-tema");
  if (!botao) return;

  function claro() {
    return raiz.getAttribute("data-tema") === "claro";
  }

  function pintarIcone() {
    const icone = botao.querySelector("iconify-icon");
    if (icone) icone.setAttribute("icon", claro() ? "solar:moon-linear" : "solar:sun-linear");
    botao.setAttribute("title", claro() ? "Mudar para o tema escuro" : "Mudar para o tema claro");
    botao.setAttribute("aria-pressed", String(claro()));
  }

  botao.addEventListener("click", () => {
    const novo = claro() ? "escuro" : "claro";
    if (novo === "claro") raiz.setAttribute("data-tema", "claro");
    else raiz.removeAttribute("data-tema");
    try { localStorage.setItem("tema", novo); } catch (e) { /* sem persistência */ }
    pintarIcone();
  });

  pintarIcone();
})();
