import requests
import time
from typing import List, Dict, Any

from spacestate import SpaceState

GEOJSON_URL: str = 'https://hackerspaces.nl/hsmap/hsnl.geojson'
REFRESH_PERIOD: int = 120  # seconds

HH_LAT: float = 52.2208671
HH_LON: float = 5.7208085
HH_NAME: str = "Hacker Hotel"

class HackerSpace:
    def __init__(self, name: str, lat: float, lon: float, state: SpaceState):
        self.name: str = name
        self.lat: float = lat
        self.lon: float = lon
        self.state: SpaceState = state

class HackerSpacesNL:
    def __init__(self):
        self.spaces: List[HackerSpace] = []

        self._last_refresh: float = 0


    def update(self) -> None:
        current_time: float = time.monotonic()
        if current_time - self._last_refresh > REFRESH_PERIOD:
            self._refresh_data()

    def _refresh_data(self) -> None:
        print('Refreshing hsnl geojson data')

        data: Dict[str, Any] = {}
        try:
            data = requests.get(GEOJSON_URL).json()
        except Exception as e:
            pass

        self._last_refresh: float = time.monotonic()

        self.spaces.clear()

        if not data:
            print('Error fetching hsnl geojson data')
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
                print(f'Error parsing feature: {feature}', e)

        if not includes_hackerhotel:
            print('Hacker Hotel not found in geojson data; adding manually')

            self.spaces.append(HackerSpace(HH_NAME, HH_LAT, HH_LON, SpaceState.UNDETERMINED))


if __name__ == '__main__':
    hsnl: HackerSpacesNL = HackerSpacesNL()
    hsnl.update()

    for space in hsnl.spaces:
        print(space.name, space.lat, space.lon, space.state)
