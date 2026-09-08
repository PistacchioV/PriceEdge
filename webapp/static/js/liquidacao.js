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

  // A data do fixing acompanha o início do fluxo: D-2 dias úteis, que é
  // exatamente o que o motor usa. Antes o campo nascia vazio e o padrão ficava
  // implícito — quem confere uma liquidação contra a confirmação da contraparte
  // precisa *ver* de que dia a taxa a termo saiu, porque num fim de trimestre
  // D-2 e D-1 estão a vários pontos-base de distância.
  //
  // O dia útil vem do servidor. Refazer a contagem aqui criaria duas verdades
  // para a mesma pergunta — a do navegador e a do pacote — e elas divergiriam
  // no primeiro Carnaval, num campo que ninguém reconfere.
  function camposDeFixing() {
    var todos = document.querySelectorAll('input[id$="_data_fixing"]');
    // só os que ainda estão no automático: o campo digitado é escolha de
    // alguém, e sobrescrevê-lo perderia a data sem avisar
    return Array.prototype.filter.call(todos, function (campo) {
      return campo.value === (campo.getAttribute("data-padrao") || "");
    });
  }

  function trazerFixing() {
    var inicio = document.getElementById("inicio");
    var calendario = document.getElementById("calendario");
    if (!inicio || !inicio.value) return;
    var campos = camposDeFixing();
    if (!campos.length) return;

    var endereco = "/api/liquidacao/fixing?inicio=" + encodeURIComponent(inicio.value) +
      "&calendario=" + encodeURIComponent(calendario ? calendario.value : "ANBIMA");
    fetch(endereco)
      .then(function (r) { return r.json(); })
      .then(function (dados) {
        if (!dados || !dados.data) return;
        campos.forEach(function (campo) {
          campo.value = dados.data;
          campo.setAttribute("data-padrao", dados.data);
        });
      })
      .catch(function () {
        // sem rede o campo fica com o que já estava, e o motor calcula o D-2
        // sozinho no envio: a tela perde a prévia, não a conta
      });
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

    ["inicio", "calendario"].forEach(function (id) {
      var campo = document.getElementById(id);
      if (campo) campo.addEventListener("change", trazerFixing);
    });
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", iniciar);
  } else {
    iniciar();
  }
})();
