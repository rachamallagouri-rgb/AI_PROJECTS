@echo off
setlocal
cd /d "%~dp0"
call :find_python
if errorlevel 1 goto no_python
%PYTHON_CMD% -m mforce gui
set "EXIT_CODE=%ERRORLEVEL%"
if not "%EXIT_CODE%"=="0" echo MForce could not launch. Please review the error above.
pause
exit /b %EXIT_CODE%

:find_python
where py >nul 2>&1
if not errorlevel 1 (
    py -3 -c "import sys; sys.exit(0 if sys.version_info >= (3, 11) else 1)" >nul 2>&1
    if not errorlevel 1 (
        set "PYTHON_CMD=py -3"
        exit /b 0
    )
)
where python >nul 2>&1
if not errorlevel 1 (
    python -c "import sys; sys.exit(0 if sys.version_info >= (3, 11) else 1)" >nul 2>&1
    if not errorlevel 1 (
        set "PYTHON_CMD=python"
        exit /b 0
    )
)
exit /b 1

:no_python
echo Python 3.11 or newer was not found.
echo Install Python and then double-click this file again.
echo https://www.python.org/downloads/windows/
pause
exit /b 1
