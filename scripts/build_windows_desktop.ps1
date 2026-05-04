$ErrorActionPreference = "Stop"

$repoRoot = Resolve-Path (Join-Path $PSScriptRoot "..")
Set-Location $repoRoot

function Invoke-Native {
    param(
        [Parameter(Mandatory = $true)]
        [string]$FilePath,
        [Parameter(ValueFromRemainingArguments = $true)]
        [string[]]$Arguments
    )

    & $FilePath @Arguments
    if ($LASTEXITCODE -ne 0) {
        throw "Command failed with exit code ${LASTEXITCODE}: $FilePath $Arguments"
    }
}

$python = "py"
$pythonArgs = @("-3.11")
$venvPath = Join-Path $repoRoot ".venv-desktop-build"
$venvPython = Join-Path $venvPath "Scripts\python.exe"

if ((Test-Path $venvPython) -and -not (Test-Path (Join-Path $venvPath "Scripts\pip.exe"))) {
    Remove-Item $venvPath -Recurse -Force
}

if (-not (Test-Path $venvPython)) {
    Invoke-Native $python @pythonArgs -m venv $venvPath
}

Invoke-Native $venvPython -m ensurepip --upgrade
Invoke-Native $venvPython -m pip install --upgrade pip
Invoke-Native $venvPython -m pip install -r requirements-desktop-build.txt

if (Test-Path "build") {
    Remove-Item "build" -Recurse -Force
}

if (Test-Path "dist\OpenPartsLibrary") {
    Remove-Item "dist\OpenPartsLibrary" -Recurse -Force
}

Invoke-Native $venvPython -m PyInstaller OpenPartsLibrary-Windows.spec --noconfirm --clean

$zipPath = Join-Path $repoRoot "dist\OpenPartsLibrary-Windows-10-11.zip"
if (Test-Path $zipPath) {
    Remove-Item $zipPath -Force
}

Compress-Archive -Path "dist\OpenPartsLibrary" -DestinationPath $zipPath -Force

Write-Host "Created $zipPath"
