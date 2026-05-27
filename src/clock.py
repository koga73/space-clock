import time
import json

from lib.daylightsaving import StandardTimePolicy, DaylightSavingPolicy, DaylightSaving 

_SINGLETON_ENFORCER = object()

# Clock with microsecond precision, timezones and daylight saving time
class Clock:
    DEFAULT_FORMAT_24HR = False
    DEFAULT_TZ = -5	# EST
    DEFAULT_DST = "us"

    _instance = None

    @staticmethod
    def get_instance():
        if (Clock._instance is None):
            Clock._instance = Clock(_SINGLETON_ENFORCER)
        return Clock._instance

    def __init__(self, enforcer = None):
        if (enforcer != _SINGLETON_ENFORCER):
            raise RuntimeError("Cannot create instance, use singleton instead")

        self.time_us = 0
        self.last_time_set = 0

        self._ds = None
    
    # region LOCALE
    def set_locale(self, format_24hr = None, tz = None, dst = None):
        self.format_24hr = format_24hr if format_24hr != None else Clock.DEFAULT_FORMAT_24HR
        self.tz = tz if tz != None else Clock.DEFAULT_TZ
        self.dst = dst if dst != None else Clock.DEFAULT_DST
        
        print("init_local", json.dumps({
            "format_24hr": format_24hr,
            "tz": tz,
            "dst": dst
        }))
        tz_minutes = self.tz * 60

        # US
        if (self.dst == "us"):
            # Daylight Saving starts on second Sunday of March at 2am
            # 0 = Northern hemisphere
            # 2 = Second week of the month
            # 3 = March
            # 6 = Sunday
            # 2 = 2AM
            # Time offset = 60 mins (GMT+1)
            dst_policy = DaylightSavingPolicy(0, 2, 3, 6, 2, tz_minutes + 60)

            # Daylight Saving ends on first Sunday of November at 2AM
            # 0 = Northern hemisphere
            # 1 = First week of the month
            # 11 = November
            # 6 = Sunday
            # 2 = 2AM
            # Time offset = 0 mins (GMT/UTC)
            std_policy = StandardTimePolicy(0, 1, 11, 6, 2, tz_minutes)

            self._ds = DaylightSaving(dst_policy, std_policy)

        # UK / EU   
        elif (self.dst == "uk"):
            # Daylight Saving starts on last Sunday of March at 1AM
            # 0 = Northern hemisphere
            # 0 = Last week of the month
            # 3 = March
            # 6 = Sunday
            # 1 = 1AM
            # Time offset = 60 mins (GMT+1)
            dst_policy = DaylightSavingPolicy(0, 0, 3, 6, 1, tz_minutes + 60)

            # Daylight Saving ends on last Sunday of October at 2AM
            # 0 = Northern hemisphere
            # 0 = Last week of the month
            # 10 = October
            # 6 = Sunday
            # 2 = 2AM
            # Time offset = 0 mins (GMT/UTC)
            std_policy = StandardTimePolicy(0, 0, 10, 6, 2, tz_minutes)

            self._ds = DaylightSaving(dst_policy, std_policy)
        
        # Australia
        elif (self.dst == "au"):
            # Daylight Saving starts on first Sunday of October at 2am
            # 1 = Southern hemisphere
            # 1 = First week of the month
            # 10 = October
            # 6 = Sunday
            # 2 = 2AM
            # Time offset = 60 mins (GMT+1)
            dst_policy = DaylightSavingPolicy(1, 1, 10, 6, 2, tz_minutes + 60)

            # Daylight Saving ends on first Sunday of April at 3AM
            # 1 = Southern hemisphere
            # 1 = First week of the month
            # 4 = April
            # 6 = Sunday
            # 3 = 3AM
            # Time offset = 0 mins (GMT/UTC)
            std_policy = StandardTimePolicy(1, 1, 4, 6, 3, tz_minutes)

            self._ds = DaylightSaving(dst_policy, std_policy)
        
        else:
            self._ds = None
    
    def get_locale(self):
        return (
            self.format_24hr if self.format_24hr != None else Clock.DEFAULT_FORMAT_24HR,
            self.tz if self.tz != None else Clock.DEFAULT_TZ,
            self.dst if self.dst != None else Clock.DEFAULT_DST
        )

    # dt = (year, month, day, weekday, hours, minutes, seconds, subseconds)
    def get_localtime(self):
        if (self.last_time_set == 0):
            return (1970, 1, 1, 4, 0, 0, 0, 0)
        
        seconds, microseconds = self.get_seconds()
        
        if (self._ds != None):
            # Adjust seconds for timezone and daylight saving time
            seconds = self._ds.localtime(seconds)
        
        # Convert seconds back to datetime tuple with microsecond precision
        year, month, mday, hour, minute, second, weekday, yearday = time.gmtime(seconds)
        return (year, month, mday, weekday, hour, minute, second, microseconds)

    def get_timestamp_local(self):
        dt = self.get_localtime()
        return self._format_timestamp(dt[0], dt[1], dt[2], dt[4], dt[5], dt[6], dt[7])
    # endregion
    
    # region DATETIME
    # SET datetime UTC where subseconds = microseconds
    # dt = (year, month, day, weekday, hours, minutes, seconds, subseconds)
    def set_datetime(self, dt, pps_delta_us = 0):
        # Convert datetime tuple to seconds since epoch (UNIX: January 1, 1970)
        seconds = time.mktime((dt[0], dt[1], dt[2], dt[4], dt[5], dt[6], dt[3], 0))

        # Assume the subseconds in tuple is in Microseconds
        self.time_us = seconds * 1000000 + dt[7] - pps_delta_us
        self.last_time_set = time.ticks_us()

    # GET datetime UTC tuple where subseconds = microseconds
    # dt = (year, month, day, weekday, hours, minutes, seconds, subseconds)
    def get_datetime(self):
        if (self.last_time_set == 0):
            return (1970, 1, 1, 4, 0, 0, 0, 0)

        seconds, microseconds = self.get_seconds()

        year, month, mday, hour, minute, second, weekday, yearday = time.gmtime(seconds)
        return (year, month, mday, weekday, hour, minute, second, microseconds)

    def get_timestamp(self):
        dt = self.get_datetime()
        return self._format_timestamp(dt[0], dt[1], dt[2], dt[4], dt[5], dt[6], dt[7])
    # endregion

    # GET time in seconds since epoch (UNIX: January 1, 1970)
    def get_seconds(self):
        if (self.last_time_set == 0):
            return 0, 0

        t = self.time_us
        delta = time.ticks_diff(time.ticks_us(), self.last_time_set)
        now = t + delta
        return int(now // 1000000), int(now % 1000000)
    
    # What to show on the display
    def get_display(self, digits = 4):
        if (self.last_time_set == 0):
            return "------" if digits == 6 else "----"

        now = self.get_localtime()
        hours = now[4]
        minutes = now[5]
        seconds = now[6]

        if (not self.format_24hr):
            hours = hours % 12
            if (hours == 0):
                hours = 12

        hours_str = "{:2d}".format(hours)
        minutes_str = "{:02d}".format(minutes)
        seconds_str = "{:02d}".format(seconds)
        
        return f'{hours_str}{minutes_str}{seconds_str}' if digits == 6 else f'{hours_str}{minutes_str}'
    # endregion

    def _format_timestamp(self, year, month, day, hours, minutes, seconds, microseconds):
        # Pad with leading zero if needed
        year = "{:02d}".format(year)
        month = "{:02d}".format(month)
        day = "{:02d}".format(day)
        hours = "{:02d}".format(hours)
        minutes = "{:02d}".format(minutes)
        seconds = "{:02d}".format(seconds)
        microseconds = "{:06d}".format(microseconds)

        return f"{year}-{month}-{day} {hours}:{minutes}:{seconds}.{microseconds}"