param(
    [int]$TestFailureCode = 0,
    [switch]$TextCheckOnly
)

$ErrorActionPreference = 'Stop'

# Run the complete repository verification without depending on the caller's
# current directory. The runbook and live E2E intentionally update the demo
# SQLite database; this script never starts or stops a server.
$Root = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path
$Backend = Join-Path $Root 'backend'
$Frontend = Join-Path $Root 'frontend'
$Python = Join-Path $Backend 'venv\Scripts\python.exe'
$VerificationExitCode = 1

function Require-File {
    param(
        [Parameter(Mandatory = $true)][string]$Path,
        [Parameter(Mandatory = $true)][string]$Description
    )

    if (-not (Test-Path -LiteralPath $Path -PathType Leaf)) {
        throw "$Description not found: $Path. Install the project dependencies first."
    }
}

function Invoke-Phase {
    param(
        [Parameter(Mandatory = $true)][string]$Name,
        [Parameter(Mandatory = $true)][string]$WorkingDirectory,
        [Parameter(Mandatory = $true)][scriptblock]$Action,
        [Parameter(Mandatory = $true)][string]$FailureContext
    )

    Write-Host "`n=== $Name ===" -ForegroundColor Cyan
    Push-Location -LiteralPath $WorkingDirectory
    try {
        $PhaseException = $null
        $PhaseExitCode = 0
        try {
            # Keep native non-zero results observable through LASTEXITCODE even
            # when the caller has enabled PowerShell 7's native error preference.
            $PSNativeCommandUseErrorActionPreference = $false
            & $Action
            $PhaseExitCode = if ($null -eq $LASTEXITCODE) { 0 } else { [int]$LASTEXITCODE }
        }
        catch {
            $PhaseException = $_
            $PhaseExitCode = 1
        }
        if ($PhaseExitCode -ne 0) {
            $script:VerificationExitCode = $PhaseExitCode
            $ErrorDetail = if ($null -ne $PhaseException) { " $($PhaseException.Exception.Message)" } else { '' }
            throw "Phase '$Name' failed with exit code $PhaseExitCode.$ErrorDetail $FailureContext"
        }
        Write-Host "PASS: $Name" -ForegroundColor Green
    }
    finally {
        Pop-Location
    }
}

function Invoke-RepositoryTextCheck {
    param([Parameter(Mandatory = $true)][string]$WorkingDirectory)

    & git diff --check
    $TrackedExitCode = if ($null -eq $LASTEXITCODE) { 0 } else { [int]$LASTEXITCODE }
    if ($TrackedExitCode -ne 0) {
        return $TrackedExitCode
    }

    $UntrackedFiles = @(& git ls-files --others --exclude-standard)
    $GitExitCode = if ($null -eq $LASTEXITCODE) { 0 } else { [int]$LASTEXITCODE }
    if ($GitExitCode -ne 0) {
        throw "Unable to list untracked files (exit code $GitExitCode)."
    }

    foreach ($RelativePath in $UntrackedFiles) {
        if ([string]::IsNullOrWhiteSpace($RelativePath)) {
            continue
        }
        $Path = Join-Path $WorkingDirectory $RelativePath
        if (-not (Test-Path -LiteralPath $Path -PathType Leaf)) {
            continue
        }
        $Bytes = [System.IO.File]::ReadAllBytes($Path)
        if ($Bytes -contains 0) {
            continue
        }
        $Content = [System.IO.File]::ReadAllText($Path)
        if ($Content -match '(?m)[ \t]+$') {
            throw "Untracked text file contains trailing whitespace: $RelativePath"
        }
    }
    return 0
}

try {
    if ($TestFailureCode -ne 0) {
        Invoke-Phase -Name 'Test failure code probe' -WorkingDirectory $Root -FailureContext 'This controlled failure verifies native exit-code propagation.' -Action {
            Write-Host "Test failure code probe returned: $TestFailureCode"
            & cmd.exe /c exit $TestFailureCode
        }
        exit 0
    }

    if ($TextCheckOnly) {
        Invoke-Phase -Name 'Git diff check' -WorkingDirectory $Root -FailureContext 'Remove trailing whitespace or resolve patch formatting errors before delivery.' -Action {
            Invoke-RepositoryTextCheck -WorkingDirectory $Root | Out-Null
        }
        exit 0
    }

    Require-File -Path $Python -Description 'Backend virtual-environment Python'
    Require-File -Path (Join-Path $Root 'scripts\test_runbooks.ps1') -Description 'Runbook script'
    Require-File -Path (Join-Path $Root 'scripts\e2e_demo.py') -Description 'HTTP E2E script'
    Require-File -Path (Join-Path $Root 'scripts\check_providers.py') -Description 'Provider preflight script'
    Require-File -Path (Join-Path $Frontend 'package.json') -Description 'Frontend package manifest'

    $NpmCommand = Get-Command npm.cmd -ErrorAction SilentlyContinue
    if ($null -eq $NpmCommand) {
        throw 'npm.cmd was not found on PATH. Install Node.js/npm before running full verification.'
    }
    $Npm = $NpmCommand.Source

    Invoke-Phase -Name 'Backend pytest' -WorkingDirectory $Backend -FailureContext 'Inspect the first failing backend test and its traceback.' -Action {
        & $Python -m pytest -q
    }

    Invoke-Phase -Name 'Alembic schema check' -WorkingDirectory $Backend -FailureContext 'Run alembic upgrade head from backend and inspect the schema drift.' -Action {
        & $Python -m alembic check
    }

    Invoke-Phase -Name 'Migration, seed, health, and schema runbook' -WorkingDirectory $Root -FailureContext 'Run scripts\test_runbooks.ps1 directly to inspect migration, seed, health, or schema output.' -Action {
        & (Join-Path $Root 'scripts\test_runbooks.ps1')
    }

    Invoke-Phase -Name 'Official HTTP E2E demo' -WorkingDirectory $Root -FailureContext 'The E2E uses the seeded demo SQLite database; inspect the first failed API assertion.' -Action {
        & $Python (Join-Path $Root 'scripts\e2e_demo.py')
    }

    Invoke-Phase -Name 'Provider capability preflight' -WorkingDirectory $Root -FailureContext 'Inspect provider settings, optional dependencies, local resources, and the reported fallback state.' -Action {
        & $Python (Join-Path $Root 'scripts\check_providers.py')
    }

    Invoke-Phase -Name 'Frontend unit tests' -WorkingDirectory $Frontend -FailureContext 'Inspect the first failing Vitest case and component assertion.' -Action {
        & $Npm run test:unit -- --run
    }

    Invoke-Phase -Name 'Frontend type-check' -WorkingDirectory $Frontend -FailureContext 'Inspect the first TypeScript error reported by vue-tsc.' -Action {
        & $Npm run type-check
    }

    Invoke-Phase -Name 'Frontend production build' -WorkingDirectory $Frontend -FailureContext 'Inspect the Vite/Rollup build error and its referenced module.' -Action {
        & $Npm run build
    }

    Invoke-Phase -Name 'Git diff check' -WorkingDirectory $Root -FailureContext 'Remove trailing whitespace or resolve patch formatting errors before delivery.' -Action {
        Invoke-RepositoryTextCheck -WorkingDirectory $Root | Out-Null
    }

    Write-Host "`nAll verification phases passed." -ForegroundColor Green
    exit 0
}
catch {
    Write-Error "`nFull verification stopped: $($_.Exception.Message)" -ErrorAction Continue
    exit $VerificationExitCode
}
