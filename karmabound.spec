# -*- mode: python ; coding: utf-8 -*-
"""
Receita do executável (PyInstaller): build.bat, ou  python -m PyInstaller karmabound.spec

Sai em dist/Karmabound/ (Karmabound.exe e a pasta _internal ao lado).

O que precisa entrar, além do código:

* `karmabound/data/` — rodas, balanceamento, votos e controles. Tudo que é número
  é dado, e o PyInstaller só leva `.py`. Mantém o caminho `karmabound/data`, porque
  `rodas.DADOS` é relativo ao próprio módulo.
* `assets/` — a fonte de pincel, os sons, as músicas e o ícone. Fica um nível acima
  do pacote, como no repositório (`game.FONTES`, `som.ASSETS`).
* a OuroborosEngine — instalada em modo editável (repositório irmão). O
  site-packages só tem um ponteiro, e o PyInstaller não o segue sozinho: sem isto
  o executável abre e morre com `No module named 'ouroboros'`, em silêncio.

`onedir`, não `onefile`: o onefile se extrai no %TEMP% e roda de lá, e o Controle
Inteligente de Aplicativos do Windows 11 barra isso num executável sem assinatura
(o mesmo achado do Penumbra).
"""
from pathlib import Path

import ouroboros
from PyInstaller.utils.hooks import collect_submodules

SPEC_DIR = Path(SPECPATH).resolve()
ENGINE_ROOT = Path(ouroboros.__file__).resolve().parent.parent

datas = [
    (str(SPEC_DIR / "karmabound" / "data"), "karmabound/data"),
    (str(SPEC_DIR / "assets"), "assets"),
]
icone = SPEC_DIR / "assets" / "karmabound.ico"

analysis = Analysis(
    [str(SPEC_DIR / "karmabound" / "__main__.py")],
    pathex=[str(SPEC_DIR), str(ENGINE_ROOT)],
    binaries=[],
    datas=datas,
    # o pacote raiz sozinho não traz ouroboros.bootstrap.* nem os adaptadores,
    # que a composição importa por nome; o módulo de autoria de ritmo puxa scipy
    hiddenimports=[
        n for n in collect_submodules("ouroboros") if not n.startswith("ouroboros.rhythm.offline")
    ]
    + collect_submodules("karmabound"),
    hookspath=[],
    runtime_hooks=[],
    excludes=[
        "tkinter", "unittest", "pytest", "numpy.testing", "pygame.tests",
        "scipy", "matplotlib", "PIL", "ouroboros.rhythm.offline",
    ],
    noarchive=False,
)
pyz = PYZ(analysis.pure)

exe = EXE(
    pyz,
    analysis.scripts,
    [],
    exclude_binaries=True,  # onedir: as bibliotecas ficam ao lado, nada se extrai no %TEMP%
    name="Karmabound",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    runtime_tmpdir=None,
    console=False,  # o jogo é uma janela; um terminal preto atrás dela não
    icon=str(icone) if icone.is_file() else None,
)

collected = COLLECT(
    exe,
    analysis.binaries,
    analysis.datas,
    strip=False,
    upx=False,
    name="Karmabound",
)
