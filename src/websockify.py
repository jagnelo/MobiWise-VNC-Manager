import os
import subprocess

import psutil

from globals import Globals
from iserver import IServer, State


class Websockify(IServer):
    def __init__(self):
        self.pid = Globals.NA
        self.port = Globals.WEBSOCKIFY_PORT
        self.state = State.Dead

    # start a websockify instance
    def start(self):
        websockify = subprocess.Popen(["websockify", "localhost:%d" % self.port, "--token-plugin", "TokenFile",
                                       "--token-source", Globals.TOKENS_FILE_DIR, "--log-file", "../websockify.log",
                                       "--verbose", "--cert", Globals.MOBIWISE_CERT_FILE, "--ssl-only"])
        self.pid = websockify.pid
        self.state = State.Unavailable
        print("Started Websockify server listening on port %d (PID = %d)" % (self.port, self.pid))

    # stop this websockify instance
    def stop(self):
        os.system("kill %d" % self.pid)
        self.state = State.Dead
        print("Stopped Websockify server listening on port %d (PID = %d)" % (self.port, self.pid))

    # checks multiple external sources and correspondingly updates the state of this Websockify instance
    def check_state(self) -> bool:
        old_state = self.state
        self.state = State.Unavailable
        try:
            process = psutil.Process(self.pid)
            self.state = State.Ready
            if process.connections():
                self.state = State.Serving
        except BaseException as e:
            print("Error: ", e)
            self.state = State.Dead
        if old_state != self.state:
            print_info = (old_state, self.state, self.pid)
            print("Updated state of Websockify server from %s to %s (PID = %d)" % print_info)
            return True
        return False

    def describe_state(self) -> str:
        info = (self.pid, self.port, self.state)
        return "PID = %d | Port = %d | State = %s" % info
