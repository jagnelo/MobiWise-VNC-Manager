from enum import Enum


class State(Enum):
    Dead = -1
    Unknown = 0
    Ready = 1
    Serving = 2


class IServer:
    NA = -1

    def start(self):
        raise NotImplementedError

    def stop(self):
        raise NotImplementedError

    def check_state(self):
        raise NotImplementedError
