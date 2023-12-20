from dataclasses import dataclass


@dataclass(eq=True, frozen=True)
class Address:
    host: str
    port: int

    # compare
    def __le__(self, other):
        return self.port <= other.port

    def __lt__(self, other):
        return self.port < other.port

    def __ge__(self, other):
        return self.port >= other.port

    def __gt__(self, other):
        return self.port > other.port

    # json serialization
    def __repr__(self):
        return str(f"{self.host}:{self.port}")

    def __hash__(self):
        return hash((self.host, self.port))
