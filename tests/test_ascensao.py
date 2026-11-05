"""Ascensão: para quem já vence, dez degraus por dificuldade (regras e Legado)."""

import random

import pytest

from karmabound import salvar
from karmabound.ascensao import (
    aplicar_ascensao,
    carregar_ascensao,
    maximo,
    modificadores,
    niveis_ate,
)
from karmabound.jornada import Jornada
from karmabound.legado import Legado
from karmabound.run import Contexto, gerar_rival


@pytest.fixture(scope="module")
def base():
    return Contexto.padrao("dificil")


def test_dez_niveis_com_nome_kanji_e_texto():
    niveis = carregar_ascensao()
    assert maximo() == 10 and len(niveis) == 10
    assert [n.nivel for n in niveis] == list(range(1, 11))
    for n in niveis:
        assert n.nome and n.kanji and n.texto and "{" not in n.texto
    assert niveis_ate(3) == list(niveis[:3]) and niveis_ate(0) == []


def test_os_modificadores_acumulam():
    assert modificadores(0) == {}
    assert modificadores(1) == {"vida_rivais_mult": 1.08}
    m = modificadores(10)
    assert m["cura_entre_lutas"] == pytest.approx(-0.1) and m["oferta_treino"] == 2
    assert set(modificadores(4)) == {
        "vida_rivais_mult",
        "cura_entre_lutas",
        "peso_elite",
        "chefe_tecnicas",
    }


def test_ascensao_zero_nao_muda_nada(base):
    assert aplicar_ascensao(base, 0) is base
    assert Contexto.padrao("dificil", ascensao=0).combate == base.combate


def test_ascensao_dez_aplica_tudo_nos_dados(base):
    ctx = Contexto.padrao("dificil", ascensao=10)
    r0, r = base.combate["rivais"], ctx.combate["rivais"]
    assert ctx.ascensao == 10
    assert r["vida_base"] == pytest.approx(r0["vida_base"] * 1.08)
    assert r["vida_por_luta"] == pytest.approx(r0["vida_por_luta"] * 1.08)
    assert r["percepcao"] == [p + 1 for p in r0["percepcao"]]
    assert ctx.combate["cura_entre_lutas"] == pytest.approx(base.combate["cura_entre_lutas"] - 0.1)
    assert ctx.combate["jogador"]["vida"] == base.combate["jogador"]["vida"] - 10
    assert ctx.config_carma.por_giro["cinza"] == base.config_carma.por_giro["cinza"] * 0.75
    assert ctx.config_carma.por_giro["divino"] == base.config_carma.por_giro["divino"]
    assert ctx.oferta_treino == 2
    assert ctx.chance_reliquia == pytest.approx(base.chance_reliquia - 0.08)
    assert ctx.caminho.pesos["elite"] == base.caminho.pesos["elite"] + 2
    assert base.combate["rivais"]["vida_base"] == r0["vida_base"]  # a base não foi tocada


def test_encruzilhadas_cobram_mais(base):
    ctx = Contexto.padrao("dificil", ascensao=7)
    for e0, e in zip(base.caminho.eventos, ctx.caminho.eventos, strict=True):
        for o0, o in zip(e0.opcoes, e.opcoes, strict=True):
            assert o.custa_carma == round(o0.custa_carma * 1.5)
            assert o.cura == pytest.approx(o0.cura * 0.75)


def test_chefe_com_uma_tecnica_a_mais(base):
    ctx = Contexto.padrao("dificil", ascensao=4)
    antes = gerar_rival(base, 4, random.Random(5), 1, True)
    depois = gerar_rival(ctx, 4, random.Random(5), 1, True)
    assert len(depois.tecnicas) == len(antes.tecnicas) + 1
    comum0 = gerar_rival(base, 2, random.Random(5), 1, False)
    comum = gerar_rival(ctx, 2, random.Random(5), 1, False)
    assert len(comum.tecnicas) == len(comum0.tecnicas)


def test_nivel_que_nao_existe():
    with pytest.raises(ValueError):
        Contexto.padrao("dificil", ascensao=11)


# ------------------------------------------------------------------ Legado


def test_vencer_abre_o_proximo_degrau_na_dificuldade(tmp_path):
    arquivo = tmp_path / "legado.json"
    leg = Legado(arquivo)
    assert leg.ascensao_maxima("dificil") == 0
    f = leg.fechar_run([], 12, 3, True, {}, ascensao=0, dificuldade="dificil")
    assert f.ascensao_aberta == 1 and leg.ascensao_maxima("dificil") == 1
    f = leg.fechar_run([], 5, 1, False, {}, ascensao=1, dificuldade="dificil")
    assert f.ascensao_aberta == 0 and leg.ascensao_maxima("dificil") == 1  # perder não abre
    leg.fechar_run([], 12, 3, True, {}, ascensao=1, dificuldade="dificil")
    assert leg.ascensao_maxima("dificil") == 2 and leg.ascensao_maxima("brutal") == 0
    f = leg.fechar_run([], 12, 3, True, {}, ascensao=0, dificuldade="dificil")
    assert f.ascensao_aberta == 0 and leg.ascensao_maxima("dificil") == 2  # não regride
    assert Legado(arquivo).ascensao_maxima("dificil") == 2  # fica no arquivo


def test_o_teto_e_dez(tmp_path):
    leg = Legado(tmp_path / "legado.json")
    leg.fechar_run([], 12, 3, True, {}, ascensao=10, dificuldade="acessivel")
    assert leg.ascensao_maxima("acessivel") == 10


def test_sem_dificuldade_nao_abre_nada():
    leg = Legado()
    leg.fechar_run([], 12, 3, True, {})
    assert leg.ascensoes == {}


# ------------------------------------------------------------------ Jornada e save


def test_a_jornada_joga_e_guarda_a_ascensao():
    j = Jornada.nova("dificil", seed=4, ascensao=3)
    assert j.ascensao == 3 and j.ctx.ascensao == 3 and j.legado["ascensao"] == 3
    assert Jornada.nova("dificil", seed=4).ascensao == 0
    j.girar_linhagem()
    salvar.salvar(j)
    de_volta = salvar.carregar()
    assert de_volta is not None and de_volta.ascensao == 3
    assert de_volta.ctx.combate["rivais"]["vida_base"] == j.ctx.combate["rivais"]["vida_base"]
