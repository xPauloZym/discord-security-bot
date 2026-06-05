import discord
from discord.ext import commands
from datetime import datetime, timezone, timedelta
import random
import asyncio
from bot import database as db

RANDOM_NICKS = [
    "🍌 BananaLoka", "🐸 SapoDoido", "🦆 PatoFeliz", "🌮 TacoDaLua",
    "🤡 PalhacoBravo", "🐙 PolvoMágico", "🦄 UnicornioRaivoso", "🍕 PizzaVolante",
    "🐧 PinguimNinja", "🌵 CactoApaixonado", "🦊 RaposaMaluca", "🍦 SorveteVivo",
    "🐢 TartarugaRocket", "🦋 BorboletaLoca", "🐝 AbelhaHacker", "🥑 AbacateTriste",
    "🐬 GolfinhoRaptor", "🌙 LunaDoida", "🎭 MáscaraLoka", "🦖 DinoBugado",
]


class Fun(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self._nick_tasks: dict = {}

    async def _restore_nick(self, member: discord.Member, original_nick: str, delay: float):
        await asyncio.sleep(delay)
        try:
            await member.edit(nick=original_nick)
        except discord.Forbidden:
            pass
        self._nick_tasks.pop(member.id, None)

    @commands.command(name="randomnick", aliases=["nickaleat"], help="Use o item RandomNick: !randomnick @user")
    @commands.guild_only()
    async def random_nick(self, ctx, member: discord.Member):
        if not await db.remove_item(str(ctx.author.id), str(ctx.guild.id), "randomnick"):
            return await ctx.send("❌ Você não tem o item **🎲 Nick Aleatório**! Compre na `!loja`.")

        if member == ctx.me:
            await db.add_item(str(ctx.author.id), str(ctx.guild.id), "randomnick")
            return await ctx.send("❌ Não posso trocar meu próprio nick!")

        if member.top_role >= ctx.guild.me.top_role:
            await db.add_item(str(ctx.author.id), str(ctx.guild.id), "randomnick")
            return await ctx.send("❌ Não tenho permissão para mudar o nick dessa pessoa.")

        original_nick = member.display_name
        new_nick = random.choice(RANDOM_NICKS)

        try:
            await member.edit(nick=new_nick)
        except discord.Forbidden:
            await db.add_item(str(ctx.author.id), str(ctx.guild.id), "randomnick")
            return await ctx.send("❌ Sem permissão para mudar o nick desta pessoa.")

        if member.id in self._nick_tasks:
            self._nick_tasks[member.id].cancel()

        task = asyncio.create_task(self._restore_nick(member, original_nick, 600))
        self._nick_tasks[member.id] = task

        embed = discord.Embed(
            title="🎲 Nick Aleatório ativado!",
            description=f"O nick de {member.mention} foi trocado para **{new_nick}**!",
            color=discord.Color.purple()
        )
        embed.add_field(name="⏰ Duração", value="10 minutos", inline=True)
        embed.add_field(name="👤 Usado por", value=ctx.author.display_name, inline=True)
        await ctx.send(embed=embed)

    @commands.command(name="bombanick", aliases=["bomb"], help="Use o item Bomba: !bombanick @user")
    @commands.guild_only()
    async def bomb_nick(self, ctx, member: discord.Member):
        if not await db.remove_item(str(ctx.author.id), str(ctx.guild.id), "bomb"):
            return await ctx.send("❌ Você não tem o item **💣 Bomba de Nick**! Compre na `!loja`.")

        if member.top_role >= ctx.guild.me.top_role:
            await db.add_item(str(ctx.author.id), str(ctx.guild.id), "bomb")
            return await ctx.send("❌ Não tenho permissão para mudar o nick dessa pessoa.")

        original_nick = member.display_name

        try:
            await member.edit(nick="BOMBA💣")
        except discord.Forbidden:
            await db.add_item(str(ctx.author.id), str(ctx.guild.id), "bomb")
            return await ctx.send("❌ Sem permissão para mudar o nick desta pessoa.")

        if member.id in self._nick_tasks:
            self._nick_tasks[member.id].cancel()

        task = asyncio.create_task(self._restore_nick(member, original_nick, 300))
        self._nick_tasks[member.id] = task

        embed = discord.Embed(
            title="💣 BOMBA ativada!",
            description=f"{member.mention} agora é **BOMBA💣** por 5 minutos!",
            color=discord.Color.orange()
        )
        embed.add_field(name="👤 Usado por", value=ctx.author.display_name, inline=True)
        await ctx.send(embed=embed)

    @commands.command(name="escudo", aliases=["shield_use"], help="Ative seu Escudo Anti-Roubo: !escudo")
    @commands.guild_only()
    async def use_shield(self, ctx):
        if not await db.remove_item(str(ctx.author.id), str(ctx.guild.id), "shield"):
            return await ctx.send("❌ Você não tem o item **🛡️ Escudo**! Compre na `!loja`.")

        expires = datetime.now(timezone.utc) + timedelta(hours=24)
        await db.set_shield(str(ctx.author.id), str(ctx.guild.id), expires.isoformat())

        embed = discord.Embed(
            title="🛡️ Escudo ativado!",
            description="Suas moedas estão protegidas contra roubo por **24 horas**!",
            color=discord.Color.blue()
        )
        await ctx.send(embed=embed)

    @commands.command(name="roubar", aliases=["steal"], help="Use o item Ladrão para roubar: !roubar @user")
    @commands.guild_only()
    async def steal(self, ctx, member: discord.Member):
        if not await db.remove_item(str(ctx.author.id), str(ctx.guild.id), "steal"):
            return await ctx.send("❌ Você não tem o item **🦝 Kit Ladrão**! Compre na `!loja`.")

        if member == ctx.author:
            await db.add_item(str(ctx.author.id), str(ctx.guild.id), "steal")
            return await ctx.send("❌ Você não pode roubar de si mesmo.")

        if await db.has_shield(str(member.id), str(ctx.guild.id)):
            return await ctx.send(f"❌ {member.display_name} tem um **🛡️ Escudo** ativo! Roubo bloqueado.")

        target_coins = await db.get_coins(str(member.id), str(ctx.guild.id))
        if target_coins <= 0:
            return await ctx.send(f"❌ {member.display_name} não tem moedas para roubar.")

        success = random.random() < 0.5
        if success:
            stolen = random.randint(1, min(30, target_coins))
            await db.add_coins(str(member.id), str(ctx.guild.id), -stolen)
            await db.add_coins(str(ctx.author.id), str(ctx.guild.id), stolen)

            embed = discord.Embed(
                title="🦝 Roubo bem-sucedido!",
                description=f"Você roubou **{stolen} 🪙** de {member.display_name}!",
                color=discord.Color.green()
            )
        else:
            fine = random.randint(5, 20)
            fine = min(fine, await db.get_coins(str(ctx.author.id), str(ctx.guild.id)))
            await db.add_coins(str(ctx.author.id), str(ctx.guild.id), -fine)
            embed = discord.Embed(
                title="🚨 Flagrado!",
                description=f"Você foi pego tentando roubar {member.display_name} e pagou **{fine} 🪙** de multa!",
                color=discord.Color.red()
            )

        await ctx.send(embed=embed)

    @commands.command(name="espiar", aliases=["spy_use"], help="Use o Espião para ver moedas: !espiar @user")
    @commands.guild_only()
    async def spy(self, ctx, member: discord.Member):
        if not await db.remove_item(str(ctx.author.id), str(ctx.guild.id), "spy"):
            return await ctx.send("❌ Você não tem o item **🕵️ Espião**! Compre na `!loja`.")

        coins = await db.get_coins(str(member.id), str(ctx.guild.id))
        has_shield = await db.has_shield(str(member.id), str(ctx.guild.id))

        embed = discord.Embed(
            title="🕵️ Informação secreta obtida!",
            color=discord.Color.dark_blue()
        )
        embed.add_field(name="Alvo", value=member.display_name, inline=True)
        embed.add_field(name="🪙 Moedas", value=f"**{coins}**", inline=True)
        if has_shield:
            embed.add_field(name="🛡️ Escudo", value="Ativo!", inline=True)
        embed.set_footer(text="Só você pode ver isso!")
        await ctx.send(embed=embed, ephemeral=False)

    @commands.command(name="8ball", aliases=["bola8"], help="Pergunte à bola mágica! Uso: !8ball <pergunta>")
    @commands.guild_only()
    async def eight_ball(self, ctx, *, question: str):
        responses = [
            "✅ Com certeza!", "✅ Definitivamente sim.", "✅ Pode contar com isso.",
            "✅ Sem dúvida!", "✅ Sim, absolutamente.", "🤷 As perspectivas são boas.",
            "🤷 Pergunte de novo mais tarde.", "🤷 Difícil de dizer agora.",
            "🤷 Não me concentre agora.", "🤷 Resposta nebulosa, tente novamente.",
            "❌ Não conte com isso.", "❌ Minha resposta é não.", "❌ Minhas fontes dizem não.",
            "❌ As perspectivas não são boas.", "❌ Muito duvidoso.",
        ]
        answer = random.choice(responses)
        embed = discord.Embed(title="🎱 Bola Mágica", color=discord.Color.dark_purple())
        embed.add_field(name="❓ Pergunta", value=question, inline=False)
        embed.add_field(name="🎱 Resposta", value=f"**{answer}**", inline=False)
        await ctx.send(embed=embed)

    @commands.command(name="dado", aliases=["dice", "rolar"], help="Role um dado! Uso: !dado [lados]")
    @commands.guild_only()
    async def dice(self, ctx, sides: int = 6):
        if sides < 2 or sides > 1000:
            return await ctx.send("❌ O dado deve ter entre 2 e 1000 lados.")
        result = random.randint(1, sides)
        embed = discord.Embed(
            title=f"🎲 Dado de {sides} lados",
            description=f"Você rolou: **{result}**",
            color=discord.Color.blurple()
        )
        await ctx.send(embed=embed)

    @commands.command(name="piada", aliases=["joke", "charada"], help="Uma piada aleatória!")
    @commands.guild_only()
    async def joke(self, ctx):
        jokes = [
            ("Por que o espantalho ganhou um prêmio?", "Porque ele era excepcional no seu campo! 🌾"),
            ("O que o zero disse para o oito?", "Que cinto bonito! 👔"),
            ("Por que o computador foi ao médico?", "Porque tinha um vírus! 🦠"),
            ("O que o mar disse para a praia?", "Nada, só deu uma onda! 🌊"),
            ("Por que o livro de matemática estava triste?", "Tinha muitos problemas! 📚"),
            ("O que o pato disse para a pata?", "Vem cá, quack! 🦆"),
            ("Por que o elefante usa sandálias?", "Para não afundar na areia! 🐘"),
            ("O que a formiga disse para a outra?", "Muita formiga aqui, né formigamente? 🐜"),
        ]
        setup, punchline = random.choice(jokes)
        embed = discord.Embed(title="😂 Piada do Dia", color=discord.Color.yellow())
        embed.add_field(name="❓", value=setup, inline=False)
        msg = await ctx.send(embed=embed)
        await asyncio.sleep(2)
        embed.add_field(name="😄", value=f"||{punchline}||", inline=False)
        await msg.edit(embed=embed)

    @commands.command(name="abraco", aliases=["hug"], help="Mande um abraço! Uso: !abraco @user")
    @commands.guild_only()
    async def hug(self, ctx, member: discord.Member):
        if member == ctx.author:
            return await ctx.send("🤗 Você se abraçou... que fofo!")
        embed = discord.Embed(
            title="🤗 Abraço!",
            description=f"**{ctx.author.display_name}** mandou um abraço para **{member.display_name}**! 🤗",
            color=discord.Color.pink() if hasattr(discord.Color, 'pink') else discord.Color.magenta()
        )
        await ctx.send(embed=embed)

    @commands.command(name="ship", help="Mede a compatibilidade entre duas pessoas! Uso: !ship @user1 @user2")
    @commands.guild_only()
    async def ship(self, ctx, user1: discord.Member, user2: discord.Member):
        seed = int(user1.id) + int(user2.id)
        random.seed(seed)
        percent = random.randint(0, 100)
        random.seed()

        if percent >= 80:
            emoji, msg = "💕", "Amor verdadeiro!"
        elif percent >= 60:
            emoji, msg = "❤️", "Muito compatíveis!"
        elif percent >= 40:
            emoji, msg = "🧡", "Pode rolar algo!"
        elif percent >= 20:
            emoji, msg = "💛", "Amizade forte!"
        else:
            emoji, msg = "💔", "Não é bem um match..."

        bar_filled = int(percent / 10)
        bar = "█" * bar_filled + "░" * (10 - bar_filled)

        embed = discord.Embed(title=f"💘 Ship: {user1.display_name} + {user2.display_name}", color=discord.Color.red())
        embed.add_field(name="Compatibilidade", value=f"`{bar}` **{percent}%**", inline=False)
        embed.add_field(name=emoji, value=msg, inline=False)
        await ctx.send(embed=embed)

    @random_nick.error
    @bomb_nick.error
    @use_shield.error
    @steal.error
    @spy.error
    async def fun_error(self, ctx, error):
        if isinstance(error, commands.MemberNotFound):
            await ctx.send("❌ Membro não encontrado.")
        elif isinstance(error, commands.MissingRequiredArgument):
            await ctx.send(f"❌ Argumento faltando. Use `!help {ctx.command}`.")
        else:
            await ctx.send(f"❌ Erro: {error}")


async def setup(bot):
    await bot.add_cog(Fun(bot))
