@echo off
chcp 65001 >nul 2>&1
title 金融市场信息聚合系统

echo ============================================================
echo   金融市场信息聚合系统 启动脚本
echo ============================================================
echo.

:: 检查 Python 是否安装
where python >nul 2>&1
if %errorlevel% neq 0 (
    echo  [错误] 未检测到 Python，请先安装 Python 3.8+
    echo  下载地址: https://www.python.org/downloads/
    pause
    exit /b 1
)

echo  [1/3] 检查 Python 环境...
python --version
echo.

:: 进入项目目录
cd /d "%~dp0"

:: 检查是否需要安装依赖
echo  [2/3] 检查依赖包...
python -c "import flask, requests, bs4, lxml" 2>nul
if %errorlevel% neq 0 (
    echo  正在安装依赖包...
    pip install -r requirements.txt
    if %errorlevel% neq 0 (
        echo  [错误] 依赖安装失败，请检查网络连接
        pause
        exit /b 1
    )
    echo  依赖安装完成!
) else (
    echo  依赖包已安装.
)
echo.

:: 启动应用
echo  [3/3] 启动应用...
echo.
echo  >>> 浏览器访问: http://127.0.0.1:5000 <<<
echo  >>> 按 Ctrl+C 停止 <<<
echo.
python app.py

pause
