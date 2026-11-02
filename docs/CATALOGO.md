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
| 体 | Corpo Resistente | Cinza | Mais vida máxima. |
| 速 | Reflexo Treinado | Cinza | Chance de esquivar. |
| 沸 | Sangue Fervente | Sangue | Causa mais dano quanto mais ferido estiver. |
| 影 | Sombra Leal | Sangue | Sua sombra repete metade do seu golpe. |
| 眼 | Olho Roubado | Maldito | Copia a última técnica do rival; fica cego no turno seguinte. |
| 灰 | Pele de Cinzas | Maldito | Ignora o primeiro golpe de cada luta; não pode ser curado. |
| 域 | Santuário | Divino | Fecha a arena por 3 turnos: seus golpes não erram. Depois, pula um turno. |
| 刻 | Instante Suspenso | Divino | Ganha um turno extra ao custo de Carma. |

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
| 呪 | Marca da Maldição | Maldito | maldita | marca 3 | 4 | 3 |  |
| 契 | Contrato | Divino | maldita | dano 30, custo de vida 10 | 99 | 2 | sim |
| 裁 | Julgamento | Divino | maldita | dano × Carma 0.4 | 4 | 3 | sim |

## 章 Arco (gira e aceita)

| | Nome | Raridade | Texto |
|---|---|---|---|
| 山 | Treino na Montanha | Cinza | Cura entre lutas. |
| 闘 | Torneio Regular | Cinza | Sem regra especial. |
| 月 | Lua de Sangue | Sangue | Todos causam mais dano. |
| 侵 | Invasão | Sangue | Lutas extras, mais giros de Relíquia. |
| 禍 | Maldição Coletiva | Maldito | O Carma enche em dobro, para você e para os rivais. |
| 審 | Arco do Juízo | Divino | O chefe do capítulo desperta junto com você. |

## 宝 Relíquias (gira e aceita)

| | Nome | Raridade | Texto |
|---|---|---|---|
| 布 | Bandagem | Cinza | Cura um pouco no início de cada luta. |
| 符 | Amuleto Rachado | Cinza | Uma vez por run, evita um golpe fatal. |
| 骨 | Rosário de Ossos | Sangue | Cada derrota de rival dá um pouco de Carma. |
| 鬼 | Máscara de Oni | Sangue | Mais dano, menos defesa. |
| 封 | Coração Selado | Maldito | Guarda um Despertar para usar quando quiser. |
| 神 | Fragmento do Deus Cego | Divino | Duplicatas viram poder em vez de fragmentos. |

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
| Acessível | 45% | 12 +2 | ×1.2 | 80 |
| Equilibrado | 36% | 12 +2 | ×1.2 | 76 |
| Difícil (padrão) | 25% | 12 +2 | ×1.25 | 72 |
| Brutal | 10% | 12 +2.5 | ×1.25 | 70 |
