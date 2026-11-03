"""A Crônica: o histórico das runs e os Feitos."""

from karmabound.cronica import FEITOS, Cronica
from karmabound.jornada import Jornada


def _fim(venceu=True, modo="dificil", seed=2):
    j = Jornada.nova(modo, seed=seed)
    j.girar_destino()
    j.fase = "vitoria" if venceu else "derrota"
    j.estado.lutas_vencidas = 12 if venceu else 4
    return j


def test_registra_a_run_e_os_feitos_uma_vez(tmp_path):
    c = Cronica(tmp_path / "cronica.json")
    novos = c.registrar(_fim())
    ids = {f.id for f in novos}
    assert "primeira_vitoria" in ids and "sem_reliquias" in ids
    segunda = c.registrar(_fim())
    assert all(f.id not in ids for f in segunda)  # um feito só vem uma vez
    de_novo = Cronica(tmp_path / "cronica.json")
    assert len(de_novo.runs) == 2 and "primeira_vitoria" in de_novo.feitos


def test_derrota_nao_da_feito_de_vitoria(tmp_path):
    c = Cronica(tmp_path / "c.json")
    assert "primeira_vitoria" not in {f.id for f in c.registrar(_fim(venceu=False))}


def test_brutal_e_grimorio_completo(tmp_path):
    c = Cronica(tmp_path / "c.json")
    ids = {f.id for f in c.registrar(_fim(modo="brutal"), vistos=70, total=70)}
    assert {"brutal", "grimorio"} <= ids


def test_arquivo_estragado_recomeca(tmp_path):
    caminho = tmp_path / "c.json"
    caminho.write_text("{ lixo", encoding="utf-8")
    assert Cronica(caminho).runs == []


def test_doze_feitos_com_nome_e_kanji():
    assert len(FEITOS) == 12 and len({f.id for f in FEITOS}) == 12
    assert all(f.kanji and f.nome and f.texto for f in FEITOS)
