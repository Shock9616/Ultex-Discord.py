"""
bot.py
Ultex

Created by Kaleb Rosborough on 12/07/2021
Copyright © Shock9616 2021 All rights reserved
"""

from pathlib import Path

import discord
from discord.ext import commands


class Bot(commands.Bot):
    def __init__(self, name, email, passwd, token, cmd_prefix='!', excluded_cogs=None):
        super().__init__(command_prefix=cmd_prefix, case_insensitive=True, intents=discord.Intents.all())
        self.name = name
        self.email = email
        self.passwd = passwd
        self.excluded_cogs = [] if excluded_cogs is None else excluded_cogs
        self.token = token
        self.dev_team = "shock9616@gmail.com"

        self._cogs = [p.stem for p in Path(".").glob("./bot/cogs/*.py")]

    def setup(self):
        print("Running setup...")

        for cog in self._cogs:
            if cog not in self.excluded_cogs:
                self.load_extension(f"bot.cogs.{cog}")
                print(f"Loaded cog: {cog}")
            else:
                print(f"Excluded cog: {cog}")

        print("Setup complete.")

    def run(self):
        self.setup()

        TOKEN = self.token

        print("Running bot...")
        super().run(TOKEN, reconnect=True)

    async def shutdown(self):
        print("Closing connection to Discord.")
        await super().close()

    async def close(self):
        print("Closing on keyboard Interrupt...")
        await self.shutdown()

    async def on_connect(self):
        print(f"Connected to Discord (latency: {self.latency * 1000} ms.")

    @staticmethod
    async def on_resumed():
        print("Bot resumed.")

    @staticmethod
    async def on_disconnect():
        print("Bot disconnected.")

    async def on_error(self, err, *args, **kwargs):
        raise

    async def on_command_error(self, ctx, exc):
        raise getattr(exc, "original", exc)

    async def on_ready(self):
        print("Bot ready!")
        print("--------------------\n"
              f"Logged in as {self.user.name}\n"
              f"Client id: {self.user.id}\n"
              "--------------------")

    async def process_commands(self, msg):
        ctx = await self.get_context(msg, cls=commands.Context)

        if ctx.command is not None:
            await self.invoke(ctx)

    async def on_message(self, msg):
        if not msg.author.bot:
            await self.process_commands(msg)

    def __repr__(self):
        return f"Bot: {self.name} - [Email: {self.email}, Dev Team: {self.dev_team}]"
