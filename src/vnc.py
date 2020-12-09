import os
import subprocess

import psutil

import utils
from globals import Globals
from iserver import IServer, State


class VNC(IServer):
    def __init__(self):
        self.display_index = Globals.NA
        self.pid = Globals.NA
        self.port = Globals.NA
        self.state = State.Dead
        self.running_process = None

    # start a vnc instance
    def start(self):
        res = "%dx%d" % (Globals.VNC_RESOLUTION["width"], Globals.VNC_RESOLUTION["height"])
        self.display_index = VNC.get_available_display_index()
        vnc = subprocess.Popen(["vncserver", ":%d" % self.display_index, "-noxstartup", "-geometry", res])
        vnc.wait(timeout=5)
        self.state = State.Unavailable
        path = self.get_files_dir()
        utils.clear_dir(path)
        utils.ensure_dir_exists(path)
        print("Started VNC server at index %d" % self.display_index)

    # run a system command on this vnc instance
    def run_command(self, command):
        if self.state == State.Serving and not self.running_process:
            command_array = [s.strip() for s in command.split(" ") if s.strip()]
            env = utils.modify_environment({"DISPLAY": ":%d" % self.display_index})
            self.running_process = subprocess.Popen(command_array, env=env, cwd=self.get_files_dir())
            print("Running new command running on VNC server at index %d (cmd = %s)" % (self.display_index, command))

    # stops a system command (if any) running on the vnc instance
    def stop_command(self):
        if self.running_process:
            self.running_process.terminate()
            self.running_process = None
            utils.clear_dir(self.get_files_dir())
            print("Stopped command running on VNC server at index %d" % self.display_index)

    # stop this vnc instance
    def stop(self):
        self.stop_command()
        os.system("vncserver -kill :%d" % self.display_index)
        self.state = State.Dead
        utils.clear_and_remove_dir(self.get_files_dir())
        print("Stopped VNC server at index %d" % self.display_index)

    # checks multiple external sources and correspondingly updates the state of this VNC instance
    def check_state(self) -> bool:
        old_state = self.state
        servers = VNC.get_vnc_server_list()
        if self.display_index in servers:
            server = servers[self.display_index]
            self.port = server["port"]
            self.pid = server["pid"]
            self.state = State.Unavailable
            try:
                process = psutil.Process(self.pid)
                for connection in process.connections():
                    if int(connection.laddr[1]) == self.port:
                        if connection.raddr and connection.status == psutil.CONN_ESTABLISHED:
                            self.state = State.Serving
                            break
                        elif not connection.raddr and connection.status == psutil.CONN_LISTEN:
                            self.state = State.Ready
            except BaseException as e:
                print("Error: ", e)
                self.state = State.Dead
        else:
            self.state = State.Dead
        if old_state != self.state:
            print_info = (self.display_index, old_state, self.state)
            print("Updated state of VNC server at index %d from %s to %s" % print_info)
            return True
        return False

    def describe_state(self) -> str:
        proc_info = "Running [PID = %d]" % self.running_process.pid if self.running_process else self.running_process
        info = (self.display_index, self.pid, self.port, self.state, proc_info)
        return "Display index = %d | PID = %d | Port = %d | State = %s | Running process = %s" % info

    # returns the path to the folder containing files used by this vnc instance
    def get_files_dir(self):
        return os.path.join(Globals.VNC_FILES_DIR, "%d" % self.display_index)

    # saves files to the directory of this vnc instance
    def store_files_to_dir(self, files):
        path = self.get_files_dir()
        utils.ensure_dir_exists(path)
        utils.clear_dir(path)
        for name in Globals.VNC_SUMO_FILES:
            file = files[name]
            file.save(os.path.join(path, "%s.xml" % name))

    # runs the "vncserver -list" command, formats its output, and returns it
    @staticmethod
    def get_vnc_server_list():
        vnc_servers = {}
        try:
            output = subprocess.check_output(["vncserver", "-list"], text=True)
            for line in [lin for lin in output.split("\n") if lin]:
                elements = [elem for elem in line.split("\t") if elem]
                if len(elements) == 3 and elements[0].startswith(":"):
                    display_index = int(elements[0].replace(":", ""))
                    vnc_port = int(elements[1])
                    if "stale" not in elements[2].lower():
                        pid = int(elements[2])
                        vnc_servers[display_index] = {"port": vnc_port, "pid": pid}
        except BaseException as e:
            print("Error: ", e)
        return vnc_servers

    # returns the next available display index, in ascending order and starting at 1
    @staticmethod
    def get_available_display_index():
        display_index = Globals.BASE_DISPLAY_INDEX
        while display_index in VNC.get_vnc_server_list():
            display_index += 1
        return display_index
