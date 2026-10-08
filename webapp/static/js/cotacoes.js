// Busca de instrumento da tela de cotações.
//
// Substitui o <datalist> nativo, que tinha três defeitos: mostrava só os
// códigos literais do cadastro (7 dos 17 de commodities — as famílias de
// vencimento, como BO"MY", não apareciam, e algodão e açúcar, que só existem
// como família, sumiam por completo); não buscava por nome nem por símbolo; e
// abria um popup branco, desenhado pelo navegador, fora do design system.
//
// O catálogo inteiro vem no HTML (`data-catalogos`). O que ele não tem é a
// resolução de um vencimento digitado — BOF6 → ZLF26.CBT —, e essa o script
// pergunta ao servidor: a regra das famílias mora no pacote, e uma cópia aqui
// seria uma segunda verdade que divergiria na primeira família nova.
(function () {
  "use strict";

  var EN = (document.documentElement.lang || "pt-BR").toLowerCase().indexOf("en") === 0;
  var TEXTOS = EN
    ? { familia: "contract family", exemplo: "e.g.", digite: "type month + year after the prefix — ",
        nada: "Nothing in the catalogue. The code is still sent as typed.",
        semMiolo: "No contract matches. After the prefix comes month + year: ",
        resolvido: "contract" }
    : { familia: "família de vencimentos", exemplo: "ex.", digite: "digite mês + ano depois do prefixo — ",
        nada: "Nada no cadastro. O código vai como foi digitado.",
        semMiolo: "Nenhum vencimento corresponde. Depois do prefixo vem mês + ano: ",
        resolvido: "vencimento" };
  var LIMITE = 60;

  function normal(texto) {
    return String(texto || "").normalize("NFD").replace(/[̀-ͯ]/g, "")
      .toUpperCase();
  }
  function compacto(texto) { return normal(texto).replace(/\s+/g, ""); }
  function escapar(texto) {
    return String(texto == null ? "" : texto).replace(/[&<>"]/g, function (c) {
      return { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c];
    });
  }

  function iniciar() {
    var tipo = document.getElementById("tipo");
    var campo = document.getElementById("instrumento");
    if (!tipo || !campo) return;

    var catalogos;
    try {
      catalogos = JSON.parse(tipo.getAttribute("data-catalogos") || "{}");
    } catch (e) {
      return;                       // sem o catálogo, o campo livre continua servindo
    }

    // A lista mora no <body>, com position: fixed — a mesma lição do
    // calendário: dentro do cartão do formulário, o backdrop-blur cria um
    // contexto de empilhamento e o rodapé seria pintado por cima dela.
    var lista = document.createElement("ul");
    lista.id = "lista-instrumentos";
    lista.className = "combo-lista";
    lista.setAttribute("role", "listbox");
    lista.hidden = true;
    document.body.appendChild(lista);

    var opcoes = [];               // o que está desenhado agora, na ordem
    var ativo = -1;
    var pedido = 0;                // descarta resposta atrasada do servidor
    var espera = null;

    function itens() { return catalogos[tipo.value] || []; }

    function posicionar() {
      var r = campo.getBoundingClientRect();
      lista.style.left = r.left + "px";
      lista.style.width = r.width + "px";
      var embaixo = window.innerHeight - r.bottom - 12;
      var emcima = r.top - 12;
      if (embaixo < 220 && emcima > embaixo) {
        lista.style.top = "";
        lista.style.bottom = (window.innerHeight - r.top + 6) + "px";
        lista.style.maxHeight = Math.min(360, emcima) + "px";
      } else {
        lista.style.bottom = "";
        lista.style.top = (r.bottom + 6) + "px";
        lista.style.maxHeight = Math.min(360, embaixo) + "px";
      }
    }

    function abrir() {
      lista.hidden = false;
      campo.setAttribute("aria-expanded", "true");
      posicionar();
    }

    function fechar() {
      lista.hidden = true;
      campo.setAttribute("aria-expanded", "false");
      campo.removeAttribute("aria-activedescendant");
      ativo = -1;
    }

    // A família cujo prefixo o texto digitado estende — o candidato a
    // vencimento. O resto depois do prefixo tem de ter cara de vencimento
    // (letra opcional + dígitos): sem essa exigência "soja" virava S + "OJA",
    // ia ao servidor e voltava com um aviso de vencimento que ninguém pediu.
    var CARA_DE_VENCIMENTO = /^[A-Z]?[0-9]{1,2}$/;
    function familiaDe(consulta) {
      var c = compacto(consulta);
      var melhor = null;
      itens().forEach(function (i) {
        if (!i.familia) return;
        var p = compacto(i.codigo);
        if (c.length > p.length && c.indexOf(p) === 0 &&
            CARA_DE_VENCIMENTO.test(c.slice(p.length)) &&
            (!melhor || p.length > compacto(melhor.codigo).length)) {
          melhor = i;
        }
      });
      return melhor;
    }

    function filtrar(consulta) {
      var c = normal(consulta).trim();
      var cc = compacto(consulta);
      if (!c) return itens().slice(0, LIMITE);
      var pontuados = [];
      itens().forEach(function (i) {
        var codigo = compacto(i.codigo);
        var simbolo = compacto(i.simbolo);
        var texto = normal(i.nome + " " + i.detalhe);
        var p = -1;
        if (codigo === cc) p = 0;
        else if (codigo.indexOf(cc) === 0) p = 1;
        else if (simbolo.indexOf(cc) === 0) p = 2;
        else if (codigo.indexOf(cc) > -1 || simbolo.indexOf(cc) > -1) p = 3;
        else if (texto.indexOf(c) > -1) p = 4;
        if (p > -1) pontuados.push([p, i]);
      });
      pontuados.sort(function (a, b) { return a[0] - b[0]; });
      return pontuados.slice(0, LIMITE).map(function (x) { return x[1]; });
    }

    function linha(item, indice) {
      if (item.aviso) {
        return '<li class="combo-aviso" role="presentation">' + escapar(item.aviso) + "</li>";
      }
      var selo = item.familia
        ? '<span class="combo-selo">' + escapar(TEXTOS.familia) + "</span>"
        : (item.resolvido ? '<span class="combo-selo combo-selo-ok">' + escapar(TEXTOS.resolvido) + "</span>" : "");
      var direita = item.familia
        ? escapar(TEXTOS.exemplo) + " " + escapar(item.exemplo) + " → " + escapar(item.simbolo)
        : escapar(item.simbolo);
      var nome = [item.nome, item.detalhe].filter(Boolean).join(" · ");
      return '<li class="combo-item" role="option" id="combo-op-' + indice + '" data-i="' + indice + '">' +
        '<div class="combo-linha"><span class="combo-codigo">' + escapar(item.familia ? item.codigo + "··" : item.codigo) +
        "</span>" + selo + '<span class="combo-simbolo">' + direita + "</span></div>" +
        (nome ? '<div class="combo-nome">' + escapar(nome) + "</div>" : "") + "</li>";
    }

    function desenhar(lista_de_itens) {
      opcoes = lista_de_itens;
      ativo = -1;
      if (!opcoes.length) {
        opcoes = [{ aviso: TEXTOS.nada }];
      }
      lista.innerHTML = opcoes.map(linha).join("");
      abrir();
    }

    function atualizar() {
      var consulta = campo.value;
      var base = filtrar(consulta);
      var familia = tipo.value === "commodities" ? familiaDe(consulta) : null;
      desenhar(base);
      if (!familia) return;

      // um vencimento digitado: o símbolo vem do servidor
      var meu = ++pedido;
      clearTimeout(espera);
      espera = setTimeout(function () {
        fetch("/api/cotacoes/simbolo?tipo=" + encodeURIComponent(tipo.value) +
              "&codigo=" + encodeURIComponent(consulta))
          .then(function (r) { return r.json(); })
          .then(function (dados) {
            if (meu !== pedido || campo.value !== consulta) return;   // chegou atrasada
            var topo = dados && dados.simbolo
              ? { codigo: consulta.toUpperCase(), simbolo: dados.simbolo, nome: familia.nome,
                  detalhe: familia.detalhe, resolvido: true }
              : { aviso: TEXTOS.semMiolo + familia.exemplo };
            desenhar([topo].concat(base.filter(function (i) { return !i.aviso; })));
          })
          .catch(function () { /* sem rede: a lista do catálogo continua valendo */ });
      }, 150);
    }

    function marcar(indice) {
      var nos = lista.querySelectorAll(".combo-item");
      Array.prototype.forEach.call(nos, function (n) { n.classList.remove("ativo"); });
      ativo = indice;
      var no = lista.querySelector('[data-i="' + indice + '"]');
      if (no) {
        no.classList.add("ativo");
        no.scrollIntoView({ block: "nearest" });
        campo.setAttribute("aria-activedescendant", no.id);
      }
    }

    function escolher(indice) {
      var item = opcoes[indice];
      if (!item || item.aviso) return;
      if (item.familia) {
        // família: o prefixo entra e a busca continua aberta pedindo mês + ano
        campo.value = item.codigo.trim();
        campo.focus();
        desenhar([{ aviso: TEXTOS.digite + TEXTOS.exemplo + " " + item.exemplo }]
                 .concat(filtrar(campo.value)));
        return;
      }
      campo.value = item.codigo;
      fechar();
    }

    campo.addEventListener("focus", atualizar);
    campo.addEventListener("input", atualizar);
    campo.addEventListener("keydown", function (e) {
      var selecionaveis = [];
      opcoes.forEach(function (o, i) { if (!o.aviso) selecionaveis.push(i); });
      if (e.key === "ArrowDown" || e.key === "ArrowUp") {
        if (lista.hidden) atualizar();
        if (!selecionaveis.length) return;
        e.preventDefault();
        var pos = selecionaveis.indexOf(ativo);
        pos = e.key === "ArrowDown" ? Math.min(pos + 1, selecionaveis.length - 1)
                                    : Math.max(pos - 1, 0);
        marcar(selecionaveis[pos < 0 ? 0 : pos]);
      } else if (e.key === "Enter" && !lista.hidden && ativo > -1) {
        e.preventDefault();               // Enter escolhe; não envia o formulário
        escolher(ativo);
      } else if (e.key === "Escape") {
        fechar();
      }
    });

    // mousedown sem preventDefault tiraria o foco do campo antes do clique
    lista.addEventListener("mousedown", function (e) { e.preventDefault(); });
    lista.addEventListener("click", function (e) {
      var no = e.target.closest(".combo-item");
      if (no) escolher(Number(no.getAttribute("data-i")));
    });

    document.addEventListener("click", function (e) {
      // redesenhar a lista tira o nó clicado do DOM antes de o clique chegar
      // aqui — o mesmo caso do calendário. Nó solto não conta como "fora".
      if (!document.contains(e.target)) return;
      if (e.target !== campo && !lista.contains(e.target)) fechar();
    });
    window.addEventListener("scroll", function () { if (!lista.hidden) posicionar(); }, true);
    window.addEventListener("resize", function () { if (!lista.hidden) posicionar(); });

    // trocar o tipo troca o catálogo, e o instrumento do tipo anterior não
    // vale no novo — sem isso a tela pediria USD ao Yahoo como se fosse ação
    tipo.addEventListener("change", function () {
      var primeiro = itens().filter(function (i) { return !i.familia; })[0];
      campo.value = primeiro ? primeiro.codigo : "";
      fechar();
      campo.focus();
    });
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", iniciar);
  } else {
    iniciar();
  }
})();
