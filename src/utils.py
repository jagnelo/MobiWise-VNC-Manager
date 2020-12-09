import os
import shutil


# creates a given directory if it does not exist
def ensure_dir_exists(path):
    if not os.path.exists(path):
        os.makedirs(path)
        print("Created directory %s" % path)


# empties the content (if any) of a given directory
def clear_dir(path):
    if os.path.exists(path) and os.path.isdir(path):
        for name in os.listdir(path):
            child_path = os.path.join(path, name)
            if os.path.isdir(os.path.join(path, name)):
                shutil.rmtree(child_path, ignore_errors=True)
            if os.path.isfile(os.path.join(path, name)):
                os.remove(child_path)
    print("Emptied directory %s" % path)


# empties the contents (if any) and removes a given directory
def clear_and_remove_dir(path):
    if os.path.exists(path) and os.path.isdir(path):
        shutil.rmtree(path, ignore_errors=True)
        print("Emptied and removed directory %s" % path)


# checks if a given directory is empty
def is_dir_empty(path):
    if os.path.exists(path) and os.path.isdir(path):
        return not os.listdir(path)
    return True


# gets the current environment, adds new key-value pairs to it, and returns it
def modify_environment(changes: dict):
    env = os.environ.copy()
    for key in changes:
        env[key] = changes[key]
    return env


