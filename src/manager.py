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
        self.scheduler_job_id = Globals.NA
        self.last_count = Globals.NA

    # initialize a pool of server pairs
    def start(self):
        print("Starting instance manager...")
        for i in range(Globals.pool_base_size):
            self.create_server()
        self.scheduler_job_id = utils.get_new_job_id()
        Globals.scheduler.add_job(self.check_state, 'interval', seconds=2, id=self.scheduler_job_id)
        print("Instance manager started")

    # terminate the pool of server pairs
    def stop(self):
        print("Stopping instance manager...")
        Globals.scheduler.remove_job(self.scheduler_job_id)
        for server_id in list(self.pool):
            self.destroy_server(server_id)
        print("Instance manager stopped")

    # adds and starts a new server pair to the pool
    def create_server(self):
        server = Server()
        server.start()
        server_id = self.create_unique_id()
        self.pool[server_id] = server
        return server_id

    # stops and removes a server pair from the pool
    def destroy_server(self, server_id):
        if server_id in self.requested:
            self.requested.pop(server_id)
        self.pool.pop(server_id).stop()

    # used to periodically check the state of the pool and its instances and make the necessary adjustments
    def check_state(self):
        count_serving = 0
        count_requested = 0
        count_ready = 0
        count_unavailable = 0
        dead_servers = []
        changes = []
        for server_id in self.pool:
            changes.append(self.pool[server_id].check_state())
            if server_id in self.requested:
                delta_secs = self.requested[server_id].seconds_elapsed()
                if self.pool[server_id].state == State.Serving:
                    self.requested.pop(server_id)
                    self.pool[server_id].run_command(Globals.vnc_sumo_cmd)
                    print_info = (server_id, self.pool[server_id].state)
                    print("Removed server ID = %s from the requested list as its state is now %s" % print_info)
                if self.pool[server_id].state in [State.Unavailable, State.Dead]:
                    self.pool[server_id].stop_command()
                    self.requested.pop(server_id)
                    print_info = (server_id, self.pool[server_id].state)
                    print("Removed server ID = %s from the requested list as its state changed to %s" % print_info)
                if delta_secs >= Globals.request_timeout_secs:
                    self.pool[server_id].stop_command()
                    self.requested.pop(server_id)
                    print_info = (server_id, self.pool[server_id].state, delta_secs)
                    print("Removed server ID = %s from the requested list as its state is still %s after %d seconds" % print_info)
            if server_id in self.requested:
                count_requested += 1
            if self.pool[server_id].state == State.Serving:
                count_serving += 1
            if self.pool[server_id].state == State.Ready:
                count_ready += 1
            if self.pool[server_id].state == State.Unavailable:
                count_unavailable += 1
            if self.pool[server_id].state == State.Dead:
                dead_servers.append(server_id)
        count_total = count_serving + count_requested
        if self.last_count != count_total or any(changes):
            self.last_count = count_total
            print("Pool status:")
            for server_id in self.pool:
                print("\tServer ID = %s \t->\t %s" % (server_id, self.pool[server_id].describe_state()))
            print_info = (len(self.pool), count_serving, State.Serving, count_ready, State.Ready, count_requested,
                          count_unavailable, State.Unavailable, len(dead_servers), State.Dead)
            print("Pool holds %d instances: %d in %s | %d in %s [%d requested] | %d in %s | %d in %s" % print_info)
        for server_id in dead_servers:
            print("Server ID = %s has state %s and will be replaced" % (server_id, self.pool[server_id].state))
            self.destroy_server(server_id)
            new_server_id = self.create_server()
            print("Server ID = %s has been replaced by Server ID = %s" % (server_id, new_server_id))
        size_changed = False
        if count_total >= self.get_expansion_threshold():
            self.expand_pool_size()
            size_changed = True
        elif count_total < self.get_reduction_threshold() and len(self.pool) > Globals.pool_base_size:
            self.reduce_pool_size()
            size_changed = True
        if size_changed:
            if len(self.pool) > Globals.pool_base_size:
                print("Next reduction at %d serving instances" % self.get_reduction_threshold())
            print("Next expansion at %d serving instances" % self.get_expansion_threshold())

    def describe_state(self) -> str:
        pass

    # returns the url of an available vnc+websockify server pair
    def request_server_pair(self, source_ip, source_port, files):
        for server_id in self.pool:
            if self.pool[server_id].state == State.Ready and server_id not in self.requested:
                self.requested[server_id] = Request(server_id, source_ip, source_port)
                print_info = (server_id, source_ip, source_port, Globals.request_timeout_secs, State.Serving)
                print("Server ID = %s was requested by %s:%s and will be made available again after %d seconds if its"
                      " state does not change to %s" % print_info)
                self.pool[server_id].store_files_to_dir(files)
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


class Request:
    def __init__(self, server_id, source_ip, source_port):
        self.server_id = server_id
        self.timestamp = datetime.now()
        self.source_ip = source_ip
        self.source_port = source_port

    def seconds_elapsed(self):
        return (datetime.now() - self.timestamp).total_seconds()
