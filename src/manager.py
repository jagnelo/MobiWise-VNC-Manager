import random
from datetime import datetime

from src import utils
from src.globals import Globals
from src.iserver import IServer, State
from src.server import Server


class Manager(IServer):
    def __init__(self):
        self.pool = {}
        self.requested = {}
        self.job_id = Globals.NA
        self.last_count_serving = Globals.NA

    # initialize a pool of server pairs
    def start(self):
        print("Starting instance manager...")
        for i in range(Globals.pool_base_size):
            self.create_server()
        self.job_id = utils.get_new_job_id()
        Globals.scheduler.add_job(self.check_state, 'interval', seconds=2, id=self.job_id)
        print("Instance manager started")

    # terminate the pool of server pairs
    def stop(self):
        print("Stopping instance manager...")
        Globals.scheduler.remove_job(self.job_id)
        for server_id in list(self.pool):
            self.destroy_server(server_id)
        print("Instance manager stopped")

    # adds and starts a new server pair to the pool
    def create_server(self):
        server = Server()
        server.start()
        self.pool[self.create_unique_id()] = server

    # stops and removes a server pair from the pool
    def destroy_server(self, server_id):
        self.pool.pop(server_id).stop()

    # used to periodically check the state of the pool and its instances and make the necessary adjustments
    def check_state(self):
        for server_id in self.pool:
            self.pool[server_id].check_state()
            if server_id in self.requested:
                delta_secs = (datetime.now() - self.requested[server_id]).total_seconds()
                if self.pool[server_id].state == State.Serving or delta_secs >= Globals.request_timeout_secs:
                    self.requested.pop(server_id)
        count_serving = sum([self.pool[server_id].state == State.Serving or server_id in self.requested for server_id in
                             self.pool])
        if self.last_count_serving != count_serving:
            self.last_count_serving = count_serving
            print_info = (count_serving, len(self.pool))
            print("Pool holds %d instances which are serving/have been requested by users out of a total of %d" % print_info)
        size_changed = False
        if count_serving >= self.get_expansion_threshold():
            self.expand_pool_size()
            size_changed = True
        elif count_serving < self.get_reduction_threshold() and len(self.pool) > Globals.pool_base_size:
            self.reduce_pool_size()
            size_changed = True
        if size_changed:
            if len(self.pool) > Globals.pool_base_size:
                print("Next reduction at %d serving instances" % self.get_reduction_threshold())
            print("Next expansion at %d serving instances" % self.get_expansion_threshold())

    # returns the url of an available vnc+websockify server pair
    def request_server_pair(self, files):
        for server_id in self.pool:
            if self.pool[server_id].state == State.Ready and server_id not in self.requested:
                print("Server pair ID = %s was requested" % server_id)
                self.requested[server_id] = datetime.now()
                self.pool[server_id].run_command(Globals.vnc_sumo_cmd, files)
                return self.pool[server_id].get_url()
        return None

    # calculates the amount of serving instances above/at which to expand the pool size by pool_expand_size
    def get_expansion_threshold(self):
        return len(self.pool) - (Globals.pool_expand_size // 2)

    # calculates the amount of serving instances below which to reduce the pool size by pool_expand_size
    def get_reduction_threshold(self):
        return self.get_expansion_threshold() - Globals.pool_expand_size

    # expand the size of the pool by pool_expand_size
    def expand_pool_size(self):
        old_size = len(self.pool)
        for i in range(Globals.pool_expand_size):
            self.create_server()
        new_size = len(self.pool)
        print("Pool was expanded by %d instances, from %d to %d" % (Globals.pool_expand_size, old_size, new_size))

    # reduce the size of the pool by pool_expand_size
    def reduce_pool_size(self):
        non_serving = [server_id for server_id in self.pool if self.pool[server_id].state != State.Serving and
                       server_id not in self.requested]
        if len(non_serving) >= Globals.pool_expand_size:
            old_size = len(self.pool)
            for i in range(Globals.pool_expand_size):
                self.destroy_server(non_serving[i])
            new_size = len(self.pool)
            print("Pool was reduced by %d instances, from %d to %d" % (Globals.pool_expand_size, old_size, new_size))
        else:
            print_info = (Globals.pool_expand_size, len(non_serving))
            print("Pool could not be reduced by %d instances as there are only %d non-serving instances" % print_info)

    # creates a random, but unique, id for a given pool instance which is now serving
    def create_unique_id(self):
        hash = None
        unique = False
        while not unique:
            hash = "%x" % random.getrandbits(64)
            unique = True
            for server_id in self.pool:
                if server_id == hash:
                    unique = False
                    break
        return hash
