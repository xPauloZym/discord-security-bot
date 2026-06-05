import discord
from discord.ext import commands
import asyncio
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from bot.config import DISCORD_BOT_TOKEN, BOT_PREFIX
from bot import database as db

intents = discord.Intents.default()
intents.members = True
intents.message_content = True
intents.guilds = True
intents.bans = True


class SecurityBot(commands.Bot):
    def __init__(self):
        super().__init__(
            command_prefix=BOT_PREFIX,
            intents=intents,
            help_command=commands.DefaultHelpCommand(no_category="Commands"),
            description="🛡️ Security & Moderation Bot",
        )

    async def setup_hook(self):
        await db.init_db()
        cogs = [
            "bot.cogs.moderation",
            "bot.cogs.ip_ban",
            "bot.cogs.anti_raid",
            "bot.cogs.economy",
            "bot.cogs.games",
            "bot.cogs.fun",
            "bot.cogs.owner",
            "bot.cogs.xphelp",
            "bot.cogs.battle",
        ]
        for cog in cogs:
            await self.load_extension(cog)
            print(f"✅ Loaded cog: {cog}")

    async def on_ready(self):
        print(f"\n{'='*50}")
        print(f"  🤖 Bot: {self.user} (ID: {self.user.id})")
        print(f"  🏠 Servers: {len(self.guilds)}")
        print(f"  ⚙️  Prefix: {BOT_PREFIX}")
        print(f"  🛡️  Security Bot is ONLINE")
        print(f"{'='*50}\n")

        activity = discord.Activity(
            type=discord.ActivityType.watching,
            name=f"{BOT_PREFIX}help | Protecting the server"
        )
        await self.change_presence(status=discord.Status.online, activity=activity)

    async def on_command_error(self, ctx, error):
        if isinstance(error, commands.CommandNotFound):
            return
        if isinstance(error, commands.NoPrivateMessage):
            return await ctx.send("❌ This command can only be used in a server.")
        if isinstance(error, commands.MissingRequiredArgument):
            await ctx.send(f"❌ Missing argument: `{error.param.name}`. Use `{BOT_PREFIX}help {ctx.command}` for usage.")
        elif isinstance(error, commands.BotMissingPermissions):
            await ctx.send(f"❌ I don't have the required permissions: `{', '.join(error.missing_permissions)}`")


async def main():
    if not DISCORD_BOT_TOKEN:
        print("❌ ERROR: DISCORD_BOT_TOKEN is not set!")
        return

    bot = SecurityBot()

    @bot.command(name="ping", help="Check if the bot is alive.")
    async def ping(ctx):
        latency = round(bot.latency * 1000)
        embed = discord.Embed(
            title="🏓 Pong!",
            description=f"Latency: **{latency}ms**",
            color=discord.Color.green()
        )
        await ctx.send(embed=embed)

    @bot.command(name="botinfo", help="Show bot information.")
    async def botinfo(ctx):
        embed = discord.Embed(
            title="🛡️ Security Bot Info",
            color=discord.Color.blurple()
        )
        embed.add_field(name="Prefix", value=f"`{BOT_PREFIX}`", inline=True)
        embed.add_field(name="Servers", value=str(len(bot.guilds)), inline=True)
        embed.add_field(name="Latency", value=f"{round(bot.latency * 1000)}ms", inline=True)
        embed.add_field(
            name="🛡️ Moderação",
            value=f"`!kick` `!ban` `!tempban` `!unban` `!mute` `!unmute` `!purge`",
            inline=False
        )
        embed.add_field(
            name="🚫 IP Ban",
            value=f"`!ipban` `!ipunban` `!registerip` `!checkip` `!checkuser` `!registeralt`",
            inline=False
        )
        embed.add_field(
            name="🪙 Economia",
            value=f"`!daily` `!saldo` `!loja` `!comprar` `!inventario` `!ranking` `!transferir`",
            inline=False
        )
        embed.add_field(
            name="🎮 Jogos",
            value=f"`!coinflip` `!adivinhar` `!pedrapapeltesoura` `!slots` `!tentativas`",
            inline=False
        )
        embed.add_field(
            name="🎉 Diversão & Itens",
            value=f"`!randomnick` `!bombanick` `!escudo` `!roubar` `!espiar` `!8ball` `!dado` `!piada` `!abraco` `!ship`",
            inline=False
        )
        embed.set_footer(text="🛡️ Protecting your server 24/7 | Use !help <comando> para detalhes")
        await ctx.send(embed=embed)

    async with bot:
        await bot.start(DISCORD_BOT_TOKEN)


if __name__ == "__main__":
    asyncio.run(main())
