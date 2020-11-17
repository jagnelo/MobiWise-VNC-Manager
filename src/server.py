import os
import subprocess

from src import utils
from src.globals import Globals
from src.iserver import IServer, State
from src.vnc import VNC
from src.websockify import Websockify


class Server(IServer):
    def __init__(self):
        self.vnc = None
        self.websockify = None
        self.state = State.Dead
        self.running_process = None

    # start a vnc+websockify instance pair
    def start(self):
        self.vnc = VNC()
        self.vnc.start()

        def func(job_id):
            def delayed_start():
                if self.vnc.state == State.Dead:
                    Globals.scheduler.remove_job(job_id)
                if self.vnc.state == State.Ready:
                    Globals.scheduler.remove_job(job_id)
                    self.websockify = Websockify(self.vnc.display_index, self.vnc.port)
                    self.websockify.start()
                    path = self.vnc.get_files_dir()
                    utils.clear_and_remove_dir(path)
                    utils.ensure_dir_exists(path)
                    print_info = (self.vnc.port, self.websockify.port)
                    print("Started server pair (VNC port = %d | Websockify port = %d)" % print_info)
            return delayed_start

        job_id = utils.get_new_job_id()
        Globals.scheduler.add_job(func(job_id), 'interval', seconds=1, id=job_id)
        self.state = State.Unknown

    # stop this vnc+websockify instance pair
    def stop(self):
        self.stop_command()
        if self.vnc:
            self.vnc.stop()
        if self.websockify:
            self.websockify.stop()
        utils.clear_and_remove_dir(self.vnc.get_files_dir())
        self.state = State.Dead
        print_info = (self.vnc.port, self.websockify.port)
        print("Stopped server pair (VNC port = %d | Websockify port = %d)" % print_info)

    # updates the state of this vnc+websockify instance pair
    def check_state(self):
        old_state = self.state
        if self.vnc:
            self.vnc.check_state()
        if self.websockify:
            self.websockify.check_state()
        if self.vnc and self.websockify:
            if self.vnc.state == State.Serving and self.websockify.state == State.Serving:
                self.state = State.Serving
            elif self.vnc.state == State.Ready and self.websockify.state == State.Ready:
                self.state = State.Ready
            elif self.vnc.state == State.Dead and self.websockify.state == State.Dead:
                self.state = State.Dead
            else:
                self.state = State.Unknown
        elif not self.vnc and not self.websockify:
            self.state = State.Dead
        else:
            self.state = State.Unknown
        if old_state != self.state:
            print_info = (old_state, self.state, self.vnc.port, self.websockify.port)
            print("Updated state of server pair server from %s to %s (VNC port = %d | Websockify port = %d)" % print_info)

    # returns url for connecting to this vnc+websockify instance pair
    def get_url(self):
        return "ws://localhost:%d/websockify" % self.websockify.port if self.websockify else None

    # run a system command on the vnc instance of this server pair
    def run_command(self, command, files):
        if self.state in [State.Ready, State.Serving] and not self.running_process:
            for name in Globals.vnc_sumo_files:
                file = files[name]
                file.save(os.path.join(self.vnc.get_files_dir(), "%s.xml" % name))
            command_array = [s.strip() for s in command.split(" ") if s.strip()]
            env = utils.modify_environment({"DISPLAY": ":%d" % self.vnc.display_index})
            self.running_process = subprocess.Popen(command_array, env=env, cwd=self.vnc.get_files_dir())
            print_info = (command, self.vnc.port, self.websockify.port)
            print("Running new command on server pair (VNC port = %d | Websockify port = %d | cmd = %s)" % print_info)

    # stops a system command (if any) running on the vnc instance of this server pair
    def stop_command(self):
        if self.state in [State.Ready, State.Serving] and self.running_process:
            self.running_process.terminate()
            print_info = (self.vnc.port, self.websockify.port)
            print("Stopped command running on server pair (VNC port = %d | Websockify port = %d)" % print_info)
            self.running_process = None
