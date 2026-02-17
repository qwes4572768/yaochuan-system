@echo off
cd /d "%~dp0"
if not exist "啟動器\一鍵啟動（前後端）.bat" (
    echo [錯誤] 找不到：啟動器\一鍵啟動（前後端）.bat
    echo 請確認本檔放在專案根目錄，與「啟動器」資料夾同一層。
    pause
    exit /b 1
)
call "啟動器\一鍵啟動（前後端）.bat"
if errorlevel 1 (
    echo.
    echo 啟動過程發生錯誤，請查看上方訊息。
    pause
    exit /b 1
)
