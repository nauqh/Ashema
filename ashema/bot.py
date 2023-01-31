import os
import hikari
import lightbulb

bot = lightbulb.BotApp(
    os.environ["TOKEN"],
    intents=hikari.Intents.ALL,
    default_enabled_guilds=int(os.environ["GUILD_ID"]),
    help_slash_command=True,
    banner=None,
)

# Extension
bot.load_extensions_from("./ashema/extensions", must_exist=True)

def run() -> None:
    bot.run(
        activity = hikari.Activity(
            name = f"/play",
            type = hikari.ActivityType.LISTENING
    ))
