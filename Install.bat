@echo off
setlocal
cd /d "%~dp0"
if not "%~1"=="" (
  if /I "%~1"=="cursor" goto run_with_agent
  if /I "%~1"=="claude" goto run_with_agent
  if /I "%~1"=="opencode" goto run_with_agent
  if /I "%~1"=="codex" goto run_with_agent
  echo Invalid agent: %~1
  echo Usage: Install.bat [cursor^|claude^|opencode^|codex]
  pause
  exit /b 1
)

python setup.py install
set EXIT_CODE=%ERRORLEVEL%
goto finish

:run_with_agent
python setup.py install --agent %~1
set EXIT_CODE=%ERRORLEVEL%

:finish
pause
exit /b %EXIT_CODE%
