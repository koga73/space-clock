import binascii
import network
import time
import json

from machine import Pin

led = Pin("LED", Pin.OUT)

MAX_NETWORKS = 10
MAX_RETRIES = 20

# region SCAN
# Scan for networks
def wlan_scan(max_networks = MAX_NETWORKS):
    print("\nwlan_scan")

    # Scan for networks
    wlan = network.WLAN(network.STA_IF)
    wlan.active(True)
    networks = wlan.scan()
    wlan.active(False)

    # Parse networks
    networks = [{
        "ssid": n[0].decode(),
        "bssid": binascii.hexlify(n[1]).decode(),
        "channel": n[2],
        "rssi": n[3],
        "security": n[4],
        "hidden": n[5]
    } for n in networks]
    networks = [n for n in networks if n["ssid"] != ""] # Filter out networks with empty
    networks = networks[:max_networks] # Limit to max networks
    networks.sort(key=lambda n:n["rssi"], reverse=True)

    for n in networks:
        print(n)
    
    return networks
# endregion

# region AP
# Create access point to connect and select wifi network
def wlan_ap(ssid, password = None):
    print("\nwlan_ap")

    # Create access point
    ap = network.WLAN(network.AP_IF)
    ap.active(False)
    ap.ifconfig(("192.168.4.1", "255.255.255.0", "192.168.4.1", "192.168.4.1"))
    
    if (password == None):
        ap.config(essid=ssid, security=0)
    else:
        ap.config(essid=ssid, password=password)
    
    ap.active(True)
    while(ap.active() == False):
        pass
    print(json.dumps({"ssid": ssid, "password": password, "gateway": ap.ifconfig()[0]}))

    return ap
# endregion

# region CONNECT
def wlan_connect(ssid, password):
    print("\nwlan_connect")

    wlan = network.WLAN(network.STA_IF)
    wlan.active(True)
    wlan.connect(ssid, password)

    # Wait for connect or fail
    num_wait = 0
    while num_wait < MAX_RETRIES:
        if (wlan.status() < 0 or wlan.status() >= 3):
            break
        num_wait += 1
        print(f"connecting... ({num_wait}/{MAX_RETRIES})")
        time.sleep(1)

    # Handle connection error
    if (wlan.status() != 3):
        wlan.active(False)
        raise RuntimeError("connection failed")
    else:
        print("connected!")
        status = wlan.ifconfig()
        print(json.dumps({
            "ip": status[0],
            "netmask": status[1],
            "gateway": status[2],
            "dns": status[3]
        }))
    
    return wlan
# endregion
