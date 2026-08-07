@echo off
echo Packaging APK as ZIP for KakaoTalk...
powershell -Command "Compress-Archive -Path '%~dp0android\app\build\outputs\apk\release\app-release.apk' -DestinationPath '%USERPROFILE%\Desktop\Friendary_app.zip' -Force"
echo.
echo ========================================================
echo SUCCESS! Created Friendary_app.zip on Desktop!
echo Now send Friendary_app.zip via KakaoTalk!
echo ========================================================
explorer "%USERPROFILE%\Desktop"
pause
