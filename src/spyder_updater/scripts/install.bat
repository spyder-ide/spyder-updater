@echo off
rem This script updates or installs a new version of Spyder

rem Create variables from arguments
:parse
IF "%~1"=="" GOTO endparse
IF "%~1"=="-i" set install_file=%~2& SHIFT
IF "%~1"=="-c" set conda=%~2& SHIFT
IF "%~1"=="-p" set prefix=%~2& SHIFT
If "%~1"=="-r" set rebuild=true
if "%~1"=="-s" set start_spyder=true

SHIFT
GOTO parse
:endparse

rem Enforce encoding
chcp 65001>nul

call :wait_for_spyder_quit
call :update_spyder
if "%start_spyder%"=="true" call :launch_spyder

:exit
    exit %ERRORLEVEL%

:wait_for_spyder_quit
    echo Waiting for Spyder to quit...
    :loop
    tasklist /v /fi "ImageName eq pythonw.exe" /fo csv 2>NUL | find "Spyder">NUL
    IF "%ERRORLEVEL%"=="0" (
        timeout /t 1 /nobreak > nul
        goto loop
    )
    echo Spyder has quit.
    goto :EOF

:update_spyder
    for %%C in ("%install_file%") do set installer_dir=%%~dpC
    pushd %installer_dir%

    echo Updating Spyder base environment...
    %conda% update --name base --yes --file conda-base-win-64.lock

    if "%rebuild%"=="true" (
        echo Rebuilding Spyder runtime environment...
        %conda% remove --prefix %prefix% --all --yes
        mkdir %prefix%\Menu
        echo. > "%prefix%\Menu\conda-based-app"
        set conda_cmd=create
    ) else (
        echo Updating Spyder runtime environment...
        set conda_cmd=update
    )
    %conda% %conda_cmd% --prefix %prefix% --yes --file conda-runtime-win-64.lock

    echo Cleaning packages and temporary files...
    %conda% clean --yes --packages --tempfiles %prefix%
    goto :EOF

:launch_spyder
    for %%C in ("%conda%") do set scripts=%%~dpC
    set pythonexe=%scripts%..\python.exe
    set menuinst=%scripts%menuinst_cli.py
    if exist "%prefix%\.nonadmin" (set mode=user) else set mode=system
    for /f "delims=" %%s in ('%pythonexe% %menuinst% shortcut --mode=%mode%') do set "shortcut_path=%%~s"

    start "" /B "%shortcut_path%"
    goto :EOF
