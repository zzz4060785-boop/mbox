@echo off
chcp 65001 > nul
echo Building new fixed Android APK and AAB...
cd /d "%~dp0android"
call gradlew.bat clean assembleRelease bundleRelease
if %ERRORLEVEL% EQU 0 (
    copy "%~dp0android\app\build\outputs\bundle\release\app-release.aab" "%USERPROFILE%\Desktop\Friendary_app.aab" /Y
    copy "%~dp0android\app\build\outputs\apk\release\app-release.apk" "%USERPROFILE%\Desktop\Friendary_app.apk" /Y
    copy "%~dp0android\app\build\outputs\apk\release\app-release.apk" "%~dp0pybo\static\Friendary_app.apk" /Y
    echo.
    echo ========================================================
    echo SUCCESS! AAB and APK Built Successfully!
    echo Desktop File: Friendary_app.aab
    echo ========================================================
    explorer "%~dp0android\app\build\outputs\bundle\release"
)
pause
