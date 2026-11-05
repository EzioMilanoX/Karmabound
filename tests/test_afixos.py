"""Afixos de elite: toda elite ganha 1 (2 a partir do capítulo 3)."""

import random

import pytest

from karmabound.caminho import (
    aplicar_afixos,
    carregar_caminho,
    fortalecer_elite,
    sortear_afixos,
)
from karmabound.combate import BLINDADO_CADA, Luta, Lutador, Tecnica

BASICO = Tecnica("golpe_basico", "Golpe", "ataque", dano=4)
GUARDA = Tecnica("guarda", "Guarda", "defesa")
SOCO = Tecnica("soco", "Soco", "ataque", dano=5)
TODOS = {
    "vampirico",
    "espinhos",
    "veloz",
    "invocador",
    "blindado",
    "furioso",
    "amaldicoado",
    "gelido",
}


@pytest.fixture(scope="module")
def cam():
    return carregar_caminho()


def _elite(cam, afixos, capitulo=1, tecnicas=(SOCO,), vida=100):
    r = Lutador("Elite", vida, 1, 0, list(tecnicas))
    aplicar_afixos(cam, r, tuple(afixos), capitulo)
    return r


def _luta(rival, seed=0):
    j = Lutador("Você", 100, 3, 0, [Tecnica("direto", "Direto", "ataque", dano=10)])
    lt = Luta(j, rival, BASICO, random.Random(seed))
    lt.abertura = False
    return lt


def test_os_afixos_dos_dados_tem_nome_kanji_e_texto(cam):
    assert set(cam.afixos) == TODOS
    for a in cam.afixos.values():
        assert a.nome and a.kanji and a.texto


def test_um_afixo_e_dois_a_partir_do_capitulo_3(cam):
    rng = random.Random(1)
    assert len(sortear_afixos(cam, rng, 1)) == 1
    assert len(sortear_afixos(cam, rng, 2)) == 1
    dois = sortear_afixos(cam, rng, 3)
    assert len(dois) == 2 and len(set(dois)) == 2


def test_fortalecer_elite_sorteia_os_afixos_com_o_rng_da_run(cam):
    r = Lutador("Elite", 50, 1, 0, [SOCO])
    fortalecer_elite(cam, r, rng=random.Random(4), capitulo=3)
    assert r.elite and len(r.afixos) == 2 and set(r.afixos) <= TODOS
    sem = Lutador("Elite", 50, 1, 0, [SOCO])
    fortalecer_elite(cam, sem)  # sem rng: sem afixo (o bando de elite, menos o Comandante)
    assert sem.afixos == ()


def test_a_elite_da_run_tem_afixo_e_no_bando_so_o_comandante(cam):
    from karmabound.run import Contexto, gerar_oponentes, nova_run

    ctx = Contexto.padrao("dificil")
    e = nova_run(ctx, random.Random(2))
    e.porta = ctx.caminho.porta("elite")
    (elite,) = gerar_oponentes(e, ctx, random.Random(5))
    assert elite.elite and len(elite.afixos) == 1
    e.porta = ctx.caminho.porta("elite", papeis=("comandante", "lamina", "curandeiro"))
    bando = gerar_oponentes(e, ctx, random.Random(5))
    assert [bool(r.afixos) for r in bando] == [True, False, False]


def test_vampirico_drena(cam):
    r = _elite(cam, ["vampirico"])
    assert r.efeitos.drenar == pytest.approx(0.3)
    r.vida = 50
    lt = _luta(r)
    lt.vez = r
    lt.intencao_rival = SOCO
    acao = lt.turno_rival()
    assert acao.curou == round(5 * 0.3) and r.vida == 50 + acao.curou


def test_espinhos_revide_permanente_que_cresce_por_capitulo(cam):
    r = _elite(cam, ["espinhos"], capitulo=2)
    assert r.efeitos.revide_permanente == 3 and r.revide == 3
    lt = _luta(r)
    lt.resolver(lt.jogador.tecnicas[0])
    assert lt.jogador.vida == 97
    lt.intencao_rival = GUARDA
    lt.turno_rival()  # o revide volta ao fim do turno dele
    assert r.revide == 3


def test_veloz_mais_velocidade_e_age_duas_vezes_a_cada_tres_turnos(cam):
    r = _elite(cam, ["veloz"], tecnicas=(GUARDA,))
    assert r.velocidade == 3 and r.veloz == 3
    lt = _luta(r)
    acoes = []
    for _ in range(3):
        lt.vez = r
        acoes.append(lt.turno_rival())
    assert [a.turno_extra for a in acoes] == [False, False, True]
    assert lt.vez is r  # a ação seguida
    lt.turno_rival()
    assert lt.vez is lt.jogador and r.turnos_luta == 3  # a encadeada não conta como turno


def test_invocador_chega_com_uma_criatura(cam):
    r = _elite(cam, ["invocador"], capitulo=2)
    assert r.invocacoes == [[4, 4, "afixo_invocador"]]
    lt = _luta(r)
    lt.vez = r
    lt.intencao_rival = GUARDA
    r.tecnicas = [GUARDA]
    acao = lt.turno_rival()
    assert acao.invocadas == (("afixo_invocador", 4),) and lt.jogador.vida == 96


def test_blindado_chega_com_bloqueio_e_renova(cam):
    r = _elite(cam, ["blindado"], tecnicas=(GUARDA,))
    assert r.blindagem == 10 and r.bloqueio == 10
    lt = _luta(r)
    for _ in range(BLINDADO_CADA):
        r.bloqueio = 0
        lt.vez = r
        lt.turno_rival()
    assert r.bloqueio == 0  # turnos 2 e 3: nada
    lt.vez = r
    lt.turno_rival()  # turno 4: renova
    assert r.bloqueio == 10


def test_furioso_bate_mais_com_menos_vida(cam):
    r = _elite(cam, ["furioso"], capitulo=1)
    assert r.efeitos.furia == 5
    r.vida = 1  # quase morto: quase toda a fúria
    lt = _luta(r)
    lt.vez = r
    lt.intencao_rival = SOCO
    assert lt.turno_rival().dano == 5 + 5


def test_amaldicoado_deixa_a_marca_em_quem_ele_fere(cam):
    r = _elite(cam, ["amaldicoado"])
    lt = _luta(r)
    lt.vez = r
    lt.intencao_rival = SOCO
    lt.turno_rival()
    assert lt.jogador.marca == 1
    lt.vez = r
    lt.turno_rival()
    assert lt.jogador.marca == 1  # não soma


def test_gelido_pode_congelar(cam):
    r = _elite(cam, ["gelido"])
    lt = _luta(r)
    lt.rng.random = lambda: 0.0  # o gelo pega
    lt.vez = r
    lt.intencao_rival = SOCO
    acao = lt.turno_rival()
    assert acao.atordoou and lt.jogador.congelado and lt.jogador.pular == 1
