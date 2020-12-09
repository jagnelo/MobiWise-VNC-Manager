from dotenv import load_dotenv, find_dotenv
from flask import Flask, request
from flask_cors import CORS

import utils
from globals import Globals
from manager import Manager

load_dotenv(find_dotenv())

app = Flask(__name__)

CORS(app, resources={r"/api/*": {"origins": "*"}})

manager = Manager()


# setup
def init():
    utils.clear_dir(Globals.VNC_FILES_DIR)
    utils.ensure_dir_exists(Globals.VNC_FILES_DIR)
    manager.start()


# teardown
def terminate():
    manager.stop()
    utils.clear_and_remove_dir(Globals.VNC_FILES_DIR)


@app.route("/api/vnc/request", methods=["POST"])
def vnc_request():
    source_ip = request.environ['REMOTE_ADDR']
    source_port = request.environ['REMOTE_PORT']
    url = manager.request_vnc_instance(source_ip, source_port, request.files)

    return {
               "success": True,
               "data":
                   {
                       "vnc_url": url,
                       "vnc_resolution": Globals.VNC_RESOLUTION
                   }
           }, 200


if __name__ == '__main__':
    try:
        init()
        app.run(port=5001)
        terminate()
    except BaseException as e:
        print("Error: ", e)
        terminate()
