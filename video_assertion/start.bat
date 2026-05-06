@echo off
REM One-click launcher for the video-assertion service (Windows).
setlocal enableextensions

cd /d "%~dp0"

if exist .env (
  for /f "usebackq tokens=1,* delims==" %%A in (".env") do (
    if not "%%A"=="" set "%%A=%%B"
  )
)

if "%DOUBAO_API_KEY%"=="" (
  echo [start] ERROR: DOUBAO_API_KEY is not set.
  echo   set DOUBAO_API_KEY=ark-xxxxxxxx
  echo   set DOUBAO_MODEL_ENDPOINT=doubao-seed-2-0-pro-260215
  exit /b 1
)

set "PY=%PYTHON%"
if "%PY%"=="" set "PY=python"

%PY% -c "import fastapi, uvicorn, video_assertion" >nul 2>&1
if errorlevel 1 (
  echo [start] installing Python dependencies (one-time)
  %PY% -m pip install -e .
)

if "%VA_HOST%"=="" set "VA_HOST=0.0.0.0"
if "%VA_PORT%"=="" set "VA_PORT=8000"
if "%VA_RUNS_DIR%"=="" set "VA_RUNS_DIR=runs"
if not exist "%VA_RUNS_DIR%" mkdir "%VA_RUNS_DIR%"

echo ================================================================
echo  video-assertion service starting
echo    Frontend  ^>  http://localhost:%VA_PORT%
echo    Swagger   ^>  http://localhost:%VA_PORT%/docs
echo    ReDoc     ^>  http://localhost:%VA_PORT%/redoc
echo    Health    ^>  http://localhost:%VA_PORT%/api/v1/health
echo ================================================================

%PY% -m uvicorn video_assertion.server.api:app --host %VA_HOST% --port %VA_PORT%
