import discord
from discord.ext import commands
from schemer import ValidationException

import decorators
from decorators import is_admin, findPerson
from game import Game
import asyncio
import models.channels
import models.game
import models.election
import models.server
import models.villager
import files
import abilities


def can_clear():
    async def predicate(ctx):
        bot_admin_channel = discord.utils.get(ctx.guild.channels, name="bot-admin")
        return ctx.author in bot_admin_channel.overwrites or ctx.author == ctx.guild.owner

    return commands.check(predicate)


def has_role(r):
    async def predicate(ctx):
        return r in ctx.author.roles

    return commands.check(predicate)


class Bot(commands.Cog):

    def __init__(self, bot):
        self.__bot = bot
        self.__bot.add_cog(Game(self.__bot))
        # self.__game = False

    @commands.Cog.listener()
    async def on_command_error(self, ctx, error):
        if not isinstance(error, commands.CheckFailure):
            await ctx.send(str(error))
        print(error)

    @commands.command(**files.command_parameters['echo'])
    async def echo(self, ctx, *args):
        if len(args) > 0:
            output = ''
            for x in args:
                output += x
                output += ' '
            print(output)
            await ctx.send(output)

    @commands.command(**files.command_parameters['tickle'])
    async def tickle(self, ctx):
        await ctx.send(":rofl:  Stop it!  :rofl: :rofl:")

    @commands.command()
    @can_clear()
    async def clear(self, ctx, number=10):
        # Converting the amount of messages to delete to an integer
        number = int(number + 1)
        counter = 0
        delete_channel = ctx.message.channel
        async for x in (delete_channel.history(limit=number)):
            if counter < number:
                if x.pinned:
                    continue
                await x.delete()
                counter += 1
                await asyncio.sleep(0.4)

    @commands.command(**files.command_parameters["ping"])
    async def ping(self, ctx):
        await ctx.send(":ping_pong: Pong!")

    @commands.command(**files.command_parameters['playing'])
    @decorators.is_no_game()
    async def playing(self, ctx):
        playing_role = discord.utils.get(ctx.guild.roles, name="Playing")
        await ctx.author.edit(roles={playing_role})
        await ctx.send(f"{ctx.author.mention} is now playing.")

    @commands.command(**files.command_parameters['notplaying'])
    @decorators.is_no_game()
    async def notplaying(self, ctx):
        await ctx.author.edit(roles=[])
        await ctx.send(f"{ctx.author.mention} is not playing.")

    @commands.command()
    @is_admin()
    async def addroles(self, ctx):
        for i, j in files.roles_config["roles"].items():
            if discord.utils.get(ctx.guild.roles, name=i) is not None:
                continue
            permission_object = discord.Permissions().none()
            permission_object.update(**files.roles_config["general-permissions"])
            if j["permissions-update"] is not None:
                permission_object.update(**j["permissions-update"])
            c = discord.Color.from_rgb(*j["color"])
            await ctx.guild.create_role(name=i, permissions=permission_object, color=c)
            message = i + " role created"
            await ctx.send(message)

    @commands.command()
    @is_admin()
    async def resetrolepermissions(self, ctx):
        for i, j in files.roles_config["roles"].items():
            role = discord.utils.get(ctx.guild.roles, name=i)
            if role is None:
                continue
            permissionObject = discord.Permissions().none()
            permissionObject.update(**files.roles_config["general-permissions"])
            if j["permissions-update"] is not None:
                permissionObject.update(**j["permissions-update"])
            await role.edit(permissions=permissionObject)
            message = i + " role permissions reset"
            await ctx.send(message)

    @commands.command()
    @is_admin()
    async def addcategory(self, ctx):
        x = models.channels.Channels.find_one({"server": ctx.guild.id})
        if x is not None:
            await ctx.send("You already have the channels set up.")
            return
        town_square_category = await ctx.guild.create_category_channel(files.channels_config["category-name"])
        for i, j in files.channels_config["category-permissions"].items():
            target = discord.utils.get(ctx.guild.roles, name=i)
            await town_square_category.set_permissions(target, overwrite=discord.PermissionOverwrite(**j))
        bot_role = discord.utils.get(ctx.guild.me.roles, managed=True)
        permissions = files.readJsonFromConfig("permissions.json")
        await town_square_category.set_permissions(bot_role,
                                                   overwrite=discord.PermissionOverwrite(**permissions["manage"]))
        channel_id_dict = dict()
        channel_id_dict["guild"] = ctx.guild.id
        for i in files.channels_config["channels"]:
            await ctx.guild.create_text_channel(name=i, category=town_square_category)
            channel = discord.utils.get(ctx.guild.channels, name=i)
            await channel.send('\n'.join(files.werewolfMessages["channel_messages"][i]))
            channel_id_dict[i] = channel.id
            async for x in (channel.history(limit=1)):
                await x.pin()

        channels = models.channels.Channels.find_one({"server": ctx.guild.id})
        if channels is None:
            channels = models.channels.Channels({
                "server": ctx.guild.id,
                "channels": channel_id_dict
            })
            channels.save()
        else:
            channels.update_instance({"channels": channel_id_dict})

        for i, j in files.channels_config["channel-permissions"].items():
            ch = discord.utils.get(town_square_category.channels, name=i)
            if ch is None:
                print("The name is", i)
            for k, l in j.items():
                target = discord.utils.get(ctx.guild.roles, name=k)
                await ch.set_permissions(target, overwrite=discord.PermissionOverwrite(**l))

    def cog_unload(self):
        return super().cog_unload()

    @commands.command()
    @is_admin()
    @decorators.is_no_game()
    async def removecategory(self, ctx):
        c = discord.utils.get(ctx.guild.categories,
                              name=files.channels_config["category-name"])
        for i in c.channels:
            await i.delete()
        await c.delete()

        channel = models.channels.Channels.find_one({"server": ctx.guild.id})
        channel.remove()

    @commands.command()
    @is_admin()
    @decorators.is_no_game()
    async def changeday(self, ctx, time):
        if models.server.set_day(ctx.guild.id, time):
            await ctx.send(f"Time set to {time}")
        else:
            await ctx.send("Bad time format. Please try using the hh:mm 24h format.")

    @commands.command()
    @is_admin()
    @decorators.is_no_game()
    async def changenight(self, ctx, time):
        if models.server.set_night(ctx.guild.id, time):
            await ctx.send(f"Time set to {time}")
        else:
            await ctx.send("Bad time format. Please try using the hh:mm 24h format")

    @commands.command()
    @is_admin()
    @decorators.is_no_game()
    async def changewarning(self, ctx, minutes):
        if models.server.set_warning(ctx.guild.id, minutes):
            await ctx.send(f"Warning set to {minutes} before nighttime")
        else:
            await ctx.send("Please make sure the number isn't bigger than 180.")

    @commands.command()
    async def gettime(self, ctx):
        server_document = models.server.Server.find_one({ "server": ctx.guild.id })
        await ctx.send(f"Day time is at {server_document['daytime']}")
        await ctx.send(f"Night time is at {server_document['nighttime']}")
        await ctx.send(f"Warning happens {server_document['warning']} minutes before nighttime")