import micropython
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

        self._pps_last_tick = 0
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

    # PPS signal IRQ handler, capture the tick and schedule processing outside of the interrupt
    def _handle_pps(self, _pin):
        micropython.schedule(self._pps_process, time.ticks_us())
    
    # Process the PPS tick and compute the ticks-per-second
    def _pps_process(self, pps_tick):
        delta = time.ticks_diff(pps_tick, self._pps_last_tick)
        
        # Ignore if the delta is too far off
        if (900000 < delta < 1100000):
            self._pps_ticks_per_second = int(_JITTER_SMOOTHING_FACTOR * delta + (1 - _JITTER_SMOOTHING_FACTOR) * self._pps_ticks_per_second)
        
        self._pps_last_tick = pps_tick
    
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
