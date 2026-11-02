"""Polimento: opções salvas, volume, dicas, pausa e quebrar um voto pela tela."""

import os

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

import pytest  # noqa: E402

from karmabound import opcoes, som  # noqa: E402
from karmabound.jornada import Jornada  # noqa: E402
from karmabound.opcoes import Opcoes  # noqa: E402
from karmabound.run import aplicar_voto  # noqa: E402
from karmabound.votos import Voto  # noqa: E402


class Entrada:
    def __init__(self):
        self.apertadas = set()

    def is_action_pressed(self, acao):
        return acao in self.apertadas


def aperta(cena, entrada, *teclas):
    entrada.apertadas = set(teclas)
    cena.update(None, 1 / 30)
    entrada.apertadas = set()


# ------------------------------------------------------------------ opções


def test_opcoes_salvam_e_voltam(tmp_path):
    o = Opcoes.carregar(tmp_path / "opcoes.json")
    o.volume_musica, o.mudo, o.velocidade = 3, True, 1.5
    o.salvar()
    de_novo = Opcoes.carregar(tmp_path / "opcoes.json")
    assert (de_novo.volume_musica, de_novo.mudo, de_novo.velocidade) == (3, True, 1.5)


def test_arquivo_estragado_e_velocidade_invalida_viram_padrao(tmp_path):
    caminho = tmp_path / "opcoes.json"
    caminho.write_text('{"velocidade": 7}', encoding="utf-8")
    assert Opcoes.carregar(caminho).velocidade == 1.0
    caminho.write_text("{ nada", encoding="utf-8")
    assert Opcoes.carregar(caminho).volume_musica == 7


def test_dica_aparece_uma_vez_e_o_ambiente_desliga(tmp_path, monkeypatch):
    monkeypatch.setenv("KARMABOUND_DICAS", "1")
    o = Opcoes.carregar(tmp_path / "opcoes.json")
    assert o.mostrar_dica("luta") and not o.mostrar_dica("luta")
    assert "luta" in Opcoes.carregar(tmp_path / "opcoes.json").dicas_vistas
    monkeypatch.setenv("KARMABOUND_DICAS", "0")
    assert not Opcoes.carregar(tmp_path / "opcoes.json").mostrar_dica("altar")


def test_volume_e_silenciar(monkeypatch):
    class Audio:
        def __init__(self):
            self.tocados, self.volume = [], None

        def load_sound(self, n, c):
            pass

        def load_track(self, n, c):
            pass

        def play_one_shot(self, n, volume=1.0):
            self.tocados.append(volume)

        def set_track_volume(self, v):
            self.volume = v

    monkeypatch.setattr(opcoes.OPCOES, "volume_musica", 5)
    monkeypatch.setattr(opcoes.OPCOES, "volume_efeitos", 10)
    monkeypatch.setattr(opcoes.OPCOES, "mudo", False)
    s, audio = som._Som(), Audio()
    s.configurar(audio)
    assert audio.volume == pytest.approx(0.5)
    s.tocar("corte")
    assert audio.tocados == [pytest.approx(1.0)]
    monkeypatch.setattr(opcoes.OPCOES, "mudo", True)
    s.aplicar_volume()
    s.tocar("corte")
    assert audio.volume == 0.0 and len(audio.tocados) == 1


# ------------------------------------------------------------------ quebrar um voto


def _com_voto(seed=2, de_quebra=False):
    j = Jornada.nova("dificil", seed=seed)
    j.girar_destino()
    j.girar_arco()
    cat = j.ctx.catalogo
    voto = Voto([cat.restricoes["sem_descanso"]], [cat.ganhos["forca"]], "run")
    aplicar_voto(j.estado, j.ctx, voto)
    if de_quebra:
        voto.de_quebra = True
    return j, voto


def test_quebrar_um_voto_cobra_e_jura_o_de_quebra():
    j, voto = _com_voto()
    j.carma.valor = 50
    vida = j.jogador.vida
    dano = j.jogador.efeitos.bonus_dano
    forca = j.ctx.catalogo.ganhos["forca"].efeito.bonus_dano
    assert j.quebrar_voto(voto, ["corpo_ofertado"])
    ativos = j.estado.votos.ativos
    assert voto not in ativos and len(ativos) == 1 and ativos[0].de_quebra
    assert ativos[0].ganhos == [] and j.carma.valor == 0
    assert j.jogador.vida < vida
    assert j.jogador.efeitos.bonus_dano == dano - forca  # a Força se foi


def test_quebrar_um_voto_de_quebra_encerra_a_run():
    j, voto = _com_voto(de_quebra=True)
    assert not j.quebrar_voto(voto, [])
    assert j.fase == "derrota" and j.estado.derrotado


# ------------------------------------------------------------------ telas


@pytest.fixture
def fluxo():
    from karmabound.game import build_game

    loop = build_game(seed=4)
    f = loop.fluxo
    f.comecar("dificil")
    yield f
    loop.renderer.shutdown()


def test_pausa_abre_e_fecha_por_cima_da_tela(fluxo):
    from karmabound.tela_pausa import PausaScene

    baixo = fluxo.loop.current_scene
    fluxo.pausar()
    pausa = fluxo.loop.current_scene
    assert isinstance(pausa, PausaScene) and pausa.baixo is baixo
    e = Entrada()
    pausa.entrada = e
    fluxo.loop.renderer.begin_frame()
    pausa.render(None, fluxo.loop.renderer)  # desenha a de baixo e o painel
    aperta(pausa, e, "cancelar")
    assert fluxo.loop.current_scene is baixo


def test_opcoes_mudam_na_hora_e_salvam(fluxo, monkeypatch):
    from karmabound.tela_pausa import OpcoesScene

    monkeypatch.setattr(opcoes.OPCOES, "caminho", None)  # não grava no teste
    fluxo.abrir_opcoes(fluxo.loop.current_scene)
    tela = fluxo.loop.current_scene
    assert isinstance(tela, OpcoesScene)
    e = Entrada()
    tela.entrada = e
    antes = opcoes.OPCOES.volume_musica
    aperta(tela, e, "esquerda")  # a primeira linha é a música
    assert opcoes.OPCOES.volume_musica == max(0, antes - 1)
    tela.cursor = tela.LINHAS.index("velocidade")
    v = opcoes.OPCOES.velocidade
    aperta(tela, e, "direita")
    assert opcoes.OPCOES.velocidade != v
    fluxo.loop.renderer.begin_frame()
    tela.render(None, fluxo.loop.renderer)


def test_a_tela_de_votos_quebra_pelo_menu(fluxo):
    from karmabound.tela_pausa import VotosScene

    j = fluxo.jornada
    cat = j.ctx.catalogo
    aplicar_voto(j.estado, j.ctx, Voto([cat.restricoes["sem_descanso"]], [cat.ganhos["vigor"]]))
    fluxo.pausar()
    fluxo.abrir_votos(fluxo.loop.current_scene)
    tela = fluxo.loop.current_scene
    assert isinstance(tela, VotosScene)
    e = Entrada()
    tela.entrada = e
    aperta(tela, e, "confirmar")  # escolhe o voto
    assert tela.voto is not None
    aperta(tela, e, "confirmar")  # marca a 1ª restrição para o voto de quebra
    tela.cursor = len(tela.restricoes)
    fluxo.loop.renderer.begin_frame()
    tela.render(None, fluxo.loop.renderer)
    aperta(tela, e, "confirmar")  # quebra
    assert j.estado.votos.ativos[0].de_quebra


def test_dica_empilha_uma_vez(fluxo, monkeypatch):
    from karmabound.tela_pausa import DicaScene

    monkeypatch.setattr(opcoes.OPCOES, "dicas", True)
    monkeypatch.setattr(opcoes.OPCOES, "dicas_vistas", [])
    monkeypatch.setattr(opcoes.OPCOES, "caminho", None)
    fluxo.dica("luta")
    assert isinstance(fluxo.loop.current_scene, DicaScene)
    fluxo.loop.pop_scene()
    fluxo.dica("luta")
    assert not isinstance(fluxo.loop.current_scene, DicaScene)


def test_toda_dica_cabe_na_fonte():
    """As dicas são texto do jogo: entram no teste de caracteres da fonte de pincel."""
    from karmabound.dicas import DICAS

    assert all(len(t) < 400 for _, _, t in DICAS.values())
