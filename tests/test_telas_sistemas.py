"""As telas dos sistemas novos fora da luta: o anúncio de fusão, o aliado que chega, os
selos de combo (融 fusão, 共 Ressonância), o build na pausa, o mapa do caminho, o Grimório
das fusões e a Ascensão ligada no Fluxo (pasta temporária, ver conftest)."""

import os

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

import pytest  # noqa: E402

from karmabound.dicas import DICAS  # noqa: E402
from karmabound.game import build_game  # noqa: E402
from karmabound.grimorio import Grimorio, perda, pista  # noqa: E402
from karmabound.jornada import Jornada  # noqa: E402
from karmabound.legado import Legado  # noqa: E402
from karmabound.mesa import Giro  # noqa: E402
from karmabound.run import aplicar_dom, atualizar_efeitos, criar_tecnica  # noqa: E402
from karmabound.tela_caminho import CaminhoScene  # noqa: E402
from karmabound.tela_grimorio import ORDEM_RODAS, GrimorioScene  # noqa: E402
from karmabound.tela_menus import (  # noqa: E402
    AliadoScene,
    FimScene,
    FusaoScene,
    SubstituirScene,
    TituloScene,
    TreinoScene,
    texto_da_perda,
    texto_da_pista,
)
from karmabound.tela_pausa import PausaScene  # noqa: E402
from karmabound.tela_roleta import RoletaScene  # noqa: E402

PASSO = 1 / 30


class Entrada:
    def __init__(self):
        self.apertadas: set[str] = set()

    def is_action_pressed(self, acao: str) -> bool:
        return acao in self.apertadas


class Gravador:
    """Um renderer que só guarda o texto desenhado (o resto não faz nada)."""

    def __init__(self):
        self.textos: list[str] = []

    def draw_text(self, x, y, text, size, rgba, anchor="topleft", font_id=None):
        self.textos.append(text)

    def __getattr__(self, nome):
        return lambda *a, **k: None

    def tem(self, pedaco: str) -> bool:
        return any(pedaco in t for t in self.textos)


@pytest.fixture
def loop():
    lp = build_game(seed=1)
    lp._input_provider = Entrada()
    yield lp
    lp.renderer.shutdown()


def apertar(loop, *teclas):
    """Um quadro com `teclas` apertadas na tela do topo, e o desenho dela."""
    cena = loop.current_scene
    loop.input_provider.apertadas = set(teclas)
    cena.update(None, PASSO)
    loop.input_provider.apertadas = set()
    loop.renderer.begin_frame()
    loop.current_scene.render(None, loop.renderer)


def mao_de_naruto(seed=3) -> Jornada:
    """Golpe, Foice de Vento, Investida e Clones de Sombra: três de Naruto (Ressonância 1)
    e a Foice, peça da Shuriken Espiral (falta a Espiral Concentrada)."""
    j = Jornada.nova("dificil", seed=seed)
    j.grimorio = Grimorio()
    tec = j.ctx.tecnicas
    jg = j.jogador
    ids = ("golpe_de_vento", "investida", "clones_de_sombra")
    jg.tecnicas[:] = [jg.tecnicas[0]] + [criar_tecnica(j.ctx, tec[i]) for i in ids]
    atualizar_efeitos(j.estado)
    return j


# ------------------------------------------------------------------ fusão e aliado no Fluxo


def test_a_fusao_e_anunciada_antes_da_proxima_tela(loop, monkeypatch):
    from tests.test_fusoes import _ate_a_luta, _despertar_vazio

    fluxo = loop.fluxo
    j = _ate_a_luta()
    j.grimorio = fluxo.grimorio
    fluxo.jornada = j
    _despertar_vazio(j, monkeypatch)
    j.estado.mesa.__dict__.pop("girar")  # o giro de teste não vai para o save
    fluxo.passo()
    cena = loop.current_scene
    assert isinstance(cena, FusaoScene)
    assert [f.id for f in cena.fatias] == ["vazio_purpura"]
    assert not j.fusoes_novas  # a tela anunciou: a lista esvaziou
    assert fluxo.grimorio.conhece("fusoes", "roxo")
    nomes = [nome for _, _, nome in cena.pecas[0]]
    assert nomes == ["Olhos que Tudo Veem", "Vazio Infinito"]
    apertar(loop, "confirmar")  # o primeiro Enter só mostra tudo
    assert loop.current_scene is cena and cena.terminou
    apertar(loop, "confirmar")
    assert isinstance(loop.current_scene, TreinoScene)  # e a run segue pela fase


def test_a_fusao_sem_espaco_anuncia_e_depois_abre_a_troca(loop, monkeypatch):
    from karmabound.run import espacos
    from tests.test_fusoes import _ate_a_luta, _despertar_vazio

    fluxo = loop.fluxo
    j = _ate_a_luta()
    j.grimorio = fluxo.grimorio
    fluxo.jornada = j
    investida = criar_tecnica(j.ctx, j.ctx.tecnicas["investida"])
    from dataclasses import replace

    while len(j.jogador.tecnicas) < espacos(j.estado, j.ctx):
        j.jogador.tecnicas.append(replace(investida, id=f"investida{len(j.jogador.tecnicas)}"))
    _despertar_vazio(j, monkeypatch)
    j.estado.mesa.__dict__.pop("girar")  # o giro de teste não vai para o save
    assert j.fase == "substituir"
    fluxo.passo()
    assert isinstance(loop.current_scene, FusaoScene)
    apertar(loop, "confirmar")
    apertar(loop, "confirmar")
    troca = loop.current_scene
    assert isinstance(troca, SubstituirScene) and troca.fusao
    loop.renderer.begin_frame()
    troca.render(None, loop.renderer)


def test_o_aliado_que_chega_e_anunciado_uma_vez(loop):
    fluxo = loop.fluxo
    fluxo.comecar("acessivel", seed=4)
    j = fluxo.jornada
    j.estado.aliado, j.estado.aliado_nivel = "faro", 1
    fluxo.passo()
    cena = loop.current_scene
    assert isinstance(cena, AliadoScene) and cena.aliado.id == "faro"
    assert fluxo.grimorio.conhece("aliados", "faro")
    gravador = Gravador()
    cena.assentar()
    cena.render(None, gravador)
    assert gravador.tem("Faro") and gravador.tem("nível 1")
    apertar(loop, "confirmar")
    apertar(loop, "confirmar")
    assert isinstance(loop.current_scene, RoletaScene)  # a fase da Linhagem
    fluxo.passo()
    assert isinstance(loop.current_scene, RoletaScene)  # sem anunciar de novo


# ------------------------------------------------------------------ pistas de combo


def test_a_pista_marca_a_peca_que_falta_e_a_ressonancia_que_sobe():
    j = mao_de_naruto()
    fusoes = j.ctx.fusoes
    p = pista(j.estado, "espiral_concentrada", fusoes)
    assert p.fusoes[0].id == "shuriken" and p.completa
    assert p.anime == "Naruto" and p.nivel == 2
    assert texto_da_pista(p, j.grimorio).startswith("融 completa uma fusão")
    j.grimorio.marcar("fusoes", ["shuriken"])
    assert "Shuriken Espiral" in texto_da_pista(p, j.grimorio, 27)
    assert len(texto_da_pista(p, j.grimorio, 27)) <= 27
    assert not pista(j.estado, "lamina_de_sangue", fusoes)  # Jujutsu: nada
    assert not pista(j.estado, "investida", fusoes)  # já está na mão


def test_a_troca_avisa_o_que_se_desfaz():
    j = mao_de_naruto()
    fusoes = j.ctx.fusoes
    sai = perda(j.estado, "investida", "lamina_de_sangue", fusoes)
    assert sai.ressonancias == (("Naruto", 1, 0),) and not sai.fusoes
    assert texto_da_perda(sai) == "desfaz 共 Naruto"
    foice = perda(j.estado, "golpe_de_vento", "lamina_de_sangue", fusoes)
    assert [f.id for f in foice.fusoes] == ["shuriken"] and "融" in texto_da_perda(foice)
    assert not perda(j.estado, "investida", "mil_clones", fusoes)  # Naruto por Naruto


def test_a_roleta_e_a_troca_mostram_os_selos(loop):
    j = mao_de_naruto()
    tec = j.ctx.tecnicas
    giro = Giro(j.ctx.rodas["tecnicas"], [tec["espiral_concentrada"], tec["lamina_de_sangue"]])
    entrada = Entrada()
    roleta = RoletaScene(
        j.estado.mesa, entrada, lambda: None, "tecnicas", lambda: giro, lambda i: None, jornada=j
    )
    roleta._comecar_giro()
    roleta.apressar = True
    for _ in range(300):
        roleta.update(None, PASSO)
        if roleta.estado == "escolhendo":
            break
    assert roleta.estado == "escolhendo"
    selos = roleta.pistas()
    assert selos[0].startswith("融") and "共" in selos[0] and selos[1] == ""
    gravador = Gravador()
    roleta.assentar()
    roleta.render(None, gravador)
    assert gravador.tem(selos[0])
    j.pendente, j.fase = tec["lamina_de_sangue"], "substituir"
    troca = SubstituirScene(j, entrada, lambda: None, lambda: None)
    troca.assentar()
    gravador = Gravador()
    troca.render(None, gravador)
    assert gravador.tem("desfaz 共 Naruto") and gravador.tem("peça de 融")


# ------------------------------------------------------------------ pausa, caminho, Grimório


def test_a_pausa_mostra_o_build(loop):
    j = mao_de_naruto()
    j.estado.aliado, j.estado.aliado_nivel = "pequeno_doutor", 2
    j.estado.fusoes_nascidas.append("roxo")
    pausa = PausaScene(
        TituloScene(Entrada(), lambda *a: None, lambda: None),
        j,
        Entrada(),
        lambda: None,
        lambda: None,
        None,
    )
    gravador = Gravador()
    pausa.relogio = 1.0
    pausa.render(None, gravador)
    assert gravador.tem("Vontade do Fogo") and gravador.tem("Pequeno Doutor · nível 2")
    assert gravador.tem("Vazio Púrpura") and gravador.tem("falta 1 peça para uma fusão")
    loop.renderer.begin_frame()
    pausa.render(None, loop.renderer)


def test_o_caminho_mostra_o_passo_seguinte(loop):
    j = Jornada.nova("acessivel", seed=7)
    j.girar_linhagem()
    j.girar_destino()
    j.girar_arco()
    assert j.fase == "caminho" and j.proximas_portas
    cena = CaminhoScene(j, Entrada(), lambda: None, lambda: None)
    gravador = Gravador()
    cena.render(None, gravador)
    assert gravador.tem("depois")
    for p in j.proximas_portas:
        assert gravador.tem(p.nome)
    j.estado.proximas_portas = ()  # o próximo é o chefe
    gravador = Gravador()
    cena.render(None, gravador)
    assert gravador.tem("o chefe")
    elite = j.ctx.caminho.porta("elite")
    j.oferta_caminho = (j.oferta_caminho[0], elite)
    cena.cursor = 1
    gravador = Gravador()
    cena.render(None, gravador)
    assert gravador.tem("sorteado ao entrar")
    loop.renderer.begin_frame()
    cena.render(None, loop.renderer)


def test_o_grimorio_tem_as_fusoes_aliados_e_afixos(loop, tmp_path):
    from karmabound.run import Contexto

    g = Grimorio(tmp_path / "g.json")
    g.marcar("fusoes", ["roxo"])
    g.marcar("afixos", ["vampirico", "vampirico"])
    de_novo = Grimorio(tmp_path / "g.json")  # salvo em disco
    assert de_novo.conhece("fusoes", "roxo") and de_novo.extras["afixos"] == {"vampirico"}
    tela = GrimorioScene(de_novo, Entrada(), lambda: None, lambda: None, ctx=Contexto.padrao())
    tela.i_roda = ORDEM_RODAS.index("fusoes")
    roxo = next(e for e in tela.lista if e.id == "roxo")
    assert tela._visto(roxo)
    assert not any(tela._visto(e) for e in tela.lista if e.id != "roxo")
    for aba in ("fusoes", "aliados", "afixos"):
        tela.i_roda = ORDEM_RODAS.index(aba)
        for i in range(len(tela.lista)):
            tela.cursor = i
            loop.renderer.begin_frame()
            tela.render(None, loop.renderer)
    tela.i_roda, tela.cursor = ORDEM_RODAS.index("fusoes"), 0
    gravador = Gravador()
    tela.render(None, gravador)
    assert gravador.tem("Olhos que Tudo Veem + Vazio Infinito")


# ------------------------------------------------------------------ Ascensão


def test_o_titulo_escolhe_o_degrau_da_ascensao():
    escolhas = []
    entrada = Entrada()
    tela = TituloScene(
        entrada, lambda m, **k: escolhas.append((m, k)), lambda: None, ascensoes={"dificil": 3}
    )
    tela.cursor = [x[0] for x in tela.itens].index("dificil")
    assert "昇 3" in tela.itens[tela.cursor][2]

    def quadro(*teclas):
        entrada.apertadas = set(teclas)
        tela.update(None, PASSO)
        entrada.apertadas = set()

    quadro("confirmar")
    assert tela.modo_asc == "dificil" and tela.nivel_asc == 3 and not escolhas
    quadro("direita")
    assert tela.nivel_asc == 3  # o máximo aberto
    quadro("esquerda")
    quadro("esquerda")
    gravador = Gravador()
    tela.render(None, gravador)
    assert gravador.tem("Ascensão 1") and gravador.tem("1. Sangue Novo")
    quadro("confirmar")
    assert escolhas == [("dificil", {"ascensao": 1})]
    # sem Ascensão aberta, a dificuldade começa direto, como antes
    tela.cursor = [x[0] for x in tela.itens].index("equilibrado")
    quadro("confirmar")
    assert escolhas[-1] == ("equilibrado", {})


def test_a_ascensao_passa_ao_comecar_e_abre_a_proxima_ao_vencer(loop):
    fluxo = loop.fluxo
    fluxo.legado.ascensoes["dificil"] = 2
    fluxo.comecar("dificil", seed=3, ascensao=2)
    j = fluxo.jornada
    assert j.ascensao == 2 and j.ctx.ascensao == 2
    j.fase = "vitoria"
    j.estado.lutas_vencidas = 12
    fluxo.passo()
    fim = loop.current_scene
    assert isinstance(fim, FimScene)
    assert fim.fechamento.ascensao_aberta == 3
    assert any("Ascensão 3 aberta" in texto for texto, _ in fim.linhas_legado())
    assert "昇2" in fim.linhas()[0]
    assert Legado.padrao().ascensao_maxima("dificil") == 3  # ficou no disco
    fluxo.titulo()
    assert loop.current_scene.ascensoes == {"dificil": 3}


def test_a_derrota_nao_abre_ascensao_e_a_semente_do_dia_joga_na_zero(loop):
    fluxo = loop.fluxo
    fluxo.comecar("equilibrado", seed=3, ascensao=1)
    fluxo.jornada.fase = "derrota"
    fluxo.passo()
    assert loop.current_scene.fechamento.ascensao_aberta == 0
    fluxo.comecar("dificil", seed=20260101, diaria="2026-01-01", ascensao=4)
    assert fluxo.jornada.ascensao == 0
    fluxo.semente_do_dia()
    assert fluxo.jornada.ascensao == 0


# ------------------------------------------------------------------ dicas


def test_as_dicas_dos_sistemas_novos_existem():
    for dica in ("fusao", "ressonancia", "guarda", "afixo", "aliado", "mecanica", "ascensao"):
        kanji, titulo, texto = DICAS[dica]
        assert kanji and titulo and 60 < len(texto) < 400


def test_o_roxo_pelo_fluxo_desenha_cada_momento(loop):
    j = Jornada.nova("dificil", seed=11)
    j.grimorio = Grimorio()
    j.girar_linhagem()
    j.girar_destino()
    dons = {f.id: f for f in j.ctx.rodas["destino"].fatias}
    aplicar_dom(j.estado, j.ctx, dons["olhos_que_tudo_veem"])
    j.estado.despertares_ids.append("vazio_infinito")
    j.fusoes_novas.clear()
    j._fundir("treino")
    assert [f.id for f in j.fusoes_novas][-1] == "vazio_purpura"
    cena = FusaoScene(j, j.fusoes_novas[-1:], Entrada(), lambda: None, lambda: None)
    for t in (0.0, 0.3, 0.7, 1.0, 1.2, 1.5, 3.0):
        cena.t_seq = t
        loop.renderer.begin_frame()
        cena.render(None, loop.renderer)
