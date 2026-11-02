@echo off
:: build.bat - gera o executavel em dist\Karmabound\Karmabound.exe
:: Precisa: pip install pyinstaller (e a OuroborosEngine instalada, como para jogar)
python tools\gerar_icone.py
python -m PyInstaller --noconfirm karmabound.spec
if %errorlevel% == 0 (
    echo.
    echo  Build OK ^>^> dist\Karmabound\Karmabound.exe
    echo.
) else (
    echo.
    echo  ERRO no build.
    echo.
)
