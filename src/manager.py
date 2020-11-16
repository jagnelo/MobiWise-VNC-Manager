import os


class Manager:
    pool_base_size = 10
    pool_expand_size = pool_base_size // 2
    FILES_DIR = os.path.join("..", "files")

    def __init__(self):
        self.pool = []

    # initialize a pool of server pairs
    def init(self):
        print("Starting server...")
        for i in range(pool_base_size):
            create_server_pair(create_unique_display_index())
            for server in get_vnc_server_list_from_shell():
                print(server)
        scheduler.add_job(check_pool_state, 'interval', seconds=10)
        scheduler.start()
        clear_and_remove_dir(FILES_DIR)
        ensure_dir_exists(FILES_DIR)
        print("Server started")

    # terminate the pool server pairs
    def terminate(self):
        print("Stopping server...")
        scheduler.shutdown()
        for display_index in list(pool):
            discard_server_pair(display_index)
            destroy_server_pair(display_index)
        clear_and_remove_dir(FILES_DIR)
        print("Server stopped")

    # returns the display_index of an available vnc+websockify server pair and changes its serving state
    def request_server_pair():
        for display_index in pool:
            if not pool[display_index]["serving"]:
                pool[display_index]["serving"] = True
                pool[display_index]["last_heartbeat"] = datetime.now()
                unique_id = create_unique_id()
                pool[display_index]["id"] = unique_id
                path = get_files_dir(display_index)
                clear_and_remove_dir(path)
                ensure_dir_exists(path)
                pool[display_index]["files_path"] = path
                print("Server pair at index %d was requested (ID = %s)" % (display_index, unique_id))
                return display_index

    # resets the serving state of a given vnc+websockify server pair and makes it available for use again
    def discard_server_pair(display_index):
        if pool[display_index]["serving"]:
            pool[display_index]["serving"] = False
            pool[display_index]["last_heartbeat"] = datetime.now()
            unique_id = pool[display_index]["id"]
            pool[display_index]["id"] = None
            stop_command(display_index)
            clear_and_remove_dir(pool[display_index]["files_path"])
            pool[display_index]["files_path"] = None
            print("Server pair at index %d was discarded (ID = %s)" % (display_index, unique_id))

    # expand the size of the pool by pool_expand_size
    def expand_pool_size():
        old_size = len(pool)
        for i in range(pool_expand_size):
            create_server_pair(create_unique_display_index())
        new_size = len(pool)
        print("Pool was expanded by %d instances, from %d to %d" % (pool_expand_size, old_size, new_size))

    # reduce the size of the pool by pool_expand_size
    def reduce_pool_size():
        non_serving = []
        for display_index in pool:
            server_pair = pool[display_index]
            if not server_pair["serving"]:
                non_serving.append((display_index, (datetime.now() - server_pair["last_heartbeat"]).total_seconds()))
        non_serving.sort(key=itemgetter(1), reverse=True)
        old_size = len(pool)
        for i in range(pool_expand_size):
            destroy_server_pair(non_serving[i][0])
        new_size = len(pool)
        print("Pool was reduced by %d instances, from %d to %d" % (pool_expand_size, old_size, new_size))

    # used to periodically check the state of the pool and its instances and make the necessary adjustments
    def check_pool_state():
        acceptable_heartbeat_delta = timedelta(seconds=heartbeat_secs * 2)
        acceptable_heartbeat_delta_secs = acceptable_heartbeat_delta.total_seconds()
        for display_index in pool:
            server_pair = pool[display_index]
            last_heartbeat_delta = (datetime.now() - server_pair["last_heartbeat"])
            last_heartbeat_delta_secs = last_heartbeat_delta.total_seconds()
            if server_pair["serving"] and last_heartbeat_delta >= acceptable_heartbeat_delta:
                print("Server pair at index %d had last heartbeat %d seconds ago (out of a %d seconds window) "
                      "and must be discarded" % (
                      display_index, last_heartbeat_delta_secs, acceptable_heartbeat_delta_secs))
                discard_server_pair(display_index)
        count_serving = sum([pool[display_index]["serving"] for display_index in pool])
        print("Pool holds %d instances which are serving users out of a total of %d" % (count_serving, len(pool)))
        size_changed = False
        if count_serving >= get_expansion_threshold():
            expand_pool_size()
            size_changed = True
        elif count_serving < get_reduction_threshold() and len(pool) > pool_base_size:
            reduce_pool_size()
            size_changed = True
        if size_changed:
            if len(pool) > pool_base_size:
                print("Next reduction at %d serving instances" % get_reduction_threshold())
            print("Next expansion at %d serving instances" % get_expansion_threshold())

    # calculates the amount of serving instances above/at which to expand the pool size by pool_expand_size
    def get_expansion_threshold():
        return len(pool) - (pool_expand_size // 2)

    # calculates the amount of serving instances below which to reduce the pool size by pool_expand_size
    def get_reduction_threshold():
        return get_expansion_threshold() - pool_expand_size

    # returns the path to the folder containing files used by a given vnc instance
    def get_files_dir(display_index):
        return os.path.join(Manager.FILES_DIR, "%d" % display_index)

    # creates a random, but unique, id for a given pool instance which is now serving
    def create_unique_id():
        hash = None
        unique = False
        while not unique:
            hash = "%x" % random.getrandbits(64)
            unique = True
            for display_index in pool:
                if pool[display_index]["id"] == hash:
                    unique = False
                    break
        return hash
