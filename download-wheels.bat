@echo off
rem Rebuild the offline wheelhouse (wheels\) for Win7 32-bit deployment.
rem Wheels are platform-specific: they MUST be downloaded using a 32-bit
rem Python 3.8 interpreter. Internet access required on this machine.

py -3.8-32 -m pip --version >nul 2>&1
if errorlevel 1 (
    echo [ERROR] py -3.8-32 not found on this machine.
    echo Install Python 3.8.10 32-bit, the "Windows x86 executable installer" from:
    echo   https://www.python.org/downloads/release/python-3810/
    echo Then re-run this script.
    exit /b 1
)

echo Downloading wheels for win32 / Python 3.8 ...
py -3.8-32 -m pip download -r demo\requirements.txt -r demo\requirements-dev.txt -d wheels
if errorlevel 1 (
    echo [ERROR] Wheel download failed. Check network / proxy settings.
    exit /b 1
)

echo.
echo Done. wheels\ is ready (~20 files).
echo Deployment: copy the whole repo folder INCLUDING wheels\ to the Win7
echo target machine, then run install.bat there (offline install, no network).
