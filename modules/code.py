"""The module which is able to run C++ code"""

import discord
from discord.ext import commands
import async_timeout
import aiohttp
import requests
import json
from modules.utils import utils
import os
from tzlocal import get_localzone
from datetime import datetime
import sys
import traceback


class Code:
    """Code module"""

    def __init__(self, bot):
        self.bot = bot
        self.timeout = 15
        self.pastebin_api_key_file_path = "data/code/pastebin_key.txt"
        self.load_pastebin_api_key()

        # Elements are list in case some extensions can be used.
        self.languages_identifiers = {
            "Bash": ("bash", "sh"),
            "C": ("c",),
            "C#": ("cs", "csharp"),
            "C++": ("cpp",),
            "CoffeeScript": ("coffeescript",),
            "Crystal": ("crystal",),
            "D": ("d",),
            "Elixir": ("elixir",),
            "Erlang": ("erlang",),
            "F#": ("fsharp",),
            "Go": ("go",),
            "Groovy": ("groovy",),
            "Haskell": ("haskell",),
            "Java": ("java",),
            "JavaScript": ("js", "javascript"),
            # Lazy K isn't supported yet (as this language use the character `,
            # it looks really ugly on Discord).
            "Lazy K": ("k", "lazy_k"),
            "Lisp": ("lisp",),
            "Lua": ("lua",),
            "Nim": ("nim", "nimrod"),
            "OCaml": ("ocaml",),
            "Pascal": ("pascal",),
            "Perl": ("perl",),
            "PHP": ("php",),
            "Pony": ("pony",),
            "Python": ("py", "python"),
            "Rill": ("rill",),
            "Ruby": ("ruby",),
            "Rust": ("rust",),
            "Scala": ("scala",),
            "SQL": ("sql",),
            "Swift": ("swift",),
            "Vim": ("vim",)
        }

        # The first element is the template name and the second one is the engine name
        self.default_engines = {
            "Bash": ("bash", "bash"),
            "C": ("gcc-c", "gcc-head-c"),
            "C#": ("mono", "mono-head"),
            "C++": ("gcc", "gcc-head"),
            "CoffeeScript": ("coffeescript", "coffeescript-head"),
            "Crystal": ("crystal", "crystal-head"),
            "D": ("dmd", "dmd-head"),
            "Elixir": ("elixir", "elixir-head"),
            "Erlang": ("erlang", "erlang-head"),
            "F#": ("fsharp", "fsharp-head"),
            "Go": ("go", "go-head"),
            "Groovy": ("groovy", "groovy-head"),
            "Haskell": ("ghc", "ghc-head"),
            "Java": ("openjdk", "openjdk-head"),
            "JavaScript": ("nodejs", "nodejs-head"),
            "Lazy K": ("lazyk", "lazyk"),
            "Lisp": ("sbcl", "sbcl-head"),
            "Lua": ("lua", "luajit-head"),
            "Nim": ("nim", "nim-head"),
            "OCaml": ("ocaml", "ocaml-head"),
            "Pascal": ("fpc", "fpc-head"),
            "Perl": ("perl", "perl-head"),
            "PHP": ("php", "php-head"),
            "Pony": ("pony", "pony-head"),
            "Python": ("cpython", "cpython-head"),
            "Rill": ("rill", "rill-head"),
            "Ruby": ("ruby", "ruby-head"),
            "Rust": ("rust", "rust-head"),
            "Scala": ("scala", "scala-2.13.x"),
            "SQL": ("sqlite", "sqlite-head"),
            "Swift": ("swift", "swift-head"),
            "Vim": ("vim", "vim-head")
        }

        # Languages logos
        self.languages_images = {
            "Bash":
            "https://i.imgur.com/Fx9vZGc.png",
            "C":
            "https://wikiprogramming.org/wp-content/uploads/2015/05/c-logo.png",
            "C#":
            "https://www.loicdelaunay.fr/ressources/Icons/v3/csharp.png",
            "C++":
            "https://upload.wikimedia.org/wikipedia/commons/thumb/1/18/ISO_C%2B%2B_Logo.svg/1200px-ISO_C%2B%2B_Logo.svg.png",
            "CoffeeScript":
            "https://pbs.twimg.com/profile_images/557241144392708096/slQydAMv_400x400.png",
            "Crystal":
            "https://i.imgur.com/YzgCXSB.png",
            "D":
            "https://upload.wikimedia.org/wikipedia/commons/thumb/2/24/D_Programming_Language_logo.svg/317px-D_Programming_Language_logo.svg.png",
            "Elixir":
            "https://developer.fedoraproject.org/static/logo/elixir.png",
            "Erlang":
            "https://upload.wikimedia.org/wikipedia/commons/thumb/0/04/Erlang_logo.svg/1200px-Erlang_logo.svg.png",
            "F#":
            "https://i.imgur.com/NbRNr5U.png",
            "Go":
            "https://humancoders-formations.s3.amazonaws.com/uploads/course/logo/87/formation-go.png",
            "Groovy":
            "https://upload.wikimedia.org/wikipedia/commons/thumb/3/36/Groovy-logo.svg/1200px-Groovy-logo.svg.png",
            "Haskell":
            "http://www.unixstickers.com/image/cache/data/stickers/haskell/Haskell-purple.sh-600x600.png",
            "Java":
            "http://searchlite.nl/wp-content/uploads/2017/08/java-logo-large.png",
            "JavaScript":
            "http://www.i-programmer.info/images/stories/prof/iprogrammer/JavascriptName/JSlogo.jpg",
            "Lazy K":
            "https://i.imgur.com/Myl1Wq0.png",
            "Lisp":
            "https://www.supinfo.com/articles/resources/214885/6357/4.png",
            "Lua":
            "http://www.unixstickers.com/image/data/stickers/lua/lua.sh.png",
            "Nim":
            "https://raw.githubusercontent.com/nim-lang/assets/master/Art/logo-crown.png",
            "OCaml":
            "https://i.imgur.com/oPMs6Ft.png",
            "Pascal":
            "https://www.cours-exercices-pdf.com/images/turbo-pascal2-cours-exercices-pdf.jpg",
            "Perl":
            "https://blog.netapsys.fr/wp-content/uploads/2015/09/perl_logo.png",
            "PHP":
            "http://www.unixstickers.com/image/data/stickers/php/php.sh.png",
            "Pony":
            "https://i.imgur.com/11TSK43.png",
            "Python":
            "http://www.unixstickers.com/image/cache/data/stickers/python/python.sh-600x600.png",
            "Rill":
            "https://i.imgur.com/VagH89j.png",
            "Ruby":
            "http://www.dctacademy.com/wp-content/uploads/2015/06/ruby-logo.png",
            "Rust":
            "https://upload.wikimedia.org/wikipedia/commons/thumb/d/d5/Rust_programming_language_black_logo.svg/1200px-Rust_programming_language_black_logo.svg.png",
            "Scala":
            "https://i.imgur.com/5uBOncQ.png",
            "SQL":
            "http://www.techgirlz.org/wp-content/uploads/2016/10/sql-logo-286x300.png",
            "Swift":
            "https://upload.wikimedia.org/wikipedia/fr/6/63/Logo_Apple_Swift.png",
            "Vim":
            "http://www.unixstickers.com/image/data/stickers/vim/vim.sh.png"
        }

        # Languages files extensions
        # https://fileinfo.com/filetypes/developer
        # https://www.wikiwand.com/en/List_of_file_formats
        # The first element must be the extension used in the
        # parameter "display-compile-command" for every langauge
        self.languages_files_extensions = {
            "Bash": ("sh",),
            "C": ("c", "h"),
            "C#": ("cs",),
            "C++": ("cc", "cpp", "cp", "cxx", "cbp", "hh", "hpp", "hxx", "inl"),
            "CoffeeScript": ("coffee", "litcoffee"),
            "Crystal": ("cr", "ecr", "slang"),
            "D": ("d",),
            "Elixir": ("exs", "ex"),
            "Erlang": ("erl", "hrl"),
            "F#": ("fs", "fsi", "fsx", ".fsscript"),
            "Go": ("go",),
            "Groovy": ("groovy",),
            "Haskell": ("hs", "has", "lhs", "lit"),
            "Java": ("java", "class", "jar", "war"),
            "JavaScript": ("js",),
            "Lazy K": ("lazy",),
            "Lisp": ("lisp", "lsp", "l", "cl", "fasl"),
            "Lua": ("lua", "luc"),
            "Nim": ("nim",),
            "OCaml": ("ml", "mli"),
            "Pascal": ("pas", "pp", "p", "inc", "tpu"),
            "Perl": ("pl", "pm", "ph", "pod"),
            "PHP": ("php", "php3", "php4", "php5", "phps", "phtml"),
            "Pony": (
                "",
                "pony",
            ),
            "Python": ("py", "pyc", "pyo", "pyd", "pyw", "rpy"),
            "Rill": ("rill",),
            "Ruby": ("rb", "erb", "rbw"),
            "Rust": ("rs", "rlib"),
            "Scala": ("scala", "sc"),
            "SQL": ("sql", "eql"),
            "Swift": ("swift",),
            "Vim": ("vim",)
        }

        self.configuration = {}
        self.load_info()

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
            # Warning: info["template"] is a list but it only contains one element at
            # the moment. So I'm just gonna consider it as a str and not as a list.
            # It may change in the future, I don't know ¯\_(ツ)_/¯
            # Some languages have only one template
            template = info["templates"][0]
            # I don't know why there is a C++ and CPP language, as CPP language seems
            # to be exactly the same that C++ (with only 2 compilers which can be
            # already found in C++ language). So I'm just gonna ignore that.
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
                # I don't know what "provider" means but as this attribute is always
                # equal to 0, I'm just gonna ignore it.
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
                    language = result[language_begin + len("margin:0\">"):
                                      language_end]
                    delimiter = url.rfind("/")
                    url = url[:delimiter] + "/raw" + url[delimiter:]
                    async with self.bot.session.get(url) as response:
                        code = await response.text()
                else:
                    code = result
                return (code, language)

    async def add_long_field(self, embed: discord.Embed, parameter_name: str,
                             result: dict, field_name: str):
        """Adds a long field to the embed. Link a pastebin in case the field value is too long"""
        if parameter_name in result:
            if len(result[parameter_name]
                  ) > 1022 or result[parameter_name].count("\n") > 20:
                url = await self.create_pastebin(field_name,
                                                 result[parameter_name])
                delimiter = url.rfind("/")
                url = url[:delimiter] + "/raw" + url[delimiter:]
                embed.add_field(
                    name=field_name,
                    value=":page_facing_up: [" + field_name + ".txt](" + url +
                    ")",
                    inline=False)
            else:
                embed.add_field(
                    name=field_name,
                    value="`" + result[parameter_name] + "`",
                    inline=False)

    async def create_embed_result(self, ctx, language: str, template_used: str,
                                  engine_used: str, command_options: str,
                                  info: dict):
        # Returns an embed corresponding to the Wandbox comile result passed
        # field amount = 25, title/field name = 256, value = 1024, footer text/description = 2048
        # Note that the sum of all characters in the embed should be less than or equal to 6000.
        embed = discord.Embed()
        embed.title = "Results"
        embed.url = info["url"]
        timestamp = ctx.message.timestamp
        timestamp += -1 * get_localzone().utcoffset(timestamp)
        embed.timestamp = timestamp
        embed.add_field(name="Engine used", value=engine_used, inline=True)
        embed.add_field(
            name="Command used",
            value=self.configuration[language][template_used][engine_used]
            ["display-compile-command"] + " " + command_options,
            inline=True)
        if "compiler_error" in info or "program_error" in info:
            if "status" not in info or info["status"] != '0':
                embed.colour = discord.Color.red()
            else:
                embed.colour = discord.Color.orange()
        elif info["status"] != '0':
            embed.colour = discord.Color.orange()
        else:
            embed.colour = discord.Color.green()
        embed.set_footer(
            text="Requested by " + ctx.message.author.name + "#" +
            ctx.message.author.discriminator,
            icon_url=ctx.message.author.avatar_url)
        embed.set_thumbnail(url=self.languages_images[language])
        embed.set_author(
            name=self.bot.user.name + "#" + self.bot.user.discriminator,
            icon_url=self.bot.user.avatar_url)

        remaining_space = 6000 - \
            (30 + len(ctx.message.author.name) + len(self.bot.user.name))

        if "status" in info:
            embed.add_field(
                name="Exit status", value=info["status"], inline=False)
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

    @commands.command(pass_context=True)
    async def code(self, ctx, *, code):
        """
        You can provide your code in two different ways:
            - You can directly use Markdown syntax with your language identifier (use the list_identifiers to list all the languages identifiers).
            - Submit the pastebin link to your code. (Specify the syntax highlighting) --> Use the parameter "code".

        If you want to explicitly specify your programming language, use the parameter "language".
        Indeed, if you have several files and if this parameter is not specified, the programming language is deduced from the files extensions provided (see the list_extensions command).

        If your program has to interact with the user with user inputs, you can specify these inputs using the parameter "input".
        Each line of this parameter value corresponds to an user input.

        If your program is sectioned into several files, you can provide provide them using the "code" parameter.
        The content of each files must be hosted on pastebin.
        The first line corresponds to the "main" file, and will have a fixed name (see the list_main_file_names command to get these names).
        Each following lines is composed of 2 elements: the file name and the pastebin link to the file content, respectively.

        If you want to explicitly specify an engine for running your code, you can use the "engine" parameter.
        You can list all the available engines by using the list_engines command.

        You can add compilation / runtime options by using the parameters "compiler-options" and "runtime-options".

        The values of the parameters "code" and "input" must be surrounded by the character `.

        The bot supports 32 programming languages, which can be listed using the list_languages command.

        See more info and examples here: https://github.com/Beafantles/Discode#how-to-use-the-bot + https://www.youtube.com/watch?v=6CVZJft65RI
        """
        try:
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
                language_extension = code[
                    begin + 3:code[begin + 3:].find("\n") + begin + 3]
                no_code = False
                try:
                    end = code[begin + 3 + len(language_extension):].rfind(
                        "```")
                except IndexError:
                    no_code = True
                if begin == -1 or end == -1:
                    no_code = True
                if no_code:
                    await self.bot.say(
                        "Incorrect syntax, please use Markdown's syntax for your code."
                    )
                    return
                for language in self.languages_identifiers:
                    if language_extension in self.languages_identifiers[
                            language]:
                        code_language = language
                        break
                if not code_language:
                    await self.bot.say(
                        "Incorrect language identifier for your code.\nTo list all the supported languages identifiers, please use `"
                        + self.bot.prefix + "list_identifiers`.")
                before = code[:begin]
                after = code[end + begin + 6 + len(language_extension):]
                lines = ((before[:-1]
                          if before else "") + (after[1:]
                                                if after else "")).split("\n")
                if len(lines) == 1 and lines[0] == '':
                    lines = []
                code = code[begin + 3 + len(language_extension):
                            end + begin + 3 + len(language_extension)]
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
                        "input", "language"
                ]:
                    await self.bot.say(
                        "Invalid parameter `" + parameter_name +
                        "`.\nCheck out available parameters by typing `" + self.
                        bot.prefix + "help code`.\nIgnoring this parameter.")
                else:
                    if parameter_name == "input":
                        begin = line.find("`")
                        if begin == -1:
                            await self.bot.say(
                                "Invalid input parameter format.\nCheck out input format by typing `"
                                + self.bot.prefix + "help code`.")
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
                            await self.bot.say(
                                "Invalid input parameter format.\nCheck out input format by typing `"
                                + self.bot.prefix + "help code`.")
                            return
                    elif parameter_name == "code":
                        begin = line.find("`")
                        if begin == -1:
                            await self.bot.say(
                                "Invalid code parameter format.\nCheck out code format by typing `"
                                + self.bot.prefix + "help code`.")
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
                            await self.bot.say(
                                "Invalid code parameter format.\nCheck out code format by typing `"
                                + self.bot.prefix + "help code`.")
                            return
                        new_value = []
                        supposed_languages = {}
                        first = True
                        first_code = None
                        for line in parameter_value:
                            if first:
                                if not line.startswith("https://pastebin.com/"):
                                    await self.bot.say(
                                        "Incorrect link for the first file.\nThe link must be an url from pastebin."
                                    )
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
                                await self.bot.say(
                                    "Invalid code parameter format.\nCheck out code format by typing `"
                                    + self.bot.prefix + "help code`.")
                                return
                            file_name = line[:delimiter]
                            file_link = line[delimiter + 1:]
                            file_code = None
                            if not file_link.startswith(
                                    "https://pastebin.com/"):
                                await self.bot.say(
                                    "Incorrect link for the file `" + file_name +
                                    "`.\nThe link must be an url from pastebin."
                                )
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
                                    await self.bot.say(
                                        "Invalid file name format.\nThere is no file extension.\nCheck out code format by typing `"
                                        + self.bot.prefix + "help code`.")
                                    return
                                file_extension = file_name[
                                    extension_delimiter + 1:]
                                for language in self.languages_files_extensions:
                                    if file_extension.lower(
                                    ) in self.languages_files_extensions[
                                            language]:
                                        if language in supposed_languages:
                                            supposed_languages[language] += 1
                                        else:
                                            supposed_languages[language] = 1
                            new_value.append({
                                "file": file_name,
                                "code": file_code
                            })
                        if supposed_languages:
                            supposed_language = sorted(
                                supposed_languages.items(),
                                key=lambda x: x[1],
                                reverse=True)[0][0]
                        parameter_value = first_code
                        parameters["codes"] = new_value
                    elif parameter_name == "language":
                        delimiter = line.find(" ")
                        if delimiter == -1:
                            await self.bot.say(
                                "Please specify a code language.\nCheck out code format by typing `"
                                + self.bot.prefix + "help code`.")
                            return
                        language_name = line[delimiter + 1:]
                        correct_language = False
                        for language in self.configuration:
                            if language.upper() == language_name.upper():
                                correct_language = True
                                code_language = language
                                break
                        if not correct_language:
                            await self.bot.say(
                                "`" + language_name +
                                "` is not a correct language name / isn't available for the bot.\nTo list all the available languages, please use `"
                                + self.bot.prefix + "list_languages`.")
                            return
                        parameter_value = code_language
                    else:
                        parameter_value = line[line.find(" ") + 1:]
                    if parameter_name in parameters:
                        await self.bot.say("The parameter `" + parameter_name +
                                           "` is already provided.")
                        return
                    parameters[parameter_name] = parameter_value
                i += 1
            if "code" not in parameters:
                await self.bot.say("Please provide the code!")
                return
            if not code_language:
                if not supposed_language:
                    await self.bot.say(
                        "Couldn't guess which language to use.\nPlease specify it with `language` parameter.\nCheck out `"
                        + self.bot.prefix + "help code` for more info.")
                    return
                else:
                    code_language = supposed_language
                    await self.bot.say(
                        code_language +
                        " was supposed according to your files names.\nTo specify it explicity, please use `language` parameter.\nCheck out `"
                        + self.bot.prefix + "help code` for more info.")
            engine_template_used = None
            if "engine" in parameters:
                correct_engine = False
                for engine_template in self.configuration[code_language]:
                    for engine in self.configuration[code_language][
                            engine_template]:
                        if parameters["engine"].lower() == engine.lower():
                            correct_engine = True
                            engine_template_used = engine_template
                            break
                    if correct_engine:
                        break
                if not correct_engine:
                    await self.bot.say(
                        "`" + parameters["engine"] +
                        "` is not a correct engine for " + code_language +
                        " / isn't available for the bot.\nTo list all the available engine for "
                        + code_language + ", please use `" + self.bot.prefix +
                        "list_engines " + code_language + "`")
                    return
            else:
                engine_template_used = self.default_engines[code_language][0]
                parameters["engine"] = self.default_engines[code_language][1]
            if "compiler-options" in parameters and not self.configuration[code_language][engine_template_used][parameters["engine"]]["compiler-option-raw"]:
                await self.bot.say(
                    "There is no options available for compilation using `" +
                    parameters["engine"] + "`.\nIgnoring these options.")
                del parameters["compiler-options"]
            if "runtime-options" in parameters and not self.configuration[code_language][engine_template_used][parameters["engine"]]["runtime-option-raw"]:
                await self.bot.say(
                    "There is no options available for runtime execution using `"
                    + parameters["engine"] + "`.\nIgnoring these options.")
                del parameters["runtime-options"]
            request = {
                "code":
                parameters["code"],
                "codes":
                parameters["codes"] if "codes" in parameters else [],
                "compiler":
                parameters["engine"],
                "save":
                True,
                "stdin":
                parameters["input"] if "input" in parameters else "",
                "compiler-option-raw":
                parameters["compiler-options"]
                if "compiler-options" in parameters else "",
                "runtime-option-raw":
                parameters["runtime-options"]
                if "runtime-options" in parameters else ""
            }
            result = await self.post_fetch(
                "https://wandbox.org/api/compile.json", request)
            embed = await self.create_embed_result(
                ctx, code_language, engine_template_used, parameters["engine"],
                (parameters["compiler-options"]
                 if "compiler-options" in parameters else "") +
                (parameters["runtime-options"]
                 if "runtime-options" in parameters else ""), result)
            await self.bot.say(embed=embed)
        except Exception as e:
            traceback.print_exc(file=sys.stdout)
            await self.bot.say(str(e))

    @commands.command(pass_context=True)
    async def list_languages(self, ctx):
        """Lists all the available languages for this module"""
        msg = "```Markdown\nAvailable languages\n===================\n\n"
        for i, language in enumerate(sorted(self.configuration)):
            msg += "[" + str(i + 1) + "](" + language + ")\n"
        msg += "```"
        await self.bot.say(msg)

    @commands.command(pass_context=True)
    async def list_engines(self, ctx, *, language_name):
        """Lists all available compilers / interpreters for a language"""
        msg = "```Markdown\nAvailable engines\n=================\n\n"
        language_name = language_name.upper()
        for language in self.configuration:
            if language.upper() == language_name:
                i = 1
                nb_templates = len(self.configuration[language])
                for template in self.configuration[language]:
                    # In case there are several templates, group the different engines in them
                    if nb_templates != 1:
                        msg += "<" + template + ">\n"
                    for engine in self.configuration[language][template]:
                        msg += "[" + str(i) + "](" + engine + ")\n"
                        i += 1
                    if nb_templates != 1:
                        msg += "\n"
                msg += "```"
                await self.bot.say(msg)
                return
        await self.bot.say(
            "There is no such available language.\nTo list all the available languages, please use `"
            + self.bot.prefix + "list_languages`.")

    @commands.command(pass_context=True)
    async def list_identifiers(self, ctx):
        """Lists all the languages identifiers recognized by Discord / the bot"""
        msg = "```Markdown\nLanguages identifiers\n=====================\n\n"
        for language in self.languages_identifiers:
            msg += "- " + language + (" " * (18 - len(language))) + "--> " + \
                " / ".join(self.languages_identifiers[language]) + "\n"
        msg += "```"
        await self.bot.say(msg)

    @commands.command(pass_context=True)
    async def list_extensions(self, ctx):
        """Lists all the languages files extensions recognized by the bot"""
        msg = "```Markdown\nLanguages files extensions\n=====================\n\n"
        for language in self.languages_files_extensions:
            msg += "- " + language + (" " * (18 - len(language))) + "--> ." + \
                " / .".join(self.languages_files_extensions[language]) + "\n"
        msg += "```"
        await self.bot.say(msg)

    @commands.command(pass_context=True)
    async def list_main_file_names(self, ctx):
        """Lists the main files names for the different languages"""
        msg = "```Markdown\nMain files names\n=====================\n\n"
        for language in self.languages_files_extensions:
            extension = self.languages_files_extensions[language][0]
            msg += "- " + language + (" " * (18 - len(language))) + "--> prog" + \
                ("." if extension != "" else "") + extension + "\n"
        msg += "```"
        await self.bot.say(msg)


def setup(bot):
    bot.add_cog(Code(bot))
