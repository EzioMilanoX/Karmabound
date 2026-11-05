"""Ressonância de anime: 3 ou mais técnicas equipadas do mesmo anime dão um bônus."""

import random

import pytest

from karmabound.fusoes import fundir
from karmabound.ressonancia import (
    carregar_ressonancias,
    contar_animes,
    efeitos_de_ressonancia,
    ressonancias_ativas,
)
from karmabound.rodas import anime_de
from karmabound.run import (
    Contexto,
    atualizar_efeitos,
    criar_tecnica,
    nova_run,
    receber_tecnica,
    substituir_tecnica,
)

NARUTO = ("espiral_concentrada", "mil_passaros", "mil_clones", "golpe_de_vento")
FATE = ("lanca_do_coracao", "sete_petalas", "espada_da_vitoria")


@pytest.fixture(scope="module")
def ctx():
    return Contexto.padrao("dificil")


def _estado(ctx, *tecnicas):
    e = nova_run(ctx, random.Random(1))
    e.dom = e.linhagem = None
    e.jogador.tecnicas = [criar_tecnica(ctx, ctx.tecnicas[t]) for t in tecnicas]
    atualizar_efeitos(e)
    return e


def test_os_dados_falam_de_animes_que_existem(ctx):
    tabela = carregar_ressonancias()
    animes = {anime_de(f.origem) for f in ctx.rodas["tecnicas"].fatias}
    assert set(tabela.animes) <= animes
    assert tabela.minimo == 3
    for b in [*tabela.animes.values(), tabela.generico]:
        assert len(b.niveis) == 2 and b.kanji and b.nome
        assert all("{" not in n.texto for n in b.niveis)


def test_tres_do_mesmo_anime_ativam_o_nivel_um(ctx):
    e = _estado(ctx, *NARUTO[:3], "golpe_direto")
    assert contar_animes(e)["Naruto"] == 3
    (r,) = ressonancias_ativas(e)
    assert (r.anime, r.nivel, r.tecnicas, r.nome) == ("Naruto", 1, 3, "Vontade do Fogo")
    assert r.kanji and "1 clone" in r.texto
    assert e.jogador.efeitos.clones_inicio == 1


def test_quatro_ativam_o_nivel_dois(ctx):
    e = _estado(ctx, *NARUTO)
    (r,) = ressonancias_ativas(e)
    assert r.nivel == 2 and e.jogador.efeitos.clones_inicio == 2


def test_duas_nao_ressoam(ctx):
    e = _estado(ctx, *NARUTO[:2], "golpe_direto")
    assert ressonancias_ativas(e) == [] and efeitos_de_ressonancia(e) == []
    assert e.jogador.efeitos.clones_inicio == 0


def test_anime_sem_entrada_propria_usa_o_generico(ctx):
    e = _estado(ctx, *FATE)
    vida_sem = e.jogador.base_vida_max
    (r,) = ressonancias_ativas(e)
    assert r.anime == "Fate" and r.nome == carregar_ressonancias().generico.nome
    assert e.jogador.vida_max == round(vida_sem * e.jogador.efeitos.vida_max_mult) + 8


def test_recalcula_ao_receber_e_ao_trocar_tecnica(ctx):
    e = _estado(ctx, *NARUTO[:2], "golpe_direto")
    assert receber_tecnica(e, ctx, ctx.tecnicas["mil_clones"]) == "equipada"
    assert e.jogador.efeitos.clones_inicio == 1  # já vale, sem esperar outro passo
    sai = next(t for t in e.jogador.tecnicas if t.id == "mil_clones")
    substituir_tecnica(e, sai, ctx.tecnicas["guarda_alta"], ctx)  # Hunter x Hunter
    assert e.jogador.efeitos.clones_inicio == 0


def test_a_fusao_conta_para_a_ressonancia(ctx):
    """A Shuriken Espiral (Naruto) toma o lugar da Espiral: o anime continua contando."""
    e = _estado(ctx, "espiral_concentrada", "golpe_de_vento", "mil_passaros")
    assert e.jogador.efeitos.clones_inicio == 1
    fundir(e, ctx)
    assert "shuriken_espiral" in [t.id for t in e.jogador.tecnicas]
    assert e.jogador.efeitos.clones_inicio == 1


def test_dois_animes_ao_mesmo_tempo(ctx):
    e = _estado(ctx, *NARUTO[:3], *FATE)
    assert {r.anime for r in ressonancias_ativas(e)} == {"Naruto", "Fate"}
