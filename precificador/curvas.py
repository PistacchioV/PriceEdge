"""Curvas de juros.

Uma ``Curva`` guarda os vértices publicados (dias úteis, dias corridos, taxa) e
sabe responder três perguntas:

* qual a taxa spot para um prazo qualquer (interpolando entre vértices);
* qual o fator de desconto desse prazo;
* qual a taxa a termo (FRA) entre dois prazos.

O ponto delicado — e o que as planilhas fazem — é que a **interpolação é feita
sobre dias corridos** (``cubic_spline(Curvas!A:A; Curvas!B:B; DC)``) enquanto o
**desconto é feito sobre dias úteis** (``(1+i)^(DU/252)``).  Misturar os dois
eixos é o erro clássico; por isso ``fator_desconto`` exige os dois prazos.

Convenções suportadas:

``EXP252``  (1 + i) ** (du / 252)      — DI, IPCA, TR
``LIN360``  1 + i * dc / 360           — cupom cambial, Term SOFR, pré em dólar
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from typing import Dict, Iterable, List, Optional, Sequence

from . import interpolacao
from .calendario import Calendario, calendario_anbima, para_data, soma_meses

EXP252 = "EXP252"
LIN360 = "LIN360"
PRECO = "PRECO"        # a curva devolve preço a termo, não taxa


@dataclass(frozen=True)
class Vertice:
    dias_uteis: int
    dias_corridos: int
    taxa: float          # decimal (0.1465), não percentual


@dataclass
class Curva:
    """Curva de juros a partir de vértices de mercado."""

    nome: str
    data_referencia: date
    vertices: List[Vertice] = field(default_factory=list)
    convencao: str = EXP252
    metodo: str = "spline"
    extrapolar: str = "flat"
    eixo: str = "dc"
    calendario: Calendario = field(default_factory=calendario_anbima)

    # ------------------------------------------------------------ construção

    @classmethod
    def de_b3(cls, vertices_b3: Iterable, nome: str, data_referencia,
              convencao: str = EXP252, metodo: str = "spline",
              eixo: str = "dc", extrapolar: str = "flat") -> "Curva":
        """Constrói a curva a partir dos vértices do módulo ``b3``.

        A B3 publica taxa em percentual e preço em unidade da moeda no mesmo
        arquivo, na mesma coluna. Dividir por 100 vale para a taxa e estraga o
        preço — o dólar a termo de um ano viraria 0,055 em vez de 5,50.
        """
        escala = 1.0 if convencao == PRECO else 100.0
        vs = [Vertice(v.dias_uteis, v.dias_corridos, v.taxa / escala)
              for v in vertices_b3]
        return cls(nome=nome, data_referencia=para_data(data_referencia),
                   vertices=vs, convencao=convencao, metodo=metodo,
                   eixo=eixo, extrapolar=extrapolar)

    @classmethod
    def de_listas(cls, dias_corridos: Sequence[int], taxas: Sequence[float],
                  nome: str, data_referencia, dias_uteis: Optional[Sequence[int]] = None,
                  convencao: str = EXP252, metodo: str = "spline",
                  eixo: str = "dc") -> "Curva":
        du = list(dias_uteis) if dias_uteis is not None else [0] * len(list(dias_corridos))
        vs = [Vertice(int(u), int(dc), float(t))
              for u, dc, t in zip(du, dias_corridos, taxas)]
        return cls(nome=nome, data_referencia=para_data(data_referencia),
                   vertices=vs, convencao=convencao, metodo=metodo, eixo=eixo)

    # ------------------------------------------------------------- consultas

    @property
    def eixo_dc(self) -> List[float]:
        return [float(v.dias_corridos) for v in self.vertices]

    @property
    def eixo_du(self) -> List[float]:
        return [float(v.dias_uteis) for v in self.vertices]

    @property
    def eixo_x(self) -> List[float]:
        """O eixo contra o qual a curva é interpolada (``eixo`` manda)."""
        return self.eixo_du if self.eixo == "du" else self.eixo_dc

    @property
    def eixo_taxas(self) -> List[float]:
        return [float(v.taxa) for v in self.vertices]

    @property
    def eh_preco(self) -> bool:
        """True quando a curva publica preço a termo em vez de taxa."""
        return self.convencao == PRECO

    @property
    def prazo_maximo(self) -> int:
        return max((v.dias_corridos for v in self.vertices), default=0)

    def taxa(self, prazo: float) -> float:
        """Taxa spot anual para o prazo, interpolada entre os vértices.

        ``prazo`` tem que estar na mesma unidade do eixo da curva — use
        ``taxa_para`` quando você tiver os dois prazos em mãos e não quiser
        pensar em qual deles vai.
        """
        if not self.vertices:
            raise ValueError(f"curva {self.nome} sem vértices")
        if len(self.vertices) == 1:
            return self.vertices[0].taxa
        return interpolacao.interpolar(
            self.eixo_x, self.eixo_taxas, float(prazo),
            metodo=self.metodo, extrapolar=self.extrapolar,
        )

    def taxa_para(self, dias_corridos: float,
                  dias_uteis: Optional[float] = None) -> float:
        """Taxa do prazo, escolhendo sozinha o eixo certo.

        Consultar a curva no eixo errado — pedir DU numa curva indexada por DC,
        ou o contrário — devolve a taxa de um prazo diferente do pedido.  É um
        erro que aparece nas planilhas (ver README) e que este método evita.
        """
        if self.eixo == "du":
            if dias_uteis is None:
                raise ValueError(
                    f"a curva {self.nome} é interpolada em dias úteis; informe dias_uteis")
            return self.taxa(dias_uteis)
        return self.taxa(dias_corridos)

    def fator_capitalizacao(self, dias_corridos: float,
                            dias_uteis: Optional[float] = None,
                            taxa: Optional[float] = None) -> float:
        """(1+i)^(du/252) para EXP252, (1 + i*dc/360) para LIN360.

        Curva de preço não tem fator: PTX, EUR, JPY e INP publicam a moeda ou o
        índice **a termo**, não uma taxa. Capitalizar um preço não significa
        nada, e deixar passar silenciosamente daria um número plausível e errado.
        """
        if self.convencao == PRECO:
            raise ValueError(
                f"{self.nome} é uma curva de preço a termo, não de taxa — "
                "não há fator de capitalização. Use taxa_para() para o preço.")
        i = self.taxa_para(dias_corridos, dias_uteis) if taxa is None else taxa
        if self.convencao == EXP252:
            if dias_uteis is None:
                raise ValueError("convenção EXP252 exige dias úteis")
            return (1.0 + i) ** (float(dias_uteis) / 252.0)
        return 1.0 + i * float(dias_corridos) / 360.0

    def fator_desconto(self, dias_corridos: float,
                       dias_uteis: Optional[float] = None,
                       taxa: Optional[float] = None) -> float:
        return 1.0 / self.fator_capitalizacao(dias_corridos, dias_uteis, taxa)

    def forward(self, dc1: float, dc2: float,
                du1: Optional[float] = None, du2: Optional[float] = None) -> float:
        """Taxa a termo (FRA) entre os dois prazos, na convenção da curva.

        EXP252:  ((1+i2)^(du2/252) / (1+i1)^(du1/252)) ^ (252/(du2-du1)) - 1
        LIN360:  (F2/F1 - 1) * 360 / (dc2-dc1)
        """
        if self.convencao == EXP252:
            if du1 is None or du2 is None:
                raise ValueError("FRA exponencial exige dias úteis")
            if du2 == du1:
                return self.taxa_para(dc2, du2)
            f1 = self.fator_capitalizacao(dc1, du1)
            f2 = self.fator_capitalizacao(dc2, du2)
            return (f2 / f1) ** (252.0 / (float(du2) - float(du1))) - 1.0
        if dc2 == dc1:
            return self.taxa_para(dc2, du2)
        f1 = self.fator_capitalizacao(dc1)
        f2 = self.fator_capitalizacao(dc2)
        return (f2 / f1 - 1.0) * 360.0 / (float(dc2) - float(dc1))

    # ------------------------------------------------------------ utilidades

    def deslocada(self, shift: float) -> "Curva":
        """Curva com todos os vértices deslocados em ``shift`` (em decimal).

        É a coluna "Shift / Ajuste na Curva" das planilhas, usada para
        sensibilidade: 0.0001 desloca a curva em 1 bp e o MtM resultante é o DV01.
        """
        return Curva(
            nome=f"{self.nome} ({shift * 10000:+.0f} bp)",
            data_referencia=self.data_referencia,
            vertices=[Vertice(v.dias_uteis, v.dias_corridos, v.taxa + shift)
                      for v in self.vertices],
            convencao=self.convencao, metodo=self.metodo,
            extrapolar=self.extrapolar, eixo=self.eixo, calendario=self.calendario,
        )

    def amostrar(self, passo: int = 30, limite: Optional[int] = None) -> List[dict]:
        """Pontos (x, taxa) prontos para plotar, no eixo próprio da curva."""
        eixo = self.eixo_x
        if not eixo:
            return []
        fim = limite or int(max(eixo))
        if fim <= 0:
            return []
        pontos = []
        x = max(1, int(min(eixo)))
        while x <= fim:
            pontos.append({"x": x, "dc": x, "taxa": self.taxa(x)})
            x += passo
        if pontos and pontos[-1]["x"] != fim:
            pontos.append({"x": fim, "dc": fim, "taxa": self.taxa(fim)})
        return pontos

    def para_dict(self) -> dict:
        return {
            "nome": self.nome,
            "data_referencia": self.data_referencia.isoformat(),
            "convencao": self.convencao,
            "metodo": self.metodo,
            "eixo": self.eixo,
            "vertices": [{"du": v.dias_uteis, "dc": v.dias_corridos, "taxa": v.taxa}
                         for v in self.vertices],
        }


# --------------------------------------------------------------- Term SOFR --

TENORES_TERM = (1, 3, 6, 12)


@dataclass
class CurvaTermSOFR:
    """Curva de desconto em dólar, ancorada no spot T+2.

    Reproduz a aba *Curva Term SOFR*, que monta a curva em duas partes:

    1. o **trecho curto** vem das taxas Term SOFR da CME (1, 3, 6 e 12 meses),
       cada uma um desconto linear 360 sobre o spot:
       ``DF(spot + n meses) = 1 / (1 + taxa_n · DC/360)``;
    2. o **trecho longo** vem do bootstrap dos futuros SR3 entre datas IMM:
       ``DF(i+1) = DF(i) / (1 + f_i · DC/360)``, com ``f_i = (100 − preço)/100``.

    O DF vale 1 na data spot — não na primeira data IMM.  Ancorar no spot é o
    que permite um swap que comece depois do spot descontar direito; a versão
    anterior, ancorada na primeira IMM, inflava o primeiro forward.
    """

    data_spot: date
    datas_imm: List[date]
    forwards: List[float]
    taxas_term: Optional[Dict[int, float]] = None    # {meses: taxa} da CME
    nome: str = "Term SOFR"

    def __post_init__(self):
        self.data_spot = para_data(self.data_spot)
        self.datas_imm = [para_data(d) for d in self.datas_imm]
        self.taxas_term = dict(self.taxas_term or {})
        self._pontos_curtos = self._montar_trecho_curto()
        self._dfs = self._bootstrap()

    # ------------------------------------------------------------ montagem

    def _montar_trecho_curto(self) -> List[tuple]:
        """[(data, DF)] das taxas Term SOFR, sempre começando pelo spot."""
        pontos = [(self.data_spot, 1.0)]
        for meses in sorted(self.taxas_term):
            taxa = self.taxas_term[meses]
            if taxa is None:
                continue
            data = soma_meses(self.data_spot, meses)
            dc = (data - self.data_spot).days
            pontos.append((data, 1.0 / (1.0 + taxa * dc / 360.0)))
        return pontos

    def _df_na_primeira_imm(self) -> float:
        """DF da primeira data IMM, vindo do trecho curto (ou extrapolado dele)."""
        if not self.datas_imm:
            return 1.0
        alvo = self.datas_imm[0]
        if len(self._pontos_curtos) < 2:
            taxa = self.forwards[0] if self.forwards else 0.0
            return 1.0 / (1.0 + taxa * (alvo - self.data_spot).days / 360.0)
        xs = [(d - self.data_spot).days for d, _ in self._pontos_curtos]
        ys = [df for _, df in self._pontos_curtos]
        return interpolacao.linear(xs, ys, (alvo - self.data_spot).days,
                                   extrapolar="linear")

    def _bootstrap(self) -> List[float]:
        """DFs nas datas IMM, encadeados a partir do trecho curto."""
        if not self.datas_imm:
            return []
        dfs = [self._df_na_primeira_imm()]
        for i in range(1, len(self.datas_imm)):
            dc = (self.datas_imm[i] - self.datas_imm[i - 1]).days
            dfs.append(dfs[-1] / (1.0 + self.forwards[i - 1] * dc / 360.0))
        return dfs

    # ------------------------------------------------------------ consultas

    @property
    def pontos(self) -> List[dict]:
        forwards = list(self.forwards) + [self.forwards[-1]] if self.forwards else []
        return [{"data": d.isoformat(), "dc": (d - self.data_spot).days,
                 "df": df, "forward": f}
                for d, df, f in zip(self.datas_imm, self._dfs, forwards)]

    @property
    def pontos_curtos(self) -> List[dict]:
        return [{"data": d.isoformat(), "dc": (d - self.data_spot).days, "df": df}
                for d, df in self._pontos_curtos]

    def fator_desconto(self, data) -> float:
        """DF da data, visto do **spot** (onde DF = 1)."""
        d = para_data(data)
        marcos = self._pontos_curtos + list(zip(self.datas_imm, self._dfs))
        marcos = sorted({m[0]: m[1] for m in marcos}.items())
        if not marcos:
            return 1.0
        if d <= marcos[0][0]:
            return marcos[0][1]
        if d >= marcos[-1][0]:
            taxa = self.forwards[-1] if self.forwards else 0.0
            dc = (d - marcos[-1][0]).days
            return marcos[-1][1] / (1.0 + taxa * dc / 360.0)
        xs = [(x - self.data_spot).days for x, _ in marcos]
        ys = [y for _, y in marcos]
        return interpolacao.linear(xs, ys, (d - self.data_spot).days)

    def fator_desconto_entre(self, inicio, fim) -> float:
        """DF de ``fim`` visto de ``inicio`` — é o que a precificação usa."""
        return self.fator_desconto(fim) / self.fator_desconto(inicio)

    def taxa_zero(self, data) -> float:
        """Taxa zero linear 360 do spot até a data."""
        d = para_data(data)
        dc = (d - self.data_spot).days
        if dc <= 0:
            return self.forwards[0] if self.forwards else 0.0
        return (1.0 / self.fator_desconto(d) - 1.0) * 360.0 / dc

    def term_forward(self, inicio, meses: int) -> float:
        """Term SOFR a termo do tenor pedido, começando em ``inicio``.

        É o que a perna flutuante usa quando o reset é 1M, 3M, 6M ou 12M:
        a taxa linear 360 implícita entre a data de início do período e a data
        ``meses`` à frente.
        """
        d0 = para_data(inicio)
        d1 = soma_meses(d0, meses)
        dc = (d1 - d0).days
        if dc <= 0:
            return 0.0
        return (1.0 / self.fator_desconto_entre(d0, d1) - 1.0) * 360.0 / dc
