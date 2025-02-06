import requests
from threading import Thread, Lock, Event
import logging
import copy
import time
from typing import List, Dict, Any

from spacestate import SpaceState

GEOJSON_URL: str = 'https://hackerspaces.nl/hsmap/hsnl.geojson'
REFRESH_PERIOD: int = 60  # seconds

HH_LAT: float = 52.2208671
HH_LON: float = 5.7208085
HH_NAME: str = "Hacker Hotel"

class HackerSpace:
    def __init__(self, name: str, lat: float, lon: float, state: SpaceState):
        self.name: str = name
        self.lat: float = lat
        self.lon: float = lon
        self.state: SpaceState = state


class _GetDataThread(Thread):
    def __init__(self) -> None:
        super().__init__()

        self._data_event: Event = Event()
        self._data_lock: Lock = Lock()
        self._stop_event: Event = Event()
        self._last_refresh: float = 0

        self._data: Dict[str, Any] = {}

    def run(self) -> None:
        while not self._stop_event.is_set():
            current_time: float = time.monotonic()
            if current_time - self._last_refresh > REFRESH_PERIOD:
                logging.info('Refreshing hsnl geojson data')

                with self._data_lock:
                    try:
                        self._data = requests.get(GEOJSON_URL).json()
                    except Exception as e:
                        self._data.clear()
                self._last_refresh: float = time.monotonic()
                self._data_event.set()

            time.sleep(0.5)

    def stop(self) -> None:
        self._stop_event.set()

    def has_data(self) -> None:
        if(self._data_event.is_set()):
            self._data_event.clear()
            return True

        return False

    def get_data(self) -> Dict[str, Any]:
        with self._data_lock:
            return copy.deepcopy(self._data)


class HackerSpacesNL:
    def __init__(self):
        self.spaces: List[HackerSpace] = []

        self._data_thread = _GetDataThread()
        self._data_thread.start()

    def stop(self) -> None:
        logging.debug("Stopping hsnl updates")
        self._data_thread.stop()
        self._data_thread.join()


    def update(self, wait: bool=False) -> None:
        if wait:
            logging.debug("Waiting for data to be fetched")
            while not self._data_thread.has_data():
                time.sleep(0.5)
        else:
            if not self._data_thread.has_data():
                return

        data = self._data_thread.get_data()
        self.spaces.clear()

        if not data:
            logging.error('Error fetching hsnl geojson data')
            return

        includes_hackerhotel: bool = False

        for feature in data['features']:
            try:
                name: str = feature['properties']['name']
                lat: float = float(feature['geometry']['coordinates'][1])
                lon: float = float(feature['geometry']['coordinates'][0])

                state: SpaceState = SpaceState.UNDETERMINED
                if feature['properties']['marker-symbol'] == '/hsmap/hs_open.png':
                    state = SpaceState.OPEN
                elif feature['properties']['marker-symbol'] == '/hsmap/hs_closed.png':
                    state = SpaceState.CLOSED

                if name == "Hacker Hotel":
                    includes_hackerhotel: bool = True

                self.spaces.append(HackerSpace(name, lat, lon, state))
            except Exception as e:
                logging.error(f'Error parsing feature: {feature}', e)

        if not includes_hackerhotel:
            logging.info('Hacker Hotel not found in geojson data; adding manually')

            self.spaces.append(HackerSpace(HH_NAME, HH_LAT, HH_LON, SpaceState.UNDETERMINED))


if __name__ == '__main__':
    logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')

    hsnl: HackerSpacesNL = HackerSpacesNL()
    hsnl.update(wait=True)
    hsnl.stop()

    for space in hsnl.spaces:
        logging.info(f"{space.name} - Lat: {space.lat}, Lon: {space.lon}, State: {space.state}")
