// Marca a ponta que o solver vai calcular: o selo "calculada" no cartão dela e
// a dica "deixe vazio" no campo de valor. O servidor já desenha o estado
// inicial; isto só acompanha a troca no seletor, que não recarrega a página —
// sem isso o selo ficaria na ponta errada até o próximo envio.
(function () {
  "use strict";

  var resolver = document.getElementById("resolver");
  if (!resolver) return;

  function aplicar() {
    var cartoes = document.querySelectorAll("[data-ponta]");
    Array.prototype.forEach.call(cartoes, function (cartao) {
      var resolvida = cartao.getAttribute("data-ponta") === resolver.value;
      var selo = cartao.querySelector("[data-selo-resolvida]");
      if (selo) selo.hidden = !resolvida;
      var campo = cartao.querySelector("[data-valor-ponta]");
      if (campo) campo.placeholder = resolvida ? (campo.getAttribute("data-dica") || "") : "";
    });
  }

  resolver.addEventListener("change", aplicar);
  aplicar();
})();
