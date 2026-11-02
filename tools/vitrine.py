"""Vitrine do visual: cada arena, cada rival e os efeitos, em PNG, sem janela.

    python tools/vitrine.py [pasta]     (padrão: docs/telas/vitrine/)

Cada quadro é uma luta montada na hora: o Arco do cenário, o rival de um estilo
e uma técnica congelada no meio da animação. Seed fixa: sai igual sempre.
"""

from __future__ import annotations

import os
import sys
from dataclasses import replace
from pathlib import Path

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")
os.environ.setdefault("OPENBLAS_NUM_THREADS", "1")
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import pygame  # noqa: E402

from karmabound import vfx  # noqa: E402
from karmabound.combate import Tecnica  # noqa: E402
from karmabound.game import build_game  # noqa: E402
from karmabound.jornada import Jornada  # noqa: E402
from karmabound.run import aplicar_arco, aplicar_dom  # noqa: E402
from karmabound.tela_luta import LutaScene  # noqa: E402

# (arquivo, arco, nº da luta (dá o estilo do rival), chefe, técnica, fração da animação)
QUADROS = [
    ("01_montanha_espiral", "treino_na_montanha", 1, False, "espiral_concentrada", 0.75),
    ("02_torneio_clones", "torneio_regular", 2, False, "clones_de_sombra", 0.7),
    ("03_eclipse_clarao_negro", "lua_de_sangue", 3, False, "clarao_negro", 0.15),
    ("04_invasao_trovao", "invasao", 4, False, "primeiro_trovao", 0.05),
    ("05_shibuya_dominio", "maldicao_coletiva", 1, False, "santuario", 0.55),
    ("06_marineford_corte_do_mundo", "arco_do_juizo", 4, True, "corte_do_mundo", 0.45),
    ("07_montanha_lua_ilusoria", "treino_na_montanha", 3, False, "lua_ilusoria", 0.5),
    ("08_torneio_presa_da_lua", "torneio_regular", 2, False, "presa_da_lua", 0.45),
    ("09_eclipse_contrato", "lua_de_sangue", 4, True, "contrato", 0.5),
    ("10_invasao_esfera", "invasao", 1, False, "esfera_dos_mil", 0.4),
    ("11_shibuya_instante", "maldicao_coletiva", 2, False, "instante_suspenso", 0.5),
    ("12_marineford_corrente", "arco_do_juizo", 3, False, "corrente_do_julgamento", 0.7),
]
DONS = {"santuario", "instante_suspenso"}


class Entrada:
    def is_action_pressed(self, _acao):
        return False


def _cena(arco: str, n_luta: int, chefe: bool) -> tuple[Jornada, LutaScene]:
    j = Jornada.nova("dificil", seed=11)
    j.estado.proxima_luta = n_luta
    if chefe:
        j.estado.luta_no_capitulo = j.estado.tamanho_capitulo
    fatias = {f.id: f for roda in j.ctx.rodas.values() for f in roda.fatias}
    j.fase = "arco"
    aplicar_arco(j.estado, j.ctx, fatias[arco])
    j._comecar_luta()
    j.luta.abertura = False
    j.luta.vez = j.jogador
    nada = lambda *a: None  # noqa: E731
    return j, LutaScene(j, Entrada(), nada, nada)


def capturar(destino: Path) -> list[Path]:
    destino.mkdir(parents=True, exist_ok=True)
    loop = build_game(seed=3)
    salvos = []
    for nome, arco, n_luta, chefe, tid, fracao in QUADROS:
        j, cena = _cena(arco, n_luta, chefe)
        fatias = {f.id: f for roda in j.ctx.rodas.values() for f in roda.fatias}
        if tid in DONS:
            aplicar_dom(j.estado, j.ctx, fatias[tid])
            tecnica = j.jogador.tecnica_dom
        else:
            tecnica = Tecnica.de_fatia(fatias[tid])
            if tecnica.critico:
                tecnica = replace(tecnica, critico=1.0)  # o quadro mostra o Clarão Negro saindo
            j.jogador.tecnicas.append(tecnica)
        j.jogador.recargas.clear()
        j.luta.rival.vida = j.luta.rival.vida_max = 999  # ninguém cai no meio do quadro
        cena.update(None, 1 / 60)
        cena._executar(tecnica)
        efeito = cena.efeito[0]
        alvo = fracao * vfx.duracao(efeito)
        passos = int(alvo * 60)
        for _ in range(passos):
            cena.update(None, 1 / 60)
        loop.renderer.begin_frame()
        cena.render(None, loop.renderer)
        caminho = destino / f"{nome}.png"
        pygame.image.save(pygame.display.get_surface(), str(caminho))
        salvos.append(caminho)
    salvos += _extras(loop, destino)
    loop.renderer.shutdown()
    return salvos


def _foto(loop, cena, caminho: Path) -> Path:
    loop.renderer.begin_frame()
    cena.render(None, loop.renderer)
    pygame.image.save(pygame.display.get_surface(), str(caminho))
    return caminho


def _extras(loop, destino: Path) -> list[Path]:
    """O Grimório com parte vista e um Despertar na luta (com a aura)."""
    from karmabound.grimorio import Grimorio
    from karmabound.tela_grimorio import GrimorioScene

    j, cena = _cena("lua_de_sangue", 2, False)
    g = Grimorio()
    todas = [f for roda in j.ctx.rodas.values() for f in roda.fatias]
    g.ver(f for i, f in enumerate(todas) if i % 3)
    grim = GrimorioScene(g, Entrada(), lambda: None, lambda: None, ctx=j.ctx)
    grim.i_roda, grim.cursor = 1, 13
    salvos = [_foto(loop, grim, destino / "13_grimorio.png")]
    grim.i_roda, grim.cursor = 3, 9
    salvos.append(_foto(loop, grim, destino / "14_grimorio_divino.png"))

    liberacao = next(f for f in j.ctx.rodas["despertar"].fatias if f.id == "liberacao_final")
    j.carma.valor = j.carma.config.maximo
    j.luta.ao_despertar = lambda: liberacao
    cena.update(None, 1 / 60)
    cena._celebrar(j.luta.despertar())
    for _ in range(int(0.6 * 60)):
        cena.update(None, 1 / 60)
    salvos.append(_foto(loop, cena, destino / "15_despertar_liberacao.png"))
    return salvos


if __name__ == "__main__":
    padrao = Path(__file__).resolve().parent.parent / "docs" / "telas" / "vitrine"
    pasta = Path(sys.argv[1]) if len(sys.argv) > 1 else padrao
    for p in capturar(pasta):
        print(p)
