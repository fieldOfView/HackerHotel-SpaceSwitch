from enum import Enum
import pyfirmata2

from spacestate import SpaceState

DEVICE = '/dev/ttyUSB0'

# fix an uncaught exception in pyfirmata2.Arduino.__del__
pyfirmata2_del = pyfirmata2.Arduino.__del__
def pyfirmata2_del_fix(self):
    try:
        pyfirmata2_del(self)
    except AttributeError:
        pass
pyfirmata2.Arduino.__del__ = pyfirmata2_del_fix


class ArduinoPin(Enum):
    RELAY_VCC = 7

    SWITCH_TOP = 8
    SWITCH_BOTTOM = 9

    RED = 10
    YELLOW = 11
    GREEN = 12
    CONFETTI = 13


class FirmataPinWithValue:
    def __init__(self, firmata_pin, value: bool = False):
        self.firmata_pin = firmata_pin
        self.value = value


class FirmataGPIO:
    def __init__(self, spacestate_callback=None):
        self.state = SpaceState.UNDETERMINED
        self.spacestate_callback = spacestate_callback

        try:
            self.board = pyfirmata2.Arduino(DEVICE)
        except Exception as e:
            self.board = None
            print("Failed to connect to device: %s" % e)
            return

        self.inputs: map[ArduinoPin, FirmataPinWithValue] = {}
        for pin_id in [ArduinoPin.SWITCH_TOP, ArduinoPin.SWITCH_BOTTOM]:
            self.inputs[pin_id] = FirmataPinWithValue(
                firmata_pin=self.board.get_pin('d:%d:i' % pin_id.value)
            )
            self.inputs[pin_id].firmata_pin.register_callback(
                self._switch_open_callback if pin_id == ArduinoPin.SWITCH_TOP
                else self._switch_closed_callback
            )
            self.inputs[pin_id].firmata_pin.enable_reporting()

        # prepare relay board
        self.relay_vcc = self.board.get_pin('d:%d:o' % ArduinoPin.RELAY_VCC.value)
        self.relay_vcc.write(False)

        self.relays: map[ArduinoPin, FirmataPinWithValue] = {}
        for pin_id in [ArduinoPin.RED, ArduinoPin.YELLOW, ArduinoPin.GREEN, ArduinoPin.CONFETTI]:
            self.relays[pin_id] = FirmataPinWithValue(
                firmata_pin=self.board.get_pin('d:%d:o' % pin_id.value)
            )
            self.set_relay(pin_id, False)

        # enable relays
        self.relay_vcc.write(True)

    def close(self):
        if self.board is None:
            return

        for input in self.inputs.values():
            input.firmata_pin.disable_reporting()
            input.firmata_pin.unregister_callback()

        for relay in self.relays.keys():
            self.set_relay(relay, False)
        self.relay_vcc.write(0)

        self.board.exit()
        self.board = None

    def set_relay(self, pin: ArduinoPin, state: bool):
        if self.board is None or pin not in self.relays:
            return

        self.relays[pin].firmata_pin.write(not state)  # NB: relays are active low
        self.relays[pin].state = state

    def _switch_open_callback(self, data):
        self.inputs[ArduinoPin.SWITCH_TOP].value = data
        self._update_switch_state()

    def _switch_closed_callback(self, data):
        self.inputs[ArduinoPin.SWITCH_BOTTOM].value = data
        self._update_switch_state()

    def _update_switch_state(self):
        last_state = self.state

        if self.board is None:
            print("Board is not connected")
            self.state = SpaceState.UNDETERMINED
        elif self.inputs[ArduinoPin.SWITCH_TOP].value and self.inputs[ArduinoPin.SWITCH_BOTTOM].value:
            print("Both open and closed contacts are connected. Weird...")
            self.state = SpaceState.UNDETERMINED
        elif self.inputs[ArduinoPin.SWITCH_TOP].value:
            print("Switch is set to 'open' state")
            self.state = SpaceState.OPEN
        elif self.inputs[ArduinoPin.SWITCH_BOTTOM].value:
            print("Switch is set to 'closed' state")
            self.state = SpaceState.CLOSED
        else:
            print("Switch is somewhere in between")
            self.state = SpaceState.UNDETERMINED

        if self.state != last_state and self.spacestate_callback is not None:
            self.spacestate_callback(self.state)


if __name__ == '__main__':
    def spacestate_callback(state: SpaceState):
        print('Switch state changed to:', state)

    gpio = FirmataGPIO(spacestate_callback)

    try:
        while True:
            pass
    except KeyboardInterrupt:
        print('Closing...')
        gpio.close()
