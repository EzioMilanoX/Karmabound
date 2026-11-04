"""Continuar a run salva e a semente do dia."""

import os

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

import pytest  # noqa: E402

from karmabound import salvar  # noqa: E402
from karmabound.jornada import Jornada  # noqa: E402


def _rival(j):
    r = j.luta.rival
    return r.nome, r.vida_max, [t.id for t in r.tecnicas], r.velocidade


def test_no_meio_da_luta_continuar_recomeca_a_mesma_luta():
    j = Jornada.nova("dificil", seed=7)
    j.girar_linhagem()
    j.girar_destino()
    j.girar_arco()
    antes = _rival(j)
    vida = j.jogador.vida
    j.luta.resolver(j.luta.basico) if j.luta.vez is j.jogador else j.luta.turno_rival()
    salvar.salvar(j)  # salvou no meio: vale a foto de antes da luta
    k = salvar.carregar()
    assert k.fase == "luta" and _rival(k) == antes and k.jogador.vida == vida


def test_salva_entre_fases_e_o_resumo_diz_onde():
    j = Jornada.nova("acessivel", seed=3)
    j.girar_linhagem()
    j.girar_destino()
    salvar.salvar(j)
    assert salvar.carregar().fase == "arco"
    assert "Acessível" in salvar.resumo() and "luta 1" in salvar.resumo()


def test_arquivo_estragado_ou_ausente_nao_quebra():
    salvar.apagar()
    assert salvar.carregar() is None and salvar.resumo() is None
    salvar.caminho().parent.mkdir(parents=True, exist_ok=True)
    salvar.caminho().write_bytes(b"lixo")
    assert salvar.carregar() is None


def test_recorde_da_semente_do_dia_guarda_o_melhor():
    assert salvar.melhor_diaria("2026-11-02") is None
    assert salvar.registrar_diaria("2026-11-02", 5) == 5
    assert salvar.registrar_diaria("2026-11-02", 3) == 5
    assert salvar.melhor_diaria("2026-11-02") == 5


@pytest.fixture
def loop():
    from karmabound.game import build_game

    lp = build_game(seed=4)
    yield lp
    lp.renderer.shutdown()


def test_o_titulo_oferece_continuar_e_continuar_retoma(loop):
    from karmabound.tela_menus import TituloScene

    f = loop.fluxo
    f.comecar("dificil")
    assert salvar.carregar() is not None  # o Fluxo salvou a primeira fase
    f.titulo()
    titulo = loop.current_scene
    assert isinstance(titulo, TituloScene) and titulo.itens[0][0] == "continuar"
    assert titulo.cursor == 0
    f.continuar()
    assert f.jornada is not None and f.jornada.fase == "linhagem"


def test_semente_do_dia_e_a_mesma_para_todos(loop):
    f = loop.fluxo
    f.semente_do_dia()
    a = f.jornada
    f.semente_do_dia()
    b = f.jornada
    assert a.diaria and a.diaria == b.diaria and a.modo == "dificil"
    assert a.girar_linhagem().fatias[0].id == b.girar_linhagem().fatias[0].id
    assert a.girar_destino().fatias[0].id == b.girar_destino().fatias[0].id


def test_fim_da_run_apaga_o_save(loop):
    f = loop.fluxo
    f.comecar("dificil")
    j = f.jornada
    j.fase = "derrota"
    f.passo()
    assert salvar.carregar() is None
