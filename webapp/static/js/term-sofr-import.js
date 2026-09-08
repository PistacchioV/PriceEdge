// Dropzone do relatório de Term SOFR da B3.
//
// O <input type="file"> continua sendo o mecanismo — a área arrastável é um
// <label> apontando para ele. Isso é de propósito: quem não arrasta clica, quem
// usa teclado chega pelo tab, e se este script não carregar o campo continua
// funcionando dentro de um formulário comum. Arrastar é a comodidade, não o
// caminho único.
(function () {
  "use strict";

  function iniciar() {
    var zona = document.getElementById("zona-termo");
    var campo = document.getElementById("arquivo-termo");
    var alvo = document.getElementById("alvo-termo");
    var rotulo = document.getElementById("rotulo-termo");
    var aviso = document.getElementById("aviso-termo");
    if (!zona || !campo || !alvo) return;

    var url = zona.getAttribute("data-url");
    var recarregar = zona.getAttribute("data-recarregar");
    var textoOriginal = rotulo ? rotulo.textContent : "";
    var ocupado = false;

    function mostrar(mensagem, tipo) {
      if (!aviso) return;
      aviso.textContent = mensagem;
      aviso.className = "mt-3 text-sm leading-6 font-geist " +
        (tipo === "erro" ? "text-rose-300" : "text-cyan-100");
      aviso.classList.remove("hidden");
    }

    function realcar(ligado) {
      alvo.classList.toggle("border-cyan-200/60", ligado);
      alvo.classList.toggle("bg-cyan-400/[0.08]", ligado);
    }

    function enviar(arquivo) {
      if (!arquivo || ocupado) return;
      ocupado = true;
      if (rotulo) rotulo.textContent = arquivo.name;
      mostrar("Lendo o arquivo…", "ok");

      var dados = new FormData();
      dados.append("arquivo", arquivo);

      fetch(url, { method: "POST", body: dados })
        .then(function (r) { return r.json().then(function (j) { return [r.ok, j]; }); })
        .then(function (par) {
          var ok = par[0], corpo = par[1];
          if (!ok) {
            // a mensagem vem do servidor por extenso: ela diz em que coluna o
            // ticker foi procurado, que é o que resolve um arquivo diferente
            mostrar(corpo.erro || "não foi possível importar o arquivo", "erro");
            if (rotulo) rotulo.textContent = textoOriginal;
            ocupado = false;
            return;
          }
          var partes = [corpo.aproveitadas + " cotações lidas"];
          if (corpo.novas) partes.push(corpo.novas + " datas novas");
          if (corpo.atualizadas) partes.push(corpo.atualizadas + " atualizadas");
          mostrar(partes.join(" · ") + ". Recarregando…", "ok");
          window.location.href = recarregar;
        })
        .catch(function (e) {
          mostrar("falha ao enviar o arquivo: " + e, "erro");
          if (rotulo) rotulo.textContent = textoOriginal;
          ocupado = false;
        });
    }

    campo.addEventListener("change", function () {
      enviar(campo.files && campo.files[0]);
    });

    ["dragenter", "dragover"].forEach(function (evento) {
      zona.addEventListener(evento, function (e) {
        e.preventDefault(); e.stopPropagation(); realcar(true);
      });
    });
    ["dragleave", "drop"].forEach(function (evento) {
      zona.addEventListener(evento, function (e) {
        e.preventDefault(); e.stopPropagation(); realcar(false);
      });
    });
    zona.addEventListener("drop", function (e) {
      var arquivos = e.dataTransfer && e.dataTransfer.files;
      if (arquivos && arquivos.length) enviar(arquivos[0]);
    });

    // sem isso, largar o arquivo fora da zona faz o navegador ABRIR o arquivo e
    // sair da página — com o formulário preenchido perdido junto
    ["dragover", "drop"].forEach(function (evento) {
      window.addEventListener(evento, function (e) {
        if (!zona.contains(e.target)) e.preventDefault();
      });
    });
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", iniciar);
  } else {
    iniciar();
  }
})();
