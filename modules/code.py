"""The module which is able to run codes"""

import discord
from discord.ext import commands
import async_timeout
import requests
import json
from modules.utils import utils
import os
from tzlocal import get_localzone


class Code(commands.Cog):
    """Code module"""

    def __init__(self, bot):
        self.bot = bot
        self.timeout = 15
        self.data_folder_path = "data/code/"
        self.pastebin_api_key_file_path = self.data_folder_path + \
            "pastebin_key.txt"
        self.users_configuration_path = self.data_folder_path + \
            "users_configuration.json"
        self.languages_identifiers_file_path = self.data_folder_path + \
            "languages_identifiers.json"
        self.default_engines_file_path = self.data_folder_path + \
            "default_engines.json"
        self.languages_images_file_path = self.data_folder_path + \
            "languages_images.json"
        self.languages_files_extensions_file_path = self.data_folder_path + \
            "languages_files_extensions.json"
        self.users_configuration = {}
        self.load_pastebin_api_key()
        self.load_users_configuration()

        # Elements are list in case some extensions can be used.
        # Lazy K isn't supported yet (as this language use the character `,
        # it looks really ugly on Discord).
        self.languages_identifiers = utils.load_json(
            self.languages_identifiers_file_path)

        # The first element is the template name and the second one is the
        # engine name
        self.default_engines = utils.load_json(self.default_engines_file_path)

        # Languages logos
        self.languages_images = utils.load_json(self.languages_images_file_path)

        # Languages files extensions
        # https://fileinfo.com/filetypes/developer
        # https://www.wikiwand.com/en/List_of_file_formats
        # The first element must be the extension used in the
        # parameter "display-compile-command" for every language
        self.languages_files_extensions = utils.load_json(
            self.languages_files_extensions_file_path)

        self.configuration = {}
        self.load_info()

    def load_users_configuration(self):
        """Loads the users configuration"""
        if not os.path.exists(self.users_configuration_path):
            if not os.path.isdir("data/code"):
                os.makedirs("data/code")

            utils.save_json(self.users_configuration,
                            self.users_configuration_path)
        else:
            self.users_configuration = utils.load_json(
                self.users_configuration_path)

    def load_pastebin_api_key(self):
        """Loads the pastebin api key"""

        if not os.path.exists(self.pastebin_api_key_file_path):
            if not os.path.isdir("data/code"):
                os.makedirs("data/code")
            self.pastebin_api_key = input(
                "Please provide your Pastebin API key:\n> ")

            with open(self.pastebin_api_key_file_path, "w") as file:
                file.write(self.pastebin_api_key)
        else:
            with open(self.pastebin_api_key_file_path, "r") as file:
                self.pastebin_api_key = file.read()

    async def create_pastebin(self, paste_name: str, paste_code: str):
        """Creates a pastebin, returns its url"""
        async with async_timeout.timeout(15):
            async with self.bot.session.post(
                    "https://pastebin.com/api/api_post.php",
                    data={
                        "api_dev_key": self.pastebin_api_key,
                        "api_option": "paste",
                        "api_paste_code": paste_code,
                        "api_paste_private": "1",
                        "api_paste_name": paste_name,
                        "api_paste_expire_date": "1W"
                    }) as response:
                return await response.text()

    def load_info(self):
        response = requests.get("https://wandbox.org/api/list.json")
        result = response.json()
        for info in result:
            language = info["language"]
            name = info["name"]
            # Warning: info["template"] is a list but it only contains
            # one element at the moment. So I'm just gonna consider
            # it as a str and not as a list. It may change in the
            # future, I don't know ¯\_(ツ)_/¯
            # Some languages have only one template
            template = info["templates"][0]
            # I don't know why there is a C++ and CPP language, as
            # CPP language seems to be exactly the same that C++
            # (with only 2 compilers which can be already found in
            # C++ language). So I'm just gonna ignore that.
            # OpenSSL isn't gonna be supported neither.
            if language != "CPP" and language != "OpenSSL":
                # Prettify languages names
                if language == "Bash script":
                    language = "Bash"
                elif language == "Vim script":
                    language = "Vim"

                if language not in self.configuration:
                    self.configuration[language] = {}
                if template not in self.configuration[language]:
                    self.configuration[language][template] = {}
                self.configuration[language][template][name] = info

                # We delete redundant info
                # ------------------------
                del self.configuration[language][template][name]["name"]
                del self.configuration[language][template][name]["display-name"]
                del self.configuration[language][template][name]["language"]
                del self.configuration[language][template][name]["templates"]
                # I don't know what "provider" means but as this attribute
                # is always equal to 0, I'm just gonna ignore it.
                del self.configuration[language][template][name]["provider"]
                del self.configuration[language][template][name]["switches"]

    async def get_fetch(self, url):
        async with async_timeout.timeout(15):
            async with self.bot.session.get(url) as response:
                return await response.json()

    async def post_fetch(self, url, data=None):
        async with async_timeout.timeout(15):
            async with self.bot.session.post(
                    url,
                    data=json.dumps(data),
                    headers={"content-type": "text/javascript"}) as response:
                return await response.json()

    async def get_paste(self, url):
        async with async_timeout.timeout(15):
            async with self.bot.session.get(url) as response:
                result = await response.text()
                language = None
                code = None
                if not url.startswith("https://pastebin.com/raw/"):
                    language_begin = result.find("<a href=\"/archive/")
                    language_begin = result[language_begin:].find(
                        "margin:0\">") + language_begin
                    language_end = result[language_begin:].find(
                        "</a>") + language_begin
                    language = result[language_begin +
                                      len("margin:0\">"):language_end]
                    delimiter = url.rfind("/")
                    url = url[:delimiter] + "/raw" + url[delimiter:]
                    async with self.bot.session.get(url) as response:
                        code = await response.text()
                else:
                    code = result
                return (code, language)

    async def add_long_field(self, embed: discord.Embed, parameter_name: str,
                             result: dict, field_name: str):
        """Adds a long field to the embed. Link a pastebin in case the
        field value is too long"""
        if parameter_name in result:
            if len(result[parameter_name])\
                    > 1022 or result[parameter_name].count("\n") > 20:
                url = await self.create_pastebin(field_name,
                                                 result[parameter_name])
                delimiter = url.rfind("/")
                url = url[:delimiter] + "/raw" + url[delimiter:]
                embed.add_field(name=field_name,
                                value=":page_facing_up: [" + field_name +
                                ".txt](" + url + ")",
                                inline=False)
            else:
                embed.add_field(name=field_name,
                                value="`" + result[parameter_name] + "`",
                                inline=False)

    async def create_embed_result(self, ctx, language: str, template_used: str,
                                  engine_used: str, command_options: str,
                                  info: dict):
        # Returns an embed corresponding to the Wandbox comile result passed
        # field amount = 25, title/field name = 256, value = 1024, footer
        # text/description = 2048 Note that the sum of all characters
        # in the embed should be less than or equal to 6000.
        embed = discord.Embed()
        embed.title = "Results"
        embed.url = info["url"]
        timestamp = ctx.message.created_at
        timestamp += -1 * get_localzone().utcoffset(timestamp)
        embed.timestamp = timestamp
        embed.add_field(name="Engine used", value=engine_used, inline=True)
        embed.add_field(name="Command used",
                        value=self.configuration[language][template_used]
                        [engine_used]["display-compile-command"] + " " +
                        command_options,
                        inline=True)
        if "compiler_error" in info or "program_error" in info:
            if "status" not in info or info["status"] != '0':
                embed.colour = discord.Color.red()
            else:
                embed.colour = discord.Color.orange()
        elif "signal" in info:
            embed.colour = discord.Color.red()
        elif info["status"] != '0':
            embed.colour = discord.Color.orange()
        else:
            embed.colour = discord.Color.green()
        embed.set_footer(text="Requested by " + ctx.message.author.name + "#" +
                         ctx.message.author.discriminator,
                         icon_url=ctx.message.author.avatar_url)
        embed.set_thumbnail(url=self.languages_images[language])
        embed.set_author(name=self.bot.user.name + "#" +
                         self.bot.user.discriminator,
                         icon_url=self.bot.user.avatar_url)

        remaining_space = 6000 - \
            (30 + len(ctx.message.author.name) + len(self.bot.user.name))

        if "status" in info:
            embed.add_field(name="Exit status",
                            value=info["status"],
                            inline=False)
            remaining_space -= 11 + len(info["status"])

        await self.add_long_field(embed, "signal", info, "Signal")
        await self.add_long_field(embed, "compiler_output", info,
                                  "Compiler output")
        await self.add_long_field(embed, "compiler_error", info,
                                  "Compiler warnings / errors")
        await self.add_long_field(embed, "program_output", info, "Output")
        await self.add_long_field(embed, "program_error", info,
                                  "Runtime errors")

        return embed

    @commands.command()
    async def code(self, ctx, *, code):
        """
        You can provide your code in two different ways:
            - You can directly use Markdown syntax with your
            language identifier (use list_identifiers to list
            all the language identifiers).
            - Submit the pastebin link to your code.
            (Specify the syntax highlighting) --> Use the
            parameter "code".

        If you want to explicitly specify your programming language,
        use the parameter "language".
        Indeed, if you have several files and if this parameter is
        not specified, the programming language is deduced from
        the extensions of the provided files (see the
        list_extensions command).

        If your program has to interact with the user using inputs,
        you can specify them using the parameter "input".
        Each line of this parameter value corresponds to an user input.

        If your program is sectioned into several files, you can provide
        them using the "code" parameter.
        The content of each files must be hosted on pastebin.
        The first line corresponds to the "main" file, and will have a
        fixed name (see the list_main_file_names command to get these names).
        Each following line is composed of 2 elements : the file name and
        the pastebin link to the file content, respectively.

        If you want to explicitly specify an engine for running your code,
        you can use the "engine" parameter.
        You can list all the available engines by using the list_engines
        command.

        You can add compilation / runtime options by using the parameters
        "compiler-options" and "runtime-options".

        You can add the "output_only" parameter to only get the output
        result of the code (only if the code has no errors).

        The values of the parameters "code" and "input" must be surrounded
        by the character `.

        The bot supports 32 programming languages, which can be listed
        using the list_languages command.

        See more info and examples here:
        https://github.com/Beafantles/Discode#how-to-use-the-bot
        https://www.youtube.com/watch?v=6CVZJft65RI
        """
        lines = code.split("\n")
        parameters = {}
        has_verbose_code = False
        code_language = None
        supposed_language = None
        for line in lines:
            if line.startswith("code"):
                has_verbose_code = True
                break
        if not has_verbose_code:
            begin = code.find("```")
            language_extension = code[begin + 3:code[begin + 3:].find("\n") +
                                      begin + 3].lower()
            no_code = False
            try:
                end = code[begin + 3 + len(language_extension):].rfind("```")
            except IndexError:
                no_code = True
            if begin == -1 or end == -1:
                no_code = True
            if no_code:
                await ctx.channel.send(
                    "Incorrect syntax, please use Markdown's "
                    "syntax for your code.")
                return
            for language in self.languages_identifiers:
                if language_extension in self.languages_identifiers[language]:
                    code_language = language
                    break
            if not code_language:
                await ctx.channel.send(
                    "Incorrect language identifier for your code.\n"
                    "To list all the supported languages identifiers, "
                    "please use `" + self.bot.prefix + "list_identifiers`.")
            before = code[:begin]
            after = code[end + begin + 6 + len(language_extension):]
            lines = ((before[:-1] if before else "") +
                     (after[1:] if after else "")).split("\n")
            if len(lines) == 1 and lines[0] == '':
                lines = []
            code = code[begin + 3 + len(language_extension):end + begin + 3 +
                        len(language_extension)]
            parameters["code"] = code
        i = 0
        while i < len(lines):
            line = lines[i]
            if line.find(" ") != -1:
                parameter_name = line[:line.find(" ")]
            else:
                parameter_name = line
            if parameter_name not in [
                    "engine", "code", "compiler-options", "runtime-options",
                    "input", "language", "output_only"
            ]:
                await ctx.channel.send(
                    "Invalid parameter `" + parameter_name +
                    "`.\nCheck out available parameters by typing `" +
                    self.bot.prefix + "help code`.\nIgnoring this parameter.")
            else:
                if parameter_name == "input":
                    begin = line.find("`")
                    if begin == -1:
                        await ctx.channel.send(
                            "Invalid input parameter format.\nCheck "
                            "out input format by typing `" + self.bot.prefix +
                            "help code`.")
                        return
                    parameter_value = ""
                    line = line[begin + 1:]
                    found = False
                    while i < len(lines):
                        end = line.find("`")
                        if end != -1:
                            found = True
                            parameter_value += line[:end]
                            break
                        else:
                            parameter_value += line + "\n"
                        i += 1
                        if i < len(lines):
                            line = lines[i]
                    if not found:
                        await ctx.channel.send(
                            "Invalid input parameter format.\nCheck out "
                            "input format by typing `" + self.bot.prefix +
                            "help code`.")
                        return
                elif parameter_name == "output_only":
                    parameter_value = True
                elif parameter_name == "code":
                    begin = line.find("`")
                    if begin == -1:
                        await ctx.channel.send(
                            "Invalid code parameter format.\n"
                            "Check out code format by typing `" +
                            self.bot.prefix + "help code`.")
                        return
                    parameter_value = []
                    line = line[begin + 1:]
                    found = False
                    while i < len(lines):
                        end = line.find("`")
                        if end != -1:
                            found = True
                            parameter_value.append(line[:end])
                            break
                        else:
                            parameter_value.append(line)
                        i += 1
                        if i < len(lines):
                            line = lines[i]
                    if not found:
                        await ctx.channel.send(
                            "Invalid code parameter format.\nCheck out "
                            "code format by typing `" + self.bot.prefix +
                            "help code`.")
                        return
                    new_value = []
                    supposed_languages = {}
                    first = True
                    first_code = None
                    for line in parameter_value:
                        if first:
                            if not line.startswith("https://pastebin.com/"):
                                await ctx.channel.send(
                                    "Incorrect link for the first file.\n"
                                    "The link must be an url from pastebin.")
                                return
                            else:
                                url = line
                            result = await self.get_paste(url)
                            first_code = result[0]
                            if result[1] and result[1] in self.configuration:
                                supposed_languages[result[1]] = 1
                            first = False
                            continue
                        delimiter = line.rfind(" ")
                        if delimiter == -1:
                            await ctx.channel.send(
                                "Invalid code parameter format.\nCheck "
                                "out code format by typing `" +
                                self.bot.prefix + "help code`.")
                            return
                        file_name = line[:delimiter]
                        file_link = line[delimiter + 1:]
                        file_code = None
                        if not file_link.startswith("https://pastebin.com/"):
                            await ctx.channel.send(
                                "Incorrect link for the file `" + file_name +
                                "`.\nThe link must be an url from pastebin.")
                            return
                        url = file_link
                        result = await self.get_paste(url)
                        file_code = result[0]
                        if result[1]:
                            if result[1] in supposed_languages:
                                supposed_languages[result[1]] += 1
                            else:
                                supposed_languages[result[1]] = 1
                        else:
                            extension_delimiter = file_name.rfind(".")
                            if extension_delimiter == -1:
                                await ctx.channel.send(
                                    "Invalid file name format.\nThere is "
                                    "no file extension.\nCheck out code "
                                    "format by typing `" + self.bot.prefix +
                                    "help code`.")
                                return
                            file_extension = file_name[extension_delimiter + 1:]
                            for language in self.languages_files_extensions:
                                if file_extension.lower(
                                ) in self.languages_files_extensions[language]:
                                    if language in supposed_languages:
                                        supposed_languages[language] += 1
                                    else:
                                        supposed_languages[language] = 1
                        new_value.append({"file": file_name, "code": file_code})
                    if supposed_languages:
                        supposed_language = sorted(supposed_languages.items(),
                                                   key=lambda x: x[1],
                                                   reverse=True)[0][0]
                    parameter_value = first_code
                    parameters["codes"] = new_value
                elif parameter_name == "language":
                    delimiter = line.find(" ")
                    if delimiter == -1:
                        await ctx.channel.send(
                            "Please specify a code language.\nCheck out "
                            "code format by typing `" + self.bot.prefix +
                            "help code`.")
                        return
                    language_name = line[delimiter + 1:]
                    correct_language = False
                    for language in self.configuration:
                        if language.upper() == language_name.upper():
                            correct_language = True
                            code_language = language
                            break
                    if not correct_language:
                        await ctx.channel.send(
                            "`" + language_name +
                            "` is not a correct language name / "
                            "isn't available for the bot.\nTo "
                            "list all the available languages, please use `" +
                            self.bot.prefix + "list_languages`.")
                        return
                    parameter_value = code_language
                else:
                    parameter_value = line[line.find(" ") + 1:]
                if parameter_name in parameters:
                    await ctx.channel.send("The parameter `" + parameter_name +
                                           "` is already provided.")
                    return
                parameters[parameter_name] = parameter_value
            i += 1
        if "code" not in parameters:
            await ctx.channel.send("Please provide the code!")
            return
        if not code_language:
            if not supposed_language:
                await ctx.channel.send(
                    "Couldn't guess which language to use.\nPlease specify "
                    "it with `language` parameter.\nCheck out `" +
                    self.bot.prefix + "help code` for more info.")
                return
            else:
                code_language = supposed_language
                await ctx.channel.send(
                    code_language +
                    " was supposed according to your files names.\nTo "
                    "specify it explicity, please use `language` "
                    "parameter.\nCheck out `" + self.bot.prefix +
                    "help code` for more info.")
        engine_template_used = None
        if "engine" in parameters:
            correct_engine = False
            parameters["engine"] = parameters["engine"].lower()
            try:
                engine_index = int(parameters["engine"])
                i = 0
                if engine_index >= 1:
                    for engine_template in self.configuration[code_language]:
                        nb_engines = len(
                            self.configuration[code_language][engine_template])
                        if engine_index > nb_engines + i:
                            i += nb_engines
                        else:
                            engine_template_used = engine_template
                            parameters["engine"] = list(
                                self.configuration[code_language]
                                [engine_template])[engine_index - i - 1]
                            correct_engine = True
                            break
            except ValueError:
                for engine_template in self.configuration[code_language]:
                    for engine in self.configuration[code_language][
                            engine_template]:
                        if parameters["engine"] == engine:
                            correct_engine = True
                            engine_template_used = engine_template
                            break
                    if correct_engine:
                        break
            if not correct_engine:
                await ctx.channel.send("`" + parameters["engine"] +
                                       "` is not a correct engine for " +
                                       code_language +
                                       " / isn't available for the bot.\nTo "
                                       "list all the available engine for " +
                                       code_language + ", please use `" +
                                       self.bot.prefix + "list_engines " +
                                       code_language + "`")
                return
        else:
            if ctx.message.author.id in self.users_configuration \
                and "engines" in self.users_configuration[
                    ctx.message.author.id
                ] and code_language in self.users_configuration[
                        ctx.message.author.id]["engines"]:
                engine_template_used = self.users_configuration[
                    ctx.message.author.id]["engines"][code_language][0]
                parameters["engine"] = self.users_configuration[
                    ctx.message.author.id]["engines"][code_language][1]
            else:
                engine_template_used = self.default_engines[code_language][0]
                parameters["engine"] = self.default_engines[code_language][1]
        if "compiler-options" in parameters and not self.configuration[
                code_language][engine_template_used][
                    parameters["engine"]]["compiler-option-raw"]:
            await ctx.channel.send(
                "There is no options available for compilation using `" +
                parameters["engine"] + "`.\nIgnoring these options.")
            del parameters["compiler-options"]
        if "runtime-options" in parameters and not self.configuration[
                code_language][engine_template_used][
                    parameters["engine"]]["runtime-option-raw"]:
            await ctx.channel.send(
                "There is no options available for runtime execution using `" +
                parameters["engine"] + "`.\nIgnoring these options.")
            del parameters["runtime-options"]
        if "output_only" not in parameters:
            if ctx.message.author.id in self.users_configuration \
                and "output_only" in self.users_configuration[
                    ctx.message.author.id]:
                parameters["output_only"] = self.users_configuration[
                    ctx.message.author.id]["output_only"]
            else:
                parameters["output_only"] = False
        if "compiler-options" not in parameters:
            if ctx.message.author.id in self.users_configuration \
                and "compiler_options" in self.users_configuration[
                    ctx.message.author.
                    id] and code_language in self.users_configuration[
                        ctx.message.author.id]["compiler_options"]:
                parameters["compiler-options"] = self.users_configuration[
                    ctx.message.author.id]["compiler_options"][code_language]
            else:
                parameters["compiler-options"] = ""
        if "runtime-options" not in parameters:
            if ctx.message.author.id in self.users_configuration \
                and "runtime_options" in self.users_configuration[
                    ctx.message.author.
                    id] and code_language in self.users_configuration[
                        ctx.message.author.id]["runtime_options"]:
                parameters["runtime-options"] = self.users_configuration[
                    ctx.message.author.id]["runtime_options"][code_language]
            else:
                parameters["runtime-options"] = ""

        request = {
            "code": parameters["code"],
            "codes": parameters["codes"] if "codes" in parameters else [],
            "compiler": parameters["engine"],
            "save": True,
            "stdin": parameters["input"] if "input" in parameters else "",
            "compiler-option-raw": parameters["compiler-options"],
            "runtime-option-raw": parameters["runtime-options"]
        }

        async with ctx.typing():
            result = await self.post_fetch(
                "https://wandbox.org/api/compile.json", request)

        if not parameters["output_only"] or "compiler_error" in result \
                or "program_error" in result:
            embed = await self.create_embed_result(
                ctx, code_language, engine_template_used, parameters["engine"],
                (parameters["compiler-options"]
                 if "compiler-options" in parameters else "") +
                (parameters["runtime-options"]
                 if "runtime-options" in parameters else ""), result)
            await ctx.channel.send(embed=embed)
        else:
            msg = ""
            if len(result["program_output"])\
                    > 1998 or result["program_output"].count('\n') > 20:
                msg = "Output here: <" + await self.create_pastebin(
                    "Output", result["program_output"]) + '>'
            else:
                msg = '`' + result["program_output"] + '`'
            await ctx.channel.send(msg)

    @commands.command()
    async def list_languages(self, ctx):
        """Lists all the available languages for this module"""
        msg = "```Markdown\nAvailable languages\n===================\n\n"
        for i, language in enumerate(sorted(self.configuration)):
            msg += "[" + str(i + 1) + "](" + language + ")\n"
        msg += "```"
        await ctx.channel.send(msg)

    @commands.command()
    async def list_engines(self, ctx, *, language_name):
        """Lists all available compilers / interpreters for a language"""
        msg = "```Markdown\nAvailable engines\n=================\n\n"
        language_name = language_name.upper()
        for language in self.configuration:
            if language.upper() == language_name:
                i = 1
                nb_templates = len(self.configuration[language])
                for template in self.configuration[language]:
                    # In case there are several templates,
                    # group the different engines in them
                    if nb_templates != 1:
                        msg += "<" + template + ">\n"
                    for engine in self.configuration[language][template]:
                        msg += "[" + str(i) + "](" + engine + ")\n"
                        i += 1
                    if nb_templates != 1:
                        msg += "\n"
                msg += "```"
                await ctx.channel.send(msg)
                return
        await ctx.channel.send(
            "There is no such available language.\nTo list all the "
            "available languages, please use `" + self.bot.prefix +
            "list_languages`.")

    @commands.command()
    async def list_identifiers(self, ctx):
        """Lists all the languages identifiers
        recognized by Discord / the bot"""
        msg = "```Markdown\nLanguages identifiers\n=====================\n\n"
        for language in self.languages_identifiers:
            msg += "- " + language + (" " * (18 - len(language))) + "--> " + \
                " / ".join(self.languages_identifiers[language]) + "\n"
        msg += "```"
        await ctx.channel.send(msg)

    @commands.command()
    async def list_extensions(self, ctx):
        """Lists all the languages files extensions recognized by the bot"""
        msg = ("```Markdown\nLanguages files extensions"
               "\n=====================\n\n")
        for language in self.languages_files_extensions:
            msg += "- " + language + (" " * (18 - len(language))) + "--> ." + \
                " / .".join(self.languages_files_extensions[language]) + "\n"
        msg += "```"
        await ctx.channel.send(msg)

    @commands.command()
    async def list_main_file_names(self, ctx):
        """Lists the main files names for the different languages"""
        msg = "```Markdown\nMain files names\n=====================\n\n"
        for language in self.languages_files_extensions:
            extension = self.languages_files_extensions[language][0]
            msg += "- " + language + (" " * (18 - len(language))) + "--> prog"\
                + ("." if extension != "" else "") + extension + "\n"
        msg += "```"
        await ctx.channel.send(msg)

    def set_user_config(self, user: discord.Member, attribute: str, value):
        if user.id not in self.users_configuration:
            self.users_configuration[user.id] = {}
        self.users_configuration[user.id][attribute] = value
        utils.save_json(self.users_configuration, self.users_configuration_path)

    def set_user_sub_config(self, user: discord.Member, sub_config_name: str,
                            attribute: str, value):
        if user.id not in self.users_configuration:
            self.users_configuration[user.id] = {}
        if sub_config_name not in self.users_configuration[user.id]:
            self.users_configuration[user.id][sub_config_name] = {}
        self.users_configuration[user.id][sub_config_name][attribute] = value
        utils.save_json(self.users_configuration, self.users_configuration_path)

    @commands.group()
    async def config(self, ctx: commands.Context):
        """Configures your default settings"""
        if ctx.invoked_subcommand is None:
            await ctx.send_help(ctx.command)

    @config.command()
    async def output(self, ctx, output_mode: str = ""):
        """Configures output of the bot
            OUTPUT_ONLY to get only the output of your code
            (except if there are warnings or errors)
            EVERYTHING to show all info
        """
        if output_mode not in ["OUTPUT_ONLY", "EVERYTHING"]:
            await ctx.channel.send("Please choose one of the following option: "
                                   "EVERYTHING / OUTPUT_ONLY.")
        else:
            self.set_user_config(
                ctx.message.author, "output_only",
                (True if output_mode == "OUTPUT_ONLY" else False))
            await ctx.channel.send("Done.")

    @config.command()
    async def reset(self, ctx):
        """Resets your configuration"""
        if ctx.message.author.id in self.users_configuration:
            del self.users_configuration[ctx.message.author.id]
            utils.save_json(self.users_configuration,
                            self.users_configuration_path)
            await ctx.channel.send("Done.")
        else:
            await ctx.channel.send("You hadn't any configured settings.")

    @config.command()
    async def engine(self, ctx, language_name: str = "", engine_name: str = ""):
        """Specifies default engine for a specific language"""
        if not language_name:
            await ctx.channel.send("Please specify a language.")
            return
        if not engine_name:
            await ctx.channel.send("Please specify an engine.")
            return
        found = False
        for language_identifier in self.languages_identifiers:
            if language_identifier.upper() == language_name.upper():
                language_name = language_identifier
                found = True
        if not found:
            await ctx.channel.send(
                "`" + language_name +
                "` is not a correct language name / isn't available "
                "for the bot.\nTo list all the available languages, "
                "please use `" + self.bot.prefix + "list_languages`.")
            return
        engine_template_name = None
        for engine_template in self.configuration[language_name]:
            if engine_name in self.configuration[language_name][
                    engine_template]:
                engine_template_name = engine_template
                break

        if not engine_template_name:
            await ctx.channel.send(
                "`" + engine_name + "` is not a correct engine for " +
                language_name +
                " / isn't available for the bot.\nTo list all the "
                "available engine for " + language_name + ", please use `" +
                self.bot.prefix + "list_engines " + language_name + "`")
            return
        self.set_user_sub_config(ctx.message.author, "engines", language_name,
                                 [engine_template_name, engine_name])
        await ctx.channel.send("Done.")

    @config.command()
    async def compiler_options(self,
                               ctx,
                               language_name: str = "",
                               *,
                               compiler_options):
        """Configures your default compilation options for a
        specifig language"""
        if not language_name:
            await ctx.channel.send("Please specify a language.")
            return
        found = False
        for language_identifier in self.languages_identifiers:
            if language_identifier.upper() == language_name.upper():
                language_name = language_identifier
                found = True
        if not found:
            await ctx.channel.send(
                "`" + language_name +
                "` is not a correct language name / isn't available "
                "for the bot.\nTo list all the available languages, "
                "please use `" + self.bot.prefix + "list_languages`.")
            return
        self.set_user_sub_config(ctx.message.author, "compiler_options",
                                 language_name, compiler_options)
        await ctx.channel.send("Done.")

    @config.command()
    async def runtime_options(self,
                              ctx,
                              language_name: str = "",
                              *,
                              runtime_options):
        """Configures your default runtime options for a specifig language"""
        if not language_name:
            await ctx.channel.send("Please specify a language.")
            return
        found = False
        for language_identifier in self.languages_identifiers:
            if language_identifier.upper() == language_name.upper():
                language_name = language_identifier
                found = True
        if not found:
            await ctx.channel.send(
                "`" + language_name +
                "` is not a correct language name / isn't available for "
                "the bot.\nTo list all the available languages, please use `" +
                self.bot.prefix + "list_languages`.")
            return
        self.set_user_sub_config(ctx.message.author, "runtime_options",
                                 language_name, runtime_options)
        await ctx.channel.send("Done.")

    @config.command()
    async def show(self, ctx):
        """Shows your configuration"""
        if ctx.message.author.id not in self.users_configuration:
            await ctx.channel.send("You don't have any settings set.")
            return
        msg = "```Markdown\nSettings\n==========\n\n"
        config = self.users_configuration[ctx.message.author.id]
        for setting in config:
            if setting == "output_only":
                msg += "[Output](" + ("Only result" if config[setting] ==
                                      "OUTPUT_ONLY" else "Everything") + ")\n"
            elif setting == "engines":
                msg += "<Engines>\n"
                for language in config["engines"]:
                    msg += "\t" + language + " --> " + \
                        config["engines"][language][1] + "\n"
            elif setting == "compiler_options":
                msg += "<Compiler options>\n"
                for language in config["compiler_options"]:
                    msg += "\t" + language + " --> " + \
                        config["compiler_options"][language] + "\n"
            elif setting == "runtime_options":
                msg += "<Runtime options>\n"
                for language in config["runtime_options"]:
                    msg += "\t" + language + " --> " + \
                        config["runtime_options"][language] + "\n"
        msg += "```"
        await ctx.channel.send(msg)


def setup(bot):
    bot.add_cog(Code(bot))
