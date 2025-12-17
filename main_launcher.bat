@echo off
setlocal
cd /d "%~dp0"

start "" powershell.exe -NoExit -ExecutionPolicy Bypass -Command "& { Set-Location -LiteralPath '%CD%'; & '.\torch_env\Scripts\Activate.ps1'; python .\project\supervision_handler\run.py }"
start "" powershell.exe -NoExit -ExecutionPolicy Bypass -Command "& { Set-Location -LiteralPath '%CD%'; & '.\torch_env\Scripts\Activate.ps1'; python .\project\workflow\detector\simulator\simulator_with_cycle_error.py }"
start "" powershell.exe -NoExit -ExecutionPolicy Bypass -Command "& { Set-Location -LiteralPath '%CD%'; & '.\torch_env\Scripts\Activate.ps1'; python .\project\workflow\detector\launch_schedule_detector.py }"

start "" cmd /k "cd ui-chatbox\auto-pilot && npm run dev"
exit
