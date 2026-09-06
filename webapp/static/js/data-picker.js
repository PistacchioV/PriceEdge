/* Date picker próprio, no idioma da aplicação.
 *
 * O calendário nativo do <input type="date"> segue o idioma do **navegador**,
 * não o da página: com a aplicação em inglês o Chrome continuava mostrando
 * "setembro de 2026", "Hoje" e "Limpar". Como não dá para traduzir o widget
 * nativo, este script troca cada campo de data por um par
 *
 *     <input type="hidden" name="..." value="AAAA-MM-DD">   ← o que é enviado
 *     <input type="text">                                   ← o que se lê e digita
 *
 * mais um calendário desenhado na linguagem visual do design system.
 *
 * O valor enviado continua sendo ISO, então o servidor não muda. O campo de
 * texto aceita dd/mm/aaaa e aaaa-mm-dd digitados e normaliza ao sair do foco —
 * não se perde a digitação rápida, que num campo de data de mesa é o que mais
 * se usa. */

(function () {
  const raiz = document.documentElement;
  const EN = (raiz.lang || "pt-BR").toLowerCase().startsWith("en");

  // A data é sempre exibida e digitada em dd/mm/aaaa, nos dois idiomas — é o
  // formato do mercado aqui, e ambíguo em lugar nenhum quando o dia vem antes.
  const TEXTOS = EN
    ? { hoje: "Today", limpar: "Clear", abrir: "Open calendar",
        anterior: "Previous month", proximo: "Next month",
        formato: "dd/mm/yyyy" }
    : { hoje: "Hoje", limpar: "Limpar", abrir: "Abrir calendário",
        anterior: "Mês anterior", proximo: "Próximo mês",
        formato: "dd/mm/aaaa" };

  const MESES = EN
    ? ["January", "February", "March", "April", "May", "June",
       "July", "August", "September", "October", "November", "December"]
    : ["janeiro", "fevereiro", "março", "abril", "maio", "junho",
       "julho", "agosto", "setembro", "outubro", "novembro", "dezembro"];

  // as duas convenções começam a semana no domingo
  const DIAS = EN ? ["S", "M", "T", "W", "T", "F", "S"]
                  : ["D", "S", "T", "Q", "Q", "S", "S"];

  function iso(d) {
    const mes = String(d.getMonth() + 1).padStart(2, "0");
    const dia = String(d.getDate()).padStart(2, "0");
    return `${d.getFullYear()}-${mes}-${dia}`;
  }

  function deIso(texto) {
    const m = /^(\d{4})-(\d{2})-(\d{2})$/.exec((texto || "").trim());
    if (!m) return null;
    const d = new Date(+m[1], +m[2] - 1, +m[3]);
    return isNaN(d) ? null : d;
  }

  function exibir(texto) {
    const d = deIso(texto);
    if (!d) return "";
    return `${String(d.getDate()).padStart(2, "0")}/` +
           `${String(d.getMonth() + 1).padStart(2, "0")}/${d.getFullYear()}`;
  }

  /** Aplica dd/mm/aaaa a uma digitação em curso, pondo as barras sozinhas.
   *
   * Trabalha só com os dígitos: o que o usuário apagou, colou ou digitou vira
   * uma sequência de números, e as barras são reinseridas a partir dela. Assim
   * apagar por cima de uma barra funciona — some o dígito antes dela, que é o
   * que se espera —, em vez de o cursor travar num separador que a máscara
   * teima em repor.
   */
  function mascarar(bruto) {
    const d = (bruto || "").replace(/\D/g, "").slice(0, 8);
    if (d.length <= 2) return d;
    if (d.length <= 4) return `${d.slice(0, 2)}/${d.slice(2)}`;
    return `${d.slice(0, 2)}/${d.slice(2, 4)}/${d.slice(4)}`;
  }

  /** Quantos dígitos existem até certa posição — a âncora do cursor.
   *
   * Guardar a posição em caracteres não serve: a máscara insere barras e o
   * cursor escorrega. Contar dígitos é estável porque é o que o usuário digitou.
   */
  function digitosAte(texto, posicao) {
    return (texto.slice(0, posicao).match(/\d/g) || []).length;
  }

  /** A posição, no texto mascarado, logo depois do n-ésimo dígito. */
  function posicaoAposDigitos(texto, quantos) {
    if (quantos <= 0) return 0;
    let vistos = 0;
    for (let i = 0; i < texto.length; i += 1) {
      if (/\d/.test(texto[i])) {
        vistos += 1;
        if (vistos === quantos) return i + 1;
      }
    }
    return texto.length;
  }

  /** Aceita dd/mm/aaaa, dd-mm-aaaa e aaaa-mm-dd; devolve ISO ou "". */
  function interpretar(texto) {
    const limpo = (texto || "").trim();
    if (!limpo) return "";
    let m = /^(\d{4})[-/](\d{1,2})[-/](\d{1,2})$/.exec(limpo);
    if (m) return iso(new Date(+m[1], +m[2] - 1, +m[3]));
    m = /^(\d{1,2})[-/.](\d{1,2})[-/.](\d{2,4})$/.exec(limpo);   // dd/mm/aaaa
    if (m) {
      const ano = +m[3] < 100 ? 2000 + +m[3] : +m[3];
      const d = new Date(ano, +m[2] - 1, +m[1]);
      return isNaN(d) ? "" : iso(d);
    }
    m = /^(\d{2})(\d{2})(\d{4})$/.exec(limpo);                   // 06092026
    if (m) return iso(new Date(+m[3], +m[2] - 1, +m[1]));
    return "";
  }

  function trocar(original) {
    const caixa = document.createElement("div");
    caixa.className = "campo-data";

    const escondido = document.createElement("input");
    escondido.type = "hidden";
    escondido.name = original.name;
    escondido.value = original.value || "";

    const texto = document.createElement("input");
    texto.type = "text";
    texto.className = original.className;
    texto.id = original.id;
    texto.autocomplete = "off";
    texto.inputMode = "numeric";
    texto.placeholder = TEXTOS.formato;
    texto.value = exibir(escondido.value);
    if (original.required) texto.required = true;
    // leva junto os data-* do campo original (limites, ganchos de outros scripts)
    Object.entries(original.dataset).forEach(([chave, valor]) => {
      texto.dataset[chave] = valor;
    });

    const botao = document.createElement("button");
    botao.type = "button";
    botao.className = "campo-data-botao";
    botao.setAttribute("aria-label", TEXTOS.abrir);
    botao.innerHTML =
      '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.6" ' +
      'stroke-linecap="round"><path d="M8 2v4M16 2v4"/>' +
      '<rect x="3" y="4" width="18" height="18" rx="2"/><path d="M3 10h18"/></svg>';

    const painel = document.createElement("div");
    painel.className = "campo-data-painel";
    painel.hidden = true;

    caixa.append(escondido, texto, botao, painel);
    original.replaceWith(caixa);

    // limites herdados do campo original
    const maximo = original.getAttribute("max") || original.dataset.maximoHoje || "";
    const minimo = original.getAttribute("min") || "";
    if (maximo) escondido.dataset.max = maximo;
    if (minimo) escondido.dataset.min = minimo;

    let mesVisivel = deIso(escondido.value) || new Date();
    mesVisivel = new Date(mesVisivel.getFullYear(), mesVisivel.getMonth(), 1);

    function foraDosLimites(d) {
      const v = iso(d);
      if (escondido.dataset.max && v > escondido.dataset.max) return true;
      if (escondido.dataset.min && v < escondido.dataset.min) return true;
      return false;
    }

    function definir(valorIso) {
      escondido.value = valorIso;
      texto.value = exibir(valorIso);
      escondido.dispatchEvent(new Event("change", { bubbles: true }));
    }

    function desenhar() {
      const ano = mesVisivel.getFullYear();
      const mes = mesVisivel.getMonth();
      const primeiro = new Date(ano, mes, 1);
      const inicio = new Date(ano, mes, 1 - primeiro.getDay());
      const selecionado = escondido.value;
      const hoje = iso(new Date());

      let html =
        '<div class="campo-data-cabecalho">' +
          `<span>${MESES[mes]} ${EN ? "" : "de "}${ano}</span>` +
          `<span class="campo-data-navegacao">` +
            `<button type="button" data-passo="-1" aria-label="${TEXTOS.anterior}">&#8593;</button>` +
            `<button type="button" data-passo="1" aria-label="${TEXTOS.proximo}">&#8595;</button>` +
          "</span>" +
        "</div><div class=\"campo-data-grade\">";

      DIAS.forEach((d) => { html += `<span class="campo-data-semana">${d}</span>`; });

      for (let i = 0; i < 42; i += 1) {
        const dia = new Date(inicio.getFullYear(), inicio.getMonth(), inicio.getDate() + i);
        const valor = iso(dia);
        const classes = ["campo-data-dia"];
        if (dia.getMonth() !== mes) classes.push("fora");
        if (valor === selecionado) classes.push("escolhido");
        if (valor === hoje) classes.push("hoje");
        const bloqueado = foraDosLimites(dia) ? " disabled" : "";
        html += `<button type="button" class="${classes.join(" ")}" ` +
                `data-valor="${valor}"${bloqueado}>${dia.getDate()}</button>`;
      }

      html += '</div><div class="campo-data-rodape">' +
        `<button type="button" data-acao="limpar">${TEXTOS.limpar}</button>` +
        `<button type="button" data-acao="hoje">${TEXTOS.hoje}</button></div>`;
      painel.innerHTML = html;
    }

    function abrir() {
      const atual = deIso(escondido.value);
      if (atual) mesVisivel = new Date(atual.getFullYear(), atual.getMonth(), 1);
      desenhar();
      painel.hidden = false;
    }

    function fechar() { painel.hidden = true; }

    botao.addEventListener("click", () => (painel.hidden ? abrir() : fechar()));

    texto.addEventListener("focus", () => {
      abrir();
      // selecionar tudo ao entrar: digitar a data nova substitui a antiga inteira,
      // que é como se preenche uma data de mesa — sem apagar caractere a caractere.
      // setTimeout e não requestAnimationFrame: rAF não dispara em aba oculta, e
      // um campo que só seleciona quando a aba está visível é um campo que falha
      // exatamente na volta do usuário para ela.
      setTimeout(() => texto.select(), 0);
    });
    texto.addEventListener("click", () => {
      if (texto.selectionStart === texto.selectionEnd) texto.select();
    });

    texto.addEventListener("input", () => {
      // colar uma data ISO ainda funciona: ela é convertida antes de mascarar,
      // senão os dígitos de 2026-09-04 virariam 20/26/0904
      const iso4 = /^(\d{4})-(\d{2})-(\d{2})$/.exec(texto.value.trim());
      if (iso4) {
        texto.value = `${iso4[3]}/${iso4[2]}/${iso4[1]}`;
        texto.setSelectionRange(texto.value.length, texto.value.length);
        return;
      }

      const antes = texto.value;
      const cursor = texto.selectionStart;
      const mascarado = mascarar(antes);
      if (mascarado === antes) return;
      // o cursor volta ancorado no dígito, não na posição crua, para não escorregar
      // quando a máscara insere uma barra à frente dele
      const alvo = digitosAte(antes, cursor);
      texto.value = mascarado;
      const posicao = posicaoAposDigitos(mascarado, alvo);
      texto.setSelectionRange(posicao, posicao);
    });

    texto.addEventListener("blur", () => {
      const valor = interpretar(texto.value);
      if (valor) definir(valor);
      else if (!texto.value.trim()) definir("");
      else texto.value = exibir(escondido.value);   // ilegível: devolve o anterior
    });

    texto.addEventListener("keydown", (e) => {
      if (e.key === "Enter") { fechar(); }
      if (e.key === "Escape") { fechar(); texto.blur(); }
    });

    painel.addEventListener("mousedown", (e) => e.preventDefault());  // não perde o foco
    painel.addEventListener("click", (e) => {
      const alvo = e.target.closest("button");
      if (!alvo) return;
      if (alvo.dataset.passo) {
        mesVisivel = new Date(mesVisivel.getFullYear(),
                              mesVisivel.getMonth() + Number(alvo.dataset.passo), 1);
        desenhar();
        return;
      }
      if (alvo.dataset.acao === "limpar") { definir(""); fechar(); return; }
      if (alvo.dataset.acao === "hoje") {
        const hoje = new Date();
        if (!foraDosLimites(hoje)) definir(iso(hoje));
        fechar();
        return;
      }
      if (alvo.dataset.valor) { definir(alvo.dataset.valor); fechar(); }
    });

    document.addEventListener("click", (e) => {
      if (!caixa.contains(e.target)) fechar();
    });

    return { escondido, texto };
  }

  document.querySelectorAll('input[type="date"]').forEach(trocar);

  /* Deixa o resto do código enxergar o campo de data como um campo só:
     `valorDe(el)` e `definirLimiteMaximo(el, iso)` funcionam tanto no input
     nativo quanto no substituto. */
  window.campoData = {
    escondido(el) {
      const caixa = el && el.closest ? el.closest(".campo-data") : null;
      return caixa ? caixa.querySelector('input[type="hidden"]') : el;
    },
    limiteMaximo(el, valorIso) {
      const alvo = window.campoData.escondido(el);
      if (!alvo) return;
      if (valorIso) {
        alvo.dataset.max = valorIso;
        if (alvo.value && alvo.value > valorIso) {
          alvo.value = valorIso;
          if (alvo !== el) el.value = valorIso;
        }
      } else {
        delete alvo.dataset.max;
      }
      if (alvo === el) {
        if (valorIso) el.max = valorIso; else el.removeAttribute("max");
      }
    },
  };
})();
