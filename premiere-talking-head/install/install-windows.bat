@echo off
REM Installs the Talking Head Toolkit panel for the current user (Windows).
setlocal

set "SRC=%~dp0.."
set "DEST=%APPDATA%\Adobe\CEP\extensions\com.talkingheadtoolkit.panel"

if exist "%DEST%" rmdir /s /q "%DEST%"
xcopy "%SRC%" "%DEST%\" /e /i /q >nul
if exist "%DEST%\install" rmdir /s /q "%DEST%\install"

REM Allow unsigned (debug) extensions for the CSXS runtimes recent Premiere
REM versions use. Harmless if a version isn't installed.
for %%v in (9 10 11 12) do (
  reg add "HKCU\Software\Adobe\CSXS.%%v" /v PlayerDebugMode /t REG_SZ /d 1 /f >nul
)

echo Installed to: %DEST%
echo Restart Premiere Pro, then open Window ^> Extensions ^> Talking Head Toolkit.
endlocal
