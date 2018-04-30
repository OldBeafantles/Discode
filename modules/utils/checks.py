from discord.ext import commands


def is_owner_check(ctx):
    """Checks if it's the owner or not"""
    return ctx.bot.owner_id == ctx.message.author.id


def is_owner():
    """Checks if it's the owner or not"""
    return commands.check(is_owner_check)
