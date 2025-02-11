import requests
from threading import Thread
from enum import Enum
import logging
from typing import Optional

from debounce import debounce
from spacestatesecrets import API_KEY

SPACESTATE_URL:str = 'https://state.hackerhotel.nl/throwswitch.php'


class SpaceState(Enum):
    CLOSED = 0
    UNDETERMINED = 1
    OPEN = 2


class _PostStateThread(Thread):
    def __init__(self, state: SpaceState) -> None:
        super().__init__()
        self._space_open: str = 'true' if state == SpaceState.OPEN else 'false'

    def run(self) -> None:
        logging.debug(f'POST state \'{self._space_open}\' to {SPACESTATE_URL}')
        try:
            response = requests.post(SPACESTATE_URL, json={
                'API_key': API_KEY,
                'sstate': self._space_open
            })
        except Exception as e:
            logging.error(f'Error posting state: {str(e)}')
            return

        if response.status_code != 200:
            logging.error(f'Got a non-ok return code while posting state: {response.status_code}')
            return

        if 'Wrong key' in response.text:
            logging.warning('Wrong key for posting state')
            return

        logging.debug('State post success')


class HackerHotelStateApi():
    def __init__(self):
        self.state: Optional[SpaceState] = None

    @debounce(1)
    def set_state(self, state: SpaceState) -> None:
        if (state == self.state):
            logging.debug(f'State was already set to {state.name}')
            return
        logging.info(f'Setting HackerHotel state to {state.name}')
        self.state = state

        post_thread = _PostStateThread(state)
        post_thread.start()


if __name__ == '__main__':
    import time

    logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')

    logging.debug('Setting state')
    api = HackerHotelStateApi()
    api.set_state(SpaceState.OPEN) # This one gets eaten by the debounce
    time.sleep(.25)
    api.set_state(SpaceState.CLOSED)
    logging.debug('Set to closed')

    time.sleep(5)
    api.set_state(SpaceState.OPEN)
    logging.debug('Set to open')

    logging.debug('Starting loop, press Ctrl-C to end')
    while True:
        time.sleep(1)