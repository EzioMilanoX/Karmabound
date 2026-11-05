"""O Legado pelo Fluxo: o que uma run deixa chega à próxima (pasta temporária, ver conftest)."""

import json
import os

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

import pytest  # noqa: E402

from karmabound import cronica  # noqa: E402
from karmabound.combate import escolher_jogador_auto  # noqa: E402
from karmabound.game import build_game  # noqa: E402
from karmabound.legado import CUSTO_ANIME, INICIAIS, MAESTRIA, Legado  # noqa: E402
from karmabound.tela_menus import FimScene, TituloScene  # noqa: E402


@pytest.fixture
def loop():
    lp = build_game(seed=1)
    yield lp
    lp.renderer.shutdown()


def perder_a_run(j):
    """Joga com o piloto, entrando em cada luta por um fio de vida e sem Carma (nenhum
    Despertar salva): a run acaba logo, em derrota."""
    for _ in range(5000):
        if j.fase == "linhagem":
            j.girar_linhagem()
        elif j.fase == "destino":
            j.girar_destino()
        elif j.fase == "arco":
            j.girar_arco()
        elif j.fase == "caminho":
            j.escolher_caminho([p.tipo for p in j.oferta_caminho].index("rival"))
            j.carma.valor = 0
            j.jogador.vida = 1
        elif j.fase == "luta":
            luta = j.luta
            if luta.acabou:
                j.terminar_luta()
            elif luta.vez is j.jogador:
                luta.resolver(escolher_jogador_auto(luta))
            else:
                luta.turno_rival()
        elif j.fase == "treino":
            j.escolher_treino(0)
        elif j.fase == "tecnica":
            j.girar_tecnica()
            j.escolher_tecnica(0)
        elif j.fase == "substituir":
            j.substituir(None)
        elif j.fase == "altar":
            j.recusar_altar()
        elif j.fase == "reliquia":
            j.girar_reliquia()
        else:
            return
    raise AssertionError("a run não acabou")


def acabar(loop, fase="derrota", lutas=0):
    j = loop.fluxo.jornada
    j.fase = fase
    j.estado.lutas_vencidas = lutas
    loop.fluxo.passo()
    return loop.current_scene


def test_quem_te_mata_vira_a_nemesis_da_proxima_run(loop):
    fluxo = loop.fluxo
    fluxo.comecar("brutal", seed=3)
    j = fluxo.jornada
    perder_a_run(j)
    assert j.fase == "derrota" and j.assassino is not None
    fluxo.passo()
    fim = loop.current_scene
    assert isinstance(fim, FimScene)
    assert fim.fechamento.nemesis == "nasceu"
    assert fim.fechamento.nemesis_nome == j.assassino["nome"]
    assert any("Nêmesis nasceu" in texto for texto, _ in fim.linhas_legado())
    salvo = Legado.padrao()  # ficou no disco
    assert salvo.nemesis["nome"] == j.assassino["nome"]
    fluxo.titulo()
    assert any("Nêmesis à espera" in linha for linha in loop.current_scene.legado)
    fluxo.comecar("acessivel", seed=4)
    assert fluxo.jornada.ctx.nemesis == salvo.nemesis


def test_a_memoria_acumula_e_abre_um_anime(loop):
    fluxo = loop.fluxo
    ordem = fluxo.ordem
    assert fluxo.legado.abertos(ordem) == frozenset(ordem[:INICIAIS])
    fluxo.legado.memoria = CUSTO_ANIME - 2
    fluxo.comecar("acessivel", seed=5)
    assert fluxo.jornada.legado["abertos"] == frozenset(ordem[:INICIAIS])
    fim = acabar(loop, lutas=3)  # +3 de Memória: passa do custo
    novo = ordem[INICIAIS]
    assert fim.fechamento.memoria == 3 and fim.fechamento.animes == [novo]
    assert any(novo in texto for texto, _ in fim.linhas_legado())
    assert Legado.padrao().memoria == CUSTO_ANIME + 1
    fluxo.comecar("acessivel", seed=6)
    assert novo in fluxo.jornada.legado["abertos"]
    fluxo.titulo()
    titulo = loop.current_scene
    assert isinstance(titulo, TituloScene)
    assert set(titulo.animes) <= fluxo.legado.abertos(ordem)
    assert titulo.legado[0].startswith(f"Memória {CUSTO_ANIME + 1}")


def test_a_maestria_passa_para_a_jornada(loop):
    fluxo = loop.fluxo
    tid = next(iter(fluxo.ctx_completo.tecnicas))
    nome = fluxo.ctx_completo.tecnicas[tid].nome
    fluxo.comecar("acessivel", seed=7)
    fluxo.jornada.usos[tid] = MAESTRIA[0]
    fim = acabar(loop)
    assert (nome, 1) in fim.fechamento.maestrias
    fluxo.comecar("acessivel", seed=8)
    assert fluxo.jornada.ctx.maestria == {tid: 1}


def test_a_semente_do_dia_joga_sem_legado_mas_registra_a_memoria(loop):
    fluxo = loop.fluxo
    fluxo.legado.nemesis = {"nome": "Oni · Tsunami", "estilo": "oni", "tecnica": "", "vezes": 1}
    fluxo.legado.usos["corte_em_cruz"] = MAESTRIA[1]
    fluxo.semente_do_dia()
    j = fluxo.jornada
    assert j.legado["abertos"] is None and not j.ctx.maestria and j.ctx.nemesis is None
    j.assassino = {"nome": "Ronin · Golpe", "estilo": "espadachim", "tecnica": "", "nemesis": False}
    fim = acabar(loop, lutas=2)
    assert fim.fechamento.memoria == 2
    assert fluxo.legado.nemesis["nome"] == "Oni · Tsunami"  # quem matou na diária não conta


def test_quem_ja_jogava_comeca_com_a_memoria_da_cronica(tmp_path):
    arquivo = cronica.caminho()
    arquivo.parent.mkdir(parents=True, exist_ok=True)
    runs = [{"lutas": 5, "venceu": False}, {"lutas": 12, "venceu": True}]
    arquivo.write_text(json.dumps({"runs": runs, "feitos": []}), encoding="utf-8")
    lp = build_game(seed=1)
    try:
        assert lp.fluxo.legado.memoria == 5 + 12 + 5
    finally:
        lp.renderer.shutdown()
