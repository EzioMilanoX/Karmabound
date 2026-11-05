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
    "caminho": (
        "岐",
        "O caminho",
        "Antes de cada luta que não é de chefe, três portas (1–3, ou ← → e Enter). Rival: "
        "um lutador. Bando: dois ou três, cada um com um papel. Elite: mais forte, e "
        "vencer garante uma Relíquia. Encruzilhada: sem luta, uma escolha com preço. "
        "Olhe a sua vida antes de escolher.",
    ),
    "encruzilhada": (
        "辻",
        "Encruzilhada",
        "Um encontro sem luta. Cada opção dá algo e cobra algo: vida, vida máxima, Carma. "
        "A que pede mais Carma do que você tem fica apagada. Algumas levam a um giro de "
        "Técnica ou de Relíquia. Depois, o caminho segue.",
    ),
    "bando": (
        "群",
        "Bando",
        "Vários rivais, cada um com um papel: a Lâmina (刃) bate forte, o Guardião (盾) "
        "protege o mais ferido, o Curandeiro (癒) fecha as feridas, o Xamã (呪) amaldiçoa, o "
        "Comandante (将) faz todos baterem mais. Em quem bater é a luta: ↑ ↓ ou Tab troca "
        "o alvo. Derrube o Curandeiro primeiro.",
    ),
    "nemesis": (
        "仇",
        "Nêmesis",
        "Quem te matou numa run passada voltou, mais forte e com o golpe que te matou. "
        "Vencer: Relíquia, Carma, um Despertar guardado e Memória a mais. Perder de novo a "
        "deixa ainda mais forte. Ela aparece uma vez por run.",
    ),
    "treino": (
        "修",
        "Treino",
        "Os rivais ganham vida a cada luta. Depois de cada vitória você escolhe um treino "
        "(1–3), e ele fica pelo resto da run: vida, dano, Velocidade, Percepção, fôlego ou "
        "Carma.",
    ),
    "chefe": (
        "鬼",
        "Chefe",
        "O chefe tem postura: um golpe só tira no máximo 30% da vida dele. As feridas que "
        "duram (chama, veneno, sangramento, Marca) passam pela postura. Na metade da vida "
        "ele revela a segunda forma: mais dano e todas as técnicas prontas de novo.",
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
    "fusao": (
        "融",
        "Fusão",
        "Algumas peças se completam: duas ou três técnicas, o seu Dom, a Linhagem, uma "
        "Relíquia ou um Despertar. Juntas, nasce uma técnica nova, uma vez por run, no "
        "lugar da primeira peça. Na escolha de técnica, o selo 融 marca a peça que falta; "
        "o Grimório guarda as receitas que você já descobriu.",
    ),
    "ressonancia": (
        "共",
        "Ressonância",
        "Três técnicas equipadas do mesmo anime ressoam: um bônus temático vale enquanto "
        "elas estiverem na mão; com quatro, o bônus sobe de nível. O selo 共 na escolha "
        "mostra quem forma ou avança uma; a pausa (Esc) mostra as ativas.",
    ),
    "guarda": (
        "崩",
        "Quebra de guarda",
        "Cada golpe que fere enche a guarda do rival; golpes múltiplos enchem mais. Quando "
        "ela quebra, ele perde o próximo turno e sofre +25% até agir de novo. A guarda "
        "esvazia um pouco a cada turno dele: pressione sem parar. No chefe, ela aguenta "
        "mais e não fura a postura.",
    ),
    "afixo": (
        "強",
        "Afixos de elite",
        "A elite chega com afixos sorteados ao entrar: Vampírico, Espinhos, Veloz, "
        "Blindado e outros. Cada um muda o jeito de lutar contra ela; o painel do rival "
        "diz quais. Vencer a elite garante uma Relíquia.",
    ),
    "aliado": (
        "伴",
        "Aliado",
        "Alguém luta do seu lado. Os rivais nunca o atacam: ele age no começo dos seus "
        "turnos (fere, cura, protege, expõe ou envenena) e cresce um nível a cada luta "
        "vencida. Só um por run: um novo toma o lugar do antigo.",
    ),
    "mecanica": (
        "魔",
        "A mecânica do chefe",
        "Cada chefe tem um truque próprio (pétalas que passam pelos clones, armadura que "
        "se renova, uma balança que decide quem obedece). O nome e o que ele faz aparecem "
        "no painel do chefe: leia antes de gastar as suas melhores técnicas.",
    ),
    "ascensao": (
        "昇",
        "Ascensão",
        "Você venceu: a mesma dificuldade agora tem um degrau acima. Na escolha da "
        "dificuldade, ← → escolhe a Ascensão; cada nível soma a sua regra às de baixo. "
        "Vencer na Ascensão mais alta abre a próxima.",
    ),
}
