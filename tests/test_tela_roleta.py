"""A cena da roleta dirigida quadro a quadro, sem janela, com uma entrada falsa."""

import json
import os

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

import pygame  # noqa: E402
import pytest  # noqa: E402

from karmabound.game import FONTES, build_game  # noqa: E402
from karmabound.rodas import DADOS  # noqa: E402

PASSO = 1 / 60


class EntradaFalsa:
    """Aperta uma ação por um quadro, como o `is_action_pressed` da engine."""

    def __init__(self):
        self.apertadas: set[str] = set()

    def is_action_pressed(self, acao: str) -> bool:
        return acao in self.apertadas


@pytest.fixture
def cena():
    loop = build_game(seed=4, roleta=True)
    cena = loop.current_scene
    cena.entrada = EntradaFalsa()
    cena.saiu = False
    cena.ao_sair = lambda: setattr(cena, "saiu", True)
    cena.loop = loop
    yield cena
    loop.renderer.shutdown()


def apertar(cena, acao):
    cena.entrada.apertadas = {acao}
    cena.update(None, PASSO)
    cena.entrada.apertadas = set()


def esperar(cena, segundos):
    for _ in range(int(segundos / PASSO)):
        cena.update(None, PASSO)
        cena.render(None, cena.loop.renderer)  # desenhar todo quadro também é testado


def test_giro_comum_termina_no_selo_sorteado(cena):
    apertar(cena, "girar")
    assert cena.estado == "girando"
    esperar(cena, 3)
    assert cena.estado == "resultado"
    assert cena.roda.fatias[cena.aceso] is cena.giro.fatias[0]
    assert cena.carma_visual == cena.mesa.carma.valor


def test_modo_escolha(cena):
    apertar(cena, "trocar_roda")
    assert cena.roda.id == "tecnicas"
    apertar(cena, "girar")
    esperar(cena, 4)
    assert cena.estado == "escolhendo"
    apertar(cena, "escolher_2")
    assert cena.estado == "resultado"
    assert cena.roda.fatias[cena.aceso] is cena.giro.fatias[1]


def test_despertar_quebra_as_correntes_e_entrega_divino(cena):
    cena.mesa.carma.valor = cena.mesa.carma.config.maximo
    cena.carma_visual = cena.mesa.carma.valor
    apertar(cena, "girar")
    assert cena.estado == "quebrando"
    esperar(cena, 6)
    assert cena.estado == "resultado" and cena.giro.despertar
    assert cena.giro.fatias[0].raridade == cena.mesa.ordem[-1]
    assert cena.carma_visual == 0


def test_dano_e_custo_enchem_o_carma_na_tela(cena):
    apertar(cena, "sofrer_dano")
    apertar(cena, "pagar_custo")
    assert cena.carma_visual == cena.mesa.carma.valor > 0


def test_nao_troca_de_roda_no_meio_do_giro(cena):
    apertar(cena, "girar")
    apertar(cena, "trocar_roda")
    assert cena.roda.id == "destino"


def test_esc_sai(cena):
    apertar(cena, "sair")
    assert cena.saiu


def test_a_fonte_tem_todo_kanji_das_rodas():
    """Um kanji sem glifo vira um quadrado vazio, e isso só apareceria na tela."""
    pygame.font.init()
    fonte = pygame.font.Font(str(FONTES / "YujiSyuku-Regular.ttf"), 20)
    rodas = json.loads((DADOS / "rodas.json").read_text(encoding="utf-8"))["rodas"]
    kanji = "".join(r["kanji"] for r in rodas) + "".join(
        f["kanji"] for r in rodas for f in r["fatias"]
    )
    faltando = [k for k, m in zip(kanji, fonte.metrics(kanji), strict=True) if m is None]
    assert not faltando
