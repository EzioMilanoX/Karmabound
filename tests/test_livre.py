"""O Laboratório (livre.py): a build e o rival a dedo, e a luta volta para a montagem."""

from karmabound import livre
from karmabound.tela_livre import LivreScene


class Tecla:
    def __init__(self):
        self.agora = ""

    def is_action_pressed(self, a):
        return a == self.agora


def test_a_build_e_o_rival_escolhidos_entram_na_luta():
    base = livre.jornada_base("dificil")
    tecnica = livre.opcoes(base, "tecnica0", "tecnicas")[5]
    reliquia = livre.opcoes(base, "reliquia0", "reliquias")[1]
    dono = next(v for v in base.ctx.elenco.viloes if v.papel == "final")
    j = livre.montar(
        {"tecnica0": tecnica.id, "reliquia0": reliquia.id, "rival": dono.id, "capitulo": 3},
        "dificil",
        seed=1,
    )
    assert j.fase == "luta"
    assert tecnica.id in {t.id for t in j.jogador.tecnicas}
    assert reliquia in j.estado.reliquias
    assert j.luta.rival.vilao == dono.id and j.luta.rival.chefe


def test_o_rival_pode_ser_qualquer_vilao_ate_o_meme():
    base = livre.jornada_base("dificil")
    papeis = {v.papel for v in livre.opcoes(base, "rival", None) if v is not None}
    assert {"tenente", "chefe", "final", "secreto", "meme"} <= papeis


def test_a_tela_troca_abre_a_lista_e_luta():
    lutou = []
    e = Tecla()
    s = LivreScene("dificil", {}, e, lutou.append, lambda _e: None)
    s.cursor = 0  # Linhagem
    e.agora = "direita"
    s.update(None, 0.1)
    assert s.escolha["linhagem"]
    e.agora = "confirmar"
    s.update(None, 0.1)
    assert s.lista == "linhagem"
    e.agora = "baixo"
    s.update(None, 0.1)
    e.agora = "confirmar"
    s.update(None, 0.1)
    assert s.lista is None
    s.cursor = len(s.linhas) - 1
    s.update(None, 0.1)
    assert lutou and lutou[0]["linhagem"]
