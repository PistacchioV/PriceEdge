/* Formatação dos campos numéricos ao sair do foco.
 *
 *   data-formato="moeda"      ->  #,##0.00            (100.000.000,00)
 *   data-formato="taxa"       ->  #,##0.00000000 %    (2,50000000 %)
 *   data-formato="percentual" ->  #,##0.0000 %        (17,0000 %)
 *   data-formato="indice"     ->  #,##0.000000        (7.545,530000)
 *   data-formato="preco"      ->  #,##0.0000          (5,1500)
 *   data-formato="inteiro"    ->  #,##0               (12)
 *
 * A leitura tem que aceitar o que o usuário digita e também o que este mesmo
 * script escreveu de volta, então a regra de separador é idêntica à do
 * `_decimal` em webapp/servicos.py: com vírgula e ponto juntos o último manda;
 * só vírgula é decimal; vários pontos são milhar; um ponto só é decimal. */

(function () {
  const CASAS = { moeda: 2, taxa: 8, percentual: 4, indice: 6, preco: 4, inteiro: 0 };
  const COM_SIMBOLO = new Set(["taxa", "percentual"]);

  function ler(texto) {
    const limpo = String(texto || "")
      .replace(/%/g, "")
      .replace(/\s| /g, "")
      .trim();
    if (!limpo) return null;

    let normalizado;
    const temVirgula = limpo.includes(",");
    const temPonto = limpo.includes(".");

    if (temVirgula && temPonto) {
      normalizado = limpo.lastIndexOf(",") > limpo.lastIndexOf(".")
        ? limpo.replace(/\./g, "").replace(",", ".")
        : limpo.replace(/,/g, "");
    } else if (temVirgula) {
      normalizado = limpo.replace(",", ".");
    } else if ((limpo.match(/\./g) || []).length > 1) {
      normalizado = limpo.replace(/\./g, "");
    } else {
      normalizado = limpo;
    }

    const numero = Number(normalizado);
    return Number.isFinite(numero) ? numero : null;
  }

  function escrever(numero, casas) {
    return numero.toLocaleString("pt-BR", {
      minimumFractionDigits: casas,
      maximumFractionDigits: casas,
    });
  }

  function formatar(campo) {
    const tipo = campo.dataset.formato;
    const casas = CASAS[tipo];
    if (casas === undefined) return;

    const numero = ler(campo.value);
    if (numero === null) return;      // vazio ou ilegível: deixa como está,
                                      // o servidor devolve a mensagem de erro
    campo.value = escrever(numero, casas) + (COM_SIMBOLO.has(tipo) ? " %" : "");
  }

  const campos = document.querySelectorAll("[data-formato]");
  campos.forEach((campo) => {
    campo.addEventListener("blur", () => formatar(campo));
    // ao focar, tira o sufixo para não atrapalhar quem vai reescrever o valor
    campo.addEventListener("focus", () => {
      campo.value = campo.value.replace(/\s*%\s*$/, "");
      campo.select();
    });
  });

  // formata o que já veio preenchido do servidor
  campos.forEach(formatar);
})();

/* Indexadores retroativos (CDI realizado) não aceitam data futura, e não pedem
 * projeção. O servidor valida de qualquer jeito; isto só evita a ida e volta. */
(function () {
  const indexador = document.getElementById("indexador");
  const vencimento = document.getElementById("vencimento");
  if (!indexador || !vencimento) return;

  const retroativos = (indexador.dataset.retroativos || "").split(",").filter(Boolean);
  const projecao = document.getElementById("bloco-projecao");
  const aviso = document.getElementById("aviso-realizado");
  const hoje = vencimento.dataset.maximoHoje;

  function aplicar() {
    const retro = retroativos.includes(indexador.value);
    if (projecao) projecao.hidden = retro;
    if (aviso) aviso.hidden = !retro;
    // o campo de data pode ter virado o picker próprio; campoData abstrai isso
    if (window.campoData) {
      window.campoData.limiteMaximo(vencimento, retro && hoje ? hoje : "");
    }
  }

  indexador.addEventListener("change", aplicar);
  aplicar();
})();

/* Preenche a tela de NDF com o fechamento do BCB da moeda escolhida.
 *
 * O que vem daqui é PTAX, e PTAX não é spot: é a média que o Banco Central
 * apura em quatro janelas e publica às 13h, e é contra ela que o NDF liquida no
 * vencimento. O spot D+2 é a cotação de mesa com que ele é precificado — não há
 * fonte pública dela, então ela continua sendo digitada. Por isso o valor entra
 * como referência de liquidação e o aviso diz de onde veio. */
(function () {
  const botao = document.getElementById("btn-cambio");
  if (!botao) return;
  const aviso = document.getElementById("aviso-cambio");
  const original = botao.innerHTML;

  function formatar(valor, casas) {
    return Number(valor).toLocaleString("pt-BR", {
      minimumFractionDigits: casas, maximumFractionDigits: casas,
    });
  }

  function escrever(id, valor, casas) {
    const campo = document.getElementById(id);
    if (campo) campo.value = formatar(valor, casas);
  }

  botao.addEventListener("click", async () => {
    const data = document.querySelector('[name="data_curva"]')?.value || "";
    const moeda = document.getElementById("moeda")?.value || "USD";
    botao.disabled = true;
    botao.textContent = "...";
    try {
      const resposta = await fetch(
        `/api/cambio?data=${encodeURIComponent(data)}&moeda=${encodeURIComponent(moeda)}`);
      const dados = await resposta.json();
      if (!resposta.ok) throw new Error(dados.erro || "falha");

      escrever("ptax", dados.spot, dados.casas);
      (dados.futuros || []).forEach((f, i) => {
        escrever(i === 0 ? "primeiro_futuro" : "segundo_futuro", f.pontos, 2);
      });
      if (aviso) {
        const partes = [`${dados.fonte_spot} · ${dados.spot_data}`];
        if (dados.fonte_futuros) {
          partes.push(`${dados.fonte_futuros} (${dados.futuros.map((f) => f.vencimento).join(" · ")})`);
        }
        partes.push("PTAX é o fixing de liquidação; o spot D+2 de precificação continua sendo o digitado acima.");
        aviso.textContent = partes.join(" — ");
        aviso.hidden = false;
      }
    } catch (erro) {
      if (aviso) { aviso.textContent = erro.message.slice(0, 160); aviso.hidden = false; }
    } finally {
      botao.disabled = false;
      botao.innerHTML = original;
    }
  });
})();

/* Ajusta a tela de NDF à moeda escolhida e mantém o spot em dia.
 *
 * O spot é buscado sozinho: ao abrir a tela, ao trocar de moeda e ao trocar a
 * data-base. Ele vem da âncora curta da curva de preço da B3 — o ponto do qual
 * ela constrói o termo —, e não da PTAX, que é o fixing de liquidação e mora no
 * campo ao lado. Se o usuário digitou um spot próprio, a busca não o atropela;
 * só a troca de moeda, que muda o par, sobrescreve. */
(function () {
  const seletor = document.getElementById("moeda");
  if (!seletor) return;
  const spot = document.getElementById("spot");
  const data = document.querySelector('[name="data_curva"]');
  let ultimoAutomatico = spot ? spot.value : "";

  function mostrar(seletorCss, visivel) {
    document.querySelectorAll(seletorCss).forEach((el) => { el.hidden = !visivel; });
  }

  async function buscarSpot(forcar) {
    if (!spot) return;
    // um spot digitado à mão vale mais que a âncora da curva
    if (!forcar && spot.value && spot.value !== ultimoAutomatico) return;
    try {
      const r = await fetch(`/api/ndf/spot?moeda=${encodeURIComponent(seletor.value)}` +
                            `&data=${encodeURIComponent(data ? data.value : "")}`);
      const d = await r.json();
      if (!r.ok) return;
      const valor = d.spot ?? d.padrao;
      if (valor == null) return;
      spot.value = Number(valor).toLocaleString("pt-BR", {
        minimumFractionDigits: d.casas, maximumFractionDigits: d.casas,
      });
      ultimoAutomatico = spot.value;
    } catch (erro) { /* offline: fica o que estava no campo */ }
  }

  function aplicar(forcar) {
    const opcao = seletor.selectedOptions[0];
    if (!opcao) return;
    mostrar(".so-dolar", opcao.value === "USD");
    mostrar(".so-manual", opcao.dataset.manual === "1");
    document.querySelectorAll(".nota-moeda").forEach((el) => {
      el.hidden = el.dataset.moeda !== opcao.value;
    });
    if (opcao.dataset.manual !== "1") buscarSpot(forcar);
  }

  seletor.addEventListener("change", () => aplicar(true));
  if (data) data.addEventListener("change", () => aplicar(false));
  aplicar(false);
})();

/* Testa cada fonte externa e mostra o resultado lado a lado.
 * Existe porque "deu erro na api" nao diz qual api, nem se o problema e a
 * fonte, a saida da rede ou a autenticacao. Todas falhando com timeout e
 * bloqueio de saida; uma so falhando e a fonte. */
(function () {
  const botao = document.getElementById("btn-testar-rede");
  if (!botao) return;
  const caixa = document.getElementById("resultado-rede");
  const original = botao.innerHTML;

  botao.addEventListener("click", async () => {
    botao.disabled = true;
    botao.textContent = "...";
    caixa.hidden = false;
    caixa.innerHTML = '<p class="text-xs text-slate-500 font-geist">testando…</p>';
    try {
      const dados = await (await fetch("/api/rede/testar")).json();
      caixa.innerHTML = dados.fontes.map((f) => `
        <div class="flex flex-wrap items-start gap-3 rounded-xl border px-4 py-3
                    ${f.ok ? "border-emerald-300/20 bg-emerald-400/[0.06]"
                           : "border-rose-300/20 bg-rose-400/[0.06]"}">
          <span class="mt-0.5 shrink-0 rounded-full px-2 py-0.5 text-[11px] font-medium
                       ${f.ok ? "bg-emerald-400/15 text-emerald-200"
                              : "bg-rose-400/15 text-rose-200"}">${f.ok ? "OK" : "FALHA"}</span>
          <div class="min-w-0">
            <p class="text-sm font-medium text-white font-geist">${f.fonte}</p>
            <p class="mt-0.5 break-words font-mono text-[11px] leading-5 text-slate-400">${f.detalhe}</p>
          </div>
        </div>`).join("");
    } catch (erro) {
      caixa.innerHTML = `<p class="text-xs text-rose-300 font-geist">${erro.message}</p>`;
    } finally {
      botao.disabled = false;
      botao.innerHTML = original;
    }
  });
})();
