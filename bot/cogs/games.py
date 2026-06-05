import discord
from discord.ext import commands
from datetime import datetime, timezone
import random
import asyncio
from bot import database as db

MAX_ATTEMPTS_PER_DAY = 20
WIN_REWARD = 10
GAME_COST = 4


def today() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%d")


async def check_attempts(ctx) -> bool:
    attempts = await db.get_game_attempts(str(ctx.author.id), str(ctx.guild.id), today())
    if attempts >= MAX_ATTEMPTS_PER_DAY:
        embed = discord.Embed(
            title="⛔ Limite diário atingido!",
            description=f"Você usou todas as **{MAX_ATTEMPTS_PER_DAY} tentativas** de hoje.\nVolte amanhã!",
            color=discord.Color.red()
        )
        await ctx.send(embed=embed)
        return False
    remaining = MAX_ATTEMPTS_PER_DAY - attempts - 1
    return remaining


async def charge_and_check(ctx) -> bool:
    coins = await db.get_coins(str(ctx.author.id), str(ctx.guild.id))
    if coins < GAME_COST:
        await ctx.send(f"❌ Você precisa de **{GAME_COST} 🪙** para jogar. Seu saldo: **{coins} 🪙**.\nUse `!daily` para ganhar moedas!")
        return False
    await db.add_coins(str(ctx.author.id), str(ctx.guild.id), -GAME_COST)
    return True


class Games(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    async def _handle_win(self, ctx, game_name: str, extra: str = ""):
        await db.add_coins(str(ctx.author.id), str(ctx.guild.id), WIN_REWARD)
        coins = await db.get_coins(str(ctx.author.id), str(ctx.guild.id))
        remaining = MAX_ATTEMPTS_PER_DAY - await db.get_game_attempts(str(ctx.author.id), str(ctx.guild.id), today())
        net = WIN_REWARD - GAME_COST
        embed = discord.Embed(
            title=f"🎉 Você ganhou — {game_name}!",
            description=extra,
            color=discord.Color.green()
        )
        embed.add_field(name="🪙 Ganho líquido", value=f"+{net} moedas (+{WIN_REWARD} - {GAME_COST} custo)", inline=True)
        embed.add_field(name="💰 Saldo", value=f"{coins} 🪙", inline=True)
        embed.add_field(name="🎮 Tentativas restantes hoje", value=str(remaining), inline=True)
        return embed

    async def _handle_loss(self, ctx, game_name: str, extra: str = "", penalty: int = None):
        if penalty is None:
            penalty = WIN_REWARD
        await db.add_coins(str(ctx.author.id), str(ctx.guild.id), -penalty)
        coins = await db.get_coins(str(ctx.author.id), str(ctx.guild.id))
        remaining = MAX_ATTEMPTS_PER_DAY - await db.get_game_attempts(str(ctx.author.id), str(ctx.guild.id), today())
        total_lost = GAME_COST + penalty
        embed = discord.Embed(
            title=f"😢 Você perdeu — {game_name}",
            description=extra,
            color=discord.Color.red()
        )
        embed.add_field(name="💸 Total perdido", value=f"-{total_lost} moedas ({GAME_COST} custo + {penalty} penalidade)", inline=False)
        embed.add_field(name="💰 Saldo", value=f"{coins} 🪙", inline=True)
        embed.add_field(name="🎮 Tentativas restantes hoje", value=str(remaining), inline=True)
        return embed

    @commands.command(name="coinflip", aliases=["cf", "moeda"], help="Aposte cara ou coroa! Uso: !coinflip cara/coroa")
    @commands.guild_only()
    async def coinflip(self, ctx, choice: str = None):
        if not choice:
            return await ctx.send(f"❌ Escolha `cara` ou `coroa`. Ex: `!coinflip cara`\n💸 Custo: **{GAME_COST} 🪙** por jogo.")

        choice = choice.lower()
        valid = {"cara": "cara", "coroa": "coroa", "heads": "cara", "tails": "coroa", "c": "cara", "k": "coroa"}
        if choice not in valid:
            return await ctx.send("❌ Escolha `cara` ou `coroa`.")

        remaining = await check_attempts(ctx)
        if remaining is False:
            return
        if not await charge_and_check(ctx):
            return
        await db.increment_game_attempts(str(ctx.author.id), str(ctx.guild.id), today())

        result = random.choice(["cara", "coroa"])
        emoji = "👑" if result == "cara" else "🔵"
        player_choice = valid[choice]

        if player_choice == result:
            embed = await self._handle_win(ctx, "Coinflip", f"{emoji} Saiu **{result}**! Você acertou!")
        else:
            embed = await self._handle_loss(ctx, "Coinflip", f"{emoji} Saiu **{result}**! Você escolheu **{player_choice}**.")
        await ctx.send(embed=embed)

    @commands.command(name="adivinhar", aliases=["guess", "numero"], help="Adivinhe o número de 1 a 10! Uso: !adivinhar <número>")
    @commands.guild_only()
    async def guess(self, ctx, number: int = None):
        if number is None or not (1 <= number <= 10):
            return await ctx.send(f"❌ Escolha um número de **1 a 10**. Ex: `!adivinhar 7`\n💸 Custo: **{GAME_COST} 🪙** por jogo.")

        remaining = await check_attempts(ctx)
        if remaining is False:
            return
        if not await charge_and_check(ctx):
            return
        await db.increment_game_attempts(str(ctx.author.id), str(ctx.guild.id), today())

        secret = random.randint(1, 10)
        if number == secret:
            embed = await self._handle_win(ctx, "Adivinhe o Número", f"🎯 O número era **{secret}**! Você acertou!")
        else:
            hint = "maior" if secret > number else "menor"
            embed = await self._handle_loss(ctx, "Adivinhe o Número", f"❌ O número era **{secret}** (era {hint} que {number}).")
        await ctx.send(embed=embed)

    @commands.command(name="pedrapapeltesoura", aliases=["rps", "jokenpo"], help="Pedra, Papel ou Tesoura! Uso: !rps pedra/papel/tesoura")
    @commands.guild_only()
    async def rps(self, ctx, choice: str = None):
        options = {"pedra": "🪨", "papel": "📄", "tesoura": "✂️", "p": "🪨", "pa": "📄", "t": "✂️",
                   "rock": "🪨", "paper": "📄", "scissors": "✂️"}
        names = {"pedra": "pedra", "papel": "papel", "tesoura": "tesoura",
                 "p": "pedra", "pa": "papel", "t": "tesoura",
                 "rock": "pedra", "paper": "papel", "scissors": "tesoura"}

        if not choice or choice.lower() not in options:
            return await ctx.send(f"❌ Escolha: `pedra`, `papel` ou `tesoura`\n💸 Custo: **{GAME_COST} 🪙** por jogo.")

        remaining = await check_attempts(ctx)
        if remaining is False:
            return
        if not await charge_and_check(ctx):
            return
        await db.increment_game_attempts(str(ctx.author.id), str(ctx.guild.id), today())

        player = names[choice.lower()]
        bot_choice = random.choice(["pedra", "papel", "tesoura"])
        emojis = {"pedra": "🪨", "papel": "📄", "tesoura": "✂️"}

        wins = {"pedra": "tesoura", "tesoura": "papel", "papel": "pedra"}
        result_line = f"{emojis[player]} **{player}** vs {emojis[bot_choice]} **{bot_choice}**"

        if player == bot_choice:
            coins = await db.get_coins(str(ctx.author.id), str(ctx.guild.id))
            remaining_now = MAX_ATTEMPTS_PER_DAY - await db.get_game_attempts(str(ctx.author.id), str(ctx.guild.id), today())
            embed = discord.Embed(title="🤝 Empate!", description=result_line, color=discord.Color.yellow())
            embed.add_field(name="💸 Custo", value=f"-{GAME_COST} moedas", inline=True)
            embed.add_field(name="💰 Saldo", value=f"{coins} 🪙", inline=True)
            embed.add_field(name="🎮 Tentativas restantes", value=str(remaining_now), inline=True)
        elif wins[player] == bot_choice:
            embed = await self._handle_win(ctx, "Pedra Papel Tesoura", result_line)
        else:
            embed = await self._handle_loss(ctx, "Pedra Papel Tesoura", result_line)

        await ctx.send(embed=embed)

    @commands.command(name="slots", help="Gire os slots! Uso: !slots")
    @commands.guild_only()
    async def slots(self, ctx):
        remaining = await check_attempts(ctx)
        if remaining is False:
            return
        if not await charge_and_check(ctx):
            return
        await db.increment_game_attempts(str(ctx.author.id), str(ctx.guild.id), today())

        symbols = ["🍒", "🍋", "🍊", "🍇", "⭐", "💎", "🔔"]
        weights = [30, 25, 20, 15, 6, 2, 2]

        reels = random.choices(symbols, weights=weights, k=3)
        display = f"| {reels[0]} | {reels[1]} | {reels[2]} |"

        msg = await ctx.send(f"🎰 Girando...\n`| ❓ | ❓ | ❓ |`")
        await asyncio.sleep(1)
        await msg.edit(content=f"🎰 Girando...\n`| {reels[0]} | ❓ | ❓ |`")
        await asyncio.sleep(0.8)
        await msg.edit(content=f"🎰 Girando...\n`| {reels[0]} | {reels[1]} | ❓ |`")
        await asyncio.sleep(0.8)

        if reels[0] == reels[1] == reels[2]:
            multiplier = 5 if reels[0] == "💎" else 3 if reels[0] == "⭐" else 2
            reward = WIN_REWARD * multiplier
            await db.add_coins(str(ctx.author.id), str(ctx.guild.id), reward)
            coins = await db.get_coins(str(ctx.author.id), str(ctx.guild.id))
            net = reward - GAME_COST
            embed = discord.Embed(
                title=f"🎰 JACKPOT! {display}",
                description=f"**TRÊS IGUAIS!** Multiplicador x{multiplier}!",
                color=discord.Color.gold()
            )
            embed.add_field(name="🪙 Ganho líquido", value=f"+{net} moedas (+{reward} - {GAME_COST} custo)", inline=True)
            embed.add_field(name="💰 Saldo", value=f"{coins} 🪙", inline=True)
        elif reels[0] == reels[1] or reels[1] == reels[2] or reels[0] == reels[2]:
            await db.add_coins(str(ctx.author.id), str(ctx.guild.id), WIN_REWARD)
            coins = await db.get_coins(str(ctx.author.id), str(ctx.guild.id))
            net = WIN_REWARD - GAME_COST
            embed = discord.Embed(
                title=f"🎰 Par! {display}",
                description="Dois iguais — você ganhou!",
                color=discord.Color.green()
            )
            embed.add_field(name="🪙 Ganho líquido", value=f"+{net} moedas (+{WIN_REWARD} - {GAME_COST} custo)", inline=True)
            embed.add_field(name="💰 Saldo", value=f"{coins} 🪙", inline=True)
        else:
            await db.add_coins(str(ctx.author.id), str(ctx.guild.id), -WIN_REWARD)
            coins = await db.get_coins(str(ctx.author.id), str(ctx.guild.id))
            remaining_now = MAX_ATTEMPTS_PER_DAY - await db.get_game_attempts(str(ctx.author.id), str(ctx.guild.id), today())
            total_lost = GAME_COST + WIN_REWARD
            embed = discord.Embed(
                title=f"🎰 {display}",
                description="Sem sorte dessa vez!",
                color=discord.Color.red()
            )
            embed.add_field(name="💸 Total perdido", value=f"-{total_lost} moedas ({GAME_COST} custo + {WIN_REWARD} penalidade)", inline=False)
            embed.add_field(name="💰 Saldo", value=f"{coins} 🪙", inline=True)
            embed.add_field(name="🎮 Tentativas restantes", value=str(remaining_now), inline=True)

        await msg.delete()
        await ctx.send(embed=embed)

    @commands.command(name="tentativas", aliases=["attempts"], help="Veja suas tentativas de jogo restantes.")
    @commands.guild_only()
    async def attempts(self, ctx):
        used = await db.get_game_attempts(str(ctx.author.id), str(ctx.guild.id), today())
        remaining = MAX_ATTEMPTS_PER_DAY - used
        coins = await db.get_coins(str(ctx.author.id), str(ctx.guild.id))

        embed = discord.Embed(
            title="🎮 Tentativas de Jogo",
            color=discord.Color.blurple()
        )
        embed.add_field(name="✅ Restantes hoje", value=f"**{remaining}/{MAX_ATTEMPTS_PER_DAY}**", inline=True)
        embed.add_field(name="❌ Usadas", value=str(used), inline=True)
        embed.add_field(name="💸 Custo por jogo", value=f"{GAME_COST} 🪙", inline=True)
        embed.add_field(name="💰 Seu saldo", value=f"{coins} 🪙", inline=True)
        embed.set_footer(text="Recarrega toda meia-noite (UTC)!")
        await ctx.send(embed=embed)

    @coinflip.error
    @guess.error
    @rps.error
    @slots.error
    async def game_error(self, ctx, error):
        if isinstance(error, commands.BadArgument):
            await ctx.send(f"❌ Argumento inválido. Use `!help {ctx.command}`.")
        else:
            await ctx.send(f"❌ Erro: {error}")


async def setup(bot):
    await bot.add_cog(Games(bot))
