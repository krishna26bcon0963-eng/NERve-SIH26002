$ErrorActionPreference = 'Stop'
$projectRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$backendPath = Join-Path $projectRoot 'backend'
$frontendPath = Join-Path $projectRoot 'frontend'
$pythonPath = Join-Path $backendPath '.venv\Scripts\python.exe'

if (-not (Test-Path -LiteralPath $pythonPath)) {
    Write-Host 'Creating Python 3.13 environment...'
    & py -3.13 -m venv (Join-Path $backendPath '.venv')
}

$fastApiPath = Join-Path $backendPath '.venv\Lib\site-packages\fastapi\__init__.py'
$uvicornPath = Join-Path $backendPath '.venv\Lib\site-packages\uvicorn\__init__.py'
if (-not (Test-Path -LiteralPath $fastApiPath) -or -not (Test-Path -LiteralPath $uvicornPath)) {
    Write-Host 'Installing backend packages (first run only)...'
    & $pythonPath -m pip install -r (Join-Path $backendPath 'requirements.txt')
    if ($LASTEXITCODE -ne 0) { throw 'Backend package installation failed. Check the internet connection and retry.' }
} else {
    Write-Host 'Backend packages already ready - skipping download.'
}

$vitePath = Join-Path $frontendPath 'node_modules\.bin\vite.cmd'
if (-not (Test-Path -LiteralPath $vitePath)) {
    Write-Host 'Installing frontend packages with npm.cmd (first run only)...'
    Push-Location $frontendPath
    & npm.cmd install
    if ($LASTEXITCODE -ne 0) { Pop-Location; throw 'Frontend package installation failed. Check Node.js and the internet connection.' }
    Pop-Location
} else {
    Write-Host 'Frontend packages already ready - skipping download.'
}

$backendCommand = "Set-Location -LiteralPath '$backendPath'; & '.\.venv\Scripts\python.exe' -m uvicorn main:app --host 0.0.0.0 --port 8000 --reload"
$frontendCommand = "Set-Location -LiteralPath '$frontendPath'; & npm.cmd run dev -- --host 0.0.0.0"
Start-Process powershell -ArgumentList '-NoExit','-Command',$backendCommand
Start-Process powershell -ArgumentList '-NoExit','-Command',$frontendCommand
Write-Host ''
Write-Host 'NERve is starting. Keep both server windows open.'
Write-Host 'This laptop: http://localhost:5173'
Write-Host 'Other devices: run ipconfig, note this laptop IPv4 address, then open:'
Write-Host '  State Control:  http://YOUR-IP:5173/?role=STATE_CONTROL'
Write-Host '  District Desk:  http://YOUR-IP:5173/?role=DISTRICT_OPS'
Write-Host '  Field Tablet:   http://YOUR-IP:5173/?role=FIELD_OFFICER'
Write-Host 'All devices must use the same Wi-Fi or phone hotspot. Allow Private network access if Windows Firewall asks.'
