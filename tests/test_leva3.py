"""Leva 3: o que os poderes fazem nos animes — chama eterna, veneno, gelo, clones,
invocações, o ritual de Hidan, purificar, o preço do Mangekyō e as transformações."""

import random

from karmabound.combate import Luta, Lutador, Modo, Tecnica, evoluir, valor_tecnica
from karmabound.efeitos import NEUTRO, Efeitos

BASICO = Tecnica("golpe_basico", "Golpe", "ataque", dano=4)
GUARDA = Tecnica("guarda", "Guarda", "defesa", bloqueio=0)


def lut(nome="J", tecnicas=(), vida=100, perc=0, efeitos=NEUTRO):
    return Lutador(nome, vida, 1, perc, list(tecnicas), efeitos=efeitos)


def luta(j, r, seed=0):
    lt = Luta(j, r, BASICO, random.Random(seed))
    lt.abertura = False
    lt.vez = j
    return lt


def rodada(lt, t=BASICO, do_rival=GUARDA):
    """Um turno de cada: o seu e o do rival."""
    lt.resolver(t)
    if not lt.acabou:
        lt.resolver(do_rival)


def test_chama_eterna_nao_apaga_e_cresce_ate_incinerar():
    amaterasu = Tecnica("amaterasu", "Amaterasu", "maldita", chama_eterna=2, recarga=99)
    j, r = lut(tecnicas=[amaterasu, GUARDA]), lut("R", tecnicas=[GUARDA], vida=60)
    lt = luta(j, r)
    lt.resolver(amaterasu)
    assert r.chama == 2
    perdas = []
    for _ in range(5):
        antes = r.vida
        lt.resolver(GUARDA)  # turno do rival: a chama queima no começo dele
        perdas.append(antes - r.vida)
        lt.resolver(GUARDA)
    assert perdas == [2, 3, 4, 5, 6]  # não para em 3 turnos, como o sangramento: cresce


def test_chama_atravessa_tudo_e_purificar_nao_apaga():
    amaterasu = Tecnica("amaterasu", "Amaterasu", "maldita", chama_eterna=3)
    limpar = Tecnica("limpar", "Limpar", "defesa", purificar=True)
    j, r = lut(tecnicas=[amaterasu]), lut("R", tecnicas=[limpar])
    r.espelho = r.escudos = 5
    lt = luta(j, r)
    lt.resolver(amaterasu)
    assert r.chama == 3  # basta o olhar: espelho e escudo não param
    lt.resolver(limpar)
    assert r.chama > 0  # só quem acendeu apaga


def test_veneno_acumula_e_cai_um_por_turno():
    picada = Tecnica("picada", "Picada", "ataque", dano=1, veneno=3)
    j, r = lut(tecnicas=[picada]), lut("R", tecnicas=[GUARDA])
    lt = luta(j, r)
    lt.resolver(picada)
    lt.resolver(GUARDA)  # o rival sofre 3, sobra 2
    assert r.veneno == 2
    lt.resolver(picada)
    assert r.veneno == 5  # as doses se somam
    vida = r.vida
    lt.resolver(GUARDA)
    assert vida - r.vida == 5 and r.veneno == 4


def test_veneno_de_golpe_precisa_ferir():
    picada = Tecnica("picada", "Picada", "ataque", dano=1, veneno=3)
    j, r = lut(tecnicas=[picada]), lut("R")
    r.escudos = 1
    luta(j, r).resolver(picada)
    assert r.veneno == 0  # o golpe não entrou na carne


def test_purificar_tira_sangue_veneno_marca_e_selos():
    limpar = Tecnica("limpar", "Limpar", "defesa", purificar=True)
    j, r = lut(tecnicas=[limpar]), lut("R")
    j.sangue, j.sangue_turnos, j.veneno, j.marca, j.silencio = 3, 2, 4, 2, 0
    j.bonus_dano = -3
    luta(j, r).resolver(limpar)
    assert (j.sangue, j.sangue_turnos, j.veneno, j.marca, j.bonus_dano) == (0, 0, 0, 0, 0)


def test_congelar_tira_o_turno_e_o_proximo_golpe_estilhaca():
    gelo = Tecnica("gelo", "Gelo", "maldita", congelar=1, recarga=3)
    j, r = lut(tecnicas=[gelo]), lut("R", tecnicas=[GUARDA])
    lt = luta(j, r)
    lt.resolver(gelo)
    assert r.congelado and r.pular == 1
    lt.resolver(lt.prontas(r)[0])  # o turno perdido
    acao = lt.resolver(BASICO)
    assert acao.dano == 8 and not r.congelado  # ×2, e o gelo se quebra


class SempreAcerta:
    """rng que sempre sorteia o menor número: todo sorteio "com chance" acontece."""

    def random(self):
        return 0.0


def test_clones_atacam_junto_e_absorvem_golpes():
    kage = Tecnica("kage", "Clones", "maldita", clones=2, recarga=3)
    soco = Tecnica("soco", "Soco", "ataque", dano=10)
    j, r = lut(tecnicas=[kage, soco]), lut("R", tecnicas=[soco])
    lt = luta(j, r)
    lt.rng = SempreAcerta()
    lt.resolver(kage)
    assert j.clones == 2
    vida = j.vida
    lt.resolver(soco)  # o rival acerta um clone
    assert j.vida == vida and j.clones == 1
    acao = lt.resolver(soco)
    assert acao.dano == 10 + 4  # o clone que sobrou bate junto, a 40%


def test_com_n_clones_o_golpe_acha_um_clone_em_n_de_n_mais_1():
    soco = Tecnica("soco", "Soco", "ataque", dano=10)
    acertos = 0
    for seed in range(400):
        j, r = lut(tecnicas=[GUARDA]), lut("R", tecnicas=[soco])
        j.clones = 1
        lt = luta(j, r, seed)
        lt.vez = r
        lt.resolver(soco)
        acertos += j.clones == 0
    assert 160 < acertos < 240  # 1 clone: metade das vezes


def test_invocacao_ataca_ao_chegar_e_depois_a_cada_turno():
    sapo = Tecnica("sapo", "Sapo", "maldita", invocar=5, invocar_turnos=2, recarga=99)
    j, r = lut(tecnicas=[sapo, GUARDA]), lut("R", tecnicas=[GUARDA])
    lt = luta(j, r)
    acao = lt.resolver(sapo)
    assert acao.dano == 5 and r.vida == 95  # chegou atacando
    lt.resolver(GUARDA)
    lt.resolver(GUARDA)  # no começo do seu turno, o segundo ataque
    assert r.vida == 90 and j.invocacoes == []  # e ele vai embora


def test_ritual_divide_a_dor_e_o_proprio_preco():
    ritual = Tecnica("ritual", "Ritual", "maldita", vinculo=3, custo_vida=8)
    j, r = lut(tecnicas=[ritual]), lut("R", tecnicas=[GUARDA])
    lt = luta(j, r)
    lt.resolver(ritual)
    assert j.vida == 92 and r.vida == 92  # a estocada em si mesmo fere os dois
    assert j.elo is r


def test_mangekyo_cobra_percepcao_para_sempre():
    tsukuyomi = Tecnica("tsukuyomi", "Tsukuyomi", "maldita", atordoar=1, custo_percepcao=1)
    j, r = lut(tecnicas=[tsukuyomi], perc=3), lut("R")
    luta(j, r).resolver(tsukuyomi)
    assert j.percepcao == 2 and j.base_percepcao == 2
    j.nova_luta()
    assert j.percepcao == 2  # não volta na próxima luta


def test_modo_fortalece_por_turnos_e_cobra_ao_acabar():
    sabio = Tecnica(
        "sabio",
        "Modo Sábio",
        "modo",
        recarga=99,
        modo=Modo(turnos=2, dano=3, percepcao=2, exausto=1),
    )
    j, r = lut(tecnicas=[sabio]), lut("R", tecnicas=[GUARDA])
    lt = luta(j, r)
    lt.resolver(sabio)
    assert j.modo is not None and j.modo_turnos == 2
    assert lt.percepcao_contra(j) == 2
    lt.resolver(GUARDA)
    assert lt.resolver(BASICO).dano == 7  # +3 no golpe
    lt.resolver(GUARDA)
    lt.resolver(BASICO)
    assert j.modo is None and j.pular == 1  # acabou: exausto


def test_modo_dos_dados_vira_modo():
    t = Tecnica.de_dict({"id": "g", "nome": "G", "tipo": "modo", "modo": {"turnos": 3}})
    assert isinstance(t.modo, Modo) and t.modo.turnos == 3
    assert evoluir(t).modo.turnos == 4
    assert valor_tecnica(t) > 0


def test_armadura_segura_a_morte_e_cobra_depois():
    armadura = Tecnica(
        "armadura", "Armadura", "modo", modo=Modo(turnos=1, inabalavel=True, adiado=True)
    )
    martelo = Tecnica("martelo", "Martelo", "ataque", dano=200)
    j, r = lut(tecnicas=[armadura]), lut("R", tecnicas=[martelo])
    lt = luta(j, r)
    lt.resolver(armadura)
    lt.resolver(martelo)
    assert j.vida == 1 and j.adiado > 0  # não cai enquanto a armadura veste
    lt.resolver(BASICO)  # o turno do modo acaba: o corpo cobra
    assert not j.vivo


def test_trocar_de_forma_cobra_a_anterior():
    g2 = Tecnica("g2", "G2", "modo", modo=Modo(turnos=3, exausto=0, perde_vida_frac=0.5))
    g4 = Tecnica("g4", "G4", "modo", modo=Modo(turnos=2))
    j, r = lut(tecnicas=[g2, g4]), lut("R", tecnicas=[GUARDA])
    lt = luta(j, r)
    lt.resolver(g2)
    lt.resolver(GUARDA)
    lt.resolver(g4)
    assert j.modo_id == "g4" and j.vida == 50


def test_efeitos_passivos_da_leva():
    inicio = lut(efeitos=Efeitos(clones_inicio=1, invocar_inicio=3))
    inicio.nova_luta()
    assert inicio.clones == 1 and inicio.invocacoes == [[3, 3, "invocacao_inicio"]]
    e = Efeitos(veneno_ao_ferir=2, dot_mult=2.0)
    j, r = lut(efeitos=e), lut("R", tecnicas=[GUARDA], efeitos=Efeitos(veneno_espinhos=2))
    lt = luta(j, r)
    lt.resolver(BASICO)
    assert r.veneno == 2 and j.veneno == 2  # injetou, e o corpo dele envenenou você
    vida = r.vida
    lt.resolver(GUARDA)
    assert vida - r.vida == 4  # o veneno de quem tem dot_mult ×2


# --- cada ferida que dura tem o seu jeito, além do dano -------------------------------


def test_sangramento_abre_a_ferida_e_a_cura_cai_a_metade():
    cura = Tecnica("cura", "Cura", "defesa", cura=10)
    j, r = lut(tecnicas=[cura], vida=100), lut("R")
    j.vida = 50
    j.sangue, j.sangue_turnos = 1, 3
    luta(j, r).resolver(cura)
    assert j.vida == 50 - 1 + 5  # sangrou 1 e a cura de 10 só fechou 5


def test_veneno_amolece_o_golpe_de_quem_esta_envenenado():
    soco = Tecnica("soco", "Soco", "ataque", dano=20)
    j, r = lut(tecnicas=[soco]), lut("R", tecnicas=[GUARDA])
    j.veneno = 5  # no começo do turno ele fere e cai a 4
    assert luta(j, r).resolver(soco).dano == 16  # 4 doses: -20%
    j2, r2 = lut(tecnicas=[soco]), lut("R", tecnicas=[GUARDA])
    j2.veneno = 30
    assert luta(j2, r2).resolver(soco).dano == 10  # o teto: -50%


def test_chama_negra_incinera_o_que_sobra():
    j, r = lut(tecnicas=[GUARDA]), lut("R", tecnicas=[GUARDA], vida=100)
    r.chama, r.vida = 5, 16
    lt = luta(j, r)
    lt.vez = r
    acao = lt.resolver(GUARDA)  # queima 5, fica 11; a chama sobe a 6 e 11 <= 12: cinzas
    assert not r.vivo and r.incinerado and acao.incinerou
    assert lt.acabou


def test_chama_negra_nao_incinera_quem_ainda_tem_vida():
    j, r = lut(tecnicas=[GUARDA]), lut("R", tecnicas=[GUARDA], vida=100)
    r.chama, r.vida = 5, 40
    lt = luta(j, r)
    lt.vez = r
    lt.resolver(GUARDA)
    assert r.vida == 35 and not r.incinerado


def test_marca_sela_e_a_tecnica_demora_mais_a_voltar():
    lamina = Tecnica("lamina", "Lâmina", "ataque", dano=5, recarga=2)
    j, r = lut(tecnicas=[lamina]), lut("R", tecnicas=[GUARDA])
    lt = luta(j, r)
    j.marca = 1
    lt.resolver(lamina)
    assert j.recargas["lamina"] == 3  # 2 + 1 da maldição
    j.marca = 0
    j.recargas.clear()
    lt.vez = j
    lt.resolver(lamina)
    assert j.recargas["lamina"] == 2
