import asyncio

from lib.tm1637 import TM1637

_DIGITS = 4
_DELAY = 300

class Display(object):
    # Constructor
    def __init__(self, clk, dio, led):
        self.delay = _DELAY
        self.text = " " * _DIGITS
        self.index = 0
        self.display = TM1637(clk=clk, dio=dio)
        self.led = led

    # Scroll during loop
    async def loop(self):
        while True:
            await asyncio.sleep_ms(self.delay)
            txtLen = len(self.text)
            if (txtLen > _DIGITS):
                self._show_current()
                # Increment index and loop, apply extra delay at end
                self.index += 1
                if (self.index >= txtLen):
                    self.index %= txtLen
                    await asyncio.sleep_ms(1000)

    def show(self, txt, delay = _DELAY):
        self.delay = delay
        self.index = 0

        if (len(txt) > _DIGITS):
            # Add spaces to beginning and end to create a gap
            buffer1 = " " * (_DIGITS - 1)
            buffer2 = " " * (_DIGITS - 1)
            self.text = buffer1 + txt + buffer2
        else:
            # Pad with spaces to fill display
            self.text = txt
        
        self._show_current()

    def _show_current(self):
        # Left pad to size of _DIGITS
        current = self.text[self.index : self.index + _DIGITS]
        current = f"{{:<{_DIGITS}}}".format(current)

        self.display.show(current)
        
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
