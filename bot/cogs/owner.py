import discord
from discord.ext import commands
from bot import database as db
from bot.cogs.economy import SHOP_ITEMS


def is_owner():
    async def predicate(ctx):
        return ctx.author.id == ctx.guild.owner_id or await ctx.bot.is_owner(ctx.author)
    return commands.check(predicate)


class Owner(commands.Cog, name="Dono"):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(name="setmoedas", help="Define exatamente quantas moedas alguém tem. Uso: !setmoedas @user <valor>")
    @commands.guild_only()
    @is_owner()
    async def set_coins(self, ctx, member: discord.Member, amount: int):
        if amount < 0:
            return await ctx.send("❌ O valor não pode ser negativo.")
        await db.set_coins(str(member.id), str(ctx.guild.id), amount)
        embed = discord.Embed(
            title="✅ Moedas definidas!",
            description=f"O saldo de {member.mention} foi definido para **{amount} 🪙**.",
            color=discord.Color.green()
        )
        embed.set_footer(text=f"Por: {ctx.author.display_name}")
        await ctx.send(embed=embed)

    @commands.command(name="darmoedas", help="Adiciona moedas ao saldo de alguém. Uso: !darmoedas @user <valor>")
    @commands.guild_only()
    @is_owner()
    async def give_coins(self, ctx, member: discord.Member, amount: int):
        if amount <= 0:
            return await ctx.send("❌ O valor deve ser positivo.")
        await db.add_coins(str(member.id), str(ctx.guild.id), amount)
        coins = await db.get_coins(str(member.id), str(ctx.guild.id))
        embed = discord.Embed(
            title="✅ Moedas adicionadas!",
            description=f"+**{amount} 🪙** para {member.mention}",
            color=discord.Color.green()
        )
        embed.add_field(name="💰 Novo saldo", value=f"**{coins} 🪙**", inline=True)
        embed.set_footer(text=f"Por: {ctx.author.display_name}")
        await ctx.send(embed=embed)

    @commands.command(name="tirarmoedas", help="Remove moedas do saldo de alguém. Uso: !tirarmoedas @user <valor>")
    @commands.guild_only()
    @is_owner()
    async def take_coins(self, ctx, member: discord.Member, amount: int):
        if amount <= 0:
            return await ctx.send("❌ O valor deve ser positivo.")
        await db.add_coins(str(member.id), str(ctx.guild.id), -amount)
        coins = await db.get_coins(str(member.id), str(ctx.guild.id))
        embed = discord.Embed(
            title="✅ Moedas removidas!",
            description=f"-**{amount} 🪙** de {member.mention}",
            color=discord.Color.orange()
        )
        embed.add_field(name="💰 Novo saldo", value=f"**{coins} 🪙**", inline=True)
        embed.set_footer(text=f"Por: {ctx.author.display_name}")
        await ctx.send(embed=embed)

    @commands.command(name="daritem", help="Dá um item diretamente para alguém. Uso: !daritem @user <item_id>")
    @commands.guild_only()
    @is_owner()
    async def give_item(self, ctx, member: discord.Member, item_id: str):
        item_id = item_id.lower()
        if item_id not in SHOP_ITEMS:
            ids = ", ".join(f"`{k}`" for k in SHOP_ITEMS)
            return await ctx.send(f"❌ Item inválido. IDs válidos: {ids}")
        await db.add_item(str(member.id), str(ctx.guild.id), item_id)
        item = SHOP_ITEMS[item_id]
        embed = discord.Embed(
            title="✅ Item concedido!",
            description=f"{member.mention} recebeu **{item['emoji']} {item['name']}**!",
            color=discord.Color.green()
        )
        embed.set_footer(text=f"Por: {ctx.author.display_name}")
        await ctx.send(embed=embed)

    @commands.command(name="tiraritem", help="Remove um item do inventário de alguém. Uso: !tiraritem @user <item_id>")
    @commands.guild_only()
    @is_owner()
    async def take_item(self, ctx, member: discord.Member, item_id: str):
        item_id = item_id.lower()
        removed = await db.remove_item(str(member.id), str(ctx.guild.id), item_id)
        if not removed:
            return await ctx.send(f"❌ {member.display_name} não tem esse item no inventário.")
        item = SHOP_ITEMS.get(item_id, {"emoji": "❓", "name": item_id})
        embed = discord.Embed(
            title="✅ Item removido!",
            description=f"**{item['emoji']} {item['name']}** removido de {member.mention}.",
            color=discord.Color.orange()
        )
        embed.set_footer(text=f"Por: {ctx.author.display_name}")
        await ctx.send(embed=embed)

    @commands.command(name="resetareco", help="Zera o saldo de moedas de alguém. Uso: !resetareco @user")
    @commands.guild_only()
    @is_owner()
    async def reset_eco(self, ctx, member: discord.Member):
        await db.reset_coins(str(member.id), str(ctx.guild.id))
        embed = discord.Embed(
            title="✅ Economia resetada!",
            description=f"O saldo de {member.mention} foi zerado.",
            color=discord.Color.orange()
        )
        embed.set_footer(text=f"Por: {ctx.author.display_name}")
        await ctx.send(embed=embed)

    @commands.command(name="resetartentativas", help="Reseta as tentativas de jogo de alguém no dia. Uso: !resetartentativas @user")
    @commands.guild_only()
    @is_owner()
    async def reset_attempts(self, ctx, member: discord.Member):
        await db.reset_game_attempts(str(member.id), str(ctx.guild.id))
        embed = discord.Embed(
            title="✅ Tentativas resetadas!",
            description=f"As tentativas de jogo de {member.mention} foram resetadas.",
            color=discord.Color.green()
        )
        embed.set_footer(text=f"Por: {ctx.author.display_name}")
        await ctx.send(embed=embed)

    @commands.command(name="vereco", help="Vê o perfil econômico completo de alguém. Uso: !vereco @user")
    @commands.guild_only()
    @is_owner()
    async def view_eco(self, ctx, member: discord.Member):
        from datetime import datetime, timezone
        coins = await db.get_coins(str(member.id), str(ctx.guild.id))
        items = await db.get_inventory(str(member.id), str(ctx.guild.id))
        has_shield = await db.has_shield(str(member.id), str(ctx.guild.id))
        today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        attempts = await db.get_game_attempts(str(member.id), str(ctx.guild.id), today)

        embed = discord.Embed(
            title=f"🔍 Perfil Econômico — {member.display_name}",
            color=discord.Color.blurple()
        )
        embed.set_thumbnail(url=member.display_avatar.url)
        embed.add_field(name="🪙 Moedas", value=f"**{coins}**", inline=True)
        embed.add_field(name="🛡️ Escudo", value="Ativo" if has_shield else "Inativo", inline=True)
        embed.add_field(name="🎮 Tentativas hoje", value=f"{attempts}/20", inline=True)

        if items:
            inv_text = "\n".join(
                f"{SHOP_ITEMS.get(iid, {}).get('emoji', '❓')} `{iid}` x{qty}"
                for iid, qty in items
            )
            embed.add_field(name="🎒 Inventário", value=inv_text, inline=False)
        else:
            embed.add_field(name="🎒 Inventário", value="Vazio", inline=False)

        embed.set_footer(text=f"Consultado por: {ctx.author.display_name}")
        await ctx.send(embed=embed)

    @set_coins.error
    @give_coins.error
    @take_coins.error
    @give_item.error
    @take_item.error
    @reset_eco.error
    @reset_attempts.error
    @view_eco.error
    async def owner_error(self, ctx, error):
        if isinstance(error, commands.CheckFailure):
            await ctx.send("❌ Apenas o **dono do servidor** pode usar este comando.")
        elif isinstance(error, commands.MissingRequiredArgument):
            await ctx.send(f"❌ Argumento faltando. Use `!XpHelp dono` para ver os comandos.")
        elif isinstance(error, commands.MemberNotFound):
            await ctx.send("❌ Membro não encontrado.")
        elif isinstance(error, commands.BadArgument):
            await ctx.send("❌ Argumento inválido.")
        else:
            await ctx.send(f"❌ Erro: {error}")


async def setup(bot):
    await bot.add_cog(Owner(bot))
