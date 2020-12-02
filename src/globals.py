import os

from apscheduler.schedulers.background import BackgroundScheduler


class Globals:
    VNC_FILES_DIR = os.path.join("..", "files")
    SCHEDULER = BackgroundScheduler()
    NA = -1
    JOB_ID = NA
    VNC_RESOLUTION = {
        "width": 800,
        "height": 600
    }
    VNC_SUMO_FILES = ["gui-settings", "net-file", "route-files"]
    VNC_SUMO_CMD = "sumo-gui --gui-settings-file gui-settings.xml " \
                   "--net-file net-file.xml " \
                   "--route-files route-files.xml " \
                   "--device.emissions.probability 1.0 " \
                   "--collision.action warn " \
                   "--time-to-teleport -1 " \
                   "--window-size $(xdpyinfo | awk '/dimensions/{print $2}' | awk '{gsub(\"x\", \",\")} {print}') " \
                   "--window-pos 0,0"
    BASE_WEBSOCKIFY_PORT = 6080
    BASE_DISPLAY_INDEX = 1
    POOL_BASE_SIZE = 10
    POOL_EXPAND_SIZE = POOL_BASE_SIZE // 2
    REQUEST_TIMEOUT_SECS = 20
