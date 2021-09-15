#!/usr/bin/env python3

"""
main.py
Ultex

Created by Kaleb Rosborough on 12/07/2021
Copyright © Shock9616 2021 All rights reserved
"""

import multiprocessing
import subprocess
import time

from bot import Bot
from config import secrets

TOKEN = secrets.DISCORD_TOKEN
EMAIL_PASSWD = secrets.EMAIL_PASSWD


def main():
    """ Create the main Bot instance and run it """
    ultex = Bot(name="Ultex",
                email="ultexbot@gmail.com",
                passwd=EMAIL_PASSWD,
                excluded_cogs=["RossRoadYouth"],
                token=TOKEN)

    ultex.run()


def launch_lavalink():
    """ Launch the lavalink server so that music can be played """
    subprocess.run(["java", "-jar", "lavalink.jar"])


if __name__ == "__main__":
    lavalink = multiprocessing.Process(target=launch_lavalink)
    bot = multiprocessing.Process(target=main)

    lavalink.start()
    time.sleep(6)
    bot.start()
