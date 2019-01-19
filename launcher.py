"""Runs bot"""

import os
import subprocess
import sys
import shutil

# USEFUL FUNCTIONS
if sys.platform == "win32" or sys.platform == "win64":

    def clear():
        return os.system("cls")
else:

    def clear():
        return os.system("clear")


def check_updates():
    """Checks if there are some available updates for the bot"""
    subprocess.call(
        "git fetch",
        stdout=open(os.devnull, 'w'),
        stderr=subprocess.STDOUT,
        shell=True)
    result = subprocess.check_output("git status", shell=True)
    if "Your branch is behind" in str(result):
        answer = input(
            "The bot isn't up-to-date, please type 'yes' to update it!\n\n> ")
        if answer.upper() == "YES":
            os.system("git pull")


def ask_user():
    """Asks user for installing requirements/launching the bot"""
    answer = ""
    while answer != "3":
        clear()

        answer = input("What do you want to do?\n\n" +
                       "1. Install & update requirements\n" +
                       "2. Launch the bot\n" + "3. Quit\n\n> ")

        if answer == "1":
            install_requirements()
        elif answer == "2":
            from bot import run_bot
            run_bot()


def install_requirements():
    """Installs requirements"""
    subprocess.call(
        "python -m pip install -U -r requirements.txt",
        stdout=open(os.devnull, 'w'),
        stderr=subprocess.STDOUT,
        shell=True)


if __name__ == "__main__":
    check_updates()
    clear()
    ask_user()
