#!/usr/bin/env python3
"""Re-apply ADB switch mapping and audit logging after an upstream merge.

Designed for upstream BRENE >= v0.0.65 which uses if_prop_exits_resetprop_n
and places ADB/USB props inside spoof_android_system_properties().
"""

from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[1]
UTILS = ROOT / "module" / "utils.sh"
CONFIG = ROOT / "module" / "config.sh"
WEBUI_HTML = ROOT / "module" / "webroot" / "index.html"

# --- utils.sh anchors (upstream v0.0.65) ---

UPSTREAM_RESETPROP_N = '''\tresetprop -n "$1" "$2"
}'''

FORK_RESETPROP_N_WITH_LOG = '''\tresetprop -n "$1" "$2"
}

adb_spoof_log() {
\t[[ "${config_brene_logs}" == "1" ]] || return
\techo "[$(date '+%Y-%m-%d %H:%M:%S')] [ADB] $*" >> "${PERSISTENT_DIR}/logs.txt"
}'''

# Upstream hardcodes these three ADB/USB props unconditionally.
# The fork replaces them with conditional blocks gated on config switches.
UPSTREAM_ADB_PROPS = '''\tif_prop_exits_resetprop_n "ro.adb.secure" "1"
\tif_prop_exits_resetprop_n "persist.sys.usb.config" "mtp"
\tif_prop_exits_resetprop_n "ro.boot.verifiedbootstate" "green"'''

FORK_ADB_PROPS = '''\tif_prop_exits_resetprop_n "ro.adb.secure" "1"
\tif_prop_exits_resetprop_n "ro.boot.verifiedbootstate" "green"'''

UPSTREAM_INIT_SVC = '''\tif_prop_exits_resetprop_n "init.svc.adbd" "stopped"
\tif_prop_exits_resetprop_n "init.svc_debug_pid.adbd" ""
\t# if_prop_exits_resetprop_n "ro.oem_unlock_supported" "0"'''

FORK_CONDITIONAL_ADB = '''\t# ADB/USB lifecycle props are conditional on debug switches.
\t# Android's USB framework and Gadget HAL must remain the sole owner
\t# of adbd and FunctionFS state when debugging is enabled.
\tif [[ "${config_usb_debugging}" == "1" ]]; then
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

\t# if_prop_exits_resetprop_n "ro.oem_unlock_supported" "0"'''

UPSTREAM_ADB_DELETE = '''\tresetprop -d "service.adb.root"
\tresetprop -d "service.adb.tcp.port"'''

FORK_ADB_DELETE_COMMENT = '''\t# service.adb.root and service.adb.tcp.port are handled by the
\t# conditional wireless debugging block above.'''

# --- webroot/index.html anchors ---

OLD_USB_SUBTITLE = "Enable or disable USB debugging"
NEW_USB_SUBTITLE = "Off spoofs USB ADB state as stopped"
OLD_WIRELESS_SUBTITLE = "Enable or disable wireless debugging"
NEW_WIRELESS_SUBTITLE = "Off hides the wireless ADB TLS port"


def replace_once(source: str, old: str, new: str, label: str) -> str:
    """Replace exactly one occurrence. Skip if already applied."""
    if new in source:
        return source
    count = source.count(old)
    if count != 1:
        raise RuntimeError(
            f"cannot apply {label}: expected exactly one match, found {count}"
        )
    return source.replace(old, new)


def set_config_default(source: str, name: str, value: int) -> str:
    """Set a config key to a specific value. Idempotent."""
    target_line = f"{name}={value}"
    if target_line in source:
        return source
    prefix = f"{name}="
    lines = source.split("\n")
    for i, line in enumerate(lines):
        if line.startswith(prefix):
            lines[i] = target_line
            return "\n".join(lines)
    raise RuntimeError(f"cannot set {name}: key not found in config")


def main() -> None:
    # --- utils.sh ---
    source = UTILS.read_text()
    source = replace_once(source, UPSTREAM_RESETPROP_N, FORK_RESETPROP_N_WITH_LOG, "ADB audit logger")
    source = replace_once(source, UPSTREAM_ADB_PROPS, FORK_ADB_PROPS, "remove hardcoded persist.sys.usb.config")
    source = replace_once(source, UPSTREAM_INIT_SVC, FORK_CONDITIONAL_ADB, "ADB switch mapping")
    source = replace_once(source, UPSTREAM_ADB_DELETE, FORK_ADB_DELETE_COMMENT, "remove unconditional service.adb deletions")
    UTILS.write_text(source)

    # --- config.sh ---
    source = CONFIG.read_text()
    source = set_config_default(source, "config_usb_debugging", 1)
    source = set_config_default(source, "config_wireless_debugging", 1)
    CONFIG.write_text(source)

    # --- webroot/index.html ---
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
