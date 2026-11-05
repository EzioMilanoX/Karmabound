"""Tela de luta: duelo frente a frente, rival em cima, você embaixo.

Só apresentação: cada ação passa pela `Luta` (regras) na hora em que é escolhida,
e a tela anima o `Acao` que voltou. Enquanto uma animação toca, a entrada fica
travada; o rival age sozinho depois de uma pausa curta.

Num bando (2 ou 3 rivais) eles ficam lado a lado, menores, cada um com a própria
placa (papel, vida, sinais e o que vai fazer). O alvo do jogador (`Luta.rival`) tem
o ensō dourado e a pincelada sob os pés; ↑ ↓ ou Tab trocam o alvo.

Em campo, ao lado de cada dono: as invocações (`Criatura`, uma por entrada de
`Lutador.invocacoes`: surgem da tinta, respiram, dão o bote no começo do turno do
dono e se desfazem quando o tempo delas acaba) e os clones (`Clone`: cópias
translúcidas que avançam junto e somem numa nuvem quando absorvem um golpe).
Golpe forte congela a cena um instante (hit-stop) com um clarão branco no alvo.
Segurar Enter (ou Shift / X do controle) acelera as animações e o turno dos rivais.

O cinema da luta: técnica Maldita/Divina, fusão ou assinatura de chefe abre com um
cut-in (a faixa diagonal com o kanji, o nome e a silhueta em pose; uma vez por técnica
por luta, menos as fusões); o golpe forte dá um punch-in na câmera (só o mundo: as
placas e barras ficam paradas) e os golpes rápidos, linhas de velocidade; intenção
perigosa acende as bordas e o rival que vai usá-la. Sob a vida de cada rival, a barra
de guarda (崩 quando quebra, e ele fica tonto); afixos e a mecânica do chefe têm selo e
reação própria; o aliado luta ao seu lado; as ressonâncias ficam no seu cabeçalho; e a
música do chefe muda na segunda forma.
"""

from __future__ import annotations

import math
from dataclasses import dataclass

from ouroboros.bootstrap.scene import IScene
from ouroboros.interfaces.input_provider import IInputProvider
from ouroboros.interfaces.renderer import IRenderer

from karmabound import som, transicoes, vfx
from karmabound.arenas import desenhar_arena, desenhar_frente
from karmabound.combate import (
    FRAQUEZA_MAXIMA,
    FRAQUEZA_POR_DOSE,
    HESITAR,
    Acao,
    Luta,
    Lutador,
    Tecnica,
    _extra_da_dor,
    limiar_guarda,
)
from karmabound.figuras import (
    ESTILOS,
    criatura_de,
    desenhar_aliado,
    desenhar_criatura,
    desenhar_lutador,
    medidas_aliado,
    medidas_criatura,
)
from karmabound.fusoes import carregar_fusoes, tecnicas_de_fusao
from karmabound.jornada import Jornada
from karmabound.opcoes import OPCOES
from karmabound.ressonancia import ressonancias_ativas
from karmabound.rodas import carregar_mecanicas
from karmabound.run import espacos
from karmabound.visual import (
    ALTURA,
    FERRO,
    FONTE_PINCEL,
    FUNDO,
    LACA,
    LARGURA,
    OURO,
    SANGUE_VIVO,
    TINTA,
    VERDE_JADE,
    Cor,
    alpha,
    ease_out,
    hex_cor,
    mistura,
    quebrar,
)

DURACAO_ACAO = 0.6
DURACAO_ENTRADA = 1.7  # a entrada do rival (o chefe demora mais)
DURACAO_ENTRADA_CHEFE = 2.6
DURACAO_FIM = 1.3  # o rival se desfaz, ou as correntes se fecham
DURACAO_DESPERTAR = 1.6
PAUSA_RIVAL = 0.35

# o impacto: quando o golpe acerta (contado do começo da ação), o congelamento do
# golpe forte (hit-stop) e quanto tempo o alvo fica branco
IMPACTO = 0.13
HITSTOP, HITSTOP_CRITICO = 0.07, 0.1
CLARAO_BRANCO = 0.09
ACELERAR = 3.0  # segurando Enter / Shift / X: tudo corre 3× (por cima da velocidade das opções)
RASTRO_SEGURA, RASTRO_SOME = 0.4, 0.45  # o branco do dano recente na barra de vida

# as invocações em campo
DURACAO_SURGIR = 0.55
DURACAO_PARTIR = 0.6
DURACAO_BOTE = 0.5  # vai, morde e volta
BOTE_IMPACTO = 0.42  # em que fração do bote ela acerta
PASSO_BOTE = 0.17  # uma depois da outra
DURACAO_MORDIDA = 0.3
# (dx, dy a partir dos pés do dono, escala): duas ao lado, a terceira atrás (mais acima)
LUGAR_INV_JOGADOR = ((-94, 6, 0.62), (142, 8, 0.62), (152, -80, 0.5))
LUGAR_INV_RIVAL = ((-104, 14, 0.6), (108, 14, 0.6), (-184, -14, 0.5))
LUGAR_INV_BANDO = ((-66, 4, 0.46), (66, 4, 0.46), (-34, -24, 0.4))  # no trio; a dupla aumenta
COR_CRIATURA = {  # a cor da mordida e do pó quando vai embora
    "sapo": (206, 130, 74, 255),
    "cao": (236, 230, 218, 255),
    "ave": (255, 220, 110, 255),
    "roda": (214, 180, 104, 255),
    "soldado": (120, 190, 255, 255),
    "broto": (110, 168, 130, 255),
    "shikigami": (216, 207, 192, 255),
}
# os clones: quantos aparecem (o resto vira "+N") e onde, a partir dos pés do dono
CLONES_VISIVEIS = 4
LUGAR_CLONE_JOGADOR = ((-60, -16), (54, -16), (-110, -30), (86, -34))
LUGAR_CLONE_RIVAL = ((-64, -10), (64, -10), (-116, -20), (116, -20))
DURACAO_POOF = 0.45

# o cinema: o cut-in (técnica Maldita/Divina, fusão, assinatura de chefe), o punch-in
# da câmera no golpe forte, as linhas de velocidade e a passagem da música do chefe
DURACAO_CUTIN = 0.6
RARIDADES_CUTIN = ("maldito", "divino")
DURACAO_ZOOM, ZOOM_SOBE = 0.42, 0.06
ZOOM_FORTE, ZOOM_CRITICO = 0.07, 0.1
DURACAO_VELOZ = 0.36
EFEITOS_VELOZES = {"investida", "trovao", "punho", "vento", "trovao_flamejante", "raio_na_mao"}
PASSAGEM_FURIA = 1.6
# a guarda, as mecânicas de chefe, o espelho do Aizen e o empurrão do Pain
KANJI_QUEBRA = "崩"
COR_GUARDA = (170, 190, 215, 255)
DURACAO_QUEBRA = 0.75
DURACAO_MECANICA = 0.95
DURACAO_VIDRO = 0.9
DURACAO_EMPURRAO = 0.5
MEC_NO_IMPACTO = {"adaptar", "contrato", "intangivel", "balanca", "balanca_virou"}
MEC_COMECO = {"armadura", "repulsao", "regenera"}  # o começo do turno dele
MEC_REGISTRO = {
    "adaptar": "a roda girou: ele se adaptou ao golpe",
    "armadura": "a armadura se renovou",
    "repulsao": "tudo foi empurrado: clones, invocações e bloqueio",
    "intangivel": "o golpe atravessou o corpo dele",
    "preco": "a Lua Sem Fim cobrou o preço: o dano dele cai à metade",
    "regenera": "ele se regenerou",
    "contrato": "o contrato desviou o golpe para outro lugar",
    "balanca": "a Balança pesou: quem tem menos vida obedece",
    "balanca_virou": "a Balança virou contra ele: perde o turno e enfraquece",
    "carregar": "o Disparo saiu carregado",
}
MEC_SOM = {
    "adaptar": "roda",
    "armadura": "defesa",
    "repulsao": "critico",
    "intangivel": "tempo",
    "preco": "maldita",
    "regenera": "cura",
    "contrato": "corrente",
    "balanca": "maldita",
    "balanca_virou": "corrente",
    "carregar": "raio",
}
COR_MECANICA = {"contrato": SANGUE_VIVO, "regenera": VERDE_JADE, "intangivel": (200, 190, 230, 255)}
# o aliado: ao lado dos seus pés, à direita; com ele em campo, as invocações abrem lugar
DURACAO_ALIADO = 0.55
ALIADO_IMPACTO = 0.42
LUGAR_ALIADO = (132, 8, 0.62)
LUGAR_INV_JOGADOR_ALIADO = ((-94, 6, 0.62), (198, 10, 0.56), (152, -80, 0.5))
COR_ALIADO = {
    "ferir": (255, 120, 60, 255),
    "expor": OURO,
    "envenenar": (180, 130, 230, 255),
    "curar": VERDE_JADE,
    "bloquear": (150, 200, 240, 255),
}
FEITO_ALIADO = {
    "ferir": "mordeu: {v}",
    "expor": "achou o ponto fraco",
    "envenenar": "envenenou ({v})",
    "curar": "curou {v}",
    "bloquear": "ergueu bloqueio {v}",
}

POS_RIVAL = (480, 282)
# o bando: lado a lado, à esquerda do painel da intenção (x >= 646)
POS_BANDO = {2: ((270, 286), (500, 286)), 3: ((160, 290), (350, 290), (540, 290))}
ESCALA_BANDO = {2: 0.8, 3: 0.72}
PLACA_Y = 92  # o nome de cada rival do bando; a barra e os sinais logo abaixo
POS_JOGADOR = (150, 626)
SELO_Y = 500
TIPOS_VOTO = {"promessa": "Promessa", "revelacao": "Revelação", "selo": "Selo"}
CONDICAO = {
    "vencer_em": "vencer em {} turnos seus",
    "sem_dano": "não ser ferido por {} turnos dele",
    "so_golpe": "só o Golpe por {} turnos",
    "sem_defesa": "não defender até o fim",
    "dano_em": "causar {meta} de dano ({} turnos)",
}
SELO_X0 = 372
SELO_PASSO = 104
RAIO_SELO = 30

KANJI_BASICO = "打"
KANJI_HESITAR = "躊"
NOMES_TIPO = {
    "ataque": "um ATAQUE",
    "defesa": "uma DEFESA",
    "maldita": "algo MALDITO",
    "modo": "uma TRANSFORMAÇÃO",
}
TIPO_CURTO = {"ataque": "ATAQUE", "defesa": "DEFESA", "maldita": "MALDITA", "modo": "FORMA"}
KANJI_BANDO, KANJI_ELITE, KANJI_NEMESIS = "群", "強", "仇"
KANJI_PROTEGIDO = "盾"
SANGUE_NEMESIS = (170, 24, 40, 255)  # a cor de quem já te matou


def _sinais_leva3(lutador, longo: bool = False) -> list[str]:
    """Os estados da Leva 3: chama, veneno, gelo, clones, invocações, ritual, forma."""
    s = []
    if lutador.chama:
        s.append(f"炎 chama {lutador.chama}" if longo else f"炎{lutador.chama}")
    if lutador.veneno:
        fraco = round(100 * min(FRAQUEZA_MAXIMA, FRAQUEZA_POR_DOSE * lutador.veneno))
        s.append(f"毒 veneno {lutador.veneno} (-{fraco}% dano)" if longo else f"毒{lutador.veneno}")
    if lutador.congelado:
        s.append("氷 congelado" if longo else "氷")
    if lutador.clones:
        s.append(f"影 clones {lutador.clones}" if longo else f"影{lutador.clones}")
    if lutador.invocacoes:
        n = len(lutador.invocacoes)
        s.append(f"召 invocação ×{n}" if longo else f"召{n}")
    if lutador.vinculo:
        s.append(f"儀 ritual {lutador.vinculo}" if longo else "儀")
    if lutador.adiado:
        s.append(f"鎧 adiado {lutador.adiado}" if longo else f"鎧{lutador.adiado}")
    if not longo and lutador.modo is not None:
        s.append(f"変{lutador.modo_turnos}")
    return s


ROMANOS = ("I", "II", "III", "IV", "V")
ESCALA_JOGADOR = 1.2
NOME_ESTILO = {
    "espadachim": "Ronin",
    "monge": "Monge Errante",
    "ninja": "Shinobi",
    "oni": "Oni",
    "hollow": "Hollow",
    "tita": "Titã",
}
KANJI_ESTILO = {
    "espadachim": "浪",
    "monge": "僧",
    "ninja": "忍",
    "oni": "鬼",
    "hollow": "虚",
    "tita": "巨",
    "colosso": "魔",
}
COR_ESTILO = {
    "espadachim": (60, 22, 24, 255),
    "monge": (62, 44, 24, 255),
    "ninja": (30, 32, 44, 255),
    "oni": (74, 18, 16, 255),
    "colosso": (44, 14, 34, 255),
    "hollow": (40, 40, 46, 255),
    "tita": (110, 62, 54, 255),
}


@dataclass
class Texto:
    """Número ou palavra que sobe e some (dano, 'percebeu!', 'surpresa!').

    `inicio` pode estar no futuro (o número do golpe espera o impacto). `pop`: o
    número estoura (cresce, passa do ponto e assenta) antes de subir."""

    x: float
    y: float
    texto: str
    cor: Cor
    inicio: float
    tamanho: int = 30
    pop: bool = False
    sobe: float = 36.0


@dataclass(eq=False)
class Criatura:
    """Uma invocação em campo: a tela acompanha cada entrada de `Lutador.invocacoes`."""

    dono: Lutador
    origem: str
    dano: int
    turnos: int  # quantos botes ainda dá
    lugar: int  # 0 e 1 ao lado do dono, 2 atrás
    nasce: float
    parte: float | None = None  # quando começa a se desfazer
    bote: tuple[float, Lutador] | None = None  # (início, alvo) do último ataque


@dataclass(eq=False)
class Clone:
    """Uma cópia do dono em campo (`Lutador.clones` diz quantas)."""

    dono: Lutador
    lugar: int
    nasce: float
    parte: float | None = None  # quando estoura na nuvem


def _volta(x: float) -> float:
    """Easing que passa do ponto e volta (0 → ~1,25 → 1): o 'pop' dos números."""
    x = max(0.0, min(1.0, x))
    c1 = 3.0
    return 1 + (c1 + 1) * (x - 1) ** 3 + c1 * (x - 1) ** 2


def _vai_e_volta(k: float, impacto: float, segura: float = 0.12) -> float:
    """0 → 1 até o `impacto`, segura um instante e volta a 0 (o bote, o avanço)."""
    if k <= 0 or k >= 1:
        return 0.0
    if k < impacto:
        x = k / impacto
        return x * x * (3 - 2 * x)
    if k < impacto + segura:
        return 1.0
    return 1 - ease_out((k - impacto - segura) / max(1e-6, 1 - impacto - segura))


class LutaScene(IScene):
    def __init__(
        self, jornada: Jornada, entrada: IInputProvider, ao_terminar, ao_sair, ao_dica=None
    ) -> None:
        self.j = jornada
        self.ao_dica = ao_dica or (lambda _id: None)  # dicas da primeira run (o Fluxo decide)
        self.luta: Luta = jornada.luta
        self.entrada = entrada
        self.ao_terminar = ao_terminar  # chamado com venceu: bool depois do banner
        self.ao_sair = ao_sair
        self.relogio = 0.0
        self.entrada_ate = DURACAO_ENTRADA_CHEFE if self.luta.rival.chefe else DURACAO_ENTRADA
        self.anim_ate = self.entrada_ate  # ninguém age durante a entrada do rival
        self.proxima_rival = self.entrada_ate + PAUSA_RIVAL
        self.fim_inicio: float | None = None
        self.manchas: list[tuple[float, float, float, float]] = []  # o sangue no chão, até o fim
        self.primeiro_quadro = True
        self.cursor = 1 if self.j.jogador.tecnicas else 0
        self.modo = "escolher"  # escolher | sacrificio | fim
        self.contrato: Tecnica | None = None
        self.textos: list[Texto] = []
        self.golpe: tuple[Lutador, float] | None = None  # quem avança e quando
        self.tremor: dict[int, float] = {}  # id(lutador) -> início do tremor
        self.vida_vista = {id(lut): lut.vida for lut in (self.j.jogador, *self.luta.rivais)}
        self.morte: dict[int, float] = {}  # id(rival) -> quando caiu (o bando segue lutando)
        self.aviso = ""
        self.aviso_ate = 0.0
        self.desperto: tuple[object, float] | None = None  # (fatia, início) da cena do Despertar
        # o efeito tocando: (nome, quem age, quem recebe, início, crítico)
        self.efeito: tuple[str, Lutador, Lutador, float, bool] | None = None
        self.bando = len(self.luta.rivais) > 1
        self.caminho = getattr(jornada.ctx, "caminho", None)  # None no Desfile de chefes
        calculado = ESTILOS[(jornada.n_luta * 5 + jornada.capitulo) % len(ESTILOS)]
        self.estilos = {  # a figura de cada rival (o motor preenche; senão, pela luta)
            id(r): r.estilo or ("colosso" if r.chefe else calculado) for r in self.luta.rivais
        }
        self.estilo_rival = self.estilos[id(self.luta.rival)]
        if self.luta.vez is self.j.jogador:
            self.registro = "A luta começa."
        else:
            self.registro = f"{self._quem(self.luta.vez)} se move primeiro."
        if jornada.aviso:  # o que aconteceu com a técnica do último giro
            self.registro = f"{jornada.aviso} · {self.registro}"
            jornada.aviso = ""
        cores = {r.id: hex_cor(r.cor) for r in jornada.ctx.raridades}
        fatias = jornada.ctx.tecnicas
        dons = {f.id: f for f in jornada.ctx.rodas["destino"].fatias}
        dons.update({f.id: f for f in jornada.ctx.rodas["linhagem"].fatias})
        self.kanji = {tid: f.kanji for tid, f in {**fatias, **dons}.items()}
        self.cor_raridade = cores
        self.kanji[jornada.ctx.basico.id] = KANJI_BASICO
        self.kanji[HESITAR.id] = KANJI_HESITAR
        # nomes pelo catálogo: uma técnica destruída pelo Contrato some da lista do lutador
        self.nomes = {tid: f.nome for tid, f in {**fatias, **dons}.items()}
        self.nomes[jornada.ctx.basico.id] = jornada.ctx.basico.nome
        self.nomes[HESITAR.id] = HESITAR.nome
        todas = [f for roda in jornada.ctx.rodas.values() for f in roda.fatias]
        todas += list(jornada.ctx.chefes)
        self.origens = {f.id: f.origem for f in todas}
        for f in jornada.ctx.chefes:  # a técnica-assinatura do chefe
            self.kanji[f.id], self.nomes[f.id] = f.kanji, f.nome
        for f in tecnicas_de_fusao().values():  # as que só nascem de fusão (as rodas valem antes)
            self.kanji.setdefault(f.id, f.kanji)
            self.nomes.setdefault(f.id, f.nome)
            self.origens.setdefault(f.id, f.origem)
        self.fusoes = {f.fatia.id for f in carregar_fusoes()}  # o cut-in delas não cansa
        self.mecanicas = carregar_mecanicas()
        for r in self.luta.rivais:  # as técnicas de papel (Guardar, Bênção...) não estão nas rodas
            papel = self._papel(r)
            for t in r.tecnicas:
                if t.id not in self.kanji:
                    self.kanji[t.id] = papel.kanji if papel is not None else "?"
                    self.nomes[t.id] = t.nome
        ids = {t.id for r in self.luta.rivais for t in r.tecnicas}
        self.assinatura = next((f for f in jornada.ctx.chefes if f.id in ids), None)
        if self.assinatura is not None and jornada.grimorio is not None:
            jornada.grimorio.ver([self.assinatura])
        self.origens[jornada.ctx.basico.id] = jornada.ctx.combate["golpe_basico"].get("origem", "")
        self.promessa_vista = ""  # para anunciar quando a promessa se cumpre ou se quebra
        # o impacto: força do tremor de cada um, o hit-stop e o clarão branco no alvo
        self.forca_tremor: dict[int, float] = {}
        self.parada: tuple[float, float] | None = None  # (quando congela, por quanto tempo)
        self.congelado = 0.0  # quanto do hit-stop ainda falta
        self.flash: tuple[Lutador, float, bool] | None = None  # (alvo, quando, crítico)
        self.acelerando = False
        self.sons: list[tuple[float, str, float]] = []  # sons que esperam o impacto
        self.rastro: dict[int, tuple[float, float]] = {}  # id -> (de onde a vida caiu, quando)
        self.vida_antes = {id(lut): lut.vida for lut in self._todos()}  # a vida que a barra mostra
        self.segura_barra_ate = 0.0  # a barra espera o primeiro impacto da ação
        # quem está em campo além dos lutadores
        self.criaturas: list[Criatura] = []
        self.clones_em_campo: list[Clone] = []
        self.nuvens: list[tuple[float, float, float, float]] = []  # (x, y, início, escala)
        self.mordidas: list[tuple[Lutador, float, Cor]] = []  # (alvo, início, cor)
        self.clones_atacam: tuple[Lutador, float] | None = None  # (dono, início)
        self.fase = {id(lut): 0.9 + 1.7 * i for i, lut in enumerate(self.luta.rivais)}
        self.fase[id(self.j.jogador)] = 0.0  # cada um respira no seu ritmo
        # o cinema: cut-in, câmera, linhas de velocidade, perigo
        self.cutin: tuple[dict, float] | None = None  # (o que mostra, quando começa)
        self.cutins_vistos: set[tuple[bool, str]] = set()  # (do rival?, técnica)
        self.zoom: tuple[float, float, Lutador] | None = None  # (quando, força, em quem)
        self.velozes: tuple[float, Lutador] | None = None  # (quando, para onde)
        self.perigo: list[Lutador] = []  # quem anuncia golpe perigoso (o render calcula)
        # a guarda, as mecânicas de chefe e o espelho
        self.guarda_vista = {id(r): 0.0 for r in self.luta.rivais}
        self.quebras: list[tuple[Lutador, float]] = []
        self.mec_fx: list[tuple[str, Lutador, float]] = []  # (mecânica, chefe, quando)
        self.vidro: tuple[float, Lutador] | None = None  # Aizen: o anúncio era isca
        self.empurrao: float | None = None  # Pain: quando a tela é empurrada
        self.casas_roda: dict[int, int] = {}  # Mahoraga: quantas casas a roda já girou
        self.giro_visto: dict[int, float] = {}
        self.foco_status = ""  # o afixo cujo texto está no painel (o selo dele acende)
        self.viu_quebra = False  # para a dica da guarda
        # o aliado (luta do seu lado; a Luta o recebe de run.comecar_luta)
        self.aliado = getattr(self.luta, "aliado", None)
        self.aliado_nivel = getattr(self.luta, "aliado_nivel", 1)
        self.aliado_acao: tuple[str, float, Lutador] | None = None  # (efeito, quando, alvo)
        # quem já começa com invocação ou clones: surgem logo depois do rival
        self._acompanhar(nasce=self.entrada_ate * 0.55)

    # --------------------------------------------------------------- slots

    def slots(self) -> list[Tecnica | None]:
        """Selo 1 = Golpe (ou Hesitar); depois os espaços; e as técnicas do Dom e da Linhagem."""
        j = self.j.jogador
        prontas = self.luta.prontas(j)
        primeiro = HESITAR if prontas == [HESITAR] else self.luta.basico
        tecnicas = list(j.tecnicas)
        vazios = [None] * max(0, espacos(self.j.estado, self.j.ctx) - len(tecnicas))
        extras = [t for t in (j.tecnica_dom, j.tecnica_linhagem) if t is not None]
        return [primeiro] + tecnicas + vazios + extras

    def _pos_selo(self, i: int, n: int) -> float:
        x0 = SELO_X0 if n <= 6 else 330
        passo = min(SELO_PASSO, (935 - x0) / max(1, n - 1))
        return x0 + i * passo

    def _disponivel(self, t: Tecnica | None) -> bool:
        return t is not None and t in self.luta.prontas(self.j.jogador)

    def _motivo_indisponivel(self, t: Tecnica) -> str:
        j = self.j.jogador
        if j.pular:
            return "você perde este turno"
        if t.copia_rival and self.luta.ultima_tecnica(self.luta.rival) is None:
            return "o rival ainda não usou nada para roubar"
        if t.tipo in j.efeitos.proibir_tipos or (
            t is self.luta.basico and j.efeitos.proibir_basico
        ):
            return "proibido pelo seu voto"
        if t.tipo in j.proibir_luta or (t is self.luta.basico and j.sem_basico_luta):
            return "selado pelo voto de luta"
        if j.silencio:
            return f"silenciado ({j.silencio}): só o Golpe"
        if j.desarme and t.tipo == "defesa":
            return f"desarmado ({j.desarme}): sem defesa"
        if j.recargas.get(t.id, 0):
            return f"em recarga ({j.recargas[t.id]})"
        if t.consome_tecnica:
            return "o pacto exige outra técnica para sacrificar"
        return "indisponível"

    # --------------------------------------------------------------- lógica

    def _avisar(self, texto: str) -> None:
        self.aviso, self.aviso_ate = texto, self.relogio + 1.6

    def _nome(self, tid: str) -> str:
        rivais = [t for r in self.luta.rivais for t in r.tecnicas]
        for t in [*self.j.jogador.tecnicas, *rivais]:
            if t.id == tid:
                return t.nome  # com o nível, se evoluiu
        return self.nomes.get(tid, tid)

    # --------------------------------------------------------------- o bando

    def _papel(self, r: Lutador):
        """O papel de um rival do bando (nome, kanji, texto), ou None."""
        if self.caminho is None or not r.papel:
            return None
        return self.caminho.papeis.get(r.papel)

    def _quem(self, r: Lutador) -> str:
        """Quem agiu, para o registro: 'Você', 'O rival' ou o título no bando."""
        if r is self.j.jogador:
            return "Você"
        return (r.titulo or r.nome) if self.bando else "O rival"

    def _titulo(self, r: Lutador) -> str:
        """O nome do rival na tela."""
        estilo = NOME_ESTILO.get(self.estilos[id(r)], "Rival")
        if r.chefe:
            return "Chefe do capítulo"
        if r.nemesis:
            return f"{KANJI_NEMESIS} {r.titulo or r.nome}"
        if self.bando:
            return r.titulo or r.nome
        if r.titulo:  # a elite sozinha: "Elite 5 · Ronin"
            return f"{r.titulo} · {estilo}"
        return f"{estilo} · Rival {self.j.n_luta}"

    def _foto(self) -> dict[int, tuple[int, int]]:
        """Vida e bloqueio de cada rival antes de uma ação: quanto o Curandeiro fechou,
        quanto o Guardião ergueu e quem caiu (quem e o respingo vêm na própria `Acao`)."""
        return {id(r): (r.vida, r.bloqueio) for r in self.luta.rivais}

    def _todos(self) -> tuple[Lutador, ...]:
        return (self.j.jogador, *self.luta.rivais)

    # --------------------------------------------------------------- quem está em campo

    def _acompanhar(self, nasce: float | None = None, some: float | None = None) -> None:
        """Põe em campo (ou tira) as invocações e os clones de cada um, pelo estado da
        luta. `nasce`: quando as novas surgem; `some`: quando os clones perdidos estouram
        (o impacto do golpe que eles absorveram)."""
        nasce = self.relogio if nasce is None else nasce
        some = self.relogio if some is None else some
        for lut in self._todos():
            self._acompanhar_invocacoes(lut, nasce)
            self._acompanhar_clones(lut, nasce, some)
        t = self.relogio
        self.criaturas = [
            c for c in self.criaturas if c.parte is None or t < c.parte + DURACAO_PARTIR
        ]
        self.clones_em_campo = [
            c for c in self.clones_em_campo if c.parte is None or t < c.parte + DURACAO_POOF
        ]
        self.nuvens = [n for n in self.nuvens if t < n[2] + DURACAO_POOF]
        self.mordidas = [m for m in self.mordidas if t < m[1] + DURACAO_MORDIDA]

    def _acompanhar_invocacoes(self, lut: Lutador, nasce: float) -> None:
        """Casa as criaturas com `lut.invocacoes` na ordem (as novas entram no fim; as
        que expiram ou o limite manda embora saem de qualquer ponto)."""
        entradas = lut.invocacoes if lut.vivo else []
        vivas = [c for c in self.criaturas if c.dono is lut and c.parte is None]
        casadas: list[Criatura] = []
        novas: list = []
        i = 0
        for turnos, dano, origem in entradas:
            k = i
            while (
                not novas
                and k < len(vivas)
                and not (
                    vivas[k].origem == origem
                    and vivas[k].dano == dano
                    and turnos <= vivas[k].turnos
                )
            ):
                k += 1
            if not novas and k < len(vivas):
                vivas[k].turnos = turnos
                casadas.append(vivas[k])
                i = k + 1
            else:
                novas.append((turnos, dano, origem))
        for c in vivas:
            if not any(c is x for x in casadas):
                fim_do_bote = c.bote[0] + DURACAO_BOTE if c.bote else 0.0
                c.parte = max(self.relogio, fim_do_bote)  # morde antes de ir embora
        for turnos, dano, origem in novas:
            ocupados = {c.lugar for c in self.criaturas if c.dono is lut and c.parte is None}
            lugar = next((n for n in range(3) if n not in ocupados), 0)
            self.criaturas.append(Criatura(lut, origem, dano, turnos, lugar, nasce))

    def _acompanhar_clones(self, lut: Lutador, nasce: float, some: float) -> None:
        n = lut.clones if lut.vivo else 0
        vivos = sorted(
            (c for c in self.clones_em_campo if c.dono is lut and c.parte is None),
            key=lambda c: c.lugar,
        )
        if n > len(vivos):
            ocupados = {c.lugar for c in vivos}
            livres = [x for x in range(max(n, CLONES_VISIVEIS) + 1) if x not in ocupados]
            for lugar in livres[: n - len(vivos)]:
                clone = Clone(lut, lugar, nasce)
                self.clones_em_campo.append(clone)
                if lugar < CLONES_VISIVEIS:  # o clone aparece numa nuvem
                    x, y, esc = self._pos_clone(clone)
                    self.nuvens.append((x, y - 70 * esc, nasce, esc))
        for _ in range(len(vivos) - n):  # absorveu um golpe: some numa nuvem
            visiveis = [c for c in vivos if c.lugar < CLONES_VISIVEIS]
            sai = visiveis[-1] if visiveis else vivos[-1]
            sai.parte = some
            vivos.remove(sai)
            if sai.lugar < CLONES_VISIVEIS:
                x, y, esc = self._pos_clone(sai)
                self.nuvens.append((x, y - 70 * esc, some, esc))
                escondido = next((c for c in vivos if c.lugar >= CLONES_VISIVEIS), None)
                if escondido is not None:  # quem estava fora de vista ocupa o lugar
                    escondido.lugar = sai.lugar

    def _pos_clone(self, c: Clone) -> tuple[float, float, float]:
        """Os pés e a escala de um clone (atrás e ao lado do dono)."""
        x, y = self._centro(c.dono)
        lugar = min(c.lugar, CLONES_VISIVEIS - 1)
        if c.dono is self.j.jogador:
            dx, dy = LUGAR_CLONE_JOGADOR[lugar]
            return x + dx, y + dy, ESCALA_JOGADOR * 0.86
        esc = self._escala_rival(c.dono)
        f = esc / 0.92 * (0.72 if self.bando else 1.0)  # no bando, mais juntos
        dx, dy = LUGAR_CLONE_RIVAL[lugar]
        return x + dx * f, y + dy * f, esc * 0.9

    def _casa(self, c: Criatura) -> tuple[float, float, float, float]:
        """(x, y dos pés, escala, lado para onde olha) de uma invocação parada."""
        x, y = self._centro(c.dono)
        if c.dono is self.j.jogador:
            lugares = LUGAR_INV_JOGADOR_ALIADO if self.aliado is not None else LUGAR_INV_JOGADOR
            dx, dy, esc = lugares[c.lugar]
            return x + dx, y + dy, esc, 1.0
        if self.bando:
            f = self._escala_rival(c.dono) / ESCALA_BANDO[3]
            dx, dy, esc = LUGAR_INV_BANDO[c.lugar]
            return x + dx * f, y + dy * f, esc * f, -1.0
        dx, dy, esc = LUGAR_INV_RIVAL[c.lugar]
        return x + dx, y + dy, esc, -1.0

    def _botes(self, acao: Acao, ator: Lutador, alvo: Lutador, base: float | None = None) -> float:
        """As invocações de quem agiu atacam primeiro, uma depois da outra (`acao.invocadas`),
        a partir de `base`. Devolve quanto a ação em si espera por elas."""
        if not acao.invocadas:
            return 0.0
        base = self.relogio if base is None else base
        vivas = [c for c in self.criaturas if c.dono is ator and c.parte is None]
        usadas: list[Criatura] = []
        tx, ty = self._centro(alvo)  # os números das mordidas: do outro lado do golpe principal
        for n, (origem, dano) in enumerate(acao.invocadas):
            inicio = base + n * PASSO_BOTE
            impacto = inicio + DURACAO_BOTE * BOTE_IMPACTO
            c = next((c for c in vivas if c.origem == origem and c not in usadas), None)
            if c is not None:
                c.bote = (inicio, alvo)
                usadas.append(c)
            cor = COR_CRIATURA[criatura_de(origem)]
            self.mordidas.append((alvo, impacto, cor))
            texto = f"-{dano}" if dano else "0"
            cor_txt = SANGUE_VIVO if dano else alpha(TINTA, 160)
            x = tx - 58 + (-1) ** n * 10 * n
            self._por(Texto(x, ty - 40 - 24 * n, texto, cor_txt, impacto, 26, True))
            if dano:
                self.tremor[id(alvo)] = impacto
                self.forca_tremor[id(alvo)] = min(9.0, 3 + dano * 0.35)
                self._agendar_som(impacto, "golpe", 0.5)
        return (len(acao.invocadas) - 1) * PASSO_BOTE + DURACAO_BOTE * 0.62

    def _por(self, t: Texto) -> None:
        """Põe um texto sem cobrir outro que ainda está ali: tenta o lugar pedido e, se
        estiver ocupado, um passo para o lado ou para cima."""
        x0, y0 = t.x, t.y
        for dx, dy in ((0, 0), (48, 0), (-48, 0), (0, -28), (96, 0), (48, -28)):
            t.x, t.y = x0 + dx, y0 + dy
            ocupado = any(
                abs(o.x - t.x) < 50 and abs(o.y - t.y) < 24 and abs(o.inicio - t.inicio) < 1.0
                for o in self.textos
            )
            if not ocupado:
                break
        else:
            t.x, t.y = x0, y0
        self.textos.append(t)

    def _agendar_som(self, quando: float, nome: str, volume: float = 1.0) -> None:
        if quando <= self.relogio:
            som.tocar(nome, volume)
        else:
            self.sons.append((quando, nome, volume))

    def _lutador(self, nome: str) -> Lutador:
        if nome == self.j.jogador.nome:
            return self.j.jogador
        return next((r for r in self.luta.rivais if r.nome == nome), self.luta.rival)

    def _trocar_alvo(self, passo: int) -> None:
        """O jogador mira no próximo (ou no anterior) rival de pé."""
        vivos = self.luta.vivos
        if len(vivos) < 2:
            return
        i = vivos.index(self.luta.rival) if self.luta.rival in vivos else 0
        self.luta.mirar(vivos[(i + passo) % len(vivos)])
        som.tocar("mover")

    def _executar(self, t: Tecnica, sacrificio: Tecnica | None = None) -> None:
        alvo, antes = self.luta.rival, self._foto()  # o motor remira se o alvo cair
        self._animar(self.luta.resolver(t, sacrificio), alvo, antes)

    def _agir_rival(self) -> None:
        antes = self._foto()
        self._animar(self.luta.turno_rival(), antes=antes)

    def _animar(
        self,
        acao: Acao,
        alvo: Lutador | None = None,
        antes: dict[int, tuple[int, int]] | None = None,
    ) -> None:
        """Anima a ação. `alvo`: quem o jogador mirava ao agir (a `Acao` também diz);
        `antes`: a `_foto`. As invocações de quem agiu dão o bote primeiro; a ação em
        si começa em `t0`, e o número, o tremor e o hit-stop esperam o impacto."""
        j = self.j.jogador
        ator = self._lutador(acao.ator)
        if ator is j:
            mirado = next((r for r in self.luta.rivais if r.nome == acao.alvo), None)
            alvo = mirado or alvo or self.luta.rival
        else:
            alvo = j
        rival = alvo if ator is j else ator  # o rival desta troca
        tecnica = next(
            (
                t
                for t in [*ator.tecnicas, ator.tecnica_dom, ator.tecnica_linhagem]
                if t and t.id == acao.tecnica
            ),
            None,
        )
        # a ordem: o aliado age, a mecânica do começo do turno do chefe, as invocações
        # dão o bote, o espelho do Aizen se quebra, o cut-in, e só então o golpe (t0)
        base = self.relogio
        espera, feito_aliado = 0.0, ""
        if acao.aliado and ator is j:
            espera, feito_aliado = self._aliado_age(acao.aliado, alvo, base)
        if acao.mecanica in MEC_COMECO:
            self._mecanica_fx(acao.mecanica, ator, base + espera)
        inicio_botes = base + espera
        espera += self._botes(acao, ator, alvo, inicio_botes)
        if acao.iludiu:  # Kyoka Suigetsu: o que você viu era um espelho
            self.vidro = (base + espera, ator)
            self._agendar_som(base + espera, "vidro")
            espera += DURACAO_VIDRO * 0.7
        espera += self._cutin(ator, tecnica, base + espera)
        t0 = base + espera
        impacto = t0 + IMPACTO
        if acao.aliado and ator is j and acao.aliado[1] == "ferir":
            self.segura_barra_ate = base + DURACAO_ALIADO * ALIADO_IMPACTO
        elif acao.invocadas:
            self.segura_barra_ate = inicio_botes + DURACAO_BOTE * BOTE_IMPACTO
        else:
            self.segura_barra_ate = impacto
        clones_antes = any(c.dono is ator and c.parte is None for c in self.clones_em_campo)
        self.golpe = (ator, t0)
        self.clones_atacam = (ator, t0) if acao.dano and clones_antes else None
        nome_efeito = vfx.efeito_de(acao.tecnica, tecnica.tipo if tecnica else "ataque")
        if acao.copiou:  # o Olho Roubado toca o efeito da técnica roubada, depois do olho
            nome_efeito = "olho"
        self.efeito = (nome_efeito, ator, alvo, t0, acao.critico)
        principal = "critico" if acao.critico else som.SOM_DO_EFEITO.get(nome_efeito, "golpe")
        self._agendar_som(t0, principal)
        if acao.reagiu:
            self._agendar_som(t0, "percebeu")
        if acao.reagiu or (ator is rival and tecnica is not None and tecnica.perigosa):
            self.ao_dica("percepcao")
        if acao.esquivas or acao.escudados or acao.instintos:
            self._agendar_som(impacto, "defesa")
        if acao.dano and alvo is j:
            self._agendar_som(impacto, "dano", 0.6)
        if acao.dano and len(self.manchas) < 24:  # o golpe deixa a sua marca no chão
            px, py = self._centro(alvo)
            semente = self.relogio * 7.3
            tam = min(34, 10 + acao.dano * 0.8)
            self.manchas.append((px + math.sin(semente) * 30, py + 4, tam, semente))
        self.anim_ate = t0 + max(DURACAO_ACAO, vfx.duracao(nome_efeito))
        ax, ay = self._centro(alvo)
        bx, by = self._centro(ator)
        nome = self._nome(acao.tecnica)
        partes = []
        if acao.invocadas:
            total = sum(d for _o, d in acao.invocadas)
            n = len(acao.invocadas)
            partes.append(f"召 {'a invocação' if n == 1 else f'{n} invocações'} fez {total}")
        i_nome = len(partes)
        partes.append(f"{self._quem(ator)}: {nome}")
        if self.bando and ator is j and acao.dano:
            partes[i_nome] += f" em {alvo.titulo or alvo.nome}"
        if acao.surpresa and not acao.reagiu:
            self._por(Texto(ax, ay - 110, "surpresa!", OURO, t0, 22))
        if acao.dano:
            self.tremor[id(alvo)] = impacto
            self.forca_tremor[id(alvo)] = min(14.0, 3 + acao.dano * 0.4)
            tam = 46 if acao.critico else 34
            self._por(Texto(ax + 30, ay - 70, f"-{acao.dano}", SANGUE_VIVO, impacto, tam, True))
            partes.append(f"{acao.dano} de dano")
            forte = acao.critico or acao.dano >= min(18, 0.25 * alvo.vida_max)
            if forte:  # o golpe forte congela a cena um instante e o alvo fica branco
                self.parada = (impacto, HITSTOP_CRITICO if acao.critico else HITSTOP)
                self.flash = (alvo, impacto, acao.critico)
                forca = ZOOM_CRITICO if acao.critico else ZOOM_FORTE
                self.zoom = (impacto - ZOOM_SOBE, forca, alvo)  # o punch-in da câmera
        if acao.dano and nome_efeito in EFEITOS_VELOZES:
            self.velozes = (t0 - 0.04, alvo)
        if acao.reagiu:
            self._por(Texto(ax - 40, ay - 92, "percebeu!", VERDE_JADE, t0, 22))
            self.tremor[id(ator)] = t0 + 0.2
            partes.append("percebido: metade, e contra-golpe")
        if acao.destruida:
            pacto = f"契 {self._nome(acao.destruida)} se desfaz"
            self._por(Texto(bx, by - 150, pacto, OURO, t0, 18))
            partes.append(f"o pacto levou {self._nome(acao.destruida)}")
        if acao.copiou:
            partes[i_nome] += f" (roubou {self._nome(acao.copiou)})"
        if acao.esquivas:
            self._por(Texto(ax - 30, ay - 120, "esquivou!", VERDE_JADE, impacto, 22))
            partes.append("esquivou")
        if acao.escudados:
            self._por(Texto(ax + 40, ay - 120, "escudo!", TINTA, impacto, 20))
            partes.append("o escudo segurou")
        if acao.sombra:
            partes.append(f"a sombra fez {acao.sombra}")
        if acao.turno_extra:
            self._por(Texto(bx, by - 150, "刻 ação extra!", OURO, t0, 20))
            partes.append("e age de novo")
        if acao.critico:
            self._por(Texto(ax, ay - 150, "黒閃!", SANGUE_VIVO, impacto, 34, True))
            partes.append("Clarão Negro: ×2,5")
        curou_aliados = self._efeitos_no_bando(acao, ator, alvo, tecnica, antes or {}, partes, t0)
        if acao.curou > curou_aliados:  # o que sobrou da cura foi em quem agiu
            proprio = acao.curou - curou_aliados
            self._por(Texto(bx, by - 120, f"+{proprio}", VERDE_JADE, t0 + 0.1, 30, True, 64))
            partes.append(f"curou {proprio}")
        if acao.selou:
            self._por(Texto(ax, ay - 130, "鎖 selado!", OURO, impacto, 22))
            partes.append(f"selou {self._nome(acao.selou)}")
        if acao.atordoou:
            self._por(Texto(ax, ay - 130, "幻 perde o turno", SANGUE_VIVO, impacto, 20))
            partes.append("perde o próximo turno")
        if acao.instintos:
            self._por(Texto(ax, ay - 120, "極 esquivou!", TINTA, impacto, 22))
            partes.append("o instinto esquivou e revidou")
        if acao.incinerou:
            self._por(Texto(bx, by - 130, "灰 cinzas", SANGUE_VIVO, t0, 26))
            quem = "você" if ator is j else (self._quem(ator) if self.bando else "o rival")
            quem += " virou"
            partes.insert(0, f"炎 a chama negra: {quem} cinzas")
        if acao.segunda_forma:
            cx, cy = self._centro(rival)
            forma = Texto(cx, cy - 160, "鬼 segunda forma", SANGUE_VIVO, t0, 28)
            self._por(forma)
            self.tremor[id(rival)] = t0 + 0.4
            partes.append("o chefe revelou a segunda forma: mais forte, técnicas prontas")
        if acao.quebrou:
            self._quebrar(acao.quebrou, impacto, partes)
        if acao.mecanica:
            dono = ator if ator.mecanica == acao.mecanica.split("_")[0] else alvo
            if acao.mecanica not in MEC_COMECO:
                quando = impacto if acao.mecanica in MEC_NO_IMPACTO else t0
                self._mecanica_fx(acao.mecanica, dono, quando)
            kanji = self._mecanica_de(dono)[0] or "鬼"
            partes.append(f"{kanji} {MEC_REGISTRO.get(acao.mecanica, acao.mecanica)}")
        if acao.iludiu:
            partes.insert(0, "鏡花水月: o que você viu era ilusão")
        if feito_aliado:
            partes.insert(0, feito_aliado)
        if acao.despertou:
            partes.append("o golpe fatal não veio: você despertou")
        self.registro = " · ".join(partes)
        self._anunciar_promessa()
        if acao.despertou:
            self._celebrar(self.luta.ultimo_despertar)
        # quem a ação pôs em campo surge com ela; o clone que absorveu estoura no impacto
        self._acompanhar(nasce=t0 + 0.12, some=impacto)
        if self.luta.vez is not j:
            self.proxima_rival = self.anim_ate + PAUSA_RIVAL

    def _efeitos_no_bando(
        self,
        acao: Acao,
        ator: Lutador,
        alvo: Lutador,
        tecnica: Tecnica | None,
        antes: dict[int, tuple[int, int]],
        partes: list[str],
        t0: float = 0.0,
    ) -> int:
        """O que a ação fez nos outros rivais: o respingo da área (`acao.respingo`), a
        cura e a proteção de aliado (`acao.curado`, `acao.protegido`) e quem caiu.
        Devolve a cura dada aos aliados (o resto do `acao.curou` foi em quem agiu)."""
        j = self.j.jogador
        if not self.bando:
            return 0
        respingo, curados, protegidos, caidos = [], [], [], []
        curou_aliados = 0
        beneficiado = None
        quando = t0 + IMPACTO + 0.05  # a área chega um pouco depois do golpe principal
        for nome_r, n in acao.respingo:  # a explosão pegou o bando
            r = self._lutador(nome_r)
            x, y = self._centro(r)
            esc = self._escala_rival(r)
            if n:
                self.tremor[id(r)] = quando
                self.forca_tremor[id(r)] = min(10.0, 3 + n * 0.4)
            texto = f"-{n}" if n else "0"
            self._por(Texto(x + 26, y - 70 * esc, texto, SANGUE_VIVO, quando, 26, True))
            respingo.append(f"{r.titulo or r.nome} {n}")
        if acao.curado and ator is not j and acao.curado != ator.nome:  # o Curandeiro
            r = self._lutador(acao.curado)
            vida0 = antes.get(id(r), (None, 0))[0]
            n = r.vida - vida0 if vida0 is not None else acao.curou
            if n > 0:
                curou_aliados, beneficiado = n, r
                x, y = self._centro(r)
                esc = self._escala_rival(r)
                cura = Texto(x - 50 * esc, y - 110 * esc, f"+{n}", VERDE_JADE, t0 + 0.1, 28, True)
                cura.sobe = 64
                self._por(cura)
                curados.append(f"{r.titulo or r.nome} +{n}")
        if acao.protegido and ator is not j:  # o Guardião
            r = self._lutador(acao.protegido)
            bloq0 = antes.get(id(r), (0, None))[1]
            n = r.bloqueio - bloq0 if bloq0 is not None else (tecnica.proteger if tecnica else 0)
            beneficiado = r
            x, y = self._centro(r)
            esc = self._escala_rival(r)
            cor = (150, 200, 240, 255)
            self._por(Texto(x + 56 * esc, y - 110 * esc, KANJI_PROTEGIDO, cor, t0 + 0.1, 30, True))
            protegidos.append(f"{r.titulo or r.nome} ({n})")
        for r in self.luta.rivais:
            if id(r) in antes and antes[id(r)][0] > 0 and not r.vivo:
                caidos.append(r.titulo or r.nome)
        if tecnica is not None and tecnica.inspirar and ator is not j:  # o Comandante
            for r in self.luta.vivos:
                x, y = self._centro(r)
                esc = self._escala_rival(r)
                txt = f"+{tecnica.inspirar} dano"
                self._por(Texto(x, y - 95 * esc, txt, OURO, t0, 18))
            partes.append(f"o bando bate +{tecnica.inspirar}")
        if respingo:
            partes.append("respingo: " + ", ".join(respingo))
        if curados:
            partes.append("curou " + ", ".join(curados))
        if protegidos:
            partes.append("protegeu " + ", ".join(protegidos))
        if caidos:
            partes.append(" e ".join(caidos) + (" caíram" if len(caidos) > 1 else " caiu"))
        if beneficiado is not None and self.efeito is not None:  # o efeito vai até o aliado
            nome_ef, _ator, _alvo, inicio, forte = self.efeito
            self.efeito = (nome_ef, ator, beneficiado, inicio, forte)
        return curou_aliados

    # --------------------------------------------------------------- o cinema da ação

    def _cutin(self, ator: Lutador, tecnica: Tecnica | None, inicio: float) -> float:
        """Abre o cut-in, se a técnica merece (Maldita, Divina, fusão ou assinatura de
        chefe) e ainda não teve o dela nesta luta (a fusão tem sempre). Devolve quanto o
        golpe espera por ele."""
        if tecnica is None or tecnica in (self.luta.basico, HESITAR):
            return 0.0
        fusao = tecnica.id in self.fusoes
        assinatura = bool(ator.assinatura) and tecnica.id == ator.assinatura
        if not (fusao or assinatura or tecnica.raridade in RARIDADES_CUTIN):
            return 0.0
        rival = ator is not self.j.jogador
        chave = (rival, tecnica.id)
        if chave in self.cutins_vistos and not fusao:
            return 0.0
        self.cutins_vistos.add(chave)
        if fusao:
            rotulo = "融合 · fusão"
        elif assinatura:
            kanji, nome = self._mecanica_de(ator)
            rotulo = f"{kanji} {nome}" if kanji else "técnica do chefe"
        else:
            rotulo = "神 · Divina" if tecnica.raridade == "divino" else "呪 · Maldita"
        info = {
            "kanji": self.kanji.get(tecnica.id, "?"),
            "nome": self._nome(tecnica.id),
            "origem": self.origens.get(tecnica.id, ""),
            "rotulo": rotulo,
            "rival": rival,
            "estilo": self.estilos.get(id(ator), "espadachim") if rival else "espadachim",
        }
        self.cutin = (info, inicio)
        self._agendar_som(inicio, "cutin")
        return DURACAO_CUTIN

    def _mecanica_de(self, r: Lutador) -> tuple[str, str]:
        """(kanji, nome) da mecânica do chefe `r` (vazio se ele não tem)."""
        m = self.mecanicas.get(r.mecanica) if r.mecanica else None
        return (m["kanji"], m["nome"]) if m else ("", "")

    def _mecanica_fx(self, mecanica: str, dono: Lutador, quando: float) -> None:
        """A reação visível de uma mecânica de chefe (`Acao.mecanica`), a partir de `quando`."""
        self.mec_fx.append((mecanica, dono, quando))
        self._agendar_som(quando, MEC_SOM.get(mecanica, "maldita"))
        kanji, nome = self._mecanica_de(dono)
        x, y = self._centro(dono)
        esc = self._escala_rival(dono)
        cor = COR_MECANICA.get(mecanica, OURO)
        if mecanica == "adaptar":
            self.casas_roda[id(dono)] = self.casas_roda.get(id(dono), 0) + 1
        elif mecanica == "repulsao":
            self.empurrao = quando
        if mecanica != "adaptar" and kanji:  # a roda já escreve 適応
            texto = "虚 atravessou" if mecanica == "intangivel" else f"{kanji} {nome}"
            self._por(Texto(x - 128 * esc, y - 128 * esc, texto, cor, quando, 24, True))

    def _quebrar(self, nome: str, quando: float, partes: list[str]) -> None:
        """A guarda de `nome` quebrou: 崩 grande, estilhaço, o estalo e o punch-in."""
        r = self._lutador(nome)
        self.quebras.append((r, quando))
        self.viu_quebra = True
        x, y = self._centro(r)
        esc = self._escala_rival(r)
        claro = (255, 236, 200, 255)
        self._por(Texto(x - 122 * esc, y - 142 * esc, KANJI_QUEBRA, claro, quando, 72, True, 30))
        self._por(Texto(x - 122 * esc, y - 52 * esc, "perde o turno", SANGUE_VIVO, quando, 17))
        self._agendar_som(quando, "quebra")
        self.zoom = (quando - ZOOM_SOBE, ZOOM_CRITICO, r)
        if self.parada is None or self.parada[0] != quando:
            self.parada = (quando, HITSTOP_CRITICO)
        quem = f"de {self._quem(r)}" if self.bando else "do rival"
        partes.append(f"崩 a guarda {quem} quebrou: perde o turno")

    def _aliado_age(self, feito: tuple, alvo: Lutador, inicio: float) -> tuple[float, str]:
        """O aliado agiu no começo do seu turno: anima e diz o quê. Devolve (quanto a
        ação espera por ele, o trecho do registro)."""
        _aid, efeito, valor = feito
        a = self.aliado
        kanji = a.kanji if a is not None else "友"
        nome = a.nome if a is not None else "o aliado"
        self.aliado_acao = (efeito, inicio, alvo)
        impacto = inicio + DURACAO_ALIADO * ALIADO_IMPACTO
        cor = COR_ALIADO.get(efeito, OURO)
        j = self.j.jogador
        if efeito in ("curar", "bloquear"):
            x, y = self._centro(j)
            texto = f"+{valor}" if efeito == "curar" else f"守 {valor}"
            self._por(Texto(x + 70, y - 190, texto, cor, impacto, 28, True))
            self._agendar_som(impacto, "cura" if efeito == "curar" else "defesa", 0.6)
        else:
            x, y = self._centro(alvo)
            esc = self._escala_rival(alvo)
            texto = {"ferir": f"{kanji} -{valor}", "expor": f"{kanji} exposto"}.get(
                efeito, f"{kanji} 毒{valor}"
            )
            self._por(Texto(x - 64 * esc, y - 150 * esc, texto, cor, impacto, 22, True))
            self.mordidas.append((alvo, impacto, cor))
            if efeito == "ferir" and valor:
                self.tremor[id(alvo)] = impacto
                self.forca_tremor[id(alvo)] = min(8.0, 3 + valor * 0.4)
            self._agendar_som(impacto, "golpe" if efeito == "ferir" else "corte_agudo", 0.5)
        feito = FEITO_ALIADO.get(efeito, efeito).format(v=valor)
        return DURACAO_ALIADO, f"{kanji} {nome} {feito}"

    def _quebrado(self, r: Lutador) -> bool:
        """A guarda quebrada à vista: espera o golpe que a quebrou acertar."""
        if not (r.quebrado and r.vivo):
            return False
        return not any(q is r and self.relogio < quando for q, quando in self.quebras)

    def _perigosos(self) -> list[Lutador]:
        """Quem anuncia um golpe perigoso que você enxerga (o aviso nas bordas)."""
        if self.luta.acabou or self.modo == "fim" or self.relogio < self.entrada_ate:
            return []
        quem = []
        for r in self.luta.vivos:
            vista = self.luta.ver_intencao(de=r)
            if isinstance(vista, Tecnica) and vista.perigosa:
                quem.append(r)
        return quem

    def _faixa(self) -> str:
        """A música desta luta: a do chefe muda na segunda forma."""
        chefes = [r for r in self.luta.rivais if r.chefe]
        if chefes:
            return "chefe_furia" if any(r.segunda_forma for r in chefes) else "chefe"
        return "luta_carma" if self.j.carma.transbordando else "luta"

    def _celebrar(self, fatia) -> None:
        """A cena do Despertar: trava a entrada um pouco mais que uma ação."""
        self.desperto = (fatia, self.relogio)
        som.tocar("despertar")
        if self.j.grimorio is not None:
            self.j.grimorio.ver([fatia])
        self.anim_ate = max(self.anim_ate, self.relogio + DURACAO_DESPERTAR)
        self.tremor[id(self.j.jogador)] = self.relogio
        self.registro = f"覚醒 {fatia.nome}: {fatia.texto}"

    def _anunciar_promessa(self) -> None:
        resultado = self.luta.promessa_resultado
        if resultado and resultado != self.promessa_vista:
            self.promessa_vista = resultado
            x, y = self._centro(self.j.jogador)
            if resultado == "cumprida":
                self._por(Texto(x, y - 170, "約 promessa cumprida", OURO, self.relogio, 22))
                som.tocar("revela_divino")
            else:
                self._por(Texto(x, y - 170, "約 promessa quebrada", SANGUE_VIVO, self.relogio, 22))
                som.tocar("derrota")
            self.registro += f" · a promessa foi {resultado}"

    def _voto(self) -> None:
        """O voto de luta aberto: Enter (ou V) jura, Backspace volta."""
        e = self.entrada
        if e.is_action_pressed("cancelar"):
            self.modo = "escolher"
            return
        if e.is_action_pressed("confirmar") or e.is_action_pressed("voto"):
            v = self.luta.voto_luta
            self.luta.jurar_luta()
            self.modo = "escolher"
            som.tocar("corrente")
            x, y = self._centro(self.j.jogador)
            self._por(Texto(x, y - 150, f"約 {v.nome}", OURO, self.relogio, 24))
            self.registro = f"約 Você jurou: {v.nome}"
            self.anim_ate = self.relogio + 0.6
            self._anunciar_promessa()

    def _musica(self) -> None:
        faixa = self._faixa()  # a fúria entra por cima da do chefe, numa passagem
        som.musica(faixa, cruzar=PASSAGEM_FURIA if faixa == "chefe_furia" else 0.0)

    def _esperando(self) -> bool:
        """Há animação tocando ou é a vez dos rivais (o que o acelerar encurta)."""
        if self.relogio < self.anim_ate or self.relogio < self.entrada_ate:
            return True
        return not self.luta.acabou and self.luta.vez is not self.j.jogador

    def _passar(self, dt: float) -> None:
        """Avança o relógio; o hit-stop congela a cena no instante do impacto."""
        while dt > 1e-9:
            if self.congelado > 0:
                usa = min(dt, self.congelado)
                self.congelado -= usa
                dt -= usa
                continue
            if self.parada is not None and self.relogio + dt >= self.parada[0]:
                quando, duracao = self.parada
                self.parada = None
                if quando > self.relogio:
                    dt -= quando - self.relogio
                    self.relogio = quando
                self.congelado = duracao
                continue
            self.relogio += dt
            dt = 0.0

    def update(self, world, delta_time: float) -> None:
        e = self.entrada
        segurar = getattr(e, "is_action_held", None)  # segurar Enter (ou Shift / X) acelera
        self.acelerando = (
            segurar is not None
            and (segurar("acelerar") or segurar("confirmar"))
            and self._esperando()
        )
        som.SOM.atualizar(delta_time)  # a passagem da música corre no tempo de verdade
        if self.acelerando:
            delta_time *= ACELERAR
        delta_time *= OPCOES.velocidade  # a velocidade das animações, das opções
        self._passar(delta_time)
        if self.primeiro_quadro:
            self.primeiro_quadro = False
            som.tocar("chefe_entra" if self.luta.rival.chefe else "rival_entra")
        self._musica()
        if self.sons:  # os sons que esperavam o impacto
            agora = [s for s in self.sons if s[0] <= self.relogio]
            self.sons = [s for s in self.sons if s[0] > self.relogio]
            for _quando, nome, volume in agora:
                som.tocar(nome, volume)
        self.textos = [t for t in self.textos if self.relogio - t.inicio < 1.1]
        segura = self.relogio < self.segura_barra_ate  # a barra só cai quando o golpe acerta
        for lut in self._todos():  # e desce devagar, com o rastro branco do dano recente
            antes = self.vida_antes.get(id(lut), lut.vida)
            agora = antes if segura else lut.vida
            if agora < antes:
                topo, inicio = self.rastro.get(id(lut), (antes, -99.0))
                ativo = self.relogio - inicio < RASTRO_SEGURA + RASTRO_SOME
                self.rastro[id(lut)] = (max(topo, antes) if ativo else antes, self.relogio)
            self.vida_antes[id(lut)] = agora
            vista = self.vida_vista.get(id(lut), agora)
            self.vida_vista[id(lut)] = vista + (agora - vista) * min(1.0, delta_time * 8)
        for rv in self.luta.rivais:  # a guarda enche junto com o golpe
            vista = self.guarda_vista.get(id(rv), 0.0)
            if not segura:
                alvo_g = 0.0 if rv.quebrado else rv.guarda / limiar_guarda(rv)
                self.guarda_vista[id(rv)] = vista + (alvo_g - vista) * min(1.0, delta_time * 10)
        t = self.relogio
        self.quebras = [q for q in self.quebras if t < q[1] + DURACAO_QUEBRA]
        self.mec_fx = [m for m in self.mec_fx if t < m[2] + DURACAO_MECANICA]
        self._acompanhar()
        if not self.luta.acabou:
            for r in self.luta.rivais:  # caiu e o bando segue: ele se desfaz quando o golpe acerta
                if not r.vivo and id(r) not in self.morte:
                    self.morte[id(r)] = max(self.relogio, self.segura_barra_ate)
            if not self.luta.rival.vivo and self.luta.vivos:
                self.luta.mirar(self.luta.vivos[0])
        if e.is_action_pressed("sair"):
            self.ao_sair()
            return
        if self.modo in ("escolher", "sacrificio") and not self.luta.acabou:
            if e.is_action_pressed("alvo") or e.is_action_pressed("baixo"):
                self._trocar_alvo(1)
            elif e.is_action_pressed("cima"):
                self._trocar_alvo(-1)
        if self.relogio < self.anim_ate:
            return
        if self.modo == "fim":
            if e.is_action_pressed("confirmar"):
                self.ao_terminar(self.luta.vencedor is self.j.jogador)
            return
        if self.luta.acabou:
            self.modo = "fim"
            self.fim_inicio = self.relogio
            self.anim_ate = self.relogio + DURACAO_FIM
            venceu = self.luta.vencedor is self.j.jogador
            som.tocar("vitoria" if venceu else "derrota")
            return
        if self.luta.vez is not self.j.jogador:
            if self.relogio >= self.proxima_rival:
                self._agir_rival()
            return

        if self.luta.rival.chefe:
            self.ao_dica("chefe")
        if self.bando:
            self.ao_dica("bando")
        if any(r.afixos for r in self.luta.rivais):
            self.ao_dica("afixo")
        if any(r.chefe and r.mecanica for r in self.luta.rivais):
            self.ao_dica("mecanica")
        if self.viu_quebra:  # a primeira guarda quebrada
            self.ao_dica("guarda")
        if any(r.nemesis for r in self.luta.rivais):
            self.ao_dica("nemesis")
        if self.luta.pode_despertar():
            self.ao_dica("despertar")
        if e.is_action_pressed("despertar") and self.luta.pode_despertar():
            self._celebrar(self.luta.despertar())  # não gasta o turno
            return
        if self.luta.pode_jurar_luta():
            self.ao_dica("voto_luta")
        if self.modo == "voto":
            self._voto()
            return
        if e.is_action_pressed("voto") and self.luta.pode_jurar_luta():
            self.modo = "voto"
            som.tocar("mover")
            return
        slots = self.slots()
        if self.modo == "sacrificio":
            self._escolher_sacrificio(slots)
            return
        for i in range(len(slots)):
            if e.is_action_pressed(f"tecnica_{i + 1}"):
                self.cursor = i
                self._tentar(slots[i])
                return
        if e.is_action_pressed("esquerda"):
            self.cursor = (self.cursor - 1) % len(slots)
            som.tocar("mover")
        elif e.is_action_pressed("direita"):
            self.cursor = (self.cursor + 1) % len(slots)
            som.tocar("mover")
        elif e.is_action_pressed("confirmar"):
            self._tentar(slots[self.cursor])

    def _tentar(self, t: Tecnica | None) -> None:
        if t is None:
            self._avisar("espaço vazio")
        elif not self._disponivel(t):
            self._avisar(f"{t.nome}: {self._motivo_indisponivel(t)}")
        elif t.consome_tecnica:
            self.contrato, self.modo = t, "sacrificio"
        else:
            self._executar(t)

    def _escolher_sacrificio(self, slots: list[Tecnica | None]) -> None:
        """O Contrato pede a técnica que leva: pelo número, ou pelo cursor (controle)."""
        e = self.entrada
        if e.is_action_pressed("cancelar"):
            self.contrato, self.modo = None, "escolher"
            return
        escolhida = next(
            (t for i, t in enumerate(slots) if e.is_action_pressed(f"tecnica_{i + 1}")), False
        )
        if escolhida is False:
            if e.is_action_pressed("esquerda"):
                self.cursor = (self.cursor - 1) % len(slots)
                return
            if e.is_action_pressed("direita"):
                self.cursor = (self.cursor + 1) % len(slots)
                return
            if not e.is_action_pressed("confirmar"):
                return
            escolhida = slots[self.cursor]
        dom, linhagem = self.j.jogador.tecnica_dom, self.j.jogador.tecnica_linhagem
        if (
            escolhida is None
            or escolhida is self.contrato
            or escolhida in (self.luta.basico, HESITAR, dom, linhagem)
        ):
            self._avisar("escolha outra das suas técnicas")
            return
        contrato, self.contrato, self.modo = self.contrato, None, "escolher"
        self._executar(contrato, sacrificio=escolhida)

    # --------------------------------------------------------------- desenho

    def _centro(self, lutador: Lutador) -> tuple[float, float]:
        """Os pés de cada um: você embaixo; o rival (ou cada um do bando) em cima."""
        if lutador is self.j.jogador:
            return POS_JOGADOR
        if not self.bando or lutador not in self.luta.rivais:
            return POS_RIVAL
        return POS_BANDO[len(self.luta.rivais)][self.luta.rivais.index(lutador)]

    def _avanco(self, lutador: Lutador, atraso: float = 0.0) -> tuple[float, float]:
        """O avanço do golpe (vai e volta); `atraso` para os clones, que vêm logo atrás."""
        if self.golpe and self.golpe[0] is lutador:
            k = (self.relogio - atraso - self.golpe[1]) / DURACAO_ACAO
            if 0 <= k < 1:
                avanço = math.sin(min(k / 0.5, 1) * math.pi) * 34
                sentido = -1 if lutador is self.j.jogador else 1
                return -sentido * avanço * 0.55, sentido * avanço
        return 0.0, 0.0

    def _deslocamento(self, lutador: Lutador) -> tuple[float, float]:
        dx, dy = self._avanco(lutador)
        if self._quebrado(lutador):  # a guarda quebrada: ele cambaleia
            dx += math.sin(self.relogio * 2.6) * 5
        inicio = self.tremor.get(id(lutador))
        if inicio is not None and 0 <= self.relogio - inicio < 0.35:
            forca = self.forca_tremor.get(id(lutador), 7.0) * (1 - (self.relogio - inicio) / 0.35)
            dx += math.sin(self.relogio * 90) * forca
        return dx, dy

    def _pose_ataque(self, lutador: Lutador, atraso: float = 0.0) -> float:
        if self.golpe and self.golpe[0] is lutador:
            k = (self.relogio - atraso - self.golpe[1]) / DURACAO_ACAO
            if 0 <= k < 1:
                return math.sin(k * math.pi)
        return 0.0

    def _pose_dano(self, lutador: Lutador) -> float:
        inicio = self.tremor.get(id(lutador))
        if inicio is not None and 0 <= self.relogio - inicio < 0.35:
            return 1 - (self.relogio - inicio) / 0.35
        return 0.0

    def _clarao(self, lutador: Lutador) -> tuple[float, Cor]:
        """O tom do golpe recebido: branco no instante do golpe forte, depois vermelho."""
        if self.flash is not None and self.flash[0] is lutador:
            if 0 <= self.relogio - self.flash[1] < CLARAO_BRANCO:
                return 1.0, (255, 255, 255, 255)
        inicio = self.tremor.get(id(lutador))
        if inicio is not None and 0 <= self.relogio - inicio < 0.3:
            return 1 - (self.relogio - inicio) / 0.3, SANGUE_VIVO
        return 0.0, SANGUE_VIVO

    def _abalo(self) -> float:
        """O tremor da cena quando um golpe acerta (mais forte quanto maior o dano)."""
        forca = max(
            self._pose_dano(lut) * min(1.6, self.forca_tremor.get(id(lut), 7.0) / 7)
            for lut in self._todos()
        )
        return math.sin(self.relogio * 70) * 6 * forca

    def _vida(self, lut: Lutador) -> int:
        """A vida que a tela mostra (cai quando o golpe acerta, não quando é decidido)."""
        return self.vida_antes.get(id(lut), lut.vida)

    def _texto(self, r: IRenderer, x, y, texto, tam, cor, anchor="topleft") -> None:
        r.draw_text(x, y, texto, tam, cor, anchor=anchor, font_id=FONTE_PINCEL)

    def _camera(self) -> tuple[float, tuple[float, float], float, float]:
        """(escala, pivô, dx, dy) do mundo: o punch-in do golpe forte e o empurrão do Pain.
        Só o mundo se move: placas, barras e selos ficam no lugar."""
        escala, pivo, dx, dy = 1.0, (LARGURA / 2, ALTURA / 2), 0.0, 0.0
        if self.zoom is not None:
            quando, forca, alvo = self.zoom
            u = self.relogio - quando
            if 0 <= u < DURACAO_ZOOM:
                if u < ZOOM_SOBE:
                    f = ease_out(u / ZOOM_SOBE)
                else:
                    f = 1 - transicoes.suave((u - ZOOM_SOBE) / (DURACAO_ZOOM - ZOOM_SOBE))
                escala += forca * f
                pivo = self._corpo(alvo)
        if self.empurrao is not None:
            u = (self.relogio - self.empurrao) / DURACAO_EMPURRAO
            if 0 <= u < 1:  # um pouco de zoom junto: a borda da arena não aparece
                dy = 22 * (1 - u) ** 2
                dx = math.sin(self.relogio * 60) * 7 * (1 - u)
                escala += 0.08 * (1 - u) ** 2
        return escala, pivo, dx, dy

    def _mundo(self, r: IRenderer):
        """O renderer do mundo (arena, figuras, efeitos), com a câmera aplicada."""
        escala, pivo, dx, dy = self._camera()
        if escala == 1.0 and not dx and not dy:
            return r
        return transicoes.Camada(r, pivo, escala, dx, dy)

    def render(self, world, renderer: IRenderer) -> None:
        hud = renderer
        r = self._mundo(hud)
        self.perigo = self._perigosos()
        arco = self.j.arco.id if self.j.arco else None
        abalo = self._abalo()
        desenhar_arena(r, arco, self.relogio, abalo)
        for mx, my, tam, semente in self.manchas:
            vfx.mancha_de_sangue(r, mx, my, tam, semente)
        if self.bando:
            for rival in self.luta.rivais:
                self._criaturas(r, rival, "atras")
            for rival in self.luta.rivais:
                self._clones(r, rival)
                self._rival_do_bando(r, rival, hud)
        else:
            # ensō atrás do rival
            r.draw_ui_arc(
                POS_RIVAL[0],
                POS_RIVAL[1] - 66,
                92,
                math.radians(110),
                math.radians(430),
                alpha(TINTA, 18),
                10,
            )
            self._criaturas(r, self.luta.rival, "atras")
            self._clones(r, self.luta.rival)
            self._rival(r, hud)
        j = self.j.jogador
        self._criaturas(r, j, "atras")
        self._clones(r, j)
        self._jogador(r, hud)
        self._criaturas(r, j, "frente")
        for lut in self._todos():  # quem está dando o bote passa por cima de tudo
            self._criaturas(r, lut, "bote")
        self._aliado(r)
        self._impactos(r)
        self._efeito(r)
        self._cinema_mundo(r)
        desenhar_frente(r, arco, self.relogio, abalo)
        r = hud  # daqui para baixo, a tela parada: placas, painéis e o cinema por cima
        vfx.vinheta(r, 1.0)
        vfx.grao(r, self.relogio)
        self._linhas_velozes(r)
        if self.perigo and self.cutin_k() is None:
            vfx.perigo(r, self.relogio, 1.0 if self.luta.vez is self.j.jogador else 0.7)
        self._cabecalho(r)
        self._intencao(r)
        self._painel_voto(r)
        self._corrente(r)
        self._selos(r)
        self._origem(r)
        self._rodape(r)
        for t in self.textos:
            passou = self.relogio - t.inicio
            if passou < 0:  # espera o impacto
                continue
            k = passou / 1.1
            tam, sobe, some = t.tamanho, t.sobe * ease_out(k), 1 - k**2
            if t.pop:  # estoura, passa do ponto e assenta; depois sobe e some
                tam = max(8, 2 * round(t.tamanho * _volta(passou / 0.22) / 2))
                sobe = t.sobe * ease_out(max(0.0, (k - 0.2) / 0.8))
                some = 1 - max(0.0, (k - 0.45) / 0.55) ** 2
            self._texto(r, t.x, t.y - sobe, t.texto, tam, alpha(t.cor, 255 * some), "center")
        if self.vidro is not None:
            inicio, dono = self.vidro
            vfx.vidro_quebrando(r, *self._corpo(dono), (self.relogio - inicio) / DURACAO_VIDRO)
        k = self.cutin_k()
        if k is not None:
            vfx.cut_in(r, k, relogio=self.relogio, **self.cutin[0])
        if self.acelerando:  # o sinal discreto de que tudo corre mais rápido
            pisca = 0.5 + 0.5 * math.sin(self.relogio * 10)
            cor = alpha(OURO, 120 + 80 * pisca)
            self._texto(r, LARGURA - 16, ALTURA - 48, "»", 26, cor, "topright")
        self._modal_voto(r)
        self._cena_despertar(r)
        self._entrada_do_rival(r)
        if self.modo == "fim" and self.relogio >= self.anim_ate:
            self._banner(r)
        transicoes.revelar(self, r, self.relogio)

    def cutin_k(self) -> float | None:
        """O progresso (0–1) do cut-in tocando agora, ou None."""
        if self.cutin is None:
            return None
        k = (self.relogio - self.cutin[1]) / DURACAO_CUTIN
        return k if 0 <= k < 1 else None

    def _linhas_velozes(self, r: IRenderer) -> None:
        if self.velozes is None:
            return
        inicio, alvo = self.velozes
        k = (self.relogio - inicio) / DURACAO_VELOZ
        if 0 <= k < 1:
            vfx.linhas_de_velocidade(r, *self._corpo(alvo), k, self.relogio)

    def _cinema_mundo(self, r: IRenderer) -> None:
        """As reações das mecânicas de chefe e o estilhaço da guarda, no mundo."""
        t = self.relogio
        for mecanica, dono, quando in self.mec_fx:
            k = (t - quando) / DURACAO_MECANICA
            if not 0 <= k < 1:
                continue
            x, y = self._corpo(dono)
            esc = self._escala_rival(dono)
            if mecanica == "adaptar":
                giro = (self.casas_roda.get(id(dono), 1) - 1) * math.pi / 4
                vfx.roda_adapta(r, x, y - 30 * esc, k, giro)
            elif mecanica == "contrato":
                vfx.selo_contrato(r, x, y - 20 * esc, k)
            elif mecanica == "armadura":
                vfx.armadura(r, x, y, k, esc)
            elif mecanica == "intangivel":
                vfx.vortice(r, x, y, k, esc)
            elif mecanica == "repulsao":
                vfx.desenhar(r, "repulsao", (x, y), (x, y), k, t)
            elif mecanica == "regenera":
                vfx.desenhar(r, "cura", (x, y), (x, y), k, t)
            elif mecanica == "carregar":
                vfx.clarao_de_golpe(r, x, y, k, 1.5)
            elif mecanica in ("preco", "balanca", "balanca_virou"):
                vfx.desenhar(r, "selo", (x, y), (x, y), k, t)
        for alvo, quando in self.quebras:
            k = (t - quando) / DURACAO_QUEBRA
            if 0 <= k < 1:
                vfx.estilhaco(r, *self._corpo(alvo), k, self._escala_rival(alvo))

    def _marcas_do_chefe(self, r: IRenderer, rival: Lutador, x: float, y: float, esc: float):
        """O que a mecânica dele deixa à vista o tempo todo (a roda, as cargas, o selo do
        contrato, as pétalas), e o halo do golpe perigoso. Atrás da figura."""
        corpo = y - 66 * esc
        if rival in self.perigo:
            vfx.brilho_perigo(r, x, corpo, 92 * esc, self.relogio)
        m = rival.mecanica
        if not m or not rival.vivo:
            return
        if m == "carregar":
            vfx.carga(r, x, corpo, rival.carga, self.relogio, esc)
        elif m == "petalas":
            vfx.petalas(r, x, corpo, self.relogio, esc)

    def _marcas_por_cima(self, r: IRenderer, rival: Lutador, x: float, y: float, esc: float):
        """Por cima da figura: a roda do Mahoraga, o selo do contrato e a tontura."""
        if not rival.vivo:
            return
        if rival.mecanica == "adaptar":
            alvo_giro = self.casas_roda.get(id(rival), 0) * math.pi / 4
            giro = self.giro_visto.get(id(rival), 0.0)
            giro += (alvo_giro - giro) * 0.2
            self.giro_visto[id(rival)] = giro
            if not any(m[0] == "adaptar" and m[1] is rival for m in self.mec_fx):
                cor = alpha(OURO, 190)
                vfx.desenhar_roda(r, x, y - 150 * esc, 13 * esc / 0.92, giro, cor)
        if rival.contrato and rival.mecanica == "contrato":
            vfx.selo_mecanica(r, x + 70 * esc, y - 150 * esc, "契", 13, alpha(SANGUE_VIVO, 230))
        if self._quebrado(rival):
            vfx.tonto(r, x, y - 158 * esc, self.relogio, esc / 0.92)

    def _translucido(self, rival: Lutador) -> float:
        """Kamui: o corpo fica translúcido enquanto o golpe atravessa (1 = normal)."""
        for mecanica, dono, quando in self.mec_fx:
            if mecanica == "intangivel" and dono is rival:
                k = (self.relogio - quando) / DURACAO_MECANICA
                if 0 <= k < 1:
                    return 1 - 0.7 * math.sin(k * math.pi)
        return 1.0

    def _guarda(self, r: IRenderer, x: float, y: float, largura: float, rival: Lutador) -> None:
        """A barra fina da guarda, sob a vida: enche com a pressão dos seus golpes."""
        if not rival.vivo:
            return
        frac = max(0.0, min(1.0, self.guarda_vista.get(id(rival), 0.0)))
        r.draw_ui_rect(x, y, largura, 3, alpha(FERRO, 150))
        if self._quebrado(rival):
            pulso = 0.5 + 0.5 * math.sin(self.relogio * 9)
            r.draw_ui_rect(x, y, largura, 3, alpha(SANGUE_VIVO, 140 + 100 * pulso))
            cor = alpha(SANGUE_VIVO, 170 + 85 * pulso)
            self._texto(r, x + largura + 10, y + 1, KANJI_QUEBRA, 15, cor, "center")
            return
        cor = mistura(COR_GUARDA, OURO, max(0.0, frac - 0.6) / 0.4)
        r.draw_ui_rect(x, y, largura * frac, 3, cor)

    def _selos_afixo(self, r: IRenderer, rival: Lutador, pontos) -> None:
        """Os selos dos afixos da elite (o do texto no painel acende)."""
        if self.caminho is None:
            return
        for aid, (sx, sy, raio) in zip(rival.afixos, pontos, strict=False):
            afixo = self.caminho.afixos.get(aid)
            if afixo is None:
                continue
            foco = aid == self.foco_status and rival is self.luta.rival
            cor = OURO if foco else alpha(mistura(OURO, TINTA, 0.4), 210)
            vfx.selo_mecanica(r, sx, sy, afixo.kanji, raio, cor)

    def _rotulo_mecanica(self, rival: Lutador) -> str:
        """O selo da mecânica sob o nome do chefe, com o estado dela."""
        kanji, nome = self._mecanica_de(rival)
        if not kanji:
            return ""
        m, extra = rival.mecanica, ""
        if m == "adaptar":
            n = sum(1 for usos in rival.adaptacao.values() if usos >= 2)
            extra = f" · adaptou-se a {n}" if n else ""
        elif m == "carregar":
            extra = f" · carga {rival.carga}/2"
        elif m == "contrato":
            extra = " · firmado" if rival.contrato else " · rompido"
        elif m == "preco" and rival.preco:
            extra = " · pago"
        return f"{kanji} {nome}{extra}"

    def _status(self, alvo: Lutador, vista) -> list[str]:
        """A linha de status do painel: a origem da técnica anunciada, os afixos da elite
        e a mecânica do chefe (alternam se houver mais de um)."""
        linhas = []
        if isinstance(vista, Tecnica) and self.origens.get(vista.id):
            linhas.append(("", f"※ {self.origens[vista.id]}"))
        if self.caminho is not None:
            for aid in alvo.afixos:
                a = self.caminho.afixos.get(aid)
                if a is not None:
                    linhas.append((aid, f"{a.kanji} {a.nome}: {a.texto}"))
        kanji, nome = self._mecanica_de(alvo)
        if kanji:
            linhas.append(("", f"{kanji} {nome}: {self.mecanicas[alvo.mecanica]['texto']}"))
        return linhas

    def _pos_aliado(self) -> tuple[float, float, float]:
        x, y = POS_JOGADOR
        dx, dy, esc = LUGAR_ALIADO
        return x + dx, y + dy, esc

    def _aliado(self, r: IRenderer) -> None:
        """O aliado ao seu lado: respira e, quando age, dá o bote no alvo (ferir, expor,
        envenenar) ou pula/ergue a guarda junto de você (curar, bloquear)."""
        a = self.aliado
        if a is None:
            return
        x, y, esc = self._pos_aliado()
        fim = self._fim()
        visivel = 1.0 - (fim[0] if fim and not fim[1] else 0.0)
        entrada = min(1.0, self.relogio / max(1e-6, self.entrada_ate * 0.6))
        visivel *= entrada
        ataque, bx, by, clarao = 0.0, x, y, 0.0
        if self.aliado_acao is not None:
            efeito, inicio, alvo = self.aliado_acao
            k = (self.relogio - inicio) / DURACAO_ALIADO
            if 0 <= k < 1:
                if efeito in ("curar", "bloquear"):
                    ataque = math.sin(k * math.pi)
                    nome_ef = "cura" if efeito == "curar" else "guarda"
                    j = self._corpo(self.j.jogador)
                    vfx.desenhar(r, nome_ef, j, j, k, self.relogio)
                else:
                    ataque = _vai_e_volta(k, ALIADO_IMPACTO)
                    tx, ty = self._corpo(alvo)
                    bx += (tx - 46 - x) * ataque * 0.85
                    by += (ty + 40 - y) * ataque * 0.85
                    if abs(k - ALIADO_IMPACTO) < 0.08:
                        clarao = 0.7
        desenhar_aliado(
            r,
            a.id,
            bx,
            by,
            esc,
            tempo=self.relogio + 0.6,
            ataque=ataque,
            visivel=visivel,
            clarao=clarao,
        )
        if ataque < 0.05 and visivel > 0.9:  # o nível, em pontinhos
            altura, tamanho = medidas_aliado(a.id)
            topo = y - altura * tamanho * esc - 10
            n = max(1, self.aliado_nivel)
            for i in range(n):
                px = x + (i - (n - 1) / 2) * 7
                r.draw_ui_circle(px, topo, 3.2, alpha(FUNDO, 210))
                r.draw_ui_circle(px, topo, 2.2, alpha(OURO, 230))

    def _ressonancias(self, r: IRenderer) -> None:
        """Os selos das ressonâncias ativas, ao lado da sua vida (pontinhos = nível)."""
        try:
            ativas = ressonancias_ativas(self.j.estado)
        except Exception:  # um estado de teste sem rodas: sem selo
            return
        for i, res in enumerate(ativas[:4]):
            sx, sy = 318 + i * 36, 398
            cor = OURO if res.nivel >= 2 else alpha(mistura(OURO, TINTA, 0.45), 230)
            vfx.selo_mecanica(r, sx, sy, res.kanji, 13, cor)
            for n in range(res.nivel):
                px = sx + (n - (res.nivel - 1) / 2) * 7
                r.draw_ui_circle(px, sy + 20, 2.4, cor)

    def _fim(self) -> tuple[float, bool] | None:
        """(progresso 0–1 do fim, venceu), ou None se a luta não acabou."""
        if self.fim_inicio is None:
            return None
        k = min(1.0, (self.relogio - self.fim_inicio) / DURACAO_FIM)
        return k, self.luta.vencedor is self.j.jogador

    def _entrada_do_rival(self, r: IRenderer) -> None:
        """Uma pincelada atravessa a tela com o nome do rival; o chefe escurece tudo antes."""
        if self.relogio >= self.entrada_ate:
            return
        k = self.relogio / self.entrada_ate
        rival = self.luta.rival
        some = 1 - max(0.0, k - 0.75) / 0.25
        if rival.chefe:
            r.draw_ui_rect(0, 0, LARGURA, ALTURA, alpha((30, 4, 6, 255), 160 * some))
        elif rival.nemesis:  # quem já te matou: o ar fica cor de sangue
            r.draw_ui_rect(0, 0, LARGURA, ALTURA, alpha(SANGUE_NEMESIS, 70 * some))
        varre = ease_out(min(1.0, k / 0.35))
        y0, altura = 168, 96
        r.draw_ui_polygon(
            [
                (0, y0 + 8),
                (LARGURA * varre, y0),
                (LARGURA * varre, y0 + altura),
                (0, y0 + altura - 10),
            ],
            alpha((8, 7, 6, 255), 235 * some),
        )
        r.draw_ui_line(0, y0 + 4, LARGURA * varre, y0 - 2, alpha(SANGUE_VIVO, 200 * some), 3)
        if k > 0.2:
            brilho = 255 * min(1.0, (k - 0.2) / 0.2) * some
            kanji, nome, sub, cor, cor_nome = self._apresentacao()
            x_nome = 360 if len(nome) < 22 else 250  # nome longo (Nêmesis): começa antes
            tam = 36 if len(nome) <= 30 else max(20, round(36 * 30 / len(nome)))
            self._texto(r, x_nome - 60, y0 + 6, kanji, 70, alpha(cor, brilho), "center")
            self._texto(r, x_nome, y0 + 18 + (36 - tam) / 2, nome, tam, alpha(cor_nome, brilho))
            if self.assinatura is not None:
                a = self.assinatura
                sub = f"{sub} · {a.kanji} {a.nome}"
                kanji, nome = self._mecanica_de(self.luta.rival)
                if kanji and len(sub) + len(nome) < 66:
                    sub = f"{sub} · {kanji} {nome}"
            self._texto(r, x_nome + 2, y0 + 62, sub, 16, alpha(TINTA, brilho * 0.6))

    def _tipo_de_porta(self, tipo: str, padrao: str) -> str:
        """O kanji da porta (do caminho.json), com um padrão quando não há caminho."""
        if self.caminho is None:
            return padrao
        return self.caminho.tipos.get(tipo, {}).get("kanji", padrao)

    def _apresentacao(self) -> tuple[str, str, str, Cor, Cor]:
        """(kanji, nome, linha de baixo, cor do kanji, cor do nome) da entrada."""
        rival = self.luta.rival
        estilo = self.estilos[id(rival)]
        arco = self.j.arco.nome if self.j.arco else ""
        sub = f"Rival {self.j.n_luta} · {arco}"
        elite = any(x.elite for x in self.luta.rivais)
        if rival.chefe:
            sub = f"Capítulo {self.j.capitulo} · {arco}"
            return KANJI_ESTILO[estilo], "Chefe do capítulo", sub, SANGUE_VIVO, TINTA
        if self.bando:
            papeis = []
            for x in self.luta.rivais:
                p = self._papel(x)
                papeis.append(f"{p.kanji} {p.nome}" if p is not None else (x.titulo or x.nome))
            sub = " · ".join(papeis) + (f" · {arco}" if arco else "")
            if elite:
                kanji = self._tipo_de_porta("elite", KANJI_ELITE)
                return kanji, "Bando de elite", sub, OURO, OURO
            return self._tipo_de_porta("bando", KANJI_BANDO), "Bando", sub, OURO, TINTA
        if rival.nemesis:
            kanji = self._tipo_de_porta("nemesis", KANJI_NEMESIS)
            nome = f"Nêmesis · {rival.titulo or rival.nome}"
            sub = f"{sub} · quem te matou voltou"
            return kanji, nome, sub, SANGUE_VIVO, mistura(SANGUE_NEMESIS, TINTA, 0.45)
        if elite:
            sub = f"{sub} · vencer garante uma Relíquia"
            nome = f"Elite · {NOME_ESTILO.get(estilo, 'Rival')}"
            return self._tipo_de_porta("elite", KANJI_ELITE), nome, sub, OURO, OURO
        return KANJI_ESTILO.get(estilo, "敵"), NOME_ESTILO.get(estilo, "Rival"), sub, OURO, TINTA

    def _corpo(self, lutador: Lutador) -> tuple[float, float]:
        """O centro do corpo (os efeitos saem e chegam aqui), com o deslocamento do golpe."""
        x, y = self._centro(lutador)
        dx, dy = self._deslocamento(lutador)
        escala = ESCALA_JOGADOR if lutador is self.j.jogador else self._escala_rival(lutador)
        return x + dx, y + dy - 66 * escala

    def _efeito(self, r: IRenderer) -> None:
        if self.efeito is None:
            return
        nome, ator, alvo, inicio, forte = self.efeito
        k = (self.relogio - inicio) / vfx.duracao(nome)
        vfx.desenhar(r, nome, self._corpo(ator), self._corpo(alvo), k, self.relogio, forte)

    def _camada(self, c: Criatura) -> str:
        """Onde a criatura entra na ordem de desenho: atrás do dono, na frente, ou por
        cima de tudo enquanto dá o bote."""
        if c.bote is not None and 0 <= self.relogio - c.bote[0] < DURACAO_BOTE:
            return "bote"
        if c.dono is self.j.jogador and c.lugar < 2:
            return "frente"
        return "atras"

    def _criaturas(self, r: IRenderer, dono: Lutador, camada: str) -> None:
        t = self.relogio
        for c in self.criaturas:
            if c.dono is not dono or t < c.nasce or self._camada(c) != camada:
                continue
            x, y, esc, lado = self._casa(c)
            altura, tamanho = medidas_criatura(c.origem)
            k_nasce = (t - c.nasce) / DURACAO_SURGIR
            vfx.mancha_de_tinta(r, x, y, k_nasce / 1.3, esc * tamanho)
            surgir = ease_out(max(0.0, min(1.0, (k_nasce - 0.15) / 0.85)))
            visivel = min(1.0, k_nasce * 1.6)
            cor = COR_CRIATURA[criatura_de(c.origem)]
            if c.parte is not None and t >= c.parte:  # o tempo dela acabou: se desfaz
                kp = (t - c.parte) / DURACAO_PARTIR
                vfx.dissolver(r, x, y, kp, cor, esc * tamanho * 0.75)
                visivel *= max(0.0, 1 - kp * 1.4)
            ataque = clarao = 0.0
            bx, by = x, y
            if camada == "bote":
                kb = (t - c.bote[0]) / DURACAO_BOTE
                ataque = _vai_e_volta(kb, BOTE_IMPACTO)
                tx, ty = self._corpo(c.bote[1])
                # para na frente do alvo (os pés vão até perto do corpo dele)
                destino = (tx - lado * 40, ty + 50 * (1 if c.dono is self.j.jogador else 0.3))
                bx += (destino[0] - x) * ataque * 0.85
                by += (destino[1] - y) * ataque * 0.85
                if abs(kb - BOTE_IMPACTO) < 0.08:
                    clarao = 0.7  # o instante da mordida
            desenhar_criatura(
                r,
                c.origem,
                bx,
                by,
                esc,
                tempo=t + 1.3 * c.lugar + self.fase.get(id(c.dono), 0.0),
                ataque=ataque,
                lado=lado,
                visivel=visivel,
                surgir=surgir,
                clarao=clarao,
            )
            if c.parte is None and surgir > 0.9 and not ataque:  # os botes que faltam
                topo = y - altura * tamanho * esc - 10
                self._turnos(r, x, topo, c.turnos, c.dono is self.j.jogador)

    def _turnos(self, r: IRenderer, x: float, y: float, turnos: int, nosso: bool) -> None:
        """Pontinhos sobre a criatura: quantos botes ela ainda dá (número se forem muitos)."""
        cor = alpha(OURO if nosso else mistura(SANGUE_VIVO, TINTA, 0.3), 230)
        if turnos > 5:
            self._texto(r, x, y - 4, str(turnos), 14, cor, "center")
            return
        for i in range(turnos):
            px = x + (i - (turnos - 1) / 2) * 9
            r.draw_ui_circle(px, y, 4, alpha(FUNDO, 210))
            r.draw_ui_circle(px, y, 2.8, cor)

    def _clones(self, r: IRenderer, dono: Lutador) -> None:
        """As cópias translúcidas do dono, atrás dele; avançam junto quando ele golpeia."""
        t = self.relogio
        vivos = [
            c
            for c in self.clones_em_campo
            if c.dono is dono and (c.parte is None or t < c.parte) and t >= c.nasce
        ]
        visiveis = sorted((c for c in vivos if c.lugar < CLONES_VISIVEIS), key=lambda c: -c.lugar)
        jogador = dono is self.j.jogador
        estilo = "espadachim" if jogador else self.estilos[id(dono)]
        base = TINTA if jogador else COR_ESTILO.get(estilo, COR_ESTILO["espadachim"])
        sumico = None if jogador else self._sumico(dono)
        some = 1.0 if sumico is None else 1 - sumico
        atacam = self.clones_atacam is not None and self.clones_atacam[0] is dono
        for c in visiveis:
            x, y, esc = self._pos_clone(c)
            atraso = 0.05 * (c.lugar + 1)
            dx, dy = self._avanco(dono, atraso) if atacam else (0.0, 0.0)
            ataque = self._pose_ataque(dono, atraso) if atacam else 0.0
            surge = min(1.0, (t - c.nasce) / 0.25)
            a = 0.42 * surge * some
            desenhar_lutador(
                r,
                x + dx * 1.2,
                y + dy * 1.2,
                esc,
                alpha(base, 255 * a),
                alpha((255, 255, 255, 255), 140 * a),
                estilo=estilo,
                tempo=t + 0.7 * (c.lugar + 1) + self.fase.get(id(dono), 0.0),
                ataque=ataque,
                costas=jogador,
                respiro=1.6,
            )
        extra = sum(1 for c in vivos if c.parte is None and c.lugar >= CLONES_VISIVEIS)
        if extra and visiveis and some > 0.5:
            x, y, esc = self._pos_clone(max(visiveis, key=lambda c: c.lugar))
            cor = alpha(TINTA, 200)
            self._texto(r, x + 18 * esc, y - 150 * esc, f"+{extra}", 18, cor, "center")

    def _impactos(self, r: IRenderer) -> None:
        """Nuvens dos clones, mordidas das invocações e o clarão do golpe forte."""
        t = self.relogio
        for x, y, inicio, esc in self.nuvens:
            vfx.nuvem(r, x, y, (t - inicio) / DURACAO_POOF, esc)
        for alvo, inicio, cor in self.mordidas:
            x, y = self._corpo(alvo)
            esc = ESCALA_JOGADOR if alvo is self.j.jogador else self._escala_rival(alvo)
            vfx.mordida(r, x, y, (t - inicio) / DURACAO_MORDIDA, cor, esc)
        if self.flash is not None:
            alvo, inicio, critico = self.flash
            k = (t - inicio) / 0.3
            if 0 <= k < 1:
                x, y = self._corpo(alvo)
                esc = ESCALA_JOGADOR if alvo is self.j.jogador else self._escala_rival(alvo)
                vfx.clarao_de_golpe(r, x, y, k, esc * (1.3 if critico else 1.0))
                if critico and k < 0.4:  # o Clarão Negro: a tela inteira pisca
                    r.draw_ui_rect(
                        0, 0, LARGURA, ALTURA, alpha((255, 255, 255, 255), 70 * (1 - k / 0.4))
                    )

    def _origem(self, r: IRenderer) -> None:
        """A homenagem da técnica sob o cursor, acima dos selos."""
        slots = self.slots()
        if (
            self.modo != "escolher"
            or not 0 <= self.cursor < len(slots)
            or slots[self.cursor] is None
        ):
            return
        origem = self.origens.get(slots[self.cursor].id, "")
        if origem:
            self._texto(r, 624, 446, f"※ {origem}", 13, alpha(TINTA, 110), "center")

    def _cena_despertar(self, r: IRenderer) -> None:
        if self.desperto is None:
            return
        fatia, inicio = self.desperto
        k = (self.relogio - inicio) / DURACAO_DESPERTAR
        if k >= 1:
            return
        vfx.aura(r, fatia.id, *self._corpo(self.j.jogador), k, self.relogio)
        if k < 0.2:
            r.draw_ui_rect(0, 0, LARGURA, ALTURA, alpha(OURO, 130 * (1 - k / 0.2)))
        brilho = 255 * min(1.0, k * 4) * (1 - max(0.0, k - 0.75) / 0.25)
        r.draw_ui_rect(0, 220, LARGURA, 210, alpha(FUNDO, 200 * brilho / 255))
        self._texto(r, 480, 262, "覚醒", 70, alpha(OURO, brilho), "center")
        self._texto(r, 480, 330, f"{fatia.kanji}  {fatia.nome}", 30, alpha(OURO, brilho), "center")
        for i, linha in enumerate(quebrar(fatia.texto, 70)[:2]):
            self._texto(r, 480, 370 + i * 22, linha, 16, alpha(TINTA, brilho), "center")
        if fatia.origem:
            self._texto(r, 480, 416, f"※ {fatia.origem}", 14, alpha(TINTA, brilho * 0.6), "center")

    def _cabecalho(self, r: IRenderer) -> None:
        j = self.j
        cap = ROMANOS[j.capitulo - 1] if j.capitulo <= len(ROMANOS) else str(j.capitulo)
        e = j.estado
        posicao = "chefe" if e.chefe else f"luta {e.luta_no_capitulo} de {e.tamanho_capitulo}"
        self._texto(r, 24, 18, f"Capítulo {cap} · {posicao}", 18, alpha(TINTA, 170))
        if j.arco:
            self._texto(r, 24, 42, f"{j.arco.kanji} {j.arco.nome}", 16, alpha(TINTA, 120))
        if e.reliquias:
            kanjis = " ".join(x.kanji for x in e.reliquias)
            self._texto(r, 24, 64, f"宝 {kanjis}", 16, alpha(OURO, 150))
        nome_modo = j.ctx.combate["dificuldades"][j.modo]["nome"]
        self._texto(r, LARGURA - 24, 18, nome_modo, 16, alpha(TINTA, 120), "topright")
        for k, v in enumerate(j.estado.votos.ativos):
            rotulo = " · ".join(x.kanji for x in v.restricoes) + (
                "  (quebra)" if v.de_quebra else ""
            )
            self._texto(
                r, LARGURA - 24, 42 + k * 22, f"誓 {rotulo}", 15, alpha(OURO, 170), "topright"
            )

    def _barra(self, r, x, y, largura, lut: Lutador, cor: Cor) -> None:
        """A vida: a parte perdida há pouco fica branca um instante e se esvai (como nos
        jogos de luta); a cura entra em verde enquanto a barra sobe."""
        vista = self.vida_vista[id(lut)]
        vida = max(0, self._vida(lut))
        escala = largura / lut.vida_max
        r.draw_ui_rect(x, y, largura, 8, LACA)
        r.draw_ui_rect(x, y, escala * max(0.0, vista), 8, alpha((255, 255, 255, 255), 90))
        rastro = self.rastro.get(id(lut))
        if rastro is not None:
            topo, inicio = rastro
            passou = self.relogio - inicio
            if passou < RASTRO_SEGURA + RASTRO_SOME and topo > vida:
                k = max(0.0, passou - RASTRO_SEGURA) / RASTRO_SOME
                ponta = vida + (min(topo, lut.vida_max) - vida) * (1 - ease_out(k))
                branco = alpha((255, 255, 255, 255), 235 * (1 - k * k))
                r.draw_ui_rect(x + escala * vida, y - 1, escala * (ponta - vida), 10, branco)
        r.draw_ui_rect(x, y, escala * min(vida, max(0.0, vista)), 8, cor)
        if vida > vista + 0.3:  # curando: o trecho novo em verde
            r.draw_ui_rect(x + escala * vista, y, escala * (vida - vista), 8, VERDE_JADE)
        if lut.efeitos.morte_abaixo:  # Fio da Navalha: a linha que não pode ser cruzada
            lx = x + largura * lut.efeitos.morte_abaixo
            r.draw_ui_line(lx, y - 3, lx, y + 11, SANGUE_VIVO, 2)

    def _escala_rival(self, rival: Lutador | None = None) -> float:
        if self.bando:
            return ESCALA_BANDO[len(self.luta.rivais)]
        return 1.05 if (rival or self.luta.rival).chefe else 0.92

    def _sinais(self, rival: Lutador) -> list[str]:
        """Os sinais curtos de status do rival (maldição, sangue, bomba, Leva 3...)."""
        sinais = []
        if rival.marca:
            sinais.append(f"呪{rival.marca}")
        if rival.sangue_turnos:
            sinais.append(f"血{rival.sangue}")
        if rival.bombas:
            sinais.append(f"爆{min(b[0] for b in rival.bombas)}")
        if rival.silencio:
            sinais.append("黙")
        if rival.desarme:
            sinais.append("網")
        if rival.exposto:
            sinais.append(f"鷹{rival.exposto}")
        return sinais + _sinais_leva3(rival)

    def _sumico(self, rival: Lutador) -> float | None:
        """Quanto do rival já se desfez (0–1), ou None se ele está de pé. Num bando, quem
        cai se desfaz na hora; o último (e o rival sozinho) se desfaz no fim da luta."""
        if rival.vivo:
            return None
        morte = self.morte.get(id(rival))
        if morte is not None:
            return max(0.0, min(1.0, (self.relogio - morte) / DURACAO_FIM))
        fim = self._fim()
        return fim[0] if fim else 0.0

    def _rival_do_bando(self, r: IRenderer, rival: Lutador, hud: IRenderer | None = None) -> None:
        """Um rival do bando: figura menor, a placa em cima e a intenção nos pés. `r` é
        o mundo (com a câmera); `hud`, a tela parada (a placa)."""
        hud = hud or r
        x, y = self._centro(rival)
        escala = self._escala_rival(rival)
        sumico = self._sumico(rival)
        if sumico is not None and sumico >= 1:
            return  # já se desfez: some, os outros continuam
        visivel = 1.0 if sumico is None else 1 - sumico
        estilo = self.estilos[id(rival)]
        alvo = rival is self.luta.rival and rival.vivo and self.modo != "fim"
        pulso = 0.5 + 0.5 * math.sin(self.relogio * 4)
        cor_enso = alpha(OURO, (60 + 40 * pulso) * visivel) if alvo else alpha(TINTA, 14)
        r.draw_ui_arc(
            x,
            y - 66 * escala,
            92 * escala,
            math.radians(110),
            math.radians(430),
            cor_enso,
            8 if alvo else 6,
        )
        if alvo:  # a pincelada sob os pés de quem você mira
            s = 70 * escala
            r.draw_ui_polygon(
                [
                    (x - s, y + 10),
                    (x + s * 1.05, y + 5),
                    (x + s * 0.9, y + 15),
                    (x - s * 0.8, y + 17),
                ],
                alpha(OURO, 150 + 60 * pulso),
            )
        if sumico:
            vfx.dissolver(r, x, y, sumico, COR_ESTILO.get(estilo, COR_ESTILO["espadachim"]))
        entrada = min(1.0, self.relogio / max(1e-6, self.entrada_ate * 0.45))
        if entrada < 1:  # a entrada: cada um surge da sua mancha de tinta
            raio = (140 * (1 - entrada) + 20) * escala
            r.draw_ui_circle(x, y - 66 * escala, raio, alpha((8, 7, 6, 255), 200 * (1 - entrada)))
            visivel *= entrada
        if visivel <= 0.01:
            visivel = 0.0
        dx, dy = self._deslocamento(rival)
        clarao, clarao_cor = self._clarao(rival)
        if visivel:
            self._marcas_do_chefe(r, rival, x + dx, y + dy, escala)
        if rival.modo is not None and visivel:
            vfx.aura(r, rival.modo_id, x + dx, y + dy - 66 * escala, 0.12, self.relogio)
        desenhar_lutador(
            r,
            x + dx,
            y + dy,
            escala,
            alpha(COR_ESTILO.get(estilo, COR_ESTILO["espadachim"]), 255 * visivel),
            alpha(TINTA, 230 * visivel),
            guarda=1.0 if rival.bloqueio or rival.revide else 0.0,
            clarao=clarao,
            clarao_cor=clarao_cor,
            estilo=estilo,
            tempo=self.relogio + self.fase.get(id(rival), 0.0),
            ataque=self._pose_ataque(rival),
            dano=self._pose_dano(rival),
            respiro=1.6,
        )
        if not visivel:
            return
        self._marcas_por_cima(r, rival, x + dx, y + dy, escala)
        if rival.congelado:
            cor_gelo = alpha((150, 200, 240, 255), 220 * visivel)
            self._texto(r, x + 48 * escala, y - 150 * escala, "氷", 22, cor_gelo, "center")
        elif rival.pular and not rival.quebrado:
            cor_ilusao = alpha(SANGUE_VIVO, 200 * visivel)
            self._texto(r, x + 48 * escala, y - 150 * escala, "幻", 22, cor_ilusao, "center")
        if rival.bloqueio:  # a guarda que o Guardião ergueu
            cor_guarda = alpha((150, 200, 240, 255), 200 * visivel)
            txt = f"{KANJI_PROTEGIDO}{rival.bloqueio}"
            self._texto(r, x - 70 * escala, y - 44 * escala, txt, 18, cor_guarda, "center")
        # a placa: papel e título, vida, sinais
        papel = self._papel(rival)
        titulo = self._titulo(rival)
        if papel is not None:
            titulo = f"{papel.kanji} {titulo}"
        if rival.elite:
            titulo = f"{KANJI_ELITE} {titulo}"
        if rival.nemesis:
            cor_titulo = SANGUE_NEMESIS
        elif alvo:
            cor_titulo = OURO
        else:
            cor_titulo = alpha(TINTA, 190)
        cor_t = alpha(cor_titulo, cor_titulo[3] * visivel)
        self._texto(hud, x, PLACA_Y, titulo, 17, cor_t, "center")
        largura = 140
        self._barra(hud, x - largura / 2, PLACA_Y + 24, largura, rival, SANGUE_VIVO)
        self._guarda(hud, x - largura / 2, PLACA_Y + 34, largura, rival)
        vida = f"{max(0, self._vida(rival))} / {rival.vida_max}"
        self._texto(hud, x, PLACA_Y + 45, vida, 13, alpha(TINTA, 150 * visivel), "center")
        if rival.afixos and rival.vivo:  # os selos da elite, à direita da barra
            pontos = [(x + largura / 2 + 16, PLACA_Y + 26 + i * 24, 10) for i in range(2)]
            self._selos_afixo(hud, rival, pontos)
        sinais = self._sinais(rival)
        if sinais:
            cor_sinais = alpha(mistura(TINTA, (157, 92, 224, 255), 0.7), 255 * visivel)
            self._texto(hud, x, PLACA_Y + 62, " ".join(sinais), 16, cor_sinais, "center")
        if rival.vivo:
            self._intencao_curta(hud, rival, x, y + 20)

    def _intencao_curta(self, r: IRenderer, rival: Lutador, x: float, y: float) -> None:
        """O que você enxerga da próxima ação deste rival, sob os pés dele."""
        if self.j.jogador.cego:
            texto, cor = "→ ?", alpha(TINTA, 100)
        else:
            vista = self.luta.ver_intencao(de=rival)
            if vista is None:
                texto, cor = "→ ?", alpha(TINTA, 100)
            elif isinstance(vista, str):
                texto, cor = f"→ {TIPO_CURTO.get(vista, vista)}", alpha(TINTA, 190)
            else:
                kanji = self.kanji.get(vista.id, "?")
                nome = vista.nome  # curto: os vizinhos estão perto
                cabe = 15 if len(self.luta.rivais) == 3 else 22
                if len(nome) > cabe:
                    nome = nome[: cabe - 1].rstrip(" ,;:") + "…"
                texto = f"→ {kanji} {nome}"
                cor = SANGUE_VIVO if vista.perigosa else alpha(TINTA, 210)
        self._texto(r, x, y, texto, 14, cor, "center")

    def _rival(self, r: IRenderer, hud: IRenderer | None = None) -> None:
        """O rival sozinho: grande, no centro, com a placa no alto da tela. `r` é o
        mundo (com a câmera); `hud`, a tela parada (a placa)."""
        hud = hud or r
        rival = self.luta.rival
        x, y = POS_RIVAL
        dx, dy = self._deslocamento(rival)
        escala = self._escala_rival()
        estilo = self.estilos[id(rival)]
        cor_estilo = COR_ESTILO.get(estilo, COR_ESTILO["espadachim"])
        if rival.chefe:
            r.draw_ui_circle(x, y - 66, 86, alpha(SANGUE_VIVO, 24))
        elif rival.nemesis:
            r.draw_ui_circle(x, y - 66, 86, alpha(SANGUE_NEMESIS, 30))
        clarao, clarao_cor = self._clarao(rival)
        visivel = 1.0
        fim = self._fim()
        if fim and fim[1]:  # venceu: o rival se desfaz em tinta
            visivel = 1 - fim[0]
            vfx.dissolver(r, x, y, fim[0], cor_estilo)
        entrada = min(1.0, self.relogio / max(1e-6, self.entrada_ate * 0.45))
        if entrada < 1:  # a entrada: o rival surge de uma mancha de tinta
            r.draw_ui_circle(
                x, y - 66, 140 * (1 - entrada) + 20, alpha((8, 7, 6, 255), 200 * (1 - entrada))
            )
            visivel *= entrada
        if visivel <= 0.01:
            visivel = 0.0
        if visivel:
            self._marcas_do_chefe(r, rival, x + dx, y + dy, escala)
        visivel *= self._translucido(rival)
        if rival.modo is not None and visivel:  # o rival transformado
            vfx.aura(r, rival.modo_id, x + dx, y + dy - 66 * escala, 0.12, self.relogio)
        desenhar_lutador(
            r,
            x + dx,
            y + dy,
            escala,
            alpha(cor_estilo, 255 * visivel),
            alpha(TINTA, 230 * visivel),
            guarda=1.0 if rival.bloqueio or rival.revide else 0.0,
            clarao=clarao,
            clarao_cor=clarao_cor,
            estilo=estilo,
            tempo=self.relogio + self.fase.get(id(rival), 0.0),
            ataque=self._pose_ataque(rival),
            dano=self._pose_dano(rival),
            respiro=1.6,
        )
        if visivel:
            self._marcas_por_cima(r, rival, x + dx, y + dy, escala)
        if rival.congelado:  # preso no gelo
            cor_gelo = alpha((150, 200, 240, 255), 220)
            self._texto(r, x + 78, y - 168, "氷", 26, cor_gelo, "center")
        elif rival.pular and not rival.quebrado:  # preso na ilusão
            self._texto(r, x + 78, y - 168, "幻", 26, alpha(SANGUE_VIVO, 200), "center")
        r = hud  # a placa no alto da tela não balança com a câmera
        nome = self._titulo(rival)
        if rival.nemesis:
            cor_nome = mistura(SANGUE_NEMESIS, TINTA, 0.45)
        elif rival.elite:
            nome, cor_nome = f"{KANJI_ELITE} {nome}", OURO
        else:
            cor_nome = TINTA
        tam = 22 if len(nome) <= 34 else max(15, round(22 * 34 / len(nome)))  # a Nêmesis
        self._texto(r, x, 36 + (22 - tam) / 2, nome, tam, cor_nome, "center")
        self._barra(r, x - 120, 72, 240, rival, SANGUE_VIVO)
        self._guarda(r, x - 120, 84, 240, rival)
        vida = f"{max(0, self._vida(rival))} / {rival.vida_max}"
        self._texto(r, x + 130, 64, vida, 15, alpha(TINTA, 150))
        rotulo = self._rotulo_mecanica(rival)
        if rotulo:  # a mecânica do chefe, sob a barra
            self._texto(r, x, 100, rotulo, 16, alpha(mistura(OURO, TINTA, 0.3), 220), "center")
        elif rival.afixos and rival.vivo:  # os selos da elite, sob a barra
            n = len(rival.afixos)
            pontos = [(x + (i - (n - 1) / 2) * 30, 104, 12) for i in range(n)]
            self._selos_afixo(r, rival, pontos)
        sinais = self._sinais(rival)
        if sinais:
            self._texto(
                r,
                x - 130,
                62,
                " ".join(sinais),
                20,
                mistura(TINTA, (157, 92, 224, 255), 0.7),
                "topright",
            )

    def _intencao(self, r: IRenderer) -> None:
        x, y = 660, 150
        r.draw_ui_rect(x - 14, y - 14, 276, 100, alpha(LACA, 230))
        rotulo = "próxima ação do rival"
        if self.bando:  # o painel detalha o alvo; os outros mostram o resumo nos pés
            rotulo = f"próxima ação · {self.luta.rival.titulo or self.luta.rival.nome}"
        self._texto(r, x, y - 6, rotulo, 14, alpha(OURO if self.bando else TINTA, 120))
        vista = self.luta.ver_intencao()
        if self.j.jogador.cego:
            self._texto(r, x, y + 22, "você está cego", 18, SANGUE_VIVO)
            self._texto(r, x, y + 46, "(o preço do Olho Roubado)", 14, alpha(TINTA, 90))
        elif vista is None:
            self._texto(r, x, y + 22, "você não consegue ler", 18, alpha(TINTA, 110))
            self._texto(r, x, y + 46, "(Percepção 0)", 14, alpha(TINTA, 90))
        elif isinstance(vista, str):
            self._texto(r, x, y + 22, f"prepara {NOMES_TIPO.get(vista, vista)}", 19, TINTA)
            self._texto(r, x, y + 46, "(Percepção 1: só o tipo)", 14, alpha(TINTA, 90))
        else:
            cor = SANGUE_VIVO if vista.perigosa else TINTA
            kanji = self.kanji.get(vista.id, "?")
            self._texto(r, x, y + 12, kanji, 34, cor)
            self._texto(r, x + 46, y + 16, vista.nome, 19, cor)
            detalhe = f"dano {vista.dano * vista.golpes}" if vista.dano else vista.tipo
            if vista.perigosa:
                detalhe += f" · perigosa · sutil {vista.sutileza}"
            self._texto(r, x + 46, y + 42, detalhe, 14, alpha(TINTA, 140))
        self._linha_status(r, x, y + 62, vista)

    def _linha_status(self, r: IRenderer, x: float, y: float, vista) -> None:
        """A última linha do painel: a origem, os afixos e a mecânica (alternando)."""
        linhas = self._status(self.luta.rival, vista)
        self.foco_status = ""
        if not linhas:
            return
        foco, texto = linhas[int(self.relogio / 3.2) % len(linhas)]
        self.foco_status = foco
        if texto.startswith("※"):
            self._texto(r, x, y, texto, 12, alpha(TINTA, 100))
            return
        partes = quebrar(texto, 35)
        if len(partes) > 2:
            partes = [partes[0], partes[1][:33].rstrip(" ,;:") + "…"]
        for k, linha in enumerate(partes):
            self._texto(r, x, y - 4 + k * 14, linha, 12, alpha(mistura(OURO, TINTA, 0.35), 200))

    def _painel_voto(self, r: IRenderer) -> None:
        v = self.luta.voto_luta
        if v is None:
            return
        x, y = 660, 246
        r.draw_ui_rect(x - 14, y - 8, 276, 64, alpha(LACA, 220))
        tipo = TIPOS_VOTO[v.tipo]
        if not self.luta.voto_jurado:
            cor = OURO if self.luta.pode_jurar_luta() else alpha(TINTA, 120)
            self._texto(r, x, y - 2, f"約 voto de luta · {tipo}", 14, alpha(TINTA, 130))
            self._texto(r, x, y + 18, f"{v.kanji} {v.nome}", 19, cor)
            self._texto(r, x + 200, y + 22, "V jura", 13, alpha(TINTA, 110))
            return
        self._texto(r, x, y - 2, f"約 jurado · {tipo}", 14, alpha(OURO, 160))
        self._texto(r, x, y + 18, f"{v.kanji} {v.nome}", 19, OURO)
        p = self.luta.promessa
        if p is not None:
            meta = CONDICAO[p.condicao].format(p.restante, meta=p.meta)
            if p.condicao == "dano_em":
                meta += f" · feito {p.feito}"
            self._texto(r, x, y + 40, meta, 13, alpha(TINTA, 140))
        elif self.luta.promessa_resultado:
            cor = OURO if self.luta.promessa_resultado == "cumprida" else SANGUE_VIVO
            self._texto(r, x, y + 40, f"promessa {self.luta.promessa_resultado}", 13, cor)

    def _modal_voto(self, r: IRenderer) -> None:
        if self.modo != "voto":
            return
        v = self.luta.voto_luta
        r.draw_ui_rect(0, 0, LARGURA, ALTURA, alpha(FUNDO, 170))
        x0, y0, x1, y1 = 200, 170, 760, 430
        r.draw_ui_rect(x0, y0, x1 - x0, y1 - y0, alpha(LACA, 245))
        r.draw_ui_rect(x0, y0, x1 - x0, 4, OURO)
        self._texto(r, x0 + 30, y0 + 22, v.kanji, 54, OURO)
        self._texto(r, x0 + 110, y0 + 26, v.nome, 30, TINTA)
        self._texto(
            r, x0 + 110, y0 + 64, f"voto de luta · {TIPOS_VOTO[v.tipo]}", 16, alpha(TINTA, 140)
        )
        for k, linha in enumerate(quebrar(v.texto, 58)[:5]):
            self._texto(r, x0 + 30, y0 + 110 + k * 22, linha, 17, TINTA)
        if v.origem:
            self._texto(r, x0 + 30, y1 - 52, f"※ {v.origem}", 13, alpha(TINTA, 100))
        self._texto(
            r,
            (x0 + x1) / 2,
            y1 - 26,
            "Enter jura (não gasta o turno) · Backspace volta",
            15,
            alpha(OURO, 200),
            "center",
        )

    def _corrente(self, r: IRenderer) -> None:
        carma = self.j.carma
        frac = carma.valor / carma.config.maximo
        cheio = carma.transbordando
        y, x0, x1, elos = 330, 70, 890, 30
        passo = (x1 - x0) / elos
        pulso = 0.5 + 0.5 * math.sin(self.relogio * 6)
        for i in range(elos):
            x = x0 + i * passo + passo / 2
            ativo = i < round(frac * elos)
            cor = FERRO
            if ativo:
                cor = mistura(FERRO, SANGUE_VIVO, (0.65 + 0.35 * pulso) if cheio else 0.45)
            if i % 2 == 0:
                r.draw_ui_polygon(
                    [
                        (x - 11, y),
                        (x - 6, y - 5),
                        (x + 6, y - 5),
                        (x + 11, y),
                        (x + 6, y + 5),
                        (x - 6, y + 5),
                    ],
                    cor,
                    2,
                )
            else:
                r.draw_ui_line(x - 13, y, x + 13, y, cor, 3)
        self._texto(r, 24, y - 12, "業", 24, OURO)
        guardados = carma.guardados
        if (
            self.luta.pode_despertar()
            and self.luta.vez is self.j.jogador
            and self.modo == "escolher"
        ):
            brilho = 160 + 95 * pulso
            extra = f" ({guardados} guardado{'s' if guardados > 1 else ''})" if guardados else ""
            self._texto(r, 480, y + 14, f"E · DESPERTAR{extra}", 18, alpha(OURO, brilho), "center")
        elif cheio:
            self._texto(
                r,
                480,
                y + 16,
                "transbordando: desperte (E), ou à beira da morte",
                15,
                SANGUE_VIVO,
                "center",
            )
        else:
            self._texto(
                r,
                480,
                y + 16,
                f"Carma {carma.valor:.0f} / {carma.config.maximo:.0f}",
                14,
                alpha(TINTA, 120),
                "center",
            )

    def _jogador(self, r: IRenderer, hud: IRenderer | None = None) -> None:
        """Você: a figura no mundo (`r`, com a câmera) e o cabeçalho na tela (`hud`)."""
        hud = hud or r
        j = self.j.jogador
        x, y = POS_JOGADOR
        dx, dy = self._deslocamento(j)
        clarao, clarao_cor = self._clarao(j)
        guarda = 1.0 if j.bloqueio or j.revide else 0.0
        auras = ((j.forma, "forma_desperta"), (j.instinto, "instinto_puro"), (j.modo, j.modo_id))
        for ativo, aura in auras:
            if ativo:  # a aura fica enquanto o Despertar (ou a transformação) dura
                vfx.aura(r, aura, x + dx, y + dy - 66 * ESCALA_JOGADOR, 0.12, self.relogio)
        fim = self._fim()
        cai = fim[0] if fim and not fim[1] else 0.0  # perdeu: você cai e as correntes fecham
        desenhar_lutador(
            r,
            x + dx,
            y + dy + 40 * cai,
            ESCALA_JOGADOR,
            alpha(TINTA, 255 * (1 - 0.6 * cai)),
            alpha((255, 255, 255, 255), 200 * (1 - 0.6 * cai)),
            guarda=guarda,
            clarao=clarao,
            clarao_cor=clarao_cor,
            tempo=self.relogio + self.fase.get(id(j), 0.0),
            ataque=self._pose_ataque(j),
            dano=max(self._pose_dano(j), cai),
            costas=True,
            respiro=1.6 * (1 - cai),
        )
        if cai:
            vfx.correntes_fechando(r, x, y - 66 * ESCALA_JOGADOR, cai)
        r = hud
        self._texto(r, 40, 360, "Você", 22, TINTA)
        dom = f"{self.j.dom.kanji} {self.j.dom.nome}" if self.j.dom else ""
        self._texto(r, 106, 365, dom, 15, alpha(TINTA, 130))
        self._barra(r, 40, 394, 250, j, TINTA)
        self._ressonancias(r)
        perc = j.percepcao + j.percepcao_luta
        info = f"{max(0, self._vida(j))} / {j.vida_max} · Vel {j.velocidade} · Perc {perc}"
        self._texto(r, 40, 406, info, 15, alpha(TINTA, 150))
        estados = []
        if j.bloqueio:
            estados.append(f"守 bloqueio {j.bloqueio}")
        if j.revide:
            estados.append(f"返 revide {j.revide}")
        if j.marca:
            estados.append(f"呪 {j.marca} (recarga +1)")
        if j.eco:
            estados.append(f"eco {j.eco}")
        if j.santuario:
            estados.append(f"域 santuário {j.santuario}")
        if j.pular:
            estados.append("perde o próximo turno")
        if j.escudos:
            estados.append(f"灰 escudo {j.escudos}")
        if self.j.estado.mesa.carma.guardados:
            estados.append(f"封 {self.j.estado.mesa.carma.guardados} guardado")
        if j.forma:
            estados.append(f"醒 forma desperta {j.forma}")
        if j.retrib_golpes:
            estados.append(f"報 +{j.retrib_por_golpe} × {j.retrib_golpes}")
        if j.instinto:
            estados.append(f"極 instinto {j.instinto}")
        if j.dano_mult > 1:
            estados.append(f"痣 dano ×{j.dano_mult:.1f}".replace(".", ","))
        if j.sangue_turnos:
            estados.append(f"血 sangra {j.sangue} (cura ½)")
        if j.silencio:
            estados.append(f"黙 silêncio {j.silencio}")
        if j.desarme:
            estados.append(f"網 sem defesa {j.desarme}")
        if j.espelho:
            estados.append(f"鏡 espelho {j.espelho}")
        if j.regen_luta:
            estados.append(f"息 +{j.regen_luta}/turno")
        if j.bombas:
            estados.append(f"爆 bomba em {min(b[0] for b in j.bombas)}")
        if j.absolutos:
            estados.append(f"界 absoluto {j.absolutos}")
        if j.modo is not None:
            nome = j.modo.nome or self.nomes.get(j.modo_id, "transformado")
            estados.insert(0, f"変 {nome} {j.modo_turnos}")
        estados += _sinais_leva3(j, longo=True)
        linhas = quebrar("   ".join(estados), 70)[:2]
        for k, linha in enumerate(linhas):
            self._texto(r, 40, 428 + k * 16, linha, 15, alpha(OURO, 170))

    def _selos(self, r: IRenderer) -> None:
        slots = self.slots()
        sac = self.modo == "sacrificio"
        for i, t in enumerate(slots):
            x = self._pos_selo(i, len(slots))
            y = SELO_Y
            if t is None:
                r.draw_ui_circle(x, y, RAIO_SELO, alpha(FERRO, 120), 1)
                self._texto(r, x, y + 40, "vazio", 14, alpha(TINTA, 70), "center")
                continue
            pronta = self._disponivel(t)
            raridade = getattr(t, "raridade", "cinza")
            cor = (
                self.cor_raridade.get(raridade, TINTA)
                if t not in (self.luta.basico, HESITAR)
                else TINTA
            )
            if sac:
                alvo_ok = t not in (
                    self.luta.basico,
                    HESITAR,
                    self.contrato,
                    self.j.jogador.tecnica_dom,
                    self.j.jogador.tecnica_linhagem,
                )
                cor = OURO if alvo_ok else alpha(FERRO, 140)
                pronta = alvo_ok
            selecionado = i == self.cursor
            if selecionado:
                r.draw_ui_circle(x, y, RAIO_SELO + 10, alpha(cor, 60))
            r.draw_ui_circle(x, y, RAIO_SELO, LACA)
            r.draw_ui_circle(
                x, y, RAIO_SELO, cor if pronta else alpha(FERRO, 160), 3 if selecionado else 2
            )
            kanji = self.kanji.get(t.id, "?")
            self._texto(
                r,
                x,
                y - 2,
                kanji,
                30,
                mistura(cor, TINTA, 0.35) if pronta else alpha(TINTA, 70),
                "center",
            )
            espera = self.j.jogador.recargas.get(t.id, 0)
            if espera and not sac:
                r.draw_ui_circle(x + 22, y - 22, 11, SANGUE_VIVO)
                self._texto(r, x + 22, y - 23, str(espera), 15, TINTA, "center")
            jj = self.j.jogador
            if (
                t.tipo in jj.efeitos.proibir_tipos
                or t.tipo in jj.proibir_luta
                or (t is self.luta.basico and (jj.efeitos.proibir_basico or jj.sem_basico_luta))
            ):
                self._texto(r, x - 22, y - 34, "縛", 18, SANGUE_VIVO, "center")
            r.draw_ui_circle(x - 25, y - 25, 10, LACA)
            self._texto(r, x - 25, y - 26, str(i + 1), 14, alpha(TINTA, 160), "center")
            nome = quebrar(t.nome, 13)[:2]  # nomes longos em duas linhas, para não colidir
            for k, linha in enumerate(nome):
                cor_nome = TINTA if pronta else alpha(TINTA, 90)
                self._texto(r, x, y + 38 + k * 16, linha, 14, cor_nome, "center")
            yr = y + 40 + len(nome) * 16
            cor_resumo = alpha(TINTA, 110 if pronta else 60)
            self._texto(r, x, yr, self._resumo(t), 13, cor_resumo, "center")

    def _resumo(self, t: Tecnica) -> str:
        j = self.j.jogador
        if t.copia_rival:
            roubada = self.luta.ultima_tecnica(self.luta.rival)
            return f"rouba {roubada.nome}" if roubada else "nada a roubar"
        if t.santuario:
            return f"santuário {t.santuario}"
        if t.turno_extra:
            return "2 ações" + (f" · -{t.custo_vida} vida" if t.custo_vida else "")
        if t.consome_carma:
            return f"{int(t.dano_por_carma * self.j.carma.valor)} · gasta o Carma"
        partes = []
        if t.dano_por_dor:
            partes.append(f"{t.dano + _extra_da_dor(t, j)} · dor")
        elif t.dano:
            partes.append(
                f"{t.dano}×{t.golpes}" if t.golpes > 1 else f"{t.dano + j.efeitos.bonus_dano}"
            )
        if t.absoluto:
            partes.append("absoluto")
        elif t.perfura:
            partes.append("fura")
        if t.critico:
            partes.append(f"{t.critico:.0%} ×2,5")
        if t.cura:
            partes.append(f"cura {t.cura}")
        if t.selar:
            partes.append("sela")
        if t.atordoar:
            partes.append("atordoa")
        if t.bloqueio:
            partes.append(f"bloq {t.bloqueio}")
        if t.revide:
            partes.append(f"revide {t.revide}")
        if t.marca:
            partes.append(f"呪{t.marca}")
        if t.consome_tecnica:
            partes.append("pacto")
        if t.modo is not None:
            partes.append(f"forma {t.modo.turnos}")
        if t.chama_eterna:
            partes.append(f"炎{t.chama_eterna}")
        if t.veneno:
            partes.append(f"毒{t.veneno}")
        if t.congelar:
            partes.append("congela")
        if t.clones:
            partes.append(f"clones {t.clones}")
        if t.invocar:
            partes.append(f"invoca {t.invocar}×{t.invocar_turnos}")
        if t.vinculo:
            partes.append("ritual")
        if t.purificar:
            partes.append("purifica")
        if t.livre:
            partes.append("livre")
        return " · ".join(partes) or t.tipo

    def _rodape(self, r: IRenderer) -> None:
        if self.modo == "sacrificio":
            self._texto(
                r,
                624,
                606,
                "契 Qual técnica o pacto leva? (número, ou ← → e Enter) · Backspace desiste",
                16,
                OURO,
                "center",
            )
            return
        dica_alvo = len(self.luta.vivos) > 1 and not self.luta.acabou and self.modo == "escolher"
        if dica_alvo:  # a dica de controle só aparece com mais de um rival de pé
            self._texto(
                r, LARGURA - 14, ALTURA - 20, "↑ ↓ / Tab: alvo", 13, alpha(OURO, 150), "topright"
            )
        if self.relogio < self.aviso_ate:
            self._texto(r, 624, 606, self.aviso, 16, SANGUE_VIVO, "center")
            return
        if self.cutin is not None and self.relogio < self.cutin[1] + DURACAO_CUTIN:
            return  # o cut-in toca: o registro (o resultado) espera o golpe sair
        largura = 54 if dica_alvo else 62
        x = 604 if dica_alvo else 624
        for k, linha in enumerate(quebrar(self.registro, largura)[:2]):
            self._texto(r, x, 598 + k * 18, linha, 14, alpha(TINTA, 150), "center")

    def _banner(self, r: IRenderer) -> None:
        venceu = self.luta.vencedor is self.j.jogador
        r.draw_ui_rect(0, 250, LARGURA, 150, alpha(FUNDO, 220))
        cor_traco = OURO if venceu else SANGUE_VIVO  # uma pincelada atrás do título
        r.draw_ui_polygon([(170, 286), (790, 276), (780, 330), (180, 338)], alpha(cor_traco, 40))
        if venceu:
            titulo, cor = ("勝  Vitória", OURO)
        elif self.luta.estourou_prazo:
            titulo, cor = ("限  O prazo do seu voto venceu", SANGUE_VIVO)
        else:
            titulo, cor = ("敗  Você caiu", SANGUE_VIVO)
        self._texto(r, 480, 300, titulo, 44, cor, "center")
        self._texto(r, 480, 356, "Enter para continuar", 16, alpha(TINTA, 140), "center")
