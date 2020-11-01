import argparse
import os
import numpy as np
import subprocess


from flask import Flask, send_file
from flask_cors import CORS
from dotenv import load_dotenv, find_dotenv


load_dotenv(find_dotenv())

app = Flask(__name__)

CORS(app, resources={r"/api/*": {"origins": "*"}})


base_pool_size = 4
pool = []
base_vnc_port = 5900
base_websockify_port = 6080


# start a vnc server
def start_vnc_server(display_index):
    vnc = subprocess.Popen(["vncserver", "-noxstartup", ":%d" % display_index])
    print("\tStarted VNC server at index %d" % display_index)
    return vnc


# stop a running vnc server
def stop_vnc_server(display_index):
    global pool
    for i in range(len(pool)):
        if pool[i]["display_index"] == display_index:
            vnc = pool[i]["vnc"]
            vnc.terminate()
            os.system("vncserver -kill :%d" % display_index)
            pool[i]["vnc"] = None
            print("\tStopped VNC server at index %d" % display_index)
            return


# create and start a vnc+websockify server pair
def create_server_pair(display_index):
    global pool
    print("Starting server pair at index %d" % display_index)
    vnc = start_vnc_server(display_index)
    websockify = start_websockify_server(display_index)
    pool.append({
        "display_index": display_index,
        "vnc": vnc,
        "websockify": websockify,
        "running": False
    })


# start a websockify server
def start_websockify_server(display_index):
    global base_vnc_port, base_websockify_port
    vnc_port = base_vnc_port + display_index
    websockify_port = base_websockify_port + display_index
    websockify = subprocess.Popen(["websockify", "localhost:%d" % websockify_port, "localhost:%d" % vnc_port])
    print("\tStarted Websockify server at index %d" % display_index)
    return websockify


# stop a running websockify server
def stop_websockify_server(display_index):
    global pool
    for i in range(len(pool)):
        if pool[i]["display_index"] == display_index:
            websockify = pool[i]["websockify"]
            websockify.terminate()
            pool[i]["websockify"] = None
            print("\tStopped Websockify server at index %d" % display_index)
            return


# stop and destroy a running vnc+websockify server pair
def destroy_server_pair(display_index):
    global pool
    print("Stopping server pair at index %d" % display_index)
    stop_vnc_server(display_index)
    stop_websockify_server(display_index)
    for i in range(len(pool)):
        if pool[i]["display_index"] == display_index:
            pool.pop(i)
            return


# initialize a pool of vnc+websockify server pairs
def init():
    global base_pool_size, pool
    for i in range(base_pool_size):
        display_index = len(pool) + 1
        create_server_pair(display_index)


# terminate the entire pool of running vnc+websockify server pairs
def terminate():
    global pool
    for i in range(len(pool)):
        destroy_server_pair(i+1)


# @app.route('/api/<scenario>/<objective1>/<objective2>/view/<solution>', methods=['GET'])
# def simulation_view(scenario, objective1, objective2, solution):
#     data = read_pickle()
#     key = format_db_entry_key(scenario, objective1, objective2)
#     tc = data[key]["tc"]
#
#     ifolder = tc["ifolder"]  # input folder
#     ofolder = tc["ofolder"] + "/inputdata"  # output folder
#     netfile = ifolder + "/" + tc["netfile"]  # net file
#     roufile = ifolder + "/" + tc["roufile"]  # inital route file
#     obname = ofolder + "/" + tc["bname"]  # output base name
#
#     sumocmd = "sumo-gui --gui-settings-file gui-settings.xml"
#
#     cmd_base = "DISPLAY=:1 " + sumocmd + " --net-file " + netfile + " --route-files " + roufile +\
#                " --tripinfo-output " + obname + "-tripinfo --device.emissions.probability 1.0 " \
#                                                 "--emission-output.precision 6 " \
#                                                 "--additional-files moreOutputInfo.xml " \
#                                                 "--collision.action warn " \
#                                                 "--time-to-teleport -1 "    # \
#                                                 # "--quit-on-end " \
#                                                 # "-S " \
#                                                 # "-G"
#
#     fcostWeights = data[key]["fcostWeights"]
#     fcostLabels = data[key]["fcostLabels"]
#     commoninfo = data[key]["commoninfo"]
#     solsinfo = data[key]["solsinfo"]
#
#     (mwgraph, demand, sourcedest, sroutes, svehicles, dynamicTypes, outFolder, base_eval) = commoninfo
#     (sols, sim_eval, simevalsd, pred_eval, solsBName) = solsinfo
#
#     sol = int(solution)
#
#     flowc, flowd, ev, predev = sols[sol]
#     obname = solsBName[sol]
#
#     roufile = obname + ".rou.xml"
#     routes, vehicles = mwgraph.getFlowDescription(flowd, demand, sourcedest, mode=2)
#
#     comments = "objective functions: (" + ", ".join(
#         map(lambda a: (str(a[0]) + "*" + str(a[1])), zip(fcostWeights, fcostLabels))) + ")"
#     comments += "\n" + "\n".join(map(str, ev.items()))
#
#     SUMOinout.printSUMORoutes(routes, vehicles, roufile, sroutes=sroutes, svehicles=svehicles, comments=comments)
#
#     cmd_optimized = "DISPLAY=:2 " + sumocmd + " --net-file " + netfile + " --route-files " + roufile +\
#                     " --tripinfo-output " + obname + "-tripinfo --device.emissions.probability 1.0 " \
#                                                      "--emission-output.precision 6 " \
#                                                      "--additional-files moreOutputInfo.xml " \
#                                                      "--collision.action warn " \
#                                                      "--time-to-teleport -1 "   # \
#                                                      # "--quit-on-end " \
#                                                      # "-S " \
#                                                      # "-G"
#
#     os.system(cmd_base + " & " + cmd_optimized + " & wait")
#
#     return {"success": True}, 200


if __name__ == '__main__':
    init()
    app.run(port=8002)
    terminate()
