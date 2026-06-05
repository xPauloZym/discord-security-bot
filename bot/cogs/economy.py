import discord
from discord.ext import commands
from datetime import datetime, timezone
from bot import database as db

DAILY_AMOUNT = 20

SHOP_ITEMS = {
    "randomnick": {
        "name": "🎲 Nick Aleatório",
        "desc": "Deixa o nick de alguém aleatório por 10 minutos",
        "price": 150,
        "emoji": "🎲",
    },
    "shield": {
        "name": "🛡️ Escudo Anti-Roubo",
        "desc": "Protege suas moedas de roubo por 24 horas",
        "price": 100,
        "emoji": "🛡️",
    },
    "steal": {
        "name": "🦝 Kit Ladrão",
        "desc": "Tenta roubar moedas de alguém (!roubar @user)",
        "price": 120,
        "emoji": "🦝",
    },
    "vip": {
        "name": "⭐ Tag VIP",
        "desc": "Ganha o cargo VIP no servidor por 7 dias",
        "price": 300,
        "emoji": "⭐",
    },
    "bomb": {
        "name": "💣 Bomba de Nick",
        "desc": "Muda o nick de alguém para 'BOMBA💣' por 5 minutos",
        "price": 80,
        "emoji": "💣",
    },
    "spy": {
        "name": "🕵️ Espião",
        "desc": "Vê a quantidade de moedas de qualquer pessoa",
        "price": 60,
        "emoji": "🕵️",
    },
}


class Economy(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(name="daily", aliases=["diario"], help="Pegue suas 20 moedas diárias!")
    @commands.guild_only()
    async def daily(self, ctx):
        today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        last = await db.get_last_daily(str(ctx.author.id), str(ctx.guild.id))

        if last == today:
            embed = discord.Embed(
                title="⏰ Já pegou hoje!",
                description=f"Volte amanhã para pegar mais **{DAILY_AMOUNT} moedas**.",
                color=discord.Color.orange()
            )
            await ctx.send(embed=embed)
            return

        await db.add_coins(str(ctx.author.id), str(ctx.guild.id), DAILY_AMOUNT)
        await db.set_last_daily(str(ctx.author.id), str(ctx.guild.id), today)
        coins = await db.get_coins(str(ctx.author.id), str(ctx.guild.id))

        embed = discord.Embed(
            title="✅ Daily coletado!",
            description=f"Você recebeu **{DAILY_AMOUNT} 🪙 moedas**!",
            color=discord.Color.gold()
        )
        embed.add_field(name="💰 Saldo atual", value=f"**{coins} 🪙**", inline=False)
        embed.set_footer(text="Volte amanhã para mais moedas!")
        await ctx.send(embed=embed)

    @commands.command(name="saldo", aliases=["balance", "coins", "moedas"], help="Veja seu saldo de moedas.")
    @commands.guild_only()
    async def balance(self, ctx, member: discord.Member = None):
        target = member or ctx.author
        coins = await db.get_coins(str(target.id), str(ctx.guild.id))
        has_shield = await db.has_shield(str(target.id), str(ctx.guild.id))

        embed = discord.Embed(
            title=f"💰 Carteira de {target.display_name}",
            color=discord.Color.gold()
        )
        embed.set_thumbnail(url=target.display_avatar.url)
        embed.add_field(name="🪙 Moedas", value=f"**{coins}**", inline=True)
        if has_shield:
            embed.add_field(name="🛡️ Escudo", value="Ativo!", inline=True)
        await ctx.send(embed=embed)

    @commands.command(name="loja", aliases=["shop"], help="Veja a loja de itens.")
    @commands.guild_only()
    async def shop(self, ctx):
        embed = discord.Embed(
            title="🏪 Loja de Itens",
            description="Use `!comprar <id_item>` para comprar.",
            color=discord.Color.blurple()
        )
        for item_id, item in SHOP_ITEMS.items():
            embed.add_field(
                name=f"{item['emoji']} {item['name']} — {item['price']} 🪙",
                value=f"{item['desc']}\nID: `{item_id}`",
                inline=False
            )
        embed.set_footer(text="Ganhe moedas com !daily e jogos!")
        await ctx.send(embed=embed)

    @commands.command(name="comprar", aliases=["buy"], help="Compre um item da loja. Uso: !comprar <id>")
    @commands.guild_only()
    async def buy(self, ctx, item_id: str):
        item_id = item_id.lower()
        if item_id not in SHOP_ITEMS:
            ids = ", ".join(f"`{k}`" for k in SHOP_ITEMS)
            return await ctx.send(f"❌ Item não encontrado. IDs válidos: {ids}")

        item = SHOP_ITEMS[item_id]
        coins = await db.get_coins(str(ctx.author.id), str(ctx.guild.id))

        if coins < item["price"]:
            falta = item["price"] - coins
            return await ctx.send(
                f"❌ Sem moedas suficientes! Você tem **{coins} 🪙** e precisa de **{item['price']} 🪙** (faltam {falta} 🪙)."
            )

        await db.add_coins(str(ctx.author.id), str(ctx.guild.id), -item["price"])
        await db.add_item(str(ctx.author.id), str(ctx.guild.id), item_id)

        embed = discord.Embed(
            title=f"✅ Compra realizada!",
            description=f"Você comprou **{item['emoji']} {item['name']}**!",
            color=discord.Color.green()
        )
        embed.add_field(name="💸 Gasto", value=f"{item['price']} 🪙", inline=True)
        embed.add_field(name="💰 Saldo restante", value=f"{coins - item['price']} 🪙", inline=True)
        embed.add_field(name="ℹ️ Como usar", value=f"Veja `!inventario` e use o comando do item.", inline=False)
        await ctx.send(embed=embed)

    @commands.command(name="inventario", aliases=["inv", "inventory"], help="Veja seus itens.")
    @commands.guild_only()
    async def inventory(self, ctx):
        items = await db.get_inventory(str(ctx.author.id), str(ctx.guild.id))

        embed = discord.Embed(
            title=f"🎒 Inventário de {ctx.author.display_name}",
            color=discord.Color.blurple()
        )

        if not items:
            embed.description = "Seu inventário está vazio. Use `!loja` para comprar itens!"
        else:
            for item_id, qty in items:
                info = SHOP_ITEMS.get(item_id, {"emoji": "❓", "name": item_id, "desc": "Item desconhecido"})
                embed.add_field(
                    name=f"{info['emoji']} {info['name']} x{qty}",
                    value=info["desc"],
                    inline=False
                )
        await ctx.send(embed=embed)

    @commands.command(name="ranking", aliases=["top", "leaderboard"], help="Ranking de moedas do servidor.")
    @commands.guild_only()
    async def ranking(self, ctx):
        rows = await db.get_top_coins(str(ctx.guild.id), 10)

        embed = discord.Embed(
            title="🏆 Ranking de Moedas",
            color=discord.Color.gold()
        )

        medals = ["🥇", "🥈", "🥉"]
        for i, (user_id, coins) in enumerate(rows):
            medal = medals[i] if i < 3 else f"`#{i+1}`"
            member = ctx.guild.get_member(int(user_id))
            name = member.display_name if member else f"User {user_id}"
            embed.add_field(name=f"{medal} {name}", value=f"**{coins} 🪙**", inline=False)

        if not rows:
            embed.description = "Ninguém tem moedas ainda! Use `!daily`."

        await ctx.send(embed=embed)

    @commands.command(name="transferir", aliases=["pay", "pagar"], help="Envie moedas para alguém. Uso: !transferir @user <valor>")
    @commands.guild_only()
    async def transfer(self, ctx, member: discord.Member, amount: int):
        if member == ctx.author:
            return await ctx.send("❌ Você não pode transferir para si mesmo.")
        if amount <= 0:
            return await ctx.send("❌ O valor deve ser positivo.")

        coins = await db.get_coins(str(ctx.author.id), str(ctx.guild.id))
        if coins < amount:
            return await ctx.send(f"❌ Você só tem **{coins} 🪙**.")

        await db.add_coins(str(ctx.author.id), str(ctx.guild.id), -amount)
        await db.add_coins(str(member.id), str(ctx.guild.id), amount)

        embed = discord.Embed(
            title="💸 Transferência realizada!",
            color=discord.Color.green()
        )
        embed.add_field(name="De", value=ctx.author.display_name, inline=True)
        embed.add_field(name="Para", value=member.display_name, inline=True)
        embed.add_field(name="Valor", value=f"**{amount} 🪙**", inline=True)
        await ctx.send(embed=embed)

    @buy.error
    @balance.error
    @transfer.error
    async def eco_error(self, ctx, error):
        if isinstance(error, commands.MissingRequiredArgument):
            await ctx.send(f"❌ Argumento faltando. Use `!help {ctx.command}`.")
        elif isinstance(error, commands.BadArgument):
            await ctx.send("❌ Argumento inválido.")
        else:
            await ctx.send(f"❌ Erro: {error}")


async def setup(bot):
    await bot.add_cog(Economy(bot))
