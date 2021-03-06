## Env ##
import PointsSystem
import discord
from discord.ext import commands
import asyncio
from helpers import *
import os
import re
import aiohttp
from dotenv import load_dotenv
os.system("")
load_dotenv()

client = commands.Bot(command_prefix=os.getenv("PREFIX"), intents=discord.Intents.all())
PointsSystem = PointsSystem.Points(client)

@client.event
async def on_ready():
    print(f"{OKCYAN}Ready as {str(client.user)}")
    print(f"Invite link:{ENDC} {UNDERLINE}https://discord.com/oauth2/authorize?client_id={client.user.id}&scope=bot&permissions=8{ENDC}\n")
    PointsSystem.cleanse_data()
    print(f"{OKGREEN}Cleansed all data!{ENDC}")

    client.channels = [int(channel.strip()) for channel in os.getenv("CHANNEL_IDS").split(",")]
    client.color = int(os.getenv("EMBED_COLOR"))
    client.default_points = int(os.getenv("DEFAULT_POINTS"))
    client.only_images = True if os.getenv("ONLY_IMAGES").lower() == "true" else False

    client.twitter_state = True if os.getenv("TWITTER_STATE").lower() == "true" else False
    client.twitter_channels = None
    client.twitter_handle = None 

    client.log_channel = client.get_channel(int(os.getenv("LOGS_CHANNEL_ID")))

    if client.twitter_state:
        client.twitter_channels = [int(channel.strip()) for channel in os.getenv("TWITTER_CHANNEL_IDS").split(",")]
        client.twitter_points = int(os.getenv("TWITTER_POINTS"))
        client.twitter_handle = os.getenv("TWITTER_HANDLE").lower()
        if "@" in client.twitter_handle:
            client.twitter_handle = client.twitter_handle.replace('@', '')
        
@client.event
async def on_member_remove(member):
    PointsSystem.remove_user(member)

async def log(message:str):
    print(YELLOW + message + ENDC)
    await client.log_channel.send(embed=discord.Embed(color=client.color, description=f"{pencil} {message}"))

@client.event
async def on_message(message):
    if client.is_ready() and message.guild is not None:
        amount = 0

        # Default Channel Points
        if message.channel.id in client.channels:
            
            if client.only_images:
                if message.attachments:
                    amount = client.default_points * len(message.attachments)

            else:
                amount = client.default_points
                
        # Twitter Points
        if client.twitter_state and client.twitter_channels and client.twitter_handle and message.channel.id in client.twitter_channels:

            async with aiohttp.ClientSession() as session:
                for link in re.findall(r"twitter\.com\/.+?\/status\/\d+", message.content):

                    async with session.get("https://" + link,headers={'user-agent':"Mozilla/5.0 (compatible; Discordbot/2.0; +https://discordapp.com)"}) as resp:
                        
                        if resp.status == 200:
                            tweet_content = (await resp.text()).split('og:description" content="???')[1].split('???">')[0]
                            if "@" + client.twitter_handle in tweet_content.lower():
                                amount += client.twitter_points

        if amount != 0:
            PointsSystem.add_points(message.author, amount)
            await log(f"Added {amount} point{'s' if amount != 1 else ''} to {str(message.author)} ({message.author.mention})")
            await message.add_reaction(check_mark_unicode)

    await client.process_commands(message)


@client.command()
@commands.check(is_admin)
async def add(ctx, member: discord.Member, amount: int = 1):
    PointsSystem.add_points(member, amount)
    await ctx.send(content=f"{check_mark} Successfully added {amount} points!", embed=PointsSystem.member_embed(member))


@client.command()
@commands.check(is_admin)
async def remove(ctx, member: discord.Member, amount: int = 1):
    PointsSystem.remove_points(member, amount)
    await ctx.send(content=f"{check_mark} Successfully removed {amount} points!", embed=PointsSystem.member_embed(member))


@client.command()
@commands.check(is_admin)
async def reset(ctx):
    await ctx.send(embed=discord.Embed(color=client.color, description=":warning: Are you sure you want to reset all information related to your server?"))

    try:
        answer = await client.wait_for('message', check=lambda m: m.channel == ctx.channel and m.author.id == ctx.author.id, timeout=10)
    except asyncio.TimeoutError:
        return await ctx.send(embed=discord.Embed(color=client.color, description=f"{x_mark} You took too long to answer!!"))

    if answer.content.lower() == "yes":
        PointsSystem.reset_guild(ctx.guild)
        return await ctx.send(embed=discord.Embed(color=client.color, description=f"{check_mark} Successfully reset your server!"))

    return await ctx.send(embed=discord.Embed(color=client.color, description=f"{check_mark} Successfully cancelled the reset!"))


@client.command()
@commands.check(is_admin)
async def raffle(ctx, count:int, *, itemName:str):
    for _ in range(count):
        winner = PointsSystem.random_raffle(ctx.guild)
        if winner is None:
            await ctx.send(embed=discord.Embed(color=client.color, description=f"{x_mark} Couldn't determine a winner for {itemName}!"))
            continue

        await ctx.send(embed=discord.Embed(color=client.color, description=f"{popper} {winner.mention} has won {itemName}!"))


@client.command()
async def points(ctx, member: discord.Member = None):
    return await ctx.send(embed=PointsSystem.member_embed(member if member else ctx.author))


@client.command()
async def leaderboard(ctx):
    return await ctx.send(embed=PointsSystem.get_leaderboard(ctx.author))


@client.event
async def on_command_error(ctx, error):
    if isinstance(error, commands.CommandNotFound):
        return

    elif isinstance(error, commands.CommandOnCooldown):
        embed = discord.Embed(
            description=f"{x_mark} Slow down {ctx.author.name}! Please try again in {error.retry_after:.2f}s", color=client.color)
        await ctx.send(embed=embed)

    elif isinstance(error, commands.MissingRequiredArgument) or isinstance(error, commands.BadArgument):
        await ctx.send_help(ctx.command)

    elif isinstance(error, commands.CheckFailure):
        embed = discord.Embed(
            color=13840175, description=f"{x_mark} Not allowed!")
        await ctx.send(embed=embed)

    else:
        raise error


client.run(os.getenv("TOKEN"))
