import os
import shutil

from src.globals import Globals


# creates a given directory if it does not exist
def ensure_dir_exists(path):
    if not os.path.exists(path):
        os.makedirs(path)
        print("Created directory %s" % path)


# empties the contents (if any) and removes a given directory
def clear_and_remove_dir(path):
    if os.path.exists(path) and os.path.isdir(path):
        shutil.rmtree(path, ignore_errors=True)
        print("Emptied and removed directory %s" % path)


# gets the current environment, adds new key-value pairs to it, and returns it
def modify_environment(changes: dict):
    env = os.environ.copy()
    for key in changes:
        env[key] = changes[key]
    return env


def get_new_job_id():
    Globals.job_id += 1
    return str(Globals.job_id)


