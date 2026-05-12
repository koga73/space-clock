import asyncio
import json
import machine
from machine import Pin

from src.display import Display
from src.gps import GPS
from src.wifi import wlan_reset, wlan_scan, wlan_ap, wlan_connect
from src.server import web_server, handle_request_gateway, handle_request_status

AP_SSID = "rpi_pico_2"
AP_PASS = None

display = Display(Pin(18), Pin(19), Pin("LED", Pin.OUT))
gps = GPS()

# region MODE_DEFAULT
async def mode_default(wlan):
    print("\nmode_default")

    await web_server(_handle_request)

    ip = wlan.ifconfig()[0]
    await display.show_async(ip.replace(".", "_"), loops = 1)
    display.show("----")

def _handle_request(request):
    satellites = gps.get_satellites()
    timestamp = gps.get_timestamp()
    lat, lon = gps.get_coords()

    return handle_request_status(request, {
        "title": "Pico GPS Clock NTP",
        "satellites": satellites,
        "timestamp": timestamp,
        "lat": lat,
        "lon": lon
    })
#endregion

# region MODE_AP
async def mode_ap():
    print("\nmode_ap")

    display.show("SCAN")
    networks = await wlan_scan()

    display.show("HOST")
    ap = await wlan_ap(AP_SSID, AP_PASS)
    ip = ap.ifconfig()[0]

    await web_server(lambda request: handle_request_gateway(request, {
        "title": "Connect to WiFi",
        "networks": networks,
        "ip": ip
    }))

    display.show(AP_SSID)
# endregion

async def _reboot():
    await asyncio.sleep_ms(1000)
    print("Rebooting...")
    display.show("    ")
    machine.soft_reset()

# region MAIN
async def main():
    print("starting...")
    
    # Add delay to allow for stopping the program if needed
    await asyncio.sleep_ms(2000)

    # Start display loop
    asyncio.create_task(display.loop())
    display.show("----")

    # Reset wlan interfaces
    await wlan_reset()

    # Start gps loop
    asyncio.create_task(gps.loop())

    try:
        with open("wifi.txt", "r") as f:
            data = f.read()
        print("wifi.txt", data)
        wifi = json.loads(data)
        
        display.show("_-^-_-^-_")
        wlan = await wlan_connect(wifi["ssid"], wifi["password"])
        # await mode_default(wlan)

    except OSError as err:
        print('not found "wifi.txt"')
        # await mode_ap()
    
    except RuntimeError as err:
        print(err)
        await _reboot()
    
    # Main loop
    while True:
        print(f"Satellites = {gps.get_satellites()}")
        print(f"Time = {gps.get_timestamp()}")
        print(f"Lat = {gps.get_lat()}, Lon = {gps.get_lon()}")
        
        # display.show(f"{minutes}{str(seconds)[0:2]}")
        await asyncio.sleep_ms(10000) # Update every 10 seconds
# endregion

try:
    asyncio.run(main())
except KeyboardInterrupt:
    print("\nstopped by user")
    display.show("    ")
