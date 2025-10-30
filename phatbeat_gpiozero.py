# phatbeat_gpiozero.py (partial)
import atexit
import time
from gpiozero import LED, Button

__version__ = '0.1.2'

# Pins
DAT_PIN = 23
CLK_PIN = 24
NUM_PIXELS = 16
CHANNEL_PIXELS = 8
BRIGHTNESS = 7  # 0–31

# Initialize LEDs
dat = LED(DAT_PIN)
clk = LED(CLK_PIN)

# Pixel buffer
pixels = [[0, 0, 0, BRIGHTNESS] for _ in range(NUM_PIXELS)]
_clear_on_exit = True

# Button handling
_buttons = {}

atexit.register(lambda: (clear(), show()))

def clear(channel=None):
    if channel is None or channel == 0:
        for x in range(CHANNEL_PIXELS):
            pixels[x][0:3] = [0,0,0]
    if channel is None or channel == 1:
        for x in range(CHANNEL_PIXELS):
            pixels[x + CHANNEL_PIXELS][0:3] = [0,0,0]

def _write_byte(byte):
    for i in range(8):
        dat.value = (byte & 0b10000000) != 0
        clk.on(); clk.off()
        byte <<= 1

def _sof():
    dat.off()
    for _ in range(32):
        clk.on(); clk.off()

def _eof():
    dat.on()
    for _ in range(32):
        clk.on(); clk.off()

def set_pixel(x, r, g, b, brightness=None):
    if brightness is None:
        brightness = pixels[x][3]
    else:
        brightness = int(31.0 * brightness) & 0b11111
    pixels[x] = [r & 0xff, g & 0xff, b & 0xff, brightness]

def set_all(r, g, b, brightness=None, channel=None):
    if channel is None or channel == 0:
        for x in range(CHANNEL_PIXELS):
            set_pixel(x, r, g, b, brightness)
    if channel is None or channel == 1:
        for x in range(CHANNEL_PIXELS):
            set_pixel(x + CHANNEL_PIXELS, r, g, b, brightness)

def show():
    _sof()
    for r, g, b, brightness in pixels:
        _write_byte(0b11100000 | brightness)
        _write_byte(b)
        _write_byte(g)
        _write_byte(r)
    _eof()

# -----------------------------
# Button decorator API
# -----------------------------
def on(pin_number, handler=None):
    """Attach a callback to a button."""
    button = Button(pin_number)
    if handler is not None:
        button.when_pressed = handler
        _buttons[pin_number] = button
        return button
    else:
        def decorator(f):
            button.when_pressed = f
            _buttons[pin_number] = button
            return f
        return decorator
