"""
FunStuff.py
Ultex/cogs

Created by Kaleb Rosborough on 12/07/2021
Copyright © Shock9616 2021 All rights reserved
"""

import random

from discord.ext import commands


class FunStuff(commands.Cog, name="Fun Stuff"):
    def __init__(self, client):
        self.client = client

    # ----- Commands -----

    @commands.command(name="joke", aliases=["dadjoke"])
    async def joke_command(self, ctx):
        """ Send a really bad joke """
        with open("data/jokes.txt", "r") as file:
            jokes = file.read().splitlines()
            joke = random.choice(jokes)
            await ctx.send(f"{joke}")


def setup(client):
    client.add_cog(FunStuff(client))
