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


class ErroDeFonte(RuntimeError):
    """Falha ao obter dado de uma fonte externa.

    Todas as exceções de fonte herdam desta. Uma tela que a captura trata
    qualquer fonte, presente ou futura.
    """
