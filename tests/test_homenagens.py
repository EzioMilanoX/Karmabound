"""As habilidades-homenagem: cada mecânica nova, isolada, e a origem de todas."""

import random
from dataclasses import replace

import pytest

from karmabound.carma import Carma, ConfigCarma
from karmabound.combate import CRITICO, HESITAR, Luta, Lutador, Tecnica
from karmabound.efeitos import NEUTRO, Efeitos
from karmabound.rodas import Fatia
from karmabound.run import (
    Contexto,
    aplicar_arco,
    aplicar_dom,
    comecar_luta,
    encerrar_luta,
    espacos,
    nova_run,
    receber_reliquia,
    receber_tecnica,
)

BASICO = Tecnica("golpe_basico", "Golpe", "ataque", dano=4)
DIRETO = Tecnica("direto", "Direto", "ataque", dano=10, recarga=1, sutileza=3)
GUARDA = Tecnica("guarda", "Guarda", "defesa", bloqueio=8, recarga=2)
LANCA = Tecnica("lanca", "Lança", "ataque", dano=12, recarga=2, sutileza=3)


def lut(nome="J", tecnicas=(), vida=100, vel=1, perc=0, efeitos=NEUTRO, carma=None):
    return Lutador(nome, vida, vel, perc, list(tecnicas), efeitos=efeitos, carma=carma)


def luta(j, r, seed=0, **kw):
    lt = Luta(j, r, BASICO, random.Random(seed), **kw)
    lt.abertura = False
    return lt


def carma_cheio():
    c = Carma(ConfigCarma(100, {}, 20, 6, 60, 3.0, ()))
    c.valor = 100
    return c


# ------------------------------------------------------------------ técnicas


def test_espiral_atravessa_o_bloqueio():
    espiral = Tecnica("espiral", "Espiral", "ataque", dano=13, perfura=True)
    j, r = lut("J", [espiral], vel=3), lut("R")
    r.bloqueio = 50
    assert luta(j, r).resolver(espiral).dano == 13 and r.bloqueio == 50


def test_corte_do_mundo_atravessa_tudo_e_espera_o_quarto_turno():
    corte = Tecnica("corte", "Corte", "maldita", dano=35, absoluto=True, inicia_em_recarga=3)
    j = lut("J", [corte], vel=3)
    r = lut("R", efeitos=Efeitos(esquiva=1.0))
    r.escudos, r.bloqueio = 2, 50
    lt = luta(j, r)
    assert corte not in lt.prontas(j)
    for _ in range(3):
        lt.resolver(BASICO)  # a esquiva leva o Golpe
        lt.turno_rival()
    assert corte in lt.prontas(j)
    assert lt.resolver(corte).dano == 35 and r.escudos == 2


def test_clarao_negro_as_vezes_sai_critico():
    clarao = Tecnica("clarao", "Clarão", "ataque", dano=8, critico=1.0)
    j, r = lut("J", [clarao], vel=3), lut("R")
    acao = luta(j, r).resolver(clarao)
    assert acao.critico and acao.dano == round(8 * CRITICO)


def test_primeiro_trovao_sempre_e_surpresa():
    trovao = Tecnica("trovao", "Trovão", "ataque", dano=6, sutileza=2, sempre_surpresa=True)
    j, r = lut("J", [trovao], vel=3), lut("R", perc=0)
    acao = luta(j, r).resolver(trovao)
    assert acao.surpresa and acao.dano == 9  # +50% de surpresa


def test_corrente_sela_a_acao_anunciada_do_rival():
    corrente = Tecnica("corrente", "Corrente", "ataque", dano=4, selar=2)
    j, r = lut("J", [corrente], vel=3), lut("R", [LANCA])
    lt = luta(j, r)
    lt.intencao_rival = LANCA
    acao = lt.resolver(corrente)
    assert acao.selou == "lanca" and r.recargas["lanca"] == 2
    assert lt.intencao_rival is not LANCA


def test_mao_curadora_cura_e_respeita_o_preco_da_cura():
    mao = Tecnica("mao", "Mão", "defesa", cura=10)
    j, r = lut("J", [mao], vel=3), lut("R")
    j.vida = 50
    assert luta(j, r).resolver(mao).curou == 10 and j.vida == 60
    j2 = lut("J", [mao], vel=3, efeitos=Efeitos(cura_mult=0.5))
    j2.vida = 50
    luta(j2, lut("R")).resolver(mao)
    assert j2.vida == 55


def test_esfera_dos_mil_cresce_com_a_dor():
    esfera = Tecnica("esfera", "Esfera", "maldita", dano=6, dano_por_dor=0.5)
    j, r = lut("J", [esfera], vel=3), lut("R", [LANCA])
    j.dor = 40
    assert luta(j, r).resolver(esfera).dano == 26
    com_teto = Tecnica("esfera", "Esfera", "maldita", dano=6, dano_por_dor=0.5, teto_dor=10)
    j2 = lut("J", [com_teto], vel=3)
    j2.dor = 40
    assert luta(j2, lut("R")).resolver(com_teto).dano == 16  # a dor rende no máximo +10


def test_lua_ilusoria_faz_o_rival_perder_o_turno():
    lua = Tecnica("lua", "Lua", "maldita", atordoar=1)
    j, r = lut("J", [lua], vel=3), lut("R", [LANCA])
    lt = luta(j, r)
    assert lt.resolver(lua).atordoou
    assert lt.intencao_rival is HESITAR
    acao = lt.turno_rival()
    assert acao.tecnica == "hesitar" and j.vida == 100 and r.pular == 0


# ------------------------------------------------------------------ Dons e Relíquias


def test_corpo_perfeito_golpe_duplo_sem_defesa():
    e = Efeitos(basico_golpes=1, basico_dano=2, proibir_tipos=frozenset({"defesa"}))
    j, r = lut("J", [GUARDA], vel=3, efeitos=e), lut("R")
    lt = luta(j, r)
    assert GUARDA not in lt.prontas(j)
    assert lt.resolver(BASICO).dano == 12  # (4 + 2) × 2


def test_regeneracao_e_sangria_a_cada_turno():
    j = lut("J", [DIRETO], vel=3, efeitos=Efeitos(regen=1, sangria=2))
    j.vida = 50
    luta(j, lut("R")).resolver(DIRETO)
    assert j.vida == 49


def test_lamina_adormecida_so_nas_tecnicas():
    e = Efeitos(dano_tecnicas_mult=1.5)
    j, r = lut("J", [DIRETO], vel=3, efeitos=e), lut("R")
    lt = luta(j, r)
    assert lt.resolver(DIRETO).dano == 15
    lt.vez = j
    assert lt.resolver(BASICO).dano == 4


@pytest.fixture
def ctx():
    return Contexto.padrao("dificil")


def _fatia(ctx, roda, fid):
    return next(f for f in ctx.rodas[roda].fatias if f.id == fid)


def _run(ctx, seed=1):
    e = nova_run(ctx, random.Random(seed))
    aplicar_arco(e, ctx, _fatia(ctx, "arco", "torneio_regular"))
    return e


def test_manto_de_peso_cresce_a_cada_tres_vitorias(ctx):
    e = _run(ctx)
    receber_reliquia(e, _fatia(ctx, "reliquias", "manto_de_peso"))
    antes = e.jogador.vida_max
    for esperado in (antes, antes, antes + 1, antes + 1):  # +1 a cada 3 vitórias
        lt = comecar_luta(e, ctx, random.Random(1))
        lt.rival.vida = 0
        encerrar_luta(e, ctx, lt)
        assert e.jogador.vida_max == esperado


def test_fruta_proibida_da_um_espaco(ctx):
    e = _run(ctx)
    receber_reliquia(e, _fatia(ctx, "reliquias", "fruta_proibida"))
    assert espacos(e, ctx) == ctx.combate["espacos"] + 1
    e.jogador.tecnicas = e.jogador.tecnicas[:2]
    for fid in ("golpe_direto", "investida", "clones_de_sombra", "presa_da_lua"):
        receber_tecnica(e, ctx, _fatia(ctx, "tecnicas", fid))
    assert len(e.jogador.tecnicas) == 5


def test_ovo_do_eclipse_desperta_sem_carma_e_cobra_o_dom(ctx):
    e = _run(ctx)
    aplicar_dom(e, ctx, _fatia(ctx, "destino", "corpo_resistente"))
    receber_reliquia(e, _fatia(ctx, "reliquias", "ovo_do_eclipse"))
    e.mesa.carma.valor = 0
    lt = comecar_luta(e, replace(ctx, elenco=None), random.Random(2))  # o rival anônimo
    e.jogador.vida, e.jogador.bloqueio = 1, 0  # sem a defesa que a Linhagem sorteada desse
    lt.vez = lt.rival
    lt.intencao_rival = ctx.basico
    acao = lt.turno_rival()
    assert acao.despertou and e.jogador.vivo
    assert e.dom is None and e.despertares == 1
    assert not lt.pode_eclipse()  # uma vez por run


# ------------------------------------------------------------------ Despertares


def tipo(**despertar) -> Fatia:
    return Fatia("x", "Tipo", "divino", "texto", "覚", despertar=despertar)


def _desperta(despertar, tecnicas=(DIRETO,), rival=()):
    j = lut("J", tecnicas, vel=3, carma=carma_cheio())
    r = lut("R", rival, vida=999)
    lt = luta(j, r, ao_despertar=lambda: tipo(**despertar))
    lt.despertar()
    return lt, j, r


def test_liberacao_final_evolui_e_volta_no_fim_da_luta():
    lt, j, _ = _desperta({"evoluir": True})
    liberada = j.tecnicas[0]
    assert liberada.nivel == 2 and lt.resolver(liberada).dano == 13
    lt.encerrar()
    assert j.tecnicas[0] is DIRETO


def test_instinto_puro_esquiva_e_devolve():
    lt, j, r = _desperta({"instinto": 3}, rival=(LANCA,))
    lt.vez, lt.intencao_rival = r, LANCA
    lt.rng = random.Random(0)
    lt.rng.random = lambda: 0.0  # a esquiva sempre sai
    acao = lt.turno_rival()
    assert acao.instintos == 1 and acao.dano == 0 and r.vida == 999 - 4
    assert j.instinto == 2


def test_modo_eremita_cura_e_fortalece_a_luta():
    j = lut("J", [DIRETO], vel=3, carma=carma_cheio())
    j.vida = 20
    lt = luta(j, lut("R", vida=999), ao_despertar=lambda: tipo(cura_frac=0.5, percepcao=3, dano=3))
    lt.despertar()
    assert j.vida == 70 and lt.percepcao_contra(j) == 3
    assert lt.resolver(DIRETO).dano == 13


def test_marca_do_cacador_dano_agora_e_vida_para_sempre():
    lt, j, _ = _desperta({"dano_mult": 1.5, "perde_vida_max": 0.1})
    assert j.vida_max == 90 and lt.resolver(DIRETO).dano == 15
    j.nova_luta()
    assert j.dano_mult == 1.0 and j.vida_max == 90


# ------------------------------------------------------------------ origens


def test_toda_habilidade_tem_a_sua_origem(ctx):
    for roda in ctx.rodas.values():
        for f in roda.fatias:
            assert " · " in f.origem, f"{f.id} sem origem"


def test_chefes_e_aliados_tem_a_sua_origem_e_o_seu_kanji(ctx):
    from karmabound.aliados import carregar_aliados
    from karmabound.rodas import carregar_mecanicas

    for f in ctx.chefes:
        assert " · " in f.origem and f.kanji, f"{f.id} sem origem/kanji"
    for m in carregar_mecanicas().values():
        assert m["kanji"]
    for a in carregar_aliados():
        assert " · " in a.origem and a.kanji, f"{a.id} sem origem/kanji"


def test_as_rodas_tem_as_habilidades_novas(ctx):
    contagem = {r.id: len(r.fatias) for r in ctx.rodas.values()}
    assert contagem == {
        "linhagem": 57,
        "destino": 72,
        "tecnicas": 202,
        "arco": 34,
        "reliquias": 65,
        "despertar": 46,
    }


def test_a_fonte_de_pincel_tem_todo_caractere_do_jogo():
    """Yuji Syuku não tem mácron (ō, ū) nem setas como ↳: viram um quadrado na tela."""
    import ast
    import json
    from pathlib import Path

    import pygame

    raiz = Path(__file__).resolve().parent.parent
    pygame.font.init()
    fonte = pygame.font.Font(str(raiz / "assets" / "fonts" / "YujiSyuku-Regular.ttf"), 20)

    def desenho(c):
        return pygame.image.tobytes(fonte.render(c, True, (255, 255, 255)), "RGBA")

    ausente = desenho("")
    texto = "".join(
        json.dumps(
            json.loads((raiz / "karmabound" / "data" / nome).read_text(encoding="utf-8")),
            ensure_ascii=False,
        )
        for nome in (
            "rodas.json",
            "treinos.json",
            "caminho.json",
            "fusoes.json",
            "ressonancias.json",
            "ascensao.json",
            "chefes.json",
            "aliados.json",
        )
    )
    for modulo in (
        "tela_luta",
        "tela_roleta",
        "tela_menus",
        "tela_grimorio",
        "tela_pausa",
        "tela_cronica",
        "tela_caminho",
        "game",
        "cronica",
        "dicas",
        "vfx",
        "arenas",
    ):
        arvore = ast.parse((raiz / "karmabound" / f"{modulo}.py").read_text(encoding="utf-8"))
        docstrings = {
            id(n.value) for n in ast.walk(arvore) if isinstance(n, ast.Expr)
        }  # docstrings não vão para a tela
        texto += "".join(
            n.value
            for n in ast.walk(arvore)
            if isinstance(n, ast.Constant) and isinstance(n.value, str) and id(n) not in docstrings
        )
    faltam = sorted({c for c in texto if ord(c) > 127 and desenho(c) == ausente})
    assert not faltam, f"a fonte não desenha: {faltam}"


def test_toda_tecnica_tem_efeito_proprio_e_todo_arco_uma_arena(ctx):
    from karmabound import vfx
    from karmabound.arenas import ARENAS

    tecnicas = [f.id for f in ctx.rodas["tecnicas"].fatias if f.combate]
    tecnicas += [f.id for f in ctx.rodas["destino"].fatias if f.tecnica]
    tecnicas += [f.id for f in ctx.rodas["linhagem"].fatias if f.tecnica]
    assert set(tecnicas) <= set(vfx.POR_HABILIDADE), set(tecnicas) - set(vfx.POR_HABILIDADE)
    assert all(n in vfx.EFEITOS for n in vfx.POR_HABILIDADE.values())
    assert {f.id for f in ctx.rodas["despertar"].fatias} == set(vfx.AURAS)
    from karmabound.arenas import _par

    assert set(ARENAS) <= {f.id for f in ctx.rodas["arco"].fatias}
    assert all(_par(f.id) is not None for f in ctx.rodas["arco"].fatias)  # os novos: por dado


def test_os_efeitos_desenham_em_qualquer_ponto_da_animacao():
    from ouroboros.interfaces.null.null_renderer import NullRenderer

    from karmabound import vfx
    from karmabound.arenas import ARENAS, desenhar_arena

    r = NullRenderer()
    for nome in vfx.EFEITOS:
        for k in (0.0, 0.3, 0.6, 0.99):
            vfx.desenhar(r, nome, (480, 220), (150, 547), k, 1.7, forte=True)
    for aura in vfx.AURAS:
        vfx.aura(r, aura, 150, 547, 0.5, 2.0)
    for arco in ARENAS:
        desenhar_arena(r, arco, 3.3)


def test_fera_interior_acerta_uma_vez_a_mais():
    lt, j, _ = _desperta({"fera": 2})
    assert lt.resolver(DIRETO).dano == 20  # 10 × 2 golpes


def test_vazio_infinito_o_turno_do_rival_nao_fere():
    lt, j, r = _desperta({"intocavel": 1, "percepcao": 5}, rival=(LANCA,))
    lt.vez, lt.intencao_rival = r, LANCA
    assert lt.turno_rival().dano == 0 and j.intocavel == 0
    assert lt.percepcao_contra(j) >= 5


def test_dragao_negro_fere_na_hora():
    lt, _, r = _desperta({"golpe_imediato": 40})
    assert r.vida == 999 - 40


def test_retorno_pela_morte_volta_a_vida_do_comeco():
    j = lut("J", [DIRETO], vel=3, carma=carma_cheio())
    j.vida = 80
    lt = luta(j, lut("R", vida=999), ao_despertar=lambda: tipo(retorno=True))
    j.vida = 15
    lt.despertar()
    assert j.vida == 80


def test_dragao_negro_pode_encerrar_a_luta_no_despertar(ctx):
    """O piloto automático não pode agir numa luta que o Despertar já encerrou."""
    import karmabound.run as run_mod

    e = _run(ctx)
    lt = comecar_luta(e, ctx, random.Random(3))
    dragao = next(f for f in ctx.rodas["despertar"].fatias if f.id == "dragao_negro")
    lt.ao_despertar = lambda: dragao
    lt.rival.vida = 10
    e.mesa.carma.valor = e.mesa.carma.config.maximo
    lt.despertar()
    assert lt.acabou and lt.vencedor is e.jogador
    assert run_mod.encerrar_luta(e, ctx, lt)


def test_fusoes_ressonancias_e_ascensao_tem_kanji_na_fonte_e_homenagem(ctx):
    """O kanji de cada fusão, ressonância e degrau da Ascensão existe na fonte; toda técnica
    de fusão diz de onde vem, e toda ressonância é de um anime das rodas."""
    from pathlib import Path

    import pygame

    from karmabound.ascensao import carregar_ascensao
    from karmabound.fusoes import tecnicas_de_fusao
    from karmabound.ressonancia import carregar_ressonancias
    from karmabound.rodas import anime_de

    raiz = Path(__file__).resolve().parent.parent
    pygame.font.init()
    fonte = pygame.font.Font(str(raiz / "assets" / "fonts" / "YujiSyuku-Regular.ttf"), 20)
    tabela = carregar_ressonancias()
    kanji = "".join(f.kanji for f in tecnicas_de_fusao().values())
    kanji += "".join(b.kanji for b in [*tabela.animes.values(), tabela.generico])
    kanji += "".join(n.kanji for n in carregar_ascensao())
    faltando = [k for k, m in zip(kanji, fonte.metrics(kanji), strict=True) if m is None]
    assert not faltando
    for f in tecnicas_de_fusao().values():
        assert " · " in f.origem and anime_de(f.origem), f"{f.id} sem origem"
    animes = {anime_de(f.origem) for f in ctx.rodas["tecnicas"].fatias}
    assert set(tabela.animes) <= animes
