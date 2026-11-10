"""O movimento fora da luta: a transição de tinta do Fluxo, as cartas e os fades.

A transição desenha por cima (callback de UI do GameLoop) e nunca segura a entrada:
a tela nova está no topo desde o primeiro quadro.
"""

import os

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

import pytest  # noqa: E402

from karmabound import opcoes  # noqa: E402
from karmabound.game import build_game  # noqa: E402
from karmabound.tela_luta import LutaScene  # noqa: E402
from karmabound.tela_menus import FimScene, TituloScene, TreinoScene  # noqa: E402
from karmabound.tela_roleta import RoletaScene  # noqa: E402
from karmabound.transicoes import Cartas, Transicao, carimbo  # noqa: E402

PASSO = 1 / 60


class Entrada:
    def __init__(self):
        self.apertadas: set[str] = set()

    def is_action_pressed(self, acao: str) -> bool:
        return acao in self.apertadas


class Velha:
    """Uma tela que sai: conta quantas vezes foi desenhada e animada."""

    segurar_saida = 0.0

    def __init__(self):
        self.desenhos = 0
        self.animado = 0.0

    def render(self, world, r):
        self.desenhos += 1

    def animar(self, dt):
        self.animado += dt


class Quebrada(Velha):
    def render(self, world, r):
        raise RuntimeError("o estado já andou")


@pytest.fixture
def velocidade(monkeypatch):
    def pôr(v):
        monkeypatch.setattr(opcoes.OPCOES, "velocidade", v)

    pôr(1.0)
    return pôr


@pytest.fixture
def loop():
    lp = build_game(seed=4)
    yield lp
    lp.renderer.shutdown()


def _ate_acabar(tr: Transicao, dt=PASSO) -> float:
    t = 0.0
    while tr.ativa:
        tr.avancar(dt)
        t += dt
        assert t < 5, "a transição não termina"
    return t


# ------------------------------------------------------------------ a transição


def test_a_transicao_comeca_cobrindo_a_velha_e_termina(velocidade):
    tr = Transicao()
    velha = Velha()
    tr.comecar(velha)
    assert tr.ativa and tr.fase() == "fecha"
    tr.avancar(tr.fecha * 0.5)
    assert velha.animado > 0  # o carimbo da velha continua enquanto a tinta a cobre
    tr.avancar(tr.fecha)
    assert tr.fase() == "abre" and tr.velha is velha
    duracao = _ate_acabar(tr) + tr.fecha * 1.5
    assert not tr.ativa and tr.velha is None
    assert 0.3 <= duracao <= 0.55


def test_sem_tela_velha_comeca_ja_coberta_e_so_abre(velocidade):
    tr = Transicao()
    tr.comecar(None)
    assert tr.fase() == "abre"
    assert _ate_acabar(tr) <= tr.abre + PASSO


def test_entrar_na_luta_e_um_corte_mais_dramatico(velocidade):
    tr = Transicao()
    tr.comecar(Velha(), "corte")
    fases = []
    while tr.ativa:
        if tr.fase() not in fases:
            fases.append(tr.fase())
        tr.avancar(PASSO)
    assert fases == ["fecha", "cheio", "abre"]


def test_a_transicao_respeita_a_velocidade(velocidade):
    tr = Transicao()
    tr.comecar(Velha())
    normal = _ate_acabar(tr)
    velocidade(2.0)
    tr.comecar(Velha())
    rapida = _ate_acabar(tr)
    assert rapida == pytest.approx(normal / 2, abs=2 * PASSO)


def test_o_carimbo_da_velha_segura_a_transicao(velocidade):
    tr = Transicao()
    sem = Velha()
    tr.comecar(sem)
    t_sem = _ate_acabar(tr)
    com = Velha()
    com.segurar_saida = 0.14
    tr.comecar(com)
    assert tr.fase() == "segura"
    assert _ate_acabar(tr) == pytest.approx(t_sem + 0.14, abs=2 * PASSO)


def test_enter_encurta_mas_nao_o_enter_que_trocou_a_tela(velocidade, loop):
    agora = [0.0]
    entrada = Entrada()
    tr = Transicao(lambda: entrada, relogio=lambda: agora[0])
    r = loop.renderer
    tr.comecar(Velha())
    entrada.apertadas = {"confirmar"}  # o mesmo quadro que trocou a tela
    r.begin_frame()
    tr.quadro(r)
    assert tr.ativa
    entrada.apertadas = set()
    agora[0] += PASSO
    r.begin_frame()
    tr.quadro(r)
    assert tr.ativa
    entrada.apertadas = {"confirmar"}
    agora[0] += PASSO
    r.begin_frame()
    tr.quadro(r)
    assert not tr.ativa


def test_tela_velha_que_quebra_vira_tinta_inteira(velocidade, loop, monkeypatch):
    tr = Transicao()
    tr.comecar(Quebrada())
    loop.renderer.begin_frame()
    tr.desenhar(loop.renderer)  # não derruba o jogo
    assert tr.velha is None and tr.ativa
    monkeypatch.setattr(Transicao, "tolerante", False)
    tr.comecar(Quebrada())
    with pytest.raises(RuntimeError):
        tr.desenhar(loop.renderer)


# ------------------------------------------------------------------ pelo Fluxo


def test_o_fluxo_troca_a_tela_na_hora_e_a_nova_recebe_entrada(velocidade, loop):
    fluxo = loop.fluxo
    entrada = Entrada()
    loop._input_provider = entrada
    fluxo.titulo()
    titulo = loop.current_scene
    fluxo.comecar("dificil", seed=3)
    roleta = loop.current_scene
    assert isinstance(roleta, RoletaScene)  # a nova já está no topo
    assert fluxo.transicao.ativa and fluxo.transicao.velha is titulo
    assert fluxo.transicao.estilo == "tinta" and roleta.sem_revelar
    entrada.apertadas = {"girar"}  # no meio da tinta, a roleta já gira
    roleta.update(None, PASSO)
    assert roleta.estado in ("girando", "quebrando")


def test_entrar_na_luta_pelo_fluxo_e_corte(velocidade, loop):
    fluxo = loop.fluxo
    fluxo.comecar("acessivel", seed=5)
    j = fluxo.jornada
    j.girar_linhagem()
    j.girar_destino()
    j.girar_arco()
    while j.fase == "caminho":
        j.escolher_caminho([p.tipo for p in j.oferta_caminho].index("rival"))
    assert j.fase == "luta"
    fluxo.passo()
    assert isinstance(loop.current_scene, LutaScene)
    assert fluxo.transicao.estilo == "corte"


def test_uma_run_inteira_com_a_transicao_desenhando(monkeypatch):
    """Como test_fluxo, mas pelo tick do GameLoop: a transição desenha a tela velha (que
    já andou) em toda troca, sem tolerar erro."""
    from tests.test_fluxo import decidir

    monkeypatch.setattr(Transicao, "tolerante", False)
    loop = build_game(seed=2)
    entrada = Entrada()
    loop._input_provider = entrada
    agora = [0.0]
    loop.fluxo.transicao._relogio = lambda: agora[0]
    loop.fluxo.titulo()
    trocas = 0
    antes = None
    for _ in range(40_000):
        cena = loop.current_scene
        if cena is not antes:
            trocas += 1
            antes = cena
        if isinstance(cena, FimScene):
            break
        entrada.apertadas = decidir(cena)
        agora[0] += 1 / 30
        loop.tick_once(1 / 30)
        entrada.apertadas = set()
    else:
        pytest.fail(f"a run não terminou; parou em {type(loop.current_scene).__name__}")
    assert trocas > 5
    loop.renderer.shutdown()


# ------------------------------------------------------------------ as cartas


def test_cartas_entram_escalonadas_e_a_selecao_anda_com_easing(velocidade):
    c = Cartas()
    c.avancar(0.1, 0, 3)
    assert 0 < c.surgiu(0) and c.surgiu(0) > c.surgiu(1) > c.surgiu(2)
    c.avancar(2.0, 0, 3)
    assert c.assentou and c.foco_de(0) == pytest.approx(1.0, abs=0.01)
    c.avancar(PASSO, 1, 3)  # o cursor foi para a 2ª: o foco desliza, não salta
    assert 0 < c.foco_de(1) < 0.5 and 0.5 < c.foco_de(0) < 1


def test_o_carimbo_cresce_e_assenta_e_as_outras_somem(velocidade, loop):
    c = Cartas()
    c.avancar(2.0, 1, 3)
    c.escolher(1)
    c.avancar(Cartas.CARIMBO * 0.3, 1, 3)
    pico = c.camada(loop.renderer, 1, (0, 0)).s
    outra = c.camada(loop.renderer, 0, (0, 0)).opac
    c.avancar(Cartas.CARIMBO, 1, 3)
    assentou = c.camada(loop.renderer, 1, (0, 0)).s
    assert pico > assentou > 1.0
    assert c.camada(loop.renderer, 0, (0, 0)).opac < outra
    assert carimbo(0) == 1.0 and max(carimbo(x / 20) for x in range(21)) <= 1.11


def test_as_cartas_respeitam_a_velocidade(velocidade):
    lenta = Cartas()
    lenta.avancar(0.1, 0, 3)
    velocidade(2.0)
    rapida = Cartas()
    rapida.avancar(0.1, 0, 3)
    assert rapida.t == pytest.approx(2 * lenta.t)


def test_o_treino_aceita_a_escolha_durante_a_entrada_e_sai_carimbando(velocidade):
    from tests.test_ritmo import _vencer_uma_luta

    j = _vencer_uma_luta()
    oferta = list(j.oferta_treino)
    fim = []
    entrada = Entrada()
    tela = TreinoScene(j, entrada, lambda: fim.append(1), lambda: None)
    entrada.apertadas = {"escolher_2"}  # no primeiro quadro, com as cartas ainda subindo
    tela.update(None, PASSO)
    assert fim and tela.cartas.escolhida == 1 and tela.segurar_saida > 0
    assert tela.fixo == oferta  # a Jornada limpou a oferta; a tela sai mostrando as cartas
    tela.animar(0.1)


# ------------------------------------------------------------------ título, fim e painéis


def test_o_titulo_desliza_a_selecao():
    entrada = Entrada()
    tela = TituloScene(entrada, lambda *a, **k: None, lambda: None)
    tela.preparar()  # o preparo tem várias linhas; o cursor fica em Começar, a última
    tela.assentar()
    antes = tela.y_sel
    entrada.apertadas = {"cima"}
    tela.update(None, PASSO)
    entrada.apertadas = set()
    tela.update(None, PASSO)
    passo = tela._layout()[1]
    assert antes - passo < tela.y_sel < antes  # a caminho, não no destino


def test_o_fim_conta_e_o_primeiro_enter_so_pula_a_sequencia(velocidade, loop):
    fluxo = loop.fluxo
    fluxo.comecar("acessivel", seed=6)
    j = fluxo.jornada
    j.fase = "derrota"
    j.estado.lutas_vencidas = 7
    fluxo.passo()
    fim = loop.current_scene
    assert isinstance(fim, FimScene)
    entrada = Entrada()
    fim.entrada = entrada
    fim.update(None, 0.7)
    assert 0 < fim.contou < 7  # a contagem das lutas no meio
    assert "lutas vencidas" in fim.linhas(fim.contou)[0]
    entrada.apertadas = {"confirmar"}
    fim.update(None, PASSO)
    assert fim.terminou and loop.current_scene is fim
    fim.update(None, PASSO)
    assert fim.contou == 7
    assert isinstance(loop.current_scene, TituloScene)


def test_a_pausa_entra_em_fade(velocidade, loop):
    fluxo = loop.fluxo
    fluxo.comecar("dificil")
    fluxo.pausar()
    pausa = loop.current_scene
    assert pausa._surgir() == 0.0
    pausa.update(None, pausa.FADE / 2)
    assert 0 < pausa._surgir() < 1
    loop.renderer.begin_frame()
    pausa.render(None, loop.renderer)
    pausa.update(None, pausa.FADE)
    assert pausa._surgir() == 1.0


def test_enter_apressa_o_giro_da_roleta(velocidade):
    from karmabound.jornada import Jornada

    j = Jornada.nova("dificil", seed=6)
    entrada = Entrada()
    tela = RoletaScene(j.estado.mesa, entrada, lambda: None, "linhagem", j.girar_linhagem, None)
    entrada.apertadas = {"girar"}
    tela.update(None, PASSO)
    entrada.apertadas = {"confirmar"}
    tela.update(None, PASSO)
    entrada.apertadas = set()
    for _ in range(5):
        tela.update(None, PASSO)
    assert tela.estado == "resultado"
