import os

from dotenv import load_dotenv, find_dotenv
from flask import Flask, request
from flask_cors import CORS

load_dotenv(find_dotenv())

app = Flask(__name__)

CORS(app, resources={r"/api/*": {"origins": "*"}})


@app.route("/api/vnc/request", methods=["POST"])
def vnc_request():
    display_index = request_server_pair()
    server_pair = pool[display_index]
    url = "ws://localhost:%d/websockify" % server_pair["websockify_port"]
    for key in ["gui-settings", "additional-files", "net-file", "route-files", "basecars-emission-by-edges-out",
                "edge-data-out"]:
        file = request.files[key]
        file.save(os.path.join(get_files_dir(display_index), "%s.xml" % key))

    cmd = "sumo-gui"
    args = "--gui-settings-file gui-settings.xml " \
           "--additional-files additional-files.xml " \
           "--net-file net-file.xml " \
           "--route-files route-files.xml " \
           "--device.emissions.probability 1.0 " \
           "--emission-output.precision 6 " \
           "--collision.action warn " \
           "--time-to-teleport -1 " + \
           "--window-size %d,%d " % (vnc_resolution["width"], vnc_resolution["height"]) + \
           "--window-pos 0,0"

    run_command(display_index, "%s %s" % (cmd, args))

    return {
               "success": True,
               "data":
                   {
                       "id": server_pair["id"],
                       "vnc_url": url,
                       "vnc_resolution": vnc_resolution
                   }
           }, 200


@app.route("/api/vnc/discard/<id>", methods=["GET"])
def vnc_discard(id):
    discard_server_pair(get_display_index_by_id(id))
    return {"success": True}, 200


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
