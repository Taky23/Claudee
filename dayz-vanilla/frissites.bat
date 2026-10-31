@echo off
title DayZ szerver - masolas / frissites
cd /d "%~dp0"
echo.
echo  Ez a fajl a Steambol telepitett DayZ Servert atmasolja IDE, ebbe a mappaba:
echo  %~dp0
echo  A beallitasaidat (serverDZ.cfg), a naplokat es a mentett vilagot NEM irja felul.
echo.

rem --- a Steam mappajanak megkeresese
set "STEAM="
for /f "tokens=2,*" %%a in ('reg query "HKCU\Software\Valve\Steam" /v SteamPath 2^>nul ^| find "SteamPath"') do set "STEAM=%%b"
if defined STEAM set "STEAM=%STEAM:/=\%"
set "FORRAS=%STEAM%\steamapps\common\DayZServer"

if not exist "%FORRAS%\DayZServer_x64.exe" (
    echo  Nem talalom a DayZ Servert itt: %FORRAS%
    echo  Steamben: jobb klikk a DayZ Serveren - Kezeles - Helyi fajlok tallozasa,
    echo  masold ki a cimsorbol az utvonalat, es illeszd be ide ^(jobb klikk^), majd Enter:
    set /p "FORRAS=> "
)
if not exist "%FORRAS%\DayZServer_x64.exe" (
    echo.
    echo  Ott sincs DayZServer_x64.exe. Telepitsd a DayZ Servert a Steambol, es futtasd ujra.
    pause
    exit /b 1
)

echo  Masolas innen: %FORRAS%
echo  ^(elso alkalommal par perc, kb. 3 GB^)
echo.
robocopy "%FORRAS%" "%~dp0." /E /NFL /NDL /NJH /NP /XF serverDZ.cfg inditas.bat frissites.bat README.txt /XD profiles storage_1
if %errorlevel% geq 8 (
    echo.
    echo  Hiba tortent a masolas kozben. Zard be a szervert, ha fut, es probald ujra.
    pause
    exit /b 1
)
echo.
echo  Kesz! Inditas: inditas.bat
pause
