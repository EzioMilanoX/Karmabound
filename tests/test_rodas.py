import json
import random
from collections import Counter

import pytest

from karmabound.rodas import (
    carregar_balanceamento,
    carregar_raridades,
    carregar_rodas,
    melhor_raridade,
    sortear,
    sortear_opcoes,
)

RARIDADES = carregar_raridades(carregar_balanceamento())
ORDEM = [r.id for r in RARIDADES]
BASE = {r.id: r.peso for r in RARIDADES}


@pytest.fixture
def rodas():
    return carregar_rodas(RARIDADES)


def test_carrega_as_seis_rodas(rodas):
    assert set(rodas) == {"linhagem", "destino", "tecnicas", "arco", "reliquias", "despertar"}
    assert rodas["despertar"].uniforme and not rodas["tecnicas"].uniforme


def test_mesma_seed_mesmo_resultado(rodas):
    def sequencia(seed):
        rng = random.Random(seed)
        return [sortear(rodas["tecnicas"], BASE, rng).id for _ in range(50)]

    assert sequencia(7) == sequencia(7)
    assert sequencia(7) != sequencia(8)


def test_taxas_seguem_os_pesos(rodas):
    rng = random.Random(1)
    n = 20_000
    contagem = Counter(sortear(rodas["destino"], BASE, rng).raridade for _ in range(n))
    total = sum(BASE.values())
    for rid, peso in BASE.items():
        assert contagem[rid] / n == pytest.approx(peso / total, abs=0.01)


def test_forcar_raridade(rodas):
    fatia = sortear(rodas["reliquias"], BASE, random.Random(3), forcar=ORDEM[-1])
    assert fatia.raridade == ORDEM[-1]


def test_escolha_nao_repete_fatias(rodas):
    roda = rodas["tecnicas"]
    for seed in range(200):
        ids = [f.id for f in sortear_opcoes(roda, BASE, random.Random(seed))]
        assert len(ids) == roda.opcoes == len(set(ids))


def test_melhor_raridade(rodas):
    fatias = [rodas["arco"].da_raridade("cinza")[0], rodas["arco"].da_raridade("maldito")[0]]
    assert melhor_raridade(fatias, ORDEM) == "maldito"


def test_roda_sem_alguma_raridade_e_recusada(tmp_path):
    roda = {
        "id": "x",
        "nome": "X",
        "modo": "aceita",
        "fatias": [
            {"id": "a", "nome": "A", "raridade": "cinza"},
        ],
    }
    caminho = tmp_path / "rodas.json"
    caminho.write_text(json.dumps({"rodas": [roda]}), encoding="utf-8")
    with pytest.raises(ValueError, match="sem fatia"):
        carregar_rodas(RARIDADES, caminho)
