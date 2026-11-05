"""O mapa: ao escolher uma porta, já se vê as portas do passo seguinte do capítulo."""

import random

from karmabound.caminho import escolher_opcao_auto
from karmabound.jornada import Jornada
from karmabound.run import (
    Contexto,
    atravessar_encruzilhada,
    nova_run,
    oferecer_caminho,
    tem_caminho,
)


def _ctx(**kw):
    return Contexto.padrao("dificil", **kw)


def _estado(ctx, seed=1):
    """Começo de capítulo, já na segunda luta da run (a primeira só tem Rival e Encruzilhada)."""
    e = nova_run(ctx, random.Random(seed))
    e.tamanho_capitulo = 4
    e.proxima_luta = 2
    return e


def test_as_portas_seguintes_viram_as_de_agora():
    ctx, rng = _ctx(), random.Random(2)
    e = _estado(ctx)
    agora = oferecer_caminho(e, ctx, rng)
    seguintes = e.proximas_portas
    assert len(agora) == 3 and len(seguintes) == 3 and seguintes[0].tipo == "rival"
    e.luta_no_capitulo += 1  # venceu a luta: o passo seguinte chegou
    e.proxima_luta += 1
    assert oferecer_caminho(e, ctx, rng) == seguintes


def test_antes_do_chefe_o_mapa_mostra_o_chefe():
    ctx, rng = _ctx(), random.Random(3)
    e = _estado(ctx)
    e.luta_no_capitulo = e.tamanho_capitulo - 1  # a última porta antes do chefe
    oferecer_caminho(e, ctx, rng)
    assert e.proximas_portas == ()
    e.luta_no_capitulo += 1
    assert not tem_caminho(e, ctx)  # o chefe: sem portas


def test_a_encruzilhada_tambem_avanca_o_mapa():
    ctx, rng = _ctx(), random.Random(4)
    e = _estado(ctx)
    oferecer_caminho(e, ctx, rng)
    seguintes = e.proximas_portas
    ev = ctx.caminho.eventos[0]
    atravessar_encruzilhada(e, ev.opcoes[escolher_opcao_auto(ev, e.jogador)])
    assert oferecer_caminho(e, ctx, rng) == seguintes


def test_a_nemesis_no_mapa_conta_como_vista():
    nemesis = {"nome": "Oni · Rasengan", "estilo": "oni", "tecnica": "perna_em_brasa", "vezes": 1}
    ctx = _ctx(nemesis=nemesis)
    for seed in range(20):
        rng = random.Random(seed)
        e = _estado(ctx, seed)
        e.capitulo = 2
        vistas = 0
        for _ in range(e.tamanho_capitulo - 1):
            vistas += any(p.tipo == "nemesis" for p in oferecer_caminho(e, ctx, rng))
            vistas += any(p.tipo == "nemesis" for p in e.proximas_portas)
            e.luta_no_capitulo += 1
            e.proxima_luta += 1
        # vista no mapa e depois atravessada é a mesma aparição: no máximo duas contagens
        assert e.nemesis_vista and 1 <= vistas <= 2


def test_a_jornada_mostra_o_mapa_na_fase_do_caminho():
    j = Jornada.nova("dificil", seed=5)
    j.girar_linhagem()
    if j.fase == "substituir":
        j.substituir(None)
    j.girar_destino()
    if j.fase == "substituir":
        j.substituir(None)
    j.girar_arco()
    assert j.fase == "caminho"
    seguintes = j.proximas_portas
    assert len(seguintes) == 3 and seguintes is j.estado.proximas_portas
    j.escolher_caminho(0)
    j.luta.rival.vida = 0
    for r in j.luta.rivais:
        r.vida = 0
    j.terminar_luta()
    while j.fase != "caminho":  # treino, técnica, troca, relíquia: até a próxima porta
        if j.fase == "treino":
            j.escolher_treino(0)
        elif j.fase == "tecnica":
            j.girar_tecnica()
            j.escolher_tecnica(0)
        elif j.fase == "substituir":
            j.substituir(None)
        elif j.fase == "reliquia":
            j.girar_reliquia()
        else:
            raise AssertionError(j.fase)
    assert j.oferta_caminho == seguintes
