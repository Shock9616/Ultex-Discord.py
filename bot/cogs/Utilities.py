"""
Utilities.py
Ultex/cogs

Created by Kaleb Rosborough on 12/07/2021
Copyright © Shock9616 2021 All rights reserved
"""

import datetime as dt
import random
import smtplib
from email.mime.text import MIMEText as text

import discord
import wikipedia
import wolframalpha
from discord.ext import commands


# ---------- Custom Error Classes ----------
class NoAddressesProvided(commands.CommandError):
    pass


class NoSearchResults(commands.CommandError):
    pass


class Utilities(commands.Cog):
    def __init__(self, client):
        self.client = client

    # ----- Commands -----

    @commands.command(name="invite")
    async def invite_command(self, ctx, *recipients: str):
        """ Send an invite link to the specified email address(es) """
        if not recipients:
            raise NoAddressesProvided

        link = await ctx.channel.create_invite(max_uses=len(recipients))

        server = smtplib.SMTP("smtp.gmail.com", 587)
        server.starttls()
        server.login(self.client.email, self.client.passwd)

        msg = text(str("Greetings earthling!\n\n" + str(ctx.author) + " has invited you to join the " + str(
            ctx.guild) + " discord server.\nClick the link below to accept the invitation.\n" + str(
            link) + "\n\nHope to talk to you soon!\n" + str(ctx.guild) + "."))
        msg["Subject"] = str("Invite to " + str(ctx.guild))
        msg["From"] = self.client.email

        for i in range(len(recipients)):
            msg["To"] = recipients[i]
            server.sendmail(self.client.email, recipients[i], msg.as_string())

        server.quit()

        if len(recipients) > 1:
            response = "Sent invite email to "
            for i in range(len(recipients)):
                if i == len(recipients) - 1:
                    response = response + "and " + recipients[i]
                else:
                    response = response + recipients[i] + ", "
        else:
            response = "Sent invite email to " + recipients[0]

        await ctx.send({response})

    @invite_command.error
    async def invite_command_error(self, ctx, exc):
        """ Display any errors related to the invite command """
        if isinstance(exc, NoAddressesProvided):
            await ctx.send("Please provide at least 1 email address")

    @commands.command(name="rand", aliases=["random"])
    async def random_number_command(self, ctx, minimum: int = 0, maximum: int = 10):
        """ Generate a random integer and send it in a message.
            Defaults to a random number between 0 and 10 """
        random_int = str(random.randint(minimum, maximum))
        await ctx.send(f"Your random number is {random_int}")

    @commands.command(name="search", aliases=["ask"])
    async def search_command(self, ctx, *query: str):
        """ Search for literally anything
        The bot isn't always correct but it will certainly try its best to be """
        # TODO: Import wolfram api key from config/secrets instead of hard-coding it
        wolf = wolframalpha.Client("AA92HA-R4TPUE59R9")
        query = " ".join(query)

        try:
            res = wolf.query(query)
            answer = next(res.results).text
        except (StopIteration, AttributeError):
            try:
                answer = wikipedia.summary(query, sentences=2)
            except wikipedia.exceptions.PageError:
                raise NoSearchResults

        embed = discord.Embed(
            title=query,
            colour=ctx.author.colour,
            timestamp=dt.datetime.utcnow()
        )
        embed.set_footer(text=f"Requested by {ctx.author.display_name}", icon_url=ctx.author.avatar_url)
        embed.add_field(name="Search Results", value=answer, inline=False)

        await ctx.send(embed=embed)

    @search_command.error
    async def search_command_error(self, ctx, exc):
        """ Display any errors related to the search command """
        if isinstance(exc, NoSearchResults):
            await ctx.send("Unable to find any search results")


def setup(client):
    client.add_cog(Utilities(client))
