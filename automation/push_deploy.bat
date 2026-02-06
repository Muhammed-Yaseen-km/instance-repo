@echo off
REM Push changes and trigger deploy on machine
REM Usage: push_deploy.bat [commit message]

setlocal

REM === CONFIG ===
set DEPLOY_URL=https://far-hindu-passed-vbulletin.trycloudflare.com/deploy
set DEPLOY_SECRET=inference-deploy-2024
REM ===============

cd /d D:\projects\inference_engine

if "%~1"=="" (
    set MSG=update
) else (
    set MSG=%*
)

echo.
echo === Pushing to GitHub ===
git add .
git commit -m "%MSG%"
git push origin main

if %ERRORLEVEL% NEQ 0 (
    echo Push failed!
    pause
    exit /b 1
)

echo.
echo === Triggering deploy on machine ===
curl -s -X POST -H "X-Deploy-Secret: %DEPLOY_SECRET%" "%DEPLOY_URL%"

echo.
echo.
echo === DONE! Changes will be live in ~30 seconds ===
pause
