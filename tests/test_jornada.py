import pytest

from karmabound.combate import escolher_jogador_auto
from karmabound.jornada import Jornada
from karmabound.mesa import Giro


def jogar_ate_o_fim(j: Jornada, max_passos: int = 5000) -> list[str]:
    """Joga a Jornada inteira com o piloto, como faria uma pessoa apertando os botões."""
    fases = []
    for _ in range(max_passos):
        fases.append(j.fase)
        if j.fase == "destino":
            j.girar_destino()
        elif j.fase == "arco":
            j.girar_arco()
        elif j.fase == "luta":
            if j.luta.acabou:
                j.terminar_luta()
            elif j.luta.vez is j.jogador:
                j.luta.resolver(escolher_jogador_auto(j.luta))
            else:
                j.luta.turno_rival()
        elif j.fase == "tecnica":
            j.girar_tecnica()
            j.escolher_tecnica(0)
        elif j.fase == "substituir":
            j.substituir(j.tecnica_mais_fraca())
        elif j.fase == "altar":
            j.recusar_altar()
        elif j.fase == "reliquia":
            j.girar_reliquia()
        else:
            return fases
    raise AssertionError("a jornada não terminou")


@pytest.mark.parametrize("seed", range(8))
def test_jornada_termina_em_vitoria_ou_derrota(seed):
    j = Jornada.nova("acessivel", seed=seed)
    fases = jogar_ate_o_fim(j)
    assert j.fase in ("vitoria", "derrota")
    assert fases[0] == "destino" and fases[1] == "arco"
    if j.fase == "vitoria":
        # a Invasão pode acrescentar lutas a um capítulo: a run tem 12 ou mais
        assert j.estado.lutas_vencidas >= j.ctx.lutas
        assert fases.count("arco") == j.ctx.capitulos


def test_acao_fora_de_fase_e_recusada():
    j = Jornada.nova(seed=1)
    with pytest.raises(RuntimeError):
        j.girar_tecnica()
    j.girar_destino()
    with pytest.raises(RuntimeError):
        j.girar_destino()


def test_espacos_cheios_pedem_substituicao():
    j = Jornada.nova(seed=2)
    j.girar_destino()
    j.girar_arco()
    while len(j.jogador.tecnicas) < j.ctx.combate["espacos"]:
        j.jogador.tecnicas.append(j.jogador.tecnicas[0])
    j.fase = "tecnica"
    nova = next(f for f in j.ctx.rodas["tecnicas"].fatias if f.id == "lamina_de_sangue")
    j.giro = Giro(j.ctx.rodas["tecnicas"], [nova])
    j.escolher_tecnica(0)
    assert j.fase == "substituir" and j.pendente is nova
    sai = j.jogador.tecnicas[1]
    j.substituir(sai)
    assert any(t.id == "lamina_de_sangue" for t in j.jogador.tecnicas)
    assert j.fase in ("reliquia", "luta", "arco")


def test_juramento_abre_o_altar_e_jurar_aplica_o_voto():
    j = Jornada.nova("acessivel", seed=3)
    j.amostras_altar = 12
    j.girar_destino()
    j.girar_arco()
    juramento = next(f for f in j.ctx.rodas["tecnicas"].fatias if f.evento == "altar")
    j.fase = "tecnica"
    j.giro = Giro(j.ctx.rodas["tecnicas"], [juramento])
    j.escolher_tecnica(0)
    assert j.fase == "altar"
    pesos = j.pesar_restricoes()
    assert set(pesos) == set(j.ctx.catalogo.restricoes)
    proposta = j.propor_voto(["sem_descanso", "corpo_ofertado"])
    assert proposta is not None and proposta.voto.restricoes
    j.jurar(proposta)
    assert j.estado.votos.ativos and j.fase in ("reliquia", "luta", "arco")


def test_carma_transbordado_desperta_no_proximo_giro():
    j = Jornada.nova(seed=4)
    j.girar_destino()
    j.carma.valor = j.carma.config.maximo
    giro = j.girar_arco()
    assert giro.despertar and giro.fatias[0].raridade == j.ctx.ordem[-1]
    assert j.despertares == 1 and j.carma.valor == 0
