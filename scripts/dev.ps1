$ErrorActionPreference = "Stop"

$Root = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$Backend = Join-Path $Root "backend"
$Frontend = Join-Path $Root "frontend"
$Python = Join-Path $Backend "venv\Scripts\python.exe"
$LogDirectory = Join-Path $Backend "storage\logs"
$BackendLog = Join-Path $LogDirectory "dev-backend.log"
$BackendErrorLog = Join-Path $LogDirectory "dev-backend.error.log"
$BackendPort = 8000
$BackendHealthUrl = "http://127.0.0.1:$BackendPort/api/v1/health"

function Get-ListeningProcessIds {
    param([int]$Port)

    @(
        Get-NetTCPConnection -State Listen -LocalPort $Port -ErrorAction SilentlyContinue |
            Select-Object -ExpandProperty OwningProcess -Unique
    )
}

function Test-BackendHealth {
    param([string]$Url)

    try {
        $response = Invoke-WebRequest -UseBasicParsing -Uri $Url -TimeoutSec 2 -ErrorAction Stop
        return ([int]$response.StatusCode -eq 200)
    }
    catch {
        return $false
    }
}

function Get-ChildProcessIds {
    param([int]$ParentId)

    $children = @(
        Get-CimInstance Win32_Process -Filter "ParentProcessId = $ParentId" -ErrorAction SilentlyContinue
    )
    foreach ($child in $children) {
        $child.ProcessId
        Get-ChildProcessIds -ParentId ([int]$child.ProcessId)
    }
}

function Stop-ProcessTree {
    param([System.Diagnostics.Process]$Process)

    if (-not $Process) {
        return
    }

    $processId = $Process.Id
    $childIds = @(
        Get-ChildProcessIds -ParentId $processId |
            Sort-Object -Descending -Unique
    )
    foreach ($childId in $childIds) {
        Stop-Process -Id $childId -Force -ErrorAction SilentlyContinue
    }
    Stop-Process -Id $processId -Force -ErrorAction SilentlyContinue
}

function Get-BackendLogs {
    $sections = @()
    foreach ($path in @($BackendLog, $BackendErrorLog)) {
        if (Test-Path -LiteralPath $path) {
            $sections += "--- $path ---"
            $sections += Get-Content -LiteralPath $path -Raw -ErrorAction SilentlyContinue
        }
    }

    if ($sections.Count -eq 0) {
        return "No backend log was created."
    }
    return ($sections -join [Environment]::NewLine)
}

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

$BackendProcess = $null
$OwnsBackendProcess = $false
$ExistingBackendProcessIds = @(Get-ListeningProcessIds -Port $BackendPort)

if ($ExistingBackendProcessIds.Count -gt 0) {
    if (Test-BackendHealth -Url $BackendHealthUrl) {
        Write-Host "Reusing the healthy backend already listening on port $BackendPort."
    }
    else {
        $owners = $ExistingBackendProcessIds -join ", "
        throw "Backend port $BackendPort is already in use by process ID(s): $owners. Stop that process or use another local service before starting BuildWise."
    }
}
else {
    Write-Host "Starting backend on port $BackendPort..."
    $BackendProcess = Start-Process `
        -FilePath $Python `
        -ArgumentList @(
            "-m", "uvicorn", "app.main:app", "--reload",
            "--host", "0.0.0.0", "--port", "$BackendPort"
        ) `
        -WorkingDirectory $Backend `
        -RedirectStandardOutput $BackendLog `
        -RedirectStandardError $BackendErrorLog `
        -WindowStyle Hidden `
        -PassThru
    $OwnsBackendProcess = $true
}

try {
    if ($OwnsBackendProcess) {
        $deadline = (Get-Date).AddSeconds(20)
        do {
            $BackendProcess.Refresh()
            if ($BackendProcess.HasExited) {
                throw "Backend exited during startup (PID $($BackendProcess.Id)).`n$(Get-BackendLogs)"
            }
            if (Test-BackendHealth -Url $BackendHealthUrl) {
                break
            }
            Start-Sleep -Milliseconds 250
        } while ((Get-Date) -lt $deadline)

        if (-not (Test-BackendHealth -Url $BackendHealthUrl)) {
            throw "Backend did not become healthy within 20 seconds.`n$(Get-BackendLogs)"
        }
        Write-Host "Backend is ready at $BackendHealthUrl."
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

    if ($OwnsBackendProcess) {
        $BackendProcess.Refresh()
        if ($BackendProcess.HasExited) {
            throw "Backend process exited while the frontend was running. See $BackendLog and $BackendErrorLog."
        }
    }
}
finally {
    if ($OwnsBackendProcess) {
        Stop-ProcessTree -Process $BackendProcess
    }
}
