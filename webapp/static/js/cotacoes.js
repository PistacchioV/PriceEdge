// Trocar o tipo troca a lista de instrumentos e o instrumento escolhido. Sem
// isso a tela abre em PTAX com "USD" e, ao passar para Ações, continua pedindo
// USD ao Yahoo — que responde com um símbolo que não existe.
//
// As três listas vêm juntas no HTML (`data-instrumentos`), e não por chamada:
// são poucos kB, e uma ida ao servidor a cada troca de tipo deixaria a lista
// vazia enquanto ela não voltasse.
(function () {
  "use strict";

  function iniciar() {
    var tipo = document.getElementById("tipo");
    var campo = document.getElementById("instrumento");
    var lista = document.getElementById("lista-instrumentos");
    if (!tipo || !campo || !lista) return;

    var porTipo;
    try {
      porTipo = JSON.parse(tipo.getAttribute("data-instrumentos") || "{}");
    } catch (e) {
      return;                       // sem a lista, o campo livre continua servindo
    }

    tipo.addEventListener("change", function () {
      var itens = porTipo[tipo.value] || [];
      lista.innerHTML = "";
      itens.forEach(function (par) {
        var opcao = document.createElement("option");
        opcao.value = par[0];
        opcao.textContent = par[1];
        lista.appendChild(opcao);
      });
      // o instrumento do tipo anterior não vale no novo: abre no primeiro
      campo.value = itens.length ? itens[0][0] : "";
      campo.focus();
    });
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", iniciar);
  } else {
    iniciar();
  }
})();
