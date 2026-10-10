@echo off
setlocal
cd /d "%~dp0"
call :find_python
if errorlevel 1 goto no_python
echo === MForce automated test suite ===
%PYTHON_CMD% -m mforce test
if errorlevel 1 goto failure
echo.
echo === Scenario demo and CSV report ===
%PYTHON_CMD% -m mforce demo
if errorlevel 1 goto failure
echo.
echo SUCCESS: Tests passed. CSV is in output\demo_results.csv
pause
exit /b 0

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
echo Python 3.11 or newer was not found. Install Python first.
pause
exit /b 1

:failure
echo FAILED: Review test errors above before uploading to GitHub.
pause
exit /b 1
