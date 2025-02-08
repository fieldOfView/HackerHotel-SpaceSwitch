import pyfirmata2
import logging
import time

from enum import Enum
from threading import Timer

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
    ORANGE1 = 11
    GREEN1 = 10
    RED2 = 9
    ORANGE2 = 7
    GREEN2 = 6
    CONFETTI = 5
    UNUSED = 4


class LampColor(Enum):
    OFF = 0
    RED = 1
    ORANGE = 2
    YELLOW = 3
    GREEN = 4


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
    def __init__(self, on_state_changed: Optional[Callable[[SpaceState], None]] = None) -> None:
        self.on_state_changed: Optional[Callable[[SpaceState], None]] = on_state_changed

        self.state: Optional[SpaceState] = None

        self._confetti_timer: Optional[Timer] = None

        self._board: Optional[pyfirmata2.Arduino] = None
        logging.info('Connecting to board...')
        try:
            self._board = pyfirmata2.Arduino(DEVICE)
        except Exception as e:
            logging.error(f'Failed to connect to device: {e}')
            return

        logging.info('Setting up inputs...')
        self._board.samplingOn(100)
        self._inputs: Dict[ArduinoPin, pyfirmata2.Pin] = {}
        for pin_id in [ArduinoPin.SWITCH_TOP, ArduinoPin.SWITCH_BOTTOM]:
            self._inputs[pin_id] = self._board.get_pin('d:%d:i' % pin_id.value)
            self._inputs[pin_id].register_callback(
                self._handle_gpio_input
            )
            self._inputs[pin_id].enable_reporting()

        logging.info('Setting up outputs...')

        # prepare relay board
        self._relay_vcc: pyfirmata2.Pin = self._board.get_pin('d:%d:o' % ArduinoPin.RELAY_VCC.value)
        self._relay_vcc.write(False)

        self._relays: Dict[ArduinoPin, pyfirmata2.Pin] = {}
        for pin_id in [
            ArduinoPin.RED1, ArduinoPin.ORANGE1, ArduinoPin.GREEN1,
            ArduinoPin.RED2, ArduinoPin.ORANGE2, ArduinoPin.GREEN2,
            ArduinoPin.CONFETTI, ArduinoPin.UNUSED
        ]:
            self._relays[pin_id] = self._board.get_pin('d:%d:o' % pin_id.value)
            self.set_relay(pin_id, False)

        # enable relays
        self._relay_vcc.write(True)

        self._update_switch_state()

    def close(self) -> None:
        if self._board is None:
            return

        logging.info('Closing GPIO...')

        for input in self._inputs.values():
            input.disable_reporting()
            input.unregister_callback()

        for relay in self._relays.keys():
            self.set_relay(relay, False)
        self._relay_vcc.write(0)

        self._board.exit()
        self._board = None

    def set_relay(self, pin: ArduinoPin, state: bool) -> None:
        if self._board is None or pin not in self._relays:
            return

        self._relays[pin].write(not state)  # NB: relays are active low

    def _handle_gpio_input(self, data) -> None:
        self._update_switch_state()

    @debounce(0.1)
    def _update_switch_state(self) -> None:
        last_state: SpaceState = self.state

        top_switch_value = not self._inputs[ArduinoPin.SWITCH_TOP].value
        bottom_switch_value = not self._inputs[ArduinoPin.SWITCH_BOTTOM].value

        if self._board is None:
            logging.warning('Board is not connected')
            self.state = SpaceState.UNDETERMINED
        elif top_switch_value and bottom_switch_value:
            logging.warning('Both open and closed contacts are connected. Weird...')
            self.state = SpaceState.UNDETERMINED
        elif top_switch_value:
            logging.debug('Switch is set to \'open\' state')
            self.state = SpaceState.OPEN
        elif bottom_switch_value:
            logging.debug('Switch is set to \'closed\' state')
            self.state = SpaceState.CLOSED
        else:
            logging.debug('Switch is somewhere in between')
            self.state = SpaceState.UNDETERMINED

        if self.state != last_state and self.on_state_changed is not None:
            self.on_state_changed(self.state)

    def set_color(self, color: LampColor) -> None:
        red: bool = True if color==LampColor.RED or color==LampColor.YELLOW else False
        orange: bool = True if color==LampColor.ORANGE or color==LampColor.YELLOW else False
        green: bool = True if color==LampColor.GREEN or color==LampColor.YELLOW else False

        self.set_relay(ArduinoPin.RED1, red)
        self.set_relay(ArduinoPin.RED2, red)
        self.set_relay(ArduinoPin.ORANGE1, orange)
        self.set_relay(ArduinoPin.ORANGE2, orange)
        self.set_relay(ArduinoPin.GREEN1, green)
        self.set_relay(ArduinoPin.GREEN2, green)

    def fire_confetti(self) -> None:
        if self._confetti_timer is not None:
            return

        logging.info('Firing confetti canons')
        self._confetti_timer = Timer(
            2, self._reset_confetti
        )
        self._confetti_timer.start()
        self.set_relay(ArduinoPin.CONFETTI, True)

    def _reset_confetti(self) -> None:
        logging.debug('Resetting confetti canon relays')

        self._confetti_timer = None
        self.set_relay(ArduinoPin.CONFETTI, False)



if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

    def spacestate_callback(state: SpaceState):
        logging.info(f'Switch state changed to: {state.name}')
        if state==SpaceState.CLOSED:
            gpio.set_color(LampColor.RED)
        elif state==SpaceState.UNDETERMINED:
            gpio.set_color(LampColor.ORANGE)
        elif state==SpaceState.OPEN:
            gpio.set_color(LampColor.GREEN)

    gpio = FirmataGPIO(spacestate_callback)

    try:
        while True:
            time.sleep(0.5)

    except KeyboardInterrupt:
        logging.info('Closing...')
        gpio.close()
