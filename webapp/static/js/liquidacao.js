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

  function iniciar() {
    var seletores = document.querySelectorAll(".campo-indexador");
    Array.prototype.forEach.call(seletores, function (seletor) {
      var lado = seletor.getAttribute("data-lado");
      aplicar(lado);
      seletor.addEventListener("change", function () { aplicar(lado); });
    });
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", iniciar);
  } else {
    iniciar();
  }
})();
