"""O aliado: um companheiro por run, que luta do seu lado e nunca é alvo."""

import random

import pytest

from karmabound.aliados import (
    ACOES,
    Aliado,
    aliado,
    carregar_aliados,
    nivel_maximo,
    sortear_aliado,
)
from karmabound.caminho import escolher_opcao_auto
from karmabound.combate import Luta, Lutador, Tecnica

BASICO = Tecnica("golpe_basico", "Golpe", "ataque", dano=4)
GUARDA = Tecnica("guarda", "Guarda", "defesa")
SOCO = Tecnica("soco", "Soco", "ataque", dano=5)


def _aliado(acao, valor=3, por_nivel=1.0, cada=1):
    return Aliado("teste", "Teste", "犬", "", "X · Y", acao, valor, por_nivel, cada)


def _luta(al, nivel=1, rivais=None):
    j = Lutador("Você", 100, 3, 0, [GUARDA])
    rivais = rivais or [Lutador("R", 50, 1, 0, [SOCO])]
    lt = Luta(j, rivais, BASICO, random.Random(0), aliado=al, aliado_nivel=nivel)
    lt.abertura = False
    return lt


def test_os_cinco_aliados_dos_dados():
    aliados = carregar_aliados()
    assert len(aliados) == 5
    assert {a.acao for a in aliados} == set(ACOES)  # um de cada jeito
    for a in aliados:
        assert a.nome and a.kanji and a.texto and " · " in a.origem
        assert a.valor_no_nivel(1) >= 1
        assert a.valor_no_nivel(nivel_maximo()) >= a.valor_no_nivel(1)
    assert aliado("faro").acao == "expor" and aliado("") is None


def test_a_forca_cresce_com_o_nivel():
    a = _aliado("ferir", valor=2, por_nivel=0.5)
    assert [a.valor_no_nivel(n) for n in (1, 2, 3, 5)] == [2, 2, 3, 4]


def test_o_aliado_fere_o_alvo_no_comeco_do_seu_turno():
    lt = _luta(_aliado("ferir"), nivel=2)  # 3 + 1
    acao = lt.resolver(GUARDA)
    assert acao.aliado == ("teste", "ferir", 4) and lt.rival.vida == 46


def test_o_aliado_cura_so_quem_esta_ferido():
    lt = _luta(_aliado("curar"))
    assert lt.resolver(GUARDA).aliado == ()  # vida cheia: nada
    lt.jogador.vida = 50
    lt.vez = lt.jogador
    assert lt.resolver(GUARDA).aliado == ("teste", "curar", 3) and lt.jogador.vida == 53


def test_o_aliado_bloqueia_expoe_e_envenena():
    lt = _luta(_aliado("bloquear"))
    lt.resolver(GUARDA)
    assert lt.jogador.bloqueio == 3
    lt = _luta(_aliado("expor", valor=1))
    lt.resolver(GUARDA)
    assert lt.rival.exposto == 1
    lt = _luta(_aliado("envenenar", valor=2))
    lt.resolver(GUARDA)
    assert lt.rival.veneno == 2
    lt.vez = lt.jogador
    lt.resolver(GUARDA)
    assert lt.rival.veneno == 2  # mantém, não empilha


def test_o_aliado_age_a_cada_n_turnos():
    lt = _luta(_aliado("expor", cada=3))
    feitos = []
    for _ in range(6):
        lt.vez = lt.jogador
        feitos.append(bool(lt.resolver(GUARDA).aliado))
    assert feitos == [False, False, True, False, False, True]


def test_o_aliado_nao_e_alvo_e_nao_age_no_turno_do_rival():
    lt = _luta(_aliado("ferir"))
    lt.vez = lt.rival
    lt.intencao_rival = SOCO
    acao = lt.turno_rival()
    assert acao.alvo == "Você" and acao.aliado == () and lt.rival.vida == 50


def test_no_bando_ele_bate_em_quem_voce_mira_e_a_mira_segue_se_o_alvo_cai():
    a = Lutador("A", 3, 1, 0, [SOCO])
    b = Lutador("B", 50, 1, 0, [SOCO])
    lt = _luta(_aliado("ferir"), rivais=[a, b])
    lt.mirar(a)
    acao = lt.resolver(lt.basico)
    assert not a.vivo and acao.alvo == "B" and b.vida == 50 - 4


# ----------------------------------------------------------------------- na run


@pytest.fixture(scope="module")
def ctx():
    from karmabound.run import Contexto

    return Contexto.padrao("dificil")


def _run(ctx, seed=1):
    from karmabound.run import nova_run

    return nova_run(ctx, random.Random(seed))


def test_sortear_nunca_repete_o_que_voce_ja_tem():
    rng = random.Random(0)
    for _ in range(20):
        assert sortear_aliado(rng, "faro").id != "faro"


def test_a_encruzilhada_do_lutador_ferido_traz_um_aliado(ctx):
    from karmabound.run import atravessar_encruzilhada

    ev = next(e for e in ctx.caminho.eventos if e.id == "ferido")
    ajudar = next(op for op in ev.opcoes if op.aliado)
    e = _run(ctx)
    vida = e.jogador.vida
    atravessar_encruzilhada(e, ajudar)
    assert e.aliado and e.aliado_nivel == 1
    assert e.jogador.vida == vida - round(vida * 0.15)
    antigo = e.aliado
    e.aliado_nivel = 4
    atravessar_encruzilhada(e, ajudar)  # um novo substitui o antigo
    assert e.aliado != antigo and e.aliado_nivel == 1


def test_o_piloto_aceita_o_aliado_quando_esta_bem_de_vida(ctx):
    ev = next(e for e in ctx.caminho.eventos if e.id == "ferido")
    j = Lutador("Você", 100, 1, 0, [])
    assert ev.opcoes[escolher_opcao_auto(ev, j)].aliado
    assert not ev.opcoes[escolher_opcao_auto(ev, j, tem_aliado=True)].aliado
    j.vida = 40
    assert not ev.opcoes[escolher_opcao_auto(ev, j)].aliado


def test_a_luta_recebe_o_aliado_e_ele_cresce_a_cada_vitoria(ctx):
    from karmabound.run import comecar_luta, encerrar_luta

    e = _run(ctx)
    e.aliado, e.aliado_nivel = "raposa_rubra", nivel_maximo() - 1
    for nivel in (nivel_maximo(), nivel_maximo()):  # para no máximo
        lt = comecar_luta(e, ctx, random.Random(2))
        assert lt.aliado.id == "raposa_rubra"
        for r in lt.rivais:
            r.vida = 0
        encerrar_luta(e, ctx, lt)
        assert e.aliado_nivel == nivel


def test_a_elite_as_vezes_deixa_um_aliado(ctx):
    from karmabound.run import comecar_luta, encerrar_luta

    e = _run(ctx)
    e.porta = ctx.caminho.porta("elite")
    lt = comecar_luta(e, ctx, random.Random(2))
    lt.rng.random = lambda: 0.0  # a sorte sai
    for r in lt.rivais:
        r.vida = 0
    encerrar_luta(e, ctx, lt)
    assert e.aliado and e.aliado_nivel == 1
