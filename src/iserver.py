from enum import Enum


class State(Enum):
    Dead = -1
    Unavailable = 0
    Ready = 1
    Serving = 2


class IServer:
    def start(self):
        raise NotImplementedError

    def stop(self):
        raise NotImplementedError

    def check_state(self) -> bool:
        raise NotImplementedError

    def describe_state(self) -> str:
        raise NotImplementedError
