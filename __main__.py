import pygame
import random

from hackerspaces import HackerSpacesNL
from gpio import FirmataGPIO


class App:
    def __init__(self):
        pygame.init()
        self.screen_width = 720
        self.screen_height = 1280
        self.screen = pygame.display.set_mode((self.screen_width, self.screen_height))
        pygame.display.set_caption("HotelSwitch")

        self.clock = pygame.time.Clock()

        self.hsnl = HackerSpacesNL()
        self.gpio = FirmataGPIO()

        self.running = True

    def _handle_events(self):
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                self.running = False

        keys = pygame.key.get_pressed()
        if keys[pygame.K_ESCAPE] or keys[pygame.K_q]:
            self.running = False

    def update(self):
        self._handle_events()

        self.hsnl.update()

    def draw(self):
        self.screen.fill((0, 0, 0))

        if self.hsnl.lat_range.range is not None and self.hsnl.lon_range.range is not None:
            for space in self.hsnl.spaces:
                x = int((space.lon - self.hsnl.lon_range.min) / self.hsnl.lon_range.range * self.screen_width)
                y = int((space.lat - self.hsnl.lat_range.min) / self.hsnl.lat_range.range * self.screen_height)

                pygame.draw.circle(self.screen, (0, 255, 0) if space.state else (255, 0, 0), (x, y), 8)


    def run(self):
        while self.running:
            self.update()
            self.draw()
            pygame.display.flip()

            self.clock.tick(60)

        if self.gpio is not None:
            self.gpio.close()


if __name__ == "__main__":
    app = App()
    app.run()