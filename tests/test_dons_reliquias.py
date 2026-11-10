"""Dons, Relíquias, Arcos e duplicatas: cada regra nova, isolada."""

import random

import pytest

from karmabound.carma import Carma, ConfigCarma
from karmabound.combate import HESITAR, Luta, Lutador, Tecnica, evoluir
from karmabound.efeitos import NEUTRO, Efeitos
from karmabound.run import (
    Contexto,
    aplicar_arco,
    aplicar_dom,
    comecar_luta,
    encerrar_luta,
    girar,
    nova_run,
    receber_reliquia,
    receber_tecnica,
)

BASICO = Tecnica("golpe_basico", "Golpe", "ataque", dano=4)
DIRETO = Tecnica("direto", "Direto", "ataque", dano=10, recarga=1, sutileza=3)
GUARDA = Tecnica("guarda", "Guarda", "defesa", bloqueio=8, recarga=2)
INVESTIDA = Tecnica(
    "investida", "Investida", "ataque", dano=11, recarga=2, sutileza=1, perigosa=True
)


def lut(nome="J", tecnicas=(), vida=100, vel=1, perc=0, efeitos=NEUTRO, carma=None):
    return Lutador(nome, vida, vel, perc, list(tecnicas), efeitos=efeitos, carma=carma)


def luta(j, r, seed=0):
    lt = Luta(j, r, BASICO, random.Random(seed))
    lt.abertura = False  # sem surpresa: o meio da luta
    return lt


def carma(valor=0.0):
    return Carma(ConfigCarma(100, {}, 20, 6, 60, 3.0, ()), valor)


# ------------------------------------------------------------------ Dons (combate)


def test_esquiva_faz_o_golpe_inteiro_errar():
    j, r = lut("J", [DIRETO], vel=3), lut("R", efeitos=Efeitos(esquiva=1.0))
    acao = luta(j, r).resolver(DIRETO)
    assert acao.dano == 0 and acao.esquivas == 1 and r.vida == 100


def test_furia_cresce_com_a_vida_perdida():
    j, r = lut("J", [DIRETO], vel=3, efeitos=Efeitos(furia=6)), lut("R")
    j.vida = 50  # metade perdida: +3
    assert luta(j, r).resolver(DIRETO).dano == 13


def test_sombra_repete_parte_do_golpe():
    j, r = lut("J", [DIRETO], vel=3, efeitos=Efeitos(sombra=0.5)), lut("R")
    acao = luta(j, r).resolver(DIRETO)
    assert acao.sombra == 5 and acao.dano == 15


def test_escudo_inicial_ignora_o_primeiro_golpe_de_cada_luta():
    j = lut("J", efeitos=Efeitos(escudo_inicial=1))
    j.nova_luta()
    r = lut("R", [DIRETO], vel=3)
    lt = luta(r, j)  # o rival (como "jogador" da Luta) ataca primeiro
    assert lt.resolver(DIRETO).escudados == 1 and j.vida == 100
    j.nova_luta()
    assert j.escudos == 1


def test_cura_no_inicio_da_luta_respeita_o_multiplicador():
    j = lut("J", efeitos=Efeitos(cura_inicio=4, cura_mult=0.5))
    j.vida = 50
    j.nova_luta()
    assert j.vida == 52


def test_salvacao_deixa_com_1_de_vida_uma_vez():
    j = lut("J", vida=20, efeitos=Efeitos(salvacao=1))
    j.sofrer(99)
    assert j.vida == 1
    j.sofrer(99)
    assert not j.vivo


def test_bloqueio_pela_metade_com_a_mascara():
    j, r = lut("J", [GUARDA], vel=3, efeitos=Efeitos(bloqueio_mult=0.5)), lut("R")
    luta(j, r).resolver(GUARDA)
    assert j.bloqueio == 4


OLHO = Tecnica(
    "olho",
    "Olho Roubado",
    "maldita",
    copia_rival=True,
    copia_bonus=1.5,
    cega_proprio=True,
    recarga=2,
)
SANTUARIO = Tecnica("santuario", "Santuário", "maldita", santuario=2, pular_depois=True, recarga=99)
INSTANTE = Tecnica("instante", "Instante", "maldita", turno_extra=True, custo_vida=3, recarga=99)


def test_olho_roubado_copia_a_ultima_tecnica_do_rival_e_cega():
    j = lut("J", vel=3, perc=3)
    j.tecnica_dom = OLHO
    r = lut("R", [INVESTIDA])
    lt = luta(j, r)
    assert OLHO not in lt.prontas(j)  # nada para roubar ainda
    lt.resolver(BASICO)
    lt.intencao_rival = INVESTIDA
    lt.turno_rival()
    assert OLHO in lt.prontas(j)
    acao = lt.resolver(OLHO)
    assert acao.copiou == "investida" and acao.dano == round(11 * 1.5)
    assert j.cego and lt.ver_intencao() is None and lt.percepcao_contra(j) == 0


def test_santuario_torna_os_golpes_imperceptiveis_e_cobra_um_turno():
    j = lut("J", [INVESTIDA], vel=3)
    j.tecnica_dom = SANTUARIO
    r = lut("R", vida=999, perc=9)
    lt = luta(j, r)
    lt.resolver(SANTUARIO)
    lt.turno_rival()
    acao = lt.resolver(INVESTIDA)
    assert not acao.reagiu and acao.dano == round(11 * 1.5)
    lt.turno_rival()
    lt.resolver(BASICO)  # segundo turno de santuário: acabou, o preço vem
    lt.turno_rival()
    assert lt.prontas(j) == [HESITAR]
    lt.resolver(HESITAR)
    lt.turno_rival()
    assert HESITAR not in lt.prontas(j)


def test_instante_da_duas_acoes_de_verdade_e_custa_vida():
    j = lut("J", [DIRETO], vel=3)
    j.tecnica_dom = INSTANTE
    r = lut("R", vida=999)
    lt = luta(j, r)
    lt.resolver(INSTANTE)
    assert j.vida == 97 and lt.vez is j
    lt.resolver(DIRETO)
    assert lt.vez is j
    lt.resolver(BASICO)
    assert lt.vez is r


def test_contrato_cresce_a_cada_tecnica_consumida():
    pacto = Tecnica(
        "pacto",
        "Contrato",
        "maldita",
        dano=40,
        recarga=1,
        consome_tecnica=True,
        cresce_ao_consumir=10,
    )
    j, r = lut("J", [pacto, GUARDA, INVESTIDA], vel=3), lut("R", vida=999)
    lt = luta(j, r)
    lt.resolver(pacto)
    assert next(t for t in j.tecnicas if t.id == "pacto").dano == 50


def test_evoluir_cresce_e_encurta_a_recarga():
    t = evoluir(Tecnica("x", "Corte", "ataque", dano=10, recarga=3))
    assert (t.nivel, t.nome, t.dano, t.recarga) == (2, "Corte II", 13, 2)
    t3 = evoluir(t)
    assert t3.nome == "Corte III" and t3.recarga == 1
    assert evoluir(Tecnica("y", "Pacto", "maldita", dano=40, recarga=99)).recarga == 99


# ------------------------------------------------------------------ passos da run


@pytest.fixture
def ctx():
    return Contexto.padrao("dificil")


def fatia(ctx, roda, fid):
    return next(f for f in ctx.rodas[roda].fatias if f.id == fid)


def test_dom_aplica_efeito_e_tecnica(ctx):
    e = nova_run(ctx, random.Random(1))
    sem_dom = e.jogador.efeitos.vida_max  # o que a Linhagem sorteada já dá
    aplicar_dom(e, ctx, fatia(ctx, "destino", "corpo_resistente"))
    assert e.jogador.efeitos.vida_max > sem_dom and e.jogador.tecnica_dom is None
    aplicar_dom(e, ctx, fatia(ctx, "destino", "santuario"))
    assert e.jogador.tecnica_dom.santuario > 0 and e.jogador.efeitos.vida_max == sem_dom


def test_reliquias_repetidas_se_somam(ctx):
    e = nova_run(ctx, random.Random(1))
    aplicar_dom(e, ctx, fatia(ctx, "destino", "corpo_resistente"))
    band = fatia(ctx, "reliquias", "bandagem")
    receber_reliquia(e, band)
    receber_reliquia(e, band)
    assert e.jogador.efeitos.cura_inicio == 2 * band.efeito["cura_inicio"]


def test_duplicata_vira_fragmento_e_depois_evolui(ctx):
    e = nova_run(ctx, random.Random(1))
    aplicar_dom(e, ctx, fatia(ctx, "destino", "corpo_resistente"))
    direto = fatia(ctx, "tecnicas", "golpe_direto")  # já vem na mão inicial
    assert receber_tecnica(e, ctx, direto) == "fragmento"
    assert receber_tecnica(e, ctx, direto) == "evoluiu"
    assert next(t for t in e.jogador.tecnicas if t.id == "golpe_direto").nivel == 2


def test_fragmento_do_deus_cego_evolui_na_hora(ctx):
    e = nova_run(ctx, random.Random(1))
    receber_reliquia(e, fatia(ctx, "reliquias", "fragmento_do_deus_cego"))
    assert receber_tecnica(e, ctx, fatia(ctx, "tecnicas", "golpe_direto")) == "evoluiu"


def test_invasao_aumenta_o_capitulo_e_garante_reliquia(ctx):
    e = nova_run(ctx, random.Random(2))
    aplicar_arco(e, ctx, fatia(ctx, "arco", "invasao"))
    assert e.tamanho_capitulo == ctx.lutas_por_capitulo + 1
    from karmabound.run import vai_ter_reliquia

    assert all(vai_ter_reliquia(e, ctx, random.Random(i)) for i in range(20))


def test_lua_de_sangue_vale_para_os_dois(ctx):
    e = nova_run(ctx, random.Random(3))
    aplicar_arco(e, ctx, fatia(ctx, "arco", "lua_de_sangue"))
    lt = comecar_luta(e, ctx, random.Random(3))
    assert lt.jogador.dano_extra == lt.rival.dano_extra == 3


def test_maldicao_coletiva_fortalece_rival_e_carma(ctx):
    e = nova_run(ctx, random.Random(4))
    normal = comecar_luta(e, ctx, random.Random(9)).rival.vida_max
    aplicar_arco(e, ctx, fatia(ctx, "arco", "maldicao_coletiva"))
    assert e.jogador.efeitos.carma_mult == 2.0
    assert comecar_luta(e, ctx, random.Random(9)).rival.vida_max == round(normal * 1.2)


def test_arco_do_juizo_chefe_mais_forte_e_carma_cheio_ao_vencer(ctx):
    e = nova_run(ctx, random.Random(5))
    aplicar_arco(e, ctx, fatia(ctx, "arco", "arco_do_juizo"))
    e.luta_no_capitulo = e.tamanho_capitulo  # a luta do chefe
    lt = comecar_luta(e, ctx, random.Random(5))
    assert lt.rival.chefe and lt.rival.dano_mult == 1.5
    lt.rival.vida = 0
    e.mesa.carma.valor = 0
    assert encerrar_luta(e, ctx, lt)
    assert e.mesa.carma.transbordando and e.arco is None and e.capitulo == 2


def test_treino_na_montanha_cura_mais(ctx):
    e = nova_run(ctx, random.Random(6))
    aplicar_arco(e, ctx, fatia(ctx, "arco", "treino_na_montanha"))
    lt = comecar_luta(e, ctx, random.Random(6))
    e.jogador.vida = 10
    lt.rival.vida = 0
    encerrar_luta(e, ctx, lt)
    assert e.jogador.vida == 10 + round(e.jogador.vida_max * 0.5 * e.jogador.efeitos.cura_mult)


def test_coracao_selado_guarda_na_hora_e_o_despertar_sai_na_luta(ctx):
    e = nova_run(ctx, random.Random(7))
    receber_reliquia(e, fatia(ctx, "reliquias", "coracao_selado"))
    aplicar_arco(e, ctx, fatia(ctx, "arco", "torneio_regular"))
    c = e.mesa.carma
    c.valor = 95
    c.registrar_custo()  # +6 (×1,5): passa de 100
    assert c.guardados == 1 and not c.transbordando and 0 < c.valor < 20
    assert not girar(e, ctx, "reliquias").despertar  # guardado não desperta no giro
    lt = comecar_luta(e, ctx, random.Random(7))
    assert lt.pode_despertar()
    lt.despertar()
    assert c.guardados == 0 and 0 < c.valor < 20  # gastou o guardado, não o Carma


def test_rosario_da_carma_a_cada_vitoria(ctx):
    e = nova_run(ctx, random.Random(8))
    receber_reliquia(e, fatia(ctx, "reliquias", "rosario_de_ossos"))
    aplicar_arco(e, ctx, fatia(ctx, "arco", "torneio_regular"))
    lt = comecar_luta(e, ctx, random.Random(8))
    lt.rival.vida = 0
    e.mesa.carma.valor = 0
    encerrar_luta(e, ctx, lt)
    assert e.mesa.carma.valor == pytest.approx(3)
