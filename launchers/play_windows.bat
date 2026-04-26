@echo off
setlocal

set "SCRIPT_DIR=%~dp0"
cd /d "%SCRIPT_DIR%\.." || goto folder_error

set "PROJECT_DIR=%CD%"
set "VENV_DIR=%PROJECT_DIR%\.venv-windows"
set "VENV_PYTHON=%VENV_DIR%\Scripts\python.exe"
set "READY_FILE=%VENV_DIR%\.pydrac-ready"

if exist "%VENV_PYTHON%" goto setup_requirements

call :find_python
if errorlevel 1 goto python_error

echo Setting up PyDrac Valley. This may take a minute the first time...
%PYTHON_CMD% -m venv "%VENV_DIR%"
if errorlevel 1 goto venv_error

:setup_requirements
if exist "%READY_FILE%" goto start_game

echo Installing game requirements. This only happens the first time...
"%VENV_PYTHON%" -m pip install --upgrade pip
if errorlevel 1 goto pip_error

"%VENV_PYTHON%" -m pip install -r requirements.txt
if errorlevel 1 goto requirements_error

type nul > "%READY_FILE%"

:start_game
echo Starting PyDrac Valley...
"%VENV_PYTHON%" code\main.py
if errorlevel 1 goto game_error
exit /b 0

:find_python
py -3 --version >nul 2>&1
if not errorlevel 1 (
  set "PYTHON_CMD=py -3"
  exit /b 0
)

python --version >nul 2>&1
if not errorlevel 1 (
  set "PYTHON_CMD=python"
  exit /b 0
)

exit /b 1

:folder_error
call :show_error "Could not open the game folder."
exit /b 1

:python_error
start "" "https://www.python.org/downloads/windows/"
call :show_error "Python 3 is not installed. A browser page was opened so you can download it. IMPORTANT: check the box that says 'Add python.exe to PATH', install Python, then double-click this shortcut again."
exit /b 1

:venv_error
call :show_error "Could not create the Python environment."
exit /b 1

:pip_error
call :show_error "Could not update pip."
exit /b 1

:requirements_error
call :show_error "Could not install the game requirements."
exit /b 1

:game_error
call :show_error "The game stopped unexpectedly."
exit /b 1

:show_error
echo.
echo PyDrac Valley could not start.
echo %~1
echo.
echo If you need help, send a screenshot of this window to the student.
echo.
pause
exit /b 0
