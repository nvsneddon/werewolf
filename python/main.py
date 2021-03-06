import discord
from discord.ext import commands

import files
import bot
import models.channels
import models.server
import models.villager
import models.game


def get_prefix(bot, message):
    guild = message.guild
    server_document = models.server.Server.find_one({
        "server": guild.id
    })
    if server_document is None or guild is None:
        return "!"
    if "prefix" not in server_document:
        return "!"
    return server_document["prefix"]


beginning = True
client = commands.Bot(command_prefix=get_prefix)


@client.event
async def on_ready():
    game_cog = client.get_cog("Bot")
    global beginning
    if game_cog is None:
        client.add_cog(bot.Bot(client))
        game_cog = client.get_cog("Game")
    if beginning:
        games_document = models.game.Game.find({})
        for guild in client.guilds:
            x = models.server.Server.find_one({"server": guild.id})
            if x is None:
                x = models.server.Server({"server": guild.id})
                x.save()
        for game in games_document:
            game_cog.schedule_day_and_night(game["server"], reschedule=True)
        print("The werewolves are howling!")
        beginning = False


@client.event
async def on_guild_remove(guild):
    models.server.delete_many({"server": guild.id})


@client.event
async def on_guild_join(guild):
    x = models.server.Server.find_one({
        "server": guild.id
    })
    if x is None:
        x = models.server.Server({
            "server": guild.id
        })
        x.save()
    if not discord.utils.get(guild.channels, name="bot-admin"):
        permissions = files.readJsonFromConfig('permissions.json')
        bot_role = discord.utils.get(guild.me.roles, managed=True)
        overwrite = {
            bot_role: discord.PermissionOverwrite(**permissions["manage"]),
            guild.default_role: discord.PermissionOverwrite(**permissions['none'])
        }
        town_square_category = await guild.create_category_channel(name="Admin")
        await guild.create_text_channel(name="bot-admin", overwrites=overwrite, category=town_square_category)
    channel = discord.utils.get(guild.channels, name="bot-admin")
    message = f"Hi there! I've made this channel for you. :) On here, you can be the admin to the bot. I'll let you " \
              f"decide who will be allowed to access this channel.\nDaytime is set to begin at {x['daytime']} and " \
              f"nighttime is set to begin at {x['nighttime']}. I will remind you {x['warning']} minutes before " \
              f"nighttime approaches.\nYou can also configure these options in this bot-admin channel by using the " \
              f"commands !changeday, !changenight, and !changewarning.\n\nTo get started, please type !setupserver " \
              f"and I'll get everything done that is needed.\nPlease be aware that a small part of this requires " \
              f"either admin privileges granted to me or manually making the permissions overwrite I need to work in " \
              f"the town-square.\nIf you want a painless setup, please grant me admin permissions temporarily and " \
              f"type !setupserver.  Once that's finished, I don't need admin privileges anymore.\n" \
              f"If you don't want to grant me admin permissions, I'll walk you through on what to do once " \
              f"I've done everything I can.\n" \
              f"Have fun :) "
    await channel.send(message)


@client.event
async def on_member_remove(member):
    v = models.villager.Villager.find_one({
        "server": member.guild.id,
        "discord_id": member.id
    })
    if v is not None:
        announcements_channel = member.guild.get_channel(models.channels.getChannelId("announcements", member.guild.id))
        await announcements_channel.send(files.werewolfMessages[v["character"]]["leave"])
        game_cog = client.get_cog("Game")
        await game_cog.die_from_db(villager_id=member.id, guild_id=member.guild.id, leaving=True)
    v.delete()


@client.event
async def on_message(message):
    # if message.guild is None and (message.author != bot.user):
    #     if message.content.startswith("!respond"):
    #         delimiter = '#'
    #         response = message.content.split(delimiter)
    #         user_id = response[1]
    #         response_message = delimiter.join(response[2:])
    #         await message.author.send("The message has been sent!")
    #         await bot.get_guild().get_member(int(user_id)).send(
    #             f"Response : {response_message}")
    #     else:
    #         question = message.content + "\n" + str(message.author.id)
    #         await message.author.send("Thanks for submitting. Your question will be answered shortly.")
    #         await bot.get_guild().owner.send(question)
    # else:
    if message.content.startswith("!volt"):
        return
    await client.process_commands(message)


if __name__ == "__main__":
    client.run(files.config["token"])
