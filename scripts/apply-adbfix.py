#!/usr/bin/env python3
"""Re-apply the fork's ADB switch mapping after an upstream merge."""

from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[1]
UTILS = ROOT / "module" / "utils.sh"
WEBUI = ROOT / "module" / "webroot" / "script.js"
WEBUI_HTML = ROOT / "module" / "webroot" / "index.html"

OLD_USB = '''\tresetprop_n "init.svc.adbd" "stopped"
\tresetprop_n "init.svc_debug_pid.adbd" ""
\tresetprop_n "persist.sys.usb.config" "mtp"
'''
NEW_USB = '''\t# Keep USB ADB's service state and function configuration real when the
\t# Android Settings USB Debugging switch is enabled.
\tif [[ "${config_usb_debugging}" != "1" ]]; then
\t\tresetprop_n "init.svc.adbd" "stopped"
\t\tresetprop_n "init.svc_debug_pid.adbd" ""
\t\tresetprop_n "persist.sys.usb.config" "mtp"
\tfi
'''
OLD_ADB = '''\tresetprop -d service.adb.root
\tresetprop -d service.adb.tcp.port
'''
NEW_ADB = '''\tresetprop -d service.adb.root

\t# Preserve the wireless TLS port while the Android Settings Wireless
\t# Debugging switch is enabled.
\tif [[ "${config_wireless_debugging}" != "1" ]]; then
\t\tresetprop -d service.adb.tcp.port
\tfi
'''
OLD_USB_ACTION = '''\t{
\t\tid: 'usb_debugging',
\t\taction: (enabled) => setFeature(`settings put global adb_enabled ${enabled ? 1 : 0}`),
\t},
'''
NEW_USB_ACTION = '''\t{
\t\tid: 'usb_debugging',
\t\taction: (enabled) =>
\t\t\tsetFeature(
\t\t\t\tenabled
\t\t\t\t\t? 'settings put global adb_enabled 1; resetprop -d init.svc.adbd; resetprop -d init.svc_debug_pid.adbd; resetprop -d persist.sys.usb.config; setprop persist.sys.usb.config mtp,adb; setprop sys.usb.config mtp,adb; svc usb resetUsbGadget'
\t\t\t\t\t: 'settings put global adb_enabled 0; resetprop -n init.svc.adbd stopped; resetprop -n init.svc_debug_pid.adbd ""; resetprop -n persist.sys.usb.config mtp',
\t\t\t),
\t},
'''
OLD_WIRELESS_ACTION = '''\t{
\t\tid: 'wireless_debugging',
\t\taction: (enabled) => setFeature(`settings put global adb_wifi_enabled ${enabled ? 1 : 0}`),
\t},
'''
NEW_WIRELESS_ACTION = '''\t{
\t\tid: 'wireless_debugging',
\t\taction: (enabled) =>
\t\t\tsetFeature(
\t\t\t\tenabled
\t\t\t\t\t? 'settings put global adb_wifi_enabled 1'
\t\t\t\t\t: 'settings put global adb_wifi_enabled 0; resetprop -d service.adb.tcp.port',
\t\t\t),
\t},
'''
OLD_USB_SUBTITLE = "Enable or disable USB debugging"
NEW_USB_SUBTITLE = "Also preserves USB ADB from system property spoofing"
OLD_WIRELESS_SUBTITLE = "Enable or disable wireless debugging"
NEW_WIRELESS_SUBTITLE = "Also preserves the wireless ADB TLS port from spoofing"


def replace_once(source: str, old: str, new: str, label: str) -> str:
    if new in source:
        return source
    if source.count(old) != 1:
        raise RuntimeError(f"cannot apply {label}: expected exactly one upstream block")
    return source.replace(old, new)


def main() -> None:
    source = UTILS.read_text()
    source = replace_once(source, OLD_USB, NEW_USB, "USB Debugging mapping")
    source = replace_once(source, OLD_ADB, NEW_ADB, "Wireless Debugging mapping")
    UTILS.write_text(source)

    source = WEBUI.read_text()
    source = replace_once(source, OLD_USB_ACTION, NEW_USB_ACTION, "USB Debugging UI action")
    source = replace_once(
        source,
        OLD_WIRELESS_ACTION,
        NEW_WIRELESS_ACTION,
        "Wireless Debugging UI action",
    )
    WEBUI.write_text(source)

    source = WEBUI_HTML.read_text()
    source = replace_once(source, OLD_USB_SUBTITLE, NEW_USB_SUBTITLE, "USB Debugging subtitle")
    source = replace_once(
        source,
        OLD_WIRELESS_SUBTITLE,
        NEW_WIRELESS_SUBTITLE,
        "Wireless Debugging subtitle",
    )
    WEBUI_HTML.write_text(source)


if __name__ == "__main__":
    try:
        main()
    except Exception as error:
        print(f"adbfix: {error}", file=sys.stderr)
        sys.exit(1)
