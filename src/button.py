import time
from machine import Pin

from src.clock import Clock
from src.filesystem import boot_write, settings_read, settings_write

class Button(object):
    def __init__(self, pin):
        self.button = Pin(pin, Pin.IN, Pin.PULL_UP)
        self.button_pressed_time = -1

    # region LOOP_BUTTON
    def loop_button(self, ticks_now, func_released, func_held):
        button = self.button
        button_pressed_time = self.button_pressed_time

        # Not pressed, when pressed set time
        if (button_pressed_time == -1 and button.value() == 0):
            self.button_pressed_time = ticks_now
        # Pressed
        elif (button_pressed_time != -1):
            delta_held = time.ticks_diff(ticks_now, button_pressed_time)

            # Not pressed anymore, click
            if (button.value() == 1):
                self.button_pressed_time = -1
                return func_released(delta_held)
            # Still pressed, check how long
            else:
                return func_held(delta_held)
    # endregion

    # region DEFAULT
    def default_released(self, held_time):
        print(f"\nbutton released after {held_time} ms")

        # Toggle 24hr format
        f24hr, tz, dst = settings_read()
        f24hr = not f24hr
        settings_write(f24hr, tz, dst)
        
        clock = Clock.get_instance()
        clock.init_localtime(f24hr, tz, dst)

    def default_held(self, held_time):
        print(f"\nbutton held for {held_time} ms")
        
        if (held_time > 3000):
            print("switching to mode_ap")
            boot_write("ap")
            return True
        
    # endregion

    # region AP
    def ap_released(self, held_time):
        print(f"\nbutton released after {held_time} ms")

    def ap_held(self, held_time):
        print(f"\nbutton held for {held_time} ms")
        
        if (held_time > 3000):
            print("switching to mode_default")
            boot_write("default")
            return True
    # endregion
