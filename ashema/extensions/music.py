import os
from typing import Optional
from googleapiclient.discovery import build
import random
import hikari
import lightbulb
import lavasnek_rs
import logging

plugin = lightbulb.Plugin("Music", "🎧 Music commands")

# If True connect to voice with the hikari gateway instead of lavasnek_rs's
HIKARI_VOICE = False

class EventHandler:
    """Events from the Lavalink server"""

    async def track_start(self, lavalink: lavasnek_rs.Lavalink, event: lavasnek_rs.TrackStart) -> None:
        logging.info("Track started on guild: %s", event.guild_id)
        
        node = await lavalink.get_guild_node(event.guild_id)
        # update bot's presence (should only work if bot is in one server)
        await plugin.bot.update_presence(
            activity = hikari.Activity(
            name = f"{node.now_playing.track.info.author} - {node.now_playing.track.info.title}",
            type = hikari.ActivityType.LISTENING
        ))

    async def track_finish(self, lavalink: lavasnek_rs.Lavalink, event: lavasnek_rs.TrackFinish) -> None:
        logging.info("Track finished on guild: %s", event.guild_id)

        node = await lavalink.get_guild_node(event.guild_id)
        # update bot's presence (should only work if bot is in one server)
        if not node.queue:
            await plugin.bot.update_presence(
                activity = hikari.Activity(
                name = f"/play",
                type = hikari.ActivityType.LISTENING
            ))

    async def track_exception(self, lavalink: lavasnek_rs.Lavalink, event: lavasnek_rs.TrackException) -> None:
        logging.warning("Track exception event happened on guild: %d", event.guild_id)

        # If a track was unable to be played, skip it
        skip = await lavalink.skip(event.guild_id)
        node = await lavalink.get_guild_node(event.guild_id)

        if not node:
            return

        if skip and not node.queue and not node.now_playing:
            await lavalink.stop(event.guild_id)

# on ready, connect to lavalink server
@plugin.listener(hikari.ShardReadyEvent)
async def start_lavalink(event: hikari.ShardReadyEvent) -> None:
    # local lavalink server
    builder = (
        lavasnek_rs.LavalinkBuilder(event.my_user.id, os.environ["TOKEN"])
        .set_host('localhost')
        .set_port(2333)
        .set_password('youshallnotpass')
    )

    if HIKARI_VOICE:
        builder.set_start_gateway(False)

    lava_client = await builder.build(EventHandler())
    plugin.bot.d.lavalink = lava_client
    plugin.bot.unsubscribe(hikari.ShardReadyEvent, start_lavalink)

    youtube = build('youtube', 'v3', static_discovery=False, developerKey=os.environ["YOUTUBE_API_KEY"])
    plugin.bot.d.youtube = youtube


async def _join(ctx: lightbulb.Context) -> Optional[hikari.Snowflake]:
    assert ctx.guild_id is not None

    states = plugin.bot.cache.get_voice_states_view_for_guild(ctx.guild_id)

    voice_state = [state[1] for state in filter(lambda i : i[0] == ctx.author.id, states.items())]
    bot_voice_state = [state[1] for state in filter(lambda i: i[0] == ctx.bot.get_me().id, states.items())]

    if not voice_state:
        await ctx.respond("Connect to a voice channel first.")
        return None

    channel_id = voice_state[0].channel_id

    if bot_voice_state:
        if channel_id != bot_voice_state[0].channel_id:
            await ctx.respond("I am already playing in another Voice Channel.")
            return None

    if HIKARI_VOICE:
        assert ctx.guild_id is not None

        await plugin.bot.update_voice_state(ctx.guild_id, channel_id, self_deaf=True)
        connection_info = await plugin.bot.d.lavalink.wait_for_full_connection_info_insert(ctx.guild_id)

    else:
        try:
            connection_info = await plugin.bot.d.lavalink.join(ctx.guild_id, channel_id)

        except TimeoutError:
            await ctx.respond("I was unable to connect to the voice channel, maybe missing permissions? or some internal issue.")
            return None

    await plugin.bot.d.lavalink.create_session(connection_info)

    return channel_id

async def _play(ctx: lightbulb.Context, query: str):
    assert ctx.guild_id is not None

    con = plugin.bot.d.lavalink.get_guild_gateway_connection_info(ctx.guild_id)
    # Join the user's voice channel if the bot is not in one.
    if not con:
        await _join(ctx)

    query_information = await plugin.bot.d.lavalink.auto_search_tracks(query)

    if not query_information.tracks:  # tracks is empty
        await ctx.respond("Could not find any video of the search query.")
        return
    try:
        # `.requester()` To set who requested the track, so you can show it on now-playing or queue.
        # `.queue()` To add the track to the queue rather than starting to play the track now.
        await plugin.bot.d.lavalink.play(ctx.guild_id, query_information.tracks[0]).requester(ctx.author.id).queue()
    except lavasnek_rs.NoSessionPresent:
        await ctx.respond(f"Use `/join` first")
        return

    await ctx.respond(
        embed = hikari.Embed(
            description = f"[{query_information.tracks[0].info.title}]({query_information.tracks[0].info.uri}) added to queue [{ctx.author.mention}]",
            colour = 0x76ffa1
        )
    )

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
@lightbulb.implements(lightbulb.PrefixCommand, lightbulb.SlashCommand)
async def leave(ctx: lightbulb.Context) -> None:
    """Leaves the voice channel the bot is in, clearing the queue."""

    await plugin.bot.d.lavalink.destroy(ctx.guild_id)

    if HIKARI_VOICE:
        if ctx.guild_id is not None:
            await plugin.bot.update_voice_state(ctx.guild_id, None)
            await plugin.bot.d.lavalink.wait_for_connection_info_remove(ctx.guild_id)
    else:
        await plugin.bot.d.lavalink.leave(ctx.guild_id)

    # Destroy nor leave remove the node nor the queue loop, you should do this manually.
    await plugin.bot.d.lavalink.remove_guild_node(ctx.guild_id)
    await plugin.bot.d.lavalink.remove_guild_from_loops(ctx.guild_id)

    await ctx.respond("Left voice channel")

@plugin.command()
@lightbulb.add_checks(lightbulb.guild_only)
@lightbulb.option("query", "The query to search for.", modifier=lightbulb.OptionModifier.CONSUME_REST, required=True)
@lightbulb.command("play", "Searches the query on youtube, or adds the URL to the queue.", auto_defer = True)
@lightbulb.implements(lightbulb.PrefixCommand, lightbulb.SlashCommand)
async def play(ctx: lightbulb.Context) -> None:
    """Searches the query on youtube, or adds the URL to the queue."""

    query = ctx.options.query
    await _play(ctx, query)

@plugin.command()
@lightbulb.add_checks(lightbulb.guild_only)
@lightbulb.command("stop", "Stops the current song and clears queue.")
@lightbulb.implements(lightbulb.PrefixCommand, lightbulb.SlashCommand)
async def stop(ctx: lightbulb.Context) -> None:
    """Stops the current song (skip to continue)."""

    await plugin.bot.d.lavalink.stop(ctx.guild_id)
    node = await plugin.bot.d.lavalink.get_guild_node(ctx.guild_id)
    node.queue = []
    await plugin.bot.d.lavalink.set_guild_node(ctx.guild_id, node)
    skip = await plugin.bot.d.lavalink.skip(ctx.guild_id)
    
    await ctx.respond(
        embed = hikari.Embed(
            description = ":stop_button: Stopped playing",
            colour = 0xd25557
        )
    )

@plugin.command()
@lightbulb.add_checks(lightbulb.guild_only)
@lightbulb.command("skip", "Skips the current song.")
@lightbulb.implements(lightbulb.PrefixCommand, lightbulb.SlashCommand)
async def skip(ctx: lightbulb.Context) -> None:
    """Skips the current song."""

    skip = await plugin.bot.d.lavalink.skip(ctx.guild_id)
    node = await plugin.bot.d.lavalink.get_guild_node(ctx.guild_id)

    if not skip:
        await ctx.respond(":caution: Nothing to skip")
    else:
        # If the queue is empty, the next track won't start playing (because there isn't any),
        # so we stop the player.
        if not node.queue and not node.now_playing:
            await plugin.bot.d.lavalink.stop(ctx.guild_id)

        await ctx.respond(
            
            embed = hikari.Embed(
                description =   f":fast_forward: Skipped: [{skip.track.info.title}]({skip.track.info.uri})",
                colour = 0xd25557
            )
        )

@plugin.command()
@lightbulb.add_checks(lightbulb.guild_only)
@lightbulb.command("pause", "Pauses the current song.")
@lightbulb.implements(lightbulb.PrefixCommand, lightbulb.SlashCommand)
async def pause(ctx: lightbulb.Context) -> None:
    """Pauses the current song."""

    await plugin.bot.d.lavalink.pause(ctx.guild_id)
    await ctx.respond(
        embed = hikari.Embed(
            description = ":pause_button: Paused player",
            colour = 0xf9c62b
        )
    )

@plugin.command()
@lightbulb.add_checks(lightbulb.guild_only)
@lightbulb.command("resume", "Resumes playing the current song.")
@lightbulb.implements(lightbulb.PrefixCommand, lightbulb.SlashCommand)
async def resume(ctx: lightbulb.Context) -> None:
    """Resumes playing the current song."""

    await plugin.bot.d.lavalink.resume(ctx.guild_id)
    await ctx.respond(
        embed = hikari.Embed(
            description = ":arrow_forward: Resumed player",
            colour = 0x76ffa1
        )
    )

@plugin.command()
@lightbulb.add_checks(lightbulb.guild_only)
@lightbulb.command("queue", "Shows the next 10 songs in the queue", aliases = ['q'])
@lightbulb.implements(lightbulb.PrefixCommand, lightbulb.SlashCommand)
async def queue(ctx : lightbulb.Context) -> None:
    node = await plugin.bot.d.lavalink.get_guild_node(ctx.guild_id)

    if not node or not node.queue:
        await ctx.respond("Nothing is playing at the moment.")
        return
    
    length = divmod(node.now_playing.track.info.length, 60000)
    queueDescription = f"Now playing: [{node.now_playing.track.info.title}]({node.now_playing.track.info.uri}) `{int(length[0])}:{round(length[1]/1000):02}` [<@!{node.now_playing.requester}>]"
    i = 1
    while i < len(node.queue) and i <= 10:
        if i == 1: 
            queueDescription += '\n\nUp next:'
        length = divmod(node.queue[i].track.info.length, 60000)
        queueDescription = queueDescription + f"\n[{i}. {node.queue[i].track.info.title}]({node.queue[i].track.info.uri}) `{int(length[0])}:{round(length[1]/1000):02}` [<@!{node.queue[i].requester}>]"
        i += 1

    queueEmbed = hikari.Embed(
        title = "Queue",
        description = queueDescription,
        colour = 0x76ffa1
    )

    await ctx.respond(embed = queueEmbed)


@plugin.command()
@lightbulb.add_checks(lightbulb.guild_only)
@lightbulb.command("chill", "Play random linhnhichill", auto_defer = True)
@lightbulb.implements(lightbulb.PrefixCommand, lightbulb.SlashCommand)
async def chill(ctx: lightbulb.Context) -> None:

    BASE_YT_URL = 'https://www.youtube.com/watch'
    query = ''

    rand_vid = -1
    next_page_token = None
    while True:
        res = plugin.bot.d.youtube.playlistItems().list(
            playlistId='PL-F2EKRbzrNS0mQqAW6tt75FTgf4j5gjS',  # linhnhichill's playlist ID
            part='snippet',
            pageToken = next_page_token,
            maxResults=50
        ).execute()

        if rand_vid == -1:
            rand_vid = random.randint(0, res['pageInfo']['totalResults'])
        if rand_vid < 50:
            vid_id = res['items'][rand_vid]['snippet']['resourceId']['videoId']  # id
            query = f"{BASE_YT_URL}?v={vid_id}" 
            break

        rand_vid -= 50
        next_page_token = res.get('nextPageToken')

    assert query is not None
    await _play(ctx, query)


@plugin.listener(hikari.VoiceStateUpdateEvent)
async def voice_state_update(event: hikari.VoiceStateUpdateEvent) -> None:

    prev_state = event.old_state
    cur_state = event.state

    if HIKARI_VOICE:
        plugin.bot.d.lavalink.raw_handle_event_voice_state_update(
            cur_state.guild_id,
            cur_state.user_id,
            cur_state.session_id,
            cur_state.channel_id,
        )

    # if only one users using bot, bot pauses when user deafens and 
    # resumes when user undeafen

    if cur_state.user_id == plugin.bot.get_me().id:  # bot 
        return

    states = plugin.bot.cache.get_voice_states_view_for_guild(cur_state.guild_id).items()
    bot_voice_state = [state[1] for state in filter(lambda i: i[0] == plugin.bot.get_me().id, states)]

    # bot not in voice channel or user not in the same channel as bot
    if not bot_voice_state or cur_state.channel_id != bot_voice_state[0].channel_id:
        return
    
    # count users in channel with bot
    cnt_user = len([state[0] for state in filter(lambda i: i[1].channel_id == bot_voice_state[0].channel_id, states)])
    if cnt_user != 2:  # if not just bot & user
        return
    
    if prev_state.is_self_deafened and not cur_state.is_self_deafened:
        await plugin.bot.d.lavalink.resume(cur_state.guild_id)
        logging.info("Track resumed on guild: %s", event.guild_id)
    if not prev_state.is_self_deafened and cur_state.is_self_deafened:
        await plugin.bot.d.lavalink.pause(cur_state.guild_id)
        logging.info("Track paused on guild: %s", event.guild_id)

if HIKARI_VOICE:
    @plugin.listener(hikari.VoiceServerUpdateEvent)
    async def voice_server_update(event: hikari.VoiceServerUpdateEvent) -> None:
        await plugin.bot.d.lavalink.raw_handle_event_voice_server_update(event.guild_id, event.endpoint, event.token)


def load(bot: lightbulb.BotApp) -> None:
    bot.add_plugin(plugin)
