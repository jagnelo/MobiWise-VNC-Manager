import os
import subprocess
import random
from datetime import datetime, timedelta
from operator import itemgetter

from dotenv import load_dotenv, find_dotenv
from flask import Flask
from flask_cors import CORS
from flask_sockets import Sockets
from apscheduler.schedulers.background import BackgroundScheduler

load_dotenv(find_dotenv())

app = Flask(__name__)
sockets = Sockets(app)

CORS(app, resources={r"/api/*": {"origins": "*"}})

pool_base_size = 10
pool_expand_size = pool_base_size // 2
pool = {}

base_display_index = 1

base_vnc_port = 5900
base_websockify_port = 6080

heartbeat_secs = 30

scheduler = BackgroundScheduler()


# calculates the amount of serving instances above/at which to expand the pool size by pool_expand_size
def get_expansion_threshold():
    global pool, pool_expand_size
    return len(pool) - (pool_expand_size // 2)


# calculates the amount of serving instances below which to reduce the pool size by pool_expand_size
def get_reduction_threshold():
    global pool_expand_size
    return get_expansion_threshold() - pool_expand_size


# calculates the vnc port based on a given display index
def get_vnc_port(display_index):
    global base_vnc_port
    return base_vnc_port + display_index


# calculates the websockify port based on a given display index
def get_websockify_port(display_index):
    global base_websockify_port
    return base_websockify_port + display_index


# finds a ninstance in the pool by its unique id, if one has been given
def get_display_index_from_id(id):
    global pool
    for display_index in pool:
        if pool[display_index]["id"] == id:
            return display_index
    return None


# creates a random, but unique, id for a given pool instance which is now serving
def create_unique_id():
    global pool
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


# creates a unique display index for a new pool instance based on the next available index in ascending order
def create_unique_display_index():
    global pool, base_display_index
    display_index = base_display_index
    while display_index in pool:
        display_index += 1
    return display_index


# start a vnc server
def start_vnc_server(display_index):
    vnc = subprocess.Popen(["vncserver", ":%d" % display_index, "-noxstartup", "-geometry", "800x600"])
    print("Started VNC server at index %d" % display_index)
    return vnc


# stop a running vnc server
def stop_vnc_server(display_index):
    global pool
    if display_index in pool:
        vnc = pool[display_index]["vnc"]
        vnc.terminate()
        os.system("vncserver -kill :%d" % display_index)
        pool[display_index]["vnc"] = None
        print("Stopped VNC server at index %d" % display_index)
        return


# start a websockify server
def start_websockify_server(display_index):
    vnc_port = get_vnc_port(display_index)
    websockify_port = get_websockify_port(display_index)
    websockify = subprocess.Popen(["websockify", "localhost:%d" % websockify_port, "localhost:%d" % vnc_port])
    print("Started Websockify server at index %d" % display_index)
    return websockify


# stop a running websockify server
def stop_websockify_server(display_index):
    global pool
    if display_index in pool:
        websockify = pool[display_index]["websockify"]
        websockify.terminate()
        pool[display_index]["websockify"] = None
        print("Stopped Websockify server at index %d" % display_index)
        return


# create and start a vnc+websockify server pair
def create_server_pair(display_index):
    global pool
    print("Starting server pair at index %d" % display_index)
    vnc = start_vnc_server(display_index)
    websockify = start_websockify_server(display_index)
    pool[display_index] = {
        "id": None,
        "vnc": vnc,
        "vnc_port": get_vnc_port(display_index),
        "websockify": websockify,
        "websockify_port": get_websockify_port(display_index),
        "online": True,
        "serving": False,
        "created": datetime.now(),
        "last_heartbeat": datetime.now()
    }


# returns the display_index of an available vnc+websockify server pair and changes its serving state
def request_server_pair():
    global pool
    for display_index in pool:
        if not pool[display_index]["serving"]:
            pool[display_index]["serving"] = True
            pool[display_index]["last_heartbeat"] = datetime.now()
            unique_id = create_unique_id()
            pool[display_index]["id"] = unique_id
            print("Server pair at index %d was requested (ID = %s)" % (display_index, unique_id))
            return display_index


# resets the serving state of a given vnc+websockify server pair and makes it available for use again
def discard_server_pair(display_index):
    global pool
    if pool[display_index]["serving"]:
        pool[display_index]["serving"] = False
        pool[display_index]["last_heartbeat"] = datetime.now()
        unique_id = pool[display_index]["id"]
        pool[display_index]["id"] = None
        print("Server pair at index %d was discarded (ID = %s)" % (display_index, unique_id))


# stop and destroy a running vnc+websockify server pair
def destroy_server_pair(display_index):
    global pool
    print("Stopping server pair at index %d" % display_index)
    stop_vnc_server(display_index)
    stop_websockify_server(display_index)
    if display_index in pool:
        pool.pop(display_index)


# expand the size of the pool by pool_expand_size
def expand_pool_size():
    global pool, pool_expand_size
    old_size = len(pool)
    for i in range(pool_expand_size):
        create_server_pair(create_unique_display_index())
    new_size = len(pool)
    print("Pool was expanded by %d instances, from %d to %d" % (pool_expand_size, old_size, new_size))


# reduce the size of the pool by pool_expand_size
def reduce_pool_size():
    global pool, pool_expand_size
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
    global pool, pool_base_size, heartbeat_secs
    acceptable_heartbeat_delta = timedelta(seconds=heartbeat_secs*2)
    acceptable_heartbeat_delta_secs = acceptable_heartbeat_delta.total_seconds()
    for display_index in pool:
        server_pair = pool[display_index]
        last_heartbeat_delta = (datetime.now() - server_pair["last_heartbeat"])
        last_heartbeat_delta_secs = last_heartbeat_delta.total_seconds()
        if server_pair["serving"] and last_heartbeat_delta >= acceptable_heartbeat_delta:
            print("Server pair at index %d had last heartbeat %d seconds ago (out of a %d seconds window) "
                  "and must be discarded" % (display_index, last_heartbeat_delta_secs, acceptable_heartbeat_delta_secs))
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


# initialize a pool of vnc+websockify server pairs
def init():
    global pool_base_size, pool, scheduler
    print("Starting server...")
    for i in range(pool_base_size):
        create_server_pair(create_unique_display_index())
    scheduler.add_job(check_pool_state, 'interval', seconds=10)
    scheduler.start()
    print("Server started")


# terminate the entire pool of running vnc+websockify server pairs
def terminate():
    global pool, scheduler
    print("Stopping server...")
    scheduler.shutdown()
    for display_index in list(pool):
        destroy_server_pair(display_index)
    print("Server stopped")


@app.route("/api/vnc/request", methods=["GET"])
def vnc_request():
    global pool, heartbeat_secs
    display_index = request_server_pair()
    server_pair = pool[display_index]
    url = "ws://localhost:%d/websockify" % server_pair["websockify_port"]
    return {
               "success": True,
               "data":
                   {
                       "id": server_pair["id"],
                       "vnc_url": url,
                       "heartbeat_seconds": heartbeat_secs
                   }
           }, 200


@app.route("/api/vnc/heartbeat/<id>", methods=["GET"])
def vnc_heartbeat(id):
    global pool
    pool[get_display_index_from_id(id)]["last_heartbeat"] = datetime.now()
    return {"success": True}, 200


@app.route("/api/vnc/discard/<id>", methods=["GET"])
def vnc_discard(id):
    discard_server_pair(get_display_index_from_id(id))
    return {"success": True}, 200


if __name__ == '__main__':
    init()
    app.run(port=8002)
    terminate()
