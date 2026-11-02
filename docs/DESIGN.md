# Karmabound — Design

Documento vivo do jogo. Decisões tomadas em 2026-11-02; o que ainda está em aberto fica no fim.

## Pitch

Um torneio de lutadores amaldiçoados, em dark fantasy com estética de anime. Você não escolhe seu poder: **gira por ele**. Dons, técnicas, o arco de cada capítulo e as relíquias saem de rodas de sorteio. Todo azar fica preso ao seu **Carma**, e quando o Carma transborda, no pior momento, você **Desperta**.

Origem: blueprint **GAM-10 F.O.R.T.U.N.A.** (`PersonalBlueprints/00 Visualizador/data.js`).

## Pilares

1. **O azar é suspense, não frustração.** Cada giro ruim enche o Carma. O jogador torce pela desgraça quando o medidor está quase cheio.
2. **Todo poder tem um preço.** Dark fantasy: nenhuma força vem de graça. O custo é parte da estratégia, não um castigo.
3. **A roleta é o jogo.** As decisões importantes acontecem entre girar e escolher; a luta é onde você descobre se escolheu bem.

## Loop de uma run

```
Roda do Destino → seu Dom e sua origem
  └─ Capítulo (arco sorteado na Roda do Arco: torneio, invasão, maldição, treino…)
       ├─ Luta por turnos contra um rival
       ├─ Giro de Técnica: gira 3, escolhe 1
       ├─ Às vezes: giro de Relíquia
       └─ Chefe do capítulo
  └─ Final do torneio
Morreu? A run acaba. O que fica entre runs: em aberto (ver fim).
```

## As quatro rodas

| Roda | Decide | Modo |
| --- | --- | --- |
| **Destino** | O Dom inato e a origem do personagem; mais tarde, o destino de rivais e aliados | gira e aceita |
| **Técnicas** | Golpes, variações e combos | gira 3, escolhe 1 |
| **Arco** | A regra do capítulo (modificador global) | gira e aceita |
| **Relíquias** | Itens e aliados; duplicatas evoluem o que você já tem | gira e aceita |

Todas são **dados** (JSON): fatias com peso, raridade e tags. Sorteio por **seed**, reproduzível.

## Carma e Despertar (o coração)

- **Pity suave:** a cada giro abaixo de raro, o peso das raridades altas sobe um pouco.
- **Pity duro:** ao atingir o limite, o próximo giro é garantidamente da raridade máxima.
- **Carma compartilhado:** o saldo de azar é **um só** para todas as rodas. Azar numa Relíquia ajuda o próximo Destino.
- **Despertar:** quando o Carma transborda **durante uma luta**, o próximo turno abre um giro especial garantido, com cena de transformação.
- Taxas visíveis: a tela mostra a taxa publicada e o Carma atual. Sem dinheiro real, nunca.

**Risco conhecido:** o jogador pode "perder de propósito" para encher o Carma. Por isso o Carma sobe com **giros ruins, dano recebido e custos de poder pagos**, nunca com derrota (derrota acaba a run). Calibrar com simulação Monte Carlo antes de mexer em números.

### Decisões de balanceamento (2026-11-02)

- **Run curta, ~20 min:** 3 capítulos de 3 lutas + chefe = 12 lutas, ~20 giros.
- **Raridades temáticas:** Cinza (60%) → Sangue (28%) → Maldito (10%) → Divino (2%). A ordem é a ordem de valor.
- **Alvo: 1–2 Despertares por run.** Calibração escolhida (`karmabound/data/balanceamento.json`): giro Cinza +6, Sangue +3, dano +22 por vida inteira perdida, custo de poder +6. Resultado em 10.000 runs: média 1,34 — 59% das runs com 1, 38% com 2, 3% sem nenhum; o primeiro chega por volta da luta 7.
- **Sofrer alimenta o Carma:** pagar o custo de um poder também enche o medidor.
- **Divino por sorte consome 40 de Carma** (a sorte "paga" o carma).
- **Carma transbordando trava** até o Despertar, para um giro bom não apagar um Despertar garantido.
- **Run sem Despertar é permitida** (~3%): nem todo mundo recebe seu momento. Sem garantia no chefe final.
- **Pity suave:** acima de 60 de Carma, Maldito e Divino ganham peso, até ×3 no máximo.

Para recalibrar: `python tools/simular.py` (o teste `test_calibracao_no_alvo` falha se a média sair de 1–2).

## Poderes: homenagem com nome próprio

Arquétipos reconhecíveis de anime são permitidos; **nomes, personagens e visual de obras existentes, não**. Cada poder tem nome, regra e **custo** próprios.

| Inspiração | No jogo | Custo |
| --- | --- | --- |
| Expansão de domínio | **Santuário**: fecha a arena por 3 turnos, seus golpes não erram | sai exausto (pula 1 turno) |
| Olho que copia | **Olho Roubado**: copia a última técnica do rival | fica cego no turno seguinte |
| Votos/restrições | **Juramento**: aceita uma restrição permanente na run em troca de poder | a restrição |
| Pacto com demônio | **Contrato**: poder enorme | remove uma fatia da sua Roda de Técnicas para sempre |
| Parar o tempo | **Instante Suspenso**: um turno extra | consome Carma |

## Tom e arte

- **Dark fantasy:** maldições, poder com preço, perdas que pesam (referências de tom: Jujutsu Kaisen, Chainsaw Man).
- **Arte viável em pygame:** começar com silhuetas, retratos simples, kanji e tinta, e uma UI forte. A roleta precisa ser bonita antes de qualquer personagem.

### A roleta (decidido e implementado em 2026-11-02)

- **Mandala de selos:** cada fatia é um selo com um kanji, num círculo ritual. O selo aceso corre pelo círculo, desacelera e para no resultado (decidido antes da animação, pela Mesa). Cada roda tem seu kanji no centro: 命 Destino, 技 Técnicas, 章 Arco, 宝 Relíquias.
- **Tinta sumi-e invertida:** tinta clara sobre laca escura, um ensō (círculo de pincel aberto) atrás da mandala, fonte de pincel **Yuji Syuku** em tudo (cobre kanji e acentos).
- **Correntes do Carma:** 44 elos em volta da mandala. Racham conforme o Carma sobe; acima do pity suave avermelham e pulsam; no transbordo tremem em vermelho vivo.
- **Despertar:** clarão dourado, 覚醒 no centro, os elos voam para fora e somem; depois o selo Divino acende com raios dourados.
- **Modo escolha:** os 3 selos sorteados acendem em sequência, ficam numerados na mandala, e o painel lista as opções (teclas 1–3).
- **Taxas visíveis:** o painel mostra a taxa publicada e a de agora (com pity) de cada raridade, destacando as que subiram.
- Teclas de teste nesta fase: D sofre dano, C paga custo (para ver as correntes sem combate).

## v0 (primeiro protótipo)

O `prototype` do GAM-10, ligado ao jogo:

1. Três rodas em JSON (Técnicas, Arco, Relíquias) + a Roda do Destino.
2. Pity suave e duro com Carma compartilhado.
3. `tools/simular.py`: 10.000 giros comparando taxa publicada e real, e o tempo médio até o Despertar.
4. Uma luta por turnos mínima (1v1, 3–4 técnicas) para sentir o Despertar no meio de uma luta.

**Pronto quando:** dá para jogar uma luta, girar uma técnica entre lutas e ver o Despertar acontecer, e a simulação mostra as taxas batendo.

## Combate (decidido até agora)

- **1v1 puro.**
- **Engine: híbrido.** Regras (rodas, Carma, combate) em Python puro e testável; tela, controles, saves e empacotamento pela OuroborosEngine. Efeitos próprios (o vocabulário de efeitos da engine é fechado e não cobre cegar, pular turno, copiar); se algum virar genérico, sobe para a engine depois.

### Regras (decididas em 2026-11-02, implementadas em `combate.py`)

- **Só recarga.** Turnos alternados; no seu turno você usa uma técnica pronta e ela fica fora por N turnos seus. Existe sempre um **Golpe básico** sem recarga, que não ocupa espaço.
- **4 espaços de técnica.** Técnica nova ganha na roleta substitui uma antiga quando está cheio.
- **Vida persiste na run**, com **30% de cura** entre lutas.
- **Velocidade** decide quem começa (empate: sorteio). A primeira ação da luta é um **ataque surpresa**: conta como perigosa e, se não for percebida, causa +50% de dano.
- **Percepção = sentir o perigo**, não iniciativa. Contra golpe perigoso (e na surpresa), se a Percepção do alvo for **maior ou igual à Sutileza** do golpe, ele reage: leva metade e devolve um Golpe básico. Determinístico, sem dado. Calibrada para reagir a **~33%** dos golpes perigosos (medido: 30–36% nos quatro modos).
- **O rival anuncia** a próxima ação ao fim do turno dele e a cumpre. A Percepção do jogador decide o quanto ele vê: 0 nada, 1 o tipo (ataque/defesa/maldita), 2 a técnica.
- Efeitos das técnicas (vocabulário próprio): dano, golpes múltiplos, bloqueio, revide, custo de vida (é custo de poder: enche o Carma), marca (o alvo sofre ao usar técnicas), fortalecer, dano proporcional ao Carma.

### Modos de dificuldade

Calibrados por simulação com o piloto automático (`python tools/simular.py --combate`). O primeiro rival sempre tem 12 de vida; os modos mudam o crescimento dos rivais, o chefe e a sua vida. Um jogador de verdade vence mais que o piloto.

| Modo | Vitória (piloto) | Rival | Chefe | Sua vida |
|---|---|---|---|---|
| Acessível | ~45% | 12 +1/luta | ×1,2 | 75 |
| Equilibrado | ~36% | 12 +1/luta | ×1,2 | 70 |
| **Difícil** (padrão) | ~25% | 12 +1,5/luta | ×1,25 | 70 |
| Brutal | ~10% | 12 +2/luta | ×1,25 | 65 |

Com combate real, o Carma enche **0,85–1,05 vez por run** em todos os modos: a calibração feita com dano aleatório se confirmou.

### A run na tela (decidido em 2026-11-02)

- **Layout de duelo frente a frente:** rival em cima, você embaixo, a corrente do Carma atravessando a tela entre os dois, cinco selos de técnica na base (o Golpe e os quatro espaços).
- **Silhuetas de tinta:** figuras de hakama e espada feitas de polígonos, com passadas de pincel deslocadas. Avançam ao golpear, tremem e ficam vermelhas ao apanhar. Sem rosto: a mesma figura serve de frente e de costas.
- **Ritmo animado e rápido:** ~0,6 s por ação, número de dano subindo, "percebeu!" em verde e "surpresa!" em dourado; o rival age sozinho depois de uma pausa curta.
- **Run completa jogável:** título com escolha de modo → Destino → Arco de cada capítulo → lutas → giro de Técnicas entre lutas (troca quando os 4 espaços estão cheios) → Relíquias às vezes → Altar quando sai o Juramento → fim. `jornada.py` é a run fase a fase, sem tela; `game.py` só troca de tela conforme a fase.
- **Altar simples:** você escolhe até 3 restrições e a duração; o Altar mede cada uma contra o seu build, compra os ganhos e mostra a estimativa de lutas a mais ou a menos antes de você jurar. A compra manual de ganhos fica para depois.
- **Despertar provisório:** enquanto o efeito na luta não é decidido, o Carma transbordado fica travado e o próximo giro de qualquer roda vira o Despertar (giro Divino garantido), como na roleta. O Julgamento ainda pode gastar esse Carma.

### Ainda não implementado no combate

- **Despertar:** vai ter **variedade** (ideias: Retribuição — a dor da luta volta ao rival; Tomar o destino — roubar uma técnica e travar as dele). **Gatilho em aberto** (assim que transborda, à beira da morte, ou quando o jogador quiser). Hoje a simulação só conta onde ele cairia.
- Percepção 3 (ver duas à frente) ainda não existe.
- Números das técnicas são rascunho; os poderes Malditos e Divinos têm efeito provisório até a conversa sobre o custo de cada um.

## Votos vinculativos — o Juramento (blueprint GAM-11 O.A.T.H.)

Decidido em 2026-11-02. O Juramento deixou de ser técnica de luta: tirá-lo na roleta abre o **Altar dos Votos**, onde o jogador monta o próprio voto, como nos animes (Nen, Jujutsu).

- **Restrições em categorias** (simples, conduta, revelação, risco) viram **pontos**; pontos compram **ganhos** (simples ou especiais). Catálogo em `karmabound/data/votos.json`; tudo legível em `docs/CATALOGO.md`.
- **O bônus vem do potencial sacrificado:** o valor de uma restrição é medido contra o build do jogador naquele momento, simulando o resto da run com e sem ela (mesmas seeds). Proibir o que você não usa não rende nada.
- **Pontos** = sacrifício × (1 + sacrifício ÷ K) × duração × categoria. K = 2. Duração: só esta luta ×1, até o fim do capítulo ×1,3, resto da run ×1,75. Categoria: simples ×1, conduta e revelação ×1,15, risco ×1,4. O bônus deve compensar muito.
- **Até 3 votos ativos**; voto expirado ou quebrado libera o espaço.
- **Quebrar:** perde os ganhos, perde metade da vida atual, o Carma zera, e é preciso jurar um **voto de quebra** (só restrições, sem ganhos). Quebrar o voto de quebra encerra a run.

**Achado da primeira medição (2026-11-02):** com o catálogo inicial, as restrições custavam mais do que o catálogo inteiro de ganhos devolvia (Sem Descanso custava 3,3 lutas; os 8 ganhos juntos devolviam 2,3), e o piloto sempre escolhia a restrição mais devastadora. Daí as duas decisões seguintes.

- **Ganhos em níveis + exclusivos fortes.** Ganhos simples até 5 níveis; o preço de cada nível é o benefício medido do 1º × o número do nível (retorno decrescente do lado do ganho). Três **exclusivos** de nível único, ×1,25 no preço: **Segunda Vida** (revive uma vez com 30%), **Carrasco** (+50% contra chefes), **Sangue Frio** (sempre reage à surpresa).
- **Retorno decrescente por restrição.** Cada restrição credita no máximo **1,5 luta** de sacrifício; o voto credita o sacrifício medido junto, limitado à soma desses créditos. A severidade continua compensando, mas para passar do teto é preciso **juntar restrições diferentes** — votos variados em vez de "Sem Descanso" sempre.
- Ferramenta: `python tools/medir_juramento.py` mede o valor do Juramento em pontos de vitória (a unidade da régua).
- **Valor alvo do Juramento: +10 a +15 pontos** (acima da régua geral do Maldito, decisão de 2026-11-02). Sem freio, os votos valiam +68. Um **câmbio** único no preço dos ganhos escala o poder total sem tirar o bônus de severidade; **câmbio 4 → +13,4 pontos** (300 runs, Difícil, Altar depois da luta 4).
- O piloto do Altar só jura se o voto completo compensa (como um jogador lendo a estimativa do Altar); sem isso, ele entrava em votos negativos com câmbio alto.
- O trio Sem Descanso + Corpo Ofertado + Voto Exposto ainda domina as escolhas do piloto; decidido não mexer por enquanto.

## Poderes Malditos e Divinos (redesenhados em 2026-11-02)

Medidos com `python tools/medir_poder.py`: o jogador começa com o poder no 3º espaço, contra uma linha de base com a Investida; 9.000 runs no Difícil. Régua: Maldito +5 a +10, Divino +10 a +20.

| Poder | Raridade | Como funciona | Valor |
|---|---|---|---|
| **Marca da Maldição** | Maldito | Golpe de 10 que amaldiçoa: o rival sofre 3 a cada turno dele, e cada nova Marca soma +3. Preço: você sofre 1 por turno por Marca aplicada. | **+8,4** |
| **Contrato** | Divino | Golpe de 60, uma vez por luta. Preço: cada uso destrói uma das suas outras técnicas para o resto da run (a mais fraca, ou a que você escolher). Sem outra técnica para sacrificar, fica indisponível. | **+11,3** |
| **Julgamento** | Divino | Dano = 0,8 × Carma, e consome todo o Carma — até um Carma transbordando. A dor vira golpe agora, ou espera o Despertar. | **+14,2** |
| Juramento | Maldito | Abre o Altar dos Votos (ver acima). | **+13,4** |

- A Marca como "só maldição" (sem dano) ficou negativa em todas as versões: as lutas duram ~4 turnos seus, e um turno sem atacar custa mais do que a maldição devolve. Virou golpe que amaldiçoa.
- O piloto usa os poderes caros como um jogador sensato: Contrato só para fechar a luta ou num chefe; Julgamento só para fechar a luta ou com Carma ≥ 60; Marca só em rival com vida e sem empilhar além de duas.
- Com o Julgamento consumindo Carma, os transbordos caíram para ~1,0 por run; o Carma por dano subiu de 32 para **44** para voltar a ~1,25. Os modos foram recalibrados depois disso (vida do jogador: 80 / 76 / 70 / 68).

## Dons, Relíquias, Arcos e duplicatas (2026-11-02)

Decidido: as três rodas que eram só texto passam a valer na luta; **sorte é permitida nos Dons** (a esquiva é a única sorte dentro da luta); os sistemas que faltavam foram criados (duplicatas, lutas extras, Despertar guardado). Régua estendida: **Cinza +1 a +3, Sangue +3 a +5** (Maldito +5 a +10, Divino +10 a +20).

Valores medidos com `python tools/medir_poder.py` (Difícil, 7.500 runs por item; ruído ~±2 pontos):

| Item | Raridade | Efeito | Valor |
|---|---|---|---|
| 体 Corpo Resistente (Dom) | Cinza | +3 de vida máxima | +3,1 |
| 速 Reflexo Treinado (Dom) | Cinza | 4% de chance de esquivar um golpe | +3,1 |
| 沸 Sangue Fervente (Dom) | Sangue | até +2 de dano, pela vida perdida | +4,8 |
| 影 Sombra Leal (Dom) | Sangue | a sombra repete 8% de cada golpe | +5,0 |
| 眼 Olho Roubado (Dom, técnica) | Maldito | usa a última técnica do rival com +40%; preço: cego até o próximo turno | +9,6 |
| 灰 Pele de Cinzas (Dom) | Maldito | o 1º golpe de cada luta não fere; preço: cura em 55% | +12,4 ⚠️ |
| 域 Santuário (Dom, técnica) | Divino | 1×/luta: 4 turnos de golpes imperceptíveis e +50%; preço: perde um turno | +6,3 ⚠️ |
| 刻 Instante Suspenso (Dom, técnica) | Divino | 1×/luta: duas ações seguidas; preço: 3 de vida | +15,2 |
| 布 Bandagem | Cinza | cura 2 no início de cada luta | +3,9 |
| 符 Amuleto Rachado | Cinza | 1×/run, golpe fatal deixa com 1 de vida | +3,1 |
| 骨 Rosário de Ossos | Sangue | +8 de Carma por rival derrotado | +7,5 ⚠️ |
| 鬼 Máscara de Oni | Sangue | +1 de dano; preço: bloqueios pela metade | +4,2 |
| 封 Coração Selado | Maldito | ao encher, o Carma vira um Despertar guardado (libera com E na roleta), e o Carma enche 50% mais rápido | +9,7 |
| 神 Fragmento do Deus Cego | Divino | duplicatas evoluem na hora, ×1,5 | +13,2 |
| 契 Contrato (técnica) | Divino | golpe de 40, 1×/luta, destrói outra técnica sua; o demônio cresce +10 por técnica consumida | +0,6 a +5 ⚠️ |
| 裁 Julgamento (técnica) | Divino | dano = 1,3 × Carma, consome o Carma | +13,6 |
| 呪 Marca da Maldição (técnica) | Maldito | golpe de 10 que amaldiçoa | +6,9 |

⚠️ fora da régua, a revisitar: **Santuário e Contrato** abaixo do piso do Divino; **Pele de Cinzas e Rosário** um pouco acima. O Contrato, mesmo crescendo, não passa de ~+5 com o piloto: perder técnicas pesa mais do que o golpe.

- **Duplicatas:** tirar de novo uma técnica que você tem dá 1 fragmento; 2 fragmentos evoluem a técnica (efeitos ×1,3, recarga −1, nome com II, III…). O Fragmento do Deus Cego evolui na hora, ×1,5. Relíquias repetidas se somam.
- **Arcos** (para os dois lados, o capítulo inteiro): Treino na Montanha (cura 50%), Torneio Regular (nada), Lua de Sangue (+3 de dano para todos), **Invasão (+1 luta no capítulo e Relíquia garantida a cada luta — a run fica com 12 ou mais)**, Maldição Coletiva (seu Carma ×2, rivais +20% de vida), Arco do Juízo (chefe +50% de vida e dano; vencê-lo enche o Carma).
- **Carma vale muito:** com o Despertar provisório (Carma cheio = Divino garantido), todo preço em Carma pesa demais. Por isso o Instante custa vida em vez de Carma (decisão de 2026-11-02).
- **Achados que eram defeito de regra, não de número:** o Instante gastava o turno e devolvia um (ganho zero) — agora são duas ações de verdade depois dele; o Coração Selado guardava só no giro (nada ganhava) — agora guarda no instante em que o Carma enche.
- **Arquitetura:** as regras da run são passos em `run.py` (`aplicar_dom`, `aplicar_arco`, `comecar_luta`, `encerrar_luta`, `receber_tecnica`, `receber_reliquia`, `girar`). O piloto automático e a Jornada do jogador usam os mesmos passos: o simulador mede exatamente o jogo que se joga.
- **Modos recalibrados** depois disso: o jogador ficou bem mais forte, então os rivais crescem +4,4 / +4,65 / +4,7 / +5,8 de vida por luta (antes +2 a +2,5). Resultado: 45,0% / 37,5% / 25,8% / 8,5%.

## Poderes impossíveis de balancear

Preocupação levantada em 2026-11-02: alguns arquétipos (parar o tempo, copiar, golpe que nunca erra, dano igual ao Carma) quebram qualquer luta.

**Filosofia decidida: quebrado, mas com preço.** Poderes absurdos existem e são a recompensa, mas cada um cobra um custo à altura. O jogador decide se vale pagar. O custo de cada poder ainda será definido um a um.

Ferramentas para calibrar os custos:

- **Quebrado de propósito, mas raro e preso à run:** em roguelites (Balatro, Hades), o build quebrado é a recompensa. O problema real é quando um poder anula as escolhas da run inteira.
- **Custo proporcional:** quanto mais forte, mais caro (já é o pilar 2).
- **Usos limitados:** uma vez por luta ou por run.
- **Contra-jogo:** chefes com resistências específicas (imune a cópia, vê através do Santuário).
- **Medir em vez de adivinhar:** quando o combate existir, simular runs com cada poder e procurar os que destoam na taxa de vitória.

## Em aberto

- **Despertar:** quais variedades e qual gatilho.
- Revisitar **Santuário, Contrato, Pele de Cinzas e Rosário** (fora da régua).
- **Conteúdo das rodas:** nomes e textos atuais são rascunho.
- **Progressão entre runs:** desbloquear fatias novas nas rodas? Carma residual?
- **Estilo de arte** definitivo.
