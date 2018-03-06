# Discode

Discode is a Discord bot that runs code.
It has been originally written for C++ support and it will remain the priority.

## Why?

I spend a lot of time on Discord and I hang out in several programming related servers. It's quite common place to see people asking for help about their code but it's sometimes hard to help out them since :

- "Sorry, I'm on mobile, I can't help you at the moment, I'll do it later."
- "I don't have your configuration for running your code so I can't really figure out what's your problem since I would get different results from you."

Also, this can be useful when we want to give examples and get instant, nice looking and embedded results within Discord, without any tool at hand.

## How does it work?

Discode is written in Python, using [discord.py](https://github.com/Rapptz/discord.py) library for interacting with Discord, [wandbox](https://wandbox.org/)'s API for running codes and [pastebin](https://pastebin.com/) for long codes / results.
I may switch from wandbox to [godbolt](https://godbolt.org/) when it'll support code execution (see this [issue](https://github.com/mattgodbolt/compiler-explorer/issues/429)), since godbolt provides more compilers and allows to get resulting assembly code. 
For info about using the bot, see [here](#how_to_use_the_bot).

## What does it support?

Discode supports 32 programming languages, listed below:

<details>
<summary>Show supported languages</summary>

- Bash script
- C
- C#
- C++
- CoffeeScript
- Crystal
- D
- Elixir
- Erlang
- F#
- Go
- Groovy
- Haskell
- Java
- Javascript
- Lazy K
- Lisp
- Lua
- Nim
- OCaml
- PHP
- Pascal
- Perl
- Pony
- Python
- Rill
- Ruby
- Rust
- SQL
- Scala
- Swift
- Vim script

</details>
<br>

You can list these languages using the `[p]list_languages` command.

Moreover, it also provides:

- Multi code files support
- Multiple compilers / interpreters
- Code from pastebin
- Compiler options (compiler flags)
- Runtime options (program parameters)
- User input

## Installing & Running

To be done.

## How to use the bot? <a id="how_to_use_the_bot">

At the momment, the bot is based on an unique command, called `code`. However, this command may appears complex at first glance.

### Basic use

The most basic way to use the bot is to directly provide code using Markdown syntax.

#### Example

```cpp
[p]code ```cpp
#include <iostream>

int main()
{
    std::cout << "Hello world!\n";
    return 0;
}```
```
where `[p]` is the bot prefix (in the picture below, the prefix is `>`).

`cpp` is a *Markdown identifier*, meaning that the following code must be identified as C++. This identifier is also used for the bot to know which language to use for evaluating the code. You can use `[p]list_identifiers` to list all the identifiers known by the bot for the different available languages.

#### Result

<details>
<summary>Show result</summary>

![result_basic_usage](https://i.imgur.com/3LWJ13F.png)

</details>

<br>

**Note:**

If your code is too long, you can instead provide a link to your code, uploaded previously on [pastebin](https://pastebin.com/). You then need to specify the parameter `code` when using the command. The link must be surrounded by the character  ``` ` ``` (AltGr + 7 on most azerty keyboards and the key just on the left of the `1` on most qwerty keyboards), as shown below:
```
[p]code
code `https://pastebin.com/pPN736RR`
```
⚠️ **Warning** ⚠️

If your pastebin doesn't have syntax highlighting or if you pass the link to the raw code, you would need to specify the programming language:
```
[p]code
code `https://pastebin.com/cd4gdeiw`
language C++
```

### Handle user input

The parameter `input` interacts directly with your program. As for `code` parameter, the inputs must be surrounded by the character  ``` ` ```. Every line corresponds to a different input. Check out the example if it's not clear.

#### Example

```cpp
[p]code ```cpp
#include <iostream>
#include <string>

int main()
{
	std::string name,
                    passion;
	std::cin >> name;
	std::cin.ignore();
	std::getline(std::cin, passion);
	std::cout << "Your name is " << name << " and you love " << passion << "!\n";
    	return 0;
}```
input `Beafantles
solving puzzles`
```

#### Result

<details>
<summary>Show result</summary>

![result_user_input](https://i.imgur.com/Fh3tVBC.png)
</details>

<br>

**Note:**

If your program asks for user inputs but you don't provide any input, *default* values will be used instead, as shown below:

<details>
<summary>Show</summary>

![result_no_user_input](https://i.imgur.com/WmIXyWv.png)

</details>

### Multi-files handling

You can also provides several files for evaluation. These files must be hosted on [pastebin](https://pastebin.com). You can then provide these files to the bot, using the `code` parameter. The first line of this parameter must be a pastebin link. Then, every line must be a pair of 2 elements : the file name and the pastebin link to its content. Actually, the first file has a fixed name, that's why only the pastebin link is required. This name can be retrieved using the `[p]list_main_file_names` command.

#### Example

```cpp
[p]code
code `https://pastebin.com/KLnbHSTD
additional_file.hpp https://pastebin.com/8RvaaFb4`
```

<details>
<summary>First file (https://pastebin.com/KLnbHSTD) - prog.cc</summary>

```cpp
#include <iostream>
#include "additional_file.hpp"

int main()
{
    std::cout << "File name: " << __FILE__ << "\n"
              << "a = " << a << "\n";
	return 0;
}
```
</details>

<details>
<summary>Second file (https://pastebin.com/8RvaaFb4) - additional_file.hpp</summary>

```cpp
int a = 1337;
```
</details>

#### Result

<details>
<summary>Show result</summary>

![result_multi_files](https://i.imgur.com/LjtbZut.png)
</details>

### Specifying an engine

You may want to set a specific compiler / interpreter for evaluating your code. You can specify it using the `engine` parameter. You can list all available engines for an available language using the `[p]list_engines language_name` command.

#### Example

```py
[p]code ```py
print "Hello world!"```
engine cpython-2.7.3
```

#### Result

<details>
<summary>Show result</summary>

![result_engine](https://i.imgur.com/uKNbk5U.png)
</details>

### Specifying compiler / runtime options

You can also specify options for compilation / execution of your programm, respectively using `compiler-options` and `runtime-options` parameters. Though, such options aren't available for every engines. These options are command-line flags.

#### Example

```cpp
[p]code ```cpp
int main()
{
	int a;
	return 0;
}```
compiler-options -Wall
```

#### Result

<details>
<summary>Show result</summary>

![result_options](https://i.imgur.com/DDHip2r.png)
</details>

## Upcoming features / ideas

⚠️ **I don't work on this project on a regular basis but rather when I want to. Don't expect any precise date for these features / ideas to be released.** ⚠️

- Gist support
- More programming languages support (however, I would appreciate not to use several API for code evaluating)
- Compilation / execution duration (wandbox's API doesn't give these info though...)
- Language reference research
- Beautify codes

## Contributing

Feel free to submit improvments / features / ideas by creating an issue to this project.

If you see any bugs, please create an issue with the details.

If you wanna merge your improvments, please ensure your code respects the google's formatting style by running `beautify.bat` if you're on Windows or `beautify.sh` if you're on Linux. In both cases, you would need to install [yapf](https://github.com/google/yapf).

## Changelog

**06/03/2018** First version of the bot (**1.0.0**)