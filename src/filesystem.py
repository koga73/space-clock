import os
import json

FILE_BOOT = "boot.txt"
FILE_SETTINGS = "settings.txt"
FILE_WIFI = "wifi.txt"

# region BOOT
def boot_write(mode):
    _write(FILE_BOOT, {
        "mode": mode
    })

def boot_read():
    boot = _read(FILE_BOOT)
    if (boot == None):
        return None
    else:
        return boot["mode"]
# endregion

# region SETTINGS
def settings_write(format_24hr, timezone, daylight_savings):
    _write(FILE_SETTINGS, {
        "format_24hr": format_24hr,
        "tz":timezone,
        "dst":daylight_savings
    })

def settings_read():
    settings = _read(FILE_SETTINGS)
    if (settings == None):
        return None, None, None
    else:
        return settings["format_24hr"], settings["tz"], settings["dst"]
# endregion

# region WIFI
def wifi_write(ssid, password):
    wifi = {
        "ssid": ssid,
        "password": password
    }
    print("\n", wifi)
    with open("wifi.txt", "w") as f:
        f.write(json.dumps(wifi))

def wifi_read():
    try:
        with open("wifi.txt", "r") as f:
            data = f.read()
        print("wifi.txt", data)
        wifi = json.loads(data)
        return wifi["ssid"], wifi["password"]
    except OSError as err:
        print('not found "wifi.txt"')
        return None, None
# endregion

def delete_all():
    _delete(FILE_BOOT)
    _delete(FILE_SETTINGS)
    _delete(FILE_WIFI)

# region INTERNAL
def _write(file, data):
    print(f"\n{file}", data)
    with open(file, "w") as f:
        f.write(json.dumps(data))

def _read(file):
    try:
        with open(file, "r") as f:
            data = f.read()
        print(file, data)
        return json.loads(data)
    except OSError as err:
        print(f'not found "{file}"')
        return None

def _delete(file):
    try:
        os.remove(file)
        print(f'deleted "{file}"')
    except OSError as err:
        print(f'not found "{file}"')
# endregion
