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
        cena.assentar()  # as opções da escolha já no lugar
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
    """As telas da run: título, roleta da jornada, luta, caminho, troca, Altar e fim."""
    from karmabound import run
    from karmabound.combate import Tecnica
    from karmabound.jornada import Jornada
    from karmabound.legado import Fechamento
    from karmabound.run import oferecer_treinos
    from karmabound.tela_caminho import CaminhoScene, EncruzilhadaScene
    from karmabound.tela_luta import LutaScene
    from karmabound.tela_menus import (
        AltarScene,
        FimScene,
        SubstituirScene,
        TituloScene,
        TreinoScene,
    )
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
            cena.assentar()  # as cartas no lugar, a sequência do fim inteira
        loop.renderer.begin_frame()
        cena.render(None, loop.renderer)
        caminho = destino / f"{nome}.png"
        pygame.image.save(pygame.display.get_surface(), str(caminho))
        salvos.append(caminho)

    legado = ["Memória 14 · próximo anime em 4", "Nêmesis à espera: Ronin · Chidori"]
    foto(TituloScene(ent, nada, nada, legado=legado), "run_01_titulo")
    nemesis = {"nome": "Ronin · Chidori", "estilo": "espadachim", "tecnica": "", "vezes": 2}
    j = Jornada.nova("dificil", seed=11, nemesis=nemesis)
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
    if j.fase == "caminho":  # a primeira luta: a porta do Rival
        j.escolher_caminho([p.tipo for p in j.oferta_caminho].index("rival"))
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
    j.oferta_treino, j.fase = oferecer_treinos(j.ctx, j.rng), "treino"
    foto(TreinoScene(j, ent, nada, nada), "run_03f_treino", 0.4)

    # o caminho: um bando, uma encruzilhada e a Nêmesis à espera
    cam = j.ctx.caminho
    eventos = {e.id: e for e in cam.eventos}
    bando = cam.porta("bando", papeis=("lamina", "guardiao", "curandeiro"))
    j.estado.capitulo, j.estado.luta_no_capitulo = 2, 2
    j.jogador.vida = round(j.jogador.vida_max * 0.55)
    j.oferta_caminho = (
        bando,
        cam.porta("evento", evento=eventos["mercador"]),
        cam.porta("nemesis"),
    )
    j.fase = "caminho"
    foto(CaminhoScene(j, ent, nada, nada), "run_03g_caminho")
    j.carma.valor = 20  # o Carma não paga a troca do Mercador: a opção fica apagada
    j.encruzilhada, j.fase = eventos["mercador"], "encruzilhada"
    foto(EncruzilhadaScene(j, ent, nada, nada), "run_03h_encruzilhada", 0.1, ["baixo"])
    j.encruzilhada = None
    run.escolher_porta(j.estado, bando)
    j._comecar_luta()
    foto(LutaScene(j, ent, nada, nada), "run_03i_bando", 2.0)
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
    fechou = Fechamento(
        memoria=24,
        animes=["Attack on Titan"],
        maestrias=[("Chidori", 1), ("Rasengan", 2)],
        nemesis="vingada",
        nemesis_nome="Ronin · Chidori",
    )
    foto(FimScene(j, ent, nada, nada, fechamento=fechou, proximo=("Berserk", 4)), "run_08_fim")
    j.fase = "derrota"
    j.estado.lutas_vencidas = 5
    caiu = Fechamento(memoria=7, nemesis="nasceu", nemesis_nome="Monge Errante · Punho Sagrado")
    foto(
        FimScene(j, ent, nada, nada, fechamento=caiu, proximo=("Berserk", 3)), "run_08b_fim_derrota"
    )
    loop.renderer.shutdown()
    return salvos


def capturar_sistemas(destino: Path) -> list[Path]:
    """As telas dos sistemas novos fora da luta: o anúncio de fusão (o Roxo), os selos de
    combo na roleta e na troca, o mapa do caminho, a Ascensão no título e no fim, o
    Grimório das fusões, o build na pausa e o aliado que chega."""
    from karmabound.grimorio import Grimorio
    from karmabound.jornada import Jornada
    from karmabound.legado import Fechamento
    from karmabound.mesa import Giro
    from karmabound.run import Contexto, aplicar_dom, criar_tecnica
    from karmabound.tela_caminho import CaminhoScene
    from karmabound.tela_grimorio import ORDEM_RODAS, GrimorioScene
    from karmabound.tela_menus import (
        AliadoScene,
        FimScene,
        FusaoScene,
        SubstituirScene,
        TituloScene,
    )
    from karmabound.tela_pausa import PausaScene
    from karmabound.tela_roleta import RoletaScene

    class Entrada:
        apertadas: set = set()

        def is_action_pressed(self, a):
            return a in self.apertadas

    destino.mkdir(parents=True, exist_ok=True)
    loop = build_game(seed=3)
    ent = Entrada()
    nada = lambda *a, **k: None  # noqa: E731
    salvos: list[Path] = []

    def foto(cena, nome, assentar=True):
        if assentar:
            cena.relogio = max(cena.relogio, 2.0)
            cena.assentar()
        loop.renderer.begin_frame()
        cena.render(None, loop.renderer)
        caminho = destino / f"{nome}.png"
        pygame.image.save(pygame.display.get_surface(), str(caminho))
        salvos.append(caminho)

    # uma run com o Seis Olhos, um aliado e a Ascensão 3
    j = Jornada.nova("dificil", seed=11, ascensao=3)
    j.grimorio = Grimorio()  # só em memória
    j.girar_linhagem()
    j.girar_destino()
    dons = {f.id: f for f in j.ctx.rodas["destino"].fatias}
    aplicar_dom(j.estado, j.ctx, dons["olhos_que_tudo_veem"])
    j.fusoes_novas.clear()
    j.fila_fusao.clear()
    j.retomar, j.pendente, j.fase = "", None, "arco"
    j.girar_arco()
    tec = j.ctx.tecnicas

    # o Roxo: os Seis Olhos e o Despertar do Vazio Infinito
    j.estado.despertares_ids.append("vazio_infinito")
    j._fundir("treino")
    fusao = FusaoScene(j, list(j.fusoes_novas), ent, nada, nada)
    j.fusoes_novas.clear()
    fusao.t_seq = 0.35  # as peças entrando
    fusao.relogio = 1.0
    foto(fusao, "sis_01a_fusao_pecas", assentar=False)
    fusao.t_seq = 1.05  # o clarão
    foto(fusao, "sis_01b_fusao_clarao", assentar=False)
    foto(fusao, "sis_01c_fusao_roxo")

    # a mão: três técnicas de Naruto (Ressonância) e a Foice de Vento (peça da Shuriken)
    jg = j.jogador
    jg.tecnicas[:] = [jg.tecnicas[0]] + [
        criar_tecnica(j.ctx, tec[i]) for i in ("golpe_de_vento", "investida", "clones_de_sombra")
    ]
    j.grimorio.marcar("fusoes", ["shuriken"])  # a Shuriken já foi descoberta noutra run
    j.estado.aliado, j.estado.aliado_nivel = "raposa_rubra", 3
    from karmabound.run import atualizar_efeitos

    atualizar_efeitos(j.estado)

    # a roleta de Técnicas com os selos 融 e 共
    giro = Giro(
        j.ctx.rodas["tecnicas"],
        [tec["espiral_concentrada"], tec["mil_clones"], tec["lamina_de_sangue"]],
    )
    roleta = RoletaScene(
        j.estado.mesa,
        ent,
        nada,
        "tecnicas",
        lambda: giro,
        nada,
        titulo="Uma técnica nova",
        jornada=j,
    )
    roleta._comecar_giro()
    roleta.apressar = True
    for _ in range(400):
        roleta.update(None, 1 / 60)
        if roleta.estado == "escolhendo":
            break
    foto(roleta, "sis_02_roleta_selos")

    # a troca: tirar uma de Naruto desfaz a Ressonância; a Foice é peça da Shuriken
    j.pendente, j.fase = tec["lamina_de_sangue"], "substituir"
    troca = SubstituirScene(j, ent, nada, nada)
    troca.cursor = 1
    foto(troca, "sis_03_substituir_perda")

    # o caminho com o mapa (uma elite agora; depois, três portas) e o canto do build
    cam = j.ctx.caminho
    eventos = {e.id: e for e in cam.eventos}
    j.oferta_caminho = (
        cam.porta("rival"),
        cam.porta("elite"),
        cam.porta("evento", evento=eventos["mercador"]),
    )
    j.estado.proximas_portas = (
        cam.porta("rival"),
        cam.porta("bando", papeis=("lamina", "curandeiro")),
        cam.porta("evento", evento=eventos["forja"]),
    )
    j.estado.capitulo, j.estado.luta_no_capitulo = 2, 2
    j.fase = "caminho"
    caminho = CaminhoScene(j, ent, nada, nada)
    caminho.cursor = 1
    foto(caminho, "sis_04a_caminho_mapa")
    j.estado.proximas_portas = ()
    j.estado.luta_no_capitulo = 3
    foto(CaminhoScene(j, ent, nada, nada), "sis_04b_caminho_chefe_depois")

    # a pausa por cima do caminho: o build
    if "roxo" not in j.estado.fusoes_nascidas:
        j.estado.fusoes_nascidas.append("roxo")
    pausa = PausaScene(caminho, j, ent, nada, nada, None)
    foto(pausa, "sis_05_pausa_build")

    # o aliado chega
    from karmabound.aliados import aliado

    chegou = AliadoScene(
        j, aliado("raposa_rubra"), ent, nada, nada, "Quem a elite mantinha preso agora segue você."
    )
    foto(chegou, "sis_06_aliado")

    # o título: Difícil com a Ascensão aberta até a 5, escolhendo a 4
    titulo = TituloScene(ent, nada, nada, ascensoes={"dificil": 5, "equilibrado": 2})
    titulo.cursor = [x[0] for x in titulo.itens].index("dificil")
    foto(titulo, "sis_07a_titulo_dificuldades")
    titulo.modo_asc, titulo.nivel_asc, titulo.t_asc = "dificil", 4, 1.0
    foto(titulo, "sis_07b_titulo_ascensao")
    titulo.nivel_asc = 0
    foto(titulo, "sis_07c_titulo_ascensao_zero")

    # o Grimório das fusões: o Roxo descoberto, outra ainda escondida
    g = Grimorio()
    g.ver([tec["espiral_concentrada"]])
    g.marcar("fusoes", ["roxo", "shuriken"])
    g.marcar("aliados", ["raposa_rubra"])
    g.marcar("afixos", ["vampirico"])
    grim = GrimorioScene(g, ent, nada, nada, ctx=Contexto.padrao())
    grim.i_roda = ORDEM_RODAS.index("fusoes")
    foto(grim, "sis_08a_grimorio_fusao")
    grim.cursor = [e.id for e in grim.lista].index("chuva_de_espirais")
    foto(grim, "sis_08b_grimorio_fusao_escondida")
    grim.i_roda, grim.cursor = ORDEM_RODAS.index("aliados"), 3
    foto(grim, "sis_08c_grimorio_aliados")

    # o fim com a Ascensão aberta
    j.fase = "vitoria"
    j.estado.lutas_vencidas = 12
    fechou = Fechamento(memoria=24, ascensao_aberta=4, maestrias=[("Rasengan", 1)])
    foto(
        FimScene(j, ent, nada, nada, fechamento=fechou, proximo=("Berserk", 4)),
        "sis_09_fim_ascensao",
    )
    loop.renderer.shutdown()
    return salvos


if __name__ == "__main__":
    # python tools/capturar_telas.py [pasta] [sistemas]: "sistemas" captura só as telas novas
    padrao = Path(__file__).resolve().parent.parent / "docs" / "telas"
    pasta = Path(sys.argv[1]) if len(sys.argv) > 1 else padrao
    if sys.argv[2:] == ["sistemas"]:
        fotos = capturar_sistemas(pasta)
    else:
        fotos = capturar(pasta) + capturar_run(pasta) + capturar_sistemas(pasta)
    for p in fotos:
        print(p)
