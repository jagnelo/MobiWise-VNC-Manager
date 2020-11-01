import argparse
import os
import numpy as np


from flask import Flask, send_file
from flask_cors import CORS
from dotenv import load_dotenv, find_dotenv


load_dotenv(find_dotenv())

app = Flask(__name__)

CORS(app, resources={r"/api/*": {"origins": "*"}})


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


def init():
    # start a pool of VNC + websockify server pairs (e.g., 20, 30, must be an even value)
    pass


def destroy():
    # destroy all running VNC (vncserver -kill :*) and websockify (terminate handles to each server) servers
    pass


if __name__ == '__main__':
    init()
    app.run(port=8002)
    destroy()
