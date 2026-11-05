"""Fusões: técnicas que nascem quando o jogador junta as peças (regras, sem tela)."""

import random
from dataclasses import replace

import pytest

from karmabound.fusoes import carregar_fusoes, fundir, nomes_dos_requisitos, tecnicas_de_fusao
from karmabound.grimorio import Grimorio
from karmabound.jornada import Jornada
from karmabound.mesa import Giro
from karmabound.rodas import anime_de
from karmabound.run import (
    Contexto,
    _fundir_auto,
    aplicar_dom,
    aplicar_linhagem,
    criar_tecnica,
    espacos,
    jogar_run,
    nova_run,
    receber_reliquia,
)


@pytest.fixture(scope="module")
def ctx():
    return Contexto.padrao("dificil")


def _fatia(ctx, roda, fid):
    return next(f for f in ctx.rodas[roda].fatias if f.id == fid)


def _estado(ctx, *tecnicas, seed=1):
    """Uma run sem Dom nem Linhagem, com estas técnicas nos espaços."""
    e = nova_run(ctx, random.Random(seed))
    e.dom = e.linhagem = None
    e.jogador.tecnica_dom = e.jogador.tecnica_linhagem = None
    e.jogador.tecnicas = [criar_tecnica(ctx, ctx.tecnicas[t]) for t in tecnicas]
    return e


def _ids(e):
    return [t.id for t in e.jogador.tecnicas]


# ------------------------------------------------------------------ dados


def test_as_fusoes_carregam_com_resultado_e_receita(ctx):
    fusoes = carregar_fusoes()
    assert len(fusoes) == 12 and len({f.id for f in fusoes}) == 12
    assert {f.id: f.resultado for f in fusoes}["roxo"] == "vazio_purpura"
    assert nomes_dos_requisitos(fusoes[0]) == ["Olhos que Tudo Veem", "Vazio Infinito"]
    assert all(f.fatia.combate for f in fusoes)
    assert ctx.fusoes == fusoes


def test_as_tecnicas_novas_sao_malditas_ou_divinas_com_homenagem(ctx):
    novas = tecnicas_de_fusao()
    assert len(novas) == 8
    for f in novas.values():
        assert f.id not in ctx.tecnicas  # só nascem de fusão: nunca saem da roda
        assert f.raridade in ("maldito", "divino")
        assert anime_de(f.origem) and f.kanji and "{" not in f.texto
        assert "Preço" in f.texto  # todo poder tem preço


# ------------------------------------------------------------------ a regra de entrada


def test_a_fusao_toma_o_lugar_da_primeira_tecnica_requisito(ctx):
    e = _estado(ctx, "espiral_concentrada", "golpe_direto", "golpe_de_vento")
    nascidas = fundir(e, ctx)
    assert [n.fatia.id for n in nascidas] == ["shuriken_espiral"]
    assert nascidas[0].resultado == "trocou" and nascidas[0].saiu == "espiral_concentrada"
    assert _ids(e) == ["shuriken_espiral", "golpe_direto", "golpe_de_vento"]  # a Foice fica


def test_cada_fusao_nasce_uma_vez_por_run(ctx):
    e = _estado(ctx, "espiral_concentrada", "golpe_de_vento")
    assert len(fundir(e, ctx)) == 1
    e.jogador.tecnicas[0] = criar_tecnica(ctx, ctx.tecnicas["espiral_concentrada"])
    assert fundir(e, ctx) == []
    assert e.fusoes_nascidas == ["shuriken"]


def test_a_primeira_fusao_da_lista_leva_a_peca_disputada(ctx):
    e = _estado(ctx, "espiral_concentrada", "golpe_de_vento", "mil_clones")
    fundir(e, ctx)
    assert _ids(e) == ["shuriken_espiral", "golpe_de_vento", "mil_clones"]
    assert "chuva_de_espirais" not in e.fusoes_nascidas  # a Espiral já virou Shuriken


def test_requisito_um_de(ctx):
    e = _estado(ctx, "golpe_direto", "punho_armado")
    aplicar_dom(e, ctx, _fatia(ctx, "destino", "pele_de_borracha"))
    assert [n.fatia.id for n in fundir(e, ctx)] == ["punho_colossal"]
    assert _ids(e) == ["golpe_direto", "punho_colossal"]


def test_linhagem_tecnica_inicial_e_reliquia(ctx):
    e = _estado(ctx, "golpe_direto", "guarda_alta")
    aplicar_linhagem(e, ctx, _fatia(ctx, "linhagem", "alquimistas"))  # traz a Parede
    assert fundir(e, ctx) == []
    receber_reliquia(e, _fatia(ctx, "reliquias", "pedra_filosofal"))
    assert [n.fatia.id for n in fundir(e, ctx)] == ["palmas_da_verdade"]
    assert "parede_transmutada" not in _ids(e) and "palmas_da_verdade" in _ids(e)


def test_sem_tecnica_requisito_entra_como_nova(ctx):
    e = _estado(ctx, "golpe_direto")
    aplicar_dom(e, ctx, _fatia(ctx, "destino", "olhos_que_tudo_veem"))
    e.despertares_ids.append("vazio_infinito")
    (n,) = fundir(e, ctx)
    assert n.resultado == "equipada" and _ids(e) == ["golpe_direto", "vazio_purpura"]


def test_o_piloto_troca_a_pior_quando_a_fusao_nasce_sem_espaco(ctx):
    e = _estado(ctx, "golpe_direto", "guarda_alta", "investida", "presa_da_lua")
    assert len(e.jogador.tecnicas) == espacos(e, ctx)
    aplicar_dom(e, ctx, _fatia(ctx, "destino", "olhos_que_tudo_veem"))
    e.despertares_ids.append("vazio_infinito")
    _fundir_auto(e, ctx)
    assert "vazio_purpura" in _ids(e) and len(e.jogador.tecnicas) == 4
    assert "presa_da_lua" in _ids(e)  # sai a pior (uma Cinza)


def test_o_piloto_funde_durante_a_run(ctx):
    e = _estado(ctx, "espiral_concentrada", "golpe_de_vento")
    jogar_run(e, ctx, random.Random(2), ate=e.proxima_luta)
    assert "shuriken" in e.fusoes_nascidas


def test_clonar_nao_divide_as_listas_das_fusoes(ctx):
    e = _estado(ctx, "golpe_direto")
    clone = e.clonar(random.Random(0))
    clone.despertares_ids.append("vazio_infinito")
    clone.fusoes_nascidas.append("roxo")
    assert e.despertares_ids == [] and e.fusoes_nascidas == []


# ------------------------------------------------------------------ na Jornada


def _ate_a_luta(seed=3, dom="olhos_que_tudo_veem") -> Jornada:
    j = Jornada.nova("dificil", seed=seed)
    j.grimorio = Grimorio()  # só em memória
    j.girar_linhagem()
    j.girar_destino()
    aplicar_dom(j.estado, j.ctx, _fatia(j.ctx, "destino", dom))
    if j.fase == "substituir":  # alguma fusão da sorte: descarta, o teste é o Roxo
        j.substituir(None)
    j.girar_arco()
    if j.fase == "caminho":
        j.escolher_caminho(0)  # sempre há um Rival
    assert j.fase == "luta"
    return j


def _despertar_vazio(j: Jornada, monkeypatch) -> None:
    """Dispara um Despertar que a roda faz sair Vazio Infinito, e vence a luta."""
    vazio = _fatia(j.ctx, "despertar", "vazio_infinito")
    girar = j.estado.mesa.girar

    def girar_vazio(roda, **kw):
        return Giro(j.ctx.rodas[roda], [vazio]) if roda == "despertar" else girar(roda, **kw)

    monkeypatch.setattr(j.estado.mesa, "girar", girar_vazio)
    j.carma.valor = j.carma.config.maximo
    j.luta.despertar()
    for r in j.luta.rivais:
        r.vida = 0
    assert j.terminar_luta()


def test_roxo_nasce_quando_os_seis_olhos_disparam_o_vazio_infinito(monkeypatch):
    j = _ate_a_luta()
    _despertar_vazio(j, monkeypatch)
    assert j.estado.despertares_ids == ["vazio_infinito"]
    assert "vazio_purpura" in [t.id for t in j.jogador.tecnicas]
    assert [f.id for f in j.fusoes_novas] == ["vazio_purpura"]
    assert "Vazio Púrpura" in j.aviso
    assert j.grimorio.viu("vazio_purpura")
    assert j.fase in ("treino", "tecnica")


def test_roxo_sem_espaco_abre_a_troca_e_depois_segue(monkeypatch):
    j = _ate_a_luta()
    investida = criar_tecnica(j.ctx, j.ctx.tecnicas["investida"])
    while len(j.jogador.tecnicas) < espacos(j.estado, j.ctx):  # enche os espaços
        j.jogador.tecnicas.append(replace(investida, id=f"investida{len(j.jogador.tecnicas)}"))
    _despertar_vazio(j, monkeypatch)
    assert j.fase == "substituir" and j.pendente.id == "vazio_purpura"
    seguinte = j.retomar
    assert seguinte in ("treino", "tecnica")
    j.substituir(j.tecnica_mais_fraca())
    assert j.fase == seguinte and "vazio_purpura" in [t.id for t in j.jogador.tecnicas]
    assert j.retomar == "" and j.pendente is None
