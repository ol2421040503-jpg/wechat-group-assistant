@echo off
chcp 65001 >nul
echo ========================================
echo    微信群助手 - 依赖安装
echo ========================================
echo.

echo 正在安装 uiautomation2...
pip install uiautomation2

echo.
echo 正在安装 pyinstaller...
pip install pyinstaller

echo.
echo ========================================
echo    安装完成！
echo ========================================
echo.
echo 运行程序: python main.py
echo 打包程序: pyinstaller --onefile --windowed --name "微信群助手" main.py
echo.
pause
