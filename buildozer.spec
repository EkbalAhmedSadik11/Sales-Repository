[app]

title = Sales Repository
package.name = salesrepository
package.domain = org.salesrepository

source.dir = .
source.include_exts = py,png,jpg,kv,atlas,ttf,db
source.exclude_dirs = tests,bin,.buildozer,.git,data,exports,backups
source.exclude_patterns = *.pyc,*.pyo

version = 1.0.0

# python3, kivy, kivymd for the UI; sqlite3 is explicit so python-for-android
# always includes the stdlib sqlite3 recipe in the build.
requirements = python3,kivy==2.2.1,kivymd==1.1.1,sqlite3,pillow

orientation = portrait
fullscreen = 0

icon.filename = %(source.dir)s/assets/icons/icon.png
presplash.filename = %(source.dir)s/assets/images/presplash.png

# ----------------------------------------------------------------------
# Android
# ----------------------------------------------------------------------

android.permissions = INTERNET

# The app stores its database in the Android-private app data directory
# (App.user_data_dir), which needs no storage permission and is not lost
# on app updates - only on uninstall. No external-storage permission is
# requested since the app never needs to write outside its own sandbox.

android.api = 33
android.minapi = 21
android.ndk = 25b
android.archs = arm64-v8a,armeabi-v7a
android.allow_backup = True

[buildozer]

log_level = 2
warn_on_root = 1
