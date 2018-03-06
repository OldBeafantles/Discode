"""Owner module"""

import discord
import sys
import os
import traceback
from discord.ext import commands
from modules.utils import checks
from modules.utils import utils
import textwrap
import inspect
import asyncio
import io
from contextlib import redirect_stdout
import requests
from os import listdir
import subprocess
from datetime import datetime, timedelta
import platform


class Base:
    """Basic commands"""

    def __init__(self, bot):
        self.bot = bot
        self.last_result = None
        self.sessions = set()
        self.infos_updater = self.bot.loop.create_task(self.update_infos())

    def __unload(self):
        self.infos_updater.cancel()

    def cleanup_code(self, content):
        """Automatically removes code blocks from the code."""
        # remove ```py\n```
        if content.startswith('```') and content.endswith('```'):
            return '\n'.join(content.split('\n')[1:-1])

        # remove `foo`
        return content.strip('` \n')

    def get_syntax_error(self, e):
        if e.text is None:
            return f'```py\n{e.__class__.__name__}: {e}\n```'
        return f'```py\n{e.text}{"^":>{e.offset}}\n{e.__class__.__name__}: {e}```'

    def save_infos(self):
        json_data = {}
        delta = datetime.now() - self.bot.launched_at
        json_data["total runtime"] = int(
            (self.bot.total_runtime + delta).total_seconds())
        json_data["total commands"] = self.bot.total_commands
        json_data["created at"] = self.bot.created_at.strftime(
            "%d/%m/%Y %H:%M:%S")
        utils.save_json(json_data, self.bot.info_file_path)

    async def update_infos(self):
        while not self.bot.is_closed:
            self.save_infos()
            await asyncio.sleep(60)

    @commands.command(pass_context=True, name='eval')
    @checks.is_owner()
    async def eval(self, ctx, *, body: str):
        """Evaluates a code"""

        env = {
            'bot': self.bot,
            'ctx': ctx,
            'channel': ctx.message.channel,
            'author': ctx.message.author,
            'server': ctx.message.server,
            'message': ctx.message,
            '_': self.last_result
        }

        env.update(globals())

        body = self.cleanup_code(body)
        stdout = io.StringIO()

        to_compile = f'async def func():\n{textwrap.indent(body, "  ")}'

        try:
            exec(to_compile, env)
        except Exception as e:
            return await self.bot.say(f'```py\n{e.__class__.__name__}: {e}\n```'
                                     )

        func = env['func']
        try:
            with redirect_stdout(stdout):
                ret = await func()
        except Exception as e:
            value = stdout.getvalue()
            await self.bot.say(f'```py\n{value}{traceback.format_exc()}\n```')
        else:
            value = stdout.getvalue()
            try:
                await ctx.message.add_reaction('\u2705')
            except:
                pass

            if ret is None:
                if value:
                    await self.bot.say(f'```py\n{value}\n```')
            else:
                self._last_result = ret
                await self.bot.say(f'```py\n{value}{ret}\n```')

    @commands.command(pass_context=True)
    @checks.is_owner()
    async def repl(self, ctx):
        """Launches an interactive REPL session."""
        variables = {
            'ctx': ctx,
            'bot': self.bot,
            'message': ctx.message,
            'server': ctx.message.server,
            'channel': ctx.message.channel,
            'author': ctx.message.author,
            '_': None,
        }

        if ctx.message.channel.id in self.sessions:
            await self.bot.say(
                'Already running a REPL session in this channel. Exit it with `quit`.'
            )
            return

        self.sessions.add(ctx.message.channel.id)
        await self.bot.say(
            'Enter code to execute or evaluate. `exit()` or `quit` to exit.')

        def check(m):
            return m.author.id == ctx.message.author.id and \
                m.channel.id == ctx.message.channel.id and \
                m.content.startswith('`')

        while True:
            try:
                response = await self.bot.wait_for_message(
                    check=check, timeout=10.0 * 60.0)
            except asyncio.TimeoutError:
                await self.bot.say('Exiting REPL session.')
                self.sessions.remove(ctx.message.channel.id)
                break

            cleaned = self.cleanup_code(response.content)

            if cleaned in ('quit', 'exit', 'exit()'):
                await self.bot.say('Exiting.')
                self.sessions.remove(ctx.message.channel.id)
                return

            executor = exec
            if cleaned.count('\n') == 0:
                # single statement, potentially 'eval'
                try:
                    code = compile(cleaned, '<repl session>', 'eval')
                except SyntaxError:
                    pass
                else:
                    executor = eval

            if executor is exec:
                try:
                    code = compile(cleaned, '<repl session>', 'exec')
                except SyntaxError as e:
                    await self.bot.say(self.get_syntax_error(e))
                    continue

            variables['message'] = response

            fmt = None
            stdout = io.StringIO()

            try:
                with redirect_stdout(stdout):
                    result = executor(code, variables)
                    if inspect.isawaitable(result):
                        result = await result
            except Exception as e:
                value = stdout.getvalue()
                fmt = f'```py\n{value}{traceback.format_exc()}\n```'
            else:
                value = stdout.getvalue()
                if result is not None:
                    fmt = f'```py\n{value}{result}\n```'
                    variables['_'] = result
                elif value:
                    fmt = f'```py\n{value}\n```'

            try:
                if fmt is not None:
                    if len(fmt) > 2000:
                        await self.bot.say('Content too big to be printed.')
                    else:
                        await self.bot.say(fmt)
            except discord.Forbidden:
                pass
            except discord.HTTPException as e:
                await self.bot.say(f'Unexpected error: `{e}`')

    @commands.command()
    @checks.is_owner()
    async def load(self, module: str):
        """Loads a module."""
        try:
            self.bot.load_extension("modules." + module)
            if module not in self.bot.loaded_modules:
                self.bot.loaded_modules.append(module)
                utils.save_json(self.bot.loaded_modules,
                                self.bot.modules_file_path)
        except Exception:
            tb = traceback.format_exc()
            await self.bot.say("\U0001f52b\n```" + tb + "```")
        else:
            await self.bot.say('\U0001f44c')
            print(module + " loaded.")

    @commands.command()
    @checks.is_owner()
    async def unload(self, module: str):
        """Unloads a module."""
        if module in self.bot.loaded_modules:
            try:
                self.bot.unload_extension("modules." + module)
                self.bot.loaded_modules.remove(module)
                utils.save_json(self.bot.loaded_modules,
                                self.bot.modules_file_path)
            except Exception:
                tb = traceback.format_exc()
                await self.bot.say("\U0001f52b\n```" + tb + "```")
            else:
                await self.bot.say('\U0001f44c')
                print(module + " unloaded.")
        else:
            await self.bot.say("This module isn't even loaded")

    @commands.command()
    @checks.is_owner()
    async def reload(self, module: str):
        """Reloads a module."""
        try:
            if module in self.bot.loaded_modules:
                self.bot.unload_extension("modules." + module)
                self.bot.loaded_modules.remove(module)
                utils.save_json(self.bot.loaded_modules,
                                self.bot.modules_file_path)

            self.bot.load_extension("modules." + module)
            self.bot.loaded_modules.append(module)
            utils.save_json(self.bot.loaded_modules, self.bot.modules_file_path)
        except Exception:
            tb = traceback.format_exc()
            await self.bot.say("\U0001f52b\n```" + tb + "```")
        else:
            await self.bot.say('\U0001f44c')
            print(module + " reloaded.")

    @commands.command()
    @checks.is_owner()
    async def list_modules(self):
        """Lists all the modules."""
        files = [f[:-3] for f in listdir("modules/") if f[-3:] == ".py"]
        msg = "Modules\n---------------------\n\n"
        for i in range(0, len(files)):
            msg += str(i + 1) + ". " + files[i] + ": "
            if files[i] in self.bot.loaded_modules:
                msg += "Loaded :white_check_mark:\n"
            else:
                msg += "Not loaded :x:\n"
        await self.bot.say(msg)

    @commands.command()
    @checks.is_owner()
    async def shutdown(self):
        """Shutdowns the bot"""
        self.save_infos()
        await self.bot.say("Bye! :wave:")
        await self.bot.logout()

    @commands.command()
    @checks.is_owner()
    async def set_avatar(self, avatar_link: str):
        """Sets bot's avatar
        Parameters:
            avatar_link: The link of the the picture which will become the new bot's avatar

        Example: [p]set_avatar http://i.imgur.com/bjmbH1e.png"""
        r = requests.get(avatar_link)
        if r.status_code == 200:
            try:
                await self.bot.edit_profile(avatar=r.content)
                await self.bot.say("Done!")
            except discord.HTTPException:
                await self.bot.say("HTTP Exception")
            except discord.InvalidArgument:
                await self.bot.say("Wrong image format")
            except requests.exceptions.MissingSchema:
                await self.bot.say("Invalid URL")
        else:
            await self.bot.say(
                "Error " + str(r.status_code) +
                ": The link must be incorrect, " +
                "make sure the link finishes with `.png`, `.jpg`, `.jpeg`, etc")

    @commands.command()
    @checks.is_owner()
    async def set_name(self, *name):
        """Sets bot's name
        Parameters:
            *name: The name you want to set for the bot

        Example: [p]set_name Beaftek's bot"""
        try:
            await self.bot.edit_profile(username=" ".join(name))
            await self.bot.say("Done!")
        except discord.HTTPException:
            await self.bot.say("HTTP Exception")
        except discord.InvalidArgument:
            await self.bot.say("Wrong name format (too long?)")

    @commands.command(pass_context=True)
    @checks.is_owner()
    async def set_nickname(self, ctx, *nickname):
        """Sets bot's nickname
        Parameters:
            *nickname:  The nickname you want to set for the bot for the server
                        Leaving this blank will remove bot's nickname

        Example: [p]set_nickname myGreatNickname"""
        try:
            await self.bot.change_nickname(
                discord.utils.find(lambda x: x.id == self.bot.user.id,
                                   ctx.message.server.members),
                " ".join(nickname))
            await self.bot.say("Done!")
        except discord.Forbidden:
            await self.bot.say(
                "I'm not permitted to change my nickname in this server.")
        except discord.HTTPException:
            await self.bot.say("HTTP Exception")

    @commands.command()
    @checks.is_owner()
    async def set_game(self, *game):
        """Sets bot's game
        Parameters:
            *game:  The game you want to set for the bot
                    Leaving this blank will remove bot's game

        Example: [p]set_game with fire!"""
        try:
            if game:
                await self.bot.change_presence(
                    game=discord.Game(name=" ".join(game), type=0))
            else:
                await self.bot.change_presence(game=None)
            await self.bot.say("Done! :ok_hand:")
        except discord.InvalidArgument:
            await self.bot.say("Wrong game name format (too long?)")

    @commands.command()
    @checks.is_owner()
    async def set_stream(self, stream_link: str = "", *game):
        """Sets bot's stream name
        Parameters:
            stream_link: the link to the stream you want to set for the bot
            *game:  The game you want to set for the bot's stream
                    Leaving this blank will remove bot's stream status

        Example: [p]set_stream https://www.twitch.tv/beafantles coding myself!"""
        try:
            if stream_link != "":
                if stream_link.startswith("https://www.twitch.tv/"):
                    await self.bot.change_presence(
                        game=discord.Game(
                            name=" ".join(game), type=1, url=stream_link))
                    await self.bot.say("Done! :ok_hand:")
                else:
                    await self.bot.say("Please provide a correct stream link")
            else:
                await self.bot.change_presence(game=None)
                await self.bot.say("Done! :ok_hand:")
        except discord.InvalidArgument:
            await self.bot.say("Wrong game name format (too long?)")

    @commands.command()
    @checks.is_owner()
    async def set_status(self, status: str = "online"):
        """Sets bot's status
        Parameters:
            status: the status you want to set for the bot
                    Leaving this blank will set bot's status as online

        Example: [p]set_status do_not_disturb

        Note: Here are all the available statutes:
                - online    --> Online status   (green)
                - idle      --> Idle            (orange)
                - dnd       --> Do not disturb  (red)
                - offline   --> Offline status  (grey)"""
        statutes = {
            "online": discord.Status.online,
            "idle": discord.Status.idle,
            "dnd": discord.Status.do_not_disturb,
            "offline": discord.Status.offline
        }
        if status in ["online", "idle", "dnd", "offline"]:
            await self.bot.change_presence(status=statutes[status])
            await self.bot.say("Done! :ok_hand:")
        else:
            await self.bot.say(
                "Please provide a correct status!\n" +
                "You can check available statutes typing `[p]help set_status`.")

    @commands.command(pass_context=True)
    @checks.is_owner()
    async def list_servers(self, ctx):
        """Lists bot's server and ask if you want to leave one"""
        msg = "```Markdown\nServers\n==================\n\n"
        i = 1
        servers = []
        for server in self.bot.servers:
            msg += "[" + str(i) + "](" + server.name + ")\n"
            i += 1
            servers.append(server.id)
        msg += "```\nIf you want me to leave one of these servers, just type its number."
        await self.bot.say(msg)
        answer = await self.bot.wait_for_message(
            timeout=180, author=ctx.message.author, channel=ctx.message.channel)
        if answer:
            try:
                index = int(answer.content)
                server_to_leave = discord.utils.find(
                    lambda x: x.id == servers[index - 1], self.bot.servers)
                await self.bot.say(
                    "If you want to leave this server, type `yes`!")

                def check(msg):
                    return msg.content.lower() == "yes"

                answer = await self.bot.wait_for_message(
                    timeout=60,
                    author=ctx.message.author,
                    channel=ctx.message.channel,
                    check=check)
                if answer:
                    try:
                        await self.bot.leave_server(server_to_leave)
                        await self.bot.say("Done! :ok_hand:")
                    except discord.HTTPException:
                        await self.bot.say("HTTP Error")
            except ValueError:
                pass

    @commands.command(pass_context=True)
    @checks.is_owner()
    async def leave_server(self, ctx):
        """Leaves the current server"""
        await self.bot.say("If you want to leave this server, type `yes`!")

        def check(msg):
            return msg.content.lower() == "yes"

        answer = await self.bot.wait_for_message(
            timeout=60,
            author=ctx.message.author,
            channel=ctx.message.channel,
            check=check)
        if answer:
            try:
                await self.bot.say("Bye! :wave:")
                await self.bot.leave_server(ctx.message.server)
            except discord.HTTPException:
                await self.bot.say("HTTP Error")

    @commands.command(pass_context=True)
    async def info(self, ctx):
        """Show bot's info"""
        embed = discord.Embed(title="Bot's info", type="rich embed")
        embed.set_thumbnail(
            url=discord.utils.find(lambda x: x.id == self.bot.user.id,
                                   ctx.message.server.members).avatar_url)
        delta = datetime.now() - self.bot.created_at
        embed.set_footer(text="Created at " + self.bot.created_at.strftime(
            "%d/%m/%Y %H:%M:%S") + " (" + utils.convert_seconds_to_str(
                delta.total_seconds()) + " ago)")

        python_version = str(
            subprocess.check_output("python --version", shell=True))[2:-5]
        python_version += " " + platform.architecture()[0][:-3] + " bits"
        commit = str(subprocess.check_output("git rev-parse HEAD",
                                             shell=True))[2:-3]
        os_infos = "Running on " + platform.platform()
        if platform.machine().endswith("64"):
            os_infos += " 64 bits"
        else:
            os_infos += " 32 bits"
        embed.add_field(name="Python's version", value=python_version)
        embed.add_field(name="Commit", value=commit)
        embed.add_field(name="Bot's version", value=self.bot.version)
        embed.add_field(name="Discord's version", value=discord.__version__)
        embed.add_field(name="Environment", value=os_infos)

        embed.add_field(
            name="Total commands typed", value=str(self.bot.total_commands + 1))
        delta = (datetime.now() - self.bot.launched_at) + \
            self.bot.total_runtime
        msg = utils.convert_seconds_to_str(delta.total_seconds())
        if msg != "":
            embed.add_field(name="Total run time", value=msg)
        delta = datetime.now() - self.bot.launched_at
        msg = utils.convert_seconds_to_str(delta.total_seconds())
        if msg != "":
            embed.add_field(name="Run time", value=msg)
        embed.add_field(name="Servers", value=str(len(self.bot.servers)))
        embed.add_field(
            name="Text channels",
            value=str(
                len([
                    x for x in self.bot.get_all_channels()
                    if x.type == discord.ChannelType.text
                ])))
        embed.add_field(
            name="Voice channels",
            value=str(
                len([
                    x for x in self.bot.get_all_channels()
                    if x.type == discord.ChannelType.voice
                ])))

        known_members = []
        for server in self.bot.servers:
            for member in server.members:
                if member.id not in known_members:
                    known_members.append(member.id)
        embed.add_field(name="Members", value=str(len(known_members)))

        await self.bot.send_message(
            destination=ctx.message.channel, embed=embed)

    @commands.command()
    async def version(self):
        """Shows bot's version"""
        python_version = str(
            subprocess.check_output("python --version", shell=True))[2:-5]
        python_version += " " + platform.architecture()[0][:-3] + " bits"
        commit = str(subprocess.check_output("git rev-parse HEAD",
                                             shell=True))[2:-3]
        os_infos = "Running on " + platform.platform()
        if platform.machine().endswith("64"):
            os_infos += " 64 bits"
        else:
            os_infos += " 32 bits"
        await self.bot.say(
            "Python version: " + python_version + "\n" + "Commit: " + commit +
            "\n" + "Bot's version: " + self.bot.version + "\n" +
            "Discord's version: " + discord.__version__ + "\n" +
            "Environment: " + os_infos)


def setup(bot):
    bot.add_cog(Base(bot))
