"""Leitura da curva DI: vértices de referência, taxa a termo e Copom implícito.

Tudo aqui recebe a curva já montada e o calendário — nada vai à rede. A tela
de análise e o boletim do mercado chamam as mesmas funções, e os testes
também, com curvas sintéticas.

A taxa a termo entre duas datas é a da capitalização 252:

    termo = ((1 + r2)^(du2/252) / (1 + r1)^(du1/252))^(252 / (du2 − du1)) − 1

e é o CDI médio que a curva precifica para o período. Entre reuniões do
Copom, é a Selic esperada naquele intervalo — com o prêmio de risco dentro:
é o que está precificado, não uma previsão.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, timedelta
from typing import List, Optional, Sequence, Tuple

from .calendario import Calendario, para_data, soma_meses
from .curvas import EXP252, Curva

BASE = 252

# os prazos que a mesa olha numa curva de juros, em meses
PRAZOS_PADRAO: List[Tuple[str, int]] = [
    ("3M", 3), ("6M", 6), ("1A", 12), ("2A", 24), ("3A", 36), ("5A", 60), ("10A", 120)]

# |Δ longo − Δ curto| até aqui é movimento paralelo, em bps
TOLERANCIA_PARALELO = 5.0

# a última reunião não tem a seguinte para fechar o período: fecha com este prazo,
# o intervalo típico entre duas reuniões do Copom
DIAS_APOS_ULTIMA_REUNIAO = 45


@dataclass
class Ponto:
    rotulo: str
    data: date
    dias_corridos: int
    dias_uteis: int
    taxa: float
    termo: Optional[float] = None        # a termo desde o ponto anterior
    fora_da_curva: bool = False          # depois do último vértice: extrapolado

    @property
    def anos(self) -> float:
        return self.dias_uteis / BASE


@dataclass
class Variacao:
    rotulo: str
    data: date
    taxa: float
    taxa_antes: Optional[float]

    @property
    def bps(self) -> Optional[float]:
        if self.taxa_antes is None:
            return None
        return (self.taxa - self.taxa_antes) * 10_000


@dataclass
class Reuniao:
    decisao: date
    vigencia: date                       # dia útil seguinte: quando a taxa nova vale
    fim: date                            # até a vigência da reunião seguinte
    cdi_implicito: float                 # a termo entre vigência e fim
    movimento_bps: float                 # contra o período anterior
    acumulado_bps: float                 # contra o período antes da 1ª reunião


@dataclass
class Copom:
    cdi_antes: float                     # a termo da data-base até a 1ª vigência
    reunioes: List[Reuniao]


def taxa_em(curva: Curva, base, alvo, calendario: Calendario) -> Tuple[int, int, float]:
    """(dias corridos, dias úteis, taxa) da curva numa data."""
    base, alvo = para_data(base), para_data(alvo)
    dc = (alvo - base).days
    du = calendario.dias_uteis(base, alvo)
    return dc, du, curva.taxa_para(dc, du)


def termo(taxa1: float, du1: int, taxa2: float, du2: int) -> float:
    """Taxa a termo 252 entre dois prazos em dias úteis."""
    if du2 <= du1:
        raise ValueError("o segundo prazo precisa ser mais longo que o primeiro")
    fator = (1 + taxa2) ** (du2 / BASE) / (1 + taxa1) ** (du1 / BASE)
    return fator ** (BASE / (du2 - du1)) - 1


def pontos(curva: Curva, base, calendario: Calendario,
           prazos: Sequence[Tuple[str, int]] = PRAZOS_PADRAO) -> List[Ponto]:
    """A curva nos prazos de referência, com a taxa a termo entre eles.

    A data de cada prazo é a data-base mais N meses, levada ao dia útil
    seguinte — é a data em que um contrato daquele prazo venceria. A termo só
    sai em curva exponencial 252; num cupom linear 360 ou num preço a termo a
    conta não faz sentido e fica vazia.
    """
    base = para_data(base)
    saida: List[Ponto] = []
    for rotulo, meses in prazos:
        alvo = calendario.ajusta(soma_meses(base, meses))
        dc, du, taxa = taxa_em(curva, base, alvo, calendario)
        p = Ponto(rotulo, alvo, dc, du, taxa,
                  fora_da_curva=bool(curva.prazo_maximo) and dc > curva.prazo_maximo)
        if curva.convencao == EXP252 and saida and du > saida[-1].dias_uteis:
            p.termo = termo(saida[-1].taxa, saida[-1].dias_uteis, taxa, du)
        saida.append(p)
    return saida


def variacoes(hoje: Sequence[Ponto], antes: Optional[Sequence[Ponto]]) -> List[Variacao]:
    """Δ por prazo: os dois lados casados pelo rótulo, não pela data.

    Comparar o "2A" de hoje com o "2A" de uma semana atrás é a leitura de
    curva constante (constant maturity), a que a mesa usa para dizer quanto
    a curva andou.
    """
    anteriores = {p.rotulo: p.taxa for p in (antes or [])}
    return [Variacao(p.rotulo, p.data, p.taxa, anteriores.get(p.rotulo)) for p in hoje]


def inclinacao_bps(pontos_curva: Sequence[Ponto], curto: str, longo: str) -> Optional[float]:
    por_rotulo = {p.rotulo: p.taxa for p in pontos_curva}
    if curto not in por_rotulo or longo not in por_rotulo:
        return None
    return (por_rotulo[longo] - por_rotulo[curto]) * 10_000


def classificar(delta_curto_bps: float, delta_longo_bps: float) -> str:
    """Nome do movimento da curva entre duas datas.

    Bull = taxas caindo (preço subindo), bear = subindo. Steepening = a ponta
    longa andou mais para cima (ou menos para baixo) que a curta.
    """
    media = (delta_curto_bps + delta_longo_bps) / 2
    diferenca = delta_longo_bps - delta_curto_bps
    if abs(diferenca) <= TOLERANCIA_PARALELO:
        if abs(media) < 1:
            return "Estável"
        return "Paralelo para cima" if media > 0 else "Paralelo para baixo"
    lado = "Bear" if media > 0 else "Bull"
    return f"{lado} steepening" if diferenca > 0 else f"{lado} flattening"


def copom(curva: Curva, base, calendario: Calendario,
          decisoes: Sequence) -> Optional[Copom]:
    """CDI implícito entre as reuniões do Copom.

    Cada decisão passa a valer no dia útil seguinte. O período de uma reunião
    vai da vigência dela até a vigência da próxima; a última fecha
    ``DIAS_APOS_ULTIMA_REUNIAO`` dias depois. Reuniões na data-base ou antes
    ficam de fora: o que já foi decidido está no CDI de hoje.
    """
    base = para_data(base)
    vigencias = sorted({(calendario.workday(para_data(d), 1), para_data(d))
                        for d in decisoes})
    vigencias = [(v, d) for v, d in vigencias if v > base]
    if not vigencias:
        return None
    fins = [v for v, _ in vigencias[1:]]
    fins.append(calendario.ajusta(vigencias[-1][0] + timedelta(days=DIAS_APOS_ULTIMA_REUNIAO)))

    _, du0, r0 = taxa_em(curva, base, vigencias[0][0], calendario)
    # o primeiro período começa na data-base: a termo de 0 a du0 é a própria taxa
    cdi_antes = r0
    anterior = cdi_antes
    reunioes: List[Reuniao] = []
    for (vigencia, decisao), fim in zip(vigencias, fins):
        _, du1, r1 = taxa_em(curva, base, vigencia, calendario)
        _, du2, r2 = taxa_em(curva, base, fim, calendario)
        implicito = termo(r1, du1, r2, du2) if du1 > 0 else r2
        reunioes.append(Reuniao(
            decisao=decisao, vigencia=vigencia, fim=fim, cdi_implicito=implicito,
            movimento_bps=(implicito - anterior) * 10_000,
            acumulado_bps=(implicito - cdi_antes) * 10_000))
        anterior = implicito
    return Copom(cdi_antes=cdi_antes, reunioes=reunioes)


def ler_datas(texto: str) -> List[date]:
    """Datas separadas por vírgula, ponto e vírgula, espaço ou linha."""
    datas = []
    for pedaco in (texto or "").replace(";", " ").replace(",", " ").split():
        datas.append(para_data(pedaco))
    return datas
