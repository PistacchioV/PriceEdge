// Cada indexador pede campos diferentes, e mostrar todos de uma vez faz a tela
// pedir PTAX num swap de pré contra CDI. Cada bloco declara em que indexadores
// ele aparece (`data-mostrar-em`) e some nos outros — sem `hidden` no HTML, para
// que a tela continue completa se o JavaScript não carregar.
(function () {
  "use strict";

  function aplicar(lado) {
    var seletor = document.getElementById(lado + "_indexador");
    if (!seletor) return;
    var escolhido = seletor.value;
    var blocos = document.querySelectorAll('[data-bloco="' + lado + '"]');
    Array.prototype.forEach.call(blocos, function (bloco) {
      var lista = (bloco.getAttribute("data-mostrar-em") || "").split(",");
      bloco.hidden = lista.indexOf(escolhido) === -1;
    });
  }

  // Trocar o índice traz junto a contagem e o regime que o mercado usa nele:
  // DU/252 composto no CDI, no pré e no IPCA; ACT/360 simples no cupom cambial,
  // no SOFR, no Term SOFR e na EURIBOR. Os dois campos continuam editáveis —
  // quem liquida contra a confirmação de uma contraparte precisa reproduzir a
  // régua dela —, mas o padrão errado é um erro silencioso.
  //
  // Só roda no `change`: na carga inicial quem manda é o servidor, senão um
  // formulário devolvido com erro perderia a convenção que a pessoa escolheu.
  function trazerConvencao(lado, seletor) {
    var tabela;
    try {
      tabela = JSON.parse(seletor.getAttribute("data-convencoes") || "{}");
    } catch (e) {
      return;
    }
    var padrao = tabela[seletor.value];
    if (!padrao) return;
    var contagem = document.getElementById(lado + "_convencao");
    var regime = document.getElementById(lado + "_regime");
    if (contagem) contagem.value = padrao[0];
    if (regime) regime.value = padrao[1];
  }

  function iniciar() {
    var seletores = document.querySelectorAll(".campo-indexador");
    Array.prototype.forEach.call(seletores, function (seletor) {
      var lado = seletor.getAttribute("data-lado");
      aplicar(lado);
      seletor.addEventListener("change", function () {
        aplicar(lado);
        trazerConvencao(lado, seletor);
      });
    });
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", iniciar);
  } else {
    iniciar();
  }
})();
