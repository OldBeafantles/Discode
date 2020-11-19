"""Owner module"""

import discord
import traceback
import textwrap
import inspect
import asyncio
import io
import requests
import subprocess
import platform
from modules.utils import utils
from discord.ext import commands
from modules.utils import checks
from datetime import datetime
from os import listdir
from contextlib import redirect_stdout


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

    @commands.command()
    async def invite(self, ctx):
        """Gets invitation link"""
        await ctx.channel.send(
            "If you want to invite the bot to your server, you can use this link: <"
            + self.bot.invite_link + ">")

    @commands.command(name='eval')
    @checks.is_owner()
    async def eval(self, ctx, *, body: str):
        """Evaluates a code"""

        env = {
            'bot': self.bot,
            'ctx': ctx,
            'channel': ctx.message.channel,
            'author': ctx.message.author,
            'server': ctx.message.guild,
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
            return await ctx.channel.send(
                f'```py\n{e.__class__.__name__}: {e}\n```')

        func = env['func']
        try:
            with redirect_stdout(stdout):
                ret = await func()
        except Exception as e:
            value = stdout.getvalue()
            await ctx.channel.send(
                f'```py\n{value}{traceback.format_exc()}\n```')
        else:
            value = stdout.getvalue()
            try:
                await ctx.message.add_reaction('\u2705')
            except:
                pass

            if ret is None:
                if value:
                    await ctx.channel.send(f'```py\n{value}\n```')
            else:
                self._last_result = ret
                await ctx.channel.send(f'```py\n{value}{ret}\n```')

    @commands.command()
    @checks.is_owner()
    async def repl(self, ctx):
        """Launches an interactive REPL session."""
        variables = {
            'ctx': ctx,
            'bot': self.bot,
            'message': ctx.message,
            'server': ctx.message.guild,
            'channel': ctx.message.channel,
            'author': ctx.message.author,
            '_': None,
        }

        if ctx.message.channel.id in self.sessions:
            await ctx.channel.send(
                'Already running a REPL session in this channel. Exit it with `quit`.'
            )
            return

        self.sessions.add(ctx.message.channel.id)
        await ctx.channel.send(
            'Enter code to execute or evaluate. `exit()` or `quit` to exit.')

        def check(m):
            return m.author.id == ctx.message.author.id and \
                m.channel.id == ctx.message.channel.id and \
                m.content.startswith('`')

        while True:
            try:
                response = await self.bot.wait_for(
                    'message', check=check, timeout=10.0 * 60.0)
            except asyncio.TimeoutError:
                await ctx.channel.send('Exiting REPL session.')
                self.sessions.remove(ctx.message.channel.id)
                break

            cleaned = self.cleanup_code(response.content)

            if cleaned in ('quit', 'exit', 'exit()'):
                await ctx.channel.send('Exiting.')
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
                    await ctx.channel.send(self.get_syntax_error(e))
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
                        await ctx.channel.send('Content too big to be printed.')
                    else:
                        await ctx.channel.send(fmt)
            except discord.Forbidden:
                pass
            except discord.HTTPException as e:
                await ctx.channel.send(f'Unexpected error: `{e}`')

    @commands.command()
    @checks.is_owner()
    async def load(self, ctx, module: str):
        """Loads a module."""
        try:
            self.bot.load_extension("modules." + module)
            if module not in self.bot.loaded_modules:
                self.bot.loaded_modules.append(module)
                utils.save_json(self.bot.loaded_modules,
                                self.bot.modules_file_path)
        except Exception:
            tb = traceback.format_exc()
            await ctx.channel.send("\U0001f52b\n```" + tb + "```")
        else:
            await ctx.channel.send('\U0001f44c')
            print(module + " loaded.")

    @commands.command()
    @checks.is_owner()
    async def unload(self, ctx, module: str):
        """Unloads a module."""
        if module in self.bot.loaded_modules:
            try:
                self.bot.unload_extension("modules." + module)
                self.bot.loaded_modules.remove(module)
                utils.save_json(self.bot.loaded_modules,
                                self.bot.modules_file_path)
            except Exception:
                tb = traceback.format_exc()
                await ctx.channel.send("\U0001f52b\n```" + tb + "```")
            else:
                await ctx.channel.send('\U0001f44c')
                print(module + " unloaded.")
        else:
            await ctx.channel.send("This module isn't even loaded")

    @commands.command()
    @checks.is_owner()
    async def reload(self, ctx, module: str):
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
            await ctx.channel.send("\U0001f52b\n```" + tb + "```")
        else:
            await ctx.channel.send('\U0001f44c')
            print(module + " reloaded.")

    @commands.command()
    @checks.is_owner()
    async def list_modules(self, ctx):
        """Lists all the modules."""
        files = [f[:-3] for f in listdir("modules/") if f[-3:] == ".py"]
        msg = "Modules\n---------------------\n\n"
        for i in range(0, len(files)):
            msg += str(i + 1) + ". " + files[i] + ": "
            if files[i] in self.bot.loaded_modules:
                msg += "Loaded :white_check_mark:\n"
            else:
                msg += "Not loaded :x:\n"
        await ctx.channel.send(msg)

    @commands.command()
    @checks.is_owner()
    async def shutdown(self, ctx):
        """Shutdowns the bot"""
        self.save_infos()
        await ctx.channel.send("Bye! :wave:")
        await self.bot.logout()

    @commands.command()
    @checks.is_owner()
    async def set_avatar(self, ctx, avatar_link: str):
        """Sets bot's avatar
        Parameters:
            avatar_link: The link of the the picture which will become the new bot's avatar

        Example: [p]set_avatar http://i.imgur.com/bjmbH1e.png"""
        r = requests.get(avatar_link)
        if r.status_code == 200:
            try:
                await self.bot.user.edit(avatar=r.content)
                await ctx.channel.send("Done!")
            except discord.HTTPException as e:
                await ctx.channel.send(e)
            except discord.InvalidArgument:
                await ctx.channel.send("Wrong image format")
            except requests.exceptions.MissingSchema:
                await ctx.channel.send("Invalid URL")
        else:
            await ctx.channel.send(
                "Error " + str(r.status_code) +
                ": The link must be incorrect, " +
                "make sure the link finishes with `.png`, `.jpg`, `.jpeg`, etc")

    @commands.command()
    @checks.is_owner()
    async def set_name(self, ctx, *name):
        """Sets bot's name
        Parameters:
            *name: The name you want to set for the bot

        Example: [p]set_name Beaftek's bot"""
        try:
            await self.bot.user.edit(username=" ".join(name))
            await ctx.channel.send("Done!")
        except discord.HTTPException as e:
            await ctx.channel.send(e)
        except discord.InvalidArgument as e:
            await ctx.channel.send(e)

    @commands.command()
    @checks.is_owner()
    async def set_nickname(self, ctx, *nickname):
        """Sets bot's nickname
        Parameters:
            *nickname:  The nickname you want to set for the bot for the server
                        Leaving this blank will remove bot's nickname

        Example: [p]set_nickname myGreatNickname"""
        try:
            await ctx.me.edit(nick=" ".join(nickname))
            await ctx.channel.send("Done!")
        except discord.Forbidden:
            await ctx.channel.send(
                "I'm not permitted to change my nickname in this server.")
        except discord.HTTPException as e:
            await ctx.channel.send(e)

    @commands.command()
    @checks.is_owner()
    async def set_game(self, ctx, *game):
        """Sets bot's game
        Parameters:
            *game:  The game you want to set for the bot
                    Leaving this blank will remove bot's game

        Example: [p]set_game with fire!"""
        try:
            if game:
                await self.bot.change_presence(
                    activity=discord.Game(" ".join(game)))
            else:
                await self.bot.change_presence()
            await ctx.channel.send("Done! :ok_hand:")
        except discord.InvalidArgument as e:
            await ctx.channel.send(e)

    @commands.command()
    @checks.is_owner()
    async def set_stream(self, ctx, stream_link: str = "", *game):
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
                        activity=discord.Streaming(
                            name=" ".join(game), url=stream_link))
                    await ctx.channel.send("Done! :ok_hand:")
                else:
                    await ctx.channel.send(
                        "Please provide a correct stream link")
            else:
                await self.bot.change_presence()
                await ctx.channel.send("Done! :ok_hand:")
        except discord.InvalidArgument:
            await ctx.channel.send("Wrong game name format (too long?)")

    @commands.command()
    @checks.is_owner()
    async def set_status(self, ctx, status: str = "online"):
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
            await ctx.channel.send("Done! :ok_hand:")
        else:
            await ctx.channel.send(
                "Please provide a correct status!\n" +
                "You can check available statutes typing `[p]help set_status`.")

    @commands.command()
    @checks.is_owner()
    async def list_servers(self, ctx):
        """Lists bot's server and ask if you want to leave one"""
        msg = "```Markdown\nServers\n==================\n\n"
        i = 1
        servers = []
        for server in self.bot.guilds:
            msg += "[" + str(i) + "](" + server.name + ")\n"
            i += 1
            servers.append(server.id)
        msg += "```\nIf you want me to leave one of these servers, just type its number."
        await ctx.channel.send(msg)

        def check_1(m):
            return m.author == ctx.message.author and m.channel == ctx.message.channel

        answer = await self.bot.wait_for('message', timeout=180, check=check_1)
        if answer:
            try:
                index = int(answer.content)
                server_to_leave = discord.utils.find(
                    lambda x: x.id == servers[index - 1], self.bot.guilds)
                await ctx.channel.send(
                    "If you want to leave this server, type `yes`!")

                def check_2(msg):
                    return msg.author == ctx.message.author and msg.channel == ctx.message.channel

                answer = await self.bot.wait_for(
                    'message', timeout=60, check=check_2)
                if answer.content.lower() == "yes":
                    try:
                        await server_to_leave.leave()
                        await ctx.channel.send("Done! :ok_hand:")
                    except discord.HTTPException:
                        await ctx.channel.send("HTTP Error")
            except ValueError:
                pass

    @commands.command()
    @checks.is_owner()
    async def leave_server(self, ctx):
        """Leaves the current server"""
        await ctx.channel.send("If you want to leave this server, type `yes`!")

        def check(msg):
            return msg.author == ctx.message.author and msg.channel == ctx.message.channel

        answer = await self.bot.wait_for('message', timeout=60, check=check)
        if answer.content.lower() == "yes":
            try:
                await ctx.channel.send("Bye! :wave:")
                await ctx.message.guild.leave()
            except discord.HTTPException:
                await ctx.channel.send("HTTP Error")

    @commands.command()
    async def info(self, ctx):
        """Show bot's info"""
        embed = discord.Embed(title="Bot's info", type="rich embed")
        embed.set_thumbnail(
            url=discord.utils.find(lambda x: x.id == self.bot.user.id, ctx.
                                   message.guild.members).avatar_url)
        delta = datetime.now() - self.bot.created_at
        embed.set_footer(
            text="Created at " +
            self.bot.created_at.strftime("%d/%m/%Y %H:%M:%S") + " (" +
            utils.convert_seconds_to_str(delta.total_seconds()) + " ago)")

        verbose_version = str(
            subprocess.check_output("python --version", shell=True))
        python_version = verbose_version[2:(
            -5 if verbose_version.endswith("\\r\\n'") else -3)]
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
        embed.add_field(name="Servers", value=str(len(self.bot.guilds)))
        channels = self.bot.get_all_channels()
        nb_text_channels = 0
        nb_voice_channels = 0
        for server in self.bot.guilds:
            nb_text_channels += len(server.text_channels)
            nb_voice_channels += len(server.voice_channels)
        embed.add_field(name="Text channels", value=str(nb_text_channels))
        embed.add_field(name="Voice channels", value=str(nb_voice_channels))

        nb_users = 0
        for server in self.bot.guilds:
            nb_users += server.member_count
        embed.add_field(name="Members", value=str(nb_users))
        embed.add_field(
            name="Development server",
            value="Join it by clicking [here](https://" +
            self.bot.dev_server_invitation_link + ")")

        await ctx.message.channel.send(embed=embed)

    @commands.command()
    async def version(self, ctx):
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
        await ctx.channel.send("Python version: " + python_version + "\n" +
                               "Commit: " + commit + "\n" + "Bot's version: " +
                               self.bot.version + "\n" + "Discord's version: " +
                               discord.__version__ + "\n" + "Environment: " +
                               os_infos)

    @commands.command()
    async def bug(self, ctx, *, message):
        """Reports a bug"""
        try:
            message = ctx.message.author.name + "#" + ctx.message.author.discriminator + \
                "[" + str(ctx.message.author.id) + \
                "] reported a bug:\n" + message
            messages = utils.split_message(message)
            owner = discord.utils.find(lambda u: u.id == self.bot.owner_id,
                                       self.bot.get_all_members())
            for msg in messages:
                await owner.send(content=msg)
            await ctx.channel.send(
                "Thanks for reporting this bug. I let it know to " +
                owner.name + "#" + owner.discriminator + ".")
        except Exception as e:
            await ctx.channel.send(e)

    @commands.command()
    async def improvement(self, ctx, *, message):
        """Submits an improvement"""
        try:
            message = ctx.message.author.name + "#" + ctx.message.author.discriminator + \
                "[" + str(ctx.message.author.id) + \
                "] submitted an improvement:\n" + message
            messages = utils.split_message(message)
            owner = discord.utils.find(lambda u: u.id == self.bot.owner_id,
                                       self.bot.get_all_members())
            for msg in messages:
                await owner.send(content=msg)
            await ctx.channel.send(
                "Thanks for submitting this improvement. I let it know to " +
                owner.name + "#" + owner.discriminator + ".")
        except Exception as e:
            await ctx.channel.send(e)


def setup(bot):
    bot.add_cog(Base(bot))
