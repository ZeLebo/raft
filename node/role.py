from enum import Enum
from enum import auto


class Role(Enum):
    LEADER = auto()
    FOLLOWER = auto()
    CANDIDATE = auto()
