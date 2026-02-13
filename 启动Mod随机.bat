@echo off
chcp 65001 >nul
cd /d "%~dp0"

REM 检查 Python 3.8+
where python >nul 2>&1
if %errorlevel% neq 0 (
    echo ❌ 未检测到 Python，请先安装 Python 3.8+
    echo.
    echo 推荐安装方式：
    echo 1. Microsoft Store 搜索 "Python 3.11" 安装（最简单，免费）
    echo 2. 或访问 https://www.python.org/downloads/ 下载安装
    echo.
    echo 安装时务必勾选 "Add Python to PATH" 选项！
    echo.
    pause
    exit /b 1
)

REM 检查脚本
if not exist "mod_randomizer.py" (
    echo ❌ 未找到 mod_randomizer.py
    pause
    exit /b 1
)

echo 正在启动 Mod 随机选择器 v4.1（手动分组优先版）...
echo 请稍候...
python mod_randomizer.py
pause