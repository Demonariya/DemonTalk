[app]

title = DemonTalk
package.name = demontalk
package.domain = com.demontalk

source.dir = .
source.include_exts = py,png,jpg,kv,atlas,json,ttf,ogg,wav,html,css,js

version = 1.0.0

requirements = python3,kivy==2.3.0,sqlite3

orientation = portrait
fullscreen = 0
android.permissions = INTERNET,ACCESS_WIFI_STATE,CHANGE_WIFI_STATE,ACCESS_NETWORK_STATE,RECORD_AUDIO,MODIFY_AUDIO_SETTINGS,WAKE_LOCK,ACCESS_FINE_LOCATION,ACCESS_COARSE_LOCATION,CHANGE_NETWORK_STATE,FOREGROUND_SERVICE,POST_NOTIFICATIONS

android.api = 33
android.minapi = 24
android.ndk = 25b
android.sdk = 33
android.accept_sdk_license = True
android.archs = arm64-v8a

android.release_artifact = apk
android.debug_artifact = apk

android.add_compile_options = sourceCompatibility=Version_11,targetCompatibility=Version_11

android.gradle_dependencies = com.google.android.material:material:1.9.0

android.allow_backup = True

p4a.branch = stable

[buildozer]
log_level = 2
warn_on_root = 0
