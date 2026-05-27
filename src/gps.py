import asyncio
import time
from machine import Pin

from lib.l76x import L76X

class GPS():
    # Constructor
    def __init__(self, pps_pin = 16):
        self.pps_pin = pps_pin

        self._pps_ready = False
        self._pps_tick = time.ticks_us()

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

        pps = Pin(self.pps_pin, Pin.IN)
        pps.irq(trigger = Pin.IRQ_RISING, handler = self._handle_pps)

    # PPS signal IRQ handler
    def _handle_pps(self, _pin):
        self._pps_tick = time.ticks_us()
        
        # If we are already true then the last message was not processed - so clear the buffer
        if (self._pps_ready == True):
            self.gps.L76X_Flush()
        
        self._pps_ready = True
    
    # Call from main loop
    def try_receive(self):
        did_update = self.gps.L76X_Receive()

        if (self._pps_ready and did_update):
            self._pps_ready = False
            return True
        
        return False

    def get_pps_delta(self):
        return time.ticks_diff(self.gps.Last_Updated, self._pps_tick)

    def get_satellites(self):
        return self.gps.Satellites

    def get_datetime(self):
        gps = self.gps
        weekday = 0 # Not supported by GPS
        return (
            gps.Time_Year, gps.Time_Month, gps.Time_Day,
            weekday,
            gps.Time_Hours, gps.Time_Minutes, gps.Time_Seconds,
            0 # gps.Time_Microseconds
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
