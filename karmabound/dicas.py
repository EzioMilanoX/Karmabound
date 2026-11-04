"""As dicas da primeira run: cada sistema se explica uma vez, na primeira vez que aparece."""

from __future__ import annotations

DICAS: dict[str, tuple[str, str, str]] = {  # id -> (kanji, título, texto)
    "roleta": (
        "命",
        "A roleta",
        "Você não escolhe o seu poder: gira por ele. Cada giro que não sai Divino enche o "
        "Carma (業), a corrente no alto da tela. A primeira roda é a da Linhagem, o sangue "
        "de onde você vem; a segunda, a do seu Dom. Espaço gira.",
    ),
    "arco": (
        "章",
        "O Arco",
        "Cada capítulo tem uma regra, que vale para você e para os rivais, e uma arena "
        "própria. O último rival do capítulo é o chefe.",
    ),
    "luta": (
        "闘",
        "A luta",
        "Os turnos se alternam. Toda técnica entra em recarga depois de usada; o Golpe (1) "
        "nunca. O rival anuncia a próxima ação no painel à direita. Escolha com 1–6, ou com "
        "← → e Enter. Esc pausa.",
    ),
    "percepcao": (
        "察",
        "Percepção",
        "É sentir o perigo. Com Percepção 1 você vê só o tipo do que vem; com 2, a técnica. "
        "Contra um golpe perigoso, se a sua Percepção alcança a sutileza dele, você reage: "
        "leva metade e devolve um Golpe.",
    ),
    "despertar": (
        "覚",
        "Despertar",
        "O Carma encheu. Aperte E para despertar quando quiser: não gasta o turno. Se um "
        "golpe fosse te matar, você desperta sozinho e ele não vem. Depois da luta, o "
        "próximo giro sai Divino.",
    ),
    "tecnicas": (
        "技",
        "Técnicas",
        "Depois de cada vitória, três técnicas: escolha uma (1–3). Uma técnica repetida vira "
        "fragmento, e dois fragmentos a fazem evoluir. A origem de cada uma aparece na carta.",
    ),
    "espacos": (
        "空",
        "Espaços cheios",
        "Quatro técnicas é o limite. Escolha qual delas sai (1–4), ou descarte a nova (Backspace).",
    ),
    "reliquia": (
        "宝",
        "Relíquias",
        "Itens que ficam a run inteira. Relíquias repetidas se somam.",
    ),
    "altar": (
        "誓",
        "O Altar dos Votos",
        "Escolha restrições: o Altar mede quanto cada uma tira de você e transforma o "
        "sacrifício em força. Depois compre os ganhos, às cegas. O que sobrar fica guardado "
        "para o próximo voto. Um voto pode ser quebrado pela pausa, com punição. O Altar "
        "abre ao fim de cada capítulo.",
    ),
    "voto_luta": (
        "約",
        "O voto de luta",
        "Toda luta oferece um voto rápido: uma Promessa, uma Revelação ou um Selo. Aperte V "
        "para ver e jurar; não gasta o turno. Promessa cumprida dá prêmio, quebrada cobra.",
    ),
}
