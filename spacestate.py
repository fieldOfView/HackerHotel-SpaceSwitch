import requests
import logging
from enum import Enum

from spacestatesecrets import API_KEY

SPACESTATE_URL:str = 'http://hackerhotel.tdvenlo.nl/throwswitch.php'

class SpaceState(Enum):
    CLOSED = 0
    UNDETERMINED = 1
    OPEN = 2

class HackerHotelStateApi():
    def __init__(self):
        self.state: SpaceState = SpaceState.UNDETERMINED
        pass

    def set_state(self, state: SpaceState) -> None:
        if (state == self.state):
            return

        self.state = state
        try:
            requests.post(SPACESTATE_URL, json={
                "API_key": API_KEY,
                "sstate": "true" if self.state == SpaceState.OPEN else "false"
            })
        except Exception as e:
            logging.error("Failed to POST state", e)
