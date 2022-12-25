import logging
import os
from typing import Optional
from datetime import datetime as dt

import hikari
import lightbulb


import lavasnek_rs


class EventHandler:
    """Events from the Lavalink server"""

    async def track_start(self, _: lavasnek_rs.Lavalink, event: lavasnek_rs.TrackStart) -> None:
        logging.info("Track started on guild: %s", event.guild_id)

    async def track_finish(self, _: lavasnek_rs.Lavalink, event: lavasnek_rs.TrackFinish) -> None:
        logging.info("Track finished on guild: %s", event.guild_id)

    async def track_exception(self, lavalink: lavasnek_rs.Lavalink, event: lavasnek_rs.TrackException) -> None:
        logging.warning(
            "Track exception event happened on guild: %d", event.guild_id)

        # If a track was unable to be played, skip it
        skip = await lavalink.skip(event.guild_id)
        node = await lavalink.get_guild_node(event.guild_id)

        if not node:
            return

        if skip and not node.queue and not node.now_playing:
            await lavalink.stop(event.guild_id)


plugin = lightbulb.Plugin("Music", "🎧 Music commands")


async def _join(ctx: lightbulb.Context) -> Optional[hikari.Snowflake]:
    assert ctx.guild_id is not None

    if not (voice_state := ctx.bot.cache.get_voice_state(ctx.guild_id, ctx.author.id)):
        await ctx.respond("Connect to a voice channel first")
        return None

    channel_id = voice_state.channel_id

    assert channel_id is not None

    await plugin.bot.update_voice_state(ctx.guild_id, channel_id, self_deaf=True)
    connection_info = await plugin.bot.d.lavalink.wait_for_full_connection_info_insert(ctx.guild_id)

    await plugin.bot.d.lavalink.create_session(connection_info)

    return channel_id


@plugin.listener(hikari.ShardReadyEvent)
async def start_lavalink(event: hikari.ShardReadyEvent) -> None:

    builder = (
        lavasnek_rs.LavalinkBuilder(
            event.my_user.id, os.environ["TOKEN"]).set_is_ssl(True).set_port(443)
        .set_host("node1.kartadharta.xyz").set_password('kdlavalink')
    )

    # builder.set_start_gateway(False)

    lava_client = await builder.build(EventHandler())

    plugin.bot.d.lavalink = lava_client


@plugin.command()
@lightbulb.add_checks(lightbulb.guild_only)
@lightbulb.command("join", "Joins the voice channel you are in.")
@lightbulb.implements(lightbulb.SlashCommand)
async def join(ctx: lightbulb.Context) -> None:
    channel_id = await _join(ctx)

    if channel_id:
        await ctx.respond(f"Joined <#{channel_id}>")


@plugin.command()
@lightbulb.add_checks(lightbulb.guild_only)
@lightbulb.command("leave", "Leaves the voice channel the bot is in, clearing the queue.")
@lightbulb.implements(lightbulb.SlashCommand)
async def leave(ctx: lightbulb.Context) -> None:

    await plugin.bot.d.lavalink.destroy(ctx.guild_id)

    if ctx.guild_id is not None:
        await plugin.bot.update_voice_state(ctx.guild_id, None)
        await plugin.bot.d.lavalink.wait_for_connection_info_remove(ctx.guild_id)

    # Destroy nor leave remove the node nor the queue loop, you should do this manually.
    await plugin.bot.d.lavalink.remove_guild_node(ctx.guild_id)
    await plugin.bot.d.lavalink.remove_guild_from_loops(ctx.guild_id)

    await ctx.respond("Left voice channel")


@plugin.command()
@lightbulb.add_checks(lightbulb.guild_only)
@lightbulb.option("query", "The query to search for.", modifier=lightbulb.OptionModifier.CONSUME_REST, required=True)
@lightbulb.command("play", "Searches the query on youtube, or adds the URL to the queue.")
@lightbulb.implements(lightbulb.PrefixCommand, lightbulb.SlashCommand)
async def play(ctx: lightbulb.Context) -> None:
    query = ctx.options.query
    con = plugin.bot.d.lavalink.get_guild_gateway_connection_info(ctx.guild_id)
    if not con:
        await _join(ctx)

    query_information = await plugin.bot.d.lavalink.auto_search_tracks(query)

    if not query_information.tracks:
        await ctx.respond("Could not find any video of the search query.")
        return

    try:
        await plugin.bot.d.lavalink.play(ctx.guild_id, query_information.tracks[0]).requester(ctx.author.id).queue()

    except lavasnek_rs.NoSessionPresent:
        await ctx.respond("Use `/join` first")
        return

    await ctx.respond(f"Added to queue: {query_information.tracks[0].info.title}")


@plugin.command()
@lightbulb.add_checks(lightbulb.guild_only)
@lightbulb.command("stop", "Stops the current song (skip to continue).")
@lightbulb.implements(lightbulb.SlashCommand)
async def stop(ctx: lightbulb.Context) -> None:

    await plugin.bot.d.lavalink.stop(ctx.guild_id)
    await ctx.respond("Stopped playing")


@plugin.command()
@lightbulb.add_checks(lightbulb.guild_only)
@lightbulb.command("skip", "Skips the current song.")
@lightbulb.implements(lightbulb.SlashCommand)
async def skip(ctx: lightbulb.Context) -> None:
    skip = await plugin.bot.d.lavalink.skip(ctx.guild_id)
    node = await plugin.bot.d.lavalink.get_guild_node(ctx.guild_id)

    if not skip:
        await ctx.respond("Nothing to skip")
    else:
        if not node.queue and not node.now_playing:
            await plugin.bot.d.lavalink.stop(ctx.guild_id)

        await ctx.respond(f"Skipped: {skip.track.info.title}")


@plugin.command()
@lightbulb.add_checks(lightbulb.guild_only)
@lightbulb.command("nowplaying", "Gets the song that's currently playing.", aliases=["np"])
@lightbulb.implements(lightbulb.SlashCommand)
async def now_playing(ctx: lightbulb.Context) -> None:
    node = await plugin.bot.d.lavalink.get_guild_node(ctx.guild_id)

    if not node or not node.now_playing:
        await ctx.respond("Nothing is playing at the moment.")
        return

    await ctx.respond(f"Now Playing: {node.now_playing.track.info.title}")


@plugin.command()
@lightbulb.add_checks(lightbulb.guild_only)
@lightbulb.command("queue", "Gets the queue of tracks", aliases=["q"])
@lightbulb.implements(lightbulb.SlashCommand)
async def now_playing(ctx: lightbulb.Context) -> None:
    target = ctx.get_guild().get_member(ctx.user)
    node = await plugin.bot.d.lavalink.get_guild_node(ctx.guild_id)

    if not node or not node.now_playing:
        await ctx.respond("Nothing is playing at the moment.")
        return

    titles = []
    requests = []
    for item in node.queue:
        titles.append(item.track.info.title)
        requests.append(item.requester)

    embed = (
        hikari.Embed(
            title=f"🎶 Current queue | {len(titles)} tracks",
            colour=0x181818,
            timestamp=dt.now().astimezone(),
        )
        .set_footer(
            text=f"Requested by {ctx.member.display_name}",
            icon=ctx.member.avatar_url or ctx.member.default_avatar_url,
        )
        .set_thumbnail(target.avatar_url or target.default_avatar_url)
    )

    for i in range(len(titles)):
        embed.add_field(
            f"[{i+1}] {titles[i]}",
            f"Requested by <@{requests[i]}>",
            inline=False
        )

    await ctx.respond(embed)


@plugin.command()
@lightbulb.add_checks(lightbulb.guild_only)
@lightbulb.add_checks(lightbulb.owner_only)  # Optional
@lightbulb.option(
    "args", "The arguments to write to the node data.", required=False, modifier=lightbulb.OptionModifier.CONSUME_REST
)
@lightbulb.command("data", "Load or read data from the node.")
@lightbulb.implements(lightbulb.SlashCommand)
async def data(ctx: lightbulb.Context) -> None:
    """Load or read data from the node.
    If just `data` is ran, it will show the current data, but if `data <key> <value>` is ran, it
    will insert that data to the node and display it."""

    node = await plugin.bot.d.lavalink.get_guild_node(ctx.guild_id)

    if not node:
        await ctx.respond("No node found.")
        return None

    if args := ctx.options.args:
        args = args.split(" ")

        if len(args) == 1:
            node.set_data({args[0]: args[0]})
        else:
            node.set_data({args[0]: args[1]})
    await ctx.respond(node.get_data())


@plugin.listener(hikari.VoiceStateUpdateEvent)
async def voice_state_update(event: hikari.VoiceStateUpdateEvent) -> None:
    plugin.bot.d.lavalink.raw_handle_event_voice_state_update(
        event.state.guild_id,
        event.state.user_id,
        event.state.session_id,
        event.state.channel_id,
    )


@plugin.listener(hikari.VoiceServerUpdateEvent)
async def voice_server_update(event: hikari.VoiceServerUpdateEvent) -> None:
    await plugin.bot.d.lavalink.raw_handle_event_voice_server_update(event.guild_id, event.endpoint, event.token)


def load(bot: lightbulb.BotApp) -> None:
    bot.add_plugin(plugin)
