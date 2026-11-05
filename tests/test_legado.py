"""O Legado entre runs: a roda se abre com a Memória, a Maestria e a Nêmesis (regras)."""

import random
from collections import Counter

from karmabound.legado import (
    CUSTO_ANIME,
    INICIAIS,
    MAESTRIA,
    Legado,
    memoria_da_cronica,
    nivel_maestria,
    ordem_dos_animes,
)
from karmabound.rodas import anime_de
from karmabound.run import Contexto, criar_tecnica, nova_run


def _ordem():
    return ordem_dos_animes(Contexto.padrao().rodas)


def test_comeca_com_os_animes_mais_ricos():
    ordem = _ordem()
    leg = Legado()
    assert len(leg.abertos(ordem)) == INICIAIS
    assert "Naruto" in leg.abertos(ordem)
    anime, falta = leg.proximo(ordem)
    assert anime == ordem[INICIAIS] and falta == CUSTO_ANIME


def test_memoria_abre_anime_novo():
    ordem = _ordem()
    leg = Legado()
    f = leg.fechar_run(ordem, lutas=4, capitulos=1, venceu=False, usos=Counter())
    assert f.memoria == 6 and f.animes == [ordem[INICIAIS]]
    assert ordem[INICIAIS] in leg.abertos(ordem)


def test_rodas_so_com_os_animes_abertos_e_sem_raridade_vazia():
    ordem = _ordem()
    abertos = frozenset(ordem[:INICIAIS])
    ctx = Contexto.padrao(abertos=abertos)
    completo = Contexto.padrao()
    for rid, roda in ctx.rodas.items():
        raridades = {f.raridade for f in completo.rodas[rid].fatias}
        assert {f.raridade for f in roda.fatias} == raridades
    fora = [f for f in ctx.rodas["tecnicas"].fatias if anime_de(f.origem) not in abertos]
    # só entram de fora: as técnicas iniciais e os convidados de uma raridade sem ninguém
    tem = {f.raridade for f in ctx.rodas["tecnicas"].fatias if anime_de(f.origem) in abertos}
    fixas = set(ctx.combate["jogador"]["tecnicas"])
    fixas |= {f.inicial for f in completo.rodas["linhagem"].fatias if f.inicial}
    assert all(f.id in fixas or f.raridade not in tem for f in fora)
    nova_run(ctx, random.Random(1))  # a run começa com as rodas filtradas


def test_maestria_por_usos():
    assert nivel_maestria(MAESTRIA[0] - 1) == 0
    assert nivel_maestria(MAESTRIA[0]) == 1
    assert nivel_maestria(MAESTRIA[1]) == 2
    leg = Legado()
    usos = Counter({"chamas_negras": MAESTRIA[0]})
    f = leg.fechar_run(_ordem(), 0, 0, False, usos, nomes={"chamas_negras": "Chamas"})
    assert leg.maestria() == {"chamas_negras": 1} and f.maestrias == [("Chamas", 1)]


def test_tecnica_com_maestria_chega_evoluida():
    ctx = Contexto.padrao(maestria={"chamas_negras": 2})
    t = criar_tecnica(ctx, ctx.tecnicas["chamas_negras"])
    assert t.nivel == 3


def test_nemesis_nasce_cresce_e_e_vingada():
    ordem = _ordem()
    leg = Legado()
    quem = {"nome": "Ronin · Chidori", "estilo": "espadachim", "tecnica": "chidori"}
    f = leg.fechar_run(ordem, 2, 0, False, Counter(), assassino=quem)
    assert f.nemesis == "nasceu" and leg.nemesis["vezes"] == 1
    f = leg.fechar_run(ordem, 2, 0, False, Counter(), assassino={**quem, "nemesis": True})
    assert f.nemesis == "cresceu" and leg.nemesis["vezes"] == 2
    f = leg.fechar_run(ordem, 9, 2, False, Counter(), vingou=True)
    assert f.nemesis == "vingada" and leg.nemesis is None and leg.vingancas == 1


def test_salva_e_recarrega(tmp_path):
    arquivo = tmp_path / "legado.json"
    leg = Legado(arquivo)
    leg.fechar_run(_ordem(), 5, 1, True, Counter({"a": 3}))
    de_novo = Legado(arquivo)
    assert de_novo.memoria == leg.memoria and de_novo.usos["a"] == 3


def test_arquivo_estragado_recomeca(tmp_path):
    arquivo = tmp_path / "legado.json"
    arquivo.write_text("{ isto não é json", encoding="utf-8")
    assert Legado(arquivo, memoria_inicial=4).memoria == 4


def test_memoria_retroativa_pela_cronica():
    runs = [{"lutas": 5, "venceu": False}, {"lutas": 12, "venceu": True}]
    assert memoria_da_cronica(runs) == 5 + 12 + 5
