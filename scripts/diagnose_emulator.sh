#!/usr/bin/env bash
# Installs the diagnostic APK on the running emulator, launches the app,
# and dumps the crash-relevant logcat. Run as a real script file (not
# inline in the workflow YAML) because reactivecircus/android-emulator-
# runner's `script:` input executes each line as a separate shell
# invocation - a variable set on one line does not survive to the next.
set -uo pipefail

APK=$(ls apk/*.apk | head -n1)
echo "Installing: $APK"
adb install -r "$APK"

adb logcat -c

echo "Launching org.salesrepository.salesrepository/org.kivy.android.PythonActivity"
adb shell am start -n org.salesrepository.salesrepository/org.kivy.android.PythonActivity

sleep 20

echo "===== is the process still alive? ====="
adb shell pidof org.salesrepository.salesrepository || echo "PROCESS NOT RUNNING (crashed or never started)"

echo "===== relevant logcat (python / crash / app package) ====="
adb logcat -d | grep -iE "python|AndroidRuntime|FATAL|Traceback|salesrepository|pyjnius" || echo "(no matching lines)"

echo "===== full logcat tail (last 400 lines, for context) ====="
adb logcat -d | tail -n 400
