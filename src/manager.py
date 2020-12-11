import os
import random
from datetime import datetime

from apscheduler.schedulers.background import BackgroundScheduler

import websockify

from globals import Globals
from iserver import IServer, State
import vnc


class Manager(IServer):
    def __init__(self):
        self.websockify = websockify.Websockify()
        self.pool = {}
        self.requested = {}
        self.scheduler = BackgroundScheduler()
        self.last_count = Globals.NA
        self.is_shutting_down = False

    # initialize a pool of VNC instances
    def start(self):
        print("Starting VNC instance manager...")
        self.websockify.start()
        for i in range(Globals.POOL_BASE_SIZE):
            self.create_vnc_instance()
        self.scheduler.add_job(self.check_state, 'interval', seconds=2)
        self.scheduler.start()
        print("VNC instance manager started")

    # terminate the pool of VNC instances
    def stop(self):
        print("Stopping VNC instance manager...")
        self.is_shutting_down = True
        self.scheduler.shutdown()
        os.remove(Globals.TOKENS_FILE_DIR)
        self.websockify.stop()
        for vnc_id in list(self.pool):
            self.destroy_vnc_instance(vnc_id)
        print("VNC instance manager stopped")

    # starts a new VNC instance and adds it to the pool
    def create_vnc_instance(self):
        vnc_instance = vnc.VNC()
        vnc_instance.start()
        vnc_id = self.create_unique_id()
        self.pool[vnc_id] = vnc_instance
        return vnc_id

    # stops an existing VNC instance and removes it from the pool
    def destroy_vnc_instance(self, vnc_id):
        if vnc_id in self.requested:
            self.requested.pop(vnc_id)
        self.pool.pop(vnc_id).stop()

    def replace_vnc_instance(self, vnc_id):
        if not self.is_shutting_down:
            self.destroy_vnc_instance(vnc_id)
            new_vnc_id = self.create_vnc_instance()
            print("VNC ID = %s has been replaced by VNC ID = %s" % (vnc_id, new_vnc_id))

    # used to periodically check the state of the pool and its instances and make the necessary adjustments
    def check_state(self):
        if self.is_shutting_down:
            return
        count_serving = 0
        count_requested = 0
        count_ready = 0
        count_unavailable = 0
        dead_instances = []
        changes = [self.websockify.check_state()]
        for vnc_id in self.pool:
            changes.append(self.pool[vnc_id].check_state())
            if vnc_id in self.requested:
                delta_secs = self.requested[vnc_id].seconds_elapsed()
                if self.pool[vnc_id].state == State.Serving:
                    self.requested.pop(vnc_id)
                    self.pool[vnc_id].run_command(Globals.VNC_SUMO_CMD)
                    print_info = (vnc_id, self.pool[vnc_id].state)
                    print("Removed VNC ID = %s from the requested list as its state is now %s" % print_info)
                if self.pool[vnc_id].state in [State.Unavailable, State.Dead]:
                    self.requested.pop(vnc_id)
                    print_info = (vnc_id, self.pool[vnc_id].state)
                    print("Removed VNC ID = %s from the requested list as its state changed to %s" % print_info)
                if delta_secs >= Globals.REQUEST_TIMEOUT_SECS:
                    self.requested.pop(vnc_id)
                    print_info = (vnc_id, self.pool[vnc_id].state, delta_secs)
                    print("Removed VNC ID = %s from the requested list as its state is still %s after %d seconds" % print_info)
            if vnc_id in self.requested:
                count_requested += 1
            if self.pool[vnc_id].state == State.Serving:
                count_serving += 1
            if self.pool[vnc_id].state == State.Ready:
                count_ready += 1
            if self.pool[vnc_id].state == State.Unavailable:
                count_unavailable += 1
            if self.pool[vnc_id].state == State.Dead:
                dead_instances.append(vnc_id)
            if not self.pool[vnc_id].state == State.Serving:
                self.pool[vnc_id].stop_command()
        count_total = count_serving + count_requested
        if self.last_count != count_total or any(changes):
            self.last_count = count_total
            print("Websockify status \t->\t %s" % (self.websockify.describe_state()))
            print("Pool status:")
            for vnc_id in self.pool:
                print("\tVNC ID = %s \t->\t %s" % (vnc_id, self.pool[vnc_id].describe_state()))
            print_info = (len(self.pool), count_serving, State.Serving, count_ready, State.Ready, count_requested,
                          count_unavailable, State.Unavailable, len(dead_instances), State.Dead)
            print("Pool holds %d instances: %d in %s | %d in %s [%d requested] | %d in %s | %d in %s" % print_info)
            self.update_vnc_ids()
        for vnc_id in dead_instances:
            print("VNC ID = %s has state %s and will be replaced" % (vnc_id, self.pool[vnc_id].state))
            self.replace_vnc_instance(vnc_id)
        size_changed = False
        if count_total >= self.get_expansion_threshold():
            self.expand_pool_size()
            size_changed = True
        elif count_total < self.get_reduction_threshold() and len(self.pool) > Globals.POOL_BASE_SIZE:
            self.reduce_pool_size()
            size_changed = True
        if size_changed:
            if len(self.pool) > Globals.POOL_BASE_SIZE:
                print("Next reduction at %d serving instances" % self.get_reduction_threshold())
            print("Next expansion at %d serving instances" % self.get_expansion_threshold())

    # returns the url of an available vnc instance
    def request_vnc_instance(self, source_ip, source_port, files):
        if self.is_shutting_down:
            return None
        for vnc_id in self.pool:
            if self.pool[vnc_id].state == State.Ready and vnc_id not in self.requested:
                self.requested[vnc_id] = Request(vnc_id, source_ip, source_port)
                print_info = (vnc_id, source_ip, source_port, Globals.REQUEST_TIMEOUT_SECS, State.Serving)
                print("VNC ID = %s was requested by %s:%s and will be made available again after %d seconds if its"
                      " state does not change to %s" % print_info)
                self.pool[vnc_id].store_files_to_dir(files)
                return "ws://193.137.203.16:80/vnc?token=%s" % vnc_id
        return None

    # calculates the amount of serving instances above/at which to expand the pool size by pool_expand_size
    def get_expansion_threshold(self):
        return len(self.pool) - (Globals.POOL_EXPAND_SIZE // 2)

    # calculates the amount of serving instances below which to reduce the pool size by pool_expand_size
    def get_reduction_threshold(self):
        return self.get_expansion_threshold() - Globals.POOL_EXPAND_SIZE

    # expand the size of the pool by pool_expand_size
    def expand_pool_size(self):
        if self.is_shutting_down:
            return
        old_size = len(self.pool)
        for i in range(Globals.POOL_EXPAND_SIZE):
            self.create_vnc_instance()
        new_size = len(self.pool)
        print("Pool was expanded by %d instances, from %d to %d" % (Globals.POOL_EXPAND_SIZE, old_size, new_size))

    # reduce the size of the pool by pool_expand_size
    def reduce_pool_size(self):
        if self.is_shutting_down:
            return
        non_serving = [vnc_id for vnc_id in self.pool if self.pool[vnc_id].state != State.Serving and
                       vnc_id not in self.requested]
        if len(non_serving) >= Globals.POOL_EXPAND_SIZE:
            old_size = len(self.pool)
            for i in range(Globals.POOL_EXPAND_SIZE):
                self.destroy_vnc_instance(non_serving[i])
            new_size = len(self.pool)
            print("Pool was reduced by %d instances, from %d to %d" % (Globals.POOL_EXPAND_SIZE, old_size, new_size))
        else:
            print_info = (Globals.POOL_EXPAND_SIZE, len(non_serving))
            print("Pool could not be reduced by %d instances as there are only %d non-serving instances" % print_info)

    # creates a random, but unique, id for a given pool instance which is now serving
    def create_unique_id(self):
        hash = None
        unique = False
        while not unique:
            hash = "%x" % random.getrandbits(64)
            unique = True
            for vnc_id in self.pool:
                if vnc_id == hash:
                    unique = False
                    break
        return hash

    def update_vnc_ids(self):
        if self.is_shutting_down:
            return
        path = Globals.TOKENS_FILE_DIR
        print("Updating VNC tokens file %s" % path)
        with open(path, "w") as f:
            for vnc_id in self.pool:
                if self.pool[vnc_id].state == State.Ready:
                    f.write("%s: localhost:%d\n" % (vnc_id, self.pool[vnc_id].port))


class Request:
    def __init__(self, vnc_id, source_ip, source_port):
        self.vnc_id = vnc_id
        self.timestamp = datetime.now()
        self.source_ip = source_ip
        self.source_port = source_port

    def seconds_elapsed(self):
        return (datetime.now() - self.timestamp).total_seconds()
