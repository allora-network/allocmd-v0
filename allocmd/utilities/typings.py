from enum import Enum, auto

class Command(Enum):
    DEPLOY = auto()
    INIT = auto()


class BlocklessNodeType(Enum):
    worker = auto()
    reputer = auto()
