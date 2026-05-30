import time
import asyncio
import machine
import network
from machine import Pin, RTC

from src.clock import Clock
from src.button import Button
from src.display import Display
from src.gps import GPS
from src.wifi import wlan_reset, wlan_scan, wlan_ap, wlan_connect
from src.server import web_server, handle_request_gateway, handle_request_status
from src.ntp import ntp_server
from src.filesystem import boot_read, wifi_read, settings_read

AP_SSID = "space_clock"
AP_PASS = None

WIFI_HOSTNAME = "space-clock"
DEFAULT_WIFI = {
    "ssid": None,
    "password": None
}

STATUS_DELAY = 15000

# region GLOBALS
rtc = RTC()
clock = Clock.get_instance()
button = Button(20)
display = Display(Pin(5), Pin(4), Pin("LED", Pin.OUT))
gps = GPS(16)
# endregion

# region MODE_DEFAULT
async def mode_default():
    print("\nmode_default")

    # See if we have settings saved
    print("\nsettings")
    f24hr, tz, dst = settings_read()
    clock.set_locale(f24hr, tz, dst)
    
    # See if we should connect to wifi
    server = None
    transport = None
    
    print("\nwifi")
    ssid = DEFAULT_WIFI["ssid"]
    password = DEFAULT_WIFI["password"]
    file_ssid, file_password = wifi_read()
    if (file_ssid != None):
        ssid = file_ssid
    if (file_password != None):
        password = file_password

    if (ssid != None and ssid != ""):
        display.show("_-^-_-^-_")
        
        # Connect to wifi
        wlan = await wlan_connect(ssid, password)
        ip = wlan.ifconfig()[0]
        
        # Start web server
        server = await web_server(
            lambda request: _handle_request(request, ip),
            _reboot
        )
        
        # Start the ntp server
        transport = await ntp_server(clock.get_seconds)

        # Show IP address on display once
        await display.show_async(ip.replace(".", "_"), loops = 1)
    
    # Main loop for GPS and display
    await _loop_default()

    # Clean up
    if (server != None):
        server.close()
    if (transport != None):
        transport.close()

def _handle_request(request, ip):
    return handle_request_status(request, {
        "ip": ip,
        "satellites": gps.get_satellites(),
        "time_display": clock.get_display(),
        "timestamp_utc": clock.get_timestamp(),
        "timestamp_local": clock.get_timestamp_local(),
        "lat": gps.get_lat(),
        "lon": gps.get_lon(),
        "altitude": gps.get_altitude(),
        "height": gps.get_height()
    })
#endregion

# region LOOP_DEFAULT
async def _loop_default():
    last_status_time = 0
    
    print("\nloop default")
    display.show("^^^^----____----^^^^")
    
    while True:
        now_ms = time.ticks_ms()

        # If our check button function returns true, break
        if (button.loop_button(now_ms, button.default_released, button.default_held)):
            break
            
        # Try to receive GPS data on PPS signal
        did_update = gps.loop()
        satellites = gps.get_satellites()
        
        # Periodic status update
        colon = True
        if (time.ticks_diff(now_ms, last_status_time) > STATUS_DELAY):
            last_status_time = now_ms
            colon = False

            print("\ngps status")
            if (gps.has_fix()):
                print(f"time = {gps.get_timestamp()}")
                print(f"lat = {gps.get_lat()}, lon = {gps.get_lon()}")
                print(f"satellites = {satellites}")
            else:
                print("searching for satellites...")
        
        # If we have a new GPS timestamp, update the clock and display
        if (did_update):
            # Update Clock with GPS time on PPS signal
            datetime = gps.get_datetime()
            # Update our custom clock
            clock.set_datetime(datetime, gps.get_pps())
            # Update RTC but it is not as accurate
            rtc.datetime(datetime)

            # Display
            _display_current_time(colon)

        # Tick
        await asyncio.sleep_ms(100)
# endregion

# region DISPLAY
def _display_current_time(colon = True):
    if (clock._time_us == 0):
        return

    display.show(clock.get_display(), colon = colon)
# endregion

# region MODE_AP
async def mode_ap():
    print("\nmode_ap")

    display.show("SCAN")
    networks = await wlan_scan()

    display.show("HOST")
    ap = await wlan_ap(AP_SSID, AP_PASS)
    ip = ap.ifconfig()[0]

    server = await web_server(
        lambda request: handle_request_gateway(request, {
            "title": "Connect to WiFi",
            "networks": networks,
            "ip": ip
        }),
        _reboot
    )

    display.show(AP_SSID)

    # Main loop for AP
    await _loop_ap()

    server.close()
# endregion

# region LOOP_AP
async def _loop_ap():
    print("\nloop ap")

    while True:
        # If our check button function returns true, break
        if (button.loop_button(time.ticks_ms(), button.ap_released, button.ap_held)):
            break

        await asyncio.sleep_ms(250)
# endregion

# region MAIN
async def main():
    print("starting...")
    # Add delay to allow for stopping the program if needed
    await asyncio.sleep_ms(2000)

    # Start display loop
    asyncio.create_task(display.loop())
    display.show("----")

    # Initialize GPS
    await gps.init()

    # Reset wlan interfaces
    await wlan_reset()
    network.hostname(WIFI_HOSTNAME)

    try:
        mode = boot_read()
        if (mode == "ap"):
            await mode_ap()
        else:
            await mode_default()
    except RuntimeError as err:
        print(err)
    
    await _reboot()

async def _reboot():
    await asyncio.sleep_ms(1000)
    print("rebooting...")
    display.show("    ")
    machine.soft_reset()
# endregion

try:
    asyncio.run(main())
except KeyboardInterrupt:
    print("\nstopped by user")
    display.show("    ")
