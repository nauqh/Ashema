# Ashema The Listener - Music Discord Bot                          

![Version](https://img.shields.io/badge/Latest%20Version-V3.1.0-blue?style=for-the-badge)

![Python](https://img.shields.io/badge/Made%20With-Python%203.8-blue.svg?style=for-the-badge&logo=Python)
![Discord](https://img.shields.io/discord/574921006817476608.svg?label=Discord&logo=Discord&colorB=7289da&style=for-the-badge)
![Reailway](https://img.shields.io/badge/deploy_to-Railway-a0c4ff.svg?style=for-the-badge&logo=Railway)

**Update** (21 December 2022): Deploy Lavalink server on `Replit`
## What is Ashema?

<img src="ashema.gif" alt="drawing"  height="250"/>

Custom music bot for housekeeping. The bot is for personal study about the new python library [**Hikari**](https://www.hikari-py.dev/) for developing Discord bots and practice working with Lavalink APIs as well as maintaining and hosting the application.

## Features

* **Daily notification:**
  * Schedule task in human time
  * Daily updates using Spotify API
  * `Slash comands` and *command aliases*
  * Minimum length for members to be in the guild before allowed to contact Tiamut (`guild_age`)

* **Moderation functionality:**
  * When you close a thread, Tiamut will generate a [log link](https://logs.modmail.dev/example) and post it to your log channel.
  * Editing and deleting messages are synced
  * Modmailing with support for the diverse range of message contents (multiple images, files)

* **Database:**
  * Maintain system database using `SQLite3` library
  * See past logs of a user with `logs`
  * Paginated commands interfaces via reactions
  * Searchable by text queries using `logs search`


## Hosting

Unfortunately, due to how this bot functions, it cannot be invited. The lack of an invite link is to ensure an individuality to your server and grant you full control over your bot and data. Nonetheless, you can quickly obtain a free copy of Tiamut for your server by following one of the methods listed below (roughly takes 15 minutes of your time).

### Heroku

You can host this bot on Heroku.

To configure automatic updates:
 - Login to [GitHub](https://github.com/) and verify your account.
 - [Fork the repo](https://github.com/kyb3r/modmail/fork).
 - Install the [Pull app](https://github.com/apps/pull) for your fork. 
 - Then go to the Deploy tab in your [Heroku account](https://dashboard.heroku.com/apps) of your bot app, select GitHub and connect your fork (usually by typing "Tiamut") 
 - Turn on auto-deploy for the `master` branch.


### Installation

Local hosting of Tiamut is also possible

Install dependencies:

```sh
$ pip install -r requirements.txt
```

Clone the repo:

```sh
$ git clone https://github.com/nauqh/music-bot
$ cd tiamut
```

Create a `.env` file to store the application authentication token and guild ids.

Finally, start the bot

```sh
$ python -m tiamut
```

## Documentation

Since Tiamut is built on the basis of `Hikari` library, it is essential to look for the library documentation for further implementation. 

- `Hikari`: https://www.hikari-py.dev/
- `Lightbulb`: https://hikari-lightbulb.readthedocs.io/en/latest/
- `Lavasnek_rs`: https://docs.vicky.rs/lavasnek_rs.html

## Contributors

**Nauqh** - [Github](https://github.com/nauqh) - `hodominhquan@gmail.com`

**Peter** - [Github](https://github.com/xuanbachtran02) - `xuanbachtran02@gmail.com`