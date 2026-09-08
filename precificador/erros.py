"""A base comum das falhas de fonte externa.

Toda fonte que a aplicação consulta — B3, Banco Central, Fed de Nova York,
Banco da Finlândia — tem a sua própria exceção, e é bom que tenha: a mensagem
de erro precisa dizer qual fonte falhou e por quê. O problema era como as telas
tratavam isso. Cada rota listava a sua tupla:

    except (servicos.ErroFormulario, ValueError) as exc:

Basta uma fonte nova, ou uma rota que passa a usar uma fonte que antes não
usava, para a tupla ficar incompleta — e aí a falha de rede sobe até o Flask e
o usuário recebe um traceback em vez da caixa de aviso. Foi o que aconteceu na
calculadora de renda fixa quando o proxy corporativo bloqueou o Banco Central:
a rota não listava ``ErroBCB``.

Com uma base comum, a tela captura ``ErroDeFonte`` e nenhuma fonte pode ficar
de fora — inclusive as que ainda não existem.
"""

from __future__ import annotations


class ErroTraduzido(Exception):
    """Erro cuja frase a tela remonta no idioma dela.

    O molde fica **separado** dos valores, e não é preciosismo: uma frase já
    montada com a data dentro — "não há PTAX entre 01/09/2026 e 05/09/2026" —
    não tem como ser chave de tradução, porque cada par de datas gera uma chave
    nova. Com o molde de um lado e os números do outro, a chave é uma só e vale
    para todas as ocorrências.

    É o mesmo padrão que ``sofr.convencao`` e ``PontaLiquidada.descricao`` já
    usam para o texto que vai à tela. A diferença é que aqui ele vale para o
    texto que vai à tela **quando dá errado**, que era o único canto do app
    onde o português vazava para a tela em inglês.

    ``str(exc)`` continua devolvendo a frase montada em português: é o que vai
    para o log e para quem chama o pacote de fora, e nenhum dos dois tem idioma
    de tela.
    """

    def __init__(self, molde: str, **valores):
        self.molde = molde
        self.valores = valores
        super().__init__(montar(molde, valores))

    @classmethod
    def de(cls, exc: Exception) -> "ErroTraduzido":
        """Reembrulha um erro de baixo **sem** achatá-lo em texto.

        Uma camada que repassa com ``str(exc)`` perde o molde, e o erro volta a
        ser intraduzível na primeira vez que muda de mão.
        """
        molde, valores = partes(exc)
        return cls(molde, **valores)


def montar(molde: str, valores: dict) -> str:
    """A frase montada, ou o molde cru quando os valores não fecham.

    Um molde editado de um lado só levantaria ``KeyError`` **dentro** do
    ``raise``, e o erro de formatação apagaria o erro de verdade — quem lesse a
    tela veria "KeyError: 'b'" em vez do que aconteceu.
    """
    if not valores:
        return molde
    try:
        return molde.format(**valores)
    except (KeyError, IndexError, ValueError):
        return molde


def partes(exc: Exception) -> tuple:
    """``(molde, valores)`` de qualquer exceção — traduzível ou não.

    Um erro que não passou pelo ``ErroTraduzido`` devolve a própria frase como
    molde, sem valores: ele cai de volta no português, que é o comportamento
    anterior, em vez de quebrar a tela.
    """
    molde = getattr(exc, "molde", None)
    if molde is None:
        return str(exc), {}
    return molde, getattr(exc, "valores", {}) or {}


class ErroDeFonte(ErroTraduzido, RuntimeError):
    """Falha ao obter dado de uma fonte externa.

    Todas as exceções de fonte herdam desta. Uma tela que a captura trata
    qualquer fonte, presente ou futura.
    """


class ErroDeDado(ErroTraduzido, ValueError):
    """Dado de entrada que não fecha, com a frase traduzível para a tela.

    Herda de ``ValueError`` de propósito: as rotas capturam ``ValueError`` há
    muito tempo, e trocar o tipo levantado por um que não fosse um deixaria a
    exceção escapar até o Flask. Aqui o tipo continua o mesmo para quem captura,
    e ganha o molde para quem exibe.
    """
