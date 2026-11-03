"""O calibrador: a matemática dele e a gravação sem estragar o arquivo."""

import importlib.util
import json
from pathlib import Path

import pytest

RAIZ = Path(__file__).resolve().parent.parent


def _calibrar():
    spec = importlib.util.spec_from_file_location("calibrar", RAIZ / "tools" / "calibrar.py")
    modulo = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(modulo)
    return modulo


def test_a_reta_acha_o_valor_do_alvo():
    c = _calibrar()
    pontos = [(5.0, 40.0), (5.5, 32.0), (6.0, 24.0)]  # cai 16 pontos por unidade
    assert c.reta_ate(pontos, 25.0) == pytest.approx(5.9375)


def test_veredito_com_folga_de_ruido():
    c = _calibrar()
    assert c.veredito(4.5, (1, 3)) == "acima"
    assert c.veredito(3.8, (1, 3)) == "ok"  # dentro da folga
    assert c.veredito(-0.5, (1, 3)) == "abaixo"
    assert c.veredito(25, (10, 20)) == "acima"


def test_gravar_modos_so_troca_os_numeros(tmp_path, monkeypatch):
    c = _calibrar()
    copia = tmp_path / "balanceamento.json"
    copia.write_text(c.BALANCEAMENTO.read_text(encoding="utf-8"), encoding="utf-8")
    monkeypatch.setattr(c, "BALANCEAMENTO", copia)
    antes = json.loads(copia.read_text(encoding="utf-8"))
    c._gravar_modos({"dificil": 5.12, "brutal": 6.4})
    depois = json.loads(copia.read_text(encoding="utf-8"))
    dif = depois["combate"]["dificuldades"]
    assert dif["dificil"]["rivais"]["vida_por_luta"] == 5.12
    assert dif["brutal"]["rivais"]["vida_por_luta"] == 6.4
    assert dif["acessivel"] == antes["combate"]["dificuldades"]["acessivel"]
    assert depois["combate"]["rivais"] == antes["combate"]["rivais"]  # a base não mudou


def test_a_regua_cobre_todas_as_raridades():
    from karmabound.rodas import carregar_balanceamento

    bal = carregar_balanceamento()
    assert {r["id"] for r in bal["raridades"]} <= set(bal["regua"])
