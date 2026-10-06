@echo off
rem LMW launcher for Windows (cmd). Usage: lmw run "요청" -w .\my-site
chcp 65001 >nul
set "PYTHONUTF8=1"
set "PYTHONPATH=%~dp0;%PYTHONPATH%"
where py >nul 2>nul && (py -3 -m lmw %*) || (python -m lmw %*)
