import os


class Globals:
    VNC_FILES_DIR = os.path.join("..", "files")
    NA = -1
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
                   "--window-size 800,600 " \
                   "--window-pos 0,0"
    WEBSOCKIFY_PORT = 6080
    TOKENS_FILE_DIR = os.path.join("..", "vnc_tokens")
    BASE_DISPLAY_INDEX = 21     # 1
    POOL_BASE_SIZE = 10
    POOL_EXPAND_SIZE = POOL_BASE_SIZE // 2
    REQUEST_TIMEOUT_SECS = 20

    LOGS_OLD_NAME = "old logs"
    LOGS_DIR = os.path.join("..", "logs")
    LOGS_LEVEL_INFO = "INFO"
    LOGS_LEVEL_DEBUG = "DEBUG"
    LOGS_LEVEL_WARN = "WARN"
    LOGS_LEVEL_ERROR = "ERROR"
    LOGS_FILE_TYPE = "log"

