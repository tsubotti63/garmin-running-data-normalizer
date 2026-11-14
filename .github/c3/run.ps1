# C3 of v2.3.0 (a disposable branch, not for main): the PowerShell lines of the Windows check of 2.3.0rc3, run on
# Windows PowerShell 5.1 with the head that chooses the folder of the share replaced by one statement that names a
# folder of the runner (the lines are otherwise the person's, byte for byte), in the order of the person's steps:
# line 1; the install of line 2 in the background, as its window stays open with the GUI; line 3; the GUI stopped
# (here with Stop-Process, as no page is used; the person quits it on the page); line 9; line 10 (with a time limit,
# as its moves to the Recycle Bin may wait for a window). Each line runs in a new PowerShell, as when pasted into a
# new window. A stand-in file takes the name of the ZIP (line 3 only copies it). Printed: the W lines of the results
# file, counts, and True/False; never the output of the install, which holds the address and key of the GUI.
$ErrorActionPreference = 'Continue'
$here = Join-Path $env:GITHUB_WORKSPACE '.github\c3'
$check = Join-Path $env:RUNNER_TEMP 'v2.3.0rc3_check'
$null = New-Item -ItemType Directory -Force -Path $check
Set-Content -LiteralPath (Join-Path $check 'v2.3.0rc3_results.txt') -Value 'CI: the lines of the Windows check of 2.3.0rc3' -Encoding ASCII
Set-Content -LiteralPath (Join-Path $check 'synthetic_garmin_export_x12d.zip') -Value 'a stand-in for the ZIP' -Encoding ASCII
Write-Output ('downloads-folder ' + (Test-Path -LiteralPath "$HOME\Downloads") + ' / shell-downloads ' + [bool](New-Object -ComObject Shell.Application).NameSpace('shell:Downloads'))
$launcher = [bool](Get-Command py -ErrorAction SilentlyContinue)
Write-Output ('py-launcher ' + $launcher)
if (-not $launcher) {
  # The lines call py (the Python launcher of the company PC); here a stand-in calls the python of setup-python.
  $shim = Join-Path $env:RUNNER_TEMP 'py-shim'
  $null = New-Item -ItemType Directory -Force -Path $shim
  Set-Content -LiteralPath (Join-Path $shim 'py.cmd') -Value '@python %*' -Encoding ASCII
  $env:PATH = $shim + ';' + $env:PATH
}

function Encoded([string]$file) {
  [Convert]::ToBase64String([Text.Encoding]::Unicode.GetBytes([IO.File]::ReadAllText((Join-Path $here $file))))
}
function Gui-Runs {
  [bool](Get-CimInstance Win32_Process -Filter "Name = 'python.exe' OR Name = 'pythonw.exe'" | Where-Object { $_.CommandLine -like '*garmin_running_data_normalizer*' })
}
function Run-Line([string]$file, [int]$seconds) {
  $out = Join-Path $env:RUNNER_TEMP ($file + '.out')
  $err = Join-Path $env:RUNNER_TEMP ($file + '.err')
  $p = Start-Process powershell -ArgumentList @('-NoProfile', '-EncodedCommand', (Encoded $file)) -NoNewWindow -PassThru -RedirectStandardOutput $out -RedirectStandardError $err
  if ($p.WaitForExit($seconds * 1000)) {
    Write-Output ($file + ': ended, error lines ' + @(Get-Content -LiteralPath $err -ErrorAction SilentlyContinue | Where-Object { $_.Trim() }).Count)
    Get-Content -LiteralPath $err -ErrorAction SilentlyContinue | Where-Object { $_ -match 'Exception|FullyQualifiedErrorId|CategoryInfo' } | Select-Object -First 6 | ForEach-Object { '  ' + $_.Trim() }
  } else {
    Stop-Process -Id $p.Id -Force
    Write-Output ($file + ': did not end in ' + $seconds + ' s, stopped')
  }
}

Run-Line '1.txt' 120

$out2 = Join-Path $env:RUNNER_TEMP '2.out'
$err2 = Join-Path $env:RUNNER_TEMP '2.err'
$p2 = Start-Process powershell -ArgumentList @('-NoProfile', '-EncodedCommand', (Encoded '2.txt')) -NoNewWindow -PassThru -RedirectStandardOutput $out2 -RedirectStandardError $err2
$up = $false
for ($i = 0; $i -lt 96; $i++) {
  Start-Sleep -Seconds 5
  if (Gui-Runs) { $up = $true; break }
  if ($p2.HasExited) { break }
}
Start-Sleep -Seconds 10
$o2 = @(Get-Content -LiteralPath $out2 -ErrorAction SilentlyContinue)
Write-Output ('2: gui-up ' + $up + ' / exited ' + $p2.HasExited + ' / downloading ' + @($o2 | Where-Object { $_ -match '^\s*Downloading ' }).Count + ' / using-cached ' + @($o2 | Where-Object { $_ -match '^\s*Using cached ' }).Count + ' / gui-address-line ' + [bool]($o2 | Where-Object { $_ -like 'GUI address*' }) + ' / error lines ' + @(Get-Content -LiteralPath $err2 -ErrorAction SilentlyContinue | Where-Object { $_.Trim() }).Count)

Run-Line '3.txt' 180

Get-CimInstance Win32_Process -Filter "Name = 'python.exe' OR Name = 'pythonw.exe'" | Where-Object { $_.CommandLine -like '*garmin_running_data_normalizer*' } | ForEach-Object { Stop-Process -Id $_.ProcessId -Force }
Start-Sleep -Seconds 5
if (-not $p2.HasExited) { Stop-Process -Id $p2.Id -Force }
Write-Output ('gui-stopped ' + (-not (Gui-Runs)))

Run-Line '9.txt' 60
Run-Line '10.txt' 240

Write-Output '--- the results file (its W lines)'
Get-Content -LiteralPath (Join-Path $check 'v2.3.0rc3_results.txt') | Where-Object { $_ -like 'W*' }
Write-Output ('left: venv-rc ' + (Test-Path -LiteralPath "$HOME\garmin-normalizer-rc") + ' / outputs ' + (Test-Path -LiteralPath "$HOME\GarminRunningData") + ' / settings ' + (Test-Path -LiteralPath "$env:LOCALAPPDATA\garmin-running-data-normalizer") + ' / zip-in-downloads ' + (Test-Path -LiteralPath "$HOME\Downloads\synthetic_garmin_export_x12d.zip"))
