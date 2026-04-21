@echo off
chcp 65001 >nul
echo ========================================
echo    微信群助手 - 打包工具
echo ========================================
echo.

echo 正在打包，请稍候...
echo.

pyinstaller ^
    --onefile ^
    --windowed ^
    --name "微信群助手" ^
    --icon=icon.ico ^
    --add-data "config.py;." ^
    --add-data "database.py;." ^
    --add-data "wechat.py;." ^
    --add-data "config.py;." ^
    main.py

echo.
echo ========================================
if exist "dist\微信群助手.exe" (
    echo    打包成功！
    echo    输出文件: dist\微信群助手.exe
) else (
    echo    打包失败，请检查错误信息
)
echo ========================================
echo.
pause
