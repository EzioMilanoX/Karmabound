# Catálogo do Karmabound

> Gerado por `python tools/gerar_catalogo.py` a partir de `karmabound/data/`. Não edite aqui: edite os JSON e gere de novo.

## Raridades

| Raridade | Chance publicada | Carma por giro |
|---|---|---|
| Cinza | 60% | +8 |
| Sangue | 28% | +4 |
| Maldito | 10% | +0 |
| Divino | 2% | -40 |

## 命 Destino (gira e aceita)

| | Nome | Raridade | Texto |
|---|---|---|---|
| 体 | Corpo Resistente | Cinza | +15 de vida máxima. |
| 速 | Reflexo Treinado | Cinza | 15% de chance de esquivar um golpe inteiro. |
| 沸 | Sangue Fervente | Sangue | Até +6 de dano, proporcional à vida que você já perdeu. |
| 影 | Sombra Leal | Sangue | Sua sombra repete cada golpe seu com 50% do dano. |
| 眼 | Olho Roubado | Maldito | Técnica: usa a última técnica do rival como se fosse sua. Preço: Percepção 0 até o seu próximo turno. |
| 灰 | Pele de Cinzas | Maldito | O primeiro golpe de cada luta não te fere. Preço: você nunca é curado. |
| 域 | Santuário | Divino | Técnica, uma vez por luta: por 3 turnos seus golpes não são percebidos e causam +50%. Preço: depois você perde um turno. |
| 刻 | Instante Suspenso | Divino | Técnica: um turno extra. Preço: 25 de Carma. |

## 技 Técnicas (gira 3, escolhe 1)

| | Técnica | Raridade | Tipo | Efeito | Recarga | Sutileza | Perigosa |
|---|---|---|---|---|---|---|---|
| 拳 | Golpe Direto | Cinza | ataque | dano 7 | 1 | 2 |  |
| 守 | Guarda Alta | Cinza | defesa | bloqueio 8 | 2 | 0 |  |
| 突 | Investida | Cinza | ataque | dano 11 | 2 | 1 | sim |
| 十 | Corte em Cruz | Sangue | ataque | dano 5, golpes 2 | 2 | 3 |  |
| 返 | Contra-ataque | Sangue | defesa | bloqueio 5, revide 6 | 3 | 0 |  |
| 刃 | Lâmina de Sangue | Sangue | ataque | dano 16, custo de vida 4 | 3 | 3 | sim |
| 誓 | Juramento | Maldito |  |  | 0 | 0 |  |
| 呪 | Marca da Maldição | Maldito | maldita | dano 10, marca 3, você sofre por turno 1 | 2 | 3 |  |
| 契 | Contrato | Divino | maldita | dano 40, destrói outra técnica sua | 99 | 2 | sim |
| 裁 | Julgamento | Divino | maldita | dano × Carma 1.3, consome o Carma | 4 | 3 | sim |

## 章 Arco (gira e aceita)

| | Nome | Raridade | Texto |
|---|---|---|---|
| 山 | Treino na Montanha | Cinza | Cura entre lutas sobe de 30% para 50%. |
| 闘 | Torneio Regular | Cinza | Sem regra especial. |
| 月 | Lua de Sangue | Sangue | Todos, você e os rivais, causam +3 de dano. |
| 侵 | Invasão | Sangue | +1 luta neste capítulo, e um giro de Relíquia garantido depois de cada luta. |
| 禍 | Maldição Coletiva | Maldito | Seu Carma enche em dobro, e os rivais têm +20% de vida. |
| 審 | Arco do Juízo | Divino | O chefe tem +50% de vida e dano; derrotá-lo enche o seu Carma ao máximo. |

## 宝 Relíquias (gira e aceita)

| | Nome | Raridade | Texto |
|---|---|---|---|
| 布 | Bandagem | Cinza | Cura 4 no início de cada luta. |
| 符 | Amuleto Rachado | Cinza | Uma vez por run, um golpe fatal te deixa com 1 de vida. |
| 骨 | Rosário de Ossos | Sangue | Cada rival derrotado dá +10 de Carma. |
| 鬼 | Máscara de Oni | Sangue | +3 de dano em todo golpe. Preço: seus bloqueios valem metade. |
| 封 | Coração Selado | Maldito | Ao transbordar, o Carma vira um Despertar guardado e zera. Você libera o Despertar no giro que quiser. |
| 神 | Fragmento do Deus Cego | Divino | Técnicas repetidas evoluem na hora, em vez de virar fragmento. |

## 誓 Votos vinculativos (Juramento)

Até 3 votos ativos; quebrar um voto libera o espaço. O valor de cada restrição é medido contra o seu build na hora, por simulação.

**Pontos** = S × (1 + S ÷ 2) × duração × categoria. S é o sacrifício (lutas vencidas a menos no resto da run), com **retorno decrescente por restrição**: cada uma credita no máximo 1.5 luta. Para ir além, junte restrições diferentes.

**Preço de um ganho** = benefício medido do 1º nível × número do nível (o 2º nível custa o dobro do 1º) × câmbio 4. Exclusivos custam ×1.25. O câmbio escala o poder total dos votos.

| Duração | Multiplicador |
|---|---|
| Momentâneo (esta luta) | ×1 |
| Até o fim do capítulo | ×1.3 |
| Permanente (resto da run) | ×1.75 |

| Categoria da restrição | Multiplicador |
|---|---|
| simples | ×1 |
| conduta | ×1.15 |
| revelacao | ×1.15 |
| risco | ×1.4 |

**Quebrar um voto:** perde os ganhos dele, perde 50% da vida atual, o Carma zera, e jura um voto de quebra. Quebrar o voto de quebra encerra a run.

### Restrições

| | Nome | Categoria | Efeito |
|---|---|---|---|
| 身 | Corpo Ofertado | simples | Vida máxima −25%. |
| 重 | Passos Pesados | simples | Velocidade −1. |
| 眠 | Sem Descanso | simples | Sem cura entre lutas. |
| 盾 | Sem Guarda | conduta | Nunca usar técnicas de defesa. |
| 縛 | Mãos Atadas | conduta | Nunca usar o Golpe básico; sem técnica pronta, você hesita e perde o turno. |
| 晒 | Voto Exposto | revelacao | O rival tem +2 de Percepção contra você. |
| 限 | Prazo | risco | Luta com mais de 10 turnos é derrota. |
| 刃 | Fio da Navalha | risco | Cair abaixo de 20% da vida máxima é morte. |

### Ganhos

| | Nome | Categoria | Efeito | Níveis |
|---|---|---|---|---|
| 力 | Força | simples | +2 de dano em todo golpe. | 5 |
| 活 | Vigor | simples | +15 de vida máxima. | 5 |
| 察 | Olhar Aguçado | simples | +1 de Percepção. | 5 |
| 軽 | Passo Leve | simples | +1 de Velocidade. | 5 |
| 隠 | Golpe Oculto | especial | Seus golpes perigosos não podem ser percebidos. | 1 |
| 棘 | Pele de Espinhos | especial | Revide 3 que se rearma a cada turno seu. | 1 |
| 餓 | Carma Faminto | especial | O Carma enche 50% mais rápido. | 1 |
| 先 | Primeiro Sangue | especial | Você sempre começa a luta, e a surpresa nunca é percebida. | 1 |
| 蘇 | Segunda Vida | exclusivo | Uma vez na run, ao cair, volta com 30% da vida. | 1 |
| 斬 | Carrasco | exclusivo | +50% de dano contra chefes. | 1 |
| 冷 | Sangue Frio | exclusivo | Você sempre reage ao ataque surpresa. | 1 |

## Modos de dificuldade

| Modo | Vitória alvo (piloto) | Rival +vida/luta | Chefe | Sua vida |
|---|---|---|---|---|
| Acessível | 45% | 12 +4.4 | ×1.2 | 80 |
| Equilibrado | 36% | 12 +4.65 | ×1.2 | 76 |
| Difícil (padrão) | 25% | 12 +4.7 | ×1.25 | 70 |
| Brutal | 10% | 12 +5.8 | ×1.25 | 68 |
