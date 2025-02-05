import pyfirmata2
import logging
import time

from enum import Enum

from typing import Dict, Callable, Optional

from debounce import debounce

from spacestate import SpaceState

DEVICE = pyfirmata2.Arduino.AUTODETECT
#DEVICE = '/dev/ttyUSB0'


class ArduinoPin(Enum):
    RELAY_VCC = 13

    SWITCH_TOP = 2
    SWITCH_BOTTOM = 3

    RED1 = 12
    YELLOW1 = 11
    GREEN1 = 10
    RED2 = 9
    YELLOW2 = 7
    GREEN2 = 6
    CONFETTI = 5
    UNUSED = 4


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


class FirmataGPIO:
    def __init__(self, spacestate_callback: Optional[Callable[[SpaceState], None]] = None) -> None:
        self.spacestate_callback: Optional[Callable[[SpaceState], None]] = spacestate_callback

        self.board: Optional[pyfirmata2.Arduino] = None
        logging.info("Connecting to board...")
        try:
            self.board = pyfirmata2.Arduino(DEVICE)
        except Exception as e:
            logging.error(f"Failed to connect to device: {e}")
            return

        logging.info("Setting up inputs...")
        self.board.samplingOn(100)
        self.inputs: Dict[ArduinoPin, pyfirmata2.Pin] = {}
        for pin_id in [ArduinoPin.SWITCH_TOP, ArduinoPin.SWITCH_BOTTOM]:
            self.inputs[pin_id] = self.board.get_pin('d:%d:i' % pin_id.value)
            self.inputs[pin_id].register_callback(
                self._handle_gpio_input
            )
            self.inputs[pin_id].enable_reporting()

        logging.info("Setting up outputs...")

        # prepare relay board
        self.relay_vcc: pyfirmata2.Pin = self.board.get_pin('d:%d:o' % ArduinoPin.RELAY_VCC.value)
        self.relay_vcc.write(False)

        self.relays: Dict[ArduinoPin, pyfirmata2.Pin] = {}
        for pin_id in [
            ArduinoPin.RED1, ArduinoPin.YELLOW1, ArduinoPin.GREEN1,
            ArduinoPin.RED2, ArduinoPin.YELLOW2, ArduinoPin.GREEN2,
            ArduinoPin.CONFETTI, ArduinoPin.UNUSED
        ]:
            self.relays[pin_id] = self.board.get_pin('d:%d:o' % pin_id.value)
            self.set_relay(pin_id, False)

        # enable relays
        self.relay_vcc.write(True)

        self.state: Optional[SpaceState] = None
        self._update_switch_state()

    def close(self) -> None:
        if self.board is None:
            return

        for input in self.inputs.values():
            input.disable_reporting()
            input.unregister_callback()

        for relay in self.relays.keys():
            self.set_relay(relay, False)
        self.relay_vcc.write(0)

        self.board.exit()
        self.board = None

    def set_relay(self, pin: ArduinoPin, state: bool) -> None:
        if self.board is None or pin not in self.relays:
            return

        self.relays[pin].write(not state)  # NB: relays are active low

    def _handle_gpio_input(self, data) -> None:
        self._update_switch_state()

    @debounce(0.1)
    def _update_switch_state(self) -> None:
        last_state: SpaceState = self.state

        top_switch_value = not self.inputs[ArduinoPin.SWITCH_TOP].value
        bottom_switch_value = not self.inputs[ArduinoPin.SWITCH_BOTTOM].value

        if self.board is None:
            logging.warning("Board is not connected")
            self.state = SpaceState.UNDETERMINED
        elif top_switch_value and bottom_switch_value:
            logging.warning("Both open and closed contacts are connected. Weird...")
            self.state = SpaceState.UNDETERMINED
        elif top_switch_value:
            logging.debug("Switch is set to 'open' state")
            self.state = SpaceState.OPEN
        elif bottom_switch_value:
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
        logging.info(f'Switch state changed to: {state.name}')
        if state==SpaceState.CLOSED:
            gpio.set_relay(ArduinoPin.RED1, True)
            gpio.set_relay(ArduinoPin.YELLOW1, False)
            gpio.set_relay(ArduinoPin.GREEN1, False)
            gpio.set_relay(ArduinoPin.RED2, True)
            gpio.set_relay(ArduinoPin.YELLOW2, False)
            gpio.set_relay(ArduinoPin.GREEN2, False)
        elif state==SpaceState.UNDETERMINED:
            gpio.set_relay(ArduinoPin.RED1, False)
            gpio.set_relay(ArduinoPin.YELLOW1, True)
            gpio.set_relay(ArduinoPin.GREEN1, False)
            gpio.set_relay(ArduinoPin.RED2, False)
            gpio.set_relay(ArduinoPin.YELLOW2, True)
            gpio.set_relay(ArduinoPin.GREEN2, False)
        elif state==SpaceState.OPEN:
            gpio.set_relay(ArduinoPin.RED1, False)
            gpio.set_relay(ArduinoPin.YELLOW1, False)
            gpio.set_relay(ArduinoPin.GREEN1, True)
            gpio.set_relay(ArduinoPin.RED2, False)
            gpio.set_relay(ArduinoPin.YELLOW2, False)
            gpio.set_relay(ArduinoPin.GREEN2, True)


    gpio = FirmataGPIO(spacestate_callback)

    try:
        while True:
            time.sleep(0.5)

    except KeyboardInterrupt:
        logging.info('Closing...')
        gpio.close()
