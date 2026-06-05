import discord
from discord.ext import commands
import aiohttp
import random

NEKOS_URL = "https://nekos.best/api/v2/{endpoint}"
TENOR_URL = (
    "https://api.tenor.com/v1/search"
    "?q={query}&key=LIVDSRZULELA&limit=20&media_filter=minimal&contentfilter=medium"
)

ANIME_RANDOM_POOL = [
    "hug", "kiss", "pat", "cuddle", "dance", "happy",
    "laugh", "wave", "wink", "blush", "pout", "smile",
    "thumbsup", "highfive", "smug",
]

GAME_QUERIES = [
    "gaming anime", "anime game", "video game win", "gamer rage",
    "gaming victory", "esports celebrate", "anime gaming reaction",
]

ACTIONS: dict[str, dict] = {
    "abraco":     {"endpoint": "hug",      "msg": "{a} abraçou {b}! 🤗"},
    "hug":        {"endpoint": "hug",      "msg": "{a} abraçou {b}! 🤗"},
    "beijo":      {"endpoint": "kiss",     "msg": "{a} beijou {b}! 💋"},
    "kiss":       {"endpoint": "kiss",     "msg": "{a} beijou {b}! 💋"},
    "carinho":    {"endpoint": "pat",      "msg": "{a} fez carinho em {b}! 🥰"},
    "pat":        {"endpoint": "pat",      "msg": "{a} fez carinho em {b}! 🥰"},
    "cutucar":    {"endpoint": "poke",     "msg": "{a} cutucou {b}! 👉"},
    "poke":       {"endpoint": "poke",     "msg": "{a} cutucou {b}! 👉"},
    "oi":         {"endpoint": "wave",     "msg": "{a} acenou para {b}! 👋"},
    "wave":       {"endpoint": "wave",     "msg": "{a} acenou para {b}! 👋"},
    "highfive":   {"endpoint": "highfive", "msg": "{a} deu um high five em {b}! ✋"},
    "dança":      {"endpoint": "dance",    "msg": "{a} dançou para {b}! 💃"},
    "dance":      {"endpoint": "dance",    "msg": "{a} dançou para {b}! 💃"},
    "feliz":      {"endpoint": "happy",    "msg": "{a} ficou feliz com {b}! 😄"},
    "choro":      {"endpoint": "cry",      "msg": "{a} chorou por causa de {b}! 😭"},
    "cry":        {"endpoint": "cry",      "msg": "{a} chorou por causa de {b}! 😭"},
    "corar":      {"endpoint": "blush",    "msg": "{a} corou por causa de {b}! 😳"},
    "blush":      {"endpoint": "blush",    "msg": "{a} corou por causa de {b}! 😳"},
    "rir":        {"endpoint": "laugh",    "msg": "{a} riu de {b}! 😂"},
    "laugh":      {"endpoint": "laugh",    "msg": "{a} riu de {b}! 😂"},
    "bico":       {"endpoint": "pout",     "msg": "{a} está de bico com {b}! 😤"},
    "pout":       {"endpoint": "pout",     "msg": "{a} está de bico com {b}! 😤"},
    "piscar":     {"endpoint": "wink",     "msg": "{a} piscou para {b}! 😉"},
    "wink":       {"endpoint": "wink",     "msg": "{a} piscou para {b}! 😉"},
    "soco":       {"endpoint": "punch",    "msg": "{a} deu um soco em {b}! 👊"},
    "punch":      {"endpoint": "punch",    "msg": "{a} deu um soco em {b}! 👊"},
    "tapa":       {"endpoint": "slap",     "msg": "{a} deu um tapa em {b}! 👋"},
    "slap":       {"endpoint": "slap",     "msg": "{a} deu um tapa em {b}! 👋"},
    "morder":     {"endpoint": "bite",     "msg": "{a} mordeu {b}! 😬"},
    "bite":       {"endpoint": "bite",     "msg": "{a} mordeu {b}! 😬"},
    "dormir":     {"endpoint": "sleep",    "msg": "{a} dormiu no colo de {b}! 😴"},
    "sleep":      {"endpoint": "sleep",    "msg": "{a} dormiu no colo de {b}! 😴"},
    "pensar":     {"endpoint": "think",    "msg": "{a} está pensando em {b}... 🤔"},
    "think":      {"endpoint": "think",    "msg": "{a} está pensando em {b}... 🤔"},
    "joinha":     {"endpoint": "thumbsup", "msg": "{a} deu joinha para {b}! 👍"},
    "thumbsup":   {"endpoint": "thumbsup", "msg": "{a} deu joinha para {b}! 👍"},
    "facepalm":   {"endpoint": "facepalm", "msg": "{a} fez facepalm por causa de {b} 🤦"},
    "smug":       {"endpoint": "smug",     "msg": "{a} está se achando na frente de {b}! 😏"},
    "abracar":    {"endpoint": "cuddle",   "msg": "{a} aconchegou {b}! 🥰"},
    "cuddle":     {"endpoint": "cuddle",   "msg": "{a} aconchegou {b}! 🥰"},
}


async def fetch_nekos(session: aiohttp.ClientSession, endpoint: str) -> str | None:
    url = NEKOS_URL.format(endpoint=endpoint)
    try:
        async with session.get(url, timeout=aiohttp.ClientTimeout(total=8)) as r:
            if r.status == 200:
                data = await r.json()
                results = data.get("results", [])
                if results:
                    return results[0]["url"]
    except Exception:
        pass
    return None


async def fetch_tenor(session: aiohttp.ClientSession, query: str) -> str | None:
    url = TENOR_URL.format(query=query.replace(" ", "+"))
    try:
        async with session.get(url, timeout=aiohttp.ClientTimeout(total=8)) as r:
            if r.status == 200:
                data = await r.json()
                results = data.get("results", [])
                if results:
                    item = random.choice(results[:10])
                    media = item.get("media", [{}])[0]
                    gif_data = media.get("gif") or media.get("mediumgif") or media.get("tinygif")
                    if gif_data:
                        return gif_data.get("url")
    except Exception:
        pass
    return None


class GifCommands(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(
        name="gif",
        aliases=["gifs"],
        help="GIF aleatório de anime ou jogo. Uso: !gif [anime/jogo]"
    )
    @commands.guild_only()
    @commands.cooldown(1, 5, commands.BucketType.user)
    async def gif(self, ctx, categoria: str = "anime"):
        categoria = categoria.lower()

        async with aiohttp.ClientSession() as session:
            if categoria == "jogo":
                query = random.choice(GAME_QUERIES)
                gif_url = await fetch_tenor(session, query)
                title = "🎮 GIF de Jogo"
                color = discord.Color.green()
            else:
                endpoint = random.choice(ANIME_RANDOM_POOL)
                gif_url = await fetch_nekos(session, endpoint)
                title = "🎌 GIF de Anime"
                color = discord.Color.red()

        if not gif_url:
            return await ctx.send("❌ Não consegui buscar um GIF agora. Tente novamente!")

        embed = discord.Embed(title=title, color=color)
        embed.set_image(url=gif_url)
        embed.set_footer(
            text=f"Pedido por {ctx.author.display_name} • !gif anime / !gif jogo",
            icon_url=ctx.author.display_avatar.url
        )
        await ctx.send(embed=embed)

    @commands.command(
        name="reagir",
        aliases=["reaction", "reacao"],
        help="Reaja a alguém com um GIF anime personalizado. Uso: !reagir @user <ação>"
    )
    @commands.guild_only()
    @commands.cooldown(1, 4, commands.BucketType.user)
    async def reagir(self, ctx, membro: discord.Member, acao: str = "abraco"):
        acao = acao.lower()

        if membro == ctx.author:
            return await ctx.send("❌ Você não pode reagir a si mesmo!")

        action_data = ACTIONS.get(acao)
        if not action_data:
            valid = ", ".join(f"`{k}`" for k in sorted(set(v["endpoint"] for v in ACTIONS.values())))
            return await ctx.send(
                f"❌ Ação desconhecida. Ações disponíveis:\n{valid}"
            )

        endpoint = action_data["endpoint"]
        msg_template = action_data["msg"]
        title = msg_template.format(a=ctx.author.display_name, b=membro.display_name)

        async with aiohttp.ClientSession() as session:
            gif_url = await fetch_nekos(session, endpoint)

        if not gif_url:
            return await ctx.send("❌ Não consegui buscar o GIF agora. Tente novamente!")

        embed = discord.Embed(
            title=title,
            color=discord.Color.pink() if endpoint in ("hug", "kiss", "pat", "cuddle") else discord.Color.blurple()
        )
        embed.set_image(url=gif_url)
        embed.set_thumbnail(url=membro.display_avatar.url)
        embed.set_footer(
            text=f"De: {ctx.author.display_name} → Para: {membro.display_name}",
            icon_url=ctx.author.display_avatar.url
        )
        await ctx.send(content=membro.mention, embed=embed)

    @gif.error
    async def gif_error(self, ctx, error):
        if isinstance(error, commands.CommandOnCooldown):
            await ctx.send(f"⏳ Aguarde **{error.retry_after:.1f}s** antes de usar !gif novamente.")

    @reagir.error
    async def reagir_error(self, ctx, error):
        if isinstance(error, commands.MemberNotFound):
            await ctx.send("❌ Membro não encontrado. Mencione alguém do servidor.")
        elif isinstance(error, commands.MissingRequiredArgument):
            await ctx.send("❌ Uso correto: `!reagir @user <ação>` — Ex: `!reagir @Paulinho abraco`")
        elif isinstance(error, commands.CommandOnCooldown):
            await ctx.send(f"⏳ Aguarde **{error.retry_after:.1f}s** antes de reagir novamente.")


async def setup(bot):
    await bot.add_cog(GifCommands(bot))
