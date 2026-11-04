"""Tela de luta: duelo frente a frente, rival em cima, você embaixo.

Só apresentação: cada ação passa pela `Luta` (regras) na hora em que é escolhida,
e a tela anima o `Acao` que voltou. Enquanto uma animação toca, a entrada fica
travada; o rival age sozinho depois de uma pausa curta.
"""

from __future__ import annotations

import math
from dataclasses import dataclass

from ouroboros.bootstrap.scene import IScene
from ouroboros.interfaces.input_provider import IInputProvider
from ouroboros.interfaces.renderer import IRenderer

from karmabound import som, vfx
from karmabound.arenas import desenhar_arena, desenhar_frente
from karmabound.combate import HESITAR, Acao, Luta, Lutador, Tecnica, _extra_da_dor
from karmabound.figuras import ESTILOS, desenhar_lutador
from karmabound.jornada import Jornada
from karmabound.opcoes import OPCOES
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

POS_RIVAL = (480, 282)
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
NOMES_TIPO = {"ataque": "um ATAQUE", "defesa": "uma DEFESA", "maldita": "algo MALDITO"}
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
    """Número ou palavra que sobe e some (dano, 'percebeu!', 'surpresa!')."""

    x: float
    y: float
    texto: str
    cor: Cor
    inicio: float
    tamanho: int = 30


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
        self.vida_vista = {
            id(self.j.jogador): self.j.jogador.vida,
            id(self.luta.rival): self.luta.rival.vida,
        }
        self.aviso = ""
        self.aviso_ate = 0.0
        self.desperto: tuple[object, float] | None = None  # (fatia, início) da cena do Despertar
        # o efeito tocando: (nome, quem age, quem recebe, início, crítico)
        self.efeito: tuple[str, Lutador, Lutador, float, bool] | None = None
        rival = self.luta.rival
        self.estilo_rival = (
            "colosso"
            if rival.chefe
            else ESTILOS[(jornada.n_luta * 5 + jornada.capitulo) % len(ESTILOS)]
        )
        self.registro = (
            "A luta começa." if self.luta.vez is self.j.jogador else "O rival se move primeiro."
        )
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
        ids = {t.id for t in self.luta.rival.tecnicas}
        self.assinatura = next((f for f in jornada.ctx.chefes if f.id in ids), None)
        if self.assinatura is not None and jornada.grimorio is not None:
            jornada.grimorio.ver([self.assinatura])
        self.origens[jornada.ctx.basico.id] = jornada.ctx.combate["golpe_basico"].get("origem", "")
        self.promessa_vista = ""  # para anunciar quando a promessa se cumpre ou se quebra

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
        for t in [*self.j.jogador.tecnicas, *self.luta.rival.tecnicas]:
            if t.id == tid:
                return t.nome  # com o nível, se evoluiu
        return self.nomes.get(tid, tid)

    def _executar(self, t: Tecnica, sacrificio: Tecnica | None = None) -> None:
        self._animar(self.luta.resolver(t, sacrificio))

    def _animar(self, acao: Acao) -> None:
        j, rival = self.j.jogador, self.luta.rival
        ator = j if acao.ator == j.nome else rival
        alvo = rival if ator is j else j
        self.golpe = (ator, self.relogio)
        tecnica = next(
            (
                t
                for t in [*ator.tecnicas, ator.tecnica_dom, ator.tecnica_linhagem]
                if t and t.id == acao.tecnica
            ),
            None,
        )
        nome_efeito = vfx.efeito_de(acao.tecnica, tecnica.tipo if tecnica else "ataque")
        if acao.copiou:  # o Olho Roubado toca o efeito da técnica roubada, depois do olho
            nome_efeito = "olho"
        self.efeito = (nome_efeito, ator, alvo, self.relogio, acao.critico)
        som.tocar("critico" if acao.critico else som.SOM_DO_EFEITO.get(nome_efeito, "golpe"))
        if acao.reagiu:
            som.tocar("percebeu")
        if acao.reagiu or (ator is rival and tecnica is not None and tecnica.perigosa):
            self.ao_dica("percepcao")
        if acao.esquivas or acao.escudados or acao.instintos:
            som.tocar("defesa")
        if acao.dano and alvo is j:
            som.tocar("dano", 0.6)
        if acao.dano and len(self.manchas) < 24:  # o golpe deixa a sua marca no chão
            px, py = self._centro(alvo)
            semente = self.relogio * 7.3
            tam = min(34, 10 + acao.dano * 0.8)
            self.manchas.append((px + math.sin(semente) * 30, py + 4, tam, semente))
        self.anim_ate = self.relogio + max(DURACAO_ACAO, vfx.duracao(nome_efeito))
        ax, ay = self._centro(alvo)
        bx, by = self._centro(ator)
        nome = self._nome(acao.tecnica)
        partes = [f"{'Você' if ator is j else 'O rival'}: {nome}"]
        if acao.surpresa and not acao.reagiu:
            self.textos.append(Texto(ax, ay - 110, "surpresa!", OURO, self.relogio, 22))
        if acao.dano:
            self.tremor[id(alvo)] = self.relogio
            self.textos.append(
                Texto(ax + 30, ay - 70, f"-{acao.dano}", SANGUE_VIVO, self.relogio, 34)
            )
            partes.append(f"{acao.dano} de dano")
        if acao.reagiu:
            self.textos.append(Texto(ax - 40, ay - 92, "percebeu!", VERDE_JADE, self.relogio, 22))
            self.tremor[id(ator)] = self.relogio + 0.2
            partes.append("percebido: metade, e contra-golpe")
        if acao.destruida:
            self.textos.append(
                Texto(
                    bx,
                    by - 150,
                    f"契 {self._nome(acao.destruida)} se desfaz",
                    OURO,
                    self.relogio,
                    18,
                )
            )
            partes.append(f"o pacto levou {self._nome(acao.destruida)}")
        if acao.copiou:
            partes[0] += f" (roubou {self._nome(acao.copiou)})"
        if acao.esquivas:
            self.textos.append(Texto(ax - 30, ay - 120, "esquivou!", VERDE_JADE, self.relogio, 22))
            partes.append("esquivou")
        if acao.escudados:
            self.textos.append(Texto(ax + 40, ay - 120, "escudo!", TINTA, self.relogio, 20))
            partes.append("o escudo segurou")
        if acao.sombra:
            partes.append(f"a sombra fez {acao.sombra}")
        if acao.turno_extra:
            self.textos.append(Texto(bx, by - 150, "刻 ação extra!", OURO, self.relogio, 20))
            partes.append("e age de novo")
        if acao.critico:
            self.textos.append(Texto(ax, ay - 150, "黒閃!", SANGUE_VIVO, self.relogio, 30))
            partes.append("Clarão Negro: ×2,5")
        if acao.curou:
            self.textos.append(Texto(bx, by - 120, f"+{acao.curou}", VERDE_JADE, self.relogio, 30))
            partes.append(f"curou {acao.curou}")
        if acao.selou:
            self.textos.append(Texto(ax, ay - 130, "鎖 selado!", OURO, self.relogio, 22))
            partes.append(f"selou {self._nome(acao.selou)}")
        if acao.atordoou:
            self.textos.append(
                Texto(ax, ay - 130, "幻 perde o turno", SANGUE_VIVO, self.relogio, 20)
            )
            partes.append("perde o próximo turno")
        if acao.instintos:
            self.textos.append(Texto(ax, ay - 120, "極 esquivou!", TINTA, self.relogio, 22))
            partes.append("o instinto esquivou e revidou")
        if acao.despertou:
            partes.append("o golpe fatal não veio: você despertou")
        self.registro = " · ".join(partes)
        self._anunciar_promessa()
        if acao.despertou:
            self._celebrar(self.luta.ultimo_despertar)
        if self.luta.vez is rival:
            self.proxima_rival = self.anim_ate + PAUSA_RIVAL

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
                self.textos.append(
                    Texto(x, y - 170, "約 promessa cumprida", OURO, self.relogio, 22)
                )
                som.tocar("revela_divino")
            else:
                self.textos.append(
                    Texto(x, y - 170, "約 promessa quebrada", SANGUE_VIVO, self.relogio, 22)
                )
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
            self.textos.append(Texto(x, y - 150, f"約 {v.nome}", OURO, self.relogio, 24))
            self.registro = f"約 Você jurou: {v.nome}"
            self.anim_ate = self.relogio + 0.6
            self._anunciar_promessa()

    def _musica(self) -> None:
        if self.luta.rival.chefe:
            som.musica("chefe")
        else:
            som.musica("luta_carma" if self.j.carma.transbordando else "luta")

    def update(self, world, delta_time: float) -> None:
        delta_time *= OPCOES.velocidade  # a velocidade das animações, das opções
        self.relogio += delta_time
        e = self.entrada
        if self.primeiro_quadro:
            self.primeiro_quadro = False
            som.tocar("chefe_entra" if self.luta.rival.chefe else "rival_entra")
        self._musica()
        self.textos = [t for t in self.textos if self.relogio - t.inicio < 1.1]
        for lut in (self.j.jogador, self.luta.rival):  # a barra de vida desce devagar
            vista = self.vida_vista[id(lut)]
            self.vida_vista[id(lut)] = vista + (lut.vida - vista) * min(1.0, delta_time * 8)
        if e.is_action_pressed("sair"):
            self.ao_sair()
            return
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
        if self.luta.vez is self.luta.rival:
            if self.relogio >= self.proxima_rival:
                self._animar(self.luta.turno_rival())
            return

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
        return POS_JOGADOR if lutador is self.j.jogador else POS_RIVAL

    def _deslocamento(self, lutador: Lutador) -> tuple[float, float]:
        dx = dy = 0.0
        if self.golpe and self.golpe[0] is lutador:
            k = (self.relogio - self.golpe[1]) / DURACAO_ACAO
            if 0 <= k < 1:
                avanço = math.sin(min(k / 0.5, 1) * math.pi) * 34  # vai e volta
                sentido = -1 if lutador is self.j.jogador else 1
                dx, dy = -sentido * avanço * 0.55, sentido * avanço
        inicio = self.tremor.get(id(lutador))
        if inicio is not None and 0 <= self.relogio - inicio < 0.35:
            forca = 7 * (1 - (self.relogio - inicio) / 0.35)
            dx += math.sin(self.relogio * 90) * forca
        return dx, dy

    def _pose_ataque(self, lutador: Lutador) -> float:
        if self.golpe and self.golpe[0] is lutador:
            k = (self.relogio - self.golpe[1]) / DURACAO_ACAO
            if 0 <= k < 1:
                return math.sin(k * math.pi)
        return 0.0

    def _pose_dano(self, lutador: Lutador) -> float:
        inicio = self.tremor.get(id(lutador))
        if inicio is not None and 0 <= self.relogio - inicio < 0.35:
            return 1 - (self.relogio - inicio) / 0.35
        return 0.0

    def _abalo(self) -> float:
        """O tremor da cena quando um golpe acerta."""
        forca = max(self._pose_dano(self.luta.rival), self._pose_dano(self.j.jogador))
        return math.sin(self.relogio * 70) * 6 * forca

    def _texto(self, r: IRenderer, x, y, texto, tam, cor, anchor="topleft") -> None:
        r.draw_text(x, y, texto, tam, cor, anchor=anchor, font_id=FONTE_PINCEL)

    def render(self, world, renderer: IRenderer) -> None:
        r = renderer
        arco = self.j.arco.id if self.j.arco else None
        abalo = self._abalo()
        desenhar_arena(r, arco, self.relogio, abalo)
        for mx, my, tam, semente in self.manchas:
            vfx.mancha_de_sangue(r, mx, my, tam, semente)
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
        self._rival(r)
        self._jogador(r)
        self._efeito(r)
        desenhar_frente(r, arco, self.relogio, abalo)
        vfx.vinheta(r, 1.0)
        vfx.grao(r, self.relogio)
        self._cabecalho(r)
        self._intencao(r)
        self._painel_voto(r)
        self._corrente(r)
        self._selos(r)
        self._origem(r)
        self._rodape(r)
        for t in self.textos:
            k = (self.relogio - t.inicio) / 1.1
            self._texto(
                r,
                t.x,
                t.y - 36 * ease_out(k),
                t.texto,
                t.tamanho,
                alpha(t.cor, 255 * (1 - k**2)),
                "center",
            )
        self._modal_voto(r)
        self._cena_despertar(r)
        self._entrada_do_rival(r)
        if self.modo == "fim" and self.relogio >= self.anim_ate:
            self._banner(r)
        vfx.revelar(r, self.relogio)

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
            kanji = KANJI_ESTILO[self.estilo_rival]
            nome = "Chefe do capítulo" if rival.chefe else NOME_ESTILO[self.estilo_rival]
            arco = self.j.arco.nome if self.j.arco else ""
            sub = (
                f"Capítulo {self.j.capitulo} · {arco}"
                if rival.chefe
                else f"Rival {self.j.n_luta} · {arco}"
            )
            cor = SANGUE_VIVO if rival.chefe else OURO
            self._texto(r, 300, y0 + 6, kanji, 70, alpha(cor, brilho), "center")
            self._texto(r, 360, y0 + 18, nome, 36, alpha(TINTA, brilho))
            if self.assinatura is not None:
                a = self.assinatura
                sub = f"{sub} · {a.kanji} {a.nome}"
            self._texto(r, 362, y0 + 62, sub, 16, alpha(TINTA, brilho * 0.6))

    def _corpo(self, lutador: Lutador) -> tuple[float, float]:
        """O centro do corpo (os efeitos saem e chegam aqui), com o deslocamento do golpe."""
        x, y = self._centro(lutador)
        dx, dy = self._deslocamento(lutador)
        escala = ESCALA_JOGADOR if lutador is self.j.jogador else self._escala_rival()
        return x + dx, y + dy - 66 * escala

    def _efeito(self, r: IRenderer) -> None:
        if self.efeito is None:
            return
        nome, ator, alvo, inicio, forte = self.efeito
        k = (self.relogio - inicio) / vfx.duracao(nome)
        vfx.desenhar(r, nome, self._corpo(ator), self._corpo(alvo), k, self.relogio, forte)

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
        vista = self.vida_vista[id(lut)]
        r.draw_ui_rect(x, y, largura, 8, LACA)
        r.draw_ui_rect(
            x, y, largura * max(0.0, vista) / lut.vida_max, 8, alpha((255, 255, 255, 255), 90)
        )
        r.draw_ui_rect(x, y, largura * max(0, lut.vida) / lut.vida_max, 8, cor)
        if lut.efeitos.morte_abaixo:  # Fio da Navalha: a linha que não pode ser cruzada
            lx = x + largura * lut.efeitos.morte_abaixo
            r.draw_ui_line(lx, y - 3, lx, y + 11, SANGUE_VIVO, 2)

    def _escala_rival(self) -> float:
        return 1.05 if self.luta.rival.chefe else 0.92

    def _rival(self, r: IRenderer) -> None:
        rival = self.luta.rival
        x, y = POS_RIVAL
        dx, dy = self._deslocamento(rival)
        escala = self._escala_rival()
        if rival.chefe:
            r.draw_ui_circle(x, y - 66, 86, alpha(SANGUE_VIVO, 24))
        clarao = 0.0
        inicio = self.tremor.get(id(rival))
        if inicio is not None and 0 <= self.relogio - inicio < 0.3:
            clarao = 1 - (self.relogio - inicio) / 0.3
        visivel = 1.0
        fim = self._fim()
        if fim and fim[1]:  # venceu: o rival se desfaz em tinta
            visivel = 1 - fim[0]
            vfx.dissolver(r, x, y, fim[0], COR_ESTILO[self.estilo_rival])
        entrada = min(1.0, self.relogio / (self.entrada_ate * 0.45))
        if entrada < 1:  # a entrada: o rival surge de uma mancha de tinta
            r.draw_ui_circle(
                x, y - 66, 140 * (1 - entrada) + 20, alpha((8, 7, 6, 255), 200 * (1 - entrada))
            )
            visivel *= entrada
        if visivel <= 0.01:
            visivel = 0.0
        desenhar_lutador(
            r,
            x + dx,
            y + dy,
            escala,
            alpha(COR_ESTILO[self.estilo_rival], 255 * visivel),
            alpha(TINTA, 230 * visivel),
            guarda=1.0 if rival.bloqueio or rival.revide else 0.0,
            clarao=clarao,
            clarao_cor=SANGUE_VIVO,
            estilo=self.estilo_rival,
            tempo=self.relogio,
            ataque=self._pose_ataque(rival),
            dano=self._pose_dano(rival),
        )
        if rival.pular:  # preso na ilusão
            self._texto(r, x, y - 200, "幻", 26, alpha(SANGUE_VIVO, 200), "center")
        nome = (
            "Chefe do capítulo"
            if rival.chefe
            else f"{NOME_ESTILO[self.estilo_rival]} · Rival {self.j.n_luta}"
        )
        self._texto(r, x, 36, nome, 22, TINTA, "center")
        self._barra(r, x - 120, 72, 240, rival, SANGUE_VIVO)
        self._texto(
            r, x + 130, 64, f"{max(0, rival.vida)} / {rival.vida_max}", 15, alpha(TINTA, 150)
        )
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
        r.draw_ui_rect(x - 14, y - 14, 276, 96, alpha(LACA, 230))
        self._texto(r, x, y - 6, "próxima ação do rival", 14, alpha(TINTA, 120))
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
            origem = self.origens.get(vista.id, "")
            if origem:
                self._texto(r, x, y + 62, f"※ {origem}", 12, alpha(TINTA, 100))

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

    def _jogador(self, r: IRenderer) -> None:
        j = self.j.jogador
        x, y = POS_JOGADOR
        dx, dy = self._deslocamento(j)
        clarao = 0.0
        inicio = self.tremor.get(id(j))
        if inicio is not None and 0 <= self.relogio - inicio < 0.3:
            clarao = 1 - (self.relogio - inicio) / 0.3
        guarda = 1.0 if j.bloqueio or j.revide else 0.0
        for ativo, aura in ((j.forma, "forma_desperta"), (j.instinto, "instinto_puro")):
            if ativo:  # a aura fica enquanto o Despertar dura
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
            clarao_cor=SANGUE_VIVO,
            tempo=self.relogio,
            ataque=self._pose_ataque(j),
            dano=max(self._pose_dano(j), cai),
            costas=True,
        )
        if cai:
            vfx.correntes_fechando(r, x, y - 66 * ESCALA_JOGADOR, cai)
        self._texto(r, 40, 360, "Você", 22, TINTA)
        dom = f"{self.j.dom.kanji} {self.j.dom.nome}" if self.j.dom else ""
        self._texto(r, 106, 365, dom, 15, alpha(TINTA, 130))
        self._barra(r, 40, 394, 250, j, TINTA)
        perc = j.percepcao + j.percepcao_luta
        info = f"{max(0, j.vida)} / {j.vida_max} · Vel {j.velocidade} · Perc {perc}"
        self._texto(r, 40, 406, info, 15, alpha(TINTA, 150))
        estados = []
        if j.bloqueio:
            estados.append(f"守 bloqueio {j.bloqueio}")
        if j.revide:
            estados.append(f"返 revide {j.revide}")
        if j.marca:
            estados.append(f"呪 {j.marca}")
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
            estados.append(f"血 sangra {j.sangue}")
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
        if self.relogio < self.aviso_ate:
            self._texto(r, 624, 606, self.aviso, 16, SANGUE_VIVO, "center")
            return
        for k, linha in enumerate(quebrar(self.registro, 62)[:2]):
            self._texto(r, 624, 598 + k * 18, linha, 14, alpha(TINTA, 150), "center")

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
