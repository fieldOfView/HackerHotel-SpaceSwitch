import pygame
from typing import List, Tuple, Optional

from hackerspaces import HackerSpace, HH_NAME
from spacestate import SpaceState
from gpio import LampColor


# empirical approximations to match the geo coordinates to the map
NL_CENTER: Tuple[float, float] = (5.24791, 52.1372954)
NL_SCALE: Tuple[float, float] = (3.854227, 2.449011)


class HackerSpacesRenderer():
    def __init__(self):
        self._background_image: pygame.Surface = pygame.image.load('data/hsnl.png')

        self._surface:pygame.Surface = self._background_image.copy()
        self._surface.fill((0,0,0))

        self._surface_width = self._surface.get_width()
        self._surface_height = self._surface.get_height()

        self._hotel_space_coordinates: Optional[Tuple[int, int]] = None

    def update(self, spaces: List[HackerSpace], hackerhotel_state:SpaceState):
        self._surface.fill((0, 0, 0))
        self._surface.blit(self._background_image, (0, 0))

        self._hotel_space = None
        for space in spaces:
            x: int = (self._surface_width // 2) + int((space.lon - NL_CENTER[0]) / NL_SCALE[0] * self._surface_width)
            y: int = (self._surface_height // 2) - int((space.lat - NL_CENTER[1]) / NL_SCALE[1] * self._surface_width)

            radius = 8

            state: SpaceState = space.state
            if space.name == HH_NAME:
                self._hotel_space_coordinates = (x, y)
                state = hackerhotel_state
                radius = 16

            if state == SpaceState.OPEN:
                color: Tuple[int, int, int] = LampColor.GREEN.value
            elif state == SpaceState.CLOSED:
                color: Tuple[int, int, int] = LampColor.RED.value
            else:
                color: Tuple[int, int, int] = LampColor.ORANGE.value

            pygame.draw.circle(
                self._surface,
                color,
                (x, y),
                radius
            )

    def draw(self, destination: pygame.Surface, x: int=0, y: int=0):
        destination.blit(self._surface, (x, y))

    def get_hotel_coordinates(self) -> Optional[Tuple[int, int]]:
        return self._hotel_space_coordinates
