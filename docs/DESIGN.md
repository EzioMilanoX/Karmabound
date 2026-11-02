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

### Ainda não implementado no combate

- **Despertar:** vai ter **variedade** (ideias: Retribuição — a dor da luta volta ao rival; Tomar o destino — roubar uma técnica e travar as dele). **Gatilho em aberto** (assim que transborda, à beira da morte, ou quando o jogador quiser). Hoje a simulação só conta onde ele cairia.
- **Dons e Relíquias** ainda não têm efeito na luta; Percepção 3 (ver duas à frente) também não.
- Números das técnicas são rascunho; os poderes Malditos e Divinos têm efeito provisório até a conversa sobre o custo de cada um.
- Tela de luta.

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
- **Custo de cada poder** Maldito e Divino (filosofia já decidida: quebrado, mas com preço).
- **Conteúdo das rodas:** nomes e textos atuais são rascunho.
- **Progressão entre runs:** desbloquear fatias novas nas rodas? Carma residual?
- **Estilo de arte** definitivo.
