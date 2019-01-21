from discord.ext import commands


def is_owner():
    """Checks if it's the owner or not"""
    return commands.is_owner()
