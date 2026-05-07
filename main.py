import machine
import json
from time import sleep_ms

from src.wifi import wlan_scan, wlan_ap, wlan_connect
from src.server import web_server, handle_request_gateway, handle_request_status

AP_SSID = "rpi_pico_2_wh"
AP_PASS = None

# region MODE_DEFAULT
def mode_default():
    print("\nmode_default")

    web_server(lambda conn, request: handle_request_status(conn, request, {
        "title": "Pico GPS Clock NTP"
    }))
#endregion

# region MODE_AP
def mode_ap():
    print("\nmode_ap")

    networks = wlan_scan()
    ap = wlan_ap(AP_SSID, AP_PASS)

    web_server(lambda conn, request: handle_request_gateway(conn, request, {
        "title": "Connect to WiFi",
        "networks": networks,
        "ip": ap.ifconfig()[0]
    }))

    sleep_ms(2000)
    ap.active(False)
# endregion

# region MAIN
def main():
    # Add delay to allow for stopping the program if needed
    sleep_ms(2000)

    # os.remove("wifi.txt")
    # return

    try:
        with open("wifi.txt", "r") as f:
            data = f.read()
        print("wifi.txt", data)
        wifi = json.loads(data)
        
        wlan = wlan_connect(wifi["ssid"], wifi["password"])
    
        mode_default()

        sleep_ms(2000)
        wlan.active(False)

    except OSError as err:
        print('not found "wifi.txt"')
        mode_ap()
    
    except RuntimeError as err:
        print(err)
        mode_ap()

    # Reboot
    print("Rebooting...")
    machine.soft_reset()

main()
# endregion
