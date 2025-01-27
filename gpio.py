from enum import Enum
import pyfirmata2

DEVICE = '/dev/ttyUSB0'

class SpaceState(Enum):
    CLOSED = 0
    UNDETERMINED = 1
    OPEN = 2


class Pin(Enum):
    RELAY_VCC = 7

    SWITCH_TOP = 8
    SWITCH_BOTTOM = 9

    RED = 10
    YELLOW = 11
    GREEN = 12
    CONFETTI = 13


class PinWithState:
    def __init__(self, pin, state: bool = False):
        self.pin = pin
        self.state = state


class FirmataGPIO:
    def __init__(self):
        self.state = SpaceState.UNDETERMINED

        try:
            self.board = pyfirmata2.Arduino(DEVICE)
        except Exception as e:
            self.board = None
            print("Failed to connect to device: %s" % e)
            return

        self.inputs = {
            Pin.SWITCH_TOP: PinWithState(pin=self.board.get_pin('d:%d:i' % Pin.SWITCH_TOP.value)),
            Pin.SWITCH_BOTTOM: PinWithState(pin=self.board.get_pin('d:%d:i' % Pin.SWITCH_BOTTOM.value))
        }
        for input in self.inputs.values():
            input.pin.register_callback(self._input_callback)
            input.pin.enable_reporting()

        self.relay_vcc = self.board.get_pin('d:%d:o' % Pin.RELAY_VCC.value)
        self.relay_vcc.write(False)

        self.relays = {
            Pin.RED: PinWithState(pin=self.board.get_pin('d:%d:o' % Pin.RED.value)),
            Pin.YELLOW: PinWithState(pin=self.board.get_pin('d:%d:o' % Pin.YELLOW.value)),
            Pin.GREEN: PinWithState(pin=self.board.get_pin('d:%d:o' % Pin.GREEN.value)),
            Pin.CONFETTI: PinWithState(pin=self.board.get_pin('d:%d:o' % Pin.CONFETTI.value))
        }

        for pin in self.relays.keys():
            self.set_relay(pin, False)

        # turn on relay board
        self.relay_vcc.write(True)

    def close(self):
        if self.board is None:
            return

        for input in self.inputs.values():
            input.pin.disable_reporting()
            input.pin.unregister_callback()

        for relay in self.relays.keys():
            self.set_relay(relay, False)
        self.relay_vcc.write(0)

        self.board.exit()
        self.board = None

    def set_relay(self, pin: Pin, state: bool):
        if self.board is None or pin not in self.relays:
            return

        self.relays[pin].pin.write(not state)  # NB: relays are active low
        self.relays[pin].state = state

    def _switch_open_callback(self, data):
        self.inputs[Pin.SWITCH_TOP]["state"] = data
        self._update_switch_state()

    def _switch_closed_callback(self, data):
        self.inputs[Pin.SWITCH_BOTTOM]["state"] = data
        self._update_switch_state()

    def _update_switch_state(self):
        if self.board is None:
            self.state = SpaceState.UNDETERMINED
            return

        if self.inputs[Pin.SWITCH_TOP]["state"] and self.inputs[Pin.SWITCH_BOTTOM]["state"]:
            print("Both open and closed contacts are connected. Weird...")
            self.state = SpaceState.UNDETERMINED
        elif self.inputs[Pin.SWITCH_TOP]["state"]:
            print("Switch is set to 'open' state")
            self.state = SpaceState.OPEN
        elif self.inputs[Pin.SWITCH_BOTTOM]["state"]:
            print("Switch is set to 'closed' state")
            self.state = SpaceState.CLOSED
        else:
            print("Switch is somewhere in between")
            self.state = SpaceState.UNDETERMINED


if __name__ == '__main__':
    gpio = FirmataGPIO()

    try:
        while True:
            pass
    except KeyboardInterrupt:
        print('Closing...')
        gpio.close()
