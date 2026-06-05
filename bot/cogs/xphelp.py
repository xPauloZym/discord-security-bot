import discord
from discord.ext import commands
from bot.config import BOT_PREFIX


CATEGORIES = {
    "moderacao": {
        "emoji": "🛡️",
        "title": "Moderação",
        "commands": [
            (f"`{BOT_PREFIX}kick @user [motivo]`", "Expulsa um membro do servidor"),
            (f"`{BOT_PREFIX}ban @user [motivo]`", "Bane permanentemente um membro"),
            (f"`{BOT_PREFIX}tempban @user 1h/1d [motivo]`", "Bane temporariamente um membro"),
            (f"`{BOT_PREFIX}unban <id> [motivo]`", "Desbane um usuário pelo ID"),
            (f"`{BOT_PREFIX}mute @user 1h [motivo]`", "Silencia um membro (timeout)"),
            (f"`{BOT_PREFIX}unmute @user`", "Remove o silêncio de um membro"),
            (f"`{BOT_PREFIX}purge <qtd> [@user]`", "Apaga mensagens do canal (máx 200)"),
            (f"`{BOT_PREFIX}modlog [qtd]`", "Mostra ações de moderação recentes"),
            (f"`{BOT_PREFIX}banlist`", "Lista todos os bans registrados"),
        ]
    },
    "seguranca": {
        "emoji": "🚫",
        "title": "Segurança & IP Ban",
        "commands": [
            (f"`{BOT_PREFIX}ipban <ip> [motivo]`", "Bane um endereço IP do servidor"),
            (f"`{BOT_PREFIX}ipunban <ip>`", "Remove o ban de um IP"),
            (f"`{BOT_PREFIX}registerip @user <ip>`", "Registra um IP associado a um usuário"),
            (f"`{BOT_PREFIX}checkip <ip>`", "Verifica se um IP está banido"),
            (f"`{BOT_PREFIX}checkuser @user`", "Verifica IPs e alts de um usuário"),
            (f"`{BOT_PREFIX}registeralt @main @alt`", "Registra uma conta alt de um usuário"),
            (f"`{BOT_PREFIX}raidmode on/off`", "Ativa/desativa o modo anti-raid manualmente"),
            (f"`{BOT_PREFIX}raidstatus`", "Verifica se o modo anti-raid está ativo"),
        ]
    },
    "economia": {
        "emoji": "🪙",
        "title": "Economia",
        "commands": [
            (f"`{BOT_PREFIX}daily`", "Pega 20 moedas diárias"),
            (f"`{BOT_PREFIX}saldo [@user]`", "Vê o saldo de moedas"),
            (f"`{BOT_PREFIX}loja`", "Mostra a loja de itens"),
            (f"`{BOT_PREFIX}comprar <id>`", "Compra um item da loja"),
            (f"`{BOT_PREFIX}inventario`", "Vê seus itens"),
            (f"`{BOT_PREFIX}ranking`", "Ranking de moedas do servidor"),
            (f"`{BOT_PREFIX}transferir @user <valor>`", "Envia moedas para alguém"),
        ]
    },
    "jogos": {
        "emoji": "🎮",
        "title": "Jogos",
        "commands": [
            (f"`{BOT_PREFIX}coinflip cara/coroa`", "Aposte cara ou coroa (custa 4 🪙, ganha/perde 10 🪙)"),
            (f"`{BOT_PREFIX}adivinhar <1-10>`", "Adivinhe o número (custa 4 🪙, ganha/perde 10 🪙)"),
            (f"`{BOT_PREFIX}pedrapapeltesoura pedra/papel/tesoura`", "Pedra Papel Tesoura (custa 4 🪙, ganha/perde 10 🪙)"),
            (f"`{BOT_PREFIX}slots`", "Gire os slots (custa 4 🪙, ganha/perde 10 🪙)"),
            (f"`{BOT_PREFIX}tentativas`", "Vê tentativas de jogo restantes hoje"),
            (f"`{BOT_PREFIX}lutar @user`", "Desafie alguém para uma batalha com emojis (aposta 20 🪙)"),
        ]
    },
    "diversao": {
        "emoji": "🎉",
        "title": "Diversão & Itens",
        "commands": [
            (f"`{BOT_PREFIX}randomnick @user`", "Troca nick aleatório por 10 min (item)"),
            (f"`{BOT_PREFIX}bombanick @user`", "Troca nick para BOMBA💣 por 5 min (item)"),
            (f"`{BOT_PREFIX}escudo`", "Ativa escudo anti-roubo por 24h (item)"),
            (f"`{BOT_PREFIX}roubar @user`", "Tenta roubar moedas (item)"),
            (f"`{BOT_PREFIX}espiar @user`", "Vê as moedas de alguém (item)"),
            (f"`{BOT_PREFIX}8ball <pergunta>`", "Pergunta à bola mágica"),
            (f"`{BOT_PREFIX}dado [lados]`", "Rola um dado"),
            (f"`{BOT_PREFIX}piada`", "Conta uma piada aleatória"),
            (f"`{BOT_PREFIX}abraco @user`", "Manda um abraço"),
            (f"`{BOT_PREFIX}ship @user1 @user2`", "Mede compatibilidade"),
        ]
    },
    "itens": {
        "emoji": "🏪",
        "title": "Itens da Loja",
        "commands": [
            ("`randomnick` — 150 🪙", "🎲 Nick aleatório por 10 minutos"),
            ("`shield` — 100 🪙", "🛡️ Escudo anti-roubo por 24 horas"),
            ("`steal` — 120 🪙", "🦝 Kit ladrão (!roubar @user)"),
            ("`vip` — 300 🪙", "⭐ Tag VIP no servidor por 7 dias"),
            ("`bomb` — 80 🪙", "💣 Bomba de nick por 5 minutos"),
            ("`spy` — 60 🪙", "🕵️ Ver moedas de qualquer pessoa"),
        ]
    },
    "dono": {
        "emoji": "🔧",
        "title": "Comandos de Dono",
        "commands": [
            (f"`{BOT_PREFIX}setmoedas @user <valor>`", "Define exatamente quantas moedas alguém tem"),
            (f"`{BOT_PREFIX}darmoedas @user <valor>`", "Adiciona moedas ao saldo de alguém"),
            (f"`{BOT_PREFIX}tirarmoedas @user <valor>`", "Remove moedas do saldo de alguém"),
            (f"`{BOT_PREFIX}daritem @user <item_id>`", "Dá um item do shop diretamente para alguém"),
            (f"`{BOT_PREFIX}tiraritem @user <item_id>`", "Remove um item do inventário de alguém"),
            (f"`{BOT_PREFIX}resetareco @user`", "Zera o saldo de moedas de alguém"),
            (f"`{BOT_PREFIX}resetartentativas @user`", "Reseta as tentativas de jogo de alguém no dia"),
            (f"`{BOT_PREFIX}vereco @user`", "Vê o perfil econômico completo de alguém"),
        ]
    },
}


class XpHelp(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(name="XpHelp", aliases=["xphelp", "ajuda", "comandos"], help="Mostra todos os comandos do bot.")
    @commands.guild_only()
    async def xphelp(self, ctx, categoria: str = None):
        if categoria is None:
            embed = discord.Embed(
                title=f"📋 XpHelp — Todos os Comandos",
                description=f"Use `{BOT_PREFIX}XpHelp <categoria>` para ver os comandos detalhados de cada categoria.\nO prefixo do bot é `{BOT_PREFIX}`",
                color=discord.Color.blurple()
            )
            for key, cat in CATEGORIES.items():
                count = len(cat["commands"])
                embed.add_field(
                    name=f"{cat['emoji']} {cat['title']}",
                    value=f"`{BOT_PREFIX}XpHelp {key}` — {count} comandos",
                    inline=True
                )
            embed.add_field(
                name="⚙️ Outros",
                value=f"`{BOT_PREFIX}ping` — Latência\n`{BOT_PREFIX}botinfo` — Informações do bot",
                inline=True
            )
            cats = " | ".join(CATEGORIES.keys())
            embed.set_footer(text=f"💡 Categorias: {cats}")
            return await ctx.send(embed=embed)

        key = categoria.lower()
        if key not in CATEGORIES:
            valid = ", ".join(f"`{k}`" for k in CATEGORIES)
            return await ctx.send(f"❌ Categoria inválida. Categorias válidas: {valid}")

        cat = CATEGORIES[key]
        embed = discord.Embed(
            title=f"{cat['emoji']} {cat['title']}",
            color=discord.Color.blurple()
        )
        if key == "dono":
            embed.description = "Comandos restritos — somente o dono do servidor tem acesso.\nIDs de item: randomnick | shield | steal | bomb | spy | vip"

        for cmd, desc in cat["commands"]:
            embed.add_field(name=cmd, value=desc, inline=False)

        embed.set_footer(text=f"Use {BOT_PREFIX}XpHelp para voltar ao menu principal")
        await ctx.send(embed=embed)


async def setup(bot):
    await bot.add_cog(XpHelp(bot))
