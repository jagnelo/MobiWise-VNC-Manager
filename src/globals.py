import os

from apscheduler.schedulers.background import BackgroundScheduler


class Globals:
    VNC_FILES_DIR = os.path.join("..", "files")
    scheduler = BackgroundScheduler()
    NA = -1
    job_id = NA
    vnc_resolution = {
        "width": 800,
        "height": 600
    }
    vnc_sumo_files = ["gui-settings", "additional-files", "net-file", "route-files", "basecars-emission-by-edges-out",
                      "edge-data-out"]
    vnc_sumo_cmd = "sumo-gui --gui-settings-file gui-settings.xml " \
                   "--additional-files additional-files.xml " \
                   "--net-file net-file.xml " \
                   "--route-files route-files.xml " \
                   "--device.emissions.probability 1.0 " \
                   "--emission-output.precision 6 " \
                   "--collision.action warn " \
                   "--time-to-teleport -1 " + \
                   "--window-size %d,%d " % (vnc_resolution["width"], vnc_resolution["height"]) + \
                   "--window-pos 0,0"
    base_websockify_port = 6080
    base_display_index = 1
    pool_base_size = 10
    pool_expand_size = pool_base_size // 2
    request_timeout_secs = 20
