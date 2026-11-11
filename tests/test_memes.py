"""Os chefes secretos (memes.py): a sequência no título, a imagem e a chance."""

import random
from types import SimpleNamespace

import pygame

from karmabound import memes
from karmabound.jornada import Jornada
from karmabound.run import Contexto, vilao_chefe
from karmabound.viloes import carregar_viloes


class Setas:
    def __init__(self):
        self.agora = ""

    def is_action_pressed(self, a):
        return a == self.agora


def _com_imagens(n=2):
    pasta = memes.pasta_memes() / "speaki"
    pasta.mkdir(parents=True, exist_ok=True)
    for i in range(n):
        pygame.image.save(pygame.Surface((40, 60)), str(pasta / f"{i}.png"))
    return pasta


def test_a_sequencia_do_bullethell_fecha_so_inteira():
    seq, e = memes.Sequencia(), Setas()
    fechou = []
    for seta in ("cima", "cima", "baixo", "baixo", "esquerda", "direita", "esquerda", "direita"):
        e.agora = seta
        fechou.append(seq.apertou(e))
    assert fechou == [False] * 7 + [True]
    e.agora = "cima"
    assert not seq.apertou(e)


def test_sem_imagem_o_chefe_secreto_nao_aparece():
    assert memes.memes_disponiveis(carregar_viloes()) == ()
    assert Contexto.padrao("dificil", memes=True).memes == ()


def test_com_imagem_ele_toma_o_lugar_de_alguns_chefes():
    _com_imagens()
    ctx = Contexto.padrao("dificil", memes=True)
    assert [v.id for v in ctx.memes] == ["speaki"]
    estado = SimpleNamespace(alem=False, capitulo=1, chefe=True, viloes_vistos=[])
    vistos = {vilao_chefe(estado, ctx, random.Random(s)).id for s in range(60)}
    assert "speaki" in vistos and len(vistos) > 1  # às vezes, não sempre
    estado.capitulo = 3  # o último capítulo é sempre do Dono
    assert all(vilao_chefe(estado, ctx, random.Random(s)).id != "speaki" for s in range(30))


def test_a_animacao_troca_de_quadro_e_desenha_a_imagem():
    _com_imagens(2)
    speaki = carregar_viloes()["speaki"]
    chamadas = []
    r = SimpleNamespace(
        load_texture=lambda tid, caminho: chamadas.append(("carrega", caminho)),
        draw_batch=lambda *a: chamadas.append(("desenha", int(a[3][0]))),
    )
    assert memes.desenhar_meme(r, speaki, 480, 380, 190, relogio=0.0)
    assert memes.desenhar_meme(r, speaki, 480, 380, 190, relogio=speaki.troca + 0.01)
    texturas = [c[1] for c in chamadas if c[0] == "desenha"]
    assert len(set(texturas)) == 2  # dois quadros diferentes


def test_a_jornada_leva_os_segredos_para_o_contexto():
    _com_imagens()
    assert Jornada.nova("dificil", seed=1, memes=True).ctx.memes


def test_o_som_do_chefe_secreto_sai_pelo_momento(monkeypatch):
    pasta = memes.pasta_memes() / "speaki" / "sons"
    pasta.mkdir(parents=True, exist_ok=True)
    for nome in ("golpe_1.mp3", "golpe_2.mp3", "dor.mp3", "leia.txt"):
        (pasta / nome).write_bytes(b"")
    speaki = carregar_viloes()["speaki"]
    assert [p.name for p in memes.sons(speaki, "golpe")] == ["golpe_1.mp3", "golpe_2.mp3"]
    tocados = []
    from karmabound.som import SOM

    monkeypatch.setattr(SOM, "tocar_arquivo", lambda p, v=1.0: tocados.append(p.name))
    assert memes.tocar_meme(speaki, "dor") and tocados == ["dor.mp3"]
    assert not memes.tocar_meme(speaki, "entrada")  # sem arquivo: mudo
    assert not memes.tocar_meme(carregar_viloes().viloes[0], "dor")  # não é meme


def test_a_speaki_luta_so_com_o_que_e_dela():
    from karmabound import livre

    j = livre.montar({"rival": "speaki"}, "dificil", seed=3)
    ids = {t.id for t in j.luta.rival.tecnicas}
    dela = {"choro_de_speaki", "olhar_pidao", "rolar_no_chao", "mais_speakis", "grito_de_speaki"}
    assert ids == dela  # nenhuma técnica sorteada do pool


def test_a_trilha_do_chefe_secreto_vem_da_pasta_dele():
    speaki = carregar_viloes()["speaki"]
    assert memes.trilha(speaki) is None  # sem arquivo: a música de chefe de sempre
    pasta = memes.pasta_memes() / "speaki"
    pasta.mkdir(parents=True, exist_ok=True)
    (pasta / "musica.wav").write_bytes(b"")
    assert memes.trilha(speaki).name == "musica.wav"
    assert memes.trilha(carregar_viloes().viloes[0]) is None
