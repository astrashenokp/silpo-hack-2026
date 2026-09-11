<#
.SYNOPSIS
  Starts the Smart Basket demo locally (Python API + Next.js) and optionally runs the QA suites.

.DESCRIPTION
  Owner: Polina. Run from any folder in Windows PowerShell:
    powershell -ExecutionPolicy Bypass -File deploy/run-local.ps1          # start both services
    powershell -ExecutionPolicy Bypass -File deploy/run-local.ps1 -Test    # start (if needed) and run e2e + UI checks
    powershell -ExecutionPolicy Bypass -File deploy/run-local.ps1 -Stop    # stop what this script started

  Creates services/api/.venv and apps/web/node_modules on the first run and reuses services
  that already answer their health checks. While BUG-001 (a stray "<" in
  services/api/pyproject.toml) is open, the documented editable install fails; the script then
  reads the dependency list tolerantly in memory, installs it and runs the API from the source
  tree. No repository file is changed. Logs: %TEMP%\smart-basket-api.log and smart-basket-web.log.
#>
param([switch]$Test, [switch]$Stop)

$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $PSScriptRoot
$python = Join-Path $root "services\api\.venv\Scripts\python.exe"
$web = Join-Path $root "apps\web"
$stateFile = Join-Path $env:TEMP "smart-basket-run-local.json"
$apiHealth = "http://127.0.0.1:8000/api/health"
$webHealth = "http://localhost:3000/api/health"

function Test-Url([string]$url) {
  try { return (Invoke-WebRequest -Uri $url -UseBasicParsing -TimeoutSec 3).StatusCode -eq 200 } catch { return $false }
}

function Wait-Url([string]$url, [string]$name) {
  for ($i = 0; $i -lt 60; $i++) {
    if (Test-Url $url) { Write-Host "$name is up: $url"; return }
    Start-Sleep -Seconds 1
  }
  throw "$name did not answer $url within 60 s. Logs: $env:TEMP\smart-basket-*.log"
}

function Save-Started([int[]]$ids) { ConvertTo-Json -InputObject $ids | Set-Content $stateFile }

function Read-Started {
  if (-not (Test-Path $stateFile)) { return @() }
  # Windows PowerShell's ConvertFrom-Json emits a JSON array as one object; piping the
  # variable enumerates it.
  $ids = Get-Content $stateFile -Raw | ConvertFrom-Json
  return @($ids | ForEach-Object { [int]$_ })
}

# The venv python.exe and npm.cmd start the real server as a child process, so the
# process that listens on the port is recorded as well; -Stop still works if a wrapper exits.
function Get-Listener([int]$port) {
  (Get-NetTCPConnection -LocalPort $port -State Listen -ErrorAction SilentlyContinue | Select-Object -First 1).OwningProcess
}

# cmd.exe writes the log, so the service does not inherit this script's output handles;
# otherwise a captured or piped run of this script would never finish.
function Start-Background([string]$workingDirectory, [string]$command, [string]$log) {
  Start-Process -FilePath "cmd.exe" -WorkingDirectory $workingDirectory -WindowStyle Hidden -PassThru `
    -ArgumentList "/c `"$command > `"$log`" 2>&1`""
}

if ($Stop) {
  $ids = @(Read-Started)
  if (-not $ids) { Write-Host "Nothing to stop: this script has not started any service."; exit 0 }
  # Windows PowerShell turns native stderr into errors; a process that already exited is fine here.
  $ErrorActionPreference = "Continue"
  foreach ($processId in $ids) {
    & taskkill.exe /PID $processId /T /F *> $null
  }
  Remove-Item $stateFile
  Write-Host "Stopped the services started by run-local.ps1."
  exit 0
}

$started = @(Read-Started)

# The API always runs from the source tree, which works with and without the editable install.
$env:PYTHONPATH = Join-Path $root "services\api\src"

if (Test-Url $apiHealth) {
  Write-Host "API already running: $apiHealth"
} else {
  if (-not (Test-Path $python)) {
    Write-Host "Creating services/api/.venv ..."
    & python -m venv (Join-Path $root "services\api\.venv")
  }
  & $python -c "import importlib.util, sys; sys.exit(0 if all(importlib.util.find_spec(m) for m in ('fastapi', 'uvicorn', 'mcp')) else 1)"
  if ($LASTEXITCODE -ne 0) {
    Write-Host "Installing backend dependencies ..."
    & $python -m pip install --disable-pip-version-check -q -e "$root\services\api[test]"
    if ($LASTEXITCODE -ne 0) {
      Write-Warning "Documented install failed (BUG-001?). Installing the declared dependencies directly."
      $reader = Join-Path $env:TEMP "smart-basket-read-dependencies.py"
      $requirements = Join-Path $env:TEMP "smart-basket-requirements.txt"
      @'
import pathlib, re, sys, tomllib
text = pathlib.Path(sys.argv[1]).read_text(encoding="utf-8")
project = tomllib.loads(re.sub(r"(?m)^<(?=dependencies)", "", text))["project"]
print("\n".join(project["dependencies"] + project["optional-dependencies"]["test"]))
'@ | Set-Content -Encoding ascii $reader
      & $python $reader (Join-Path $root "services\api\pyproject.toml") | Set-Content -Encoding ascii $requirements
      & $python -m pip install --disable-pip-version-check -q -r $requirements
      if ($LASTEXITCODE -ne 0) { throw "Backend dependencies could not be installed." }
    }
  }
  $api = Start-Background $root "`"$python`" -m uvicorn smart_basket.app:app --host 127.0.0.1 --port 8000" `
    (Join-Path $env:TEMP "smart-basket-api.log")
  $started += $api.Id
  Save-Started $started
  Wait-Url $apiHealth "API"
  $started += Get-Listener 8000
  Save-Started $started
}

# Rebuild when there is no build or a source, fixture or config file is newer than it
# (pages and API_BASE_URL are fixed at build time).
function Test-BuildStale {
  $buildId = Join-Path $web ".next\BUILD_ID"
  if (-not (Test-Path $buildId)) { return $true }
  $builtAt = (Get-Item $buildId).LastWriteTime
  $inputs = @(Get-ChildItem (Join-Path $web "src"), (Join-Path $root "fixtures") -Recurse -File) +
    @(Get-Item (Join-Path $web "next.config.ts"), (Join-Path $web "package-lock.json"))
  return [bool]($inputs | Where-Object { $_.LastWriteTime -gt $builtAt } | Select-Object -First 1)
}

if (Test-Url $webHealth) {
  Write-Host "Web app already running: http://localhost:3000"
  if (Test-BuildStale) { Write-Warning "The running web app is older than the sources; run -Stop, then start again to rebuild." }
} else {
  Push-Location $web
  try {
    if (-not (Test-Path "node_modules")) { Write-Host "Installing frontend dependencies ..."; & npm.cmd ci --no-audit --no-fund }
    if (Test-BuildStale) { Write-Host "Building the frontend ..."; & npm.cmd run build }
  } finally { Pop-Location }
  $webProcess = Start-Background $web "npm.cmd run start" (Join-Path $env:TEMP "smart-basket-web.log")
  $started += $webProcess.Id
  Save-Started $started
  Wait-Url $webHealth "Web app"
  $started += Get-Listener 3000
  Save-Started $started
}

Write-Host ""
Write-Host "Open http://localhost:3000 (use localhost: 127.0.0.1 gets 403 on every POST)."
Write-Host "Stop with: powershell -ExecutionPolicy Bypass -File deploy/run-local.ps1 -Stop"

if ($Test) {
  $failed = 0
  & $python -m pip install --disable-pip-version-check -q -r (Join-Path $root "tests\e2e\requirements.txt")
  $env:E2E_BASE_URL = "http://localhost:3000"
  & $python -m pytest (Join-Path $root "tests\e2e") -q
  if ($LASTEXITCODE -ne 0) { $failed++ }
  if (Test-Path (Join-Path $root "tests\ui\node_modules")) {
    Push-Location (Join-Path $root "tests\ui")
    try { & npm.cmd test; if ($LASTEXITCODE -ne 0) { $failed++ } } finally { Pop-Location }
  } else {
    Write-Host "UI checks skipped: run 'npm.cmd ci' and 'npx.cmd playwright install chromium' in tests/ui first."
  }
  if ($failed) { Write-Host "$failed QA suite(s) failed."; exit 1 }
  Write-Host "All QA suites passed."
}
