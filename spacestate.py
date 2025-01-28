from enum import Enum

SPACESTATE_URL:str = 'http://hackerhotel.tdvenlo.nl/throwswitch.php'

class SpaceState(Enum):
    CLOSED = 0
    UNDETERMINED = 1
    OPEN = 2
