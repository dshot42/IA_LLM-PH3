@echo off
setlocal
cd /d "%~dp0"

start "" powershell.exe -NoExit -ExecutionPolicy Bypass -Command "& { Set-Location -LiteralPath '%CD%'; & '..\torch_env\Scripts\Activate.ps1'; python -m supervision_handler.run }"
REM start "" powershell.exe -NoExit -ExecutionPolicy Bypass -Command "& { Set-Location -LiteralPath '%CD%'; & '..\torch_env\Scripts\Activate.ps1'; python -m workflow.detector.simulator.simulator_scenario_nominal_no_error }"
start "" powershell.exe -NoExit -ExecutionPolicy Bypass -Command "& { Set-Location -LiteralPath '%CD%'; & '..\torch_env\Scripts\Activate.ps1'; python -m workflow.detector.simulator.simulator_with_cycle_error }"

REM start "" powershell.exe -NoExit -ExecutionPolicy Bypass -Command "& { Set-Location -LiteralPath '%CD%'; & '..\torch_env\Scripts\Activate.ps1'; python  -m workflow.detector.launch_schedule_detector }"

start "" cmd /k "cd ..\ui-chatbox\auto-pilot && npm run dev"
exit
