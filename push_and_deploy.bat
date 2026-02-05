@echo off
REM Push local changes and deploy to AWS instance
REM Usage: push_and_deploy.bat [commit message]
REM Example: push_and_deploy.bat "fix api bug"

setlocal

REM === CONFIGURE THESE ===
set INSTANCE_IP=YOUR_INSTANCE_IP_HERE
set KEY_PATH=C:\Users\Yaseen\Downloads\llama-spot.pem
REM =======================

if "%~1"=="" (
    set MSG=update
) else (
    set MSG=%~1
)

echo === Pushing to GitHub ===
git add .
git commit -m "%MSG%"
git push

echo.
echo === Deploying to AWS Instance ===
ssh -i "%KEY_PATH%" -o StrictHostKeyChecking=no ubuntu@%INSTANCE_IP% "cd ~/inference_engine && git pull && sudo docker-compose up -d --build && sudo docker-compose logs --tail=20"

echo.
echo === Done! ===
pause
