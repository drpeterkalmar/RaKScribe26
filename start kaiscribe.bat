@echo off
echo Starting KaiScribe in Python Mode...
echo.
echo Check list:
echo 1. Is Ollama running (if using offline mode)?
echo 2. Is your NVIDIA GPU driver up to date?
echo.
python source_code\RaKScribe.py
if %ERRORLEVEL% NEQ 0 (
    echo.
    echo [ERROR] KaiScribe exited with an error. 
    echo Please make sure all dependencies are installed (pip install -r requirements.txt).
    pause
)
pause
