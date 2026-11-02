"""O Grimório salva em disco: nos testes, sempre numa pasta temporária."""

import pytest


@pytest.fixture(autouse=True)
def _grimorio_temporario(tmp_path, monkeypatch):
    monkeypatch.setenv("KARMABOUND_SAVE", str(tmp_path / "save"))
    monkeypatch.setenv("KARMABOUND_DICAS", "0")  # nenhuma dica trava uma run jogada pelas telas
