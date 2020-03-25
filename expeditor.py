#!/usr/bin/env python3

from os import listdir, scandir, path, stat, mkdir
from threading import Event
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

# To update ASAP, the access token DOES NOT HAVE TO stay in clear in the code...
ACCESS_TOKEN = ""

# HTTP Request Status enumeration
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


def convert_date(date, fromtimestamp=False):
    if not fromtimestamp:
        date_str = date.split("T")[0].split("-")
        time_str = date.split("T")[1].split("Z")[0].split(":")

    else:
        date_str = date.split(" ")[0].split("-")
        time_str = date.split(" ")[1].split(":")

    return datetime.datetime(
        int(date_str[0]),
        int(date_str[1]),
        int(date_str[2]),
        int(time_str[0]),
        int(time_str[1]),
        int(time_str[2])
    )


"""
INIT ROUTINE: Local Backups
Executing this routine on script launch only !!!
"""


def init_local_backups():
    today = datetime.datetime.now().strftime('%d_%m_%Y')
    bak_directory = BACKUP_DIRECTORY + "/todos_bak-" + today + "/"

    if not path.exists(BACKUP_DIRECTORY) or len(listdir(BACKUP_DIRECTORY)) == 0:
        # Routine 1: Create all the necessary directories and the first backup folder
        if not path.exists(BACKUP_DIRECTORY):
            mkdir(BACKUP_DIRECTORY)

        mkdir(bak_directory)

        for file in listdir(DIRECTORY):
            if file.endswith(".todo"):
                shutil.copyfile(
                    DIRECTORY + "/" + file, bak_directory + file)
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

        match = True

        # Looking for a single mismatch
        for todo_file in list_local_files():
            todo_file_match = False

            for file in list_local_files(
                    True,
                    BACKUP_DIRECTORY + "/todos_bak-" +
                    max(bak_date_list).strftime('%d_%m_%Y') + "/"
            ):
                time_delta = todo_file._last_modified_date - \
                    file._last_modified_date
                if todo_file._filename == file._filename:
                    if 0 < time_delta.total_seconds() / 60 <= 2:
                        todo_file_match = True
                    else:
                        if todo_file._size == file._size and filecmp.cmp(
                                DIRECTORY + "/" + todo_file._filename,
                                DIRECTORY + "/" + file._filename):
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
INIT ROUTINE: Dropbox backups
Executing this routine on script launch only !!!
"""


def init_dropbox_backups():
    comparing_todos(list_local_files(), list_dropbox_files())


"""
GARBAGE CLEANER: For local backups only
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
CHECK ROUTINE: For Dropbox backups
It checks all the saves on dropbox
"""


def comparing_todos(local_todo_files, dropbox_todo_files):
    missing_dropbox_files = []
    missing_local_files = []

    # Detect Local Lacks

    for dropbox_todo in dropbox_todo_files:
        dropbox_file_match = False

        for local_todo in local_todo_files:
            time_delta = dropbox_todo._last_modified_date - \
                local_todo._last_modified_date
            if dropbox_todo._filename == local_todo._filename:
                if time_delta.total_seconds() / 60 < 240:
                    dropbox_file_match = True
                else:
                    if dropbox_todo._size == local_todo._size and filecmp.cmp(
                            DIRECTORY + "/" + dropbox_todo._filename,
                            DIRECTORY + "/" + local_todo._filename):
                        dropbox_file_match = True

        if dropbox_file_match == False:
            missing_local_files.append(dropbox_todo)

    # Detect Dropbox Lacks

    for local_todo in local_todo_files:
        local_file_match = False

        for dropbox_todo in dropbox_todo_files:
            time_delta = local_todo._last_modified_date - dropbox_todo._last_modified_date
            if local_todo._filename == dropbox_todo._filename:
                if time_delta.total_seconds() / 60 < 240:
                    local_file_match = True
                else:
                    if local_todo._size == dropbox_todo._size and filecmp.cmp(
                            DIRECTORY + "/" + local_todo._filename,
                            DIRECTORY + "/" + dropbox_todo._filename):
                        local_file_match = True

        if local_file_match == False:
            missing_dropbox_files.append(local_todo)

    # Transaction for missing files

    if missing_dropbox_files != []:
        print("Des mises à jour ont été détectées: Upload en cours...")
        for missing_dropbox_file in missing_dropbox_files:
            print("> " + missing_dropbox_file._filename)
            upload_todo(missing_dropbox_file._filename)
    if missing_local_files != []:
        print("Des mises à jour ont été détectées: Téléchargement en cours...")
        for missing_local_file in missing_local_files:
            print("> " + missing_local_file._filename)
            download_todo(missing_local_file._filename)


"""
CHECK ROUTINE: For local backups
Comparing the previous repertoring and the new repertoring
to detect new files on the local directory...
...or to detect a file update
"""


def comparing_local_todos(prev_todo_files, new_todo_files):
    todo_files_delta = []

    for todo_file in new_todo_files:
        todo_file_match = False

        for prev_todo_file in prev_todo_files:
            time_delta = todo_file._last_modified_date - prev_todo_file._last_modified_date
            if todo_file._filename == prev_todo_file._filename:
                if 0 < time_delta.total_seconds() / 60 <= 2:
                    todo_file_match = True
                elif -2 < time_delta.total_seconds() / 60 <= 0:
                    todo_file_match = True
                else:
                    if todo_file._size == prev_todo_file._size and filecmp.cmp(
                            DIRECTORY + "/" + todo_file._filename,
                            DIRECTORY + "/" + prev_todo_file._filename):
                        todo_file_match = True

        if todo_file_match == False:
            todo_files_delta.append(todo_file)

    if todo_files_delta != []:
        print("Des mises à jour ont été détectées: Sauvegarde en local:")
        backup_todo(todo_files_delta)


"""
SUBROUTINE: Upload files on Dropbox
Never call it outside a function !!!
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
        return STATUS_FAILURE

    return STATUS_SUCCESS


"""
SUBROUTINE: Download files on Dropbox
Never call it outside a function !!!
"""


def download_todo(todo_filename):
    headers = {
        "Authorization": "Bearer " + ACCESS_TOKEN,
        "Dropbox-API-Arg": "{\"path\":\"/todos/" + todo_filename + "\"}"
    }

    response = requests.post(DOWNLOAD_URL, headers=headers)

    if response.status_code != 200:
        return STATUS_FAILURE

    todo_file_downloaded = open(DIRECTORY + "/" + todo_filename, "w+")
    todo_file_downloaded.write(response.text)
    todo_file_downloaded.close()

    return STATUS_SUCCESS


"""
SUBROUTINE: Backup files on appropriate backup defined folders
Never call it outside a function !!!
"""


def backup_todo(filelist):
    today = datetime.datetime.now().strftime('%d_%m_%Y')
    bak_directory = DIRECTORY + "/ToDosBak/todos_bak-" + today + "/"
    if not path.exists(bak_directory) or not path.isdir(bak_directory):
        mkdir(bak_directory)
    for todo_file in filelist:
        print("> " + todo_file._filename)
        shutil.copyfile(
            DIRECTORY + "/" + todo_file._filename, bak_directory + todo_file._filename)

# Repertoring all the todo files into the Documents directory


"""
LIST ROUTINE: List all local todo files
"""


def list_local_files(custom_dir=False, custom_dir_name=None):
    todo_files = []
    for file in (listdir(DIRECTORY) if not custom_dir else listdir(custom_dir_name)):
        if file.endswith(".todo"):
            todo_files.append(TodoFile(
                file,
                stat(DIRECTORY + "/" + file).st_size,
                convert_date(
                    datetime.datetime.fromtimestamp(
                        stat(DIRECTORY + "/" + file).st_mtime).strftime('%Y-%m-%d %H:%M:%S'), True)
            ))
    return todo_files


"""
LIST ROUTINE: List all dropbox todo files
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
                    entry["server_modified"])
            ))

    return todo_files


"""
LOOP ROUTINE
"""


def permanent_check():
    # init the prev a first time, so he gets the same values as local_files below
    prev_local_files = list_local_files()
    stopped = Event()

    while not stopped.wait(10):
        local_files = list_local_files()
        comparing_local_todos(prev_local_files, local_files)
        comparing_todos(local_files, list_dropbox_files())
        garbage_backups_cleaner()
        prev_local_files = local_files


"""
MAIN ROUTINE
"""

if __name__ == "__main__":
    init_local_backups()
    init_dropbox_backups()
    garbage_backups_cleaner()

    permanent_check()
