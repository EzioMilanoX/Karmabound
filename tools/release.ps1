# Lança uma versão do Karmabound: confere, testa, sobe a versão, fecha o CHANGELOG,
# cria a tag e sobe. O GitHub Actions (.github/workflows/release.yml) gera o
# executável e cria o Release como RASCUNHO: você revisa e publica no GitHub.
#
#   powershell -File tools/release.ps1 -Versao 0.4.0 -Titulo "Vilões, o Dono da Roda e o modo História"
#   -SemTestes   pula ruff e pytest (o Actions roda de novo de qualquer jeito)
#   -Simular     mostra o que faria, sem mudar nada
param(
    [Parameter(Mandatory = $true)][string]$Versao,
    [Parameter(Mandatory = $true)][string]$Titulo,
    [switch]$SemTestes,
    [switch]$Simular
)

$ErrorActionPreference = "Stop"
$raiz = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
$engine = Join-Path (Split-Path -Parent $raiz) "OuroborosEngine"
$utf8 = New-Object System.Text.UTF8Encoding($false)  # sem BOM
$tag = "v$Versao"
$contaPessoal, $contaTrabalho = "EzioMilanoX", "EnzoLai01"

function Falhar($msg) { Write-Host "ERRO: $msg" -ForegroundColor Red; exit 1 }
function Passo($msg) { Write-Host "-> $msg" -ForegroundColor Cyan }
function Ler($caminho) { [IO.File]::ReadAllText($caminho, $utf8) }
function Gravar($caminho, $texto) { [IO.File]::WriteAllText($caminho, $texto, $utf8) }
# (não chame de "Git": o PowerShell não diferencia maiúsculas, e a função chamaria a si mesma)
function RodarGit { & git.exe -C $raiz @args; if ($LASTEXITCODE -ne 0) { Falhar "git $args" } }

if ($Versao -notmatch '^\d+\.\d+\.\d+$') { Falhar "versão no formato 0.4.0" }

# ---------------------------------------------------------------- conferências
Passo "Conferindo o repositório"
if ((git -C $raiz branch --show-current) -ne "main") { Falhar "o release sai da main: troque para ela" }
if (git -C $raiz status --porcelain) { Falhar "há mudanças sem commit; commite ou guarde antes" }
RodarGit fetch -q origin
if ((git -C $raiz rev-parse HEAD) -ne (git -C $raiz rev-parse origin/main)) {
    Falhar "a main local e a do GitHub estão diferentes (git pull / git push antes)"
}
if (git -C $raiz tag --list $tag) { Falhar "a tag $tag já existe" }
if ((git -C $raiz config user.email) -ne "enzolai01@gmail.com") { Falhar "identidade git do repositório não é a pessoal" }

$changelog = Join-Path $raiz "CHANGELOG.md"
$textoLog = Ler $changelog
$m = [regex]::Match($textoLog, '(?ms)^## Ainda sem versão\s*\r?\n(.*?)(?=^## |\z)')
if (-not $m.Success -or -not $m.Groups[1].Value.Trim()) { Falhar "escreva as notas em '## Ainda sem versão' no CHANGELOG.md" }

# a engine: o Actions baixa exatamente este commit, que precisa estar no GitHub
Passo "Conferindo a OuroborosEngine"
& git -C $engine fetch -q origin
$refEngine = (& git -C $engine rev-parse HEAD).Trim()
if (& git -C $engine status --porcelain) { Falhar "a OuroborosEngine tem mudanças sem commit" }
if (-not (& git -C $engine branch -r --contains $refEngine)) { Falhar "o commit $refEngine da engine não está no GitHub (push nela antes)" }

if (-not $SemTestes) {
    Passo "ruff e pytest"
    Push-Location $raiz
    try {
        $env:OPENBLAS_NUM_THREADS = "1"
        python -m ruff check .; if ($LASTEXITCODE -ne 0) { Falhar "ruff" }
        python -m pytest -q -p no:cacheprovider; if ($LASTEXITCODE -ne 0) { Falhar "pytest" }
    } finally { Pop-Location }
}

$hoje = Get-Date -Format "yyyy-MM-dd"
if ($Simular) {
    Write-Host "Simulação: $tag — $Titulo ($hoje), engine $refEngine" -ForegroundColor Yellow
    exit 0
}

# ---------------------------------------------------------------- a versão
Passo "Subindo a versão para $Versao"
$pyproject = Join-Path $raiz "pyproject.toml"
Gravar $pyproject ([regex]::Replace((Ler $pyproject), '(?m)^version = "[^"]+"', "version = `"$Versao`""))
$init = Join-Path $raiz "karmabound\__init__.py"
Gravar $init ([regex]::Replace((Ler $init), '__version__ = "[^"]+"', "__version__ = `"$Versao`""))
$novaSecao = "## Ainda sem versão`n`n## $tag — $Titulo ($hoje)`n"
Gravar $changelog ([regex]::Replace($textoLog, '(?m)^## Ainda sem versão\s*\r?\n', $novaSecao, 1))
Gravar (Join-Path $raiz "engine.ref") "$refEngine`n"

RodarGit add pyproject.toml karmabound/__init__.py CHANGELOG.md engine.ref
RodarGit commit -q -m "$tag — $Titulo"
RodarGit tag -a $tag -m "$tag — $Titulo"

# ---------------------------------------------------------------- subir
Passo "Subindo (como $contaPessoal)"
& gh auth switch -u $contaPessoal | Out-Null
try {
    RodarGit push -q origin main --follow-tags
} finally {
    & gh auth switch -u $contaTrabalho | Out-Null
}

Write-Host ""
Write-Host "Pronto: $tag subiu. O Actions gera o executável e cria o Release como rascunho:" -ForegroundColor Green
Write-Host "  https://github.com/EzioMilanoX/Karmabound/actions"
Write-Host "  https://github.com/EzioMilanoX/Karmabound/releases  (revise e aperte Publish)"
