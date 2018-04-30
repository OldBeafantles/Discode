"""Admin module"""
import os
import math
from datetime import datetime
import copy
import discord
from discord.ext import commands
from modules.utils import checks
from modules.utils import utils


class Admin:
    """Admin module"""

    def __init__(self, bot):
        """Init function"""
        self.bot = bot

    @commands.command()
    @checks.is_owner()
    async def add_blacklist(self, user: discord.Member):
        """Adds an user to the bot's blacklist
        Parameters:
            user: The user you want to add to the bot's blacklist.

        Example: [p]add_blacklist @AVeryMeanUser"""
        if user.id not in self.bot.blacklist:
            self.bot.blacklist.append(user.id)
            utils.save_json(self.bot.blacklist, self.bot.blacklist_file_path)
            await self.bot.say("Done.")
        else:
            await self.bot.say(user.name + "#" + user.discriminator + " (" +
                               user.id + ") is already blacklisted.")

    @commands.command()
    @checks.is_owner()
    async def add_blacklist_id(self, user_id: str):
        """Adds an user to the bot's blacklist using his ID
        Parameters:
            user_id: The ID of the user you want to add to the bot's blacklist.

        Example: [p]add_blacklist_id 346654353341546499"""
        if user_id not in self.bot.blacklist:
            self.bot.blacklist.append(user_id)
            utils.save_json(self.bot.blacklist, self.bot.blacklist_file_path)
            await self.bot.say("Done.")
        else:
            await self.bot.say("This ID is already in the blacklist.")

    @commands.command()
    @checks.is_owner()
    async def rem_blacklist(self, user: discord.Member):
        """Removes an user from the bot's blacklist
        Parameters:
            user: The user you want to remove from the bot's blacklist.

        Example: [p]rem_blacklist @AGoodGuyUnfairlyBlacklisted"""
        if user.id in self.bot.blacklist:
            self.bot.blacklist.remove(user.id)
            utils.save_json(self.bot.blacklist, self.bot.blacklist_file_path)
            await self.bot.say("Done.")
        else:
            await self.bot.say("This user wasn't even blacklisted.")

    @commands.command()
    @checks.is_owner()
    async def rem_blacklist_id(self, user_id: str):
        """Removes an user from the bot's blacklist using his ID
        Parameters:
            user_id: The ID of the user you want to to remove from the bot's blacklist.

        Example: [p]rem_blacklist @AGoodGuyUnfairlyBlacklisted"""
        if user_id in self.bot.blacklist:
            self.bot.blacklist.remove(user_id)
            utils.save_json(self.bot.blacklist, self.bot.blacklist_file_path)
            await self.bot.say("Done.")
        else:
            await self.bot.say("This ID wasn't even in the blacklist.")

    @commands.command()
    @checks.is_owner()
    async def list_blacklist(self):
        """Lists all the blacklisted users"""
        if self.bot.blacklist:
            msg = "```Markdown\nList of blacklisted users:\n=================\n\n"
            i = 1
            has_unknown = False
            for user_id in self.bot.blacklist:
                user = discord.utils.find(
                    lambda u, u_id=user_id: u.id == u_id,
                    self.bot.get_all_members())
                msg += str(i) + ". "
                if user:
                    msg += user.name + "#" + \
                        user.discriminator + " (" + user.id + ")\n"
                else:
                    has_unknown = True
                    msg += "UNKNOWN USER\n"
                i += 1
            msg += "```"
            if has_unknown:
                msg += "\n`UNKNOWN USER` means that this user hasn't any server in " + \
                    "common with the bot."
            await self.bot.say(msg)
        else:
            await self.bot.say("There is no blacklisted users.")


def setup(bot):
    """Setup function"""
    bot.add_cog(Admin(bot))
