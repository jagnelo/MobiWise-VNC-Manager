import os
import random
import shutil
import socket


# returns True if a given local port is available, False otherwise
def is_port_available(port):
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    available = sock.connect_ex(("localhost", port)) == 0
    sock.close()
    return available


# if the given port is not available, exhaustively tries different port numbers until one is available
def get_available_port(base_port):
    port = base_port - 1
    available = False
    while not available:
        port += 1
        available = is_port_available(port)
    return port


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

