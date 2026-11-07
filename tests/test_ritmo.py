"""O ritmo da run: a postura e a segunda forma do chefe, e o treino entre as lutas."""

import random

from karmabound.carma import Carma, ConfigCarma
from karmabound.combate import (
    FURIA_CHEFE,
    POSTURA_CHEFE,
    Luta,
    Lutador,
    Tecnica,
)
from karmabound.jornada import Jornada
from karmabound.rodas import carregar_balanceamento
from karmabound.tela_menus import TreinoScene
from karmabound.treino import Treino, aplicar, carregar_treinos, escolher_auto, oferecer

BASICO = Tecnica("golpe_basico", "Golpe", "ataque", dano=4)
GUARDA = Tecnica("guarda", "Guarda", "defesa", bloqueio=0)
MARRETA = Tecnica("marreta", "Marreta", "ataque", dano=90, recarga=3)


def _luta(chefe=True, vida_rival=100):
    j = Lutador("J", 100, 1, 0, [MARRETA])
    r = Lutador("R", vida_rival, 1, 0, [GUARDA], chefe=chefe)
    lt = Luta(j, r, BASICO, random.Random(0))
    lt.abertura = False
    lt.vez = j
    return lt


# ----------------------------------------------------------------------- chefe


def test_a_postura_segura_o_golpe_que_mataria_o_chefe():
    lt = _luta()
    acao = lt.resolver(MARRETA)
    assert acao.dano == round(100 * POSTURA_CHEFE)
    assert lt.rival.vivo


def test_rival_comum_nao_tem_postura():
    lt = _luta(chefe=False)
    assert lt.resolver(MARRETA).dano == 90


def test_feridas_que_duram_passam_pela_postura():
    lt = _luta()
    lt.rival.veneno = 60  # 60 de veneno por turno: muito mais que a postura
    lt.vez = lt.rival
    lt.resolver(GUARDA)
    assert lt.rival.vida <= 100 - 60


def test_segunda_forma_na_metade_da_vida_uma_vez_so():
    lt = _luta()
    rival = lt.rival
    rival.recargas["guarda"] = 3
    rival.vida = 60
    acao = lt.resolver(MARRETA)  # 30 de postura: 60 -> 30, metade de 100
    assert acao.segunda_forma and rival.segunda_forma
    assert rival.dano_mult == FURIA_CHEFE
    assert not rival.recargas  # todas as técnicas prontas de novo
    lt.vez = lt.jogador
    acao = lt.resolver(BASICO)
    assert not acao.segunda_forma
    assert rival.dano_mult == FURIA_CHEFE  # não empilha


# ----------------------------------------------------------------------- treino


def _jogador():
    bal = carregar_balanceamento()
    carma = Carma(ConfigCarma.de_dict(bal["carma"]))
    return Lutador("Você", 100, 2, 1, [], carma=carma)


def test_treinos_dos_dados_e_oferta_de_tres_diferentes():
    treinos, n = carregar_treinos()
    assert n == 3 and len(treinos) >= 6
    oferta = oferecer(treinos, n, random.Random(1))
    assert len({t.id for t in oferta}) == 3
    for t in treinos:  # todo treino faz alguma coisa
        assert t.vida_max or t.dano or t.velocidade or t.percepcao or t.cura or t.carma


def test_o_treino_fica_mesmo_quando_os_efeitos_mudam():
    j = _jogador()
    j.vida = 50
    aplicar(j, Treino("a", "A", "体", "", vida_max=10, dano=1, velocidade=1, percepcao=1))
    assert (j.vida_max, j.vida, j.dano_run) == (110, 60, 1)
    j.aplicar_efeitos(j.efeitos)  # recalcular da base não desfaz o treino
    assert (j.vida_max, j.velocidade, j.percepcao) == (110, 3, 2)


def test_respirar_e_meditar():
    j = _jogador()
    j.vida = 20
    aplicar(j, Treino("r", "R", "息", "", cura=0.4))
    assert j.vida == 60
    aplicar(j, Treino("m", "M", "業", "", carma=30))
    assert j.carma.valor == 30


def test_o_piloto_respira_quando_esta_mal_e_treina_quando_esta_bem():
    treinos, _ = carregar_treinos()
    por_id = {t.id: t for t in treinos}
    oferta = (por_id["respiracao_profunda"], por_id["punhos_de_ferro"], por_id["passos_leves"])
    j = _jogador()
    assert escolher_auto(j, oferta).id == "punhos_de_ferro"
    j.vida = 30
    assert escolher_auto(j, oferta).id == "respiracao_profunda"


def _vencer_uma_luta(seed=4):
    j = Jornada.nova("acessivel", seed=seed)
    j.girar_linhagem()
    j.girar_destino()
    j.girar_arco()
    if j.fase == "caminho":  # antes da luta, as portas: a do Rival
        j.escolher_caminho([p.tipo for p in j.oferta_caminho].index("rival"))
    j.luta.rival.vida = 0  # a luta acaba com a vitória
    assert j.terminar_luta()
    return j


def test_depois_da_vitoria_vem_o_treino_e_depois_a_tecnica():
    j = _vencer_uma_luta()
    extra = j.estado.regra.get("treino_extra", 0)  # um Arco pode oferecer um a mais
    assert j.fase == "treino" and len(j.oferta_treino) == 3 + extra
    antes = j.jogador.base_vida_max
    escolhido = j.escolher_treino(0)
    assert j.fase == "tecnica" and not j.oferta_treino
    assert j.jogador.base_vida_max == antes + escolhido.vida_max


def test_tela_do_treino_escolhe_pelo_cursor():
    from tests.test_controle import Entrada, aperta

    j = _vencer_uma_luta()
    terceiro = j.oferta_treino[2]
    fim = []
    tela = TreinoScene(j, Entrada(), lambda: fim.append(1), lambda: None)
    e = tela.entrada
    aperta(tela, e, "direita")
    aperta(tela, e, "direita")
    vel = j.jogador.base_velocidade
    aperta(tela, e, "confirmar")
    assert fim and j.fase == "tecnica"
    assert j.jogador.base_velocidade == vel + terceiro.velocidade
