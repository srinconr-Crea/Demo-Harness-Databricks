@echo off
setlocal
if "%~1"=="" goto usage
if "%~2"=="" goto usage
if exist "%~dp0src\agents\harness\.venv\Scripts\python.exe" (
  "%~dp0src\agents\harness\.venv\Scripts\python.exe" "%~dp0scripts\start_harness.py" "%~1" "%~2"
) else (
  py -3 "%~dp0scripts\start_harness.py" "%~1" "%~2"
)
exit /b %errorlevel%
:usage
echo Uso: iniciar-harness.bat APP_NAME DATABRICKS_PROFILE
exit /b 1
endlocal
