@echo off
title DayZ szerver - Loot Goblinok
cd /d "%~dp0"

rem Modok helye (most ures = vanilla). Kesobb pl.: set MODOK=@CF;@VPPAdminTools
set MODOK=

:start
echo [%date% %time%] Szerver indul...
if "%MODOK%"=="" (
    DayZServer_x64.exe -config=serverDZ.cfg -port=2302 -profiles=profiles -dologs -adminlog -netlog -freezecheck
) else (
    DayZServer_x64.exe -config=serverDZ.cfg -port=2302 -profiles=profiles -dologs -adminlog -netlog -freezecheck "-mod=%MODOK%"
)
echo [%date% %time%] A szerver leallt. Ujrainditas 10 masodperc mulva. Bezarashoz: zard be ezt az ablakot.
timeout /t 10
goto start
