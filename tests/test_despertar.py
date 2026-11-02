"""O Despertar na luta: gatilho, Roda do Despertar, os quatro tipos e o Divino depois."""

import random

import pytest

from karmabound.carma import Carma, ConfigCarma
from karmabound.combate import Luta, Lutador, Tecnica
from karmabound.rodas import Fatia
from karmabound.run import Contexto, aplicar_arco, comecar_luta, encerrar_luta, girar, nova_run

BASICO = Tecnica("golpe_basico", "Golpe", "ataque", dano=4)
DIRETO = Tecnica("direto", "Direto", "ataque", dano=10, recarga=2, sutileza=3)
LANCA = Tecnica("lanca", "Lança", "ataque", dano=30, recarga=1, sutileza=3)
GUARDA = Tecnica("guarda", "Guarda", "defesa", bloqueio=8, recarga=2)


def tipo(**despertar) -> Fatia:
    return Fatia("x", "Tipo", "divino", "texto", "覚", despertar=despertar)


def carma_cheio() -> Carma:
    c = Carma(ConfigCarma(100, {}, 20, 6, 60, 3.0, ()))
    c.valor = 100
    return c


def montar(despertar: Fatia, jogador_tec=(DIRETO,), rival_tec=(), vida_j=100, vida_r=999):
    j = Lutador("Você", vida_j, 3, 0, list(jogador_tec), carma=carma_cheio())
    r = Lutador("Rival", vida_r, 1, 0, list(rival_tec))
    girados = []

    def ao_despertar():
        girados.append(despertar)
        return despertar

    lt = Luta(j, r, BASICO, random.Random(0), ao_despertar=ao_despertar)
    lt.abertura = False
    return lt, j, r, girados


def test_so_desperta_com_carma_cheio_ou_guardado():
    lt, j, _, _ = montar(tipo(forma=3))
    assert lt.pode_despertar()
    j.carma.valor = 50
    assert not lt.pode_despertar()
    with pytest.raises(RuntimeError):
        lt.despertar()
    j.carma.guardados = 1
    assert lt.pode_despertar()


def test_despertar_paga_o_carma_e_nao_gasta_o_turno():
    lt, j, _, girados = montar(tipo(forma=3))
    lt.despertar()
    assert j.carma.valor == 0 and girados and lt.vez is j


def test_forma_desperta_dobra_e_nao_deixa_recarregar():
    lt, j, r, _ = montar(tipo(forma=2))
    lt.despertar()
    assert lt.resolver(DIRETO).dano == 20
    assert j.recargas.get("direto", 0) == 0
    lt.turno_rival()
    assert lt.resolver(DIRETO).dano == 20  # ainda na forma, ainda sem recarga
    lt.turno_rival()
    assert lt.resolver(DIRETO).dano == 10  # a forma acabou


def test_retribuicao_devolve_a_dor_da_luta_em_3_golpes():
    lt, j, r, _ = montar(tipo(retribuicao_golpes=3), rival_tec=(LANCA,))
    lt.vez = r
    lt.intencao_rival = LANCA
    lt.turno_rival()  # você leva 30
    assert lt.dano_recebido == 30
    j.carma.valor = 100
    lt.despertar()
    assert (j.retrib_golpes, j.retrib_por_golpe) == (3, 10)
    assert lt.resolver(DIRETO).dano == 20


def test_tomar_o_destino_rouba_e_trava_o_rival():
    lt, j, r, _ = montar(tipo(roubar=True, travar_rival=2), rival_tec=(LANCA, GUARDA))
    lt.despertar()
    assert any(t.id == "lanca" for t in j.tecnicas)
    assert r.recargas["lanca"] >= 2 and r.recargas["guarda"] >= 2
    assert lt.intencao_rival is BASICO


def test_renascer_cura_tudo_e_escuda():
    lt, j, _, _ = montar(tipo(cura_total=True, escudos=2), vida_j=100)
    j.vida = 10
    lt.despertar()
    assert j.vida == 100 and j.escudos == 2


def test_a_beira_da_morte_o_golpe_fatal_e_anulado_e_voce_desperta():
    lt, j, r, girados = montar(tipo(forma=3), rival_tec=(LANCA,), vida_j=20)
    lt.vez = r
    lt.intencao_rival = LANCA
    acao = lt.turno_rival()  # 30 de dano: mataria
    assert acao.despertou == "x" and acao.dano == 0 and j.vida == 20
    assert girados and j.carma.valor == 0 and j.forma == 3


def test_sem_carma_o_golpe_fatal_mata():
    lt, j, r, _ = montar(tipo(forma=3), rival_tec=(LANCA,), vida_j=20)
    j.carma.valor = 0
    lt.vez = r
    lt.intencao_rival = LANCA
    lt.turno_rival()
    assert not j.vivo


# ------------------------------------------------------------------ na run


@pytest.fixture
def ctx():
    return Contexto.padrao("dificil")


def _arco(ctx):
    return next(f for f in ctx.rodas["arco"].fatias if f.id == "torneio_regular")


def test_roda_do_despertar_nao_mexe_no_carma(ctx):
    e = nova_run(ctx, random.Random(1))
    e.mesa.carma.valor = 33
    giro = e.mesa.girar("despertar")
    assert giro.fatias[0].despertar and e.mesa.carma.valor == 33


def test_carma_cheio_espera_a_luta_e_nao_desperta_no_giro(ctx):
    e = nova_run(ctx, random.Random(2))
    e.mesa.carma.valor = e.mesa.carma.config.maximo
    assert not girar(e, ctx, "tecnicas").despertar
    assert e.mesa.carma.transbordando


def test_despertar_na_luta_garante_um_divino_no_proximo_giro(ctx):
    e = nova_run(ctx, random.Random(3))
    aplicar_arco(e, ctx, _arco(ctx))
    e.mesa.carma.valor = e.mesa.carma.config.maximo
    lt = comecar_luta(e, ctx, random.Random(3))
    lt.despertar()
    assert e.despertares == 1 and e.divino_pendente == 1
    lt.rival.vida = 0
    encerrar_luta(e, ctx, lt)
    giro = girar(e, ctx, "tecnicas")
    assert giro.despertar and giro.fatias[0].raridade == ctx.ordem[-1]
    assert e.divino_pendente == 0
    assert not girar(e, ctx, "reliquias").despertar
