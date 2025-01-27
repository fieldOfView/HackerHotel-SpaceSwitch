import pygame
import random

from hackerspaces import HackerSpacesNL
from gpio import FirmataGPIO


class Ball:
    def __init__(self, screen_width, screen_height):
        self.screen_width = screen_width
        self.screen_height = screen_height
        self.radius = random.randint(10, 30)
        self.x = random.randint(self.radius, self.screen_width - self.radius)
        self.y = random.randint(self.radius, self.screen_height - self.radius)

        self.color = (random.randint(0, 255), random.randint(0, 255), random.randint(0, 255))
        self.speed_x = random.uniform(-3, 3)
        self.speed_y = random.uniform(-3, 3)

    def update(self):
        self.x += self.speed_x
        self.y += self.speed_y

        if self.x - self.radius < 0 or self.x + self.radius > self.screen_width:
            self.speed_x *= -1
        if self.y - self.radius < 0 or self.y + self.radius > self.screen_height:
            self.speed_y *= -1

    def draw(self, screen):
        pygame.draw.circle(screen, self.color, (int(self.x), int(self.y)), self.radius)


class App:
    def __init__(self):
        pygame.init()
        self.screen_width = 720
        self.screen_height = 1280
        self.screen = pygame.display.set_mode((self.screen_width, self.screen_height))
        pygame.display.set_caption("HotelSwitch")

        self.clock = pygame.time.Clock()
        self.balls = [Ball(self.screen_width, self.screen_height) for _ in range(10)]

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

        #for ball in self.balls:
        #    ball.update()

    def draw(self):
        self.screen.fill((0, 0, 0))
        #for ball in self.balls:
        #    ball.draw(self.screen)

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