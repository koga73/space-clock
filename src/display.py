import asyncio
import _thread

from lib.tm1637 import TM1637

_DIGITS = 4
_DELAY = 350

class Display(object):
    # Constructor
    def __init__(self, clk, dio, led):
        self._lock = _thread.allocate_lock()

        self.delay = _DELAY
        self.loops = -1
        self.colon = False

        self.text = " " * _DIGITS
        self.index = 0
        
        self.display = TM1637(clk=clk, dio=dio, brightness = 3)
        self.led = led

    # Scroll during loop
    async def loop(self):
        while True:
            await asyncio.sleep_ms(self.delay)

            needs_render = False
            needs_extra_delay = False

            with self._lock:
                if (self.loops == 0):
                    continue

                txtLen = len(self.text)
                if (txtLen > _DIGITS):
                    needs_render = True

                    # Increment index and loop, apply extra delay at end
                    self.index += 1
                    if (self.index >= txtLen):
                        self.index %= txtLen
                        if (self.loops > 0):
                            self.loops -= 1
                        needs_extra_delay = True
            
            if (needs_render):
                self._show_current()

            if (needs_extra_delay):
                await asyncio.sleep_ms(1000)
    
    async def _loop_done(self):
        while (self.loops > 0):
            await asyncio.sleep_ms(self.delay)

    def show(self, txt, delay = _DELAY, loops = -1, colon = False):
        with self._lock:
            self.delay = delay
            self.loops = loops
            self.colon = colon

            self.index = 0
            if (len(txt) > _DIGITS):
                # Add spaces to beginning and end to create a gap
                buffer1 = " " * (_DIGITS - 1)
                buffer2 = " " * (_DIGITS - 1)
                self.text = buffer1 + txt + buffer2
            else:
                self.loops = 0
                self.text = txt
        
        self._show_current()
    
    async def show_async(self, txt, delay = _DELAY, loops = -1, colon = False):
        self.show(txt, delay, loops, colon)

        # Wait for loops to finish
        if (self.loops > 0):
            await self._loop_done()

    def _show_current(self):
        # Left pad to size of _DIGITS
        with self._lock:
            current = self.text[self.index : self.index + _DIGITS]
            show_colon = self.colon == True
        current = f"{{:<{_DIGITS}}}".format(current)

        self.display.show(current, show_colon)
        
        # LED
        led_on = False
        for i in range(_DIGITS):
            char = current[i]
            if (char != " "):
                led_on = True
                break
        if (led_on):
            self.led.on()
        else:
            self.led.off()

    # 0-7
    def set_brightness(self, brightness):
        return self.display.brightness(brightness)
