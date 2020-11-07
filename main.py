import os
import subprocess
from datetime import datetime
from enum import Enum

from dotenv import load_dotenv, find_dotenv
from flask import Flask
from flask_cors import CORS
from flask_sockets import Sockets
from gevent import pywsgi
from geventwebsocket.handler import WebSocketHandler

load_dotenv(find_dotenv())

app = Flask(__name__)
sockets = Sockets(app)

CORS(app, resources={r"/api/*": {"origins": "*"}})

base_pool_size = 4
pool = {}
base_vnc_port = 5900
base_websockify_port = 6080


class ServerType(Enum):
    PERSISTENT = 0
    TEMPORARY = 1


def get_vnc_port(display_index):
    global base_vnc_port
    return base_vnc_port + display_index


def get_websockify_port(display_index):
    global base_websockify_port
    return base_websockify_port + display_index


# start a vnc server
def start_vnc_server(display_index):
    vnc = subprocess.Popen(["vncserver", "-noxstartup", ":%d" % display_index])
    print("\tStarted VNC server at index %d" % display_index)
    return vnc


# stop a running vnc server
def stop_vnc_server(display_index):
    global pool
    if display_index in pool:
        vnc = pool[display_index]["vnc"]
        vnc.terminate()
        os.system("vncserver -kill :%d" % display_index)
        pool[display_index]["vnc"] = None
        print("\tStopped VNC server at index %d" % display_index)
        return


# start a websockify server
def start_websockify_server(display_index):
    vnc_port = get_vnc_port(display_index)
    websockify_port = get_websockify_port(display_index)
    websockify = subprocess.Popen(["websockify", "localhost:%d" % websockify_port, "localhost:%d" % vnc_port])
    print("\tStarted Websockify server at index %d" % display_index)
    return websockify


# stop a running websockify server
def stop_websockify_server(display_index):
    global pool
    if display_index in pool:
        websockify = pool[display_index]["websockify"]
        websockify.terminate()
        pool[display_index]["websockify"] = None
        print("\tStopped Websockify server at index %d" % display_index)
        return


# create and start a vnc+websockify server pair
def create_server_pair(display_index, server_type: ServerType):
    global pool
    print("Starting server pair at index %d" % display_index)
    vnc = start_vnc_server(display_index)
    websockify = start_websockify_server(display_index)
    pool[display_index] = {
        "vnc": vnc,
        "websockify": websockify,
        "type": server_type,
        "online": True,
        "serving": False,
        "created": datetime.now(),
        "last_use": None
    }


# stop and destroy a running vnc+websockify server pair
def destroy_server_pair(display_index):
    global pool
    print("Stopping server pair at index %d" % display_index)
    stop_vnc_server(display_index)
    stop_websockify_server(display_index)
    if display_index in pool:
        pool.pop(display_index)


# initialize a pool of vnc+websockify server pairs
def init():
    global base_pool_size, pool
    for i in range(base_pool_size):
        display_index = len(pool.keys()) + 1
        create_server_pair(display_index, ServerType.PERSISTENT)


# terminate the entire pool of running vnc+websockify server pairs
def terminate():
    global pool
    for display_index in list(pool):
        destroy_server_pair(display_index)


@app.route('/')
def hello():
    return 'Hello World!'


@sockets.route('/echo')
def echo_socket(ws):
    while not ws.closed:
        message = ws.receive()
        print(message)
        ws.send(message)


if __name__ == '__main__':
    init()
    # app.run(port=8002)
    try:
        server = pywsgi.WSGIServer(('', 8002), app, handler_class=WebSocketHandler)
        server.serve_forever()
    except BaseException as e:
        print("Error: ", e)
    terminate()
