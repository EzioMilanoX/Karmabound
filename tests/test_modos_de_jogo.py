"""Modos de jogo: Torre sem fim, Desfile de chefes e Mundo de um anime."""

import random

import pytest

from karmabound.jornada import Jornada
from karmabound.rodas import anime_de
from karmabound.run import (
    CAPITULOS_TORRE,
    Contexto,
    animes_jogaveis,
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


def test_mundo_de_um_anime_so_gira_aquele_anime():
    base = Contexto.padrao("dificil")
    animes = animes_jogaveis(base.rodas)
    assert "Naruto" in animes and "One Piece" in animes
    ctx = Contexto.padrao("dificil", jogo="anime", anime="Naruto")
    fixas = set(ctx.combate["jogador"]["tecnicas"])  # as do começo e as que Linhagens dão
    fixas |= {f.inicial for f in base.rodas["linhagem"].fatias if f.inicial}
    tecnicas = ctx.rodas["tecnicas"].fatias
    de_fora = [f for f in tecnicas if anime_de(f.origem) != "Naruto" and f.id not in fixas]
    # só as raridades que o anime não tem voltam como convidadas
    raridades_naruto = {f.raridade for f in tecnicas if anime_de(f.origem) == "Naruto"}
    assert all(f.raridade not in raridades_naruto for f in de_fora)
    for roda in ctx.rodas.values():  # nenhuma roda fica sem raridade para sortear
        assert {f.raridade for f in roda.fatias} == {f.raridade for f in base.rodas[roda.id].fatias}
    estado = jogar_run(nova_run(ctx, random.Random(4)), ctx, random.Random(4))
    assert estado.acabou


def test_modo_que_nao_existe():
    with pytest.raises(ValueError):
        Contexto.padrao("dificil", jogo="xadrez")
    with pytest.raises(ValueError):
        Contexto.padrao("dificil", jogo="anime")


def test_jornada_guarda_o_modo_de_jogo():
    j = Jornada.nova("dificil", seed=5, jogo="anime", anime="One Piece")
    assert j.ctx.jogo == "anime" and j.ctx.anime == "One Piece"
