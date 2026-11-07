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
Roda da Linhagem → o sangue de onde você vem
Roda do Destino → seu Dom
  └─ Capítulo (arco sorteado na Roda do Arco: torneio, invasão, maldição, treino…)
       ├─ Luta por turnos contra um rival
       ├─ Giro de Técnica: gira 3, escolhe 1
       ├─ Às vezes: giro de Relíquia
       └─ Chefe do capítulo
  └─ Fim do capítulo: o Altar dos Votos abre (jurar é opcional)
  └─ Final do torneio
Morreu? A run acaba. O que fica entre runs: em aberto (ver fim).
```

## As rodas

| Roda | Decide | Modo |
| --- | --- | --- |
| **Linhagem** | O clã, a família ou o povo: atributos, às vezes uma técnica, e um preço nas raras | gira e aceita |
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

Calibrados por simulação com o piloto automático (`python tools/simular.py --combate`). O primeiro rival sempre tem 24 de vida; os modos mudam o crescimento dos rivais, o chefe e a sua vida. Um jogador de verdade vence mais que o piloto.

| Modo | Vitória (piloto) | Rival | Chefe | Sua vida |
|---|---|---|---|---|
| Acessível | ~45% | 24 +4,94/luta | postura | 127 |
| Equilibrado | ~36% | 24 +5,70/luta | postura | 119 |
| **Difícil** (padrão) | ~25% | 24 +6,61/luta | postura | 110 |
| Brutal | ~10% | 24 +9,28/luta | postura | 107 |

Valores de 2026-11-04, recalibrados depois da expansão (`python tools/calibrar.py modos --aplicar`): os rivais crescem menos por luta do que antes (eram 4,6–5,9). Mesmo com o Altar garantido e o voto de luta do lado do jogador, foi preciso baixar a vida deles. Os rivais sorteiam técnicas da mesma roda, e as novas (gravidade, sangramento, bomba) pesam mais na mão deles.

Recalibrados de novo depois da Leva 3: o jogador ficou mais forte com as formas, os clones e as invocações, e o Difícil e o Brutal subiram (3,64 → 3,87 e 4,44 → 5,05 por luta); o Acessível e o Equilibrado quase não mudaram. Com o efeito próprio de cada ferida (logo abaixo), o Brutal voltou um pouco (5,21 → 5,05) e os outros mudaram menos de 0,03.

Com combate real, o Carma enche **0,85–1,05 vez por run** em todos os modos: a calibração feita com dano aleatório se confirmou.

### A run na tela (decidido em 2026-11-02)

- **Layout de duelo frente a frente:** rival em cima, você embaixo, a corrente do Carma atravessando a tela entre os dois, cinco selos de técnica na base (o Golpe e os quatro espaços).
- **Silhuetas de tinta:** figuras de hakama e espada feitas de polígonos, com passadas de pincel deslocadas. Avançam ao golpear, tremem e ficam vermelhas ao apanhar. Sem rosto: a mesma figura serve de frente e de costas.
- **Ritmo animado e rápido:** ~0,6 s por ação, número de dano subindo, "percebeu!" em verde e "surpresa!" em dourado; o rival age sozinho depois de uma pausa curta.
- **Run completa jogável:** título com escolha de modo → Destino → Arco de cada capítulo → lutas → giro de Técnicas entre lutas (troca quando os 4 espaços estão cheios) → Relíquias às vezes → Altar quando sai o Juramento → fim. `jornada.py` é a run fase a fase, sem tela; `game.py` só troca de tela conforme a fase.
- **Altar com compra manual** (2026-11-02): você escolhe até 3 restrições e a duração; o Altar mede cada uma contra o seu build e dá a força do voto. A compra abre com a sugestão do Altar marcada e você muda nível a nível. **Às cegas, por decisão:** a tela não mostra preço nem benefício nem a estimativa final — só a barra de força que resta e "não cabe". **A sobra fica guardada** para o próximo voto (`EstadoRun.pontos_guardados`; o piloto automático também guarda).

### O Despertar (decidido e implementado em 2026-11-02)

- **Gatilho:** com o Carma cheio (ou um Despertar guardado pelo Coração Selado), o jogador desperta **quando quiser** — tecla E na luta, e não gasta o turno. Se um golpe do rival for matá-lo antes, o Despertar **dispara sozinho e anula o golpe**.
- **Variedade:** o tipo sai da **Roda do Despertar** (sorteio igual, fora do Carma), girada no momento:
  - 報 **Retribuição:** a dor recebida na luta volta ao rival, dividida nos seus próximos 3 golpes.
  - 奪 **Tomar o Destino:** rouba a melhor técnica do rival para o resto da run; as dele entram em recarga por 2 turnos.
  - 醒 **Forma Desperta:** por 3 turnos, dano dobrado e nada entra em recarga.
  - 鳳 **Renascer das Cinzas:** cura total, e os próximos 2 golpes do rival não ferem.
- **O Divino garantido continua:** o próximo giro depois da luta vem Divino. O Carma cheio fica esperando a luta — não desperta mais no giro.
- Frequência com o piloto (que desperta contra chefes ou com pouca vida): **~1,2 Despertar por run**.
- O Despertar de verdade fez o jogo ~12 pontos mais fácil e mudou o valor de tudo que mexe com Carma (Santuário subiu de +6 para +14; Julgamento caiu para +3, Coração e Rosário subiram demais) — itens e modos recalibrados de novo.

### Homenagens e visual (decidido e implementado em 2026-11-02)

- **Toda habilidade é uma homenagem com nome próprio**, e a origem fica escrita (`origem` no JSON: "técnica · obra") na carta da roleta, sob o selo na luta, na intenção do rival e no Grimório. Fontes: shonen amplo (Naruto, One Piece, Bleach, Dragon Ball, HxH, JoJo, JJK, Demon Slayer, Chainsaw Man, Berserk, Solo Leveling, Attack on Titan).
- **24 habilidades novas** (10 técnicas, 6 Dons, 4 Relíquias, 4 Despertares), com mecânicas novas quando a referência pedia: atravessar bloqueio (Rasengan), golpe absoluto que espera o 4º turno (Corte do Mundo), crítico ×2,5 (Kokusen), surpresa sempre (Hekireki Issen), selar a ação anunciada (Corrente do Kurapika), cura (Ninjutsu Médico), dano pela dor sofrida (Genki Dama), atordoar (Tsukuyomi), Golpe duplo (Sukuna Heian), regeneração abaixo de 40% (Oni), espaço extra (Akuma no Mi), Despertar sem Carma (Behelit), e quatro Despertares (Bankai: técnicas +1 nível na luta; Ultra Instinto: 60% de esquiva com revide; Modo Sábio; Marca do Caçador: +50% de dano, −10% de vida para sempre).
- **Medidas na régua.** Lições da medição: **ser perigosa** pesa muito numa técnica do jogador (o rival que percebe leva metade e devolve um Golpe) — a Espiral com 17 e perigosa valia menos que sem perigo; **Percepção e Velocidade valem demais** (+1 de Percepção num Cinza deu +9; +1 de Velocidade, +7) — o Sentir a Intenção virou "a surpresa do rival não ganha bônus", e o Sangue de Soldado subiu para Maldito.
- **Os rivais também sorteiam as técnicas novas** (a Esfera dos Mil cresce com a dor deles), o que endureceu o jogo; os modos foram recalibrados.
- **Visual:** um efeito por habilidade (`vfx.py`, funções puras do progresso da animação), uma arena por Arco (`arenas.py`), cinco silhuetas de rival (Ronin, Monge, Shinobi, Oni e o colosso dos chefes), uma aura por Despertar e cartas com moldura de raridade.
- **A fonte de pincel (Yuji Syuku) não tem mácron nem setas** (ō, ū, ↳ viram um quadrado): as romanizações vão sem mácron (Myoboku, Tensho) e um teste confere todo texto do jogo contra a fonte.
- **Grimório:** guarda os ids já vistos em `~/.karmabound/grimorio.json` (pasta trocável por `KARMABOUND_SAVE`; os testes usam uma temporária). Só a Jornada registra — o simulador nunca toca no arquivo.

### Som, música e cinema (decidido e implementado em 2026-11-02)

- **Tudo sintetizado em código** (`tools/gerar_sons.py`, numpy): taiko com a pele que afina depois da batida, gongo de parciais inarmônicos, sinos, shamisen e koto por Karplus-Strong (o shamisen com o zumbido do sawari), correntes, vento e cortes de ruído filtrado. Sem assets de terceiros; seed fixa.
- **Músicas em loop sem emenda**: mistura num buffer circular (as caudas voltam para o começo) e as camadas contínuas entram e saem em rampa sobre a emenda. Escalas hirajoshi e in. Faixas: título (koto, drone, vento), roleta (batida de coração), luta (taiko e shamisen), luta com o Carma cheio (mais densa) e chefe (odaiko, gongo, trítono).
- `som.py` é mudo até o jogo chamar `SOM.configurar` (testes e simulador nunca tocam nada); arquivo que falta ou placa de som ausente vira silêncio, nunca erro.
- **Cinema**: entrada do rival (1,7 s; o chefe 2,6 s), vitória (o rival se desfaz em tinta) e derrota (as correntes se fecham), título animado, e uma transição de tinta no começo de cada tela.
- **Reação**: o Primeiro Trovão passou a sutileza 1 — a reação a golpes perigosos tinha caído para 17% (o alvo de design é ~33%); voltou a 26–31% sem mudar as vitórias.

### Polimento para jogar (2026-11-02)

- **Pausa** (Esc em qualquer tela da run): continuar, opções, quebrar um voto, voltar ao título (pede confirmação: a run se perde) e sair. No título e no fim, Esc sai.
- **Opções**, salvas em `~/.karmabound/opcoes.json`: volume da música e dos efeitos (0–10), silenciar, tela cheia, velocidade das animações (1×, 1,5×, 2×), dicas. O volume da música pediu um marco na engine (**M17**: `IAudioEngine.set_track_volume`, default no-op).
- **Dicas da primeira run**: cada sistema se explica uma vez (roleta, Arco, luta, Percepção, Despertar, técnicas, espaços cheios, Relíquias, Altar). `KARMABOUND_DICAS=0` desliga (os testes usam).
- **Quebrar um voto pela tela**: a regra já existia (`Votos.quebrar`); agora `Jornada.quebrar_voto` e a tela. O voto de quebra fica no lugar do quebrado pelo prazo que faltava.
- **Bug achado pelo teste:** jurar um voto recalculava o lutador só com os votos — o Dom e as Relíquias sumiam até o fim da luta seguinte (e o Altar media os votos com esse defeito). `aplicar_voto` agora recalcula tudo.

### Continuar e semente do dia (2026-11-02)

- **A run salva a cada fase** (`salvar.py`, `~/.karmabound/run.sav`, um espaço só). Sair no meio de uma luta guarda a **foto de antes dela** (`Jornada.antes_da_luta`): ao continuar, a luta recomeça igual, com o mesmo rival e a mesma sorte — sair de uma luta ruim não sorteia outra. Vitória ou derrota apagam o arquivo; arquivo de outra versão ou estragado é ignorado.
- **Semente do dia**: Difícil, seed tirada da data (todo mundo gira a mesma sorte); o melhor resultado de cada dia fica em `recordes.json` e aparece no título e no fim da run.
- A pausa não pede mais confirmação para voltar ao título: a run fica salva.

### Visual de verdade e conteúdo novo (2026-11-02)

- **Lutadores articulados** (`figuras.py`): juntas montadas de uma `Pose` (inclinação, agachamento, ombros, cotovelos, arma, cabeça); as poses se misturam (parado → guarda → ataque → golpe recebido) e o corpo respira. Por estilo: kimono e hakama com dobras, manto, juba, chifres, máscara de osso, músculos, vapor. O jogador é visto de costas (sem rosto).
- **Arenas em camadas** (`arenas.py`): uma câmera que deriva desloca cada camada pela profundidade; brilhos de luz, névoa, primeiro plano nas bordas (na frente dos lutadores, longe da interface) e `abalo` nos golpes.
- **Sombrio** (pedido de 2026-11-02): vinheta, grão de tinta, céu mais escuro, sangue que fica no chão, espadas fincadas e corvos.
- **4 Arcos** (Torre Celestial: +1 de dano por vitória no capítulo; Floresta da Morte: sem cura, Relíquia a cada vitória; Hueco Mundo: Carma ×1,5 e rivais +1 de Percepção; Torneio do Poder: uma luta a menos, chefe ×1,6, vencê-lo guarda um Despertar) e **técnicas-assinatura dos chefes** (`data/chefes.json`).
- Continuar uma run recarrega os dados atuais (`Contexto.padrao`): um ajuste de balanceamento vale também para a run salva.

### Calibrador automático (2026-11-02)

- `tools/calibrar.py` faz sozinho o ciclo que era manual: para cada modo mede a vitória em três valores de vida dos rivais, ajusta uma reta, acha o valor do alvo, confere e (com `--aplicar`) grava. Para os itens, compara com a **régua**, que agora é dado (`balanceamento.json` → `regua`), e só aponta o lado — o que mexer em cada item é decisão de design.

### Controle (2026-11-02)

- Joga-se inteiro de controle (XInput: Xbox, e DualShock/genéricos pelo mapeamento do SDL): direcional ou analógico move, A confirma e gira, B volta, Start pausa, Y desperta, X abre as opções e Back o Grimório no título. A engine já resolvia `PAD_*`; o que faltava era cursor nas telas que só aceitavam números (escolher 1 de 3 na roleta, o sacrifício do Contrato, a troca de técnica).

### Crônica e Feitos (2026-11-02)

- `cronica.py` guarda cada run terminada (modo, lutas, Dom, Despertares, votos, Relíquias) e doze Feitos, avaliados do estado final — sem contadores espalhados pelo jogo. Um Feito novo aparece no fim da run; a tela da Crônica (C / LB no título) mostra os Feitos e as últimas runs.

### Ainda não implementado no combate

- Percepção 3 (ver duas à frente) ainda não existe.
- Números das técnicas comuns são rascunho.

## Votos vinculativos — o Juramento (blueprint GAM-11 O.A.T.H.)

Decidido em 2026-11-02. O Juramento deixou de ser técnica de luta: tirá-lo na roleta abre o **Altar dos Votos**, onde o jogador monta o próprio voto, como nos animes (Nen, Jujutsu).

**Desde 2026-11-04 o Juramento não é mais uma fatia da roleta**: o Altar abre sozinho ao fim de cada capítulo (duas vezes por run), e na luta existe o voto de luta (ver "Expansão").

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
| Juramento (até 2026-11-03) | Maldito | Abria o Altar dos Votos; hoje o Altar abre entre capítulos. | **+13,0** (re-medido em 2026-11-02, com o Altar manual, a força guardada e o bug dos efeitos corrigido) |

- A Marca como "só maldição" (sem dano) ficou negativa em todas as versões: as lutas duram ~4 turnos seus, e um turno sem atacar custa mais do que a maldição devolve. Virou golpe que amaldiçoa.
- O piloto usa os poderes caros como um jogador sensato: Contrato só para fechar a luta ou num chefe; Julgamento só para fechar a luta ou com Carma ≥ 60; Marca só em rival com vida e sem empilhar além de duas.
- Com o Julgamento consumindo Carma, os transbordos caíram para ~1,0 por run; o Carma por dano subiu de 32 para **44** para voltar a ~1,25. Os modos foram recalibrados depois disso (vida do jogador: 80 / 76 / 70 / 68).

## Dons, Relíquias, Arcos e duplicatas (2026-11-02)

Decidido: as três rodas que eram só texto passam a valer na luta; **sorte é permitida nos Dons** (a esquiva é a única sorte dentro da luta); os sistemas que faltavam foram criados (duplicatas, lutas extras, Despertar guardado). Régua estendida: **Cinza +1 a +3, Sangue +3 a +5** (Maldito +5 a +10, Divino +10 a +20).

Valores medidos com `python tools/medir_poder.py` na dificuldade final (Difícil, 6.000 runs por item; ruído ~±2 pontos), depois das 24 habilidades-homenagem. O valor de um item depende da força do resto do jogo (o tamanho das rodas, o que os rivais sorteiam, os Divinos que todo Despertar entrega), então itens e modos foram recalibrados juntos.

| Item | Raridade | Efeito | Valor |
|---|---|---|---|
| 体 Corpo Resistente (Dom) | Cinza | +3 de vida máxima | +3,8 |
| 速 Reflexo Treinado (Dom) | Cinza | 4% de chance de esquivar | +3,8 |
| 見 Sentir a Intenção (Dom) | Maldito | a surpresa do rival não ganha bônus | +7,7 |
| 沸 Sangue Fervente (Dom) | Sangue | até +1,5 de dano, pela vida perdida | +3,2 |
| 影 Sombra Leal (Dom) | Sangue | a sombra repete 8% de cada golpe | +5,2 |
| 再 Carne que Volta (Dom) | Sangue | abaixo de 30% da vida, cura 1 por turno | +5,8 |
| 兵 Sangue de Soldado (Dom) | Maldito | +1 de Velocidade; −6 de vida | +4,9 |
| 眼 Olho Roubado (Dom, técnica) | Maldito | usa a última técnica do rival com +25%; cego até o próximo turno | +9,0 |
| 灰 Pele de Cinzas (Dom) | Maldito | o 1º golpe de cada luta não fere; cura em 63% | +6,7 |
| 六 Olhos que Tudo Veem (Dom) | Maldito | +2 de Percepção; −10% de vida | +8,3 |
| 門 Portões Abertos (Dom) | Maldito | +5 de dano; 1 de vida por turno | +7,5 |
| 域 Santuário (Dom, técnica) | Divino | 4 turnos imperceptíveis e +50%; perde um turno | +19,7 |
| 刻 Instante Suspenso (Dom, técnica) | Divino | duas ações seguidas; 8 de vida | +18,0 |
| 宿 Corpo Perfeito (Dom) | Divino | Golpe 2× com +2; nunca defende | +12,7 |
| 布 Bandagem | Cinza | cura 1 no início de cada luta | +3,5 |
| 符 Amuleto Rachado | Cinza | 1×/run, golpe fatal deixa com 1 | +3,9 |
| 重 Manto de Peso | Cinza | +1 de vida máxima a cada 2 vitórias | +2,8 |
| 骨 Rosário de Ossos | Sangue | +3 de Carma por vitória | +2,9 |
| 鬼 Máscara de Oni | Sangue | +1 de dano; bloqueios pela metade | +2,6 |
| 刀 Lâmina Adormecida | Sangue | técnicas com +8% de dano | +3,8 |
| 封 Coração Selado | Maldito | o Carma cheio vira um Despertar guardado; Carma +20% | +7,9 |
| 果 Fruta Proibida | Maldito | +1 espaço de técnica e +1 de dano | +7,5 |
| 神 Fragmento do Deus Cego | Divino | duplicatas evoluem na hora, ×1,8 | +10,4 |
| 卵 Ovo do Eclipse | Divino | desperta sem Carma, 1×/run; perde o Dom | +15,5 |
| 雷 Primeiro Trovão | Cinza | 6, sempre surpresa | +1,2 |
| 分 Clones de Sombra | Cinza | 3 golpes de 3 | +2,8 |
| 癒 Mão Curadora | Cinza | cura 5 | +1,3 |
| 螺 Espiral Concentrada | Sangue | 14 que atravessa bloqueio | +4,0 |
| 黒 Clarão Negro | Sangue | 8, 20% de sair ×2,5 | +3,1 |
| 牙 Presa da Lua | Sangue | 12, sutileza 4 | +3,4 |
| 鎖 Corrente do Julgamento | Sangue | 7 e sela a ação anunciada | +2,8 |
| 元 Esfera dos Mil | Maldito | 10 + a dor sofrida, até +20 | +6,8 |
| 幻 Lua Ilusória | Maldito | o rival perde o turno; 2 de vida | +6,7 |
| 呪 Marca da Maldição | Maldito | golpe de 10 que amaldiçoa (4 por turno) | +4,5 |
| 契 Contrato | Divino | golpe de 40, 1×/luta, destrói outra técnica; +7 por técnica consumida | +12,3 |
| 裁 Julgamento | Divino | dano = 1,8 × Carma, consome o Carma | +14,6 |
| 界 Corte do Mundo | Divino | 50 absoluto, pronto no 4º turno | +9,5 |

Todos dentro da régua (±2 de ruído) depois da segunda rodada de ajustes (2026-11-02). A Pele de Cinzas mostrou o quanto a cura entre lutas vale: com a cura a 55% ela dava +2; a 75%, +20.

- **O Contrato e o tamanho da roda.** Com 10 técnicas, os giros traziam muita repetida (fragmento) e o Contrato ficava sem o que consumir. Com 20, quase todo giro traz uma técnica nova, e o Contrato (+15 por técnica consumida) virava uma bola de neve: +45 pontos. Agora cresce +5. A mesma causa derrubou o Fragmento do Deus Cego (que vive de repetidas), que passou a ×1,8.
- **A Esfera dos Mil nos rivais.** Os rivais também sorteiam as técnicas novas; uma Esfera sem teto num rival que já apanhou 60 devolvia 70 de dano e empurrava o jogo inteiro para matar rápido. O bônus da dor tem teto de +20.

- **Duplicatas:** tirar de novo uma técnica que você tem dá 1 fragmento; 2 fragmentos evoluem a técnica (efeitos ×1,3, recarga −1, nome com II, III…). O Fragmento do Deus Cego evolui na hora, ×1,5. Relíquias repetidas se somam.
- **Arcos** (para os dois lados, o capítulo inteiro): Treino na Montanha (cura 50%), Torneio Regular (nada), Lua de Sangue (+3 de dano para todos), **Invasão (+1 luta no capítulo e Relíquia garantida a cada luta — a run fica com 12 ou mais)**, Maldição Coletiva (seu Carma ×2, rivais +20% de vida), Arco do Juízo (chefe +50% de vida e dano; vencê-lo enche o Carma).
- **Carma vale muito:** cheio, ele é um Despertar na luta e um Divino depois. Todo preço em Carma pesa demais — por isso o Instante custa vida (decisão de 2026-11-02), e o Julgamento precisa de um golpe enorme para compensar.
- **Achados que eram defeito de regra, não de número:** o Instante gastava o turno e devolvia um (ganho zero) — agora são duas ações de verdade depois dele; o Coração Selado guardava só no giro (nada ganhava) — agora guarda no instante em que o Carma enche.
- **Arquitetura:** as regras da run são passos em `run.py` (`aplicar_dom`, `aplicar_arco`, `comecar_luta`, `encerrar_luta`, `receber_tecnica`, `receber_reliquia`, `girar`). O piloto automático e a Jornada do jogador usam os mesmos passos: o simulador mede exatamente o jogo que se joga.
- **Modos:** com Dons, Relíquias, Despertar e Divinos fortes, os rivais cresciam +5,8 / +6,1 / +6,2 / +7,5 de vida por luta. Com as homenagens (que os rivais também usam) e os ajustes do Contrato e do Instante, passaram a +5,25 / +5,5 / +5,55 / +6,7 (com a força do Altar guardada entre votos) e, com os Arcos novos e as técnicas de chefe (já suavizadas: Floresta com metade da cura, Torneio do Poder com chefe ×1,4), a +4,8 / +4,95 / +4,95 / +6,05; depois da régua dos itens (Amuleto vira Maldito, Corpo +2, Manto a cada 3, Clones 3×2, Pele 58%, Fervente 2,5, Corte do Mundo 58), o calibrador automático levou a +4,57 / +4,72 / +4,81 / +5,92 e, com os 12 Despertares, a **+4,6 / +4,77 / +4,77 / +5,9**. Resultado: **43,8% / 36,3% / 25,0% / 9,5%**.

## Expansão (2026-11-04)

Pedido: 150 poderes novos, 30 Despertares, Linhagens, mais votos, e o Juramento como mecânica, não como poder. Decisões tomadas com o Enzo:

- **O Juramento sai da roleta.** O Altar dos Votos abre ao fim de cada capítulo (fora da luta). Na luta, um **voto de luta**, mais limitado e diferente: toda luta a roleta oferece um, sorteado entre três tipos, e o jogador jura com V (ou RB) uma vez por luta, sem gastar o turno.
  - **Promessa:** meta com prazo (vencer em N turnos, não ser ferido, só o Golpe, não defender, causar X de dano). Força na hora; cumprir dá prêmio, falhar cobra.
  - **Revelação:** expor algo ao rival (ele ganha Percepção, ou o seu dano sofrido sobe) em troca de força — "revelar a técnica" deixa a próxima técnica usada muito mais forte até o fim da luta.
  - **Selo:** selar parte de si até o fim da luta (defesa, Golpe, Percepção, metade da vida, o Despertar, a técnica mais forte) e a força volta em outro lugar.
- **Linhagem**, roda nova (gira e aceita) antes do Dom: 30 (12 Cinza, 9 Sangue, 6 Malditas, 3 Divinas). Muda o corpo; algumas começam com uma técnica num espaço (`inicial`), outras trazem uma técnica própria que não ocupa espaço.
- **150 poderes:** 90 técnicas (35 Cinza, 28 Sangue, 18 Malditas, 9 Divinas), 35 Dons e 25 Relíquias, todos homenagens com nome próprio. Mais **30 Despertares** e **17 votos novos no Altar** (8 restrições, 9 ganhos), e **18 votos de luta**.
- **Mecânicas novas de combate** (`combate.py`): sangramento (3 turnos), roubo de vida, execução (dobra abaixo de X%), enfraquecer, cegar (o alvo não percebe N golpes), expor (+50% nos próximos golpes), acelerar recargas, dissipar defesas, dano que acumula a cada uso, gravidade (fração da vida do alvo, com teto), detonar Marca e sangramento, combo (por técnica em recarga), desespero (pela vida perdida), bomba-relógio, silêncio (só o Golpe), desarme (sem defesa), espelho (devolve o golpe), regeneração na luta, dano sorteado, e o preço que fica na run: **vida máxima perdida a cada uso**. Os Despertares ganharam chaves novas (atordoar, renovar as técnicas, ações extras, execução, troca das frações de vida, +dano pelo resto da run, bomba…). Dons e Relíquias: roubo de vida, execução, sangrar, recarga −1, primeiro golpe, último suspiro, vida cheia, contra marcados, bloqueio inicial, Sutileza, Golpe que fura, crescer por turno, dano ×, dano sofrido ×, chance de Relíquia.
- **Textos que não mentem:** os textos da roleta usam marcadores (`{dano}`, `{drenar%}`, `{dano_mult+%}`) preenchidos pelos números na carga; o afinador mexe no número e o texto acompanha.
- **Tela:** a mandala mostra no máximo 20 selos (uma amostra fixa com todas as raridades, e sempre as fatias sorteadas); o Grimório rola; a luta mostra a técnica da Linhagem, até 8 selos, os estados novos, o painel do voto de luta e a promessa em andamento.
- **O Altar ficou rápido:** com o catálogo dobrado e o jogo mais pesado, pesar levava 36 s. Agora mede o próximo capítulo (4 lutas, 30 continuações) e projeta para o resto da run: ~1–2 s.
- **O simulador também jura:** como o Altar é garantido, a dificuldade precisa contar com ele. O Altar do simulador (`run.altar_rapido`) usa valores típicos de cada restrição e ganho (`tipico` em `votos.json`, medidos por `tools/medir_tipicos.py`) em vez de medir na hora.
- **O afinador** (`tools/afinar.py`): mede cada item pela régua e mexe no número principal (dano, efeito ou recarga) de quem sai da faixa, por rodadas. O passo é amortecido, e um passo que deixa o item mais longe da faixa é desfeito. O afinador nunca mexe em preço; preço muda só à mão (abaixo).

### O balanceamento da expansão (2026-11-04)

Duas rodadas do afinador, uma medição final (2000 runs × 3 seeds, no Difícil) e ajustes à mão. Resultado: dos 172 itens novos, **123 ficaram na régua** (com folga de 1 ponto); os outros estão listados abaixo. O ruído da medição é de cerca de ±1,5 ponto.

O que a primeira rodada ensinou:

- **O piloto queimava vida à toa.** Ele usava golpes que custam vida máxima para sempre (Lua sem Luz, Vazio Púrpura, Banquete) em toda luta que eles fechavam. Quanto mais dano o afinador dava, mais lutas eles fechavam, e pior mediam (o dano da Lua sem Luz chegou a 184). Agora o piloto só os usa contra chefe ou abaixo de 35% da vida. Preparos pagos em vida só entram em luta longa e nunca enquanto o efeito está de pé; golpes que custam 6 de vida ou mais ficam para chefe ou para fechar uma luta que vale a pena.
- **Preparar não valia nada.** As lutas comuns duram de 1 a 3 turnos do jogador, e o turno gasto preparando era o turno que derrubava o rival: o Deus do Sol com +40 de dano medía o mesmo que com +15. Decisão: os preparos de uma vez por luta (Deus do Sol, Vontade do Rei, Céu Acelerado, Kaioken, Quarta Marcha, Os Mascarados, Sangue de Ymir) **não gastam o turno** (campo `livre` da técnica; "livre" no selo). O piloto só prepara com turno gasto se a luta ainda vai durar (rival com mais que o dobro do melhor golpe).
- **Duas mecânicas que nem o mínimo segurava:** +1 de dano por turno (Esquentar, Relógio de Bolso) valia +10 pontos; agora o crescimento é fracionário (0,2 e 0,4 por turno; vale a parte inteira). O sangramento passivo (Veneno de Glicínia, Pilares da Chama) somava a cada golpe; agora ele renova, não empilha.
- **Golpes de muitos acertos** valem muito mais do que parecem, porque todo bônus fixo de dano entra em cada acerto. As Sessenta e Quatro Palmas tinham 8 golpes e mediam +24; com 5, +7. As Nove Cabeças do Dragão ficaram com 6 golpes.
- **Degraus:** um golpe que passa a matar o rival comum de uma vez muda de valor num salto (a Onda de Ki foi de −1 a +11 entre 31 e 43 de dano; ficou em 40). Por isso o afinador amortece o passo.

Preços e raridades mudados à mão: Explosão Final 20 → 10 de vida; Lua sem Luz −8 → −3 de vida máxima; Banquete −2 → −1; Pedra Filosofal, Selo de Restrição e Respiração Constante −15%/−10% → −5% de vida máxima; Olhos Brancos −6 → −3 de vida. Viraram de outra raridade porque o efeito vale outra coisa: Olho Transplantado (Maldito → Cinza), Espada que Bebe (Maldito → Cinza, sem preço), Imortal (Divino → Maldito) e Clã dos Cães (Cinza → Sangue).

**Ainda fora da régua (medição final):**

| Grupo | Itens | Medem | Por quê |
|---|---|---|---|
| Preparos e controle Malditos/Divinos | Céu Acelerado, Vazio Púrpura, Vontade do Rei, Lua sem Luz, Era do Gelo, Deus do Sol, Guerreiro Espectral, Quarta Marcha, Kaioken, Grilhão, Calma Absoluta, Possessão, Prisão de Cristal, Arte Explosiva, Banquete, Carne Maldita, Previsão, Sexto Sentido | −4 a 0 | O número quase não muda o resultado: a run do piloto morre por pico de dano nas lutas comuns, não por falta de dano. Um jogador que guarda esses poderes para o chefe tira mais deles do que o piloto. |
| Recargas −1 | Respiração Constante, Selo de Restrição | ≈ −1,5 | Recarga −1 vale pouco com lutas curtas; o preço já foi a −5%. |
| Técnicas Sangue | Muralha de Terra, Névoa Venenosa, Luz Cegante, Olhos do Futuro, Pistola a Jato, Dança dos Ossos, Pele de Diamante, Rajada de Dempsey, Bomba-Relógio, Selo da Força de Cem, Enxame, Gaiola de Fios, Sombra que Prende | +0 a +2 | A técnica entra no 3º espaço, que pesa pouco: até a Investida com 30 de dano mede só +4. |

O que fica em aberto: medir esses grupos com um piloto que guarda poderes para o chefe, ou mudar a régua das técnicas (que hoje compara só o 3º espaço).

## Leva 3: fidelidade, transformações e modos de jogo (2026-11-04)

Pedido do Enzo: a wiki também por anime; mais técnicas e habilidades pensadas, com mais suporte e dano contínuo; explorar o que cada poder faz na obra ("a Amaterasu: o fogo que nunca apaga até incinerar"); transformações e modos de jogo. Decidido com ele: ~80 itens novos mais a revisão de fidelidade dos antigos, e equilibrar os animes (aprofundar os que tinham pouco e trazer novos).

- **Wiki por anime:** a wiki (`docs/wiki.html`, gerada por `tools/gerar_catalogo.py`) agrupa por roda ou por anime, com filtro de anime. O anime sai do fim da origem (`… · Naruto`); um teste garante que toda origem o diga.
- **Mecânicas novas de combate** (`combate.py`, campos de `Tecnica`):
  - `chama_eterna`: a chama negra não apaga e cresce 1 a cada turno, até o fim da luta. Basta o olhar: não há esquiva, escudo ou espelho, e purificar não apaga.
  - `veneno`: doses que se somam, ferem e caem 1 por turno. Em golpe, só entra se ferir; sem golpe (névoa, gás), entra direto.
  - `congelar`: o alvo perde N turnos, e o próximo golpe nele causa ×2 e quebra o gelo.
  - `clones`: cada clone ataca junto (40% do golpe, até 3) e absorve um golpe recebido.
  - `invocar` (+ `invocar_turnos`): uma invocação que fere sozinha a cada turno seu.
  - `vinculo` (o ritual do Hidan): por N turnos seus, toda dor que você sofre o alvo também sofre — o ritual vem antes do preço, então a estocada em si mesmo já é dividida.
  - `purificar`: tira sangramento, veneno, Marca, cegueira, selos, bombas e o que enfraquecia.
  - `custo_percepcao` (o Mangekyou): −N de Percepção pelo resto da run, a cada uso.
  - Efeitos passivos novos: `dot_mult` (o que você aplica fere mais), `veneno_ao_ferir`, `veneno_espinhos` (quem te fere é envenenado), `clones_inicio`, `invocar_inicio`, `modo_extra` (formas mais longas). Despertares ganharam `chama`, `veneno`, `clones`, `invocar` e `purificar`.
- **Transformações** (`Modo`, tipo de técnica `modo`): por `turnos` turnos seus, +dano, ×dano, golpes a mais, Percepção, Sutileza, cura ou sangria por turno, esquiva, bloqueio renovado, dano recebido ×, roubo de vida, `inabalavel` (não cai abaixo de 1; o dano fica adiado), `absoluto`, `sem_recarga`. O preço vem quando a forma acaba: `exausto` (turnos perdidos), `travar` (todas as técnicas em recarga), `perde_vida_frac`, `vida_max_run`, `adiado` (a Armadura cobra tudo de uma vez). Uma forma por vez; trocar cobra a anterior. Os textos usam `{modo_turnos}`, `{modo_dano_mult+%}` etc.
- **Transformar não gasta o turno.** A primeira medição mostrou de novo o que a expansão ensinou: com lutas de 1 a 3 turnos, uma forma que gasta o turno mede negativo (o Cabelo Dourado deu −8,5). Toda transformação e as Chamas Negras são `livre`; o custo fica no preço, que é o da obra.
- **Revisões de fidelidade:** Chamas Negras (chama eterna + Mangekyou, virou Maldita), Lua Ilusória (atordoa, enfraquece, cobra Percepção), Punho Carmesim/Kaioken e Deus do Sol/Gear Fifth (viraram transformações), Quarta Marcha (forma com bloqueio e sem Haki depois), Berserker (a Armadura: inabalável e o dano adiado), Clones de Sombra (clones de verdade), Agulhas de Veneno (Shizune, veneno), Enxame (os insetos comem chakra: drenar), Névoa Venenosa (veneno), Lança de Gelo e Era do Gelo (congelar), Marionetes (veneno do Sasori), Mão Curadora (tira o veneno), Veneno de Glicínia (veneno a cada golpe).
- **Itens novos:** 60 técnicas, 8 Dons, 7 Relíquias, 6 Linhagens, 3 Despertares, 2 Arcos (com arena) e 3 técnicas de chefe. Animes novos: Frieren, Mob Psycho 100, Fate, Dandadan e My Hero Academia; e mais de JJK, JoJo, Berserk, FMA, Hellsing, Black Clover, Demon Slayer, Chainsaw Man, SAO e Solo Leveling. "Dragon Ball Super" virou "Dragon Ball", para o agrupamento.
- **Modos de jogo** (`Contexto.padrao(jogo=…)`, escolhidos no título com ← →): Clássico; **Torre sem fim** (capítulos sem fim; o Altar e o piloto projetam um horizonte de 12 lutas; o recorde por dificuldade fica em `recordes.json`); **Desfile de chefes** (3 capítulos de 2 lutas, todas contra chefes); **Mundo de um anime** (as rodas filtradas por anime, para animes com 10+ técnicas; uma raridade que o anime não tem numa roda entra com os convidados de fora, e as técnicas iniciais ficam sempre). A run salva lembra o modo.
- **Telas:** as listas de voto (Altar e quebra) rolam com barra de rolagem (`rolagem.py`); a luta mostra 炎 chama, 毒 veneno, 氷 gelo, 影 clones, 召 invocação, 儀 ritual, 鎧 dano adiado e 変 a forma ativa, com aura própria por transformação (`vfx.AURAS_MODO`).

### O balanceamento da Leva 3 (2026-11-04)

Três passadas do afinador (que aprendeu as transformações: mexe no multiplicador, no dano, na esquiva, no bloqueio ou na cura da forma, senão na duração), ajustes à mão e uma medição final (2000 runs × 3 seeds, no Difícil, antes da recalibração das dificuldades). Dos 97 itens novos e revisados, **57 ficaram na régua** (folga de 1 ponto).

O que a medição ensinou:

- **Transformar tem que ser livre** (acima). E o piloto só se transforma com preço (sangria, exaustão, travar, vida máxima, Armadura) em luta que vale: chefe ou rival com 30 de vida ou mais. Antes ele pagava a sangria em toda luta.
- **Clones absorvendo golpes inteiros** eram fortes demais (um clone grátis por luta valia +35). Agora o golpe acha um clone em N de N+1 vezes ("quem sabe qual é o verdadeiro?"), e o Dom dos clones virou uma técnica de Dom (2 clones, gasta o turno).
- **Invocações chegavam tarde:** com lutas de 1 a 3 turnos, uma invocação que só atacava a partir do turno seguinte quase não lutava. Agora ela ataca ao chegar (o mesmo total de ataques, antes).
- **Degraus de novo:** a Espada da Vitória Prometida mediu +14 com 40 de dano e +42 com 52 (passa a matar o chefe de uma vez); ficou em 40. O Soco que Quebra o Braço e a Lança do Coração têm o mesmo degrau.
- **Golpes de muitos acertos e bônus fixo** continuam valendo mais do que parecem: a Espada Grande Demais (+1 de dano em todo golpe) mede como Maldita, e virou Maldita.
- **Números que o afinador infla sem efeito:** Caixão Negro chegou a 94 de dano, O Indomável a 34 por turno, o Punho Carmesim a ×3,84, sem sair do negativo. Voltaram a números razoáveis à mão: não vale deformar o jogo para agradar um piloto que só usa esses poderes no chefe.

**Ainda fora da régua (medição final):**

| Grupo | Itens | Medem | Por quê |
|---|---|---|---|
| Suporte | Mão Curadora, Punhado de Sal, Arraia Curandeira, Diamante que Conserta, Barreira de Mana, Olhar que Apaga, Disco Cortante | −0,5 a 0 | Cura e defesa no 3º espaço quase não aparecem na régua (o mesmo limite da expansão). |
| Controle e preparo | O Indomável, Era do Gelo, Caixão Negro, Lua Ilusória, Chamas Negras, Ritual de Sangue, Sete Pétalas, Chiclete Elástico, Levantem-se, Apagar o Tempo, Mãos Invisíveis, Lótus de Gelo, Punho Carmesim | −8 a −1,5 | Insensíveis ao número com o piloto de hoje; as que cobram Percepção ou vida na run ele só usa contra chefe. |
| Sangue abaixo de +2 | Sangue Acelerado, Ponto Monstro, Chacal, Olhar de Pedra, Mil Clones, Sapo Chefe, Névoa Venenosa, Máscara de Pedra | 0 a +1,5 | O 3º espaço pesa pouco. |
| Malditas abaixo de +4 | Velocidade Divina, Caixão da Montanha, Cabelo Dourado, Tempo do Imperador | +0,8 a +3,7 | Formas: medidas com o piloto que só se transforma em luta grande. |

Remedidos depois dos ajustes à mão: Motosserra +2,7, Casa dos Feiticeiros +3,1, Mana Escondida +2,4, Mundo de Lâminas +13,6, Espada da Vitória +14,2.

### Cada ferida tem o seu jeito (2026-11-04)

Antes, os quatro jeitos de ferir com o tempo só tiravam vida. Agora cada um faz uma coisa que é dele, tirada da obra:

| Ferida | Além do dano | Por quê |
|---|---|---|
| 血 Sangramento (cortes e queimaduras) | Quem sangra recebe só **metade da cura**. | A ferida aberta não fecha. Responde aos rivais e builds de cura. |
| 毒 Veneno | O envenenado causa **−5% de dano por dose**, até −50%. | O corpo amolece (a glicínia da Shinobu, a Ashisogi Jizo do Mayuri). Veneno vira defesa, não só dano. |
| 炎 Chama negra | Com a vida em até **2× a chama**, o que sobra **vira cinza**. | A Amaterasu não apaga até incinerar. |
| 呪 Marca | Cada técnica do amaldiçoado demora **+1 turno** a voltar. | A maldição sela (o Selo Amaldiçoado, o Gogyo Fuin). |

Os números ficam em `combate.py` (`CURA_SANGRANDO`, `FRAQUEZA_POR_DOSE`, `FRAQUEZA_MAXIMA`, `INCINERAR`, `RECARGA_AMALDICOADA`). A cura de Despertar escapa da ferida aberta: é um milagre.

**Medição (A/B no Difícil, 6000 runs por item, com e sem as regras):** as regras somam de 0 a +2 pontos a cada item, perto do ruído (±1). Nenhum item saiu da régua por causa delas. Os que estão fora já estavam antes:

| Item | Raridade | Sem as regras | Com as regras |
|---|---|---|---|
| Chuva de Sangue | Maldito | +14,6 | +15,0 |
| Enma | Maldito | +14,7 | +14,7 |
| Frasco de Glicínia | Cinza | +5,0 | +6,3 |
| Marca da Maldição | Maldito | −4,1 | −3,5 |

A recalibração das dificuldades depois das regras mexeu pouco: Brutal 5,21 → 5,05 por luta; os outros, menos de 0,03.

## Ritmo e progressão (2026-11-05)

O Enzo jogou e sentiu: as lutas eram rápidas demais, dava para matar de um golpe, e os chefes ou te destruíam ou eram obliterados. Faltava a progressão de um roguelite. A medição (piloto, Difícil, 400 runs) confirmou:

| | Antes | Depois |
|---|---|---|
| Ações suas por luta | 2,3 a 3,1 | 3,4 a 5,3 |
| Lutas decididas com 1 ou 2 ações suas | 41% a 71% | 4% a 34% |
| Maior golpe seu (mediana, % da vida do rival) | 44% a 97% | 29% a 57% |
| Chefe da luta 12 | 73% quase intacto · 19% morte | 28% quase intacto · 39% suado · 31% morte |

O que mudou:

- **Rivais com o dobro de vida** (base 12 → 24, e o crescimento por luta recalibrado). A luta dura o bastante para a recarga pesar e para as feridas que duram valerem.
- **Postura do chefe** (`POSTURA_CHEFE = 0,3`): uma ação tira no máximo 30% da vida do chefe. As feridas que duram (chama, veneno, sangramento, Marca) passam pela postura: são o jeito de derrubar um chefe. Por isso o multiplicador de vida do chefe saiu (×1,2–1,25 → ×1).
- **Segunda forma** (`SEGUNDA_FORMA = 0,5`, `FURIA_CHEFE = 1,3`): com a vida na metade, o chefe fica +30% mais forte e todas as técnicas dele voltam prontas. Uma vez por luta.
- **Treino** (`treino.py`, `data/treinos.json`): depois de cada vitória, 1 de 3: Corpo Forjado (+10 de vida máxima), Punhos de Ferro (+1 de dano em todo golpe), Passos Leves (+1 Velocidade), Olhos Abertos (+1 Percepção), Respiração Profunda (40% da vida) ou Meditar no Carma (+30 de Carma). Mexe na base do lutador: dura a run. O piloto respira abaixo de 45% da vida; senão prefere dano, depois vida.
- **Você aguenta mais:** vida 70 → 100 no Difícil (os outros modos na mesma proporção) e cura entre lutas 30% → 50%. Sem isso, a luta mais longa virava só desgaste: o rival age o dobro de vezes.

Os modos foram recalibrados (`tools/calibrar.py modos --aplicar`) e bateram o alvo. No meio da run (lutas 5 a 7) ainda há cerca de um terço de lutas curtas contra rivais comuns: o build cresce mais rápido que a vida deles ali. Os itens ainda não foram medidos de novo contra a régua com este ritmo.

A progressão **entre** runs veio logo depois: ver "O caminho, os bandos e o Legado".

## O caminho, os bandos e o Legado (2026-11-05)

O Enzo escolheu, de uma lista de formas de progressão: a roda que se abre, a Nêmesis, a Maestria, o caminho com escolha e rivais com papel — e pediu lutas com até 3 inimigos, cada um com uma função.

**Dentro da run: o caminho** (`caminho.py`, `data/caminho.json`). Antes de cada luta que não é de chefe, 1 de 3 portas. Sempre há um Rival; as outras saem dos pesos sem repetir:

- 敵 **Rival**: o duelo de sempre.
- 群 **Bando**: 2 ou 3 rivais com papel. A vida do bando é a de um rival comum ×1,35, repartida pelo peso de cada papel; cada um bate ×0,62 (dupla) ou ×0,38 (trio) vezes o do papel. Não aparece na primeira luta (você ainda bate fraco: um curandeiro ali virava uma luta sem fim).
- 強 **Elite**: ×1,35 de vida, ×1,15 de dano, +1 técnica, +1 Percepção; às vezes um bando com Comandante (reforço menor). Vencer garante uma Relíquia.
- 岐 **Encruzilhada**: sem luta. Seis encontros (Fonte, Mercador de Almas, Mestre Errante, Santuário, Cemitério, Forja), cada um com 2 ou 3 escolhas e o seu preço. O tempo passa: o próximo rival é o da luta seguinte.
- 仇 **Nêmesis**: só do capítulo 2 em diante, uma vez por run (ver o Legado).

**Os papéis** (`Lutador.papel`; a IA do papel vem antes da IA comum em `escolher_rival`): 刃 Lâmina (bate, ×1,2), 盾 Guardião (bloqueio de 20% da vida de um rival comum no aliado mais ferido), 癒 Curandeiro (cura 18% no aliado mais ferido), 呪 Xamã (Praga: veneno e fraqueza; prefere maldições) e 将 Comandante (Grito de Guerra: +2 de dano no bando, +1 por capítulo; só na elite).

**O combate com bando** (`combate.py`): `Luta.rivais`, `Luta.rival` é o seu alvo (`mirar`; quando cai, a mira passa sozinha). O lado dos rivais age em sequência, o mais rápido primeiro, cada um anunciando a própria ação (`intencao_de`). A luta 1 contra 1 ficou idêntica (mesmos sorteios: a suíte antiga passou sem mudança). Técnicas de explosão ganharam `area`: os outros rivais sofrem uma fração do dano (Arte Explosiva, Era do Gelo, Explosão Final, Chuva de Sangue, Enxame, Suor Explosivo, Estalo de Chamas, Chuva de Chutes). O piloto mira quem cai com um Golpe; senão o curandeiro, o xamã e por último o guardião.

**Entre runs: o Legado** (`legado.py`, `~/.karmabound/legado.json`; só quem joga registra):

- **A roda se abre.** Começa com os 7 animes mais ricos. Cada run deixa Memória (1 por luta vencida, 2 por capítulo fechado, 5 pela vitória, 3 pela Nêmesis vingada); a cada 6, o próximo anime entra em todas as rodas. Uma raridade que os animes abertos não têm numa roda volta inteira, como no Mundo de um anime. Quem já jogava ganha a Memória das runs da Crônica. A semente do dia joga com tudo aberto, sem Maestria nem Nêmesis.
- **Maestria.** Cada uso de uma técnica das rodas conta. Com 20 usos ela chega à mão já evoluída uma vez (★); com 60, duas (★★). As duplicatas continuam evoluindo por cima.
- **Nêmesis.** Quem deu o último golpe vira a Nêmesis, com o nome do estilo e do golpe ("Ronin · Lâmina do Inferno"). Ela volta numa run seguinte com ×1,3 de vida (+0,1 por vez que te matou), ×1,1 de dano (+0,05) e o golpe que te matou, evoluído a cada vez. Vencer: Relíquia garantida, +40 de Carma e um Despertar guardado; ela some. Perder de novo: fica mais forte.

**O balanceamento.** A primeira recalibração com o caminho baixou a vida dos rivais (Difícil 5,99 → 4,69 por luta): o duelo voltava a acabar com 2 ações suas, o problema que o Enzo tinha acabado de reclamar. A compensação foi pelo outro lado: cura entre lutas 50% → 65% e a sua vida ×1,1 em todos os modos; a vida dos rivais quase não mexeu (Difícil 5,99 → 5,66; modos em 45,7 / 35,6 / 25,7 / 9,8%). Piloto, Difícil, 400 runs:

| | Antes do caminho | Com o caminho |
|---|---|---|
| Suas ações por luta (lutas 1 a 12) | 3,4 a 5,3 | 3,8 a 7,8 |
| Lutas decididas com 1 ou 2 ações suas | 4% a 34% | 2% a 25% |
| Chefe da luta 12 (perde) | 31% | 35% |

Morte por luta, por porta (Difícil, piloto): rival ~7%, dupla ~4%, trio ~9%, elite ~6%, chefe ~20%. Um trio dura ~23 ações no total (umas 6 suas).

Os itens ainda não foram medidos de novo contra a régua com o caminho.

### Invocações em campo (2026-11-05)

Pedido do Enzo: as invocações aparecerem, e um limite. Cada invocação guarda de onde veio (`[turnos, dano, origem]`) e a tela desenha a criatura certa (sapo, cão de sombra, ave-trovão, Mahoraga, soldado de sombra, broto) ao lado do dono, atacando quando ela fere. **No máximo 3 em campo** (`MAX_INVOCACOES`); a quarta manda embora a mais antiga. Clones continuam até 5 (`MAX_CLONES`) e aparecem como cópias translúcidas. A `Acao` passou a dizer à tela o alvo, as invocações que atacaram, o respingo da área, quem foi protegido e quem foi curado.

## Fusões, Ressonância, chefes com regra própria e o resto da lista (2026-11-05)

O Enzo pediu tudo da lista de ideias, mais "técnicas desbloqueadas quando tem certos requisitos, ex.: Seis Olhos + Infinito para dar o Roxo".

- **Fusões** (`fusoes.py`, `data/fusoes.json`). Requisitos podem ser técnica equipada, Dom, Linhagem, Relíquia ou um Despertar já disparado na run (`EstadoRun.despertares_ids`); "um de" vale. Com tudo, a fusão nasce: toma o lugar da primeira técnica-requisito, ou entra como nova (sem espaço: a troca). Uma vez por run. O exemplo do Enzo: Olhos que Tudo Veem (Dom) + Vazio Infinito (Despertar) → Vazio Púrpura. Mais onze: Shuriken Espiral, Guerreiro Espectral, Lua Sem Luz, e oito técnicas novas só de fusão (Corta-Raio, Punho Colossal, Onda Carmesim, Trovão em Chamas, Repulsão Escarlate, Tempestade de Espirais, Relâmpago Ligeiro, Palmas da Verdade), medidas entre +9 e +16 na régua, todas com preço. São descobertas raras: o piloto (que agora prefere a peça de combo no empate) chega a uma em ~1% das runs.
- **Ressonância** (`ressonancia.py`, `data/ressonancias.json`): 3 técnicas equipadas do mesmo anime dão um bônus temático; 4, o nível seguinte. Naruto clones, One Piece Haki (Percepção), Jujutsu Kaisen primeiro golpe, Bleach pressão espiritual (dano), Demon Slayer respiração (cura), Dragon Ball ki que cresce, Hunter x Hunter Nen (esquiva), e um genérico para os outros.
- **Quebra de guarda** (todo rival): os seus golpes enchem um medidor (dano + 2 por golpe); a 50% da vida máxima (chefe 70%) a guarda quebra: ele perde o turno e sofre +25% até agir. O medidor esvazia 15% por turno dele. Com 40%/10% quebrava em 75% das lutas e a vitória ia de 22% a 42%; 50%/15% quebra em ~62%.
- **Chefes com mecânica própria** (`chefes.json`, seção `mecanicas`): cada assinatura traz uma regra. Duas novas: General da Roda (Mahoraga: o 2º uso da mesma técnica fere metade, o 3º nada; a roda recomeça na segunda forma) e Flor no Espelho (Aizen: metade dos anúncios são isca). As antigas ganharam: Pétalas (atravessa clones), Armadura, Repulsão (a cada 3 turnos você perde clones, invocações e bloqueio), Intangível (1 em 4 ataques atravessa), O Preço (depois da Lua Sem Fim, −50% de dano), Regenera (o sangramento corta), Contrato (o primeiro golpe que o feriria é ignorado, renova), Balança (quem tem menos vida obedece) e Carregar (o disparo cresce se não for interrompido).
- **Afixos de elite** (`caminho.json`, `afixos`): 1 por elite (2 do capítulo 3): Vampírico, Espinhos, Veloz, Invocador, Blindado, Furioso, Amaldiçoado, Gélido.
- **Aliado** (`aliados.py`, `data/aliados.json`): um companheiro por run que age no começo do seu turno e não é alvo (Faro, Pequeno Doutor, Cavaleiro de Sombra, Raposa Rubra, Borboleta de Glicínia); sobe de nível a cada vitória. Vem da encruzilhada "Lutador Ferido na Estrada" ou, às vezes, de uma elite.
- **Mapa**: as portas do próximo passo já aparecem junto com as de agora (`EstadoRun.proximas_portas`; vazio = o chefe).
- **Ascensão** (`ascensao.py`, `data/ascensao.json`): 10 níveis acumulados por dificuldade; vencer na N libera a N+1. Piloto no Difícil: A0 29% · A5 22% · A10 13% (antes da recalibração).
- **Visual e som**: cut-in de técnica (Maldita, Divina, fusão, assinatura de chefe), câmera que dá um soco no golpe forte, aviso de perigo nas bordas, barra de guarda e "崩" na quebra, selos de afixo, a mecânica do chefe sob o nome dele, o aliado em campo, as ressonâncias no seu cabeçalho e a música do chefe que intensifica na segunda forma.

Efeito medido (piloto, Difícil, antes da recalibração): guarda +8 pontos de vitória, mecânicas de chefe −4, afixos −8, aliado ~0 (aparece pouco), fusões e ressonância ~0 no piloto (ele quase não monta combo; para quem joga, valem mais). A Makima é o chefe mais duro (morte 25% na luta 12). Depois de tudo, os modos foram recalibrados: os rivais ganharam vida por luta (Difícil 5,66 → 6,61; Acessível 4,94, Equilibrado 5,70, Brutal 9,28), com a vitória em 45 / 37 / 25 / 9%.

## Leva 5: vilões, chefes fixos, modo História e mais Arcos (2026-11-07)

Pedido do Enzo: chefes fixos especiais como em The Binding of Isaac, um modo história, um modo de cada anime só com os poderes, vilões, linhagens e arcos dele, e mais Arcos. Decidido com ele: chefes sorteados por capítulo com um final fixo e um chefe secreto que se desbloqueia; uma história original e uma campanha curta por anime; o Mundo completo para 10 animes; uns 12 Arcos novos (viraram 22, porque cada anime precisa de 3 para a campanha).

**Os vilões** (`viloes.py`, `data/viloes.json`, 68). Cada anime tem 3 **tenentes** (rivais comuns com nome, a partir do capítulo deles), 2 **chefes** (capítulos 1 e 2, uma assinatura) e 1 **final** (o maior vilão da obra, duas assinaturas). O vilão leva primeiro as técnicas dele que cabem nas raridades do capítulo; o resto é sorteado como antes. Nome próprio, figura, cor e falas (`entrada`, `furia` na segunda forma, `derrota`, `vitoria`); a obra só na origem. Num mesmo run, um vilão não se repete enquanto houver outro.

**Quem aparece onde:**

| Modo | Rivais | Chefes dos capítulos 1 e 2 | Último capítulo |
|---|---|---|---|
| Clássico | tenentes das obras abertas (e os originais) | sorteados da lista do capítulo (no 2, também os finais das obras) | **o Dono da Roda**, sempre |
| Mundo de um anime | tenentes da obra | os chefes da obra | o final da obra |
| História | os da cena do capítulo | o do capítulo | o do capítulo |
| Torre sem fim | como o Clássico | como o Clássico | o Dono a cada 5 capítulos |
| Desfile de chefes | — | as listas, em ordem | o Dono na última luta |

**O Dono da Roda e o capítulo secreto.** O Dono (original) gira a própria Roda (`giro_da_roda`): no 1º turno dele e a cada 3 (2 na segunda forma), sem gastar o turno, sorteia Sangue (+3 de dano para os dois), Ferrugem (suas técnicas +1 de recarga), Dívida (ele cura 6% por turno, a não ser que sangre ou queime) ou Juízo (seus golpes nele +25%). Todo giro te dá +10 de Carma: a Roda dele alimenta o seu Despertar. Vencer o Dono **3 vezes** (`legado.DONOS_PARA_ALEM`) abre o **capítulo secreto**: depois do Dono, a Roda range e você escolhe terminar ou ir além (capítulo 4, Arco Além da Roda). Lá espera **o Reflexo**, que luta com as suas técnicas (`reflexo`: copia as equipadas quando a luta começa). Vencê-lo é o final verdadeiro.

**O modo História** (`historias.py`, `data/historias.json`, `tela_historia.py`). A campanha original, **O Torneio da Roda**, mais uma por anime (10). Cada capítulo fixa o Arco, os rivais e o chefe, e traz cenas: abertura, antes do chefe e depois. As rodas continuam sorteando poderes; o que a História fixa é o caminho. No fim do Torneio da Roda, dois finais à escolha: **Quebrar a Roda** ou **Tomar a Roda**; com o secreto aberto, o convite vem antes (e o capítulo secreto substitui a escolha). As campanhas de anime jogam com as rodas daquele anime. Fases novas da Jornada: `cena`, `convite`, `final`.

**Mecânicas dos finais** (`chefes.json` → `mecanicas`; regras em `combate.py`, constantes no topo): Sonho Eterno (Madara: a lua cai dois turnos depois, só uma proteção a reflete), Escuridão (Barba Negra: sofre +20%, e o Vórtice que fere desfaz sua forma e trava as Malditas), Rei Renascido (Meruem: volta uma vez com 40%, envenenado), Domínio (Sukuna: 4 absolutos por turno seu, e um corte final de 15%), Cinco Minutos (Freeza: em 5 turnos dele o planeta explode, 40% em você, 10% nele), Amanhecer (Muzan: cura até o 6º turno, depois o sol o queima), O Mundo Para (Dio: 2 e depois 3 ações seguidas que ninguém percebe), O Roubo (All For One: toma a sua técnica mais forte, até 2), A Marcha (Eren: dano absoluto crescente a cada turno dele). Com duas assinaturas, a mecânica nova do final vence a antiga (`run.MECANICAS_ANTIGAS`). Os textos das mecânicas antigas ficaram genéricos (Ilusão, Contrato, Carregar, Adaptação), porque agora servem a vários vilões.

**Os Arcos** (22 novos, 34 na roda e 4 só da História). Regras novas: `dano_rivais_mult`, `cura_por_vitoria`, `portas` (multiplica o peso de cada porta), `sangria_todos`, `sutileza_rivais`, `velocidade_rivais`, `guarda_mult`, `carma_por_vitoria`, `treino_extra`, `opcoes_tecnica` (4 técnicas na escolha; tecla 4). O cenário dos Arcos novos vem dos dados (`arena`: marco, céu, chão, partículas, lua), desenhado por `arenas._por_dado` com 14 marcos.

**Conteúdo novo para os Mundos:** técnicas (Dragon Ball, Demon Slayer, JoJo, My Hero Academia, Attack on Titan e Bleach chegaram a 10 ou mais), 8 Linhagens.

**Dois consertos que os vilões revelaram:**
- O **enfraquecer** não tinha teto. Dois lutadores que se enfraqueciam de volta chegavam a 0 de dano e a luta não acabava. Agora o teto é −3 por luta (`ENFRAQUECER_MAX`): o Golpe sempre causa pelo menos 1.
- A **luta longa** (`LUTA_LONGA` = 60 ações): daí em diante ninguém cura, e os dois se desgastam cada vez mais. Uma regeneração contra golpes fracos não prende mais ninguém.

**Balanceamento.** Os vilões (que preferem as técnicas fortes da obra) e o Dono deixaram o jogo mais duro: o calibrador baixou a vida dos rivais por luta (Acessível 4,94 → 4,36, Equilibrado 5,7 → 4,99, Difícil 6,61 → 5,71, Brutal 9,28 → 8,14), com a vitória em 44,7 / 34,8 / 25,1 / 10,5%. As técnicas e Linhagens novas ainda não passaram pela régua (`tools/calibrar.py itens`).

**Telas:** a entrada do vilão mostra kanji, nome, quem ele é e a fala; a fala da segunda forma aparece no alto; o banner do fim traz a última fala. Figuras com a cor do vilão. O título tem o modo História com a campanha (← →, 完 nas terminadas). O Grimório ganhou a aba **Vilões** (o bestiário). O Legado guarda as vitórias sobre o Dono, os finais vistos, os vilões vencidos e as campanhas terminadas.

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
- Revisitar o que ficou fora da régua (tabela acima).
- **Conteúdo das rodas:** nomes e textos atuais são rascunho.
- **Progressão entre runs:** feita (o Legado). Em aberto: ascensão (Juramentos permanentes para quem já vence).
- **Estilo de arte** definitivo.
