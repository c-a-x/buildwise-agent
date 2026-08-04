$ErrorActionPreference = "Stop"

$Root = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$Backend = Join-Path $Root "backend"
$Frontend = Join-Path $Root "frontend"
$Python = Join-Path $Backend "venv\Scripts\python.exe"
$LogDirectory = Join-Path $Backend "storage\logs"
$BackendLog = Join-Path $LogDirectory "dev-backend.log"

if (-not (Test-Path -LiteralPath $Python)) {
    throw "backend/venv Python was not found. Install dependencies first."
}

New-Item -ItemType Directory -Path $LogDirectory -Force | Out-Null

Push-Location $Backend
try {
    & $Python -m alembic upgrade head
    if ($LASTEXITCODE -ne 0) {
        throw "Alembic migration failed with exit code $LASTEXITCODE."
    }
    & $Python -m app.db.seed
    if ($LASTEXITCODE -ne 0) {
        throw "Demo seed failed with exit code $LASTEXITCODE."
    }
}
finally {
    Pop-Location
}

$BackendCommand = "& '$Python' -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000 *>> '$BackendLog' 2>&1"
$BackendProcess = Start-Process -FilePath "powershell.exe" -ArgumentList @("-NoProfile", "-NonInteractive", "-Command", $BackendCommand) -WorkingDirectory $Backend -WindowStyle Hidden -PassThru

try {
    Start-Sleep -Seconds 2
    if ($BackendProcess.HasExited) {
        $backendOutput = if (Test-Path -LiteralPath $BackendLog) { Get-Content -LiteralPath $BackendLog -Raw } else { "No backend log was created." }
        throw "Backend exited immediately (PID $($BackendProcess.Id)).`n$backendOutput"
    }

    Push-Location $Frontend
    try {
        & npm.cmd run dev -- --host 0.0.0.0
        if ($LASTEXITCODE -ne 0) {
            throw "Frontend dev server exited with code $LASTEXITCODE."
        }
    }
    finally {
        Pop-Location
    }
    if ($BackendProcess.HasExited) {
        throw "Backend process exited while the frontend was running. See $BackendLog."
    }
}
finally {
    if ($BackendProcess -and -not $BackendProcess.HasExited) {
        Stop-Process -Id $BackendProcess.Id -Force
    }
}
