"""O caminho entre as lutas: portas, elite, encruzilhadas e a Nêmesis (regras)."""

import random
from collections import Counter

from karmabound.caminho import (
    Opcao,
    aplicar_opcao,
    carregar_caminho,
    escolher_opcao_auto,
    escolher_porta_auto,
    oferecer_portas,
    pode_escolher,
)
from karmabound.carma import Carma, ConfigCarma
from karmabound.combate import Lutador, Tecnica
from karmabound.run import (
    Contexto,
    atravessar_encruzilhada,
    comecar_luta,
    encerrar_luta,
    escolher_porta,
    jogar_run,
    nova_run,
    oferecer_caminho,
    tem_caminho,
)


def _ctx(**kw):
    return Contexto.padrao("dificil", **kw)


def test_sempre_ha_um_rival_entre_tres_portas_sem_repetir():
    cam = carregar_caminho()
    rng = random.Random(1)
    for n in range(2, 13):
        portas = oferecer_portas(cam, rng, n, 1 + (n - 1) // 4)
        tipos = [p.tipo for p in portas]
        assert len(portas) == 3 and tipos[0] == "rival"
        assert len(set(tipos)) == 3


def test_primeira_luta_e_um_duelo_ou_a_encruzilhada():
    cam = carregar_caminho()
    rng = random.Random(2)
    for _ in range(50):
        tipos = {p.tipo for p in oferecer_portas(cam, rng, 1, 1)}
        assert tipos <= {"rival", "evento"}


def test_nemesis_so_a_partir_do_capitulo_dois():
    cam = carregar_caminho()
    rng = random.Random(3)
    assert all(p.tipo != "nemesis" for p in oferecer_portas(cam, rng, 2, 1, nemesis=True))
    assert any(p.tipo == "nemesis" for p in oferecer_portas(cam, rng, 6, 2, nemesis=True))


def test_chefe_nao_tem_porta():
    ctx = _ctx()
    estado = nova_run(ctx, random.Random(1))
    estado.luta_no_capitulo = estado.tamanho_capitulo
    assert not tem_caminho(estado, ctx)
    assert not tem_caminho(estado, _ctx(caminho=False))


def _lutar(estado, ctx, rng, tipo, papeis=()):
    porta = ctx.caminho.porta(tipo, papeis=papeis)
    escolher_porta(estado, porta)
    return comecar_luta(estado, ctx, rng)


def test_porta_de_bando_traz_o_bando():
    ctx = _ctx()
    rng = random.Random(4)
    estado = nova_run(ctx, rng)
    luta = _lutar(estado, ctx, rng, "bando", ("lamina", "guardiao", "curandeiro"))
    assert [r.papel for r in luta.rivais] == ["lamina", "guardiao", "curandeiro"]


def test_elite_e_mais_forte_e_paga_com_reliquia():
    ctx = _ctx()
    rng = random.Random(5)
    estado = nova_run(ctx, rng)
    comum = comecar_luta(estado, ctx, random.Random(9)).rival
    luta = _lutar(estado, ctx, random.Random(9), "elite")
    assert luta.rival.elite and luta.rival.vida_max > comum.vida_max
    for r in luta.rivais:
        r.vida = 0
    assert encerrar_luta(estado, ctx, luta)
    assert estado.reliquia_garantida and estado.elites == 1


def test_nemesis_volta_com_o_golpe_e_vinga_com_premio():
    nemesis = {
        "nome": "Ronin · Chidori",
        "estilo": "espadachim",
        "tecnica": "chamas_negras",
        "vezes": 2,
    }
    ctx = _ctx(nemesis=nemesis)
    rng = random.Random(6)
    estado = nova_run(ctx, rng)
    estado.capitulo = 2
    luta = _lutar(estado, ctx, rng, "nemesis")
    r = luta.rival
    assert r.nemesis and r.nome == "Ronin · Chidori" and r.estilo == "espadachim"
    assert any(t.id == "chamas_negras" and t.nivel == 2 for t in r.tecnicas)  # 2 mortes: evoluiu
    carma = estado.mesa.carma
    guardados = carma.guardados
    r.vida = 0
    assert encerrar_luta(estado, ctx, luta)
    assert estado.vingou and carma.guardados == guardados + 1


def test_nemesis_aparece_uma_vez_por_run():
    nemesis = {"nome": "Oni · Rasengan", "estilo": "oni", "tecnica": "perna_em_brasa", "vezes": 1}
    ctx = _ctx(nemesis=nemesis)
    rng = random.Random(7)
    estado = nova_run(ctx, rng)
    estado.capitulo = 2
    vistas = sum(
        any(p.tipo == "nemesis" for p in oferecer_caminho(estado, ctx, rng)) for _ in range(5)
    )
    assert vistas == 1


def _jogador():
    j = Lutador("Você", 100, 2, 1, [Tecnica("a", "A", "ataque", dano=5)])
    j.carma = Carma(ConfigCarma.de_dict(Contexto.padrao().config_carma.__dict__))
    return j


def test_opcoes_da_encruzilhada():
    j = _jogador()
    j.vida = 50
    aplicar_opcao(Opcao("beber", cura=0.6), j)
    assert j.vida == 100
    aplicar_opcao(Opcao("mergulhar", vida_max=15, perde_vida_frac=0.25), j)
    assert j.vida_max == 115 and j.vida == 86
    aplicar_opcao(Opcao("afiar", dano=1), j)
    assert j.dano_run == 1
    aplicar_opcao(Opcao("treinar", evoluir=True, vida_max=-8), j)
    assert j.tecnicas[0].nivel == 2 and j.vida_max == 107


def test_opcao_que_custa_carma_so_com_carma():
    j = _jogador()
    op = Opcao("trocar", custa_carma=40, giro="tecnicas")
    assert not pode_escolher(op, j)
    j.carma.valor = 50
    assert pode_escolher(op, j)
    aplicar_opcao(op, j)
    assert j.carma.valor == 10


def test_encruzilhada_avanca_o_caminho_sem_luta():
    ctx = _ctx()
    estado = nova_run(ctx, random.Random(8))
    antes = (estado.luta_no_capitulo, estado.proxima_luta, estado.lutas_vencidas)
    giro = atravessar_encruzilhada(estado, Opcao("nada"))
    assert giro == ""
    assert (estado.luta_no_capitulo, estado.proxima_luta) == (antes[0] + 1, antes[1] + 1)
    assert estado.lutas_vencidas == antes[2] and estado.encruzilhadas == 1


def test_piloto_cura_quando_esta_mal():
    cam = carregar_caminho()
    fonte = next(e for e in cam.eventos if e.id == "fonte")
    j = _jogador()
    j.vida = 20
    assert fonte.opcoes[escolher_opcao_auto(fonte, j)].cura


def test_piloto_percorre_o_caminho_inteiro():
    ctx = _ctx()
    tipos = Counter()
    for i in range(30):
        rng = random.Random(100 + i)
        estado = nova_run(ctx, rng)
        jogar_run(estado, ctx, rng)
        assert estado.acabou
        tipos["bandos"] += estado.bandos
        tipos["elites"] += estado.elites
        tipos["encruzilhadas"] += estado.encruzilhadas
    assert tipos["bandos"] and tipos["elites"]


def test_piloto_mal_de_vida_procura_a_encruzilhada():
    cam = carregar_caminho()
    portas = (cam.porta("rival"), cam.porta("bando", papeis=("lamina", "xama")))
    portas += (cam.porta("evento", evento=cam.eventos[0]),)
    j = _jogador()
    j.vida = 30
    assert portas[escolher_porta_auto(portas, j)].tipo == "evento"
    j.vida = 90
    assert portas[escolher_porta_auto(portas, j)].tipo == "bando"


def test_desfile_de_chefes_nao_tem_caminho():
    assert Contexto.padrao("dificil", jogo="chefes").caminho is None
