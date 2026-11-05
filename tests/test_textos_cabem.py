"""Nenhuma descrição de item fica cortada no cartão do resultado da roleta."""

from types import SimpleNamespace

import pytest

from karmabound.rodas import carregar_balanceamento, carregar_raridades, carregar_rodas
from karmabound.tela_roleta import TOPO_MAXIMO_CARTAO, RoletaScene

RODAS = carregar_rodas(carregar_raridades(carregar_balanceamento()))
FATIAS = [f for roda in RODAS.values() for f in roda.fatias]


@pytest.mark.parametrize("despertar", [False, True])
def test_todo_texto_cabe_inteiro_no_cartao(despertar):
    cortados = []
    for f in FATIAS:
        cena = SimpleNamespace(_escolhida=lambda f=f: f, giro=SimpleNamespace(despertar=despertar))
        c = RoletaScene._cartao(cena)
        if c.topo < TOPO_MAXIMO_CARTAO or " ".join(c.linhas) != " ".join(f.texto.split()):
            cortados.append(f.id)
    assert not cortados
