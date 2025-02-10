import pygame
import time
import logging
import json
from typing import List, Dict, Tuple, Optional

from spacestate import SpaceState
from gpio import FirmataGPIO, LampColor


class Assets():
    def __new__(cls):
        if not hasattr(cls, 'instance'):
            cls.instance = super(Assets, cls).__new__(cls)
        return cls.instance

    def __init__(self):
        self._surfaces:Dict[str, pygame.Surface] = {}
        self._sounds:Dict[str, pygame.mixer.Sound] = {}

    def get_surface(self, filename: str) -> pygame.Surface:
        if filename not in self._surfaces:
            self._surfaces[filename] = pygame.image.load("data/" + filename)

        return self._surfaces[filename]

    def get_sound(self, filename: str) -> pygame.mixer.Sound:
        if filename not in self._sounds:
            self._sounds[filename] = pygame.mixer.Sound("data/" + filename)

        return self._sounds[filename]


class Phrase():
    def __init__(self, duration: float, actor: Optional[str] = None,
                 from_position: Tuple[int, int] = (0,0), to_position: Optional[Tuple[int, int]] = None,
                 color: Optional[str] = None, sound: Optional[str] = None) -> None:

        self.duration: float = duration
        self.actor: Optional[pygame.Surface] = Assets().get_surface(actor) if actor else None # Optional[pygame.Surface]

        self.from_position: Tuple[int, int] = from_position
        self.to_position: Tuple[int, int] = to_position if to_position else from_position

        self.color: Optional[LampColor] = LampColor[color] if color else None
        self.sound: Optional[pygame.mixer.Sound] = Assets().get_sound(sound) if sound else None

    def __repr__(self):
        return f"<Phrase: duration: {self.duration}, actor: {self.actor}>"

    @classmethod
    def from_json(cls, json: Dict[str, any]) -> 'Phrase':
        return cls(
            duration=json['duration'],
            actor=json['actor'] if 'actor' in json else None,
            from_position=tuple(json['from']) if 'from' in json else (0,0),
            to_position=tuple(json['to']) if 'to' in json else None,
            color=json['color'] if 'color' in json else None,
            sound=json['sound'] if 'sound' in json else None
        )


class StateAnimationRenderer():
    def __init__(self, gpio: FirmataGPIO) -> None:
        self._gpio = gpio

        logging.info("Loading state animations...")

        with open('data/animations.json') as json_file:
            json_data = json.load(json_file)

        self._phrases: Dict[SpaceState, List[Phrase]] = {}
        for state in SpaceState:
            self._phrases[state] = [
                Phrase.from_json(phrase_json) for phrase_json in json_data[state.name]
            ] if state.name in json_data else []

        self._state = SpaceState.UNDETERMINED
        self._state_start_time: float = 0

        self._phrase_number: int = 0
        self._phrase_start: float = 0

    def stop(self) -> None:
        self._gpio.close()

    def set_state(self, state: SpaceState) -> None:
        if state != self._state:
            self._state = state
            self._state_start_time = time.monotonic()

    def draw(self, destination: pygame.Surface) -> None:
        if self._state not in self._phrases:
            # we don't have anything to do in this state
            return

        phrases: List[Phrase] = self._phrases[self._state]

        if self._phrase_number >= len(phrases):
            # all phrases for this state have been played out
            return

        phrase: Phrase = phrases[self._phrase_number]
        current_time: float = time.monotonic()

        if current_time - self._phrase_start > phrase.duration:
            self._phrase_number += 1

            if self._phrase_number >= len(phrases):
                # nothing left to do
                return

            phrase = phrases[self._phrase_number]

            self._phrase_start = current_time
            phrase.duration = phrase.duration
            logging.debug(f"Entering phrase: {self._state.name}.{self._phrase_number}")

            # change the lamps if necessary
            if phrase.color:
                self._gpio.set_color(phrase.color)

            # play a sound if necessary
            if phrase.sound:
                phrase.sound.play()

        phrase_progress = (current_time - self._phrase_start) / phrase.duration

        # draw the actor to the destination surface, if an actor is specified
        if phrase.actor:
            coordinate = tuple(
                int(0.5 + (c[0] * (1-phrase_progress)) + (c[1] * phrase_progress))
                for c in zip (phrase.from_position, phrase.to_position)
            )
            destination.blit(phrase.actor, coordinate)



if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

    pygame.init()

    pygame.init()
    screen: pygame.Surface = pygame.display.set_mode(
        (1080, 1600),
    )
    clock: pygame.time.Clock = pygame.time.Clock()

    gpio = FirmataGPIO()

    anim = StateAnimationRenderer(gpio)
    anim.set_state(SpaceState.OPEN)

    try:
        while True:
            screen.fill((0,0,0))
            anim.draw(screen)

            pygame.display.flip()
            clock.tick(60)

    except KeyboardInterrupt:
        logging.info('Closing...')
        anim.stop()


# Animation steps:
#   pause
#   dimi up to portrait
#   dimi confused
#   dimi up to hh marker
#   whack -> GREEN
#   raised arm
#   ORANGE
#   dimi raised arm confused
#   whack -> GREEN
#   raised arm
#   ORANGE
#   whack -> GREEN
#   raised arm
#   whack -> GREEN
#   raised arm
#   whack -> GREEN -> BOOM
#   dimi confused
#   dimi thumbs up
#   dimi leaves
