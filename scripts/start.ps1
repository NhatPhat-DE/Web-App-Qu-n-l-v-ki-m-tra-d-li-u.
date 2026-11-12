$ErrorActionPreference = 'Stop'
$projectRoot = Split-Path -Parent $PSScriptRoot
Set-Location -LiteralPath $projectRoot
$runtimeDir = Join-Path $projectRoot '.runtime'
New-Item -ItemType Directory -Path $runtimeDir -Force | Out-Null

function Test-Url([string]$Url) {
    try {
        return (Invoke-WebRequest -UseBasicParsing -Uri $Url -TimeoutSec 3).StatusCode -eq 200
    } catch { return $false }
}

function Wait-Url([string]$Url) {
    for ($attempt = 0; $attempt -lt 40; $attempt++) {
        if (Test-Url $Url) { return }
        Start-Sleep -Seconds 1
    }
    throw "Service did not become ready: $Url. See logs in .runtime."
}

function Test-DockerReady {
    # Windows PowerShell 5.1 turns native stderr into an ErrorRecord. With
    # Stop enabled globally, an unavailable engine used to abort this script
    # before the branch that starts Docker Desktop could execute.
    $ErrorActionPreference = 'Continue'
    & $docker info *> $null
    return $LASTEXITCODE -eq 0
}

try {
    Write-Host 'Starting DataGuard SME...'
    $docker = (Get-Command docker.exe -ErrorAction Stop).Source
    $python = Join-Path $projectRoot 'backend\.venv\Scripts\python.exe'
    $vite = Join-Path $projectRoot 'frontend\node_modules\vite\bin\vite.js'
    $node = (Get-Command node.exe -ErrorAction Stop).Source
    if (!(Test-Path -LiteralPath $python) -or !(Test-Path -LiteralPath $vite)) {
        throw 'Dependencies are missing. Install backend requirements and run npm.cmd ci in frontend first.'
    }

    if (!(Test-DockerReady)) {
        $dockerDesktop = Join-Path $env:ProgramFiles 'Docker\Docker\Docker Desktop.exe'
        if (!(Test-Path -LiteralPath $dockerDesktop)) {
            throw 'Docker Desktop is not installed at the expected path. Install/start Docker Desktop, then run start.cmd again.'
        }
        if (!(Get-Process -Name 'Docker Desktop' -ErrorAction SilentlyContinue)) {
            Start-Process -FilePath $dockerDesktop -WindowStyle Hidden
        }
        Write-Host 'Waiting for Docker Desktop...'
        $dockerReady = $false
        for ($attempt = 0; $attempt -lt 90; $attempt++) {
            Start-Sleep -Seconds 2
            if (Test-DockerReady) { $dockerReady = $true; break }
        }
        if (!$dockerReady) { throw 'Docker Desktop did not become ready. Open Docker Desktop and try again.' }
    }

    & $docker compose --env-file backend/.env up -d --wait --wait-timeout 120
    if ($LASTEXITCODE -ne 0) { throw 'Could not start PostgreSQL.' }

    if (!(Test-Url 'http://127.0.0.1:8000/api/health')) {
        Push-Location (Join-Path $projectRoot 'backend')
        try {
            & $python -m alembic upgrade head
            if ($LASTEXITCODE -ne 0) { throw 'Database migration failed.' }
        } finally { Pop-Location }
        Start-Process -FilePath $python -ArgumentList '-m uvicorn app.main:app --host 127.0.0.1 --port 8000' -WorkingDirectory (Join-Path $projectRoot 'backend') -WindowStyle Hidden -RedirectStandardOutput (Join-Path $runtimeDir 'backend.stdout.log') -RedirectStandardError (Join-Path $runtimeDir 'backend.stderr.log') | Out-Null
    }
    Wait-Url 'http://127.0.0.1:8000/api/health/db'

    if (!(Test-Url 'http://127.0.0.1:5173/')) {
        Start-Process -FilePath $node -ArgumentList ('"' + $vite + '"') -WorkingDirectory (Join-Path $projectRoot 'frontend') -WindowStyle Hidden -RedirectStandardOutput (Join-Path $runtimeDir 'frontend.stdout.log') -RedirectStandardError (Join-Path $runtimeDir 'frontend.stderr.log') | Out-Null
    }
    Wait-Url 'http://127.0.0.1:5173/'
    Wait-Url 'http://127.0.0.1:5173/api/health/db'
    Start-Process 'http://127.0.0.1:5173/'
    Write-Host 'Ready: http://127.0.0.1:5173/' -ForegroundColor Green
} catch {
    Write-Host $_.Exception.Message -ForegroundColor Red
    exit 1
}
