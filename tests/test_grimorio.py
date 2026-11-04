"""Grimório: o que já saiu da roleta fica salvo; a tela lista tudo com a origem."""

import os

import pytest

from karmabound.grimorio import Grimorio, caminho_padrao
from karmabound.jornada import Jornada
from karmabound.tela_grimorio import entradas


def test_salva_e_recarrega(tmp_path):
    g = Grimorio(tmp_path / "g.json")
    j = Jornada.nova("dificil", seed=1)
    fatia = j.ctx.rodas["destino"].fatias[0]
    assert g.ver([fatia]) == [fatia]
    assert g.ver([fatia]) == []  # já visto
    assert Grimorio(tmp_path / "g.json").viu(fatia.id)


def test_arquivo_estragado_recomeca(tmp_path):
    caminho = tmp_path / "g.json"
    caminho.write_text("{ nada", encoding="utf-8")
    assert Grimorio(caminho).vistos == set()


def test_testes_nunca_gravam_na_pasta_pessoal():
    assert "save" in str(caminho_padrao()) and os.environ["KARMABOUND_SAVE"] in str(
        caminho_padrao()
    )


def test_a_jornada_registra_os_giros():
    j = Jornada.nova("dificil", seed=2)
    j.grimorio = Grimorio()
    j.girar_linhagem()
    giro = j.girar_destino()
    assert j.grimorio.viu(giro.fatias[0].id)


def test_o_piloto_automatico_nao_registra():
    j = Jornada.nova("dificil", seed=3)
    assert j.grimorio is None


@pytest.fixture
def ctx():
    from karmabound.run import Contexto

    return Contexto.padrao("dificil")


def test_o_grimorio_lista_todas_as_habilidades_com_origem(ctx):
    por_roda = entradas(ctx)
    total = sum(len(v) for v in por_roda.values())
    fatias = sum(len(r.fatias) for r in ctx.rodas.values())
    assert total == fatias + 1 + len(ctx.chefes)  # + o Golpe e os chefes
    assert por_roda["tecnicas"][0].id == "golpe_basico"
    assert all(e.origem for v in por_roda.values() for e in v)


def test_as_telas_de_menu_desenham_de_verdade(ctx):
    """Cada tela do título desenha pelo menos uma vez num renderer nulo."""
    from ouroboros.interfaces.null.null_renderer import NullRenderer

    from karmabound.tela_grimorio import GrimorioScene
    from karmabound.tela_menus import TituloScene

    class Entrada:
        def is_action_pressed(self, acao):
            return False

    r = NullRenderer()
    g = Grimorio()
    for i in range(6):
        tela = GrimorioScene(g, Entrada(), lambda: None, lambda: None, ctx=ctx)
        tela.i_roda = i
        tela.render(None, r)
    titulo = TituloScene(
        Entrada(),
        lambda m: None,
        lambda: None,
        continuar="Difícil · capítulo 1 · luta 2",
        ao_continuar=lambda: None,
        ao_diaria=lambda: None,
        recorde_diaria=4,
        ao_cronica=lambda: None,
    )
    titulo.relogio = 3.0
    titulo.render(None, r)
