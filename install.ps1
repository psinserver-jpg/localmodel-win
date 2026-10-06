# LMW installer for Windows.
#   PowerShell:  irm https://raw.githubusercontent.com/psinserver-jpg/localmodel-win/main/install.ps1 | iex
#   cmd:         powershell -ExecutionPolicy Bypass -c "irm https://raw.githubusercontent.com/psinserver-jpg/localmodel-win/main/install.ps1 | iex"
# Then open a NEW terminal and type:  lmw
$ErrorActionPreference = "Stop"
try { [Net.ServicePointManager]::SecurityProtocol = [Net.ServicePointManager]::SecurityProtocol -bor [Net.SecurityProtocolType]::Tls12 } catch {}
$Repo   = "psinserver-jpg/localmodel-win"
$Branch = if ($env:LMW_BRANCH) { $env:LMW_BRANCH } else { "main" }
$Dest   = Join-Path $env:LOCALAPPDATA "lmw"
$App    = Join-Path $Dest "app"
$Bin    = Join-Path $Dest "bin"

Write-Host "`n  LMW 설치 중…" -ForegroundColor Cyan

# 1) Python 3.8+
$py = $null
foreach ($c in @("py -3", "python", "python3")) {
    try { $v = & ([scriptblock]::Create("$c --version")) 2>$null; if ($v -match "Python 3\.(\d+)" -and [int]$Matches[1] -ge 8) { $py = $c; break } } catch {}
}
if (-not $py) {
    Write-Host "  Python 이 없어 설치합니다 (winget)…" -ForegroundColor Yellow
    try {
        winget install -e --id Python.Python.3.12 --accept-source-agreements --accept-package-agreements | Out-Null
    } catch {
        Write-Host "  ✘ Python 자동 설치 실패. https://www.python.org/downloads/ 에서 설치 후 다시 실행하세요" -ForegroundColor Red
        Write-Host "    (설치할 때 'Add python.exe to PATH' 체크)" -ForegroundColor Red
        return
    }
    $env:Path = [Environment]::GetEnvironmentVariable("Path", "Machine") + ";" + [Environment]::GetEnvironmentVariable("Path", "User")
    $py = "py -3"
}

# 2) Download (git if available, otherwise a zip — no git needed)
New-Item -ItemType Directory -Force -Path $Dest, $Bin | Out-Null
# $PSScriptRoot is empty when piped through `irm | iex`
if ($PSScriptRoot -and (Test-Path (Join-Path $PSScriptRoot "lmw\__main__.py"))) {
    $App = $PSScriptRoot   # running from a cloned folder: use it in place
} elseif (Get-Command git -ErrorAction SilentlyContinue) {
    if (Test-Path (Join-Path $App ".git")) { git -C $App pull -q origin $Branch } else { git clone -q -b $Branch "https://github.com/$Repo.git" $App }
} else {
    # No git: download a zip and copy over the old files (no folder delete -> works even if a
    # terminal is still open inside the old install).
    $zip = Join-Path $env:TEMP ("lmw-" + [guid]::NewGuid().ToString() + ".zip")
    $tmp = Join-Path $env:TEMP ("lmw-" + [guid]::NewGuid().ToString())
    try {
        Invoke-WebRequest "https://github.com/$Repo/archive/refs/heads/$Branch.zip" -OutFile $zip -UseBasicParsing
        Expand-Archive $zip -DestinationPath $tmp -Force
        $src = (Get-ChildItem $tmp -Directory | Select-Object -First 1).FullName
        New-Item -ItemType Directory -Force -Path $App | Out-Null
        Copy-Item -Path (Join-Path $src "*") -Destination $App -Recurse -Force
    } catch {
        Write-Host "  ✘ 다운로드/설치 실패: $($_.Exception.Message)" -ForegroundColor Red
        Write-Host "    실행 중인 lmw 창을 모두 닫고 다시 실행하세요. 계속되면 $App 폴더를 지우고 다시 시도하세요." -ForegroundColor Red
        return
    } finally {
        Remove-Item -Recurse -Force $tmp, $zip -ErrorAction SilentlyContinue
    }
}

# 3) `lmw` command
$launcher = "@echo off`r`nchcp 65001 >nul`r`nset `"PYTHONUTF8=1`"`r`nset `"PYTHONPATH=$App;%PYTHONPATH%`"`r`n$py -m lmw %*`r`n"
try {
    Set-Content -Path (Join-Path $Bin "lmw.cmd") -Value $launcher -Encoding ASCII
} catch {
    Write-Host "  ✘ lmw 명령 만들기 실패: $($_.Exception.Message)" -ForegroundColor Red
    return
}
$userPath = [Environment]::GetEnvironmentVariable("Path", "User")
if (-not (($userPath -split ";") -contains $Bin)) {
    [Environment]::SetEnvironmentVariable("Path", ($userPath.TrimEnd(";") + ";" + $Bin), "User")
}
$env:Path += ";$Bin"

Write-Host "  ✔ 설치 완료!" -ForegroundColor Green
Write-Host "  새 터미널(cmd 또는 PowerShell)을 열고  lmw  를 입력하세요 (처음 실행 시 Google 로그인 → 모델 설정)." -ForegroundColor Green
