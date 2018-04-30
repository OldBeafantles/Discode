"""The bot"""

import asyncio
import aiohttp
from datetime import datetime, timedelta
import discord
from discord.ext import commands
import importlib
import logging
from modules.utils import utils
import os
import sys

# Useful functions
if sys.platform == "win32" or sys.platform == "win64":

    def clear():
        return os.system("cls")
else:

    def clear():
        return os.system("clear")


def _prefix_callable(bot, msg):
    return ["<@!" + bot.user.id + "> ", "<@" + bot.user.id + "> ", bot.prefix]


class CppBot(commands.Bot):
    """The bot class"""

    def load_config(self):
        """Loads self.config_file_path, gets the infos if the file doesn't exists"""
        if not os.path.exists(self.config_file_path):

            json_data = {}
            token = input("Please put your bot's token here:\n> ")
            print("DO NOT SPREAD YOUR bot'S TOKEN TO ANYONE. NEVER.\n")
            prefix = input("\n\nPlease put your bot's prefix here:\n> ")
            description = input(
                "\n\nPlease put a little description for your bot (optionnal)\n> "
            )
            if description == "":
                description = "A bot that runs code.\nIf you have any problem with Discode or if you just want to be in the development server, you can join it using this link: discord.gg/UpYc98d"
            owner_id = input("\n\nPlease put your ID:\n> ")

            json_data["token"] = token
            json_data["prefix"] = prefix
            json_data["description"] = description
            json_data["owner id"] = owner_id
            self.token = token
            self.prefix = prefix
            self.description = description
            self.owner_id = owner_id

            if not os.path.isdir("settings"):
                os.makedirs("settings")

            utils.save_json(json_data, self.config_file_path)

        else:
            json_data = utils.load_json(self.config_file_path)
            if not "token" in json_data or not "prefix" in json_data \
                    or not "description" in json_data or not "owner id" in json_data:
                print(
                    "\"settings/config.json\" is incorrect! The bot will be reseted, "
                    + "please restart the bot!")
                os.remove(self.config_file_path)
                sys.exit(1)
            else:
                self.token = json_data["token"]
                self.prefix = json_data["prefix"]
                self.description = json_data["description"]
                self.owner_id = json_data["owner id"]

    def reset_infos(self):
        """Resets bot's info"""
        json_data = {}
        json_data["created at"] = datetime.now().strftime("%d/%m/%Y %H:%M:%S")
        json_data["total commands"] = 0
        json_data["total runtime"] = 0
        self.created_at = datetime.now()
        self.total_commands = 0
        self.total_runtime = timedelta(seconds=0)

        # Shouldn't be call, except if the user deletes this folder
        if not os.path.isdir("settings"):
            os.makedirs("settings")

        utils.save_json(json_data, self.info_file_path)

    def load_infos(self):
        """Load bot's info"""
        if not os.path.exists(self.info_file_path):
            self.reset_infos()
        else:
            json_data = utils.load_json(self.info_file_path)
            if not "created at" in json_data or not "total commands" in json_data \
                    or not "total runtime" in json_data:
                print("\"settings/infos.json\" is incorrect! The info of " +
                      "the bot will be reseted!")
                self.reset_infos()
            else:
                self.created_at = datetime.strptime(json_data["created at"],
                                                    "%d/%m/%Y %H:%M:%S")
                self.total_commands = json_data["total commands"]
                self.total_runtime = timedelta(
                    seconds=json_data["total runtime"])

    def load_blacklist(self):
        """Loads the blacklist"""
        if not os.path.exists(self.blacklist_file_path):
            if not os.path.isdir("settings"):
                os.makedirs("settings")

            utils.save_json(self.blacklist, self.blacklist_file_path)
        else:
            self.blacklist = utils.load_json(self.blacklist_file_path)

    def load_modules(self):
        """Loads the bot modules"""
        if not os.path.exists(self.modules_file_path):
            json_data = self.default_modules
            self.modules = self.default_modules
            utils.save_json(json_data, self.modules_file_path)

        print("\n\n")
        self.modules = set(utils.load_json(self.modules_file_path))
        to_remove = []
        for mod in self.modules:
            module_path = "modules/" + mod + ".py"
            module_name = module_path.replace('/', '.')[:-3]
            if not os.path.exists(module_path):
                print("\n\nThe module \"" + mod + "\" doesn't exist!")
                to_remove.append(mod)
            else:
                try:
                    print("Loading " + mod + " module...")
                    module = importlib.import_module(
                        module_path.replace('/', '.')[:-3])
                    importlib.reload(module)
                    super().load_extension(module_name)
                    self.loaded_modules.append(mod)
                except SyntaxError as ex:
                    print("Error in " + mod + " module:\n\n" + str(ex) + "\n\n")
                    to_remove.append(mod)
        for mod in to_remove:
            self.modules.remove(mod)
        utils.save_json(list(self.modules), self.modules_file_path)

    def init_data(self):
        if not os.path.isdir("data"):
            os.makedirs("data")

    async def send_cmd_help(self, ctx, message: str):
        if ctx.invoked_subcommand:
            pages = self.formatter.format_help_for(ctx, ctx.invoked_subcommand)
            for page in pages:
                await self.send_message(ctx.message.channel,
                                        message + "\n" + page)
        else:
            pages = self.formatter.format_help_for(ctx, ctx.command)
            for page in pages:
                await self.send_message(ctx.message.channel,
                                        message + "\n" + page)

    def __init__(self, loop):

        clear()
        self.token = ""
        self.prefix = ""
        self.description = ""
        self.owner_id = ""
        self.config_file_path = "settings/config.json"
        self.load_config()
        self.created_at = None
        self.total_commands = 0
        self.total_runtime = None
        self.info_file_path = "settings/infos.json"
        self.load_infos()
        self.bot = discord.Client()
        self.default_modules = ["base", "admin", "code"]
        self.loaded_modules = []
        self.modules_file_path = "settings/modules.json"
        self.blacklist_file_path = "settings/blacklist.json"
        self.blacklist = []
        self.load_blacklist()
        self.init_data()
        self.invite_link = ""
        self.modules = []
        self.version = "1.0.2"
        self.logger = logging.getLogger('discord')
        self.logger.setLevel(logging.DEBUG)
        self.handler = logging.FileHandler(
            filename="discord.log", encoding='utf-8', mode='w')
        self.handler.setFormatter(
            logging.Formatter(
                "%(asctime)s:%(levelname)s:%(name)s: %(message)s"))
        self.logger.addHandler(self.handler)
        self.launched_at = datetime.now()
        super().__init__(
            command_prefix=_prefix_callable,
            description=self.description,
            loop=loop)
        self.session = aiohttp.ClientSession(loop=loop)
        self.dev_server_invitation_link = "discord.gg/UpYc98d"
        clear()

    async def close(self):
        await super().close()
        await self.session.close()


def run_bot():
    """Runs the bot"""

    loop = asyncio.get_event_loop()

    bot = CppBot(loop)

    @bot.event
    async def on_ready():
        """Triggers when the bot just logged in"""

        bot.owner = discord.utils.find(lambda m: m.id == bot.owner_id,
                                       bot.get_all_members())
        print("Logged in as " + bot.user.name + "#" + bot.user.discriminator)
        print(str(len(bot.servers)) + " servers")
        print(str(len(set(bot.get_all_channels()))) + " channels")
        print(str(len(set(bot.get_all_members()))) + " members")
        bot.invite_link = "https://discordapp.com/oauth2/authorize?client_id=" \
            + bot.user.id + "&scope=bot"
        print("\nHere's the invitation link for your bot: " + bot.invite_link)
        bot.load_modules()
        bot.launched_at = datetime.now()
        print("\n" + str(len(bot.loaded_modules)) + " modules loaded.")

    @bot.event
    async def on_command(command, ctx):
        """Triggers AFTER a command is called"""
        bot.total_commands += 1

    @bot.event
    async def on_message(message):
        """Triggers when the bot reads a new message"""
        if message.author.id not in bot.blacklist:
            await bot.process_commands(message)

    @bot.event
    async def on_command_error(error, ctx):
        if isinstance(error, commands.MissingRequiredArgument):
            await bot.send_cmd_help(ctx, "Missing required argument")
        elif isinstance(error, commands.BadArgument):
            await bot.send_cmd_help(ctx, "Bad argument")
        elif isinstance(error, commands.CommandNotFound):
            pass
        elif isinstance(error, commands.CheckFailure):
            pass
        else:
            bot.logger.exception(type(error).__name__, exc_info=error)

    try:
        bot.run(bot.token, reconnect=True)
    except discord.LoginFailure:
        print(
            "Couldn't log in, your bot's token might be incorrect! If it's not, "
            + "then check Discord's status here: https://status.discordapp.com/"
        )
        answer = input("Do you want to change your bot's token? (yes/no)\n> ")
        if answer.upper() == "YES":
            token = input("\n\nPlease put your new bot's token here:\n> ")
            json_data = utils.load_json("settings/infos.json")
            json_data["token"] = token
            bot.token = token
            utils.save_json(json_data, "settings/infos.json")
    except KeyboardInterrupt:
        loop.run_util_complete(bot.close())
    except discord.GatewayNotFound:
        print("Gateway not found! The problem comes from Discord.")
        sys.exit(1)
    except discord.ConnectionClosed:
        print("No more connection.")
        loop.run_util_complete(bot.close())
        sys.exit(1)
    except discord.HTTPException:
        print("HTTP Error.")
        loop.run_util_complete(bot.close())
        sys.exit(1)
    except Exception as e:
        print(e)
        loop.run_util_complete(bot.close())
        sys.exit(1)
    finally:
        loop.close()
