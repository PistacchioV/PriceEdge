/* Rede de segurança para o scroll-reveal do design system.
 *
 * reveal-and-parallax.js zera a opacidade de todo título e parágrafo dentro de
 * <main> e confia no IntersectionObserver para trazê-los de volta. Numa landing
 * page isso é inofensivo; numa ferramenta de trabalho não é — se o observer não
 * dispara (aba em segundo plano no momento da carga, impressão, movimento
 * reduzido, iframe sem render), o resultado do cálculo simplesmente não aparece.
 *
 * Este script não substitui o efeito: ele só revela o que já está na viewport,
 * a cada scroll e em alguns eventos de borda. A animação de entrada continua
 * exatamente como no design original. */

(function () {
  const seletor = "main :is(h1, h2, h3, h4, p, li), main .reveal, footer :is(h2, h3, h4, p, li)";

  function revelar(elemento) {
    if (elemento.style.opacity === "1") return;
    elemento.style.opacity = "1";
    elemento.style.transform = "translateY(0)";
  }

  function naViewport(elemento) {
    const caixa = elemento.getBoundingClientRect();
    const altura = window.innerHeight || document.documentElement.clientHeight;
    return caixa.top < altura && caixa.bottom > 0;
  }

  function varrer(tudo) {
    document.querySelectorAll(seletor).forEach((elemento) => {
      if (tudo || naViewport(elemento)) revelar(elemento);
    });
  }

  const semMovimento = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
  if (semMovimento) {
    varrer(true);
    return;
  }

  let agendado = false;
  function agendar() {
    if (agendado) return;
    agendado = true;
    requestAnimationFrame(() => {
      agendado = false;
      varrer(false);
    });
  }

  window.addEventListener("scroll", agendar, { passive: true });
  window.addEventListener("resize", agendar, { passive: true });
  document.addEventListener("visibilitychange", () => { if (!document.hidden) agendar(); });
  window.addEventListener("beforeprint", () => varrer(true));

  // As varreduras de borda chamam varrer() direto, sem requestAnimationFrame:
  // numa aba oculta o rAF fica congelado, que é justamente o cenário em que
  // esta rede de segurança precisa funcionar.
  setTimeout(() => varrer(false), 200);
  setTimeout(() => varrer(false), 1500);
})();
