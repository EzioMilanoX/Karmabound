"""Renderiza os estados da roleta em PNG, sem janela: python tools/capturar_telas.py [pasta]

Padrão: docs/telas/ (as imagens de referência do visual, versionadas com o projeto).

Serve para revisar o visual sem jogar até cada estado. Seed fixa: as imagens
saem iguais a cada execução enquanto o código não mudar.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import pygame  # noqa: E402

from karmabound.game import build_game  # noqa: E402
from karmabound.tela_roleta import DURACAO_QUEBRA, RoletaScene  # noqa: E402


def capturar(destino: Path) -> list[Path]:
    destino.mkdir(parents=True, exist_ok=True)
    loop = build_game(seed=3, roleta=True)
    cena: RoletaScene = loop.current_scene
    carma = cena.mesa.carma
    salvos: list[Path] = []

    def foto(nome: str) -> None:
        cena.relogio = max(cena.relogio, 1.0)  # já passou a tinta da transição
        loop.renderer.begin_frame()
        cena.render(None, loop.renderer)
        caminho = destino / f"{nome}.png"
        pygame.image.save(pygame.display.get_surface(), str(caminho))
        salvos.append(caminho)

    def avancar(segundos: float) -> None:
        passo = 1 / 60
        for _ in range(int(segundos / passo)):
            cena.update(None, passo)

    foto("01_parado")

    cena._comecar_giro()
    avancar(0.9)
    foto("02_girando")
    avancar(3)
    foto("03_resultado")

    cena.i_roda = 1  # Técnicas: gira 3, escolhe 1
    cena._ir("parado")
    cena._comecar_giro()
    avancar(4)
    foto("04_escolhendo")
    cena.escolhida, cena.aceso = 0, cena.alvos[0]
    cena._ir("resultado")
    foto("05_tecnica_escolhida")

    cena.i_roda = 0
    cena._ir("parado")
    cena.giro = None
    carma.valor = 80
    cena.carma_visual = 80
    foto("06_carma_pity_suave")
    carma.valor = carma.config.maximo
    cena.carma_visual = carma.valor
    foto("07_carma_transbordando")

    cena._comecar_giro()  # vira o Despertar
    avancar(DURACAO_QUEBRA * 0.15)
    foto("08_quebra_inicio")
    avancar(DURACAO_QUEBRA * 0.45)
    foto("09_quebra_meio")
    avancar(5)
    foto("10_despertar_resultado")

    loop.renderer.shutdown()
    return salvos


def capturar_run(destino: Path) -> list[Path]:
    """As telas da run: título, roleta da jornada, luta, troca, Altar e fim."""
    from karmabound.combate import Tecnica
    from karmabound.jornada import Jornada
    from karmabound.tela_luta import LutaScene
    from karmabound.tela_menus import AltarScene, FimScene, SubstituirScene, TituloScene
    from karmabound.tela_roleta import RoletaScene

    class Entrada:
        apertadas: set = set()

        def is_action_pressed(self, a):
            return a in self.apertadas

    destino.mkdir(parents=True, exist_ok=True)
    loop = build_game(seed=3)
    ent = Entrada()
    nada = lambda *a: None  # noqa: E731
    salvos: list[Path] = []

    def foto(cena, nome, segundos=0.0, teclas=()):
        ent.apertadas = set(teclas)
        cena.update(None, 1 / 60)
        ent.apertadas = set()
        for _ in range(int(segundos * 60)):
            cena.update(None, 1 / 60)
        if not isinstance(cena, LutaScene):
            cena.relogio = max(cena.relogio, 2.0)  # o ensō do título fechado, a tinta já recolhida
        loop.renderer.begin_frame()
        cena.render(None, loop.renderer)
        caminho = destino / f"{nome}.png"
        pygame.image.save(pygame.display.get_surface(), str(caminho))
        salvos.append(caminho)

    foto(TituloScene(ent, nada, nada), "run_01_titulo")
    j = Jornada.nova("dificil", seed=11)
    j.amostras_altar = 40
    linhagem = RoletaScene(
        j.estado.mesa, ent, nada, "linhagem", j.girar_linhagem, nada, titulo="Seu sangue"
    )
    foto(linhagem, "run_02a_linhagem", 3.5, ["girar"])
    roleta = RoletaScene(
        j.estado.mesa, ent, nada, "destino", j.girar_destino, nada, titulo="Seu destino"
    )
    foto(roleta, "run_02_destino", 3.5, ["girar"])
    j.girar_arco()
    from karmabound.run import aplicar_dom, receber_reliquia

    dons = {f.id: f for f in j.ctx.rodas["destino"].fatias}
    rel = {f.id: f for f in j.ctx.rodas["reliquias"].fatias}
    aplicar_dom(j.estado, j.ctx, dons["instante_suspenso"])
    for rid in ("bandagem", "mascara_de_oni", "coracao_selado"):
        receber_reliquia(j.estado, rel[rid])
    j.aviso = "Golpe Direto: fragmento 1 de 2"
    tec = j.ctx.tecnicas
    j.jogador.tecnicas.append(Tecnica.de_fatia(tec["marca_da_maldicao"]))
    j.jogador.percepcao = 2
    luta = LutaScene(j, ent, nada, nada)
    foto(luta, "run_03_luta", 2.0)
    j.carma.valor = j.carma.config.maximo
    while j.luta.vez is not j.jogador and not j.luta.acabou:
        luta.update(None, 1 / 60)
    luta.anim_ate = 0
    foto(luta, "run_03b_luta_despertar_pronto")
    foto(luta, "run_03c_despertar", 0.5, ["despertar"])
    luta.desperto, luta.anim_ate = None, 0
    if j.luta.voto_luta is not None and j.luta.pode_jurar_luta():
        luta.modo = "voto"
        foto(luta, "run_03d_voto_de_luta")
        luta.modo = "escolher"
    # Leva 3: uma transformação ativa, e o rival queimando na chama negra e envenenado
    if not j.luta.acabou:
        cabelo = Tecnica.de_fatia(tec["cabelo_dourado"])
        j.jogador.entrar_no_modo(cabelo)
        j.jogador.clones = 2
        rival = j.luta.rival
        rival.chama, rival.veneno = 6, 4
        luta.anim_ate = 0
        foto(luta, "run_03e_transformacao")
        j.jogador.modo, j.jogador.modo_id, j.jogador.clones = None, "", 0
        rival.chama = rival.veneno = 0

    j.jogador.tecnicas.append(Tecnica.de_fatia(tec["julgamento"]))
    j.pendente, j.fase = tec["contrato"], "substituir"
    foto(SubstituirScene(j, ent, nada, nada), "run_04_substituir")

    j.fase = "reliquia"  # entre lutas; o capítulo acabou: o Altar abre
    j.estado.altar_pendente = True
    j._proxima_luta()
    altar = AltarScene(j, ent, nada, nada)
    foto(altar, "run_05_altar_pesando")
    altar.update(None, 1 / 60)
    altar.marcadas = {"sem_descanso", "corpo_ofertado"}
    foto(altar, "run_06_altar")
    altar.cursor = altar.linhas.index("pesar")
    foto(altar, "run_07_altar_proposta", 0.1, ["confirmar"])

    j.fase = "vitoria"
    j.estado.lutas_vencidas = 12
    foto(FimScene(j, ent, nada, nada), "run_08_fim")
    loop.renderer.shutdown()
    return salvos


if __name__ == "__main__":
    padrao = Path(__file__).resolve().parent.parent / "docs" / "telas"
    pasta = Path(sys.argv[1]) if len(sys.argv) > 1 else padrao
    for p in capturar(pasta) + capturar_run(pasta):
        print(p)
