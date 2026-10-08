"""Inflação implícita das NTN-B — o que o mercado precifica de IPCA até cada vencimento.

A conta é a de Fisher, título a título:

    (1 + pré) = (1 + juro real) · (1 + inflação implícita)
    inflação implícita = (1 + pré) / (1 + juro real) − 1

O juro real é a taxa indicativa da NTN-B no boletim da ANBIMA (``anbima.py``).
A pergunta é **qual pré** entra no numerador, e é aqui que esta página se
afasta da planilha da mesa: ela usa o CDI do dia, um número só, para todos os
vencimentos — e compara o juro real de 35 anos da NTN-B 2060 com a taxa de um
dia. A conta certa usa a taxa pré **do mesmo prazo**, lida na curva DI x Pré da
B3 no ponto da duration do título. A coluna "contra o CDI do dia" fica na tela
para conferir com a planilha, não para decidir.

**Por que na duration e não no vencimento.** A NTN-B paga cupom semestral: o
dinheiro dela chega espalhado no tempo, e a duration de Macaulay é o prazo
médio desse fluxo, ponderado pelo valor presente. É o prazo que representa o
título inteiro — no vencimento, a conta trataria uma NTN-B de 2060 como se
pagasse tudo em 2060, e a inflação implícita sairia dos 35 anos em vez dos
~14 que o título de fato tem.

**O fluxo.** Cupom de 6% a.a., pago em semestres: ``1,06^0,5 − 1`` =
2,956301% do VNA por semestre, no dia 15 dos meses do vencimento e seis meses
antes (maio/novembro ou fevereiro/agosto). Os prazos são em dias úteis ANBIMA
da data de referência até cada pagamento.

A duration daqui é conferida contra a que a ANBIMA publica no ANBIMA Data —
ver os testes. O VNA não precisa vir de fora: ``PU ÷ cotação`` dá o VNA
implícito, e ele tem de ser o mesmo para todas as NTN-B da data (é um número
só por dia). Se não for, o fluxo está errado.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from typing import Callable, List, Optional, Tuple

from .anbima import NTN_B, Titulo
from .calendario import Calendario, calendario_anbima, para_data, soma_meses

CUPOM_NTNB = 1.06 ** 0.5 - 1.0           # 2,956301% ao semestre
BASE = 252.0


@dataclass(frozen=True)
class Fluxo:
    data: date
    dias_uteis: int
    valor: float                         # por 1 de VNA: cupom, ou 1 + cupom no fim


def datas_de_cupom(vencimento, referencia) -> List[date]:
    """Do vencimento para trás, de seis em seis meses, enquanto for depois da referência."""
    venc, ref = para_data(vencimento), para_data(referencia)
    datas, n = [], 0
    while True:
        d = soma_meses(venc, -6 * n)
        if d <= ref:
            break
        datas.append(d)
        n += 1
    return sorted(datas)


def fluxos_ntnb(vencimento, referencia,
                calendario: Optional[Calendario] = None) -> List[Fluxo]:
    cal = calendario or calendario_anbima()
    ref = para_data(referencia)
    datas = datas_de_cupom(vencimento, ref)
    saida = []
    for i, d in enumerate(datas):
        valor = CUPOM_NTNB + (1.0 if i == len(datas) - 1 else 0.0)
        # O prazo é até o PAGAMENTO, que cai no dia útil seguinte quando o dia
        # 15 não é útil. Contando até o 15, a NTN-B 2027 em 07/10/2026 saía com
        # duration de 144,48 contra os 145,48 da ANBIMA: os dois pagamentos dela
        # (15/11/2026, domingo e feriado, e 15/05/2027, sábado) perdiam um dia.
        pagamento = cal.ajusta(d)
        saida.append(Fluxo(pagamento, cal.dias_uteis(ref, pagamento), valor))
    return saida


def cotacao(taxa: float, fluxos: List[Fluxo]) -> float:
    """Preço por 1 de VNA: Σ fluxo / (1 + taxa)^(DU/252)."""
    return sum(f.valor / (1.0 + taxa) ** (f.dias_uteis / BASE) for f in fluxos)


def cotacao_anbima(taxa: float, fluxos: List[Fluxo]) -> float:
    """A cotação como a ANBIMA a usa: truncada na 4ª casa do percentual.

    É ela, e não a exata, que multiplica o VNA para dar o PU publicado — por
    isso o VNA implícito sai do PU dividido por esta.
    """
    return int(cotacao(taxa, fluxos) * 1e6) / 1e6


def duration_du(taxa: float, fluxos: List[Fluxo]) -> float:
    """Duration de Macaulay em dias úteis: o prazo médio, ponderado pelo valor presente."""
    vps = [f.valor / (1.0 + taxa) ** (f.dias_uteis / BASE) for f in fluxos]
    total = sum(vps)
    return sum(f.dias_uteis * vp for f, vp in zip(fluxos, vps)) / total if total else 0.0


@dataclass
class LinhaImplicita:
    vencimento: date
    juro_real: float
    duration_du: float
    data_duration: date                  # o dia útil no ponto da duration
    dias_corridos: int
    pre: Optional[float]                 # da curva DI x Pré, no prazo da duration
    implicita: Optional[float]           # (1 + pré) / (1 + juro real) − 1
    implicita_cdi: Optional[float]       # contra o CDI do dia — a conta da planilha
    pu: Optional[float]
    vna_implicito: Optional[float]       # PU ÷ cotação — tem de ser igual em todas

    @property
    def duration_anos(self) -> float:
        return self.duration_du / BASE


def fisher(pre: float, real: float) -> float:
    return (1.0 + pre) / (1.0 + real) - 1.0


def calcular(titulos: List[Titulo],
             taxa_pre: Optional[Callable[[int, float], float]] = None,
             cdi: Optional[float] = None,
             calendario: Optional[Calendario] = None) -> List[LinhaImplicita]:
    """Uma linha por NTN-B do boletim, do vencimento mais curto ao mais longo.

    ``taxa_pre(dias_corridos, dias_uteis)`` é a curva DI x Pré — ``Curva.taxa_para``.
    Sem ela, a coluna principal fica vazia e só a do CDI aparece.
    """
    cal = calendario or calendario_anbima()
    linhas = []
    for t in sorted((t for t in titulos if t.tipo == NTN_B and t.taxa_indicativa is not None),
                    key=lambda t: t.vencimento):
        ref = t.referencia
        fluxos = fluxos_ntnb(t.vencimento, ref, cal)
        if not fluxos:
            continue
        real = t.taxa_indicativa
        dur = duration_du(real, fluxos)
        data_dur = cal.workday(ref, round(dur))
        dc = (data_dur - ref).days
        pre = taxa_pre(dc, dur) if taxa_pre else None
        cot = cotacao_anbima(real, fluxos)
        linhas.append(LinhaImplicita(
            vencimento=t.vencimento, juro_real=real, duration_du=dur,
            data_duration=data_dur, dias_corridos=dc, pre=pre,
            implicita=fisher(pre, real) if pre is not None else None,
            implicita_cdi=fisher(cdi, real) if cdi is not None else None,
            pu=t.pu, vna_implicito=(t.pu / cot) if (t.pu and cot) else None))
    return linhas


def vna_do_dia(linhas: List[LinhaImplicita]) -> Tuple[Optional[float], float]:
    """O VNA implícito (mediana) e a maior distância relativa entre os títulos.

    A distância é o termômetro do fluxo: com cupom e prazos certos, todas as
    NTN-B dão o mesmo VNA, a menos do truncamento do PU na sexta casa.
    """
    vnas = sorted(l.vna_implicito for l in linhas if l.vna_implicito)
    if not vnas:
        return None, 0.0
    meio = vnas[len(vnas) // 2]
    return meio, max(abs(v / meio - 1.0) for v in vnas)
