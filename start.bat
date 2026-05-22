@echo off

chcp 65001 >nul

title 视频服务

cd /d "%~dp0"



if not exist "%~dp0ComfyUI\main.py" (

  echo.

  echo  [错误] 缺少 ComfyUI 文件夹: %~dp0ComfyUI\

  echo  请把引擎放在本目录下的 ComfyUI 文件夹里。

  echo.

  pause

  exit /b 1

)



echo.

echo  ========================================

echo    视频服务 - 源码启动

echo  ========================================

echo.

echo   文生视频: http://127.0.0.1:8080/v1/video

echo   示例 JSON: {"prompt":"一只猫在海边"}

echo.



set PY=python

if not "%VIDEO_SERVICE_PYTHON%"=="" set PY=%VIDEO_SERVICE_PYTHON%



if "%~1"=="" (

  %PY% run.py

) else (

  %PY% run.py -m "%~1"

)



if errorlevel 1 (

  echo.

  echo 启动失败，请看上面报错（常见原因：缺模型文件，见 MODELS.md）。

  pause

)

