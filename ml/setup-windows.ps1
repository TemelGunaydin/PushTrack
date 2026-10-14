#Requires -Version 5.1
[CmdletBinding()]
param(
    [string]$Workspace = 'D:\PushTrackML',
    [switch]$DataPreparation,
    [switch]$Training
)

$ErrorActionPreference = 'Stop'
if ($DataPreparation -and $Training) {
    throw 'Choose DataPreparation or Training, not both.'
}

function Resolve-Executable([string]$Name) {
    $command = Get-Command $Name -CommandType Application -ErrorAction Stop | Select-Object -First 1
    $entry = Get-Item -LiteralPath $command.Source -Force
    # WinGet's symbolic link may not execute in a Windows OpenSSH session.
    if ($entry.LinkType -eq 'SymbolicLink') {
        return @($entry.Target)[0]
    }
    return $command.Source
}

function Invoke-Checked([string]$Executable, [string[]]$Arguments) {
    & $Executable @Arguments
    if ($LASTEXITCODE -ne 0) {
        throw "$Executable exited with code $LASTEXITCODE."
    }
}

$python = Resolve-Executable 'python.exe'
$uv = Resolve-Executable 'uv.exe'
$version = & $python -c "import sys, struct; print('%s.%s:%s' % (sys.version_info.major, sys.version_info.minor, struct.calcsize('P') * 8))"
if ($LASTEXITCODE -ne 0 -or $version.Trim() -ne '3.12:64') {
    throw 'An existing 64-bit Python 3.12 installation is required; Python will not be downloaded.'
}

$Workspace = [IO.Path]::GetFullPath($Workspace)
$environmentName = '.venv'
$requirementsName = 'requirements-windows'
$index = 'https://download.pytorch.org/whl/cu130'
$backendArgs = @()
if ($DataPreparation) {
    $environmentName = '.venv-data'
    $requirementsName = 'requirements-data'
    $index = 'https://pypi.org/simple'
} elseif ($Training) {
    $environmentName = '.venv-train'
    $requirementsName = 'requirements-train'
    $index = 'https://pypi.org/simple'
    $backendArgs = @('--torch-backend', 'cu130')
}
$venv = Join-Path $Workspace $environmentName
$venvPython = Join-Path $venv 'Scripts\python.exe'
$cache = Join-Path $Workspace '.cache\uv'
$lock = Join-Path $PSScriptRoot ($requirementsName + '.lock')
$inputRequirements = Join-Path $PSScriptRoot ($requirementsName + '.in')
$oldCache = $env:UV_CACHE_DIR
$oldDownloads = $env:UV_PYTHON_DOWNLOADS
$oldTemp = $env:TEMP
$oldTmp = $env:TMP

try {
    New-Item -ItemType Directory -Force -Path $Workspace, $cache, (Join-Path $Workspace '.tmp') | Out-Null
    # Process-local settings only: do not edit PATH, profiles, or registry values.
    $env:UV_CACHE_DIR = $cache
    $env:UV_PYTHON_DOWNLOADS = 'never'
    $env:TEMP = Join-Path $Workspace '.tmp'
    $env:TMP = $env:TEMP

    if (-not (Test-Path -LiteralPath $venvPython)) {
        if (Test-Path -LiteralPath $venv) {
            throw "An incomplete environment already exists at $venv; inspect it before retrying."
        }
        Invoke-Checked $uv @('venv', '--python', $python, $venv)
    }
    $venvVersion = & $venvPython -c "import sys; print('%s.%s' % sys.version_info[:2])"
    if ($LASTEXITCODE -ne 0 -or $venvVersion.Trim() -ne '3.12') {
        throw 'The existing workspace environment is not Python 3.12; it was not replaced.'
    }

    # Resolve only on the first setup. Subsequent runs consume the committed lock.
    if (-not (Test-Path -LiteralPath $lock)) {
        Invoke-Checked $uv (@('pip', 'compile', $inputRequirements, '--python', $venvPython,
            '--generate-hashes', '--no-build', '--output-file', $lock) + $backendArgs)
    }
    Invoke-Checked $uv (@('pip', 'sync', $lock, '--python', $venvPython,
        '--index-url', $index, '--require-hashes', '--no-build') + $backendArgs)

    Write-Output "Environment ready: $venvPython"
    Write-Output 'No model, dataset, CUDA toolkit, or system Python packages were installed.'
} finally {
    $env:UV_CACHE_DIR = $oldCache
    $env:UV_PYTHON_DOWNLOADS = $oldDownloads
    $env:TEMP = $oldTemp
    $env:TMP = $oldTmp
}
