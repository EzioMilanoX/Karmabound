from karmabound.rolagem import Rolagem


class Quadro:
    """Renderer falso: guarda os retângulos desenhados."""

    def __init__(self):
        self.retangulos = []

    def draw_ui_rect(self, x, y, w, h, cor):
        self.retangulos.append((x, y, w, h))


def test_a_janela_segue_o_cursor_nas_duas_direcoes():
    rol = Rolagem(8)
    rol.seguir(7, 16)
    assert rol.topo == 0
    rol.seguir(8, 16)
    assert rol.topo == 1 and list(rol.faixa(16)) == list(range(1, 9))
    rol.seguir(15, 16)
    assert rol.topo == 8
    rol.seguir(0, 16)  # deu a volta: o topo volta junto
    assert rol.topo == 0


def test_cursor_fora_da_lista_nao_mexe_na_janela():
    rol = Rolagem(8, topo=8)
    rol.seguir(None, 16)  # o cursor está nas ações embaixo da lista
    assert rol.topo == 8
    rol.seguir(None, 5)  # a lista encolheu: o topo não passa do fim
    assert rol.topo == 0


def test_a_barra_so_aparece_quando_a_lista_nao_cabe():
    q = Quadro()
    Rolagem(8).desenhar(q, 938, 112, 44, 8)
    assert q.retangulos == []
    rol = Rolagem(8)
    rol.seguir(15, 16)
    rol.desenhar(q, 938, 112, 44, 16)
    trilho, alca = q.retangulos
    assert alca[3] < trilho[3]
    assert alca[1] + alca[3] == trilho[1] + trilho[3]  # no fim da lista, a alça encosta embaixo
