$ErrorActionPreference = 'Stop'

$Root = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path
$Backend = Join-Path $Root 'backend'
$Python = Join-Path $Backend 'venv\Scripts\python.exe'

if (-not (Test-Path -LiteralPath $Python)) {
    throw 'backend/venv Python was not found. Install dependencies first.'
}

Push-Location $Backend
try {
    Write-Output '== migration: alembic upgrade head =='
    & $Python -m alembic upgrade head
    if ($LASTEXITCODE -ne 0) {
        throw 'Alembic migration failed.'
    }

    Write-Output '== seed: demo data =='
    & $Python -m app.db.seed
    if ($LASTEXITCODE -ne 0) {
        throw 'Demo seed failed.'
    }

    Write-Output '== health: API health =='
    & $Python (Join-Path $Root 'scripts\check_health.py')
    if ($LASTEXITCODE -ne 0) {
        throw 'Health check failed.'
    }

    Write-Output '== schema: alembic check =='
    & $Python -m alembic check
    if ($LASTEXITCODE -ne 0) {
        throw 'Alembic schema check failed.'
    }
}
finally {
    Pop-Location
}

Write-Output 'Runbook checks passed: migration, seed, health, and schema.'
