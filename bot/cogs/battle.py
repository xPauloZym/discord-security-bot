import discord
from discord.ext import commands
import random
import asyncio
from bot import database as db

BATTLE_REWARD = 20
MAX_HP = 100
BATTLE_TIMEOUT = 30

MOVES = [
    {"name": "Ataque Normal",  "emoji": "⚔️",  "dmg": (10, 20), "hit_chance": 1.0,  "desc": "desfere um golpe rápido"},
    {"name": "Ataque Pesado",  "emoji": "🗡️",  "dmg": (22, 38), "hit_chance": 0.60, "desc": "lança um golpe devastador"},
    {"name": "Magia",          "emoji": "✨",  "dmg": (14, 24), "hit_chance": 0.85, "desc": "conjura um feitiço"},
    {"name": "Chamas",         "emoji": "🔥",  "dmg": (16, 26), "hit_chance": 0.80, "desc": "lança uma bola de fogo"},
    {"name": "Golpe Raio",     "emoji": "⚡",  "dmg": (18, 30), "hit_chance": 0.70, "desc": "invoca um raio"},
    {"name": "Esquiva + Corte","emoji": "💨",  "dmg": (8,  18), "hit_chance": 0.95, "desc": "esquiva e contra-ataca"},
    {"name": "Gelo",           "emoji": "🧊",  "dmg": (12, 22), "hit_chance": 0.90, "desc": "dispara uma lasca de gelo"},
    {"name": "Veneno",         "emoji": "☠️",  "dmg": (10, 20), "hit_chance": 0.85, "desc": "envenena o adversário"},
]


def hp_bar(current: int, maximum: int = MAX_HP) -> str:
    pct = max(0, current) / maximum
    filled = round(pct * 10)
    bar = "█" * filled + "░" * (10 - filled)
    color = "🟢" if pct > 0.6 else "🟡" if pct > 0.3 else "🔴"
    return f"{color} `{bar}` **{max(0, current)}/{maximum}**"


def pick_move() -> dict:
    return random.choice(MOVES)


def apply_move(move: dict) -> tuple[int, bool]:
    hit = random.random() < move["hit_chance"]
    if not hit:
        return 0, False
    dmg = random.randint(*move["dmg"])
    return dmg, True


active_battles: set = set()


class Battle(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(name="lutar", aliases=["batalha", "fight", "duel"], help="Desafie alguém para uma luta! Uso: !lutar @user")
    @commands.guild_only()
    @commands.cooldown(1, 30, commands.BucketType.user)
    async def lutar(self, ctx, opponent: discord.Member):
        challenger = ctx.author

        if opponent == challenger:
            return await ctx.send("❌ Você não pode lutar contra si mesmo!")
        if opponent.bot:
            return await ctx.send("❌ Você não pode lutar contra um bot!")

        if challenger.id in active_battles or opponent.id in active_battles:
            return await ctx.send("❌ Um dos jogadores já está em uma batalha!")

        challenger_coins = await db.get_coins(str(challenger.id), str(ctx.guild.id))
        opponent_coins = await db.get_coins(str(opponent.id), str(ctx.guild.id))
        if challenger_coins < BATTLE_REWARD:
            return await ctx.send(f"❌ Você precisa de pelo menos **{BATTLE_REWARD} 🪙** para lutar. Seu saldo: **{challenger_coins} 🪙**")
        if opponent_coins < BATTLE_REWARD:
            return await ctx.send(f"❌ {opponent.display_name} precisa de pelo menos **{BATTLE_REWARD} 🪙** para lutar. Saldo: **{opponent_coins} 🪙**")

        invite = discord.Embed(
            title="⚔️ Desafio de Batalha!",
            description=(
                f"{challenger.mention} desafiou {opponent.mention} para uma luta!\n\n"
                f"💰 Aposta: **{BATTLE_REWARD} 🪙** do perdedor para o vencedor\n\n"
                f"Reaja com ⚔️ para aceitar ou ❌ para recusar (30s)"
            ),
            color=discord.Color.orange()
        )
        invite_msg = await ctx.send(embed=invite)
        await invite_msg.add_reaction("⚔️")
        await invite_msg.add_reaction("❌")

        def check(reaction, user):
            return (
                user == opponent
                and str(reaction.emoji) in ("⚔️", "❌")
                and reaction.message.id == invite_msg.id
            )

        try:
            reaction, _ = await self.bot.wait_for("reaction_add", timeout=BATTLE_TIMEOUT, check=check)
        except asyncio.TimeoutError:
            await invite_msg.delete()
            return await ctx.send(f"⏰ {opponent.display_name} não respondeu a tempo. Batalha cancelada.")

        await invite_msg.delete()

        if str(reaction.emoji) == "❌":
            return await ctx.send(f"❌ {opponent.display_name} recusou o desafio.")

        active_battles.add(challenger.id)
        active_battles.add(opponent.id)

        try:
            await self._run_battle(ctx, challenger, opponent)
        finally:
            active_battles.discard(challenger.id)
            active_battles.discard(opponent.id)

    async def _run_battle(self, ctx, p1: discord.Member, p2: discord.Member):
        hp = {p1.id: MAX_HP, p2.id: MAX_HP}

        header = discord.Embed(
            title="⚔️ BATALHA INICIADA!",
            description=f"**{p1.display_name}** vs **{p2.display_name}**",
            color=discord.Color.red()
        )
        header.add_field(name=f"❤️ {p1.display_name}", value=hp_bar(hp[p1.id]), inline=False)
        header.add_field(name=f"❤️ {p2.display_name}", value=hp_bar(hp[p2.id]), inline=False)
        header.set_footer(text="A batalha está prestes a começar...")
        battle_msg = await ctx.send(embed=header)
        await asyncio.sleep(2)

        round_num = 0
        log_lines = []

        while hp[p1.id] > 0 and hp[p2.id] > 0 and round_num < 15:
            round_num += 1
            log_lines = []

            for attacker, defender in [(p1, p2), (p2, p1)]:
                if hp[attacker.id] <= 0 or hp[defender.id] <= 0:
                    break
                move = pick_move()
                dmg, hit = apply_move(move)
                if hit:
                    hp[defender.id] = max(0, hp[defender.id] - dmg)
                    log_lines.append(
                        f"{move['emoji']} **{attacker.display_name}** {move['desc']} em **{defender.display_name}** — `-{dmg}` HP"
                    )
                else:
                    log_lines.append(
                        f"{move['emoji']} **{attacker.display_name}** tentou {move['name'].lower()} mas **errou!**"
                    )

            round_embed = discord.Embed(
                title=f"⚔️ Round {round_num}",
                description="\n".join(log_lines),
                color=discord.Color.blurple()
            )
            round_embed.add_field(name=f"❤️ {p1.display_name}", value=hp_bar(hp[p1.id]), inline=False)
            round_embed.add_field(name=f"❤️ {p2.display_name}", value=hp_bar(hp[p2.id]), inline=False)

            if hp[p1.id] <= 0 or hp[p2.id] <= 0:
                round_embed.set_footer(text="💥 Fim de batalha!")
            else:
                round_embed.set_footer(text="...")

            await battle_msg.edit(embed=round_embed)
            await asyncio.sleep(2.5)

        await self._resolve_battle(ctx, p1, p2, hp)

    async def _resolve_battle(self, ctx, p1: discord.Member, p2: discord.Member, hp: dict):
        p1_hp = hp[p1.id]
        p2_hp = hp[p2.id]

        if p1_hp > p2_hp:
            winner, loser = p1, p2
        elif p2_hp > p1_hp:
            winner, loser = p2, p1
        else:
            draw_embed = discord.Embed(
                title="🤝 EMPATE!",
                description=f"**{p1.display_name}** e **{p2.display_name}** ficaram no empate!\nNenhuma moeda foi transferida.",
                color=discord.Color.yellow()
            )
            draw_embed.add_field(name=f"❤️ {p1.display_name}", value=hp_bar(p1_hp), inline=True)
            draw_embed.add_field(name=f"❤️ {p2.display_name}", value=hp_bar(p2_hp), inline=True)
            return await ctx.send(embed=draw_embed)

        await db.add_coins(str(loser.id), str(ctx.guild.id), -BATTLE_REWARD)
        await db.add_coins(str(winner.id), str(ctx.guild.id), BATTLE_REWARD)
        winner_coins = await db.get_coins(str(winner.id), str(ctx.guild.id))
        loser_coins = await db.get_coins(str(loser.id), str(ctx.guild.id))

        result_embed = discord.Embed(
            title=f"🏆 {winner.display_name} VENCEU!",
            description=f"{winner.mention} derrotou {loser.mention} em batalha épica!",
            color=discord.Color.gold()
        )
        result_embed.add_field(
            name=f"❤️ {p1.display_name}",
            value=hp_bar(p1_hp),
            inline=True
        )
        result_embed.add_field(
            name=f"❤️ {p2.display_name}",
            value=hp_bar(p2_hp),
            inline=True
        )
        result_embed.add_field(
            name=f"🏆 {winner.display_name}",
            value=f"+**{BATTLE_REWARD} 🪙** → **{winner_coins} 🪙**",
            inline=False
        )
        result_embed.add_field(
            name=f"💀 {loser.display_name}",
            value=f"-**{BATTLE_REWARD} 🪙** → **{loser_coins} 🪙**",
            inline=False
        )
        await ctx.send(embed=result_embed)

    @lutar.error
    async def battle_error(self, ctx, error):
        if isinstance(error, commands.MemberNotFound):
            await ctx.send("❌ Membro não encontrado.")
        elif isinstance(error, commands.MissingRequiredArgument):
            await ctx.send(f"❌ Mencione alguém para lutar. Ex: `!lutar @user`")
        elif isinstance(error, commands.CommandOnCooldown):
            await ctx.send(f"⏳ Aguarde **{error.retry_after:.0f}s** antes de lutar novamente.")
        else:
            active_battles.discard(ctx.author.id)
            await ctx.send(f"❌ Erro: {error}")


async def setup(bot):
    await bot.add_cog(Battle(bot))
