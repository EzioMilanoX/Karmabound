"""Telas por cima de outra: pausa, opções, dica e quebrar um voto.

Todas guardam a tela de baixo e a desenham primeiro (a engine só desenha o topo
da pilha), escurecida, com o painel por cima. Fecham com `ao_fechar` (o Fluxo
desempilha).
"""

from __future__ import annotations

from ouroboros.interfaces.renderer import IRenderer

from karmabound import som
from karmabound.dicas import DICAS
from karmabound.jornada import Jornada
from karmabound.opcoes import OPCOES, VELOCIDADES
from karmabound.tela_menus import DURANTE, _Base, _cortar
from karmabound.visual import (
    ALTURA,
    FERRO,
    FUNDO,
    LACA,
    LARGURA,
    OURO,
    SANGUE_VIVO,
    TINTA,
    alpha,
    moldura,
    quebrar,
)


class _Sobre(_Base):
    """Uma tela que fica por cima de `baixo`: desenha ela, escurece, e desenha o painel."""

    def __init__(self, baixo, entrada, ao_fechar, ao_sair) -> None:
        super().__init__(entrada, ao_sair)
        self.baixo = baixo
        self.ao_fechar = ao_fechar
        self.cursor = 0

    def _fundo_escuro(self, r: IRenderer, opacidade: float = 190) -> None:
        baixo = self.baixo
        while isinstance(baixo, _Sobre):  # o jogo de fundo, sem os painéis do meio
            baixo = baixo.baixo
        baixo.render(None, r)
        r.draw_ui_rect(0, 0, LARGURA, ALTURA, alpha(FUNDO, opacidade))

    def _mover(self, n: int) -> None:
        e = self.entrada
        if e.is_action_pressed("cima"):
            self.cursor = (self.cursor - 1) % n
            som.tocar("mover")
        elif e.is_action_pressed("baixo"):
            self.cursor = (self.cursor + 1) % n
            som.tocar("mover")

    def _lista(self, r, x, y, itens: list[str], largura=360, passo=40) -> None:
        for i, texto in enumerate(itens):
            yi = y + i * passo
            if i == self.cursor:
                r.draw_ui_rect(x - 16, yi - 6, largura, passo - 6, alpha(OURO, 30))
                r.draw_ui_polygon([(x - 6, yi + 4), (x + 2, yi + 10), (x - 6, yi + 16)], OURO)
            self._t(r, x + 12, yi - 2, texto, 20, TINTA if i == self.cursor else alpha(TINTA, 150))


# ----------------------------------------------------------------------- pausa


class PausaScene(_Sobre):
    """Esc numa run: continuar, opções, votos, voltar ao título ou sair."""

    def __init__(self, baixo, jornada: Jornada | None, entrada, ao_fechar, ao_sair, fluxo) -> None:
        super().__init__(baixo, entrada, ao_fechar, ao_sair)
        self.j = jornada
        self.fluxo = fluxo
        self.confirmar_titulo = False

    @property
    def itens(self) -> list[tuple[str, str]]:
        itens = [("continuar", "Continuar"), ("opcoes", "Opções")]
        if self.j is not None and self.j.estado.votos.ativos:
            itens.append(("votos", "Votos (quebrar um voto)"))
        itens += [("titulo", "Voltar ao título"), ("sair", "Sair do jogo")]
        return itens

    def update(self, world, delta_time: float) -> None:
        self.relogio += delta_time
        e = self.entrada
        if e.is_action_pressed("sair") or e.is_action_pressed("cancelar"):
            if self.confirmar_titulo:
                self.confirmar_titulo = False
            else:
                self.ao_fechar()
            return
        itens = self.itens
        self._mover(len(itens))
        if self.cursor >= len(itens):
            self.cursor = 0
        if not e.is_action_pressed("confirmar"):
            return
        som.tocar("confirmar")
        acao = itens[self.cursor][0]
        if acao == "continuar":
            self.ao_fechar()
        elif acao == "opcoes":
            self.fluxo.abrir_opcoes(self)
        elif acao == "votos":
            self.fluxo.abrir_votos(self)
        elif acao == "titulo":
            if self.confirmar_titulo:
                self.fluxo.titulo()
            else:
                self.confirmar_titulo = True
        elif acao == "sair":
            self.ao_sair()

    def render(self, world, r: IRenderer) -> None:
        self._fundo_escuro(r)
        r.draw_ui_rect(300, 150, 360, 320, alpha(LACA, 250))
        moldura(r, 300, 150, 660, 470, OURO)
        self._t(r, 480, 172, "止  Pausa", 32, OURO, "center")
        self._lista(r, 340, 236, [texto for _, texto in self.itens], largura=300)
        if self.confirmar_titulo:
            self._t(
                r,
                480,
                432,
                "A run será perdida. Enter de novo confirma.",
                15,
                SANGUE_VIVO,
                "center",
            )
        self._t(
            r,
            480,
            ALTURA - 26,
            "↑ ↓ move · Enter escolhe · Esc volta",
            14,
            alpha(TINTA, 110),
            "center",
        )


# ----------------------------------------------------------------------- opções


class OpcoesScene(_Sobre):
    """Volume, silenciar, tela cheia, velocidade das animações e dicas. Tudo vale na hora."""

    LINHAS = ("musica", "efeitos", "mudo", "tela_cheia", "velocidade", "dicas", "rever", "voltar")

    def __init__(self, baixo, entrada, ao_fechar, ao_sair, renderer=None) -> None:
        super().__init__(baixo, entrada, ao_fechar, ao_sair)
        self.renderer = renderer
        self.aviso = ""

    def _rotulo(self, linha: str) -> tuple[str, str]:
        o = OPCOES
        barra = lambda v: "■" * v + "□" * (10 - v)  # noqa: E731
        return {
            "musica": ("Música", barra(o.volume_musica)),
            "efeitos": ("Efeitos", barra(o.volume_efeitos)),
            "mudo": ("Silenciar tudo", "sim" if o.mudo else "não"),
            "tela_cheia": ("Tela cheia", "sim" if o.tela_cheia else "não"),
            "velocidade": ("Velocidade das animações", f"{o.velocidade:g}×".replace(".", ",")),
            "dicas": ("Dicas da primeira run", "ligadas" if o.dicas else "desligadas"),
            "rever": ("Rever todas as dicas", ""),
            "voltar": ("Voltar", ""),
        }[linha]

    def _mudar(self, linha: str, passo: int) -> None:
        o = OPCOES
        if linha == "musica":
            o.volume_musica = max(0, min(10, o.volume_musica + passo))
        elif linha == "efeitos":
            o.volume_efeitos = max(0, min(10, o.volume_efeitos + passo))
        elif linha == "mudo":
            o.mudo = not o.mudo
        elif linha == "tela_cheia":
            o.tela_cheia = not o.tela_cheia
            if self.renderer is not None:
                try:
                    self.renderer.set_fullscreen(o.tela_cheia)
                except Exception:
                    o.tela_cheia = False
        elif linha == "velocidade":
            i = VELOCIDADES.index(o.velocidade) if o.velocidade in VELOCIDADES else 0
            o.velocidade = VELOCIDADES[(i + (1 if passo >= 0 else -1)) % len(VELOCIDADES)]
        elif linha == "dicas":
            o.dicas = not o.dicas
        elif linha == "rever":
            o.dicas_vistas.clear()
            o.dicas = True
            self.aviso = "as dicas voltam a aparecer"
        som.SOM.aplicar_volume()
        o.salvar()
        som.tocar("mover")

    def update(self, world, delta_time: float) -> None:
        self.relogio += delta_time
        e = self.entrada
        if e.is_action_pressed("sair") or e.is_action_pressed("cancelar"):
            self.ao_fechar()
            return
        self._mover(len(self.LINHAS))
        linha = self.LINHAS[self.cursor]
        if e.is_action_pressed("esquerda"):
            self._mudar(linha, -1)
        elif e.is_action_pressed("direita"):
            self._mudar(linha, +1)
        elif e.is_action_pressed("confirmar"):
            if linha == "voltar":
                self.ao_fechar()
            elif linha in ("musica", "efeitos"):
                self._mudar(linha, +1)
            else:
                self._mudar(linha, 0)

    def render(self, world, r: IRenderer) -> None:
        self._fundo_escuro(r, 215)
        r.draw_ui_rect(180, 90, 600, 470, alpha(LACA, 250))
        moldura(r, 180, 90, 780, 560, OURO)
        self._t(r, 480, 110, "設  Opções", 30, OURO, "center")
        for i, linha in enumerate(self.LINHAS):
            y = 172 + i * 44
            nome, valor = self._rotulo(linha)
            if i == self.cursor:
                r.draw_ui_rect(204, y - 6, 552, 38, alpha(OURO, 30))
            cor = TINTA if i == self.cursor else alpha(TINTA, 150)
            self._t(r, 230, y, nome, 19, cor)
            self._t(
                r, 736, y + 2, valor, 17, OURO if i == self.cursor else alpha(OURO, 150), "topright"
            )
        if self.aviso:
            self._t(r, 480, 532, self.aviso, 14, alpha(OURO, 180), "center")
        self._t(
            r, 480, ALTURA - 26, "↑ ↓ move · ← → muda · Esc volta", 14, alpha(TINTA, 110), "center"
        )


# ----------------------------------------------------------------------- dica


class DicaScene(_Sobre):
    """Uma dica da primeira run, por cima da tela. Enter (ou Espaço) fecha."""

    def __init__(self, baixo, dica_id: str, entrada, ao_fechar, ao_sair) -> None:
        super().__init__(baixo, entrada, ao_fechar, ao_sair)
        self.kanji, self.titulo, self.texto = DICAS[dica_id]

    def update(self, world, delta_time: float) -> None:
        self.relogio += delta_time
        e = self.entrada
        if self.relogio > 0.25 and (
            e.is_action_pressed("confirmar")
            or e.is_action_pressed("cancelar")
            or e.is_action_pressed("girar")
        ):
            som.tocar("confirmar")
            self.ao_fechar()

    def render(self, world, r: IRenderer) -> None:
        self._fundo_escuro(r, 150)
        linhas = quebrar(self.texto, 58)
        altura = 130 + len(linhas) * 26
        y0 = (ALTURA - altura) / 2
        r.draw_ui_rect(170, y0, 620, altura, alpha(LACA, 245))
        moldura(r, 170, y0, 790, y0 + altura, OURO)
        self._t(r, 210, y0 + 22, self.kanji, 40, OURO)
        self._t(r, 266, y0 + 32, self.titulo, 24, TINTA)
        for k, linha in enumerate(linhas):
            self._t(r, 210, y0 + 86 + k * 26, linha, 17, alpha(TINTA, 220))
        self._t(r, 750, y0 + altura - 30, "Enter continua", 14, alpha(TINTA, 120), "topright")


# ----------------------------------------------------------------------- quebrar um voto


class VotosScene(_Sobre):
    """Os votos ativos; escolher um leva à quebra: punição e o voto de quebra."""

    def __init__(self, baixo, jornada: Jornada, entrada, ao_fechar, ao_sair, ao_acabou) -> None:
        super().__init__(baixo, entrada, ao_fechar, ao_sair)
        self.j = jornada
        self.ao_acabou = ao_acabou  # quebrar um voto de quebra encerra a run
        self.voto = None  # o voto escolhido para quebrar
        self.marcadas: set[str] = set()
        self.restricoes = list(jornada.ctx.catalogo.restricoes.values())
        self.aviso = ""

    def update(self, world, delta_time: float) -> None:
        self.relogio += delta_time
        e = self.entrada
        if e.is_action_pressed("sair") or e.is_action_pressed("cancelar"):
            if self.voto is not None:
                self.voto, self.marcadas, self.cursor, self.aviso = None, set(), 0, ""
            else:
                self.ao_fechar()
            return
        if self.voto is None:
            votos = self.j.estado.votos.ativos
            self._mover(len(votos) + 1)
            if e.is_action_pressed("confirmar"):
                if self.cursor >= len(votos):
                    self.ao_fechar()
                else:
                    self.voto, self.cursor = votos[self.cursor], 0
            return
        linhas = len(self.restricoes) + 1
        self._mover(linhas)
        if not e.is_action_pressed("confirmar"):
            return
        if self.cursor < len(self.restricoes):
            rid = self.restricoes[self.cursor].id
            if rid in self.marcadas:
                self.marcadas.discard(rid)
            elif len(self.marcadas) < 3:
                self.marcadas.add(rid)
            som.tocar("mover")
            return
        if not self.voto.de_quebra and not self.marcadas:  # o voto de quebra precisa de restrição
            self.aviso = "o voto de quebra precisa de ao menos uma restrição"
            return
        som.tocar("corrente")
        vivo = self.j.quebrar_voto(self.voto, sorted(self.marcadas) or [self.restricoes[0].id])
        if vivo:
            self.ao_fechar()
        else:
            self.ao_acabou()

    def render(self, world, r: IRenderer) -> None:
        self._fundo_escuro(r, 225)
        self._t(r, 40, 24, "誓  Quebrar um voto", 30, SANGUE_VIVO)
        if self.voto is None:
            self._t(r, 40, 76, "Escolha o voto que você quer quebrar.", 16, alpha(TINTA, 150))
            itens = []
            for v in self.j.estado.votos.ativos:
                rest = " · ".join(f"{x.kanji} {x.nome}" for x in v.restricoes)
                ganhos = ", ".join(sorted({g.nome for g in v.ganhos})) or "nenhum ganho"
                marca = "  (voto de quebra)" if v.de_quebra else ""
                itens.append(f"{rest} → {ganhos}{marca}")
            self._lista(r, 60, 120, [*itens, "Voltar"], largura=860)
            return
        v = self.voto
        rest = " · ".join(f"{x.kanji} {x.nome}" for x in v.restricoes)
        self._t(r, 40, 76, f"Quebrar: {rest} ({DURANTE[v.duracao].lower()})", 17, TINTA)
        if v.de_quebra:
            texto = "Este é um voto de quebra. Quebrá-lo encerra a run. Enter em Quebrar confirma."
        else:
            texto = (
                "Quebrar custa os ganhos dele, metade da sua vida e todo o Carma. No lugar dele "
                "você jura um voto de quebra, só de restrições (escolha até 3), pelo prazo que "
                "faltava. Quebrar um voto de quebra encerra a run."
            )
        for k, linha in enumerate(quebrar(texto, 92)):
            self._t(r, 40, 104 + k * 20, linha, 15, SANGUE_VIVO)
        y0 = 178
        for i, res in enumerate(self.restricoes):
            y = y0 + i * 38
            if i == self.cursor:
                r.draw_ui_rect(30, y - 5, 900, 34, LACA)
            marcada = res.id in self.marcadas
            r.draw_ui_rect(44, y + 4, 16, 16, OURO if marcada else alpha(FERRO, 160))
            self._t(r, 72, y - 1, res.kanji, 22, SANGUE_VIVO if marcada else TINTA)
            self._t(r, 108, y + 1, res.nome, 17, TINTA)
            self._t(r, 290, y + 3, _cortar(res.texto, 66), 14, alpha(TINTA, 140))
        y = y0 + len(self.restricoes) * 38 + 8
        if self.cursor == len(self.restricoes):
            r.draw_ui_rect(30, y - 5, 420, 32, LACA)
        self._t(r, 52, y - 1, "Quebrar o voto", 19, SANGUE_VIVO)
        if self.aviso:
            self._t(r, 920, y, self.aviso, 15, SANGUE_VIVO, "topright")
        self._t(
            r,
            480,
            ALTURA - 26,
            "↑ ↓ move · Enter marca/quebra · Esc volta",
            14,
            alpha(TINTA, 110),
            "center",
        )
