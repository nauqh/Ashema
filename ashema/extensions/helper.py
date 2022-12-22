import os
import lightbulb
import random
from googleapiclient.discovery import build
import lavasnek_rs

from ashema.extensions.music import _join

youtube = build('youtube', 'v3', developerKey=os.environ["YOUTUBE_API_KEY"])
plugin = lightbulb.Plugin("Helper", "Other commands")

@plugin.command()
@lightbulb.add_checks(lightbulb.guild_only)
@lightbulb.command("chill", "Add random linh-nhi-chill to queue")
@lightbulb.implements(lightbulb.SlashCommand)
async def chill(ctx: lightbulb.Context) -> None:
    con = plugin.bot.d.lavalink.get_guild_gateway_connection_info(ctx.guild_id)
    if not con:
        await _join(ctx)

    next_page_token = None 
    for i in range(random.randint(1, 7)):  # 336 vid ~ 6 pages of 50 search results
        res = youtube.playlistItems().list(
            playlistId='PL-F2EKRbzrNS0mQqAW6tt75FTgf4j5gjS',
            part='snippet',
            pageToken = next_page_token,
            maxResults=50).execute()
        next_page_token = res.get('nextPageToken')

    vid_id = res['items'][random.randint(0, 50)]['snippet']['resourceId']['videoId']
    url = f'https://www.youtube.com/watch?v={vid_id}'

    query_information = await plugin.bot.d.lavalink.auto_search_tracks(url)

    if not query_information.tracks:
        await ctx.respond("Could not find any video of the search query.")
        return
    try:
        await plugin.bot.d.lavalink.play(ctx.guild_id, query_information.tracks[0]).requester(ctx.author.id).queue()
    except lavasnek_rs.NoSessionPresent:
        await ctx.respond("Use `/join` first")
        return
    await ctx.respond(f"Added to queue: {query_information.tracks[0].info.title}")

def load(bot: lightbulb.BotApp) -> None:
    bot.add_plugin(plugin)