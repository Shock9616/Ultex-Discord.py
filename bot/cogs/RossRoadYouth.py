"""
RossRoadYouth.py
Ultex/cogs

Created by Kaleb Rosborough on 17/07/2021
Copyright © Shock9616 2021 All rights reserved
"""

import random

from discord.ext import commands


class RossRoadYouth(commands.Cog, name="Ross Road Youth"):
    def __init__(self, client):
        self.client = client

    @commands.command(name="verse", aliases=["passage", "scripture", "encourage"])
    async def verse(self, ctx):
        """ Send an encouraging bible verse """
        with open("data/verses.txt", "r") as file:
            verses = file.read().splitlines()
            verse = random.choice(verses)
            await ctx.send(f"{verse}")

    @commands.command(name="hollyjoke", aliases=["craigjoke"])
    async def joke_command(self, ctx):
        """ Exactly the same as !joke, but with a more relevant name """
        with open("data/jokes.txt", "r") as file:
            jokes = file.read().splitlines()
            joke = random.choice(jokes)
            await ctx.send(f"{joke}")


def setup(client):
    client.add_cog(RossRoadYouth(client))
