# Instalando e rodando Karmabound

Dá para jogar de dois jeitos: pelo **executável do Windows** (gerado a partir do código, sem precisar de Python para jogar) ou direto do código, com Python.

## Executável (Windows)

Com o ambiente de desenvolvimento pronto (passos abaixo) e `pip install pyinstaller`:

```bat
build.bat
```

Sai `dist\Karmabound\Karmabound.exe`, com a pasta `_internal` ao lado — leve a pasta `Karmabound` inteira. É `onedir` de propósito: um `.exe` único se extrai no `%TEMP%` e o Windows 11 (Controle Inteligente de Aplicativos) barra isso num executável sem assinatura. Sem assinatura de código, o Windows ainda pode avisar na primeira vez ("O Windows protegeu o computador" → Mais informações → Executar assim mesmo).

`Karmabound.exe --headless` abre o jogo, desenha um quadro e sai: serve para testar um build sem abrir janela.

O progresso do Grimório fica em `%USERPROFILE%\.karmabound\grimorio.json`.

## Do código

## Requisitos

- Windows 10/11, macOS ou Linux.
- **Python 3.11 ou mais novo** ([python.org](https://www.python.org/downloads/) — no Windows, marque "Add python.exe to PATH" na instalação).
- A **Ouroboros Engine** com o marco **M16** (primitivas de UI e fontes customizadas). Versões anteriores da engine abrem com erro, porque a tela da roleta usa `draw_ui_circle`, `draw_ui_arc` e `load_font`.

## Passo a passo

### 1. Baixe os dois repositórios lado a lado

```
pasta-qualquer/
├── OuroborosEngine/
└── Karmabound/
```

```bash
git clone https://github.com/EzioMilanoX/OuroborosEngine.git
git clone https://github.com/EzioMilanoX/Karmabound.git
```

### 2. Instale as dependências

Dentro de `Karmabound/`:

```bash
pip install -r requirements.txt
```

Isso instala o `pygame-ce` e a engine **em modo editável** a partir de `../OuroborosEngine` (a engine traz `numpy` e `librosa` junto). Se preferir não clonar a engine:

```bash
pip install pygame-ce "ouroboros-engine @ git+https://github.com/EzioMilanoX/OuroborosEngine.git"
```

### 3. Rode

```bash
python -m karmabound
```

No Windows, duplo clique em **`run.bat`** faz o mesmo. Abre o título; escolha o modo e jogue uma run inteira. `python -m karmabound --roleta` abre só a roleta, como caixa de areia.

## Para desenvolver

```bash
pip install pytest ruff
pytest           # testes headless; não abre janela
ruff check .     # lint
```

As ferramentas de calibração e documentação estão descritas no [README](README.md#ferramentas-e-testes).

## Problemas comuns

- **`ModuleNotFoundError: No module named 'ouroboros'`** — a engine não foi instalada. Repita o passo 2 a partir da pasta `Karmabound/`, com a engine clonada ao lado.
- **`AttributeError: ... has no attribute 'draw_ui_circle'` ou `'load_font'`** — a engine instalada é anterior ao M16. Atualize o clone da engine (`git pull` dentro de `OuroborosEngine/`) e reinstale.
- **Kanji aparecendo como quadrados** — a fonte `assets/fonts/YujiSyuku-Regular.ttf` não foi encontrada. Confira se o clone veio completo (o arquivo tem ~8 MB).
- **`librosa` falhando ao instalar** numa versão muito nova do Python — instale a engine com `pip install -e ../OuroborosEngine --no-deps` e depois `pip install numpy pygame-ce`. O Karmabound não usa a análise de áudio da engine.
