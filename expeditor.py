#!/usr/bin/env python3

from os import listdir, scandir, path, stat, mkdir, remove
from threading import Event
from enum import Enum
import json
import getpass
import datetime
import shutil
import filecmp
import requests

# OS constants
USERNAME = getpass.getuser()
DIRECTORY = path.dirname("/home/" + USERNAME + "/Documents/")
BACKUP_DIRECTORY = path.dirname(DIRECTORY + "/ToDosBak/")

# URL constants
UPLOAD_URL = "https://content.dropboxapi.com/2/files/upload"
DOWNLOAD_URL = "https://content.dropboxapi.com/2/files/download"
LIST_FOLDER_URL = "https://api.dropboxapi.com/2/files/list_folder"

ACCESS_TOKEN = open(
    path.join(DIRECTORY, "DropboxAPI/token.txt")).read()

# HTTP Request Status enumeration


class HTTPRequest(Enum):
    STATUS_SUCCESS = 0
    STATUS_FAILURE = 1


"""
TodoFile class
"""


class TodoFile():
    """
    Parameters:

    _filename (str): Explorer file name
    _size (int): Explorer file size
    _last_modified_date (str): Explorer file last date of modification
    """

    def __init__(self, filename, size, last_modified_date):
        self._filename = filename
        self._size = size
        self._last_modified_date = last_modified_date


"""
Routine to convert these two type of date: "2020-03-22T14:33:23Z" or "2020-03-22 14:33:23"
"""


def convert_date(date, fromtimestamp=False, timezone=False):
    if not fromtimestamp:
        date_str = date.split("T")[0].split("-")
        time_str = date.split("T")[1].split("Z")[0].split(":")

    else:
        date_str = date.split(" ")[0].split("-")
        time_str = date.split(" ")[1].split(":")

    date = datetime.datetime(
        year=int(date_str[0]),
        month=int(date_str[1]),
        day=int(date_str[2]),
        hour=int(time_str[0]),
        minute=int(time_str[1]),
        second=int(time_str[2])
    )

    return date + datetime.timedelta(hours=1) if timezone else date


"""
Init Local Backups
On script launch only
"""


def init_local_backups():
    today = datetime.datetime.now().strftime('%d_%m_%Y')
    bak_directory = BACKUP_DIRECTORY + "/todos_bak-" + today + "/"

    if not path.exists(BACKUP_DIRECTORY) or len(listdir(BACKUP_DIRECTORY)) == 0:
        # Routine 1: Create all the necessary directories and the first backup folder
        if not path.exists(BACKUP_DIRECTORY):
            mkdir(BACKUP_DIRECTORY)

        mkdir(bak_directory)

        for f in listdir(DIRECTORY):
            if f.endswith(".todo"):
                shutil.copyfile(
                    DIRECTORY + "/" + f, bak_directory + f)
    else:
        bak_folder_list = []
        bak_date_list = []

        # Routine 2: Take the last backup generated folder and check all the saves
        for folder in scandir(BACKUP_DIRECTORY):
            bak_folder_list.append(folder)

        for bak_folder in bak_folder_list:
            bak_foldername = bak_folder.name
            bak_date_list.append(datetime.datetime(
                int(bak_foldername.split("-")[1].split("_")[2]),
                int(bak_foldername.split("-")[1].split("_")[1]),
                int(bak_foldername.split("-")[1].split("_")[0])
            ))

        most_recent_folder_date = max(bak_date_list).strftime('%d_%m_%Y')

        match = True

        todo_files_list = list_local_files()
        bak_files_list = list_local_files(
            custom_dir=True,
            custom_dir_name=BACKUP_DIRECTORY + "/todos_bak-" + most_recent_folder_date
        )

        # Looking for a single mismatch
        for todo_file in todo_files_list:
            todo_file_match = False

            for _f in bak_files_list:
                if todo_file._filename == _f._filename:
                    if filecmp.cmp(
                            DIRECTORY + "/" + todo_file._filename,
                            DIRECTORY + "/" + _f._filename):
                        todo_file_match = True

            if todo_file_match == False:
                match = False

        # Make a cleaner and proper save folder if a mismatch has been detected
        if not match:
            if not path.exists(bak_directory):
                mkdir(bak_directory)
            for file in listdir(DIRECTORY):
                if file.endswith(".todo"):
                    shutil.copyfile(
                        DIRECTORY + "/" + file, bak_directory + file)


"""
For local backups only
It removes backup folders older than 7 days
"""


def garbage_backups_cleaner(days=7):
    for folder in listdir(BACKUP_DIRECTORY):
        date = datetime.date(
            int(folder.split("-")[1].split("_")[2]),
            int(folder.split("-")[1].split("_")[1]),
            int(folder.split("-")[1].split("_")[0])
        )
        if date < (datetime.date.today() - datetime.timedelta(days)):
            shutil.rmtree(BACKUP_DIRECTORY + "/" + folder)


"""
For Dropbox backups
It checks all the saves on dropbox
"""


def comparing_todos(local_todo_files, dropbox_todo_files, prev_local_files):
    update_list = []

    for local_todo in local_todo_files:
        mismatch = False
        misupdate = False

        for dropbox_todo in dropbox_todo_files:
            time_delta = local_todo._last_modified_date - dropbox_todo._last_modified_date
            if local_todo._filename == dropbox_todo._filename:
                if time_delta.total_seconds() / 60 > 2:
                    misupdate = True
                else:
                    if local_todo._size != dropbox_todo._size:
                        misupdate = True
            else:
                mismatch = True

        if mismatch:
            for prev_local_file in prev_local_files:
                if prev_local_file._filename != local_todo._filename:
                    update_list.append(local_todo)
        else:
            update_list.append(local_todo)

        if misupdate:
            update_list.append(local_todo)

    # Transaction for files not to date

    if update_list != []:
        for dropbox_file in update_list:
            upload_todo(dropbox_file._filename)


"""
For local backups
Comparing the previous repertoring and the new repertoring
to detect new files on the local directory...
...or to detect a file update
"""


def comparing_local_todos(prev_todo_files, new_todo_files):
    todo_files_delta = []

    for todo_file in new_todo_files:
        misupdate = False

        for prev_todo_file in prev_todo_files:
            time_delta = todo_file._last_modified_date - prev_todo_file._last_modified_date
            if todo_file._filename == prev_todo_file._filename:
                if time_delta.total_seconds() / 60 != 0:
                    misupdate = True
                else:
                    if todo_file._size != prev_todo_file._size:
                        misupdate = True

        if misupdate == True:
            todo_files_delta.append(todo_file)

    if todo_files_delta != []:
        backup_todo(todo_files_delta)


"""
Upload files on Dropbox
"""


def upload_todo(todo_filename):
    headers = {
        "Authorization": "Bearer " + ACCESS_TOKEN,
        "Content-Type": "application/octet-stream",
        "Dropbox-API-Arg": "{\"path\":\"/todos/" + todo_filename + "\",\"mode\":{\".tag\":\"overwrite\"}}"
    }

    data = open(DIRECTORY + "/" + todo_filename, "rb").read()

    response = requests.post(UPLOAD_URL, headers=headers, data=data)

    if response.status_code != 200:
        return HTTPRequest.STATUS_FAILURE

    return HTTPRequest.STATUS_SUCCESS


"""
Backup files on appropriate backup defined folders
"""


def backup_todo(filelist):
    today = datetime.datetime.now().strftime('%d_%m_%Y')
    bak_directory = DIRECTORY + "/ToDosBak/todos_bak-" + today + "/"
    if not path.exists(bak_directory) or not path.isdir(bak_directory):
        mkdir(bak_directory)
    for todo_file in filelist:
        shutil.copyfile(
            DIRECTORY + "/" + todo_file._filename, bak_directory + todo_file._filename)


"""
List all local todo files
"""


def list_local_files(custom_dir=False, custom_dir_name=None):
    todo_files = []
    dirname = custom_dir_name if custom_dir else DIRECTORY
    folder_files = listdir(
        custom_dir_name) if custom_dir else listdir(DIRECTORY)

    for f in folder_files:
        if f.endswith(".todo"):
            todo_files.append(TodoFile(
                f,
                stat(dirname + "/" + f).st_size,
                convert_date(
                    datetime.datetime.fromtimestamp(
                        stat(dirname + "/" + f).st_mtime).strftime('%Y-%m-%d %H:%M:%S'), True)
            ))
    return todo_files


"""
List all dropbox todo files
"""


def list_dropbox_files():
    headers = {
        "Authorization": "Bearer " + ACCESS_TOKEN,
        "Content-Type": "application/json"
    }

    data = {
        "path": "/todos/",
        "recursive": False
    }

    response = requests.post(
        LIST_FOLDER_URL, headers=headers, data=json.dumps(data))

    if response.status_code != 200:
        print("FAILED: Le dossier contenant les todos n'existe probablement pas:")
        print("Créer un dossier \"todos\" dans Dropbox")
        return None

    entries = json.loads(response.text)['entries']

    todo_files = []

    for entry in entries:
        if entry[".tag"] == "file":
            todo_files.append(TodoFile(
                entry["name"],
                entry["size"],
                convert_date(
                    entry["server_modified"], timezone=True)
            ))

    return todo_files


"""
LOOP ROUTINE
"""


def permanent_check():
    # init the prev a first time, so he gets the same values as local_files below
    prev_local_files = []

    stopped = Event()

    while not stopped.wait(10):
        local_files = list_local_files()
        dropbox_files = list_dropbox_files()

        comparing_local_todos(prev_local_files, local_files)
        comparing_todos(
            local_files,
            dropbox_files,
            prev_local_files)
        garbage_backups_cleaner()

        prev_local_files = local_files


"""
MAIN
"""

if __name__ == "__main__":
    init_local_backups()
    garbage_backups_cleaner()

    permanent_check()
