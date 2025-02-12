#!/home/hacker/HotelSwitch/venv/bin/python3

import pygame
import logging
import traceback
from logging.handlers import RotatingFileHandler
from typing import Tuple, List

from hackerspaces import HackerSpace, HackerSpacesNL
from hackerspaces_renderer import HackerSpacesRenderer
from gpio import FirmataGPIO, LampColor
from spacestate import SpaceState, HackerHotelStateApi
from state_animation import StateAnimationRenderer

# empirical approximations to match the geo coordinates to the map
NL_CENTER: Tuple[float, float] = (5.24791, 52.1372954)
NL_SCALE: Tuple[float, float] = (3.85422677912357, 4.353798024388546)


class App:
    def __init__(self) -> None:
        logging.basicConfig(
            level=logging.DEBUG,
            format='%(asctime)s - %(levelname)s - %(module)s:%(funcName)s - %(message)s',
            handlers=[
                RotatingFileHandler('./logs/hotelstate.log', maxBytes=100000, backupCount=10),
                logging.StreamHandler()
            ]
        )

        pygame.init()
        pygame.mouse.set_visible(False)
        self.screen_width: int = 1080
        self.screen_height: int = 1920
        self.screen: pygame.Surface = pygame.display.set_mode(
            (self.screen_width, self.screen_height),
            flags=pygame.FULLSCREEN
        )
        pygame.display.set_caption('HotelSwitch')

        self.clock: pygame.time.Clock = pygame.time.Clock()

        self.open_sfx: pygame.mixer.Sound = pygame.mixer.Sound('data/open.wav')
        self.close_sfx: pygame.mixer.Sound = pygame.mixer.Sound('data/close.wav')

        self.state: SpaceState = SpaceState.UNDETERMINED  # data from FirmataGPIO
        self.spaces: List[HackerSpace] = []  # data from HackerSpacesNL

        self.space_api: HackerHotelStateApi = HackerHotelStateApi()

        self.gpio: FirmataGPIO = FirmataGPIO(self._handle_gpio_state)
        self.hsnl: HackerSpacesNL = HackerSpacesNL(self._handle_hackerspaces_update)

        self.hsnl_renderer: HackerSpacesRenderer = HackerSpacesRenderer()
        self.animation_renderer: StateAnimationRenderer = StateAnimationRenderer(self.gpio)

        self.exit_app: bool = False
        self.show_spark: bool = False



    def _handle_events(self) -> None:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                self.exit_app = True

        keys = pygame.key.get_pressed()
        if keys[pygame.K_ESCAPE] or keys[pygame.K_q]:
            self.exit_app = True

        if keys[pygame.K_c]:
            self.gpio.fire_confetti()


    def _handle_gpio_state(self, state: SpaceState) -> None:
        if hasattr(self, 'animation_renderer') and state != self.state:
            self.animation_renderer.set_state(state)
        self.state = state

        logging.info(f'Hacker Hotel state: {state.name}')

        self.show_spark = True

        if state == SpaceState.UNDETERMINED:
            self.open_sfx.play()
        else:
            self.close_sfx.play()

        # update relays via GPIO
        if state == SpaceState.OPEN:
            self.gpio.set_color(LampColor.GREEN)
        elif state == SpaceState.UNDETERMINED:
            self.gpio.set_color(LampColor.ORANGE)
        elif state == SpaceState.CLOSED:
            self.gpio.set_color(LampColor.RED)

        self.space_api.set_state(state)

        self.hsnl_renderer.update(self.spaces, self.state)


    def _handle_hackerspaces_update(self, spaces: List[HackerSpace]) -> None:
        self.spaces = spaces
        self.hsnl_renderer.update(self.spaces, self.state)


    def update(self) -> None:
        self._handle_events()
        hotel_coordinates = self.hsnl_renderer.get_hotel_coordinates()
        if hotel_coordinates:
            self.animation_renderer.set_hotel_coordinates(hotel_coordinates)


    def draw(self) -> None:
        if self.show_spark:
            self.screen.fill((255,255,255))
            self.show_spark = False
            return

        self.screen.fill((0,0,0))
        self.hsnl_renderer.draw(self.screen)
        self.animation_renderer.draw(self.screen)


    def run(self) -> None:
        try:
            while not self.exit_app:
                self.update()
                self.draw()
                pygame.display.flip()

                self.clock.tick(60)
        except KeyboardInterrupt:
            pass
        except Exception:
            traceback.print_exc()

        # cleanup
        self.gpio.close()
        self.hsnl.stop()


if __name__ == '__main__':
    app: App = App()
    app.run()
