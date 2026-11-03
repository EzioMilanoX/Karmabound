# Karmabound

**Torneio dark fantasy por turnos, com estética de anime, construído sobre a [Ouroboros Engine](https://github.com/EzioMilanoX/OuroborosEngine).**

Você não escolhe seu poder: **gira por ele**. Dons, técnicas, o arco de cada capítulo e as relíquias saem de rodas de sorteio desenhadas como uma mandala de selos. Todo azar fica preso ao seu **Carma** — e quando o Carma transborda, no pior momento, você **Desperta**.

> Protótipo jogável. Uma run inteira já se joga do título ao fim, e tudo o que sai da roleta vale na luta: 59 habilidades — cada uma uma **homenagem** a um anime ou mangá, com a origem na carta —, Dons, técnicas, Relíquias, Arcos com arena própria, duplicatas que evoluem, o Altar dos Votos, o Despertar e o Grimório, com quatro modos de dificuldade calibrados por simulação. Executável do Windows pelo `build.bat`.

📖 **[Manual](docs/index.html)** — o jogo explicado por dentro: a roleta, o Carma, a luta e os votos.

![Uma luta: o rival anuncia a próxima ação, a corrente do Carma atravessa a tela e as técnicas ficam na base](docs/telas/run_03_luta.png)

## Rodando

Requisitos: Python ≥ 3.11, `pygame-ce` e a Ouroboros Engine com as primitivas de UI do marco M16 (círculos, arcos, polígonos e fontes customizadas).

```bash
# com o repositório da engine clonado ao lado (recomendado para dev):
pip install -e ../OuroborosEngine --no-deps
pip install numpy pygame-ce

# ou direto do GitHub:
pip install "ouroboros-engine @ git+https://github.com/EzioMilanoX/OuroborosEngine.git"

# na raiz deste repositório:
python -m karmabound
```

No Windows, **`run.bat`** na raiz faz o mesmo com duplo clique, e **`build.bat`** gera o executável em `dist\Karmabound\` (PyInstaller, onedir). Passo a passo e problemas comuns em [INSTALL.md](INSTALL.md). `python -m karmabound --roleta` abre só a roleta, como caixa de areia (Tab troca de roda; D e C enchem o Carma sem lutar).

### Controles

| Onde | Ação | Tecla |
|---|---|---|
| Título | Escolher o modo / começar / Grimório / opções | ↑ ↓ / Enter / G / O |
| Durante a run | Pausa: continuar, opções, quebrar um voto, voltar ao título | Esc |
| Opções | Música, efeitos, silenciar, tela cheia, velocidade, dicas | ↑ ↓ / ← → |
| Grimório | Trocar de roda / de habilidade / voltar | ← → / ↑ ↓ / Backspace |
| Roleta | Girar / escolher 1 de 3 / continuar | Espaço / 1–3 / Enter |
| Luta | Usar a técnica do selo (6 = técnica do Dom) | 1–6 (ou ← → e Enter) |
| Luta | Despertar (com o Carma cheio; não gasta o turno) | E |
| Luta | Contrato: escolher a técnica sacrificada / desistir | 1–5 / Backspace |
| Espaços cheios | Trocar uma técnica / descartar a nova | 1–4 / Backspace |
| Altar | Mover / marcar restrição ou escolher opção / voltar | ↑ ↓ / Enter / Backspace |
| Altar (compra) | Comprar um nível do ganho / devolver / voltar | → ou Enter / ← / Backspace |
| Título e fim da run | Sair | Esc |

### Uma run

Título → **Destino** (seu Dom) → para cada um dos 3 capítulos: **Arco** (a regra do capítulo) → 3 lutas e o chefe. Depois de cada vitória: 30% de cura e um giro de **Técnicas** (escolhe 1 de 3; com os 4 espaços cheios, troca uma). Às vezes, um giro de **Relíquias**. O **Juramento** abre o Altar dos Votos. A run acaba ao vencer as 12 lutas — ou ao cair.

## A ideia em uma frase

Num roguelite, a sorte costuma ser o inimigo. Aqui ela é **o suspense**: cada giro ruim aproxima o Despertar, e o jogador passa a torcer pela desgraça quando o medidor está quase cheio.

## Homenagens: todo poder tem uma origem

Cada habilidade é uma homenagem com nome próprio, e a origem aparece na carta, na luta e no Grimório: a **Espiral Concentrada** é o Rasengan (Naruto), o **Clarão Negro** é o Kokusen (Jujutsu Kaisen), o **Corte do Mundo** é o corte que divide o mundo do Sukuna, o **Corpo Perfeito** é o Sukuna da Era Heian, o **Instante Suspenso** é The World (JoJo), a **Liberação Final** é o Bankai (Bleach). As obras vão de Naruto, One Piece, Bleach, Dragon Ball e Hunter x Hunter a Jujutsu Kaisen, Demon Slayer, Chainsaw Man, Berserk, Solo Leveling e Attack on Titan. A lista completa, com a origem de cada uma, está no [catálogo](docs/CATALOGO.md).

O **Grimório** (G, no título) guarda todas as habilidades que já saíram da roleta, entre runs; as que faltam aparecem como ???.

A run **fica salva** a cada fase: o título oferece **Continuar a run** (no meio de uma luta, ela recomeça igual — mesmo rival, mesma sorte). A **Semente do dia** dá a todo mundo a mesma sorte no Difícil, e o título mostra o seu melhor resultado do dia.

Na **primeira run**, cada sistema se explica uma vez, na primeira vez que aparece (dá para desligar ou rever nas opções). **Esc** pausa: dali se abrem as opções (volume da música e dos efeitos, silenciar, tela cheia, velocidade das animações) e se **quebra um voto**, com a punição e o voto de quebra.

### O visual

- **Um efeito por habilidade**, em tinta: a esfera que gira do Rasengan, os raios do Hekireki Issen, a lua negra do Getsuga, as correntes do Kurapika, o Domínio que fecha a arena, o tempo parado em sépia, a tela que se parte no Corte do Mundo.
- **Lutadores articulados**: um esqueleto com poses (parado respirando, guarda, ataque, golpe recebido), roupa e rosto por estilo. Rivais: Ronin, Monge Errante, Shinobi, Oni, Hollow e Titã; o chefe é um colosso de quatro braços, com uma **técnica-assinatura** (Senbonzakura, Susanoo, Chibaku Tensei, Kamui, Mugetsu, Leigan).
- **Arenas com profundidade**: camadas em parallax, luz, névoa, um primeiro plano na frente dos lutadores e a cena tremendo nos golpes. Dez Arcos, cada um com a sua (entre eles a Torre Celestial, a Floresta da Morte, Hueco Mundo e o Torneio do Poder).
- **Sombrio**: vinheta, grão de tinta, o sangue dos golpes que fica no chão, espadas quebradas fincadas e corvos no céu.
- **Uma aura por Despertar**, e cartas com moldura da raridade e a linha de origem.
- **Cinema**: o rival entra numa pincelada de tinta com o nome em caligrafia (o chefe escurece a tela antes); na vitória ele se desfaz em tinta, na derrota as correntes se fecham sobre você; o título respira (ensō, corrente do Carma, tinta escorrendo); entre telas, a tinta cobre e recolhe.
- **Som e música sintetizados em código** (`python tools/gerar_sons.py`): taiko, gongo, sinos, shamisen, koto, correntes e cortes, em escalas japonesas. Uma faixa para o título, a roleta, a luta e o chefe; a música da luta acelera quando o Carma enche.

![O Corte do Mundo atravessando a tela contra o chefe, em Marineford](docs/telas/vitrine/06_marineford_corte_do_mundo.png)

## A roleta: quatro rodas, um destino

| Roda | Decide | Modo |
|---|---|---|
| 命 **Destino** | O Dom inato e a origem do personagem | gira e aceita |
| 技 **Técnicas** | Golpes, defesas e técnicas malditas | gira 3, escolhe 1 |
| 章 **Arco** | A regra do capítulo (Lua de Sangue, Invasão, Maldição Coletiva…) | gira e aceita |
| 宝 **Relíquias** | Itens; duplicatas evoluem o que você já tem | gira e aceita |
| 覚 **Despertar** | O tipo de Despertar (8), na luta: Bankai, Ultra Instinto, Modo Sábio... | sorteio igual |

Tudo o que a roleta entrega vale na luta: o **Dom** (efeito passivo ou uma técnica própria, num 6º selo), as **Relíquias** (acumulam e se somam), o **Arco** (a regra do capítulo, para os dois lados — a Invasão até acrescenta uma luta) e as técnicas, que **evoluem** quando repetidas (2 fragmentos = nível II). Cada item foi medido em pontos de vitória contra uma régua por raridade.

Cada fatia é um **selo com um kanji**, colorido pela raridade: **Cinza** (60%), **Sangue** (28%), **Maldito** (10%), **Divino** (2%). O resultado é decidido antes da animação; o selo aceso só corre pelo círculo até ele. A tela mostra a **taxa publicada ao lado da taxa real** de cada raridade — sem dinheiro, nunca.

## Carma e Despertar

O Carma é um **pity compartilhado entre todas as rodas**. Ele enche com giros ruins, com dano recebido e com o preço dos poderes pagos — sofrer alimenta o Carma.

- **Pity suave:** acima de 60, Malditos e Divinos ficam até 3× mais prováveis. As correntes em volta da mandala racham e avermelham.
- **Transbordo:** em 100, as correntes tremem e o Carma fica esperando a luta.
- **Despertar:** na luta, quando você quiser (E, sem gastar o turno) — ou sozinho, quando um golpe for te matar: o golpe é anulado. O tipo sai da **Roda do Despertar**, com oito: 報 Retribuição (a dor da luta volta ao rival), 奪 Tomar o Destino (rouba a melhor técnica dele), 醒 Forma Desperta (dano dobrado, sem recarga), 鳳 Renascer das Cinzas (cura total e escudo), 卍 Liberação Final (Bankai), 極 Instinto Puro (Ultra Instinto), 仙 Modo Eremita (Modo Sábio) ou 痣 Marca do Caçador. E o próximo giro depois da luta vem Divino garantido.
- **Calibrado** por simulação de lutas reais: cerca de **1,2 Despertar por run**. Algumas runs terminam sem nenhum — nem todo mundo recebe seu momento.

## Lutas: só recarga

Duelo 1v1, turnos alternados, regras curtas:

- Você usa **uma técnica pronta** por turno; ela fica fora por alguns turnos seus. O **Golpe básico** nunca entra em recarga.
- **4 espaços** de técnica. **Vida persiste** na run, com 30% de cura entre lutas.
- **Velocidade** decide quem começa — e quem começa tenta um **ataque surpresa** (+50% de dano se não for percebido).
- **Percepção é sentir o perigo:** contra golpe perigoso, se a sua Percepção for ≥ a **Sutileza** do golpe, você leva metade e devolve um golpe. Determinístico, sem dado; calibrado para salvar ~33% das vezes.
- **O rival anuncia** a próxima ação e cumpre. Sua Percepção decide o quanto você vê: nada, o tipo, ou a técnica.

### Modos de dificuldade

Calibrados com um piloto automático simples em 12 lutas — um jogador de verdade, lendo o rival, vence mais.

| Modo | Vitória (piloto) | Rivais | Sua vida |
|---|---|---|---|
| Acessível | ~45% | 12 + 4,57 por luta, chefe ×1,2 | 80 |
| Equilibrado | ~36% | 12 + 4,72 por luta, chefe ×1,2 | 76 |
| **Difícil** (padrão) | ~25% | 12 + 4,81 por luta, chefe ×1,25 | 70 |
| Brutal | ~10% | 12 + 5,92 por luta, chefe ×1,25 | 68 |

### Poderes com preço

Os poderes mais raros são quebrados de propósito — e cobram à altura. Cada um foi medido em pontos de vitória contra uma régua (Maldito +5 a +10, Divino +10 a +20):

| Poder | Raridade | O que faz | O preço | Vale |
|---|---|---|---|---|
| 呪 Marca da Maldição | Maldito | Golpe de 10; o rival sofre 4 por turno, e Marcas se somam | você sofre 1 por turno por Marca | +4,5 |
| 幻 Lua Ilusória (Tsukuyomi) | Maldito | O rival perde o próximo turno | 2 de vida: os olhos sangram | +7 |
| 界 Corte do Mundo (Sukuna) | Divino | 50 de dano que atravessa bloqueio, escudo e esquiva, impossível de perceber | só fica pronto no seu 4º turno | +9,5 |
| 宿 Corpo Perfeito (Sukuna Heian) | Divino | Quatro braços: o Golpe acerta 2× com +2 | você nunca defende | +13 |
| 卵 Ovo do Eclipse (Behelit) | Divino | Desperta à beira da morte, mesmo sem Carma (1×/run) | o seu Dom é sacrificado | +16 |
| 契 Contrato | Divino | Golpe de 40, uma vez por luta; cresce +7 a cada técnica consumida | destrói uma das suas outras técnicas para sempre | +12 |
| 裁 Julgamento | Divino | Dano = 1,8 × o seu Carma | consome todo o Carma — e o Despertar que vinha com ele | +15 |

## Votos vinculativos (o Juramento)

Tirar o **Juramento** na roleta abre o **Altar dos Votos**: você monta o próprio voto, como nos animes. Escolhe **restrições** — simples (−25% de vida), de conduta (nunca usar defesa), de revelação (o rival te lê melhor) ou de risco (cair abaixo de 20% é morte) — e os pontos compram **ganhos**: simples em níveis (Força, Vigor, Percepção, Velocidade), especiais (Golpe Oculto, Primeiro Sangue…) e exclusivos (Segunda Vida, Carrasco, Sangue Frio).

**Você compra os ganhos.** O Altar abre com a compra que ele faria já marcada, e você mexe à vontade — mas às cegas: sem preço nem estimativa, só uma barra com a **força do voto** que resta e o aviso de quando um ganho não cabe mais. O que você não gastar **fica guardado** para o próximo voto (dá até para jurar só as restrições e guardar toda a força).

O que torna o sistema diferente: **o valor de uma restrição não é tabelado**. O Altar simula o resto da sua run com e sem ela e mede o potencial que você realmente sacrificaria. Proibir o que você não usa não rende nada; proibir o seu melhor golpe rende muito. Sacrifícios maiores e permanentes rendem mais que a soma, mas cada restrição tem um teto — para ir além, é preciso combinar restrições diferentes. Quebrar um voto é possível, com punição e um voto de quebra que, se quebrado, encerra a run. Calibrado, o Juramento vale cerca de **+13 pontos de vitória**.

O conceito vive também como blueprint reutilizável (**GAM-11 O.A.T.H.**).

## Arquitetura

Híbrida: **regras em Python puro**, **apresentação pela engine**.

```
karmabound/
  rodas.py      dados das rodas e sorteio por seed
  carma.py      pity suave e duro, compartilhado
  mesa.py       uma sessão de giros: a tela e o simulador giram pela mesma Mesa
  combate.py    a luta 1v1 por recarga, IA do rival e piloto automático
  efeitos.py    o que votos, Dons e Relíquias fazem no lutador
  votos.py      catálogo, pontos, teto, preço e quebra dos votos
  run.py        os passos de uma run (Dom, Arco, luta, técnica, relíquia) + o piloto automático
  simulacao.py  runs em massa para calibrar
  jornada.py    a run jogada por uma pessoa, fase a fase (as telas só chamam a Jornada)
  tela_roleta.py  a mandala, as correntes e o Despertar (IScene da engine)
  tela_luta.py  o duelo frente a frente
  tela_menus.py título, troca de técnica, Altar dos Votos e fim
  figuras.py    as silhuetas de tinta (5 estilos), feitas de polígonos
  vfx.py        um efeito de tinta por habilidade e uma aura por Despertar
  arenas.py     o cenário de cada Arco
  som.py        efeitos e música por nome (mudo até o jogo configurar)
  grimorio.py   o que já saiu da roleta, salvo entre runs (~/.karmabound)
  tela_grimorio.py  o Grimório: todas as habilidades, com a origem
  visual.py     paleta, fonte e utilitários de desenho
  game.py       o Fluxo: põe a tela da fase atual da Jornada no topo da engine
  data/         rodas, balanceamento, controles e votos em JSON
```

- **Tudo que é número está em JSON** (`karmabound/data/`): raridades, Carma, técnicas, modos, votos.
- A tela desenha só pela API do `IRenderer` da engine (`draw_ui_*`, `draw_text` com fonte própria) — nunca com pygame direto.
- O sorteio é sempre por **seed**: qualquer bug de sorte é reproduzível.

## Ferramentas e testes

```bash
pytest                              # testes headless, incluindo runs inteiras jogadas pelas telas
ruff check .                        # lint
python tools/simular.py --combate   # vitórias, Carma e Percepção por modo
python tools/medir_juramento.py     # quanto o Juramento vale em pontos de vitória
python tools/medir_poder.py         # quanto cada Dom, Relíquia e técnica vale, contra a régua
python tools/calibrar.py tudo       # o ciclo inteiro: modos no alvo (--aplicar grava) e itens contra a régua
python tools/gerar_catalogo.py      # regenera docs/CATALOGO.md a partir dos JSON
python tools/capturar_telas.py      # PNG de cada estado da roleta e das telas da run, em docs/telas/
python tools/vitrine.py             # PNG de cada arena, rival e efeito, em docs/telas/vitrine/
python tools/gerar_sons.py          # sintetiza os efeitos e as músicas em assets/ (WAV)
python tools/gerar_icone.py         # o ícone (業 dourado) em assets/
```

## Documentação

- **[docs/index.html](docs/index.html)** — o manual.
- **[docs/DESIGN.md](docs/DESIGN.md)** — todas as decisões de design, com data e motivo.
- **[docs/CATALOGO.md](docs/CATALOGO.md)** — todo o conteúdo (rodas, técnicas, votos, modos), gerado dos dados.
- **[docs/telas/](docs/telas/)** — capturas de cada estado da roleta; **[docs/telas/vitrine/](docs/telas/vitrine/)**, as arenas e os efeitos.

## Licença

Uso para testes e avaliação; todos os direitos reservados — ver [LICENSE](LICENSE). A fonte **Yuji Syuku** (`assets/fonts/`) é distribuída sob a SIL Open Font License 1.1 ([OFL.txt](assets/fonts/OFL.txt)).
