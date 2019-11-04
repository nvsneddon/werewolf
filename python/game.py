import datetime
import random
import threading
import time
from typing import Optional, List, Tuple

import discord
import schedule
from discord.ext import commands

from files import getChannelId, werewolfMessages, config
from villager import Villager


def is_from_channel(channel_name: str):
    async def predicate(ctx):
        channel1 = ctx.guild.get_channel(getChannelId(channel_name))
        channel2 = ctx.channel
        channel_check = channel1 == channel2
        return channel_check

    return commands.check(predicate)


class Game(commands.Cog):

    __resettedCharacters: Tuple[str, str, str]
    __inlove: List[Villager]
    __players: List[Villager]

    # players is a list of all of the name of people playing
    # roles is a list of numbers of all of the characters that will be playing
    # raises ValueError Exception when too many roles are handed out

    def timer(self):
        while not self.schedstop.is_set():
            schedule.run_pending()
            time.sleep(3)

    def __init__(self, bot, players, roles, randomshuffle=True):
        self.__bot = bot
        self.__players = []
        self.__inlove = []
        self.__bakerdead: bool = False
        # self.__protected = None
        self.__daysleft = 3
        self.__hunter = False  # Variable to turn on the hunter's power
        self.__resettedCharacters = ("bodyguard", "seer", "werewolf")
        self.__running = True

        self.schedstop = threading.Event()
        self.schedthread = threading.Thread(target=self.timer)
        self.schedthread.start()



        schedule.every().day.at(config["daytime"]).do(self.daytime).tag("game")
        schedule.every().day.at(config["vote-warning"]).do(self.almostnighttime).tag("game")
        schedule.every().day.at(config["nighttime"]).do(self.nighttime).tag("game")

        check_time = datetime.datetime.now().time()
        if datetime.time(7, 0) <= check_time <= datetime.time(21, 0):
            self.__killed = False
        else:
            # Night time
            self.__killed = True

        cards = []
        if len(roles) >= 6:
            cards += roles[5] * ["baker"]
        if len(roles) >= 5:
            cards += roles[4] * ["hunter"]
        if len(roles) >= 4:
            cards += roles[3] * ["cupid"]
        if len(roles) >= 3:
            cards += roles[2] * ["bodyguard"]
        if len(roles) >= 2:
            cards += roles[1] * ["seer"]
        if len(roles) >= 1:
            cards += roles[0] * ["werewolf"]

        if len(players) > len(cards):
            cards += (len(players) - len(cards)) * ["villager"]
        if randomshuffle:
            random.shuffle(cards)

        for x in players:
            y = Villager(str(x), cards[0], x.id)
            self.__players.append(y)
            cards.pop(0)

        for i in self.__players:
            print(i)

    @commands.command()
    @is_from_channel("werewolves")
    async def kill(self, ctx, person_name:str):
        target = self.findVillager(person_name)
        if target is None:
            await ctx.send("That person could not be found. Please try again.")
            return
        if target.protected:
            await ctx.send("That person has been protected. You just wasted your kill!")
        else:
            await ctx.send("Killing {}".format(target.Name))
            target.die()
            dead_role = discord.utils.get(ctx.guild.roles, name="Dead")
            target_user = ctx.message.guild.get_member_named(target.DiscordTag)
            await target_user.edit(roles=[dead_role])
            town_square_id = getChannelId("town-square")
            town_square_channel = ctx.guild.get_channel(town_square_id)
            await town_square_channel.send(werewolfMessages[target.Character]["killed"].format(target.Name))\

    @commands.command(aliases=["see", "look", "suspect"])
    @is_from_channel("seer")
    async def investigate(self, ctx, person_name: str):
        target = self.findVillager(person_name)
        seer: Villager = self.findVillager(ctx.message.author.name)
        if seer is None:
            message = "Seer is None. This should never happen"
            print(message)
            ctx.send(message)
            return
        if target is None:
            await ctx.send("That person could not be found. Please try again.")
            return
        if self.useAbility(seer):
            await ctx.send("{} is {} a werewolf".format(person_name, "" if target.IsWerewolf else "not"))
        else:
            await ctx.send("You already used your ability tonight.")

    def useAbility(self, v: Villager) -> bool:
        if v.UsedAbility:
            return False
        v.UsedAbility = True
        return True

    def cog_unload(self):
        schedule.clear("game")
        # self.__bot.remove_cog("Election")
        return super().cog_unload()

    def daytime(self):
        if self.__bakerdead:
            self.__daysleft -= 1
        self.__killed = True
        for x in self.__players:
            if x.Character in self.__resettedCharacters:
                x.UsedAbility = False
            x.protected = False

    def nighttime(self):
        self.__killed = False

    def almostnighttime(self):
        pass

    def getVillagerByID(self, player_id: int) -> Optional[Villager]:
        for x in self.__players:
            if player_id == x.UserID:
                return x
        return None

    # returns person that was killed
    #TODO Do we need to have this really?
    def killmaybe(self, killer, target) -> None:
        killerVillager = self.findVillager(killer)
        if killerVillager.iskiller():
            self.findVillager(target).die()

    def findVillager(self, name: str) -> Optional[Villager]:
        if name[0:3] == "<@!":  # in case the user that is passed in has been mentioned with @
            name = name[3:-1]
        elif name[0:2] == "<@":
            name = name[2:-1]
        for x in self.__players:
            if x.Name.lower() == name.lower() or x.DiscordTag.lower() == name.lower():
                return x
        return None
