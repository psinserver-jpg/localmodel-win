# LMW launcher for PowerShell. Usage: .\lmw.ps1 run "요청" -w .\my-site
$env:PYTHONUTF8 = "1"
$env:PYTHONPATH = "$PSScriptRoot;$env:PYTHONPATH"
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8
if (Get-Command py -ErrorAction SilentlyContinue) { py -3 -m lmw @args } else { python -m lmw @args }
exit $LASTEXITCODE
