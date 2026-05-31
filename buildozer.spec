[app]
title = WhatsApp Assistant
package.name = whatsappassistant
package.domain = com.assistant
source.dir = .
source.include_exts = py,png,jpg,kv,atlas,json,txt
version = 1.0.0
requirements = python3,requests,flet,pillow,urllib3,charset_normalizer,certifi,idna
orientation = portrait
fullscreen = 0
android.permissions = INTERNET,ACCESS_NETWORK_STATE,FOREGROUND_SERVICE,WAKE_LOCK
android.api = 33
android.minapi = 21
android.arch = arm64-v8a
android.allow_backup = True
android.logcat_filters = *:S python:D
p4a.local_recipes = 
ios.kivy_ios_url = https://github.com/kivy/kivy-ios
ios.kivy_ios_branch = master
ios.ios_deploy_url = https://github.com/phonegap/ios-deploy
ios.ios_deploy_branch = 1.10.0
[buildozer]
log_level = 2
warn_on_root = 1
