#!/usr/bin/env python3
"""Re-apply ADB switch mapping and audit logging after an upstream merge."""

from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[1]
UTILS = ROOT / "module" / "utils.sh"
CONFIG = ROOT / "module" / "config.sh"
WEBUI_HTML = ROOT / "module" / "webroot" / "index.html"

OLD_USB = '''\tresetprop_n "init.svc.adbd" "stopped"
\tresetprop_n "init.svc_debug_pid.adbd" ""
\tresetprop_n "persist.sys.usb.config" "mtp"
'''
NEW_USB = '''\tif [[ "${config_usb_debugging}" == "1" ]]; then
\t\tadb_spoof_log "usb=preserve init=$(getprop init.svc.adbd) usb=$(getprop sys.usb.config)"
\telse
\t\tadb_spoof_log "usb=spoof before init=$(getprop init.svc.adbd) usb=$(getprop persist.sys.usb.config)"
\t\tresetprop_n "init.svc.adbd" "stopped"
\t\tresetprop_n "init.svc_debug_pid.adbd" ""
\t\tresetprop_n "persist.sys.usb.config" "mtp"
\t\tadb_spoof_log "usb=spoof after init=$(getprop init.svc.adbd) usb=$(getprop persist.sys.usb.config)"
\tfi

\tif [[ "${config_wireless_debugging}" == "1" ]]; then
\t\tadb_spoof_log "wireless=preserve tls=$(getprop service.adb.tls.port)"
\telse
\t\tadb_spoof_log "wireless=spoof before tls=$(getprop service.adb.tls.port)"
\t\tresetprop -d "service.adb.tcp.port"
\t\tadb_spoof_log "wireless=spoof after tls=$(getprop service.adb.tls.port)"
\tfi
'''
RESET_PROP = '''resetprop_n() {
\tresetprop -n "$1" "$2"
}
'''
RESET_PROP_WITH_LOG = '''resetprop_n() {
\tresetprop -n "$1" "$2"
}

adb_spoof_log() {
\t[[ "${config_brene_logs}" == "1" ]] || return
\techo "[$(date '+%Y-%m-%d %H:%M:%S')] [ADB] $*" >> "${PERSISTENT_DIR}/logs.txt"
}
'''
OLD_ADB = '''\tresetprop -d service.adb.root
\tresetprop -d service.adb.tcp.port
'''
OLD_USB_SUBTITLE = "Enable or disable USB debugging"
NEW_USB_SUBTITLE = "Off spoofs USB ADB state as stopped"
OLD_WIRELESS_SUBTITLE = "Enable or disable wireless debugging"
NEW_WIRELESS_SUBTITLE = "Off hides the wireless ADB TLS port"


def replace_once(source: str, old: str, new: str, label: str) -> str:
    if new in source:
        return source
    if source.count(old) != 1:
        raise RuntimeError(f"cannot apply {label}: expected exactly one upstream block")
    return source.replace(old, new)


def set_config_default(source: str, name: str, value: int) -> str:
    line = f"{name}={value}"
    if line in source:
        return source
    prefix = f"{name}="
    if source.count(prefix) != 1:
        raise RuntimeError(f"cannot set {name}: expected exactly one config entry")
    start = source.index(prefix)
    end = source.find("\n", start)
    return source[:start] + line + source[end:]


def main() -> None:
    source = UTILS.read_text()
    source = replace_once(source, RESET_PROP, RESET_PROP_WITH_LOG, "ADB audit logger")
    source = replace_once(source, OLD_USB, NEW_USB, "ADB switch mapping")
    source = source.replace(OLD_ADB, "")
    UTILS.write_text(source)

    source = CONFIG.read_text()
    source = set_config_default(source, "config_usb_debugging", 1)
    source = set_config_default(source, "config_wireless_debugging", 1)
    CONFIG.write_text(source)

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
