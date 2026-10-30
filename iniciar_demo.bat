@echo off
set PYTHONUTF8=1
cd /d "%~dp0"
python run_demo.py
if errorlevel 1 echo A execucao falhou. Consulte a mensagem acima.
pause
