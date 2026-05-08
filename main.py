import machine
import asyncio
import json

from lib.tm1637 import TM1637
from src.wifi import wlan_reset, wlan_scan, wlan_ap, wlan_connect
from src.server import web_server, handle_request_gateway, handle_request_status

AP_SSID = "rpi_pico_2"
AP_PASS = None

display = TM1637(clk=machine.Pin(16), dio=machine.Pin(17))

# region MODE_DEFAULT
async def mode_default(wlan):
    print("\nmode_default")

    await web_server(lambda request: handle_request_status(request, {
        "title": "Pico GPS Clock NTP"
    }))

    ip = wlan.ifconfig()[0]
    asyncio.create_task(_scroll_text(ip.replace(".", "-")))
#endregion

# region MODE_AP
async def mode_ap():
    print("\nmode_ap")

    networks = await wlan_scan()
    ap = await wlan_ap(AP_SSID, AP_PASS)
    ip = ap.ifconfig()[0]

    await web_server(lambda request: handle_request_gateway(request, {
        "title": "Connect to WiFi",
        "networks": networks,
        "ip": ip
    }))

    asyncio.create_task(_scroll_text(AP_SSID))
# endregion

# TODO: Move to a separate file to manage display state
async def _scroll_text(text, delay = 500, digits = 4):
    # No need to scroll
    if len(text) <= digits:
        display.show(text.ljust(digits)) # Pad with spaces to fill display
        return
    
    # Add spaces to beginning and end to create a gap
    buffer1 = " " * (digits - 1)
    buffer2 = " " * digits
    text = buffer1 + text + buffer2

    while True:
        for i in range(len(text) - digits + 1):
            display.show(text[i: i + digits])
            await asyncio.sleep_ms(delay)

# region MAIN
async def main():
    print("starting...")
    
    # Add delay to allow for stopping the program if needed
    await asyncio.sleep_ms(2000)

    display.show("----")
    await wlan_reset()

    # os.remove("wifi.txt")
    # return

    try:
        with open("wifi.txt", "r") as f:
            data = f.read()
        print("wifi.txt", data)
        wifi = json.loads(data)
        
        wlan = await wlan_connect(wifi["ssid"], wifi["password"])
        await mode_default(wlan)

    except OSError as err:
        print('not found "wifi.txt"')
        await mode_ap()
    
    except RuntimeError as err:
        print(err)
        await mode_ap()
    
    # Heartbeat
    while True:
        await asyncio.sleep_ms(5)
# endregion

try:
    asyncio.run(main())
except KeyboardInterrupt:
    display.show("    ")
    print("\nstopped by user")
