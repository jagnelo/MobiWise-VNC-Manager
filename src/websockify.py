import os
import subprocess

import psutil

from src.globals import Globals
from src.iserver import IServer, State


class Websockify(IServer):
    def __init__(self, vnc_index, vnc_port):
        self.pid = Globals.NA
        self.port = Globals.base_websockify_port + vnc_index
        self.vnc_port = vnc_port
        self.state = State.Dead

    # start a websockify instance
    def start(self):
        websockify = subprocess.Popen(["websockify", "localhost:%d" % self.port, "localhost:%d" % self.vnc_port])
        self.pid = websockify.pid
        self.state = State.Unknown
        print("Started Websockify server listening on port %d (PID = %d)" % (self.port, self.pid))

    # stop this websockify instance
    def stop(self):
        os.system("kill %d" % self.pid)
        self.state = State.Dead
        print("Stopped Websockify server listening on port %d (PID = %d)" % (self.port, self.pid))

    # checks multiple external sources and correspondingly updates the state of this Websockify instance
    def check_state(self):
        old_state = self.state
        self.state = State.Unknown
        try:
            process = psutil.Process(self.pid)
            for connection in process.connections():
                if int(connection.laddr[1]) == self.port:
                    if connection.raddr and connection.status == psutil.CONN_ESTABLISHED:
                        self.state = State.Serving
                        break
                    elif not connection.raddr and connection.status == psutil.CONN_LISTEN:
                        self.state = State.Ready
        except psutil.NoSuchProcess as e:
            print("Error: ", e)
            self.state = State.Dead
        if old_state != self.state:
            print_info = (old_state, self.state, self.pid)
            print("Updated state of Websockify server from %s to %s (PID = %d)" % print_info)
