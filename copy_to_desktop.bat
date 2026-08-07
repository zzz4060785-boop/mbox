@echo off
copy "%~dp0android\app\build\outputs\apk\release\app-release.apk" "%USERPROFILE%\Desktop\Friendary_app.apk" /Y
copy "%~dp0android\app\build\outputs\bundle\release\app-release.aab" "%USERPROFILE%\Desktop\Friendary_app.aab" /Y
echo.
echo ========================================================
echo SUCCESS! Both APK and AAB copied to Windows Desktop!
echo File on Desktop: Friendary_app.aab
echo ========================================================
explorer "%USERPROFILE%\Desktop"
pause
