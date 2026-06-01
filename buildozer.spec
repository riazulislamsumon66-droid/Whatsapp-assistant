[app]
title = Maya Assistant
package.name = mayaassistant
package.domain = com.maya.assistant
source.dir = .
source.include_exts = py,png,jpg,kv,atlas,json,txt,ttf,otf
version = 1.0.0
requirements = python3,requests,pillow,flet
orientation = portrait
fullscreen = 0
android.permissions = INTERNET,ACCESS_NETWORK_STATE,FOREGROUND_SERVICE,WAKE_LOCK
android.api = 34
android.minapi = 21
android.archs = arm64-v8a
android.allow_backup = True
android.logcat_filters = *:S python:D

[buildozer]
log_level = 2
warn_on_root = 0
