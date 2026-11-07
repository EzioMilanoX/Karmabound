"""A compra manual no Altar: pontos, níveis, o que cabe e a força guardada."""

import pytest

from karmabound.jornada import Jornada
from karmabound.tela_menus import AltarScene


def no_altar(seed=5) -> Jornada:
    j = Jornada.nova("acessivel", seed=seed)
    j.amostras_altar = 10
    j.girar_linhagem()
    j.girar_destino()
    j.girar_arco()
    j.estado.altar_pendente = True  # o capítulo acabou
    j._proxima_luta()
    assert j.fase == "altar"
    return j


RESTRICOES = ["sem_descanso", "corpo_ofertado"]


def test_a_sugestao_cabe_nos_pontos():
    j = no_altar()
    p = j.propor_voto(RESTRICOES)
    assert p.pontos > 0 and set(p.beneficio) == set(j.ctx.catalogo.ganhos)
    assert p.custo(j.ctx, p.voto.ganhos) <= p.pontos + 1e-9
    assert p.saldo is None  # o Altar não estima o saldo sem pedirem


def test_cabe_respeita_pontos_e_niveis():
    j = no_altar()
    p = j.propor_voto(RESTRICOES)
    forca = j.ctx.catalogo.ganhos["forca"]
    compra = []
    while p.cabe(j.ctx, compra, forca):
        compra.append(forca)
    assert len(compra) <= forca.niveis
    assert p.custo(j.ctx, compra) <= p.pontos + 1e-9


def test_jurar_com_a_propria_compra_guarda_a_sobra():
    j = no_altar()
    p = j.propor_voto(RESTRICOES)
    j.jurar(p, [])  # nenhum ganho: toda a força fica guardada
    assert j.estado.pontos_guardados == pytest.approx(p.pontos)
    assert j.estado.votos.ativos[-1].ganhos == []


def test_a_forca_guardada_entra_no_proximo_voto():
    j = no_altar()
    p = j.propor_voto(RESTRICOES)
    j.jurar(p, [])
    guardado = j.estado.pontos_guardados
    j.fase = "altar"
    j.sacrificios = {}
    p2 = j.propor_voto(["prazo"])
    if p2 is not None:
        base = p2.pontos - guardado
        assert base >= 0 and p2.pontos == pytest.approx(base + guardado)


def test_nao_jura_compra_cara_demais():
    j = no_altar()
    p = j.propor_voto(RESTRICOES)
    tudo = [g for g in j.ctx.catalogo.ganhos.values() for _ in range(g.niveis)]
    if p.custo(j.ctx, tudo) > p.pontos:
        with pytest.raises(ValueError):
            j.jurar(p, tudo)


class Entrada:
    def __init__(self):
        self.apertadas = set()

    def is_action_pressed(self, acao):
        return acao in self.apertadas


def test_a_tela_abre_com_a_sugestao_e_deixa_mexer():
    j = no_altar()
    e = Entrada()
    fim = []
    tela = AltarScene(j, e, lambda: fim.append(True), lambda: None)

    def quadro(*teclas):
        e.apertadas = set(teclas)
        tela.update(None, 1 / 30)
        e.apertadas = set()

    quadro()
    quadro()  # pesa as restrições
    assert tela.estado == "escolher"
    tela.marcadas = set(RESTRICOES)
    tela.cursor = tela.linhas.index("pesar")
    quadro("confirmar")
    quadro()
    quadro()
    assert tela.estado == "comprar"
    assert tela.compra == tela.proposta.voto.ganhos  # a sugestão do Altar vem marcada
    if tela.compra:
        primeiro = tela.compra[0]
        tela.cursor_compra = tela.ganhos.index(primeiro)
        antes = len(tela.compra)
        quadro("esquerda")
        assert len(tela.compra) == antes - 1
    tela.cursor_compra = tela.linhas_compra.index("jurar")
    quadro("confirmar")
    assert fim and j.estado.votos.ativos
