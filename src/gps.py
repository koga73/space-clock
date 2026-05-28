import asyncio
import time
from machine import Pin

from lib.l76x import L76X

# New ticks-per-second gets multiplied by this factor to smooth out into an averaged jitter 
_JITTER_SMOOTHING_FACTOR = 0.1

class GPS():
    # Constructor
    def __init__(self, pps_pin = 16):
        self._pps_pin = pps_pin

        self._pps_last_tick = time.ticks_us()
        self._pps_ticks_per_second = 1000000

    async def init(self):
        gps = L76X()
        gps.L76X_Set_Baudrate(9600)
        await asyncio.sleep_ms(1000)

        # Increase BAUD rate for faster NMEA parsing
        gps.L76X_Send_Command(gps.SET_NMEA_BAUDRATE_115200)
        await asyncio.sleep_ms(1000)
        gps.L76X_Set_Baudrate(115200)

        # Timing
        gps.L76X_Send_Command(gps.SET_POS_FIX_1S)
        gps.L76X_Send_Command(gps.SET_PPS_ON)

        # Output format
        gps.L76X_Send_Command(gps.SET_NMEA_OUTPUT)
        gps.L76X_Exit_BackupMode()

        self.gps = gps

        pps = Pin(self._pps_pin, Pin.IN)
        pps.irq(trigger = Pin.IRQ_RISING, handler = self._handle_pps)

    # PPS signal IRQ handler
    def _handle_pps(self, _pin):
        now = time.ticks_us()
        
        # Compute number of ticks in a second
        delta = self._pps_ticks_per_second = time.ticks_diff(now, self._pps_last_tick)
        self._pps_ticks_per_second = int(_JITTER_SMOOTHING_FACTOR * delta + (1 - _JITTER_SMOOTHING_FACTOR) * self._pps_ticks_per_second)
        
        self._pps_last_tick = now
    
    # Call from main loop
    def loop(self):
        return self.gps.L76X_Receive()

    # Return tuple of (last_pps_tick, ticks_per_second)
    def get_pps(self):
        return self._pps_last_tick, self._pps_ticks_per_second

    def get_satellites(self):
        return self.gps.Satellites

    def get_datetime(self):
        gps = self.gps
        weekday = 0 # Not supported by GPS
        return (
            gps.Time_Year, gps.Time_Month, gps.Time_Day,
            weekday,
            gps.Time_Hours, gps.Time_Minutes, gps.Time_Seconds,
            gps.Time_Microseconds
        )

    def get_timestamp(self):
        return self.gps.Timestamp

    def get_lat(self):
        return self.gps.Lat

    def get_lon(self):
        return self.gps.Lon
    
    def get_altitude(self):
        return self.gps.Altitude

    def get_height(self):
        return self.gps.Height

    def has_fix(self):
        return self.gps.Satellites > 0
