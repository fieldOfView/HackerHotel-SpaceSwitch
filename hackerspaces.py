import requests
import time

from spacestate import SpaceState

GEOJSON_URL = 'https://hackerspaces.nl/hsmap/hsnl.geojson'
REFRESH_PERIOD = 120  # seconds

class CoordinateRange:
    def __init__(self):
        self.reset()

    def reset(self):
        self.min = None
        self.max = None
        self.range = None
        self.center = None
        self.count = 0
        self.average = None

    def include(self, value: float):
        if self.min is None or value < self.min:
            self.min = value
        if self.max is None or value > self.max:
            self.max = value

        self.range = self.max - self.min
        self.center = (self.min + self.max) / 2

        self.average = (self.average * self.count + value) / (self.count + 1) if self.average is not None else value
        self.count += 1

    def __str__(self):
        return f'CoordinateRange: {self.min} - {self.max} ({self.range})'


class HackerSpace:
    def __init__(self, name: str, lat: float, lon: float, state: SpaceState):
        self.name = name
        self.lat = lat
        self.lon = lon
        self.state = state

class HackerSpacesNL:
    def __init__(self):
        self.spaces: list[HackerSpace] = []
        self.lat_range = CoordinateRange()
        self.lon_range = CoordinateRange()

        self._data = {}
        self._last_refresh = 0


    def update(self):
        if time.monotonic() - self._last_refresh > REFRESH_PERIOD:
            self._refresh_data()

    def _refresh_data(self):
        print('Refreshing hsnl geojson data')
        try:
            self._data = requests.get(GEOJSON_URL).json()
        except:
            self._data.clear()

        self._last_refresh = time.monotonic()

        self.spaces.clear()
        self.lat_range.reset()
        self.lon_range.reset()

        if not self._data:
            print('Error fetching hsnl geojson data')
            return

        includes_hackerhotel = False

        for feature in self._data['features']:
            try:
                name = feature['properties']['name']
                lat = float(feature['geometry']['coordinates'][1])
                lon = float(feature['geometry']['coordinates'][0])
                state = SpaceState.UNDETERMINED
                if feature['properties']['marker-symbol'] == '/hsmap/hs_open.png':
                    state = SpaceState.OPEN
                elif feature['properties']['marker-symbol'] == '/hsmap/hs_closed.png':
                    state = SpaceState.CLOSED

                self.lat_range.include(lat)
                self.lon_range.include(lon)

                if name == "Hacker Hotel":
                    includes_hackerhotel = True

                self.spaces.append(HackerSpace(name, lat, lon, state))
            except:
                print('Error parsing feature:', feature)

        if not includes_hackerhotel:
            print('Hacker Hotel not found in geojson data; adding manually')

            self.spaces.append(HackerSpace("Hacker Hotel", 52.2208671, 5.7208085, SpaceState.UNDETERMINED))

if __name__ == '__main__':
    hsnl = HackerSpacesNL()
    hsnl.update()

    for space in hsnl.spaces:
        print(space.name, space.lat, space.lon, space.state)
    print(hsnl.lat_range, hsnl.lon_range)