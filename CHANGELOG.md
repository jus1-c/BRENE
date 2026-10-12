# Changelog

# Supports SuSFS 2.2.0 and 2.3.0+

- improve: Spoof /system/etc/hosts: use open_redirect to spoof it as a stock hosts file
- improve: simplify "Reset fake_files folder" code
- fix: set ro.crypto.state after boot completed to preserve vendor crypto transition triggers (#61)
- add: webui: UID Filter module
- Merge branch 'main' of https://github.com/rrr333nnn333/BRENE
- improve: webui: add some useful links to Recommended Modules
- change: webui: move "Spoof /system/etc/hosts" to Custom ROM section
- change: disable some options by default
- change: webui: move "Custom Spoof Uname" to SuSFS section
- improve: webui: add example for OPEN_REDIRECT and replace "/storage/emulated/0" with "/sdcard"
- add: "Set logcat and logd buffer to 64K" toggle

- fork: sync v0.0.71 as v0.0.71-adbfix
