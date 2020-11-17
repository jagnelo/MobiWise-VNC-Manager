import os

from dotenv import load_dotenv, find_dotenv
from flask import Flask, request
from flask_cors import CORS

from src import utils
from src.globals import Globals
from src.manager import Manager

load_dotenv(find_dotenv())

app = Flask(__name__)

CORS(app, resources={r"/api/*": {"origins": "*"}})

manager = Manager()


# setup
def init():
    utils.clear_and_remove_dir(Globals.VNC_FILES_DIR)
    utils.ensure_dir_exists(Globals.VNC_FILES_DIR)
    Globals.scheduler.start()
    manager.start()


# teardown
def terminate():
    manager.stop()
    Globals.scheduler.shutdown()
    utils.clear_and_remove_dir(Globals.VNC_FILES_DIR)


@app.route("/api/vnc/request", methods=["POST"])
def vnc_request():
    url = manager.request_server_pair(request.files)

    return {
               "success": True,
               "data":
                   {
                       "vnc_url": url,
                       "vnc_resolution": Globals.vnc_resolution
                   }
           }, 200


if __name__ == '__main__':
    try:
        init()
        app.run(port=8002)
        terminate()
    except BaseException as e:
        print("Error: ", e)
        print("Killing any still-running VNC servers...")
        os.system("vncserver -kill :*")
        print("All VNC servers have been terminated")
