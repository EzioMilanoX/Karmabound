"""A expansão: mecânicas novas de combate, Linhagem, voto de luta e o Altar entre capítulos."""

import random
from collections import Counter

import pytest

from karmabound.carma import Carma, ConfigCarma
from karmabound.combate import HESITAR, Luta, Lutador, Tecnica, jurar_luta_auto
from karmabound.efeitos import NEUTRO, Efeitos
from karmabound.rodas import preencher
from karmabound.run import (
    Contexto,
    altar_rapido,
    aplicar_linhagem,
    encerrar_luta,
    jogar_run,
    nova_run,
)
from karmabound.votos_luta import VotoDeLuta

BASICO = Tecnica("golpe_basico", "Golpe", "ataque", dano=4)
NADA = Tecnica("nada", "Nada", "defesa", bloqueio=0, recarga=1)


def lut(nome="J", tecnicas=(), vida=100, vel=1, perc=0, efeitos=NEUTRO, carma=None):
    return Lutador(nome, vida, vel, perc, list(tecnicas), efeitos=efeitos, carma=carma)


def luta(j, r, seed=0, **kw):
    lt = Luta(j, r, BASICO, random.Random(seed), **kw)
    lt.abertura = False
    lt.vez = j
    return lt


def carma(valor=0.0):
    c = Carma(ConfigCarma(100, {}, 20, 6, 60, 3.0, ()))
    c.valor = valor
    return c


@pytest.fixture(scope="module")
def ctx():
    return Contexto.padrao("dificil")


# ------------------------------------------------------------------ combate


def test_sangramento_dura_tres_turnos_de_quem_sangra():
    t = Tecnica("garra", "Garra", "ataque", dano=1, sangrar=2, recarga=1)
    j, r = lut(tecnicas=[t]), lut("R", vida=100)
    lt = luta(j, r)
    lt.resolver(t)
    assert r.sangue == 2 and r.sangue_turnos == 3
    vida = r.vida
    while r.sangue_turnos:
        lt.resolver(BASICO)
    assert r.sangue == 0 and r.vida <= vida - 2 * 3 - 4


def test_drenar_cura_parte_do_dano():
    t = Tecnica("mordida", "Mordida", "ataque", dano=10, drenar=0.5)
    j, r = lut(tecnicas=[t]), lut("R")
    j.vida = 50
    acao = luta(j, r).resolver(t)
    assert acao.dano == 10 and j.vida == 55 and acao.curou == 5


def test_executar_dobra_contra_quem_esta_por_baixo():
    t = Tecnica("fim", "Fim", "ataque", dano=10, executar=0.3)
    j, r = lut(tecnicas=[t]), lut("R", vida=100)
    r.vida = 29
    assert luta(j, r).resolver(t).dano == 20


def test_bomba_explode_depois_de_dois_turnos_do_alvo():
    t = Tecnica("bomba", "Bomba", "ataque", bomba=15, bomba_turnos=2, recarga=3)
    j, r = lut(tecnicas=[t]), lut("R", tecnicas=[NADA])
    lt = luta(j, r)
    lt.resolver(t)
    assert r.bombas == [[2, 15]] and r.vida == 100
    lt.resolver(HESITAR if HESITAR in lt.prontas(r) else NADA)  # 1º turno do rival
    lt.resolver(BASICO)
    vida = r.vida
    lt.resolver(NADA if NADA in lt.prontas(r) else BASICO)  # 2º turno: explode
    assert r.vida <= vida - 15 and not r.bombas


def test_silencio_deixa_so_o_golpe_e_desarme_tira_a_defesa():
    t = Tecnica("sombra", "Sombra", "maldita", silenciar=1, desarmar=2, recarga=4)
    guarda = Tecnica("guarda", "Guarda", "defesa", bloqueio=5, recarga=1)
    j, r = lut(tecnicas=[t]), lut("R", tecnicas=[guarda])
    lt = luta(j, r)
    lt.resolver(t)
    assert lt.prontas(r) == [BASICO]
    lt.resolver(BASICO)  # o turno silenciado
    assert guarda not in lt.prontas(r)  # ainda desarmado


def test_espelho_devolve_o_golpe_inteiro():
    espelho = Tecnica("espelho", "Espelho", "defesa", espelho=1, recarga=3)
    soco = Tecnica("soco", "Soco", "ataque", dano=12)
    j, r = lut(tecnicas=[espelho]), lut("R", tecnicas=[soco])
    lt = luta(j, r)
    lt.resolver(espelho)
    acao = lt.resolver(soco)
    assert acao.dano == 0 and j.vida == 100 and r.vida == 88


def test_custo_de_vida_maxima_fica_na_run():
    t = Tecnica("portao", "Portão", "ataque", dano=30, custo_vida_max=4, recarga=4)
    j, r = lut(tecnicas=[t], vida=70), lut("R")
    luta(j, r).resolver(t)
    assert j.base_vida_max == 66 and j.vida_max == 66
    j.nova_luta()
    assert j.vida_max == 66


def test_acelerar_e_detonar():
    lento = Tecnica("lento", "Lento", "ataque", dano=1, recarga=4)
    rapido = Tecnica("rapido", "Rápido", "ataque", dano=1, acelerar=2, recarga=1)
    det = Tecnica("det", "Detonar", "maldita", dano=1, detonar=3, recarga=2)
    j, r = lut(tecnicas=[lento, rapido, det]), lut("R")
    lt = luta(j, r)
    lt.resolver(lento)
    lt.resolver(BASICO)
    lt.resolver(rapido)
    assert j.recargas["lento"] <= 1
    r.marca, r.sangue, r.sangue_turnos = 2, 1, 2
    lt.resolver(BASICO)
    acao = lt.resolver(det)
    # no turno do rival a Marca (2) e o sangue (1 por mais 1 turno) ficaram: 1 + 3 × 3
    assert r.marca == 0 and r.sangue == 0 and acao.dano == 1 + 3 * 3


def test_acumula_cresce_a_cada_uso():
    t = Tecnica("jet", "Jet", "ataque", dano=5, acumula=3, recarga=0)
    j, r = lut(tecnicas=[t]), lut("R", vida=500)
    lt = luta(j, r)
    danos = []
    for _ in range(3):
        danos.append(lt.resolver(t).dano)
        lt.resolver(BASICO)
    assert danos == [5, 8, 11]


# ------------------------------------------------------------------ Despertar e preços


def test_despertar_aplica_chaves_novas(ctx):
    j, r = lut(carma=carma(100)), lut("R", vida=100)
    r.vida = 30
    fatia = next(f for f in ctx.rodas["despertar"].fatias if f.id == "espada_do_fim")
    lt = luta(j, r, ao_despertar=lambda: fatia)
    lt.despertar()
    assert not r.vivo  # abaixo de 50%: a Espada do Fim derruba


def test_troca_de_corpos_troca_as_fracoes_de_vida():
    j, r = lut(vida=100), lut("R", vida=200)
    j.vida, r.vida = 20, 200
    luta(j, r).aplicar({"trocar_vida": True})
    assert j.vida == 100 and r.vida == 40


# ------------------------------------------------------------------ voto de luta


def promessa(condicao, agora=None, premio=None, falha=None):
    return VotoDeLuta(
        "p",
        "P",
        "約",
        "promessa",
        "",
        agora=agora or {},
        condicao=condicao,
        premio=premio or {},
        falha=falha or {},
    )


def test_promessa_cumprida_paga_o_premio():
    soco = Tecnica("soco", "Soco", "ataque", dano=60)
    j, r = lut(tecnicas=[soco], carma=carma()), lut("R", vida=100)
    v = promessa({"vencer_em": 2}, {"dano_mult": 1.0}, {"carma": 25})
    lt = luta(j, r, voto_luta=v)
    lt.jurar_luta()
    lt.resolver(soco)
    lt.turno_rival()  # 60 de 100 quebra a guarda: ele perde o turno
    lt.resolver(soco)
    assert not r.vivo and lt.promessa_resultado == "cumprida" and j.carma.valor >= 25


def test_promessa_quebrada_cobra_a_falha():
    j, r = lut(carma=carma(50)), lut("R", vida=500)
    v = promessa({"vencer_em": 1}, falha={"perde_vida_frac": 0.5, "zera_carma": True})
    lt = luta(j, r, voto_luta=v)
    lt.jurar_luta()
    lt.resolver(BASICO)
    assert lt.promessa_resultado == "quebrada" and j.vida == 50 and j.carma.valor == 0


def test_so_golpe_quebra_ao_usar_tecnica():
    t = Tecnica("t", "T", "ataque", dano=1, recarga=1)
    j, r = lut(tecnicas=[t]), lut("R", vida=500)
    lt = luta(j, r, voto_luta=promessa({"so_golpe": 2}, falha={"hesitar": 1}))
    lt.jurar_luta()
    lt.resolver(t)
    assert lt.promessa_resultado == "quebrada" and j.pular == 1


def test_revelacao_fortalece_a_proxima_tecnica_e_da_percepcao_ao_rival():
    t = Tecnica("t", "T", "ataque", dano=10, recarga=0)
    j, r = lut(tecnicas=[t]), lut("R", vida=500)
    v = VotoDeLuta(
        "rev", "Rev", "明", "revelacao", "", agora={"revelar": 1.0, "percepcao_rival": 2}
    )
    lt = luta(j, r, voto_luta=v)
    lt.jurar_luta()
    assert lt.percepcao_contra(r) == 2
    assert lt.resolver(t).dano == 20
    lt.resolver(BASICO)
    assert lt.resolver(t).dano == 20  # revelada até o fim da luta
    lt.resolver(BASICO)
    assert lt.resolver(BASICO).dano == 4


def test_selos_de_luta():
    forte = Tecnica("forte", "Forte", "ataque", dano=30, recarga=2)
    fraca = Tecnica("fraca", "Fraca", "ataque", dano=10, recarga=1)
    guarda = Tecnica("guarda", "Guarda", "defesa", bloqueio=5, recarga=1)
    j, r = lut(tecnicas=[forte, fraca, guarda], carma=carma(100)), lut("R", vida=500)
    v = VotoDeLuta(
        "s",
        "S",
        "犠",
        "selo",
        "",
        agora={
            "selar_melhor": True,
            "dano_mult": 1.5,
            "proibir": ["defesa"],
            "sem_despertar": True,
        },
    )
    lt = luta(j, r, voto_luta=v, ao_despertar=lambda: None)
    lt.jurar_luta()
    prontas = lt.prontas(j)
    assert forte not in prontas and guarda not in prontas and fraca in prontas
    assert not lt.pode_despertar()
    assert lt.resolver(fraca).dano == 15
    assert not lt.pode_jurar_luta()  # uma vez por luta


def test_catalogo_de_votos_de_luta(ctx):
    tipos = Counter(v.tipo for v in ctx.votos_luta)
    assert tipos == {"promessa": 6, "revelacao": 6, "selo": 6}


def test_o_piloto_jura_e_cumpre_a_promessa(ctx):
    juradas = 0
    for seed in range(40):
        estado = nova_run(ctx, random.Random(seed))
        jogar_run(estado, ctx, random.Random(seed), ate=3)
        juradas += estado.votos_de_luta
    assert juradas > 20  # o piloto usa o voto de luta


# ------------------------------------------------------------------ Linhagem e Altar


def test_linhagem_com_tecnica_inicial_e_tecnica_propria(ctx):
    estado = nova_run(ctx, random.Random(1))
    caes = next(f for f in ctx.rodas["linhagem"].fatias if f.id == "cla_dos_caes")
    aplicar_linhagem(estado, ctx, caes)
    assert any(t.id == "presa_sobre_presa" for t in estado.jogador.tecnicas)
    ymir = next(f for f in ctx.rodas["linhagem"].fatias if f.id == "sangue_de_ymir")
    aplicar_linhagem(estado, ctx, ymir)
    assert estado.jogador.tecnica_linhagem is not None
    assert estado.jogador.vida == estado.jogador.vida_max


def test_o_altar_nao_abre_mais_entre_capitulos(ctx):
    """Os votos são jurados no menu, antes da run (pacto.py)."""
    abertos = []
    for seed in range(30):
        estado = nova_run(ctx, random.Random(seed))
        jogar_run(
            estado, ctx, random.Random(seed), altar=lambda e, c, r: abertos.append(e.capitulo)
        )
    assert abertos == []


def test_altar_rapido_jura_com_os_valores_tipicos(ctx):
    estado = nova_run(ctx, random.Random(3))
    estado.proxima_luta = 5
    jurou = 0
    for seed in range(5):
        e = estado.clonar(random.Random(seed))
        altar_rapido(e, ctx, random.Random(seed))
        jurou += bool(e.votos.ativos)
    tipicos = any(r.tipico for r in ctx.catalogo.restricoes.values())
    assert jurou == (5 if tipicos else 0) or not tipicos


def test_encerrar_luta_do_chefe_avanca_o_capitulo_sem_altar(ctx):
    estado = nova_run(ctx, random.Random(2))
    estado.luta_no_capitulo = estado.tamanho_capitulo
    lt = luta(estado.jogador, lut("R", vida=1))
    lt.resolver(BASICO)
    encerrar_luta(estado, ctx, lt)
    assert not estado.altar_pendente and estado.capitulo == 2  # os votos são do menu


# ------------------------------------------------------------------ textos


def test_marcadores_dos_textos():
    assert preencher("{dano} e {drenar%}", {"dano": 6, "drenar": 0.5}) == "6 e 50%"
    assert preencher("{m+%} {m-%}", {"m": 0.92}) == "−8% 8%"
    with pytest.raises(ValueError):
        preencher("{nada}", {})


def test_nenhum_texto_fica_com_marcador(ctx):
    for roda in ctx.rodas.values():
        for f in roda.fatias:
            assert "{" not in f.texto, f.id


def test_efeitos_novos_somam():
    from karmabound.efeitos import somar

    e = somar([Efeitos(drenar=0.1, dano_mult=1.2), Efeitos(drenar=0.05, dano_mult=1.5)])
    assert e.drenar == pytest.approx(0.15) and e.dano_mult == pytest.approx(1.8)


def test_piloto_do_voto_respeita_a_dica():
    j, r = lut(), lut("R", vida=100, tecnicas=[NADA])
    chefe = VotoDeLuta("c", "C", "王", "selo", "", agora={}, piloto="chefe")
    assert not jurar_luta_auto(luta(j, r, voto_luta=chefe))
    r.chefe = True
    assert jurar_luta_auto(luta(j, r, voto_luta=chefe))
