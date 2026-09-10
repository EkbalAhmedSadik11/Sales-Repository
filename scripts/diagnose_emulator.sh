#!/usr/bin/env bash
# Installs the diagnostic APK on the running emulator, launches the app,
# and dumps the crash-relevant logcat. Run as a real script file (not
# inline in the workflow YAML) because reactivecircus/android-emulator-
# runner's `script:` input executes each line as a separate shell
# invocation - a variable set on one line does not survive to the next.
set -uo pipefail

PKG="org.salesrepository.salesrepository"
ACTIVITY="org.kivy.android.PythonActivity"

APK=$(ls apk/*.apk | head -n1)
echo "Installing: $APK"
adb install -r "$APK"

adb logcat -c

echo "Launching $PKG/$ACTIVITY"
adb shell am start -n "$PKG/$ACTIVITY"

# First run has to unpack the whole Python/Kivy/KivyMD/Pillow bundle
# (hundreds of files) before main.py even starts, which can take well
# over 20s on a CI emulator - a short fixed sleep just catches it
# mid-extraction. System logcat is far too noisy (background OS
# services constantly logging) to detect "things settled down", so
# just poll pidof every 5s for up to 2.5 minutes and stop early only
# if the process actually dies (crash).
MAX_WAIT=150
elapsed=0
while [ "$elapsed" -lt "$MAX_WAIT" ]; do
  sleep 5
  elapsed=$((elapsed + 5))
  if ! adb shell pidof "$PKG" > /dev/null 2>&1; then
    echo "Process exited/crashed after ${elapsed}s"
    break
  fi
  echo "  ...${elapsed}s elapsed, process still alive"
done

echo "===== is the process still alive after ${elapsed}s? ====="
adb shell pidof "$PKG" || echo "PROCESS NOT RUNNING (crashed or never started)"

echo "===== relevant logcat (python / crash / app package) ====="
adb logcat -d | grep -iE "python|AndroidRuntime|FATAL|Traceback|salesrepository|pyjnius" || echo "(no matching lines)"

echo "===== full logcat tail (last 800 lines, for context) ====="
adb logcat -d | tail -n 800
