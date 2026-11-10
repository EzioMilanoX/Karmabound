"""Modos de jogo: Torre sem fim, Desfile de chefes e Mundo de um anime."""

import random

import pytest

from karmabound.jornada import Jornada
from karmabound.rodas import anime_de
from karmabound.run import (
    CAPITULOS_TORRE,
    Contexto,
    comecar_luta,
    jogar_run,
    nova_run,
)


def test_classico_continua_igual():
    ctx = Contexto.padrao("dificil")
    assert ctx.jogo == "classico" and ctx.lutas == 12 and not ctx.todos_chefes


def test_torre_nao_tem_fim_e_o_altar_projeta_um_horizonte():
    ctx = Contexto.padrao("acessivel", jogo="torre")
    assert ctx.capitulos == CAPITULOS_TORRE
    assert ctx.restantes(50) == 12
    estado = jogar_run(nova_run(ctx, random.Random(1)), ctx, random.Random(1))
    assert estado.derrotado and not estado.venceu  # só se sai da torre caindo


def test_desfile_de_chefes_e_so_chefe():
    ctx = Contexto.padrao("dificil", jogo="chefes")
    assert ctx.lutas == 6
    estado = nova_run(ctx, random.Random(2))
    estado.arco = ctx.rodas["arco"].fatias[0]
    for _ in range(3):
        assert comecar_luta(estado, ctx, random.Random(3)).rival.chefe
        estado.luta_no_capitulo = 1


@pytest.mark.parametrize("campanha", ["naruto", "my_hero_academia"])
def test_a_historia_de_um_anime_so_gira_aquele_mundo(campanha):
    ctx = Contexto.padrao("dificil", jogo="historia", historia=campanha)
    base = Contexto.padrao("dificil")
    fixas = set(ctx.combate["jogador"]["tecnicas"])  # o kit do começo é de todos
    fixas |= {f.inicial for f in base.rodas["linhagem"].fatias if f.inicial}
    for rid in ("linhagem", "destino", "tecnicas", "reliquias"):
        fatias = ctx.rodas[rid].fatias
        assert all(anime_de(f.origem) == ctx.anime or f.id in fixas for f in fatias), rid
        assert {f.raridade for f in fatias} >= set(ctx.ordem), rid  # nenhum buraco
    estado = jogar_run(nova_run(ctx, random.Random(4)), ctx, random.Random(4))
    assert estado.acabou


def test_modo_que_nao_existe():
    with pytest.raises(ValueError):
        Contexto.padrao("dificil", jogo="xadrez")
    with pytest.raises(ValueError):
        Contexto.padrao("dificil", jogo="anime")


def test_jornada_guarda_o_modo_de_jogo():
    j = Jornada.nova("dificil", seed=5, jogo="historia", historia="one_piece")
    assert j.ctx.jogo == "historia" and j.ctx.anime == "One Piece"
