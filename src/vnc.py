import os
import subprocess

import psutil

from src.iserver import IServer, State


class VNC(IServer):
    base_display_index = 1
    vnc_resolution = {
        "width": 800,
        "height": 600
    }

    def __init__(self):
        self.display_index = IServer.NA
        self.pid = IServer.NA
        self.port = IServer.NA
        self.state = State.Dead

    # start a vnc instance
    def start(self):
        res = "%dx%d" % (VNC.vnc_resolution["width"], VNC.vnc_resolution["height"])
        self.display_index = VNC.get_available_display_index()
        subprocess.Popen(["vncserver", ":%d" % self.display_index, "-noxstartup", "-geometry", res])
        self.state = State.Unknown
        print("Started VNC server at index %d" % self.display_index)

    # stop this vnc instance
    def stop(self):
        os.system("vncserver -kill :%d" % self.display_index)
        self.state = State.Dead
        print("Stopped VNC server at index %d" % self.display_index)

    # checks multiple external sources and correspondingly updates the state of this VNC instance
    def check_state(self):
        old_state = self.state
        servers = VNC.get_vnc_server_list()
        if self.display_index in servers:
            server = servers[self.display_index]
            self.port = server["port"]
            self.pid = server["pid"]
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
        else:
            self.state = State.Dead
        if old_state != self.state:
            print_info = (self.display_index, old_state, self.state)
            print("Updated state of VNC server at index %d from %s to %s" % print_info)

    # runs the "vncserver -list" command, formats its output, and returns it
    @staticmethod
    def get_vnc_server_list():
        vnc_servers = {}
        output = subprocess.check_output(["vncserver", "-list"], text=True)
        for line in [lin for lin in output.split("\n") if lin]:
            elements = [elem for elem in line.split("\t") if elem]
            if len(elements) == 3 and elements[0].startswith(":"):
                display_index = int(elements[0].replace(":", ""))
                vnc_port = int(elements[1])
                pid = int(elements[2])
                vnc_servers[display_index] = {"port": vnc_port, "pid": pid}
        return vnc_servers

    # returns the next available display index, in ascending order and starting at 1
    @staticmethod
    def get_available_display_index():
        display_index = VNC.base_display_index
        while display_index in VNC.get_vnc_server_list():
            display_index += 1
        return display_index
