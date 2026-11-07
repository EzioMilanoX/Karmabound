"""O cinema da luta: cut-in, câmera, aviso de perigo, guarda, afixos, mecânicas de
chefe, aliado, ressonância no cabeçalho, fusões e a música da segunda forma."""

import os

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

from dataclasses import replace  # noqa: E402

from karmabound import som, vfx  # noqa: E402
from karmabound.combate import Acao, Tecnica, limiar_guarda  # noqa: E402
from karmabound.fusoes import tecnicas_de_fusao  # noqa: E402
from karmabound.jornada import Jornada  # noqa: E402
from karmabound.rodas import anime_de  # noqa: E402
from karmabound.run import escolher_porta  # noqa: E402
from karmabound.tela_luta import DURACAO_CUTIN, IMPACTO, LutaScene  # noqa: E402


class Entrada:
    def __init__(self):
        self.apertadas: set[str] = set()
        self.seguradas: set[str] = set()

    def is_action_pressed(self, acao):
        return acao in self.apertadas

    def is_action_held(self, acao):
        return acao in self.seguradas


class Gravador:
    """Um renderer que só anota os textos (o resto passa)."""

    def __init__(self):
        self.textos: list[str] = []

    def draw_text(self, x, y, texto, *a, **k):
        self.textos.append(texto)

    def __getattr__(self, nome):
        return lambda *a, **k: None


def anda(cena, segundos, passo=1 / 60):
    for _ in range(round(segundos / passo)):
        cena.update(None, passo)


def _luta(tipo="rival", papeis=(), seed=11, extras=(), aliado="", nivel=1, chefe=None):
    j = Jornada.nova("dificil", seed=seed, jogo="chefes" if chefe else "classico")
    if chefe:
        # um chefe anônimo com esta assinatura (sem vilão, que traria as dele)
        j.ctx = replace(j.ctx, chefes=tuple(c for c in j.ctx.chefes if c.id == chefe), elenco=None)
    j.ctx = replace(j.ctx, elenco=None)  # rivais anônimos: estes testes olham a tela
    j.estado.aliado, j.estado.aliado_nivel = aliado, nivel
    j.girar_linhagem()
    j.girar_destino()
    j.girar_arco()
    for tid in extras:
        f = j.ctx.tecnicas.get(tid) or tecnicas_de_fusao()[tid]
        j.jogador.tecnicas.append(Tecnica.de_fatia(f))
    j.jogador.percepcao = 3
    if j.fase == "caminho":
        escolher_porta(j.estado, j.ctx.caminho.porta(tipo, papeis=papeis))
        j._comecar_luta()
    elif j.fase != "luta":
        j._comecar_luta()
    return j


def _tela(j, dicas=None):
    e = Entrada()
    ao_dica = dicas.append if dicas is not None else None
    tela = LutaScene(j, e, lambda v: None, lambda: None, ao_dica)
    tela.entrada_ate = 0
    tela.relogio = 1.0
    tela.anim_ate = tela.proxima_rival = 0
    j.luta.vez = j.jogador
    return tela, e


def _usar(tela, tid):
    j = tela.j.jogador
    t = next(t for t in [tela.luta.basico, *j.tecnicas] if t.id == tid)
    j.recargas.pop(t.id, None)
    tela.luta.vez = j
    tela.anim_ate = tela.relogio
    tela._executar(t)
    return tela.luta.log[-1]


# ----------------------------------------------------------------------- cut-in


def test_cut_in_da_maldita_aparece_segura_o_golpe_e_termina():
    tela, _ = _tela(_luta(extras=("onda_de_ki",)))
    inicio = tela.relogio
    _usar(tela, "onda_de_ki")
    info, quando = tela.cutin
    assert info["nome"] == "Onda de Ki" and info["kanji"] == "気" and not info["rival"]
    assert "Dragon Ball" in info["origem"] and quando == inicio
    assert tela.golpe[1] >= inicio + DURACAO_CUTIN  # o golpe sai depois do cut-in
    tela.render(None, Gravador())
    assert tela.cutin_k() is not None
    anda(tela, DURACAO_CUTIN + 0.05)
    assert tela.cutin_k() is None


def test_o_cut_in_da_mesma_tecnica_nao_repete_na_luta():
    tela, _ = _tela(_luta(extras=("onda_de_ki",)))
    _usar(tela, "onda_de_ki")
    primeiro = tela.cutin
    anda(tela, 3)
    _usar(tela, "onda_de_ki")
    assert tela.cutin is primeiro  # nenhum cut-in novo
    assert tela.golpe[1] < tela.relogio + 0.1  # e o golpe sai na hora


def test_fusao_tem_cut_in_toda_vez_e_kanji_proprio():
    tela, _ = _tela(_luta(extras=("onda_carmesim",)))
    assert tela.kanji["onda_carmesim"] == "紅" and tela.nomes["onda_carmesim"] == "Onda Carmesim"
    _usar(tela, "onda_carmesim")
    primeiro = tela.cutin
    assert primeiro[0]["rotulo"].startswith("融合")
    anda(tela, 3)
    _usar(tela, "onda_carmesim")
    assert tela.cutin is not primeiro


def test_toda_tecnica_de_fusao_e_assinatura_tem_efeito_proprio():
    ids = [*tecnicas_de_fusao(), "general_da_roda", "flor_no_espelho"]
    for tid in ids:
        nome = vfx.POR_HABILIDADE[tid]
        assert nome in vfx.EFEITOS and nome in som.SOM_DO_EFEITO, tid


def test_cut_in_do_rival_cor_de_sangue():
    j = _luta(seed=12)
    tela, _ = _tela(j)
    enma = Tecnica.de_fatia(j.ctx.tecnicas["enma"])
    r = j.luta.rival
    r.tecnicas.append(enma)
    j.luta.vez, j.luta.intencoes[id(r)] = r, enma
    tela.proxima_rival = 0
    tela.update(None, 1 / 60)
    assert tela.cutin[0]["rival"] and tela.cutin[0]["nome"] == enma.nome


def test_acelerar_encurta_o_cut_in():
    tela, e = _tela(_luta(extras=("onda_de_ki",)))
    _usar(tela, "onda_de_ki")
    e.seguradas = {"acelerar"}
    anda(tela, DURACAO_CUTIN / 3 + 0.05)
    assert tela.cutin_k() is None


# ----------------------------------------------------------------------- câmera


def test_golpe_forte_da_punch_in_so_no_mundo():
    j = _luta()
    tela, _ = _tela(j)
    j.jogador.tecnicas.append(Tecnica("negro", "Golpe Negro", "ataque", dano=20, critico=1.0))
    _usar(tela, "negro")
    assert tela.zoom is not None
    anda(tela, IMPACTO)
    escala, _pivo, _dx, _dy = tela._camera()
    assert 1.05 < escala <= 1.1
    anda(tela, 1.0)
    assert tela._camera()[0] == 1.0


# ----------------------------------------------------------------------- perigo


def test_aviso_de_perigo_liga_com_intencao_perigosa():
    j = _luta()
    tela, _ = _tela(j)
    r = j.luta.rival
    calma = Tecnica("calma", "Calma", "ataque", dano=3)
    j.luta.intencoes[id(r)] = calma
    assert tela._perigosos() == []
    perigosa = Tecnica("lamina", "Lâmina", "ataque", dano=14, perigosa=True)
    j.luta.intencoes[id(r)] = perigosa
    assert tela._perigosos() == [r]
    tela.render(None, Gravador())
    assert tela.perigo == [r]
    j.jogador.cego = True  # não enxerga: não há aviso
    assert tela._perigosos() == []


def test_aviso_de_perigo_no_bando_marca_so_quem_vai_usar():
    j = _luta("bando", ("lamina", "guardiao", "curandeiro"))
    tela, _ = _tela(j)
    perigosa = Tecnica("lamina", "Lâmina", "ataque", dano=14, perigosa=True)
    for r in j.luta.rivais:
        j.luta.intencoes[id(r)] = Tecnica("calma", "Calma", "ataque", dano=3)
    alvo = j.luta.rivais[2]
    j.luta.intencoes[id(alvo)] = perigosa
    assert tela._perigosos() == [alvo]


# ----------------------------------------------------------------------- guarda


def test_quebra_de_guarda_mostra_崩_e_o_tonto_espera_o_golpe():
    dicas = []
    j = _luta()
    tela, _ = _tela(j, dicas)
    r = j.luta.rival
    r.guarda = limiar_guarda(r) - 1
    acao = _usar(tela, "golpe_basico")
    assert acao.quebrou == r.nome and r.quebrado
    assert tela.quebras and not tela._quebrado(r)  # o golpe ainda não acertou
    anda(tela, IMPACTO + 0.05)
    assert tela._quebrado(r)
    g = Gravador()
    tela.render(None, g)
    assert "崩" in g.textos
    assert "guarda" in tela.registro
    tela.luta.vez, tela.anim_ate = j.jogador, 0
    tela.update(None, 1 / 60)
    assert "guarda" in dicas


def test_a_barra_de_guarda_enche_com_a_pressao():
    j = _luta()
    tela, _ = _tela(j)
    r = j.luta.rival
    r.guarda = limiar_guarda(r) // 2
    anda(tela, 1.0)
    assert 0.4 < tela.guarda_vista[id(r)] < 0.6


# ----------------------------------------------------------------------- afixos e mecânicas


def test_elite_com_afixos_tem_selos_e_texto_no_painel():
    dicas = []
    j = _luta("elite")
    tela, _ = _tela(j, dicas)
    r = j.luta.rival
    r.afixos = ("vampirico", "espinhos")
    linhas = tela._status(r, None)
    assert [foco for foco, _t in linhas] == ["vampirico", "espinhos"]
    assert "Vampírico" in linhas[0][1]
    g = Gravador()
    tela.render(None, g)
    assert "吸" in g.textos and "棘" in g.textos
    tela.update(None, 1 / 60)
    assert "afixo" in dicas


def test_chefe_mostra_a_mecanica_e_a_roda_gira_quando_adapta():
    dicas = []
    j = _luta(chefe="general_da_roda")
    tela, _ = _tela(j, dicas)
    r = j.luta.rival
    assert r.mecanica == "adaptar"
    assert tela._rotulo_mecanica(r).startswith("輪 Adaptação")
    tela.update(None, 1 / 60)
    assert "mecanica" in dicas
    _usar(tela, "golpe_basico")
    anda(tela, 3)
    acao = _usar(tela, "golpe_basico")
    assert acao.mecanica == "adaptar"
    assert tela.casas_roda[id(r)] == 1
    assert "adaptou" in tela._rotulo_mecanica(r)


def test_aizen_iludiu_quebra_o_espelho_antes_do_golpe():
    j = _luta(chefe="flor_no_espelho")
    tela, _ = _tela(j)
    r = j.luta.rival
    tela._animar(Acao(r.nome, r.tecnicas[0].id, 4, alvo=j.jogador.nome, iludiu=True))
    assert tela.vidro is not None and tela.golpe[1] > tela.relogio
    assert tela.registro.startswith("鏡花水月")
    tela.render(None, Gravador())


def test_cada_mecanica_tem_reacao_sem_quebrar():
    for chefe, mecanica in (
        ("disparo_espiritual", "carregar"),
        ("dedo_que_aponta", "contrato"),
        ("estrela_que_prende", "repulsao"),
        ("desvio_dimensional", "intangivel"),
        ("guerreiro_esqueleto", "armadura"),
        ("lua_sem_fim", "preco"),
        ("luas_crescentes", "regenera"),
        ("balanca_da_obediencia", "balanca_virou"),
    ):
        j = _luta(chefe=chefe)
        tela, _ = _tela(j)
        r = j.luta.rival
        jogador_age = mecanica in ("contrato", "intangivel")
        ator, alvo = (j.jogador, r) if jogador_age else (r, j.jogador)
        tela._animar(Acao(ator.nome, "golpe_basico", 3, alvo=alvo.nome, mecanica=mecanica))
        assert tela.mec_fx and tela.mec_fx[-1][:2] == (mecanica, r), chefe
        for _ in range(6):
            tela.render(None, Gravador())
            anda(tela, 0.15)


# ----------------------------------------------------------------------- aliado e ressonância


def test_aliado_aparece_respira_e_age_com_animacao():
    j = _luta(aliado="raposa_rubra", nivel=3)
    tela, _ = _tela(j)
    assert tela.aliado is not None and tela.aliado.id == "raposa_rubra"
    tela.render(None, Gravador())
    acao = _usar(tela, "golpe_basico")
    assert acao.aliado and acao.aliado[0] == "raposa_rubra"
    efeito, inicio, alvo = tela.aliado_acao
    assert efeito == "ferir" and alvo is j.luta.rival
    assert tela.golpe[1] > inicio  # o golpe espera o aliado
    assert "Raposa Rubra" in tela.registro
    for _ in range(5):
        tela.render(None, Gravador())
        anda(tela, 0.1)


def test_sem_aliado_nada_aparece():
    tela, _ = _tela(_luta())
    assert tela.aliado is None
    _usar(tela, "golpe_basico")
    assert tela.aliado_acao is None


def test_ressonancias_ativas_aparecem_no_cabecalho():
    j = _luta()
    naruto = [
        f
        for f in j.ctx.tecnicas.values()
        if anime_de(f.origem) == "Naruto" and f.combate and f.combate.get("tipo") == "ataque"
    ]
    for f in naruto[:4]:
        j.jogador.tecnicas.append(Tecnica.de_fatia(f))
    tela, _ = _tela(j)
    from karmabound.ressonancia import ressonancias_ativas

    ativas = ressonancias_ativas(j.estado)
    assert ativas
    g = Gravador()
    tela.render(None, g)
    assert ativas[0].kanji in g.textos


# ----------------------------------------------------------------------- música


def test_a_musica_do_chefe_muda_na_segunda_forma():
    j = _luta(chefe="general_da_roda")
    tela, _ = _tela(j)
    assert tela._faixa() == "chefe"
    r = j.luta.rival
    r.vida = r.vida_max // 2 + 1
    acao = _usar(tela, "golpe_basico")
    assert acao.segunda_forma and tela._faixa() == "chefe_furia"


def test_fora_do_chefe_a_musica_e_a_de_sempre():
    tela, _ = _tela(_luta())
    assert tela._faixa() in ("luta", "luta_carma")


class AudioFalso:
    def __init__(self):
        self.faixas, self.volumes, self.paradas = [], [], []

    def load_sound(self, nome, caminho):
        pass

    def load_track(self, nome, caminho):
        pass

    def play_one_shot(self, nome, volume=1.0):
        pass

    def play_track(self, nome, start_offset_seconds=0.0, loop=False):
        self.faixas.append((nome, start_offset_seconds))

    def stop_track(self, nome):
        self.paradas.append(nome)

    def set_track_volume(self, v):
        self.volumes.append(v)

    def get_clock(self):
        class Relogio:
            def now_seconds(self):
                return 25.0

        return Relogio()


def test_a_passagem_baixa_troca_no_mesmo_compasso_e_sobe():
    s = som._Som()
    audio = AudioFalso()
    s.configurar(audio)
    assert {"chefe", "chefe_furia"} <= s.musicas
    s.musica("chefe")
    s.musica("chefe_furia", cruzar=1.0)
    assert audio.faixas == [("chefe", 0.0)]  # ainda não trocou
    s.atualizar(0.25)
    assert audio.volumes[-1] < 1.0
    s.atualizar(0.3)  # passou da metade: troca, no mesmo ponto do loop
    nome, onde = audio.faixas[-1]
    assert nome == "chefe_furia" and audio.paradas == ["chefe"]
    assert abs(onde - 25.0 % s.duracoes["chefe"]) < 1e-6
    s.atualizar(0.6)
    assert s.passagem is None and s.tocando == "chefe_furia"
    s.musica("chefe_furia", cruzar=1.0)  # a mesma: nada muda
    assert s.passagem is None
