"""Cada técnica-assinatura dá ao chefe uma mecânica própria: uma por teste."""

import random

import pytest

from karmabound.combate import (
    ARMADURA_FRAC,
    CARGA_BONUS,
    CONTRATO_CADA,
    PRECO,
    REGENERA,
    Luta,
    Lutador,
    Tecnica,
    escolher_jogador_auto,
    escolher_rival,
)
from karmabound.rodas import carregar_chefes, carregar_mecanicas

BASICO = Tecnica("golpe_basico", "Golpe", "ataque", dano=4)
DIRETO = Tecnica("direto", "Direto", "ataque", dano=10)
GUARDA = Tecnica("guarda", "Guarda", "defesa")
SOCO = Tecnica("soco", "Soco", "ataque", dano=5)


def _chefe(mecanica, assinatura=None, outras=(GUARDA,), vida=1000):
    tecnicas = list(outras) + ([assinatura] if assinatura is not None else [])
    return Lutador(
        "Chefe",
        vida,
        1,
        0,
        tecnicas,
        chefe=True,
        mecanica=mecanica,
        assinatura=assinatura.id if assinatura is not None else "",
    )


def _luta(chefe, tecnicas=(DIRETO,), vida=100, seed=0):
    j = Lutador("Você", vida, 3, 0, list(tecnicas))
    lt = Luta(j, chefe, BASICO, random.Random(seed))
    lt.abertura = False
    return lt


def _vez_do_jogador(lt):
    lt.vez = lt.jogador


def _vez_do_chefe(lt, t):
    lt.vez = lt.rival
    lt.intencao_rival = t


# ----------------------------------------------------------------------- os dados


def test_toda_assinatura_tem_uma_mecanica_com_nome_kanji_e_texto():
    mecanicas = carregar_mecanicas()
    chefes = carregar_chefes()
    assert {c.id for c in chefes} >= {"general_da_roda", "flor_no_espelho"}
    for c in chefes:  # a 2ª assinatura de um vilão final pode vir sem mecânica
        assert c.mecanica in mecanicas or c.mecanica == "", c.id
    for m in mecanicas.values():
        assert m["nome"] and m["kanji"] and m["texto"]
    # nenhuma sobra (o Reflexo ganha a dele do código, sem assinatura)
    assert {c.mecanica for c in chefes} - {""} == set(mecanicas) - {"reflexo"}


def test_o_chefe_da_run_ganha_a_mecanica_da_assinatura():
    from karmabound.run import Contexto, gerar_rival

    ctx = Contexto.padrao("dificil")
    chefe = gerar_rival(ctx, 4, random.Random(3), 1, True)
    sig = next(c for c in ctx.chefes if c.id == chefe.assinatura)
    assert chefe.mecanica == sig.mecanica
    assert any(t.id == sig.id for t in chefe.tecnicas)
    assert gerar_rival(ctx, 3, random.Random(3), 1, False).mecanica == ""


# ----------------------------------------------------------------------- uma por mecânica


def test_adaptar_a_roda_gira_a_cada_uso_da_mesma_tecnica():
    lt = _luta(_chefe("adaptar"))
    danos = []
    for _ in range(3):
        _vez_do_jogador(lt)
        danos.append(lt.resolver(DIRETO))
    assert [a.dano for a in danos] == [10, 5, 0]
    assert danos[1].mecanica == "adaptar"
    _vez_do_jogador(lt)
    assert lt.resolver(BASICO).dano == 4  # o Golpe é outra técnica: chega inteiro...
    _vez_do_jogador(lt)
    assert lt.resolver(BASICO).dano == 2  # ...e também se adapta


def test_ilusao_o_anuncio_e_uma_isca():
    fraco = Tecnica("fraco", "Fraco", "ataque", dano=3)
    forte = Tecnica("forte", "Forte", "ataque", dano=9)
    lt = _luta(_chefe("ilusao", outras=(fraco, forte)))
    lt.rng.random = lambda: 0.0  # mente sempre
    _vez_do_chefe(lt, forte)
    assert lt.intencao_rival != forte  # você vê a isca
    acao = lt.turno_rival()
    assert acao.tecnica == "forte" and acao.iludiu


def test_ilusao_as_vezes_diz_a_verdade():
    fraco = Tecnica("fraco", "Fraco", "ataque", dano=3)
    forte = Tecnica("forte", "Forte", "ataque", dano=9)
    lt = _luta(_chefe("ilusao", outras=(fraco, forte)))
    lt.rng.random = lambda: 0.99
    _vez_do_chefe(lt, forte)
    assert lt.intencao_rival == forte
    acao = lt.turno_rival()
    assert acao.tecnica == "forte" and not acao.iludiu


def test_petalas_passam_pelos_clones_e_escudos():
    laminas = Tecnica("laminas", "Lâminas", "ataque", dano=3, golpes=5)
    lt = _luta(_chefe("petalas", laminas))
    j = lt.jogador
    j.clones, j.escudos = 5, 2
    _vez_do_chefe(lt, laminas)
    acao = lt.turno_rival()
    assert acao.dano == 15 and j.clones == 5 and j.escudos == 2


def test_armadura_bloqueio_no_primeiro_turno_e_a_cada_dois():
    lt = _luta(_chefe("armadura", vida=100))
    r = lt.rival
    bloqueio = round(100 * ARMADURA_FRAC)
    _vez_do_chefe(lt, GUARDA)
    assert lt.turno_rival().mecanica == "armadura" and r.bloqueio == bloqueio
    r.bloqueio = 0
    _vez_do_chefe(lt, GUARDA)
    assert lt.turno_rival().mecanica == "" and r.bloqueio == 0
    _vez_do_chefe(lt, GUARDA)
    lt.turno_rival()
    assert r.bloqueio == bloqueio


def test_repulsao_empurra_clones_invocacoes_e_bloqueio_a_cada_tres_turnos():
    lt = _luta(_chefe("repulsao"))
    j = lt.jogador
    j.clones, j.invocacoes, j.bloqueio = 3, [[5, 2, "x"]], 6
    for _ in range(2):
        _vez_do_chefe(lt, GUARDA)
        assert lt.turno_rival().mecanica == ""
    assert j.clones == 3
    _vez_do_chefe(lt, GUARDA)
    assert lt.turno_rival().mecanica == "repulsao"
    assert (j.clones, j.invocacoes, j.bloqueio) == (0, [], 0)


def test_intangivel_o_ataque_atravessa_menos_o_absoluto():
    corte = Tecnica("corte", "Corte", "ataque", dano=10, absoluto=True)
    lt = _luta(_chefe("intangivel"), tecnicas=(DIRETO, corte))
    lt.rng.random = lambda: 0.0  # atravessa sempre que puder
    acao = lt.resolver(DIRETO)
    assert acao.dano == 0 and acao.escudados == 1 and acao.mecanica == "intangivel"
    _vez_do_jogador(lt)
    assert lt.resolver(corte).dano == 10
    lt.rng.random = lambda: 0.99
    _vez_do_jogador(lt)
    assert lt.resolver(DIRETO).dano == 10


def test_preco_depois_da_lua_sem_fim_metade_do_dano_ate_o_fim():
    lua = Tecnica("lua", "Lua", "maldita", dano=22, recarga=99)
    lt = _luta(_chefe("preco", lua), vida=500)
    r = lt.rival
    _vez_do_chefe(lt, lua)
    acao = lt.turno_rival()
    assert acao.mecanica == "preco" and r.preco and r.dano_mult == PRECO
    r.vida = r.vida_max
    r.segunda_forma = False
    lt.vez = lt.jogador
    lt._ferir(r, round(r.vida_max * 0.6))  # a segunda forma devolve as técnicas...
    assert r.segunda_forma and r.recargas["lua"] == 99  # ...menos a Lua


def test_preco_o_chefe_guarda_a_lua_para_fechar_a_luta():
    lua = Tecnica("lua", "Lua", "maldita", dano=22, recarga=99)
    lt = _luta(_chefe("preco", lua, outras=(SOCO,)), vida=500)
    with lt.foco(lt.rival):
        assert escolher_rival(lt) == SOCO  # você inteiro: ele não gasta a Lua
        lt.jogador.vida = 20
        assert escolher_rival(lt) == lua  # ela fecha a luta


def test_regenera_cura_por_turno_mas_nao_sangrando():
    lt = _luta(_chefe("regenera", vida=100))
    r = lt.rival
    r.vida = 50
    _vez_do_chefe(lt, GUARDA)
    assert lt.turno_rival().mecanica == "regenera"
    assert r.vida == 50 + round(100 * REGENERA)
    r.vida, r.sangue, r.sangue_turnos = 50, 1, 3
    _vez_do_chefe(lt, GUARDA)
    lt.turno_rival()
    assert r.vida == 49  # o sangramento fere e corta a cura


def test_contrato_o_primeiro_golpe_vai_para_outro_lugar():
    lt = _luta(_chefe("contrato"))
    r = lt.rival
    assert r.contrato
    acao = lt.resolver(DIRETO)
    assert acao.dano == 0 and acao.mecanica == "contrato" and not r.contrato
    _vez_do_jogador(lt)
    assert lt.resolver(DIRETO).dano == 10
    for _ in range(CONTRATO_CADA):
        _vez_do_chefe(lt, GUARDA)
        lt.turno_rival()
    assert r.contrato  # renovado


def test_contrato_golpes_multiplos_passam_do_primeiro():
    rajada = Tecnica("rajada", "Rajada", "ataque", dano=5, golpes=3)
    lt = _luta(_chefe("contrato"), tecnicas=(rajada,))
    assert lt.resolver(rajada).dano == 10


def test_balanca_quem_tem_menos_obedece():
    balanca = Tecnica("balanca", "Balança", "maldita", atordoar=1, enfraquecer=3, recarga=99)
    lt = _luta(_chefe("balanca", balanca, vida=100))
    j = lt.jogador
    j.vida = 30  # 30% contra 100%: você obedece
    _vez_do_chefe(lt, balanca)
    acao = lt.turno_rival()
    assert acao.mecanica == "balanca" and j.pular == 1 and j.bonus_dano == -3


def test_balanca_vira_contra_quem_a_ergue():
    balanca = Tecnica("balanca", "Balança", "maldita", atordoar=1, enfraquecer=3, recarga=99)
    lt = _luta(_chefe("balanca", balanca, vida=100))
    j, r = lt.jogador, lt.rival
    r.vida = 40  # você tem mais (em fração)
    _vez_do_chefe(lt, balanca)
    acao = lt.turno_rival()
    assert acao.mecanica == "balanca_virou"
    assert j.pular == 0 and j.bonus_dano == 0
    assert r.pular == 1 and r.bonus_dano == -3
    with lt.foco(r):  # ele não ergue a Balança quando ela viraria
        r.recargas.clear()
        r.pular = 0
        assert escolher_rival(lt) != balanca


def test_carregar_cada_turno_sem_disparar_carrega_o_disparo():
    disparo = Tecnica("disparo", "Disparo", "ataque", dano=10, recarga=3)
    lt = _luta(_chefe("carregar", disparo), vida=500)
    r = lt.rival
    for carga in (1, 2, 2):
        _vez_do_chefe(lt, GUARDA)
        lt.turno_rival()
        assert r.carga == carga  # até 2 cargas
    _vez_do_chefe(lt, disparo)
    acao = lt.turno_rival()
    assert acao.dano == round(10 * (1 + 2 * CARGA_BONUS)) and acao.mecanica == "carregar"
    assert r.carga == 0


def test_carregar_atordoar_descarrega_e_o_piloto_interrompe():
    disparo = Tecnica("disparo", "Disparo", "ataque", dano=10, recarga=3)
    lua = Tecnica("lua_ilusoria", "Lua", "maldita", atordoar=1, recarga=3)
    lt = _luta(_chefe("carregar", disparo), tecnicas=(DIRETO, lua))
    lt.jogador.percepcao = 3  # vê o que vem
    r = lt.rival
    r.carga = 2
    with lt.foco(r):
        lt.intencao_rival = disparo
    _vez_do_jogador(lt)
    assert escolher_jogador_auto(lt) == lua
    lt.resolver(lua)
    assert r.carga == 0


@pytest.mark.parametrize("mecanica", ["adaptar", "contrato"])
def test_o_piloto_nao_gasta_a_tecnica_que_nao_renderia(mecanica):
    lt = _luta(_chefe(mecanica), tecnicas=(DIRETO,))
    if mecanica == "adaptar":
        lt.rival.adaptacao["direto"] = 2  # a roda já girou para o Direto
    # (no contrato firmado, o primeiro golpe vai embora: o Golpe gasta o contrato)
    assert escolher_jogador_auto(lt) == BASICO
