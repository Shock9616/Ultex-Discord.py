"""
Music.py
Ultex

Created by Kaleb Rosborough on 13/07/2021
Copyright © Shock9616 2021 All rights reserved
"""
import asyncio
import datetime as dt
import random
import re
import typing as t
from enum import Enum

import discord
import wavelink
from discord.ext import commands

URL_REGEX = r"(?i)\b((?:https?://|www\d{0,3}[.]|[a-z0-9.\-]+[.][a-z]{2,4}/)(?:[^\s()<>]+|\(([^\s()<>]+|(\([^\s()<>]+\)))*\))+(?:\(([^\s()<>]+|(\([^\s()<>]+\)))*\)|[^\s`!()\[\]{};:'\".,<>?«»“”‘’]))"
OPTIONS = {
    "1️⃣": 0,
    "2⃣": 1,
    "3⃣": 2,
    "4⃣": 3,
    "5⃣": 4,
}


# ---------- Custom Error Classes ----------
class AlreadyConnectedToChannel(commands.CommandError):
    pass


class NoVoiceChannel(commands.CommandError):
    pass


class QueueIsEmpty(commands.CommandError):
    pass


class NoTracksFound(commands.CommandError):
    pass


class PlayerIsAlreadyPlaying(commands.CommandError):
    pass


class PlayerIsAlreadyPaused(commands.CommandError):
    pass


class NoMoreTracks(commands.CommandError):
    pass


class NoPreviousTracks(commands.CommandError):
    pass


class InvalidRepeatMode(commands.CommandError):
    pass


class RepeatMode(Enum):
    NONE = 0
    ONE = 1
    ALL = 2


class Queue:
    def __init__(self):
        self._queue = []
        self.position = 0
        self.repeat_mode = RepeatMode.NONE

    @property
    def is_empty(self):
        return not self._queue

    @property
    def first_track(self):
        """ Return the first track in the queue """
        if not self._queue:
            raise QueueIsEmpty

        return self._queue[0]

    @property
    def current_track(self):
        if not self._queue:
            raise QueueIsEmpty

        if self.position <= len(self._queue) - 1:
            return self._queue[self.position]

    @property
    def up_next(self):
        if not self._queue:
            raise QueueIsEmpty

        return self._queue[self.position + 1:]

    @property
    def history(self):
        if not self._queue:
            raise QueueIsEmpty

        return self._queue[:self.position]

    @property
    def length(self):
        return len(self._queue)

    def add(self, *args):
        """ Add a song to the queue """
        self._queue.extend(args)

    def empty(self):
        """ Remove all tracks from the queue """
        self._queue.clear()
        self.position = 0

    def get_next_track(self):
        """ Return the next track in the queue"""
        if not self._queue:
            raise QueueIsEmpty

        self.position += 1

        if self.position < 0:
            return None
        elif self.position > len(self._queue) - 1:
            if self.repeat_mode == RepeatMode.ALL:
                self.position = 0
            else:
                return None

        return self._queue[self.position]

    def shuffle(self):
        """ Shuffle the upcoming tracks in the queue """
        if not self._queue:
            raise QueueIsEmpty

        up_next = self.up_next
        random.shuffle(up_next)
        self._queue = self._queue[:self.position + 1]
        self._queue.extend(up_next)

    def set_repeat_mode(self, mode):
        if mode == "none":
            self.repeat_mode = RepeatMode.NONE
        elif mode == "1":
            self.repeat_mode = RepeatMode.ONE
        elif mode == "all":
            self.repeat_mode = RepeatMode.ALL


class Player(wavelink.Player):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.queue = Queue()

    async def connect(self, ctx, channel=None):
        """ Connect to your current voice channel or the channel that you specify """
        if self.is_connected:
            raise AlreadyConnectedToChannel

        if (channel := getattr(ctx.author.voice, "channel", channel)) is None:
            raise NoVoiceChannel

        await super().connect(channel.id)
        return channel

    async def teardown(self):
        """ Disconnect from the current voice channel """
        try:
            await self.destroy()
        except KeyError:
            pass

    async def add_tracks(self, ctx, tracks):
        """ Add track(s) to the queue """
        if not tracks:
            raise NoTracksFound

        if isinstance(tracks, wavelink.TrackPlaylist):
            self.queue.add(*tracks.tracks)

        elif len(tracks) == 1:
            self.queue.add(tracks[0])
            await ctx.send(f"Added \"{tracks[0].title}\" to the queue")

        else:
            if (track := await self.choose_track(ctx, tracks)) is not None:
                self.queue.add(track)
                await ctx.send(f"Added \"{track.title}\" to the queue")

        if not self.is_playing and not self.queue.is_empty:
            await self.start_playback()

    async def choose_track(self, ctx, tracks):
        """ Show an embed of the top 5 search results
        and use reactions to detect the choice"""

        def _check(r, u):
            return (
                r.emoji in OPTIONS.keys()
                and u == ctx.author
                and r.message.id == msg.id
            )

        embed = discord.Embed(
            title="Choose a song:",
            description=(
                "\n".join(
                    f"**{i + 1}.** {j.title} ({j.length // 60000}:{str(j.length % 60).zfill(2)})"
                    for i, j in enumerate(tracks[:5])
                )
            ),
            colour=ctx.author.colour,
            timestamp=dt.datetime.utcnow()
        )
        embed.set_author(name="Query Results")
        embed.set_footer(text=f"Invoked by {ctx.author.display_name}", icon_url=ctx.author.avatar_url)

        msg = await ctx.send(embed=embed)
        for emoji in list(OPTIONS.keys())[:min(len(tracks), len(OPTIONS))]:
            await msg.add_reaction(emoji)

        try:
            reaction, _ = await self.bot.wait_for("reaction_add", timeout=60.0, check=_check)
        except asyncio.TimeoutError:
            await msg.delete()
            await ctx.message.delete()
        else:
            await msg.delete()
            return tracks[OPTIONS[reaction.emoji]]

    async def start_playback(self):
        """ Start playing the first track in the queue """
        await self.play(self.queue.current_track)

    async def advance(self):
        """ Advance to the next track in the queue """
        try:
            if (track := self.queue.get_next_track()) is not None:
                await self.play(track)

        except QueueIsEmpty:
            pass

    async def repeat_track(self):
        await self.play(self.queue.current_track)


class Music(commands.Cog, wavelink.WavelinkMixin):
    def __init__(self, client):
        self.client = client
        self.wavelink = wavelink.Client(bot=client)
        self.client.loop.create_task(self.start_nodes())

    @commands.Cog.listener()
    async def on_voice_state_update(self, member, before, after):
        """ When a user disconnects from the current voice channel,
            and if they are the last non-bot user, disconnect """
        if not member.bot and after.channel is None:
            if not [m for m in before.channel.members if not m.bot]:
                await self.get_player(member.guild).teardown()

    @wavelink.WavelinkMixin.listener()
    async def on_node_ready(self, node):
        """ Let the console know that the wavelink node is ready """
        print(f"Wavelink node '{node.identifier}' ready")

    @wavelink.WavelinkMixin.listener("on_track_stuck")
    @wavelink.WavelinkMixin.listener("on_track_end")
    @wavelink.WavelinkMixin.listener("on_track_exception")
    async def on_player_stop(self, node, payload):
        if payload.player.queue.repeat_mode == RepeatMode.ONE:
            await payload.player.repeat_track()
        else:
            await payload.player.advance()

    async def cog_check(self, ctx):
        """ Make sure that the command is not being issued from a DM """
        if isinstance(ctx.channel, discord.DMChannel):
            await ctx.send("Sorry, Music commands are not available in DMs")
            return False

        return True

    async def start_nodes(self):
        """ Start wavelink nodes """
        await self.client.wait_until_ready()

        nodes = {
            "MAIN": {
                "host": "127.0.0.1",
                "port": 2333,
                "rest_uri": "http://127.0.0.1:2333",
                "password": "youshallnotpass",
                "identifier": "MAIN",
                "region": "us_west"
            }
        }

        for node in nodes.values():
            await self.wavelink.initiate_node(**node)

    def get_player(self, obj):
        """ Return the player that issued the command """
        if isinstance(obj, commands.Context):
            return self.wavelink.get_player(obj.guild.id, cls=Player, context=obj)
        elif isinstance(obj, discord.Guild):
            return self.wavelink.get_player(obj.id, cls=Player)

    @commands.command(name="connect", aliases=["join"])
    async def connect_command(self, ctx, *, channel: t.Optional[discord.VoiceChannel]):
        """ Connect to a voice channel """
        player = self.get_player(ctx)
        channel = await player.connect(ctx, channel)
        await ctx.send(f"```Connected to {channel.name}.```")

    @connect_command.error
    async def connect_command_error(self, ctx, exc):
        """ Display any errors related to the connect command """
        if isinstance(exc, AlreadyConnectedToChannel):
            await ctx.send("Already connected to a voice channel")
        elif isinstance(exc, NoVoiceChannel):
            await ctx.send("No suitable voice channel was provided")

    @commands.command(name="disconnect", aliases=["leave"])
    async def disconnect_command(self, ctx):
        """ Disconnect from the current voice channel """
        player = self.get_player(ctx)
        await player.disconnect()
        await ctx.send("Disconnected from voice chat")

    @commands.command(name="play")
    async def play_command(self, ctx, *, query: t.Optional[str]):
        """ Play a song or resume playback """
        player = self.get_player(ctx)

        if not player.is_connected:
            await player.connect(ctx)

        if query is None:
            if player.queue.is_empty:
                raise QueueIsEmpty

            if player.is_playing:
                raise PlayerIsAlreadyPlaying

            await player.set_pause(False)
            await ctx.send("Playback resumed")

        else:
            query = query.strip("<>")
            if not re.match(URL_REGEX, query):
                query = f"ytsearch:{query}"

            await player.add_tracks(ctx, await self.wavelink.get_tracks(query))

    @play_command.error
    async def play_command_error(self, ctx, exc):
        """ Display any errors related to the play command """
        if isinstance(exc, QueueIsEmpty):
            await ctx.send("Queue is empty")

        if isinstance(exc, NoVoiceChannel):
            await ctx.send("Please join a voice channel before playing music")

    @commands.command(name="pause")
    async def pause_command(self, ctx):
        """ Pause playback """
        player = self.get_player(ctx)

        if player.is_paused:
            raise PlayerIsAlreadyPaused

        await player.set_pause(True)
        await ctx.send("Playback paused")

    @pause_command.error
    async def pause_command_error(self, ctx, exc):
        """ Display any errors related to the pause command """
        if isinstance(exc, PlayerIsAlreadyPaused):
            await ctx.send("Playback is already paused")

    @commands.command(name="stop")
    async def stop_command(self, ctx):
        """ Stop playback and clear the queue """
        player = self.get_player(ctx)
        player.queue.empty()
        await player.stop()
        await ctx.send("Playback stopped")

    @commands.command(name="skip", aliases=["next"])
    async def skip_command(self, ctx):
        """ Skip to the next track in the queue """
        player = self.get_player(ctx)

        if not player.queue.up_next:
            raise NoMoreTracks

        await player.stop()
        await ctx.send("Playing next track in queue")

    @skip_command.error
    async def skip_command_error(self, ctx, exc):
        """ Display any errors related to the skip command"""
        if isinstance(exc, QueueIsEmpty):
            await ctx.send("Could not skip as the queue is currently empty")

        if isinstance(exc, NoMoreTracks):
            await ctx.send("Could not skip as there are no more tracks in the queue")

    @commands.command(name="back", aliases=["previous"])
    async def back_command(self, ctx):
        """ Go back to the previous track in the queue """
        player = self.get_player(ctx)

        if not player.queue.history:
            raise NoPreviousTracks

        player.queue.position -= 2
        await player.stop()
        await ctx.send("Playing previous track in queue")

    @back_command.error
    async def back_command_error(self, ctx, exc):
        """ Display any errors related to the back command """
        if isinstance(exc, QueueIsEmpty):
            await ctx.send("Could not go back as the queue is currently empty")

        if isinstance(exc, NoPreviousTracks):
            await ctx.send("Could not go back as there are no previous tracks to go to")

    @commands.command(name="shuffle")
    async def shuffle_command(self, ctx):
        """ Shuffle the upcoming tracks in the queue """
        player = self.get_player(ctx)

        player.queue.shuffle()
        await ctx.send("Shuffled queue")

    @shuffle_command.error
    async def shuffle_command_error(self, ctx, exc):
        """ Display any errors related to the shuffle command """
        if isinstance(exc, QueueIsEmpty):
            await ctx.send("Couldn't shuffle queue as the queue is currently empty")

    @commands.command(name="repeat", aliases=["loop"])
    async def repeat_command(self, ctx, mode: str):
        """ Set the music to repeat 1 song or the whole queue """
        player = self.get_player(ctx)

        if mode not in ("none", "1", "all"):
            raise InvalidRepeatMode

        player.queue.set_repeat_mode(mode)

        await ctx.send(f"The repeat mode has been set to {mode}")

    @commands.command(name="queue")
    async def queue_command(self, ctx, show: t.Optional[int] = 10):
        """ Show the specified number of tracks. Defaults to 10 """
        player = self.get_player(ctx)

        if player.queue.is_empty:
            raise QueueIsEmpty

        embed = discord.Embed(
            title="Queue",
            description=f"Showing up to the next {show} tracks",
            colour=ctx.author.colour,
            timestamp=dt.datetime.utcnow()
        )
        embed.set_author(name="Query Results")
        embed.set_footer(text=f"Requested by {ctx.author.display_name}", icon_url=ctx.author.avatar_url)
        embed.add_field(
            name="Currently playing",
            value=getattr(player.queue.current_track, "title", "No tracks are currently playing "),
            inline=False
        )
        if up_next := player.queue.up_next[:show]:
            embed.add_field(
                name="Next up",
                value="\n".join(track.title for track in up_next),
                inline=False
            )

        await ctx.send(embed=embed)

    @queue_command.error
    async def queue_command_error(self, ctx, exc):
        """ Display any errors related to the queue command """
        if isinstance(exc, QueueIsEmpty):
            await ctx.send("The queue is currently empty")


def setup(client):
    client.add_cog(Music(client))
