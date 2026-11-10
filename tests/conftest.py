"""O Grimório salva em disco: nos testes, sempre numa pasta temporária."""

import pytest


@pytest.fixture(autouse=True)
def _grimorio_temporario(tmp_path, monkeypatch):
    monkeypatch.setenv("KARMABOUND_SAVE", str(tmp_path / "save"))
    monkeypatch.setenv("KARMABOUND_MEMES", str(tmp_path / "memes"))  # nunca as imagens reais
    monkeypatch.setenv("KARMABOUND_DICAS", "0")  # nenhuma dica trava uma run jogada pelas telas
    # o golpe sai na hora, sem a barra do Kokusen nem o sorteio dele (os números ficam certos)
    from karmabound import tela_luta
    from karmabound.opcoes import OPCOES

    monkeypatch.setattr(OPCOES, "kokusen", False)
    monkeypatch.setattr(tela_luta, "KOKUSEN_SORTE", 0.0)
