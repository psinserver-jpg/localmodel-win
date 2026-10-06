---
name: windows-dev
description: Developing on Windows - PowerShell vs cmd, py launcher, venv activation and execution policy, paths, CRLF line endings, cp949 vs UTF-8 encoding, ports and long paths.
triggers: [windows, powershell, cmd, bat, ps1, cp949, encoding, utf-8, crlf, path, execution policy, wsl, winget, 윈도우, 파워쉘, 인코딩, 한글깨짐, 경로]
---
# Windows Development Reference

Assume the user may be on Windows unless told otherwise. Give PowerShell commands first, bash second when they differ.

## 1. Shells

| Task | PowerShell | cmd | bash |
|---|---|---|---|
| list files | `Get-ChildItem` / `dir` / `ls` | `dir` | `ls` |
| env var (session) | `$env:API_KEY = "x"` | `set API_KEY=x` | `export API_KEY=x` |
| read env var | `$env:API_KEY` | `%API_KEY%` | `$API_KEY` |
| delete folder | `Remove-Item -Recurse -Force build` | `rmdir /s /q build` | `rm -rf build` |
| copy | `Copy-Item a b` | `copy a b` | `cp a b` |
| chain on success | `cmd1; if ($?) { cmd2 }` (PS 7: `cmd1 && cmd2`) | `cmd1 && cmd2` | `cmd1 && cmd2` |
| current dir | `$PWD` / `Get-Location` | `cd` | `pwd` |
| find text | `Select-String -Pattern foo -Path *.py` | `findstr foo *.py` | `grep foo *.py` |

- Windows PowerShell 5.1 does not support `&&`; PowerShell 7 does.
- Never give bash-only syntax (`export`, `rm -rf`, `$(...)` in Windows contexts, `source`) as the only option.

## 2. Python on Windows

```powershell
py --version                 # the py launcher is installed with python.org Python
py -3.12 -m venv .venv
.\.venv\Scripts\Activate.ps1  # PowerShell
.venv\Scripts\activate.bat    # cmd
python -m pip install -r requirements.txt
python app.py
deactivate
```

- `'python' is not recognized` / Microsoft Store opens → use `py`, or reinstall Python with "Add python.exe to PATH" checked; disable the Store aliases in Settings → Apps → Advanced app settings → App execution aliases.
- `pip` not recognized → always use `python -m pip ...` (or `py -m pip`).
- Activation blocked ("running scripts is disabled on this system"):
```powershell
Set-ExecutionPolicy -Scope CurrentUser RemoteSigned
```
  Or run once without changing policy: `powershell -ExecutionPolicy Bypass -File .\script.ps1`.
- venv paths: `Scripts\` on Windows vs `bin/` on macOS/Linux.

## 3. Node on Windows

- Install: `winget install OpenJS.NodeJS.LTS` (or the installer from nodejs.org). Check `node -v`, `npm -v`.
- `npm` scripts run in cmd by default: avoid `rm -rf`, `cp`, `VAR=x cmd` in package.json — use `rimraf`, `cross-env`, or Node scripts.
- `npx` blocked by execution policy → same fix as above, or use `npx.cmd`.

## 4. Paths

- Use `pathlib.Path` / `path.join` — never hard-code `/` or `\\` separators in code.
- In Python strings use raw strings or forward slashes: `r"C:\Users\me\data"` or `"C:/Users/me/data"`. `"C:\new"` is broken (`\n`).
- Paths with spaces must be quoted in shells: `cd "C:\Program Files\App"`.
- Home folder: `Path.home()`, `os.homedir()`; app data: `%APPDATA%` / `$env:APPDATA`.
- Long paths (> 260 chars) can fail: keep projects near the drive root (`C:\dev\project`), or enable long paths (`git config --global core.longpaths true`; Windows setting `LongPathsEnabled`).
- File names are case-insensitive on Windows but case-sensitive on Linux servers — keep imports' case exactly matching file names.
- Reserved names: `CON`, `PRN`, `AUX`, `NUL`, `COM1`, `LPT1` cannot be file names.

## 5. Encoding (Korean text!)

- Korean Windows defaults to cp949 for many tools. Always be explicit:
```python
open(path, "r", encoding="utf-8")
open(path, "w", encoding="utf-8", newline="")
Path(p).read_text(encoding="utf-8")
pd.read_csv(path, encoding="utf-8")          # Excel-exported Korean CSV is often "cp949"
df.to_csv(path, index=False, encoding="utf-8-sig")   # utf-8-sig so Excel shows Korean correctly
subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace")
```
- `UnicodeDecodeError: 'cp949' codec can't decode` → you opened a UTF-8 file without `encoding="utf-8"`.
- `UnicodeEncodeError` when printing → set `PYTHONUTF8=1` (`$env:PYTHONUTF8 = "1"`) or `sys.stdout.reconfigure(encoding="utf-8")`.
- Broken Korean in cmd output → `chcp 65001` to switch the console to UTF-8.
- PowerShell 5.1 `Out-File`/`>` writes UTF-16 by default → use `Set-Content -Encoding utf8` or PowerShell 7.
- HTML: `<meta charset="utf-8">` first in `<head>`, and save files as UTF-8.

## 6. Line endings

- Windows editors may use CRLF. Git setting for Windows users: `git config --global core.autocrlf true`.
- Shell scripts (`.sh`) must be LF or they fail on Linux (`/bin/bash^M: bad interpreter`). Add `.gitattributes`:
```
* text=auto
*.sh text eol=lf
*.bat text eol=crlf
*.ps1 text eol=crlf
```

## 7. Ports & processes

```powershell
netstat -ano | findstr :3000         # find PID using port 3000
taskkill /PID 12345 /F               # kill it
Get-NetTCPConnection -LocalPort 3000 | Select-Object OwningProcess   # PowerShell way
```
- Firewall prompt appears when a server binds to `0.0.0.0`; bind `127.0.0.1` for local-only dev.

## 8. Opening things

- Open a file/URL in the default app: `start index.html` (cmd), `Start-Process index.html` or `ii index.html` (PowerShell).
- Pages using ES modules (`<script type="module">`) or `fetch()` of local files do not work from `file://` — run a local server: `python -m http.server 8000` then open `http://localhost:8000`.

## 9. Scripts for users

- Provide a `.bat` for double-click users; start with `@echo off` and `chcp 65001 >nul` for Korean output, and `pause` at the end so the window stays open.
- `.ps1` scripts may be blocked by execution policy; mention the fix.
- WSL is an option for Linux-only tooling (`wsl --install`), but don't require it unless necessary.
