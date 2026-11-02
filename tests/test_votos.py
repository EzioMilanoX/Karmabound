import random

import pytest

from karmabound.combate import HESITAR, Luta, Lutador, Tecnica
from karmabound.efeitos import NEUTRO, Efeitos, somar
from karmabound.run import Contexto, aplicar_voto, jogar_run, medir, nova_run
from karmabound.votos import FimDaRun, Voto, Votos, carregar_catalogo, lutas_da_duracao

CAT = carregar_catalogo()
R, G = CAT.restricoes, CAT.ganhos
BASICO = Tecnica("golpe_basico", "Golpe", "ataque", dano=4)
GUARDA = Tecnica("guarda", "Guarda", "defesa", bloqueio=8, recarga=2)
INVESTIDA = Tecnica(
    "investida", "Investida", "ataque", dano=10, recarga=2, sutileza=1, perigosa=True
)


def lutador(tecnicas=(), efeitos=NEUTRO, vida=50, vel=1, perc=0):
    return Lutador("J", vida, vel, perc, list(tecnicas), efeitos=efeitos)


# ------------------------------------------------------------------ catálogo e efeitos


def test_catalogo_carrega_restricoes_e_ganhos():
    assert len(R) == 8 and len(G) == 11
    assert {g.categoria for g in G.values()} == {"simples", "especial", "exclusivo"}
    assert G["forca"].niveis == 5 and G["segunda_vida"].niveis == 1
    assert {r.categoria for r in R.values()} == {"simples", "conduta", "revelacao", "risco"}


def test_somar_efeitos():
    total = somar([R["corpo_ofertado"].efeito, G["vigor"].efeito, G["forca"].efeito])
    assert total.vida_max_mult == 0.75 and total.vida_max == 15 and total.bonus_dano == 2


def test_aplicar_e_desfazer_efeitos_volta_a_base():
    j = lutador(vel=2, perc=1)
    j.aplicar_efeitos(somar([R["corpo_ofertado"].efeito, G["passo_leve"].efeito]))
    assert (j.vida_max, j.velocidade, j.vida) == (38, 3, 38)
    j.aplicar_efeitos(Efeitos())
    assert (j.vida_max, j.velocidade) == (50, 2)
    assert j.vida == 38  # vida perdida não volta sozinha


# ------------------------------------------------------------------ efeitos no combate


def test_sem_guarda_tira_a_defesa_das_opcoes():
    j = lutador([GUARDA, INVESTIDA], efeitos=R["sem_guarda"].efeito, vel=3)
    lt = Luta(j, lutador(), BASICO, random.Random(0))
    assert GUARDA not in lt.prontas(j)
    with pytest.raises(ValueError):
        lt.resolver(GUARDA)


def test_maos_atadas_sem_tecnica_pronta_hesita():
    j = lutador([INVESTIDA], efeitos=R["maos_atadas"].efeito, vel=3)
    lt = Luta(j, lutador(), BASICO, random.Random(0))
    assert BASICO not in lt.prontas(j)
    lt.resolver(INVESTIDA)
    lt.turno_rival()
    assert lt.prontas(j) == [HESITAR]
    assert lt.resolver(HESITAR).dano == 0


def test_golpe_oculto_nao_e_percebido():
    j = lutador([INVESTIDA], efeitos=G["golpe_oculto"].efeito, vel=3)
    rival = lutador(perc=5)
    lt = Luta(j, rival, BASICO, random.Random(0))
    lt.abertura = False
    assert not lt.resolver(INVESTIDA).reagiu


def test_voto_exposto_da_percepcao_ao_rival():
    j = lutador([INVESTIDA], efeitos=R["voto_exposto"].efeito, vel=3)
    lt = Luta(j, lutador(perc=0), BASICO, random.Random(0))
    lt.abertura = False
    assert lt.resolver(INVESTIDA).reagiu  # 0 + 2 >= Sutileza 1


def test_primeiro_sangue_comeca_e_a_surpresa_passa():
    j = lutador([INVESTIDA], efeitos=G["primeiro_sangue"].efeito, vel=0)
    lt = Luta(j, lutador(vel=9, perc=9), BASICO, random.Random(0))
    assert lt.vez is j
    acao = lt.resolver(INVESTIDA)
    assert acao.surpresa and not acao.reagiu


def test_fio_da_navalha_mata_abaixo_de_20_por_cento():
    j = lutador(efeitos=R["fio_da_navalha"].efeito)
    j.sofrer(39)  # sobra 11 de 50: acima de 10
    assert j.vivo
    j.sofrer(2)
    assert not j.vivo


def test_prazo_estourado_e_derrota():
    j = lutador(efeitos=R["prazo"].efeito, vel=3)
    rival = lutador(vida=999)
    lt = Luta(j, rival, BASICO, random.Random(0))
    while not lt.acabou:
        if lt.vez is j:
            lt.resolver(BASICO)
        else:
            lt.turno_rival()
    assert lt.estourou_prazo and lt.vencedor is rival and j.vivo
    assert lt.turnos == 20


def test_pele_de_espinhos_rearma_o_revide():
    j = lutador(efeitos=G["pele_de_espinhos"].efeito, vel=3)
    rival = lutador([INVESTIDA])
    lt = Luta(j, rival, BASICO, random.Random(0))
    lt.resolver(BASICO)
    assert j.revide == 3
    lt.turno_rival()
    assert j.revide == 0  # gastou no golpe recebido
    lt.resolver(BASICO)
    assert j.revide == 3


# ------------------------------------------------------------------ pontos, duração, limite


def test_pontos_crescem_mais_que_o_sacrificio():
    r = [R["corpo_ofertado"]]
    um, tres = CAT.pontos(1, "run", r), CAT.pontos(3, "run", r)
    assert tres > 3 * um
    assert CAT.pontos(0, "run", r) == 0 and CAT.pontos(-1, "run", r) == 0


def test_permanente_e_risco_rendem_mais():
    assert CAT.pontos(2, "run", [R["prazo"]]) > CAT.pontos(2, "luta", [R["prazo"]])
    assert CAT.pontos(2, "run", [R["prazo"]]) > CAT.pontos(2, "run", [R["corpo_ofertado"]])


def test_duracoes():
    assert lutas_da_duracao("luta", 5, 4) == 1
    assert lutas_da_duracao("capitulo", 5, 4) == 4  # depois do chefe: o capítulo seguinte inteiro
    assert lutas_da_duracao("capitulo", 7, 4) == 2  # lutas 7 e 8
    assert lutas_da_duracao("run", 3, 4) is None


def test_voto_temporario_expira_e_libera_espaco():
    v = Votos(CAT)
    voto = Voto([R["sem_guarda"]], [G["forca"]], "luta", lutas_restantes=1)
    v.jurar(voto)
    assert v.efeitos().bonus_dano == 2
    assert v.fim_de_luta() == [voto]
    assert not v.ativos and v.efeitos().bonus_dano == 0


def test_limite_de_votos():
    v = Votos(CAT)
    for _ in range(CAT.limite_ativos):
        v.jurar(Voto([R["sem_descanso"]], []))
    assert not v.pode_jurar()
    with pytest.raises(ValueError):
        v.jurar(Voto([R["prazo"]], []))


# ------------------------------------------------------------------ quebra


def test_quebrar_pune_libera_espaco_e_exige_voto_de_quebra():
    from karmabound.carma import Carma, ConfigCarma

    carma = Carma(ConfigCarma(100, {}, 20, 6, 60, 3.0, ()), valor=70)
    j = lutador(vida=40)
    v = Votos(CAT)
    original = Voto([R["sem_guarda"]], [G["forca"], G["vigor"]])
    v.jurar(original)
    j.aplicar_efeitos(v.efeitos())
    with pytest.raises(ValueError):
        v.quebrar(original, None, j, carma)
    quebra = Voto([R["passos_pesados"]], [G["forca"]])
    vida = j.vida
    v.quebrar(original, quebra, j, carma)
    assert original in v.quebrados and original not in v.ativos
    assert quebra.de_quebra and quebra.ganhos == []  # paga a dívida, não compra poder
    assert j.vida == vida - round(vida * 0.5) and carma.valor == 0
    assert j.efeitos.bonus_dano == 0 and j.velocidade == 0  # perdeu os ganhos, pagou a quebra


def test_quebrar_o_voto_de_quebra_encerra_a_run():
    j = lutador()
    v = Votos(CAT)
    original = Voto([R["sem_guarda"]], [])
    v.jurar(original)
    quebra = Voto([R["prazo"]], [])
    v.quebrar(original, quebra, j)
    with pytest.raises(FimDaRun):
        v.quebrar(quebra, Voto([R["sem_descanso"]], []), j)


# ------------------------------------------------------------------ medição (o Altar)


def test_medir_e_deterministico_e_restricao_dura_custa():
    ctx = Contexto.padrao("equilibrado")
    estado = nova_run(ctx, random.Random(3))

    def corpo(e):
        aplicar_voto(e, ctx, Voto([R["corpo_ofertado"], R["sem_descanso"]], []))

    a = medir(estado, ctx, corpo, amostras=40, seed=9)
    assert a == medir(estado, ctx, corpo, amostras=40, seed=9)
    assert a < 0  # tirar vida e cura custa lutas


def test_medir_sem_modificacao_da_zero():
    ctx = Contexto.padrao()
    estado = nova_run(ctx, random.Random(5))
    assert medir(estado, ctx, lambda e: None, amostras=20, seed=1) == 0


def test_clonar_nao_mexe_no_original():
    ctx = Contexto.padrao()
    estado = nova_run(ctx, random.Random(2))
    vida, carma = estado.jogador.vida, estado.mesa.carma.valor
    jogar_run(estado.clonar(random.Random(1)), ctx, random.Random(1))
    assert estado.jogador.vida == vida and estado.mesa.carma.valor == carma
    assert estado.proxima_luta == 1


# ------------------------------------------------------------------ níveis, teto, exclusivos


def test_niveis_de_um_ganho_se_somam():
    voto = Voto([], [G["forca"], G["forca"], G["forca"]])
    assert voto.efeitos.bonus_dano == 6


def test_teto_por_restricao_credita_no_maximo_o_teto():
    teto = CAT.teto_por_restricao
    assert CAT.creditado(5.0, [5.0]) == teto  # uma devastadora sozinha: só o teto
    assert CAT.creditado(3.0, [2.0, 2.0]) == min(3.0, 2 * teto)  # juntas passam do teto
    assert CAT.creditado(0.4, [2.0, 2.0]) == 0.4  # nunca credita mais que o medido junto
    assert CAT.creditado(-1, [1.0]) == 0


def test_juntar_restricoes_rende_mais_que_uma_so():
    r = [R["sem_descanso"]]
    so_uma = CAT.pontos(CAT.creditado(4.0, [4.0]), "run", r)
    duas = CAT.pontos(CAT.creditado(4.0, [2.0, 2.0]), "run", r + [R["passos_pesados"]])
    assert duas > so_uma


def test_preco_cresce_com_o_nivel_e_exclusivo_custa_mais():
    assert CAT.preco(G["forca"], 0.5, 2) == 2 * CAT.preco(G["forca"], 0.5, 1)
    assert CAT.preco(G["carrasco"], 0.5, 1) > CAT.preco(G["forca"], 0.5, 1)
    assert CAT.preco(G["forca"], -1.0, 1) == CAT.preco_minimo * CAT.preco_cambio  # nunca de graça


def test_segunda_vida_revive_uma_vez():
    j = lutador(efeitos=G["segunda_vida"].efeito)
    j.sofrer(999)
    assert j.vivo and j.vida == 15
    j.sofrer(999)
    assert not j.vivo


def test_carrasco_bate_mais_forte_em_chefe():
    j = lutador([INVESTIDA], efeitos=G["carrasco"].efeito, vel=3)
    chefe = Lutador("Chefe", 99, 1, 0, [], chefe=True)
    lt = Luta(j, chefe, BASICO, random.Random(0))
    lt.abertura = False
    assert lt.resolver(INVESTIDA).dano == 15


def test_sangue_frio_sempre_reage_a_surpresa():
    rival = lutador([INVESTIDA], vel=9)
    lancada = Tecnica("lanca", "Lança", "ataque", dano=10, sutileza=3, perigosa=True)
    rival.tecnicas = [lancada]
    j = lutador(efeitos=G["sangue_frio"].efeito, perc=0)
    lt = Luta(j, rival, BASICO, random.Random(0))
    assert lt.vez is rival
    lt.intencao_rival = lancada
    assert lt.turno_rival().reagiu
