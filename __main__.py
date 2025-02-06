#!/home/hacker/HotelSwitch/venv/bin/python3

import pygame
import logging

from typing import Tuple

from hackerspaces import HackerSpacesNL, HH_NAME
from gpio import FirmataGPIO, LampColor
from spacestate import SpaceState, HackerHotelStateApi

# empirical approximations to match the geo coordinates to the map
NL_CENTER: Tuple[float, float] = (5.24791, 52.1372954)
NL_SCALE: Tuple[float, float] = (3.85422677912357, 4.353798024388546)


class App:
    def __init__(self) -> None:
        logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')

        pygame.init()
        pygame.mouse.set_visible(False)
        self.screen_width: int = 1080
        self.screen_height: int = 1920
        self.screen: pygame.Surface = pygame.display.set_mode(
            (self.screen_width, self.screen_height),
            flags=pygame.FULLSCREEN
        )
        pygame.display.set_caption("HotelSwitch")

        self.clock: pygame.time.Clock = pygame.time.Clock()

        self.state: SpaceState = SpaceState.UNDETERMINED

        self.hsnl: HackerSpacesNL = HackerSpacesNL()
        self.gpio: FirmataGPIO = FirmataGPIO(self._handle_gpio_state)
        self.space_api: HackerHotelStateApi = HackerHotelStateApi()

        self.running: bool = True

        self.show_spark: bool = False

        self.background_image: pygame.Surface = pygame.image.load("data/hsnl.png")
        self.open_sfx: pygame.mixer.Sound = pygame.mixer.Sound("data/open.wav")
        self.close_sfx: pygame.mixer.Sound = pygame.mixer.Sound("data/close.wav")


    def _handle_events(self) -> None:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                self.running = False

        keys = pygame.key.get_pressed()
        if keys[pygame.K_ESCAPE] or keys[pygame.K_q]:
            self.running = False

        if keys[pygame.K_c]:
            self.gpio.fire_confetti()


    def _handle_gpio_state(self, state: SpaceState) -> None:
        self.state = state

        logging.info(f"Hacker Hotel state: {state.name}")

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

        return

        self.space_api.set_state(state)


    def update(self) -> None:
        self._handle_events()

        self.hsnl.update()


    def draw(self) -> None:
        if self.show_spark:
            self.screen.fill((255,255,255))
            self.show_spark = False
            return

        self.screen.fill((0, 0, 0))
        self.screen.blit(self.background_image, (0, 0))

        screen_center: Tuple[int, int] = (self.screen_width // 2, self.screen_height // 2)

        for space in self.hsnl.spaces:
            x: int = screen_center[0] + int((space.lon - NL_CENTER[0]) / NL_SCALE[0] * self.screen_width)
            y: int = screen_center[1] - int((space.lat - NL_CENTER[1]) / NL_SCALE[1] * self.screen_height)

            radius = 8

            state: SpaceState = space.state
            if space.name == HH_NAME:
                state = self.gpio.state
                radius = 16

            if state == SpaceState.OPEN:
                color: Tuple[int, int, int] = (0, 255, 0)
            elif state == SpaceState.CLOSED:
                color: Tuple[int, int, int] = (255, 0, 0)
            else:
                color: Tuple[int, int, int] = (255, 255, 0)

            pygame.draw.circle(
                self.screen,
                color,
                (x, y),
                radius
            )


    def run(self) -> None:
        try:
            while self.running:
                self.update()
                self.draw()
                pygame.display.flip()

                self.clock.tick(60)
        except KeyboardInterrupt:
            pass

        # cleanup
        self.gpio.close()
        self.hsnl.stop()


if __name__ == "__main__":
    app: App = App()
    app.run()
