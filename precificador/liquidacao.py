"""Liquidação de swap — quanto de fato se paga, e sobre qual saldo.

A tela de precificação responde "quanto vale hoje": desconta fluxo futuro pelas
curvas da B3 e devolve MtM e taxa par. Esta responde a outra pergunta, a que
aparece no dia do caixa: **quanto uma parte paga à outra**. São contas
diferentes e nenhuma substitui a outra.

Três diferenças que valem por todo o módulo:

1. **Índice realizado, não projetado.** O CDI vem da série 4389 do Banco
   Central, dia a dia, e a variação cambial vem da PTAX publicada. Nada aqui
   sai de curva interpolada — é o que aconteceu. Por isso o fim do fluxo não
   pode passar de hoje quando alguma ponta é indexada.

2. **A base é o notional remanescente.** Num swap com amortização o principal
   cai a cada pagamento, e o que rende no fluxo seguinte é o que sobrou.
   Aplicar o notional original num swap já amortizado infla o ajuste na
   proporção exata do que já foi pago, e o erro passa despercebido porque a
   conta continua fechando consigo mesma. Aqui o saldo remanescente é campo de
   entrada, e é ele — não o notional de registro — que multiplica o fator das
   duas pontas.

3. **Só a diferença liquida.** O principal do swap é nocional: não troca de
   mãos. O que passa de uma parte para a outra é ``VF_ativa − VF_passiva``, e
   quem tem o resultado negativo paga.

As três datas não são a mesma coisa e o módulo as separa de propósito:

    data da operação   contratação — conta o prazo para a tabela do IR
    início do fluxo    onde os índices começam a acumular
    fim do fluxo       onde param, e a data do ajuste

Cada ponta escolhe a sua contagem de dias e o seu regime — DU/252, ACT/360,
ACT/365, 30/360, 30E/360 ou ACT/ACT, composto ou simples. O módulo ``contagem``
guarda essa parte; aqui entra apenas o τ que ela devolve:

    Pré              F = cap(i, τ)
    % do CDI         F = Π [ 1 + ((1 + DI_k)^(1/252) − 1) · p ]
    CDI + spread     F = Π (1 + DI_k)^(1/252) · cap(s, τ)
    Cambial          F = cap(c, τ)
    SOFR composto    F = Π (1 + SOFR_k · n/360) · cap(s, τ)
    Term SOFR        F = cap(fixing + s, τ)
    EURIBOR          F = cap(fixing + s, τ)
    IPCA             F = (NI_final / NI_inicial) · cap(c, τ)
    Equity           F = (preço_final / preço_inicial) · cap(s, τ)

e uma ponta em moeda estrangeira multiplica tudo isso pela variação cambial,
``fixing_final / fixing_inicial``. As duas metades ficam guardadas separadas no
resultado: dá para ver se o ajuste veio do índice ou do câmbio.

**Equity é a exceção: ela é quanto.** Ação e índice liquidam em reais sem
conversão — o retorno entra como número puro e o câmbio não participa. Quem
compra S&P via swap quer o S&P, não o S&P mais dólar. A moeda que a ponta
declara é de cotação, não de conversão, e o fator cambial dela é sempre 1.

onde ``cap(i, τ)`` é ``(1+i)^τ`` no regime composto e ``1 + i·τ`` no simples.

O acúmulo do CDI é a exceção que não se escolhe: ele é um produto de fatores
diários ``(1 + DI_k)^(1/252)``, um por fixing publicado, e essa capitalização
diária **é** a definição do índice. A contagem escolhida na ponta de CDI vale
para o spread, não para o produto — e a tela diz isso.

O motor não sabe nada de formulário: ele recebe duas ``Ponta`` e devolve um
``ResultadoLiquidacao``, e ``para_dict`` serializa tudo. Quem já tem a operação
registrada em base chama ``liquidar`` direto, sem passar pela tela.

A PTAX que entra nas pontas cambiais é a de **fechamento do dia útil anterior**
a cada data, que é como o swap registrado na B3 define a variação cambial. Quem
tiver a confirmação na mão digita as duas e a busca sai do caminho.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, timedelta
from typing import List, Optional

from . import cambio, cdi, contagem, euribor, sofr, term_sofr
from .calendario import (Calendario, calendario_anbima, calendario_sofr,
                         para_data)
from .renda_fixa import aliquota_ir
from .erros import ErroTraduzido

PRE = "pre"
CDI_PERCENTUAL = "cdi_percentual"
CDI_SPREAD = "cdi_spread"
MOEDA = "moeda"
CAMBIO = "cambio"
SOFR = "sofr"
TERM_SOFR = "term_sofr"
EURIBOR = "euribor"
IPCA = "ipca"
EQUITY = "equity"
FATOR = "fator"

INDEXADORES = [
    (PRE, "Pré — taxa fixa ao ano"),
    (CDI_PERCENTUAL, "CDI — % do CDI realizado"),
    (CDI_SPREAD, "CDI + spread realizado"),
    (MOEDA, "Moeda — só a variação cambial"),
    (CAMBIO, "Variação cambial + cupom"),
    (SOFR, "SOFR composto realizado + spread"),
    (TERM_SOFR, "Term SOFR do fixing + spread"),
    (EURIBOR, "EURIBOR do fixing + spread"),
    (IPCA, "IPCA por número-índice + cupom real"),
    (EQUITY, "Equity — ação ou índice, por variação de preço"),
    (FATOR, "Fator acumulado digitado"),
]
INDEXADOR_POR_CODIGO = dict(INDEXADORES)

# indexadores que leem o que já aconteceu: o fluxo não pode terminar no futuro
REALIZADOS = {CDI_PERCENTUAL, CDI_SPREAD, MOEDA, CAMBIO, SOFR, EURIBOR}

# indexadores cujo fluxo é denominado em moeda estrangeira. Todos eles pedem o
# par de fixings que traz a ponta de volta para reais — sem isso a variação
# cambial some da conta e o ajuste sai no tamanho errado.
# equity entra aqui porque um índice estrangeiro — S&P, Nasdaq, Euro Stoxx —
# rende na moeda dele e só vira reais depois da conversão
COM_MOEDA = {MOEDA, CAMBIO, SOFR, TERM_SOFR, EURIBOR}

# **Quanto.** A ponta de equity é cotada em moeda estrangeira e liquida em reais
# sem conversão: o retorno do índice entra como número puro, e a variação
# cambial não participa. É o desenho padrão do swap de ação e de índice no
# mercado local — quem compra S&P via swap quer o S&P, não o S&P mais dólar.
#
# Por isso equity **não** está em COM_MOEDA. A moeda dela é de cotação, para
# dizer em que régua o preço está, e não entra em conta nenhuma. Uma ponta que
# converte de verdade é a cambial, que existe ao lado justamente para isso.
QUANTO = {EQUITY}

# indexadores que declaram uma moeda na tela, convertendo ou não
DECLARAM_MOEDA = COM_MOEDA | QUANTO

# indexadores sem taxa nenhuma: não há o que capitalizar, então contagem de dias
# e regime não se aplicam — τ não entra em lugar nenhum da conta
SEM_TAXA = {MOEDA, FATOR}

# teto de lookback e observation shift, o mesmo da tela de SOFR Index
LIMITE_DEFASAGEM = 15

# A contagem e o regime de cada indexador, como o mercado os usa. Não são
# trava: a tela troca os dois ao escolher o índice e deixa mudar depois, porque
# quem liquida contra a confirmação de uma contraparte precisa reproduzir a
# régua dela — mas o padrão errado é um erro silencioso, e o certo evita a
# maioria das digitações.
#
#   DU/252 composto   o padrão brasileiro: DI, pré em real, IPCA. O juro
#                     capitaliza em dia útil, que é como o CDI é publicado.
#   ACT/360 simples   o padrão do mercado em dólar e em euro: cupom cambial,
#                     SOFR, Term SOFR e EURIBOR. Taxa a termo não capitaliza
#                     dentro do próprio período — ela é linear sobre ele.
#
# Equity fica em DU/252 composto porque a ponta é quanto: ela liquida em reais,
# contra uma perna de funding local, e o spread segue a régua de cá.
CONVENCAO_PADRAO = {
    PRE:            (contagem.DU_252, contagem.COMPOSTO),
    CDI_PERCENTUAL: (contagem.DU_252, contagem.COMPOSTO),
    CDI_SPREAD:     (contagem.DU_252, contagem.COMPOSTO),
    IPCA:           (contagem.DU_252, contagem.COMPOSTO),
    EQUITY:         (contagem.DU_252, contagem.COMPOSTO),
    FATOR:          (contagem.DU_252, contagem.COMPOSTO),
    MOEDA:          (contagem.ACT_360, contagem.SIMPLES),
    CAMBIO:         (contagem.ACT_360, contagem.SIMPLES),
    SOFR:           (contagem.ACT_360, contagem.SIMPLES),
    TERM_SOFR:      (contagem.ACT_360, contagem.SIMPLES),
    EURIBOR:        (contagem.ACT_360, contagem.SIMPLES),
}


def convencao_padrao(indexador: str) -> tuple:
    """``(contagem, regime)`` que o mercado usa naquele índice."""
    return CONVENCAO_PADRAO.get(indexador,
                                (contagem.DU_252, contagem.COMPOSTO))

# a moeda de cada índice, quando ele tem uma só
MOEDA_DO_INDEXADOR = {SOFR: "USD", TERM_SOFR: "USD", EURIBOR: "EUR"}

SEM_CONVERSAO = "BRL"


@dataclass(frozen=True)
class MoedaDeFluxo:
    """Uma moeda que a ponta pode declarar.

    ``automatica`` diz se o Banco Central boletina essa moeda. As que ele
    boletina têm PTAX buscada sozinha; as outras dependem dos dois fixings
    digitados, e a tela precisa avisar antes, não depois de dar erro.
    """
    codigo: str
    nome: str
    automatica: bool = True
    nota: str = ""


# As dez do boletim do BCB foram conferidas contra o endpoint de moedas do
# Olinda — é a lista fechada dele, não uma suposição. O que estiver fora dela
# não tem PTAX pública, e por isso entra aqui com ``automatica=False``.
MOEDAS = [
    MoedaDeFluxo(SEM_CONVERSAO, "Real — fluxo já em reais, sem conversão"),
    MoedaDeFluxo("USD", "Dólar dos Estados Unidos"),
    MoedaDeFluxo("EUR", "Euro"),
    MoedaDeFluxo("GBP", "Libra esterlina"),
    MoedaDeFluxo("JPY", "Iene"),
    MoedaDeFluxo("CHF", "Franco suíço"),
    MoedaDeFluxo("CAD", "Dólar canadense"),
    MoedaDeFluxo("AUD", "Dólar australiano"),
    MoedaDeFluxo("DKK", "Coroa dinamarquesa"),
    MoedaDeFluxo("NOK", "Coroa norueguesa"),
    MoedaDeFluxo("SEK", "Coroa sueca"),
    MoedaDeFluxo("CNH", "Yuan offshore", False,
                 "O BCB não boletina o yuan: os dois fixings entram digitados. "
                 "CNH é o offshore, negociado fora da China continental, e não é "
                 "a mesma cotação do CNY onshore."),
    MoedaDeFluxo("CNY", "Yuan onshore", False,
                 "O BCB não boletina o yuan: os dois fixings entram digitados."),
]
MOEDA_POR_CODIGO = {m.codigo: m for m in MOEDAS}
MOEDAS_AUTOMATICAS = {m.codigo for m in MOEDAS if m.automatica}

TENORES_EURIBOR = list(euribor.TENORES)
TENORES_TERM_SOFR = ["1 month", "3 month", "6 month", "12 month"]

# o tenor da tela em meses, que é como a base importada indexa os prazos
_MESES_DO_TENOR = {"1 week": 1, "1 month": 1, "3 month": 3,
                   "6 month": 6, "12 month": 12}

# indexadores de taxa a termo: a taxa é fixada antes do fluxo começar, e a data
# em que ela foi lida é campo próprio. O padrão do mercado é D-2 úteis do
# início — dois dias para o fixing publicado virar a taxa do período.
COM_FIXING = {TERM_SOFR, EURIBOR}
DEFASAGEM_FIXING = 2

ATIVA = "ativa"
PASSIVA = "passiva"


def nome_da_descricao(ponta: "PontaLiquidada") -> str:
    """A descrição da ponta já montada em português, para log e uso de fora.

    A tela recebe o molde separado dos números porque é bilíngue; quem chama o
    motor de outro sistema quer a frase pronta.
    """
    molde, valores = ponta.descricao
    return molde.format(**valores)

BASE_JUROS = "juros"
BASE_VALOR_FUTURO = "valor_futuro"
BASE_AUTOMATICA = "auto"

BASES_DE_AJUSTE = [
    (BASE_AUTOMATICA, "Pelas datas — juros no fluxo intermediário, valor futuro no vencimento"),
    (BASE_JUROS, "Só os juros — fluxo intermediário, o principal segue"),
    (BASE_VALOR_FUTURO, "Valor futuro das duas pontas — liquidação final"),
]

SOBRE_ORIGINAL = "original"
SOBRE_REMANESCENTE = "remanescente"

BASES_AMORTIZACAO = [
    (SOBRE_ORIGINAL, "Sobre o valor original — parcela constante"),
    (SOBRE_REMANESCENTE, "Sobre o saldo remanescente — parcela decrescente"),
]


class ErroLiquidacao(ErroTraduzido, ValueError):
    """Dado que falta ou não fecha para liquidar."""


def amortizar(nocional_original: float, saldo: float, percentual: float,
              base: str = SOBRE_ORIGINAL) -> float:
    """Quanto o percentual de amortização vale em dinheiro.

    Os mesmos "10%" dão dois números diferentes conforme a base, e a diferença
    cresce a cada parcela paga. Sobre o **valor original** a parcela é constante
    — 10% de 100 milhões são 10 milhões no primeiro fluxo e no último. Sobre o
    **saldo remanescente** ela é decrescente: 10% de um saldo de 60 milhões são
    6 milhões, e o principal nunca zera por amortização percentual.

    A amortização acontece **no fim do fluxo**: ela não entra no fator deste
    período, que rendeu sobre o saldo de abertura. Ela define o saldo do fluxo
    seguinte.
    """
    if percentual <= 0:
        return 0.0
    referencia = saldo if base == SOBRE_REMANESCENTE else nocional_original
    return min(saldo, referencia * percentual)


# ---------------------------------------------------------------- as pontas

@dataclass
class Ponta:
    """Como uma ponta do swap é remunerada.

    ``taxa`` é sempre decimal: 0,14 para 14% a.a. pré, 1,10 para 110% do CDI,
    0,02 para CDI+2%, 0,0325 para um cupom cambial de 3,25%.
    """
    indexador: str
    taxa: float = 0.0
    convencao: str = contagem.DU_252
    regime: str = contagem.COMPOSTO
    moeda: str = "USD"
    ptax_inicial: Optional[float] = None
    ptax_final: Optional[float] = None
    ni_inicial: Optional[float] = None
    ni_final: Optional[float] = None
    fator_manual: Optional[float] = None
    ativo: str = ""                        # equity: ticker ou nome do índice
    preco_inicial: Optional[float] = None  # equity
    preco_final: Optional[float] = None    # equity
    tenor: str = "3 month"                 # EURIBOR e Term SOFR
    data_fixing: Optional[date] = None     # padrão: D-2 úteis do início
    taxa_indice: Optional[float] = None    # Term SOFR entra digitado (licenciado)
    lookback: int = 0                      # SOFR composto
    shift: int = 0                         # SOFR composto


@dataclass(frozen=True)
class DiaDoFator:
    """Um dia do acúmulo, na mesma forma venha ele do CDI ou do SOFR.

    As duas fontes têm formatos próprios — ``cdi.DiaCDI`` traz ``data``,
    ``sofr.DiaComposicao`` traz ``data_juros`` e ``data_observacao``. A tela não
    tem por que saber disso, e enquanto soube ela quebrou: a tabela do resultado
    lia ``.data`` num objeto de SOFR e derrubava a página inteira.
    """
    data: date                              # o dia que rende
    taxa: float
    fator_dia: float
    fator_acumulado: float
    data_observacao: Optional[date] = None  # de onde a taxa veio, se for outra

    @property
    def defasado(self) -> bool:
        return bool(self.data_observacao and self.data_observacao != self.data)


def _dias_do_cdi(acumulado) -> List[DiaDoFator]:
    return [DiaDoFator(d.data, d.taxa, d.fator_dia, d.fator_acumulado)
            for d in acumulado.dias]


def _dias_do_sofr(composto) -> List[DiaDoFator]:
    return [DiaDoFator(d.data_juros, d.taxa, d.fator_dia, d.fator_acumulado,
                       d.data_observacao) for d in composto.dias]


@dataclass
class PontaLiquidada:
    """A ponta depois da conta: fator, valor e de onde o fator saiu."""
    indexador: str
    fator: float
    nocional: float
    valor: float
    descricao: tuple = ("", {})    # (molde, valores) — a tela é bilíngue
    convencao: Optional[str] = contagem.DU_252
    regime: Optional[str] = contagem.COMPOSTO
    dias_contados: Optional[int] = 0   # o numerador da convenção escolhida
    fracao_de_ano: Optional[float] = 0.0   # τ — None quando não há taxa
    contagem_vale_para_spread: bool = False
    dias_uteis: int = 0
    dias_corridos: int = 0
    moeda: Optional[str] = None
    quanto: bool = False           # cotada em moeda estrangeira, liquida sem converter
    fator_cambial: float = 1.0     # (fixing final / fixing inicial)
    fator_do_indice: float = 1.0   # o que a ponta rendeu na moeda dela
    ptax_inicial: Optional[float] = None
    ptax_final: Optional[float] = None
    data_ptax_inicial: Optional[date] = None
    data_ptax_final: Optional[date] = None
    data_fixing: Optional[date] = None
    taxa_do_fixing: Optional[float] = None
    tenor: Optional[str] = None
    ativo: Optional[str] = None
    preco_inicial: Optional[float] = None
    preco_final: Optional[float] = None
    defasagem: tuple = ("", {})        # (molde, valores) — lookback e shift
    obs_inicio: Optional[date] = None  # janela de observação do SOFR
    obs_fim: Optional[date] = None
    fixings: List["DiaDoFator"] = field(default_factory=list)

    @property
    def juros(self) -> float:
        """Só o que a **taxa** rendeu — a moeda fica de fora, na linha dela.

        Antes isto era ``valor − nocional``, que numa ponta cambial soma duas
        coisas de naturezas diferentes: o cupom, que é remuneração contratada, e
        a variação da moeda, que é mercado. Com o dólar caindo 2,88%, um cupom
        de 4,67% aparecia como juros **negativos** de R$ 2,58 MM — o número
        estava certo como soma e não respondia a nenhuma pergunta que alguém
        faça olhando para "juros do período".

        Os juros nascem na moeda da ponta e vêm para reais pelo fixing do fim:

            juros = nocional · (fixing_fim/fixing_ini) · (fator do índice − 1)
        """
        return self.nocional * self.fator_cambial * (self.fator_do_indice - 1.0)

    @property
    def efeito_cambial(self) -> float:
        """O que a moeda fez com o principal, sozinha.

        ``juros + efeito_cambial == valor − nocional``, sempre: a decomposição é
        exata, e é isso que permite mostrar as duas linhas sem que a soma deixe
        de fechar com o valor futuro.
        """
        return self.nocional * (self.fator_cambial - 1.0)


def _numero(valor: float, casas: int = 4) -> str:
    """Número já no padrão brasileiro, para entrar no molde da descrição."""
    return f"{valor:.{casas}f}".replace(".", ",")


def _ptax_do_dia_anterior(moeda: str, referencia: date) -> cambio.Ptax:
    """PTAX de fechamento do dia útil anterior — a convenção do contrato.

    A busca já anda para trás sozinha até dez dias, o que resolve fim de semana,
    feriado e o dia corrente antes das 13h.
    """
    return cambio.ptax_moeda(moeda, referencia - timedelta(days=1))


def data_de_fixing(inicio, calendario: Optional[Calendario] = None,
                   defasagem: int = DEFASAGEM_FIXING) -> date:
    """A data em que a taxa a termo foi lida — D-2 úteis do início do fluxo.

    EURIBOR e Term SOFR são taxas *forward-looking*: valem para o período
    inteiro e são fixadas antes de ele começar. Dois dias úteis é a defasagem
    padrão, e ela não é decoração — num fim de trimestre a taxa de D-2 e a de
    D-1 podem estar a vários pontos-base de distância.
    """
    cal = calendario or calendario_anbima()
    return cal.workday(para_data(inicio), -abs(defasagem))


def _fixing_euribor(tenor: str, quando: date) -> tuple:
    """Fixing da EURIBOR no prazo e na data — ou o último publicado antes dela."""
    curva = euribor.carregar()
    data, linha = curva.em(quando)
    if not linha or tenor not in linha:
        raise ErroLiquidacao(
            "não há fixing de EURIBOR {tenor} publicado até {data}",
            tenor=tenor, data=f"{quando:%d/%m/%Y}")
    return data, linha[tenor] / 100.0


def _fator_cambial(ponta: Ponta, d0: date, d1: date) -> tuple:
    """(fator, fixing inicial, fixing final, data inicial, data final).

    Sem conversão quando o fluxo já está em reais. Com conversão, os dois
    fixings entram digitados ou vêm da PTAX do dia útil anterior a cada data.
    """
    if ponta.indexador not in COM_MOEDA or ponta.moeda == SEM_CONVERSAO:
        # Preencher os dois fixings e deixar a moeda em Real é ambíguo, e as duas
        # leituras dão números diferentes: ou a conversão foi esquecida, ou os
        # fixings sobraram de outra tentativa. Descartar em silêncio é o pior dos
        # dois — o ajuste sai sem a variação cambial e nada na tela diz isso.
        if (ponta.moeda == SEM_CONVERSAO and ponta.indexador in COM_MOEDA
                and ponta.ptax_inicial is not None and ponta.ptax_final is not None):
            raise ErroLiquidacao(
                "os dois fixings de moeda estão preenchidos, mas a moeda do fluxo "
                "está em Real, que não converte. Escolha a moeda estrangeira para "
                "a variação cambial entrar na conta, ou apague os fixings.")
        return 1.0, None, None, None, None
    p0, p1 = ponta.ptax_inicial, ponta.ptax_final
    data0 = data1 = None
    if p0 is None or p1 is None:
        if ponta.moeda not in MOEDAS_AUTOMATICAS:
            # o BCB boletina dez moedas; fora delas não há PTAX para buscar, e o
            # erro precisa dizer isso em vez de falhar na fonte
            faltando = "inicial" if p0 is None else "final"
            raise ErroLiquidacao(
                "o Banco Central não boletina {moeda}: informe o fixing {qual} da "
                "moeda. Os dois entram digitados.",
                moeda=ponta.moeda, qual=faltando)
        b0 = _ptax_do_dia_anterior(ponta.moeda, d0)
        b1 = _ptax_do_dia_anterior(ponta.moeda, d1)
        p0 = p0 if p0 is not None else b0.venda
        p1 = p1 if p1 is not None else b1.venda
        data0, data1 = b0.data, b1.data
    if not p0:
        raise ErroLiquidacao("o fixing inicial da moeda não pode ser zero")
    return p1 / p0, p0, p1, data0, data1


def liquidar_ponta(ponta: Ponta, nocional: float, inicio, fim,
                   calendario: Optional[Calendario] = None,
                   arredondar_di: bool = False) -> PontaLiquidada:
    """Fator acumulado da ponta no fluxo, aplicado ao notional remanescente.

    O fator de uma ponta em moeda estrangeira tem duas metades que o módulo
    guarda separadas: o que ela rendeu **na moeda dela** e a variação cambial
    que a traz de volta para reais. Juntas viram um número só; separadas, dá
    para ver qual das duas explicou o ajuste.
    """
    cal = calendario or calendario_anbima()
    d0, d1 = para_data(inicio), para_data(fim)
    tau = contagem.fracao(ponta.convencao, d0, d1, cal)
    fx, p0, p1, data_p0, data_p1 = _fator_cambial(ponta, d0, d1)
    # numa ponta sem taxa a contagem não entrou em conta nenhuma; deixá-la no
    # resultado faria o consumidor achar que ela pesou no número
    sem_taxa = ponta.indexador in SEM_TAXA
    comum = dict(
        indexador=ponta.indexador, nocional=nocional,
        convencao=None if sem_taxa else ponta.convencao,
        regime=None if sem_taxa else ponta.regime,
        dias_contados=None if sem_taxa else contagem.dias(ponta.convencao, d0, d1, cal),
        fracao_de_ano=None if sem_taxa else tau,
        dias_uteis=cal.dias_uteis(d0, d1), dias_corridos=(d1 - d0).days,
        moeda=ponta.moeda if ponta.indexador in DECLARAM_MOEDA else None,
        quanto=ponta.indexador in QUANTO and ponta.moeda != SEM_CONVERSAO,
        fator_cambial=fx, ptax_inicial=p0, ptax_final=p1,
        data_ptax_inicial=data_p0, data_ptax_final=data_p1,
    )

    def capitalizar(taxa: float) -> float:
        return contagem.fator(taxa, ponta.convencao, ponta.regime, d0, d1, cal)

    def montar(indice: float, descricao: tuple, **extra) -> PontaLiquidada:
        fator = fx * indice
        return PontaLiquidada(fator=fator, valor=nocional * fator,
                              fator_do_indice=indice, descricao=descricao,
                              **comum, **extra)

    if ponta.indexador == PRE:
        return montar(capitalizar(ponta.taxa),
                      ("{taxa}% a.a. sobre τ = {tau}",
                       {"taxa": _numero(ponta.taxa * 100), "tau": _numero(tau, 6)}))

    if ponta.indexador in (CDI_PERCENTUAL, CDI_SPREAD):
        com_spread = ponta.indexador == CDI_SPREAD
        acumulado = cdi.acumular(cdi.serie(d0, d1), d0, d1, valor=1.0,
                                 percentual=1.0 if com_spread else ponta.taxa,
                                 arredondar=arredondar_di)
        indice = acumulado.fator
        if com_spread:
            # o produto diário é a definição do índice; a contagem escolhida
            # capitaliza só o spread, que é onde ela de fato tem escolha
            indice *= capitalizar(ponta.taxa)
            molde = "CDI + {taxa}% em {du} dias úteis publicados"
            valores = {"taxa": _numero(ponta.taxa * 100), "du": acumulado.dias_uteis}
        else:
            molde = "{taxa}% do CDI em {du} dias úteis publicados"
            valores = {"taxa": _numero(ponta.taxa * 100, 2), "du": acumulado.dias_uteis}
        return montar(indice, (molde, valores), fixings=_dias_do_cdi(acumulado),
                      contagem_vale_para_spread=com_spread)

    if ponta.indexador == MOEDA:
        if fx == 1.0 and ponta.moeda == SEM_CONVERSAO:
            raise ErroLiquidacao(
                "uma ponta de moeda pura precisa de uma moeda estrangeira — em "
                "reais ela não renderia nada")
        return montar(1.0, ("variação de {variacao}%, sem cupom",
                            {"variacao": _numero((fx - 1) * 100)}))

    if ponta.indexador == CAMBIO:
        return montar(
            capitalizar(ponta.taxa),
            ("variação de {variacao}% mais cupom de {taxa}% sobre τ = {tau}",
             {"variacao": _numero((fx - 1) * 100), "taxa": _numero(ponta.taxa * 100),
              "tau": _numero(tau, 6)}))

    if ponta.indexador == SOFR:
        for nome, valor in (("lookback", ponta.lookback), ("observation shift", ponta.shift)):
            if valor < 0 or valor > LIMITE_DEFASAGEM:
                raise ErroLiquidacao(
                    "o {defasagem} tem que ficar entre 0 e {teto} dias úteis",
                    defasagem=nome, teto=LIMITE_DEFASAGEM)
        # shift e lookback empurram a janela de observação para trás do início
        # do fluxo: buscar só o período deixaria a composição sem os fixings
        # que ela vai ler, e o erro apareceria na fonte, não aqui
        margem = timedelta(days=40 + (ponta.lookback + ponta.shift) * 2)
        composto = sofr.compor(sofr.serie_sofr(d0 - margem, d1 + timedelta(days=1)),
                               d0, d1, lookback=ponta.lookback, shift=ponta.shift,
                               calendario=calendario_sofr())
        indice = composto.fator * capitalizar(ponta.taxa)
        return montar(
            indice,
            ("SOFR composto de {sofr}% mais spread de {taxa}% em {dc} dias corridos",
             {"sofr": _numero(composto.taxa_composta * 100),
              "taxa": _numero(ponta.taxa * 100), "dc": composto.dias_corridos}),
            fixings=_dias_do_sofr(composto), taxa_do_fixing=composto.taxa_composta,
            defasagem=sofr.convencao(ponta.lookback, ponta.shift),
            obs_inicio=composto.obs_inicio, obs_fim=composto.obs_fim)

    if ponta.indexador in (TERM_SOFR, EURIBOR):
        quando = ponta.data_fixing or data_de_fixing(d0, cal)
        if ponta.indexador == EURIBOR:
            # a base local guarda o histórico; o Term SOFR da CME é licenciado
            # e não pode ser redistribuído, então ele entra digitado
            quando, taxa_indice = _fixing_euribor(ponta.tenor, quando)
        elif ponta.taxa_indice is None:
            # a taxa digitada continua vencendo; sem ela, procura no que o
            # usuário importou da B3 na tela de Term SOFR
            importada = term_sofr.carregar()
            achada = (None if importada.vazio
                      else importada.taxa(_MESES_DO_TENOR.get(ponta.tenor, 3), quando))
            if achada is None:
                raise ErroLiquidacao(
                    "o Term SOFR é licenciado pela CME e não tem fonte pública. "
                    "Informe a taxa do fixing, ou importe o relatório da B3 na "
                    "tela de Term SOFR.")
            taxa_indice = achada
            quando = importada.em(quando)[0] or quando
        else:
            taxa_indice = ponta.taxa_indice
        indice = capitalizar(taxa_indice + ponta.taxa)
        nome = "Term SOFR" if ponta.indexador == TERM_SOFR else "EURIBOR"
        return montar(
            indice,
            ("{nome} {tenor} de {indice}% mais spread de {taxa}%, fixado em {quando}",
             {"nome": nome, "tenor": ponta.tenor, "indice": _numero(taxa_indice * 100, 5),
              "taxa": _numero(ponta.taxa * 100), "quando": f"{quando:%d/%m/%Y}"}),
            data_fixing=quando, taxa_do_fixing=taxa_indice, tenor=ponta.tenor)

    if ponta.indexador == EQUITY:
        if not ponta.preco_inicial or ponta.preco_final is None:
            raise ErroLiquidacao(
                "a ponta de equity precisa do preço inicial e do preço final")
        retorno = ponta.preco_final / ponta.preco_inicial
        return montar(
            retorno * capitalizar(ponta.taxa),
            ("{ativo} variou {retorno}% mais spread de {taxa}%, sem conversão cambial",
             {"ativo": ponta.ativo or "equity",
              "retorno": _numero((retorno - 1) * 100),
              "taxa": _numero(ponta.taxa * 100)}),
            ativo=ponta.ativo or None, preco_inicial=ponta.preco_inicial,
            preco_final=ponta.preco_final)

    if ponta.indexador == IPCA:
        if not ponta.ni_inicial or ponta.ni_final is None:
            raise ErroLiquidacao(
                "a ponta de IPCA precisa do número-índice inicial e do final")
        correcao = ponta.ni_final / ponta.ni_inicial
        return montar(
            correcao * capitalizar(ponta.taxa),
            ("correção de {correcao}% mais cupom real de {taxa}% a.a.",
             {"correcao": _numero((correcao - 1) * 100),
              "taxa": _numero(ponta.taxa * 100)}))

    if ponta.indexador == FATOR:
        if ponta.fator_manual is None:
            raise ErroLiquidacao("informe o fator acumulado da ponta")
        return montar(ponta.fator_manual, ("fator digitado", {}))

    raise ErroLiquidacao("indexador desconhecido: {indexador}",
                         indexador=ponta.indexador)


# ------------------------------------------------------------- a liquidação

@dataclass
class ResultadoLiquidacao:
    data_operacao: date
    inicio: date
    fim: date
    vencimento: Optional[date]
    base_de_ajuste: str
    juros_da_ativa: float
    juros_da_passiva: float
    nocional: float
    nocional_original: float
    percentual_amortizacao: float
    base_amortizacao: str
    valor_amortizado: float
    saldo_seguinte: float
    ativa: PontaLiquidada
    passiva: PontaLiquidada
    ajuste_bruto: float
    quem_recebe: str
    dias_corridos: int
    dias_uteis: int
    dias_da_operacao: int
    aliquota_ir: float
    ir: float
    ajuste_liquido: float
    banco_paga: bool

    @property
    def diferenca_de_fator(self) -> float:
        """O ajuste em pontos de fator — o que sobra por real de notional."""
        if self.base_de_ajuste == BASE_JUROS:
            return (self.juros_da_ativa - self.juros_da_passiva) / self.nocional
        return self.ativa.fator - self.passiva.fator

    @property
    def so_juros(self) -> bool:
        return self.base_de_ajuste == BASE_JUROS

    @property
    def efeito_cambial_do_principal(self) -> float:
        """O que separa as duas bases: o câmbio sobre o principal.

        Existe para a tela poder mostrar a distância entre a liquidação de fluxo
        e a final sem obrigar ninguém a refazer a conta — é sempre esse número,
        nem mais nem menos.
        """
        futuro = self.ativa.valor - self.passiva.valor
        return futuro - (self.juros_da_ativa - self.juros_da_passiva)

    def para_dict(self) -> dict:
        """O resultado inteiro em tipos simples, pronto para JSON.

        Existe para quem chama o motor de fora da tela — outro sistema que já
        tem a operação registrada em base e só quer o ajuste de volta.
        """
        def ponta(p: PontaLiquidada) -> dict:
            saida = {k: v for k, v in p.__dict__.items() if k != "fixings"}
            saida["descricao"] = nome_da_descricao(p)
            saida["fixings"] = len(p.fixings)
            for campo in ("data_ptax_inicial", "data_ptax_final", "data_fixing"):
                if saida.get(campo):
                    saida[campo] = saida[campo].isoformat()
            return saida

        return {
            "data_operacao": self.data_operacao.isoformat(),
            "inicio": self.inicio.isoformat(), "fim": self.fim.isoformat(),
            "nocional": self.nocional, "nocional_original": self.nocional_original,
            "percentual_amortizacao": self.percentual_amortizacao,
            "base_amortizacao": self.base_amortizacao,
            "valor_amortizado": self.valor_amortizado,
            "saldo_seguinte": self.saldo_seguinte,
            "ativa": ponta(self.ativa), "passiva": ponta(self.passiva),
            "ajuste_bruto": self.ajuste_bruto, "quem_recebe": self.quem_recebe,
            "dias_corridos": self.dias_corridos, "dias_uteis": self.dias_uteis,
            "dias_da_operacao": self.dias_da_operacao,
            "aliquota_ir": self.aliquota_ir, "ir": self.ir,
            "ajuste_liquido": self.ajuste_liquido,
            "diferenca_de_fator": self.diferenca_de_fator,
        }


def juros_de(ponta: PontaLiquidada) -> float:
    """Atalho para ``ponta.juros`` — a conta mora lá, e mora numa só."""
    return ponta.juros


def base_de_ajuste(fim, vencimento, escolha: str = BASE_AUTOMATICA) -> str:
    """Qual das duas liquidações vale — pelas datas, quando não é escolhida.

    Um fluxo que termina **antes** do vencimento do swap não liquida principal:
    só o diferencial de juros muda de mãos, e o principal segue para o período
    seguinte. Netar valor futuro ali cobraria da contraparte a variação cambial
    de um principal que ninguém pagou.

    Sem a data de vencimento não há como saber, e o padrão é a liquidação final
    — que é o caso de um swap bullet, o mais comum de conferir.
    """
    if escolha in (BASE_JUROS, BASE_VALOR_FUTURO):
        return escolha
    if vencimento is None:
        return BASE_VALOR_FUTURO
    return BASE_JUROS if para_data(fim) < para_data(vencimento) else BASE_VALOR_FUTURO


def liquidar(data_operacao, inicio, fim, nocional: float,
             ponta_ativa: Ponta, ponta_passiva: Ponta,
             vencimento=None, base_ajuste: str = BASE_AUTOMATICA,
             nocional_original: Optional[float] = None,
             percentual_amortizacao: float = 0.0,
             base_amortizacao: str = SOBRE_ORIGINAL,
             calendario: Optional[Calendario] = None,
             arredondar_di: bool = False,
             reter_ir: bool = True) -> ResultadoLiquidacao:
    """Ajuste a pagar entre as duas pontas no fim do fluxo.

    ``nocional`` é o saldo remanescente na data de início do fluxo — o valor
    que de fato rende, já líquido das amortizações anteriores. As duas pontas
    acumulam sobre ele.

    ``percentual_amortizacao`` é o quanto do principal amortiza no fim deste
    fluxo, e ``base_amortizacao`` diz sobre o quê: o valor original de registro
    (``nocional_original``, que cai no remanescente quando não é informado) ou o
    próprio saldo remanescente. A amortização não muda o ajuste deste período —
    ela define o saldo que abre o próximo.

    ``vencimento`` é a data em que o swap acaba, e ela decide o que liquida: um
    fluxo que termina antes dela é intermediário, e nele só o diferencial de
    **juros** muda de mãos — o principal segue para o período seguinte. No
    vencimento liquidam os dois, e o ajuste é a diferença dos valores futuros.
    ``base_ajuste`` força uma das duas quando as datas não bastam.

    ``reter_ir`` aplica a tabela regressiva pelo prazo contado da **data da
    operação** até o fim do fluxo, que é o que a legislação olha. Ela só incide
    quando o **banco paga** — quando a ponta ativa perde —, porque a retenção é
    da fonte pagadora e é sobre o ganho de quem recebe. Com a ativa ganhando,
    quem recebe é o banco, e não há o que reter de si mesmo.
    """
    cal = calendario or calendario_anbima()
    dop = para_data(data_operacao)
    d0, d1 = para_data(inicio), para_data(fim)

    if d1 <= d0:
        raise ErroLiquidacao("o fim do fluxo tem que ser posterior ao início")
    if d0 < dop:
        raise ErroLiquidacao(
            "o fluxo não pode começar ({inicio}) antes da operação ({operacao})",
            inicio=f"{d0:%d/%m/%Y}", operacao=f"{dop:%d/%m/%Y}")
    if nocional <= 0:
        raise ErroLiquidacao("o notional remanescente tem que ser positivo")

    indexadores = {ponta_ativa.indexador, ponta_passiva.indexador}
    if indexadores & REALIZADOS and d1 > date.today():
        raise ErroLiquidacao(
            "a liquidação usa índice realizado, não projeção — o fim do fluxo não "
            "pode passar de hoje ({hoje})", hoje=f"{date.today():%d/%m/%Y}")

    original = float(nocional_original) if nocional_original else float(nocional)
    if original < nocional:
        raise ErroLiquidacao(
            "o notional remanescente não pode ser maior que o valor original")
    amortizado = amortizar(original, nocional, percentual_amortizacao,
                           base_amortizacao)

    ativa = liquidar_ponta(ponta_ativa, nocional, d0, d1, cal, arredondar_di)
    passiva = liquidar_ponta(ponta_passiva, nocional, d0, d1, cal, arredondar_di)

    dv = para_data(vencimento) if vencimento else None
    base = base_de_ajuste(d1, dv, base_ajuste)
    juros_ativa, juros_passiva = juros_de(ativa), juros_de(passiva)
    bruto = (juros_ativa - juros_passiva if base == BASE_JUROS
             else ativa.valor - passiva.valor)
    dias_operacao = (d1 - dop).days
    # A retenção é da FONTE PAGADORA, e a fonte pagadora aqui é o banco: ele só
    # retém quando é ele quem paga, isto é, quando a ponta ativa perde. Com a
    # ativa ganhando, quem recebe é o banco — não há o que reter de si mesmo, e
    # o imposto do outro lado é problema da contabilidade dele.
    #
    # Reter dos dois lados inflava o número em toda liquidação a favor do banco,
    # e o resultado parecia plausível porque a alíquota estava certa.
    banco_paga = bruto < 0
    pct_ir = aliquota_ir(dias_operacao) if (reter_ir and banco_paga) else 0.0
    ir = abs(bruto) * pct_ir if pct_ir else 0.0
    # o IR reduz o que sai do caixa, então ele encolhe o ajuste em módulo
    liquido = (bruto + ir) if bruto < 0 else (bruto - ir)

    return ResultadoLiquidacao(
        data_operacao=dop, inicio=d0, fim=d1, vencimento=dv,
        base_de_ajuste=base, juros_da_ativa=juros_ativa,
        juros_da_passiva=juros_passiva, nocional=float(nocional),
        nocional_original=original,
        percentual_amortizacao=percentual_amortizacao,
        base_amortizacao=base_amortizacao,
        valor_amortizado=amortizado, saldo_seguinte=nocional - amortizado,
        ativa=ativa, passiva=passiva, ajuste_bruto=bruto,
        quem_recebe=ATIVA if bruto > 0 else PASSIVA,
        dias_corridos=(d1 - d0).days, dias_uteis=cal.dias_uteis(d0, d1),
        dias_da_operacao=dias_operacao,
        aliquota_ir=pct_ir, ir=ir, ajuste_liquido=liquido,
        banco_paga=banco_paga,
    )
