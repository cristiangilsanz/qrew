#!/bin/bash
# syncs and launches the app on a connected android phone
set -e
ADB="/mnt/c/Users/Cristian/AppData/Local/Android/Sdk/platform-tools/adb.exe"
SERIAL="CESOAA99UKONEY9H"

echo "Setting up adb reverse tunnel..."
$ADB -s $SERIAL reverse tcp:5173 tcp:5173

echo "Syncing Capacitor..."
cd "$(dirname "$0")/../apps/app"
ANDROID_HOME=/mnt/c/Users/Cristian/AppData/Local/Android/Sdk npx cap sync android

echo "Building and installing APK..."
cmd.exe /c "cd /d C:\Users\Cristian\Desktop\qrew\apps\app\android && gradlew.bat installDebug"

echo "Launching app..."
$ADB -s $SERIAL shell am start -n com.qrew.app/com.qrew.app.MainActivity

echo "Done! App is running on phone."
