import pyfirmata2
import logging
import time

from enum import Enum
from typing import Dict, Callable, Optional

from spacestate import SpaceState

DEVICE = '/dev/ttyUSB0'


class ArduinoPin(Enum):
    RELAY_VCC = 13

    SWITCH_TOP = 3
    SWITCH_BOTTOM = 4

    RED1 = 12
    YELLOW1 = 11
    GREEN1 = 10
    RED2 = 9
    YELLOW2 = 8
    GREEN2 = 7
    CONFETTI = 6
    UNUSED = 5


# fix an uncaught exception in pyfirmata2.Arduino.__del__
pyfirmata2_del = pyfirmata2.Arduino.__del__
def pyfirmata2_del_fix(self):
    try:
        pyfirmata2_del(self)
    except AttributeError:
        pass
pyfirmata2.Arduino.__del__ = pyfirmata2_del_fix

# fix a typo in pyfirmata2.Pin
pyfirmata2.Pin.unregister_callback = pyfirmata2.Pin.unregiser_callback


class FirmataPinWithValue:
    def __init__(self, firmata_pin: pyfirmata2.Pin, value: bool = False) -> None:
        self.firmata_pin: pyfirmata2.Pin = firmata_pin
        self.value: bool = value


class FirmataGPIO:
    def __init__(self, spacestate_callback: Optional[Callable[[SpaceState], None]] = None) -> None:
        self.spacestate_callback: Optional[Callable[[SpaceState], None]] = spacestate_callback

        self.state: SpaceState = SpaceState.UNDETERMINED
        self.board: Optional[pyfirmata2.Arduino] = None
        logging.info("Connecting to board...")
        try:
            self.board = pyfirmata2.Arduino(DEVICE)
        except Exception as e:
            logging.error(f"Failed to connect to device: {e}")
            return

        logging.info("Setting up inputs...")
        self.board.samplingOn(100)
        self.inputs: Dict[ArduinoPin, FirmataPinWithValue] = {}
        for pin_id in [ArduinoPin.SWITCH_TOP, ArduinoPin.SWITCH_BOTTOM]:
            self.inputs[pin_id] = FirmataPinWithValue(
                firmata_pin=self.board.get_pin('d:%d:i' % pin_id.value)
            )
            self.inputs[pin_id].firmata_pin.register_callback(
                self._switch_top_callback if pin_id == ArduinoPin.SWITCH_TOP
                else self._switch_bottom_callback
            )
            self.inputs[pin_id].firmata_pin.enable_reporting()

        logging.info("Setting up outputs...")

        # prepare relay board
        self.relay_vcc: pyfirmata2.Pin = self.board.get_pin('d:%d:o' % ArduinoPin.RELAY_VCC.value)
        self.relay_vcc.write(False)

        self.relays: Dict[ArduinoPin, FirmataPinWithValue] = {}
        for pin_id in [
            ArduinoPin.RED1, ArduinoPin.YELLOW1, ArduinoPin.GREEN1,
            ArduinoPin.RED2, ArduinoPin.YELLOW2, ArduinoPin.GREEN2,
            ArduinoPin.CONFETTI, ArduinoPin.UNUSED
        ]:
            self.relays[pin_id] = FirmataPinWithValue(
                firmata_pin=self.board.get_pin('d:%d:o' % pin_id.value)
            )
            self.set_relay(pin_id, False)

        # enable relays
        self.relay_vcc.write(True)

    def close(self) -> None:
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

    def set_relay(self, pin: ArduinoPin, state: bool) -> None:
        if self.board is None or pin not in self.relays:
            return

        self.relays[pin].firmata_pin.write(not state)  # NB: relays are active low
        self.relays[pin].value = state

    def _switch_top_callback(self, data: bool) -> None:
        self.inputs[ArduinoPin.SWITCH_TOP].value = not data
        self._update_switch_state()

    def _switch_bottom_callback(self, data: bool) -> None:
        self.inputs[ArduinoPin.SWITCH_BOTTOM].value = not data
        self._update_switch_state()

    def _update_switch_state(self) -> None:
        last_state: SpaceState = self.state

        if self.board is None:
            logging.warning("Board is not connected")
            self.state = SpaceState.UNDETERMINED
        elif self.inputs[ArduinoPin.SWITCH_TOP].value and self.inputs[ArduinoPin.SWITCH_BOTTOM].value:
            logging.warning("Both open and closed contacts are connected. Weird...")
            self.state = SpaceState.UNDETERMINED
        elif self.inputs[ArduinoPin.SWITCH_TOP].value:
            logging.debug("Switch is set to 'open' state")
            self.state = SpaceState.OPEN
        elif self.inputs[ArduinoPin.SWITCH_BOTTOM].value:
            logging.debug("Switch is set to 'closed' state")
            self.state = SpaceState.CLOSED
        else:
            logging.debug("Switch is somewhere in between")
            self.state = SpaceState.UNDETERMINED

        if self.state != last_state and self.spacestate_callback is not None:
            self.spacestate_callback(self.state)


if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

    def spacestate_callback(state: SpaceState):
        logging.info('Switch state changed to:', state)

    gpio = FirmataGPIO(spacestate_callback)

    state: bool = False

    try:
        while True:
            state = not state
            gpio.set_relay(ArduinoPin.RED1, state)
            gpio.set_relay(ArduinoPin.RED2, state)
            gpio.set_relay(ArduinoPin.GREEN1, state)
            gpio.set_relay(ArduinoPin.GREEN2, state)
            gpio.set_relay(ArduinoPin.YELLOW1, state)
            gpio.set_relay(ArduinoPin.YELLOW2, state)
            time.sleep(0.5)
    except KeyboardInterrupt:
        logging.info('Closing...')
        gpio.close()
