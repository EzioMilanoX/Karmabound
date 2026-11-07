"""Leva 5: os vilões, o Dono da Roda, o capítulo secreto, o modo História e os Arcos novos."""

import random
from collections import Counter

import pytest
from test_jornada import jogar_ate_o_fim

from karmabound import combate
from karmabound.combate import Luta, Lutador, Tecnica
from karmabound.historias import ORIGINAL, carregar_arcos_da_historia, carregar_historias
from karmabound.jornada import Jornada
from karmabound.legado import DONOS_PARA_ALEM, Legado
from karmabound.rodas import anime_de, carregar_chefes, carregar_mecanicas
from karmabound.run import Contexto, animes_jogaveis, gerar_oponentes
from karmabound.viloes import DONO, REFLEXO, carregar_viloes, escolher_chefe

ELENCO = carregar_viloes()
HISTORIAS = carregar_historias()
CTX = Contexto.padrao()
ASSINATURAS = {c.id: c for c in carregar_chefes()}
MECANICAS = carregar_mecanicas()
TECNICAS = CTX.tecnicas
ARCOS = {f.id for f in CTX.rodas["arco"].fatias} | set(carregar_arcos_da_historia())

BASICO = Tecnica("golpe_basico", "Golpe", "ataque", dano=4)
GUARDA = Tecnica("guarda", "Guarda", "defesa")
DIRETO = Tecnica("direto", "Direto", "ataque", dano=10)


# ----------------------------------------------------------------------- os dados


def test_todo_id_citado_por_um_vilao_existe():
    for v in ELENCO.viloes:
        assert all(a in ASSINATURAS for a in v.assinaturas), v.id
        assert all(t in TECNICAS for t in v.tecnicas), v.id
        assert v.estilo in ("espadachim", "monge", "ninja", "oni", "hollow", "tita", "colosso")


def test_toda_mecanica_de_assinatura_tem_nome_kanji_e_texto():
    for a in ASSINATURAS.values():
        if a.mecanica:
            m = MECANICAS[a.mecanica]
            assert m["nome"] and m["kanji"] and m["texto"], a.id


@pytest.mark.parametrize("anime", animes_jogaveis(CTX.rodas))
def test_cada_anime_tem_tenentes_chefes_e_um_final(anime):
    so = frozenset({anime})
    papeis = Counter(v.papel for v in ELENCO.viloes if v.anime == anime)
    assert papeis["tenente"] >= 3 and papeis["chefe"] >= 2 and papeis["final"] == 1
    capitulos = {v.capitulo for v in ELENCO.do_papel("chefe", so)}
    assert {1, 2} <= capitulos
    assert len(ELENCO.final_de(anime).assinaturas) == 2


def test_os_dez_animes_tem_mundo_proprio():
    assert len(animes_jogaveis(CTX.rodas)) >= 10


@pytest.mark.parametrize("hid", list(HISTORIAS))
def test_toda_campanha_aponta_para_o_que_existe(hid):
    h = HISTORIAS[hid]
    assert len(h.capitulos) == 3
    caps = list(h.capitulos) + ([h.alem] if h.alem else [])
    for cap in caps:
        assert cap.arco in ARCOS, (hid, cap.arco)
        assert ELENCO.get(cap.chefe) is not None, (hid, cap.chefe)
        assert all(ELENCO.get(r) is not None for r in cap.rivais), hid
        for linha in (*cap.abertura, *cap.antes_do_chefe, *cap.depois):
            assert linha.quem in ("", "voce") or ELENCO.get(linha.quem), (hid, linha.quem)
    assert ELENCO[h.capitulos[-1].chefe].papel == "final"
    if h.anime:  # a campanha de um anime fecha com o maior vilão dele
        assert ELENCO[h.capitulos[-1].chefe].anime == h.anime


def test_a_campanha_original_tem_os_dois_finais_e_o_secreto():
    h = HISTORIAS[ORIGINAL]
    assert {f.id for f in h.escolha} == {"quebrar", "tomar"}
    assert h.alem is not None and h.alem.chefe == REFLEXO
    assert h.capitulos[-1].chefe == DONO and h.convite


def test_os_arcos_novos_tem_cenario():
    from karmabound.arenas import _par

    for a in CTX.rodas["arco"].fatias:
        assert _par(a.id) is not None, a.id
    for aid in carregar_arcos_da_historia():
        assert _par(aid) is not None, aid


# ----------------------------------------------------------------------- quem aparece


def test_o_dono_fecha_o_ultimo_capitulo_do_classico():
    rng = random.Random(1)
    assert escolher_chefe(ELENCO, 3, True, rng).id == DONO
    pool = {escolher_chefe(ELENCO, 1, False, random.Random(s)).id for s in range(40)}
    assert DONO not in pool and len(pool) > 3  # o capítulo 1 sorteia de uma lista


def test_no_mundo_de_um_anime_so_aparecem_os_viloes_dele():
    for seed in range(4):
        j = Jornada.nova("acessivel", seed=seed, jogo="anime", anime="Bleach")
        jogar_ate_o_fim(j)
        assert all(ELENCO[v].anime == "Bleach" for v in j.estado.viloes_vistos)


def test_um_rival_com_vilao_tem_o_nome_e_as_tecnicas_dele():
    ctx = Contexto.padrao("acessivel", jogo="historia", historia="naruto")
    j = Jornada.nova("acessivel", seed=2, jogo="historia", historia="naruto")
    e = j.estado
    e.luta_no_capitulo = e.tamanho_capitulo  # a luta do chefe
    chefe = gerar_oponentes(e, ctx, random.Random(0))[0]
    vilao = ELENCO[HISTORIAS["naruto"].capitulos[0].chefe]
    assert chefe.nome == vilao.nome and chefe.vilao == vilao.id and chefe.chefe
    assert set(vilao.assinaturas) <= {t.id for t in chefe.tecnicas}


def test_o_final_fica_com_a_mecanica_nova():
    """Com duas assinaturas, a mecânica que só o final tem vence a antiga."""
    ctx = Contexto.padrao("acessivel", jogo="historia", historia="naruto")
    j = Jornada.nova("acessivel", seed=2, jogo="historia", historia="naruto")
    e = j.estado
    e.capitulo, e.luta_no_capitulo = 3, e.tamanho_capitulo
    final = gerar_oponentes(e, ctx, random.Random(0))[0]
    assert final.mecanica == "sonho_eterno"


# ----------------------------------------------------------------------- a História


def test_a_historia_mostra_as_cenas_e_termina_num_final():
    for seed in range(6):
        j = Jornada.nova("acessivel", seed=seed, jogo="historia", historia=ORIGINAL)
        fases = jogar_ate_o_fim(j)
        assert fases[2] == "cena"  # a abertura do capítulo 1 vem antes do Arco
        if j.fase == "vitoria":
            assert "final" in fases and j.estado.final in ("quebrar", "tomar")
            return
    pytest.fail("nenhuma das seeds venceu a campanha")


def test_o_arco_da_historia_e_o_do_capitulo():
    j = Jornada.nova("acessivel", seed=0, jogo="historia", historia="one_piece")
    j.girar_linhagem()
    j.girar_destino()
    while j.fase == "cena":
        j.avancar_cena()
    assert j.girar_arco().fatias[0].id == HISTORIAS["one_piece"].capitulos[0].arco


def test_derrota_na_historia_passa_pela_cena():
    for seed in range(8):
        j = Jornada.nova("acessivel", seed=seed, jogo="historia", historia=ORIGINAL)
        fases = jogar_ate_o_fim(j)
        if j.fase == "derrota":
            assert fases[-2:] == ["cena", "derrota"]
            return


# ----------------------------------------------------------------------- além da Roda


def test_o_convite_leva_ao_reflexo_e_ao_final_verdadeiro():
    vistos = Counter()
    for seed in range(12):
        j = Jornada.nova("acessivel", seed=seed, jogo="classico", alem=True)
        fases = jogar_ate_o_fim(j, seguir=True)
        if "convite" in fases:
            assert j.estado.alem
            vistos["convite"] += 1
            if j.fase == "vitoria":
                assert REFLEXO in j.estado.viloes_vistos and j.estado.capitulo == 5
                return
    assert vistos["convite"], "ninguém venceu o Dono em 12 seeds"


def test_recusar_o_convite_e_vencer():
    for seed in range(12):
        j = Jornada.nova("acessivel", seed=seed, jogo="classico", alem=True)
        fases = jogar_ate_o_fim(j, seguir=False)
        if "convite" in fases:
            assert j.fase == "vitoria" and not j.estado.alem
            return


def test_sem_o_secreto_aberto_nao_ha_convite():
    for seed in range(6):
        j = Jornada.nova("acessivel", seed=seed, jogo="classico")
        assert "convite" not in jogar_ate_o_fim(j)


def test_o_legado_abre_o_secreto_depois_de_vencer_o_dono():
    leg = Legado()
    for n in range(DONOS_PARA_ALEM):
        f = leg.fechar_run(["Naruto"], 12, 3, True, Counter(), dono=True)
        assert leg.alem_aberto == (n + 1 >= DONOS_PARA_ALEM)
    assert f.alem_aberto
    f = leg.fechar_run(["Naruto"], 12, 3, True, Counter(), final="verdadeiro")
    assert f.final_novo == "verdadeiro" and "verdadeiro" in leg.finais


# ----------------------------------------------------------------------- as mecânicas


def _chefe(mecanica, tecnicas, vida=1000, assinatura=""):
    return Lutador(
        "Chefe", vida, 1, 0, list(tecnicas), chefe=True, mecanica=mecanica, assinatura=assinatura
    )


def _luta(chefe, tecnicas=(DIRETO,), vida=100, seed=0):
    j = Lutador("Você", vida, 3, 0, list(tecnicas))
    lt = Luta(j, chefe, BASICO, random.Random(seed))
    lt.abertura = False
    return lt


def _chefe_usa(lt, t):
    lt.vez = lt.rival
    lt.intencao_rival = t
    return lt.resolver(t)


def test_o_reflexo_luta_com_as_suas_tecnicas():
    ctx = Contexto.padrao("acessivel", jogo="classico", alem=True)
    j = Jornada.nova("acessivel", seed=0, alem=True)
    e = j.estado
    e.alem, e.capitulo, e.luta_no_capitulo = True, 4, e.tamanho_capitulo
    from karmabound.run import comecar_luta

    luta = comecar_luta(e, ctx, random.Random(0))
    assert luta.rival.vilao == REFLEXO
    assert {t.id for t in e.jogador.tecnicas} <= {t.id for t in luta.rival.tecnicas}


def test_o_giro_do_dono_muda_a_regra_e_te_da_carma():
    dono = _chefe("giro_da_roda", [GUARDA])
    lt = _luta(dono)
    from karmabound.carma import Carma, ConfigCarma
    from karmabound.rodas import carregar_balanceamento

    lt.jogador.carma = Carma(ConfigCarma.de_dict(carregar_balanceamento()["carma"]))
    _chefe_usa(lt, GUARDA)
    assert lt.roda_dono in combate.GIRO_FATIAS
    assert lt.jogador.carma.valor >= combate.GIRO_CARMA - 1e-9


def test_o_roubo_toma_a_sua_tecnica_mais_forte():
    mao = Tecnica("mao", "Mão", "ataque", dano=6)
    lt = _luta(_chefe("roubar", [mao], assinatura="mao"), tecnicas=(DIRETO, GUARDA))
    _chefe_usa(lt, mao)
    assert lt.jogador.recargas["direto"] == 99
    assert any(t.id == "direto" for t in lt.rival.tecnicas)


def test_a_marcha_fere_cada_vez_mais_sem_defesa():
    passo = Tecnica("passo", "Passo", "maldita", invocar=1)
    lt = _luta(_chefe("marcha", [passo, GUARDA], assinatura="passo"), vida=200)
    _chefe_usa(lt, passo)
    lt.jogador.bloqueio = 999
    vida = lt.jogador.vida
    _chefe_usa(lt, GUARDA)
    _chefe_usa(lt, GUARDA)
    assert vida - lt.jogador.vida == 2 + 3  # a marcha sobe e atravessa o bloqueio


def test_o_rei_renascido_volta_uma_vez():
    lt = _luta(_chefe("rei_renascido", [GUARDA], vida=100), tecnicas=(DIRETO,))
    lt.rival.vida, lt.rival.segunda_forma = 1, True  # à beira da morte (a postura não segura 1)
    lt.vez = lt.jogador
    lt.resolver(DIRETO)
    assert lt.rival.vivo and lt.rival.renasceu and lt.rival.chama
    assert not lt.acabou


def test_os_cinco_minutos_explodem_o_planeta():
    nucleo = Tecnica("nucleo", "Núcleo", "maldita", dano=1)
    lt = _luta(_chefe("cinco_minutos", [nucleo, GUARDA], assinatura="nucleo"), vida=100)
    _chefe_usa(lt, nucleo)
    for _ in range(combate.CINCO_MINUTOS):
        _chefe_usa(lt, GUARDA)
    assert lt.jogador.vida <= 100 - 1 - round(100 * combate.CINCO_MINUTOS_DANO)


def test_o_amanhecer_queima_do_sexto_turno_em_diante():
    lt = _luta(_chefe("amanhecer", [GUARDA], vida=100))
    lt.rival.vida = 50
    for _ in range(combate.AMANHECER_TURNO - 1):
        _chefe_usa(lt, GUARDA)
    curado = lt.rival.vida
    assert curado > 50
    _chefe_usa(lt, GUARDA)
    assert lt.rival.vida < curado


def test_uma_luta_longa_demais_termina():
    """Ninguém causa dano: o desgaste da luta longa acaba com ela mesmo assim."""
    a = Lutador("Você", 30, 3, 0, [GUARDA])
    b = Lutador("Rival", 30, 1, 0, [GUARDA])
    lt = Luta(a, b, Tecnica("golpe_basico", "Golpe", "ataque", dano=0), random.Random(0))
    for _ in range(400):
        if lt.acabou:
            break
        if lt.vez is lt.jogador:
            lt.resolver(GUARDA)
        else:
            lt.turno_rival()
    assert lt.acabou


def test_o_enfraquecer_tem_teto():
    a = Lutador("A", 30, 1, 0, [])
    combate.enfraquecer(a, 10)
    assert a.bonus_dano == -combate.ENFRAQUECER_MAX


def test_origens_dos_viloes_de_anime_dizem_a_obra():
    for v in ELENCO.viloes:
        if v.papel != "secreto" and v.id != DONO and v.origem:
            assert anime_de(v.origem), v.id
