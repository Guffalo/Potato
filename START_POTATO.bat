@echo off
title POTATO
cd /d "%~dp0"
echo.
echo   ==========================================
echo     POTATO - LAN Media Hub ^& TV Transmitter
echo     Created by Guffalo (GPL-3.0-or-later)
echo   ==========================================
echo.
where py >nul 2>nul
if %errorlevel%==0 (
    py -3 potato.py --open
    goto :done
)
where python >nul 2>nul
if %errorlevel%==0 (
    python potato.py --open
    goto :done
)
echo [!] Python 3 was not found on this PC.
echo     Download Python 3 free from https://www.python.org/downloads/
echo     (Check "Add Python to PATH" during install, then double-click START_POTATO.bat again.)
pause
:done
