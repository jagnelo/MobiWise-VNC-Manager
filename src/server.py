from apscheduler.schedulers.background import BackgroundScheduler

from src.iserver import IServer, State
from src.vnc import VNC
from src.websockify import Websockify


class Server(IServer):
    job_id = IServer.NA
    scheduler = BackgroundScheduler()

    def __init__(self):
        self.vnc = None
        self.websockify = None
        self.state = State.Dead
        self.user_id = None
        self.files_path = None
        self.running_process = None

    # start a vnc+websockify instance pair
    def start(self):
        self.vnc = VNC()
        self.vnc.start()

        def func(job_id):
            def delayed_start():
                if self.vnc.state == State.Dead:
                    Server.scheduler.remove_job(job_id)
                if self.vnc.port != IServer.NA:
                    Server.scheduler.remove_job(job_id)
                    self.websockify = Websockify(self.vnc.port)
                    self.websockify.start()
                    print_info = (self.vnc.port, self.websockify.port)
                    print("Started server pair (VNC port = %d | Websockify port = %d)" % print_info)
            return delayed_start

        job_id = Server.get_job_id()
        Server.scheduler.add_job(func(job_id), 'interval', seconds=1, id=job_id)
        self.state = State.Unknown

    # stop this vnc+websockify instance pair
    def stop(self):
        if self.vnc:
            self.vnc.stop()
        if self.websockify:
            self.websockify.stop()
        self.state = State.Dead
        print_info = (self.vnc.port, self.websockify.port)
        print("Stopped server pair (VNC port = %d | Websockify port = %d)" % print_info)

    # updates the state of this vnc+websockify instance pair
    def check_state(self):
        old_state = self.state
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

    # run a system command on a given vnc display
    def run_command(display_index, command):
        command_array = [s.strip() for s in command.split(" ") if s.strip()]
        env = modify_environment({"DISPLAY": ":%d" % display_index})
        process = subprocess.Popen(command_array, env=env, cwd=get_files_dir(display_index))
        pool[display_index]["running_process"] = process
        print("Running new command on server pair at index %d (cmd = %s)" % (display_index, command))

    # stops a system command (if any) running on a given vnc display
    def stop_command(display_index):
        if pool[display_index]["running_process"]:
            pool[display_index]["running_process"].terminate()
            print("Stopped command running on server pair at index %d" % display_index)
        pool[display_index]["running_process"] = None

    # increases the class-level variable job_id by 1 and returns it
    @staticmethod
    def get_job_id():
        Server.job_id += 1
        return str(Server.job_id)
