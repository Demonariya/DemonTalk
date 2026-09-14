[app]

title = DemonTalk
package.name = demontalk
package.domain = com.demontalk

source.dir = .
source.include_exts = py,png,jpg,kv,atlas,json,ttf,ogg,wav

version = 1.0.0

requirements = python3,kivy,kivymd,pyjnius,cryptography,zeroconf,sqlite3

orientation = portrait
fullscreen = 0
android.permissions = INTERNET,ACCESS_WIFI_STATE,CHANGE_WIFI_STATE,ACCESS_NETWORK_STATE,RECORD_AUDIO,MODIFY_AUDIO_SETTINGS,WAKE_LOCK,ACCESS_FINE_LOCATION,ACCESS_COARSE_LOCATION,CHANGE_NETWORK_STATE,ACCESS_BACKGROUND_LOCATION,FOREGROUND_SERVICE,POST_NOTIFICATIONS

android.api = 33
android.minapi = 24
android.ndk = 25b
android.sdk = 33
android.accept_sdk_license = True
android.arch = arm64-v8a

android.release_artifact = aab
android.debug_artifact = apk

android.add_compile_options = sourceCompatibility=Version_11,targetCompatibility=Version_11

android.gradle_dependencies = com.google.android.material:material:1.9.0

android.uses_permissions = android.permission.INTERNET,android.permission.ACCESS_WIFI_STATE,android.permission.CHANGE_WIFI_STATE,android.permission.ACCESS_NETWORK_STATE,android.permission.RECORD_AUDIO,android.permission.MODIFY_AUDIO_SETTINGS,android.permission.WAKE_LOCK,android.permission.ACCESS_FINE_LOCATION,android.permission.ACCESS_COARSE_LOCATION,android.permission.CHANGE_NETWORK_STATE,android.permission.FOREGROUND_SERVICE,android.permission.POST_NOTIFICATIONS

android服务 org.kivy.android.PythonService
android.service_foreground_service_type = microphone

# P4A recipe configs
p4a.branch = develop

[buildozer]
log_level = 2
warn_on_root = 0
