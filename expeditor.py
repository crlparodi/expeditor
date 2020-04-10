#!/usr/bin/env python3

from os import listdir, scandir, path, stat, mkdir, remove
from threading import Event
from enum import Enum
import subprocess
import json
import getpass
import datetime
import shutil
import filecmp
import requests
import time

# OS constants
USERNAME = getpass.getuser()

# Main Directories
DIRECTORY = path.dirname("/home/" + USERNAME + "/Documents/")
BACKUP_DIRECTORY = path.dirname(DIRECTORY + "/ToDosBak/")
CACHE_DIRECTORY = path.dirname(BACKUP_DIRECTORY + "/.cache/")
LOCAL_CACHE = path.dirname(CACHE_DIRECTORY + "/local/")
DROPBOX_CACHE = path.dirname(CACHE_DIRECTORY + "/dropbox/")

# URL constants
UPLOAD_URL = "https://content.dropboxapi.com/2/files/upload"
DOWNLOAD_URL = "https://content.dropboxapi.com/2/files/download"
LIST_FOLDER_URL = "https://api.dropboxapi.com/2/files/list_folder"

# Access Token
ACCESS_TOKEN = open(
    path.join(DIRECTORY, "DropboxAPI/token.txt")).read()

# List of current files
FILENAMES = []


class HTTPRequest(Enum):
    STATUS_SUCCESS = 0
    STATUS_FAILURE = 1


def notify_launch(char_sequence):
    subprocess.Popen(['notify-send', "expeditor:" + " " + char_sequence])


def init_local_directories():
    all_exists = True

    if not path.exists(DIRECTORY):
        mkdir(DIRECTORY)
        all_exists = False
    elif not path.exists(BACKUP_DIRECTORY):
        mkdir(BACKUP_DIRECTORY)
        all_exists = False
    elif not path.exists(CACHE_DIRECTORY):
        mkdir(CACHE_DIRECTORY)
        all_exists = False
    elif not path.exists(LOCAL_CACHE):
        mkdir(LOCAL_CACHE)
        all_exists = False
    elif not path.exists(DROPBOX_CACHE):
        mkdir(DROPBOX_CACHE)
        all_exists = False

    return all_exists


def repo_files():
    FILENAMES.clear()
    for filename in listdir(DIRECTORY):
        if filename.endswith(".todo"):
            if filename not in FILENAMES:
                FILENAMES.append(filename)


def cache_files():
    for filename in FILENAMES:
        download_todo(filename, DROPBOX_CACHE)
        shutil.copyfile(DIRECTORY + "/" + filename,
                        LOCAL_CACHE + "/" + filename)


def dir_compare():
    for filename in FILENAMES:
        try:
            local_file = LOCAL_CACHE + "/" + filename
            dropbox_file = DROPBOX_CACHE + "/" + filename

            if path.exists(local_file) and path.exists(dropbox_file):
                if not file_compare(dropbox_file, local_file):
                    notify_launch("Update" + " " + filename +
                                  " " + "to Dropbox")
                    upload_todo(filename)
            elif path.exists(local_file) and not path.exists(dropbox_file):
                notify_launch("Create" + " " + filename + " " + "on Dropbox")
                upload_todo(filename)
        except FileNotFoundError:
            notify_launch("Create" + " " + filename + " " + "on Dropbox")
            upload_todo(filename)


def file_compare(dropbox_file, local_file):
    return filecmp.cmp(dropbox_file, local_file, False)


def clear_cache():
    for filename in listdir(LOCAL_CACHE):
        remove(LOCAL_CACHE + "/" + filename)

    for filename in listdir(DROPBOX_CACHE):
        remove(DROPBOX_CACHE + "/" + filename)


def download_todo(filename, path):
    headers = {
        "Authorization": "Bearer " + ACCESS_TOKEN,
        "Dropbox-API-Arg": "{\"path\":\"/todos/" + filename + "\"}"
    }

    response = requests.post(DOWNLOAD_URL, headers=headers)

    if response.status_code != 200:
        return HTTPRequest.STATUS_FAILURE

    file = open(path + "/" + filename, "w+")
    file.write(response.text)
    file.close()

    return HTTPRequest.STATUS_SUCCESS


def upload_todo(filename):
    headers = {
        "Authorization": "Bearer " + ACCESS_TOKEN,
        "Content-Type": "application/octet-stream",
        "Dropbox-API-Arg": "{\"path\":\"/todos/" + filename + "\",\"mode\":{\".tag\":\"overwrite\"}}"
    }

    with open(DIRECTORY + "/" + filename, "rb") as data:
        response = requests.post(UPLOAD_URL, headers=headers, data=data.read())

    if response.status_code != 200:
        return HTTPRequest.STATUS_FAILURE

    return HTTPRequest.STATUS_SUCCESS


if __name__ == "__main__":
    notify_launch("Init all directories")
    if init_local_directories():
        clear_cache()

    stopped = Event()

    try:
        notify_launch("I'm ready to watch .todo files")
        while not stopped.wait(3):
            repo_files()
            cache_files()
            dir_compare()
            clear_cache()
    except KeyboardInterrupt:
        notify_launch("Process aborted")
        clear_cache()
