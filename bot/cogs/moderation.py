import discord
from discord.ext import commands
from datetime import datetime, timezone, timedelta
import asyncio
from bot import database as db
from bot.config import LOG_CHANNEL_NAME


def parse_duration(duration_str: str) -> timedelta | None:
    """Parse duration strings like 1h, 30m, 2d, 1w"""
    units = {"s": 1, "m": 60, "h": 3600, "d": 86400, "w": 604800}
    unit = duration_str[-1].lower()
    if unit not in units:
        return None
    try:
        value = int(duration_str[:-1])
        return timedelta(seconds=value * units[unit])
    except ValueError:
        return None


async def send_log(guild: discord.Guild, embed: discord.Embed):
    channel = discord.utils.get(guild.text_channels, name=LOG_CHANNEL_NAME)
    if channel:
        try:
            await channel.send(embed=embed)
        except discord.Forbidden:
            pass


class Moderation(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    def is_mod():
        async def predicate(ctx):
            return (
                ctx.author.guild_permissions.ban_members
                or ctx.author.guild_permissions.kick_members
                or ctx.author.guild_permissions.administrator
            )
        return commands.check(predicate)

    @commands.command(name="kick", help="Kick a member. Usage: !kick @user [reason]")
    @commands.has_permissions(kick_members=True)
    @commands.guild_only()
    async def kick(self, ctx, member: discord.Member, *, reason: str = "No reason provided"):
        if member.top_role >= ctx.author.top_role and ctx.author != ctx.guild.owner:
            return await ctx.send("❌ You cannot kick someone with a role equal to or higher than yours.")

        try:
            await member.send(
                f"⚠️ You have been **kicked** from **{ctx.guild.name}**.\nReason: {reason}"
            )
        except discord.Forbidden:
            pass

        await member.kick(reason=f"{reason} | By {ctx.author}")
        await db.log_mod_action(str(ctx.guild.id), "KICK", str(member.id), str(ctx.author.id), reason)

        embed = discord.Embed(title="👢 Member Kicked", color=discord.Color.orange(), timestamp=datetime.now(timezone.utc))
        embed.add_field(name="User", value=f"{member} (`{member.id}`)", inline=False)
        embed.add_field(name="Moderator", value=str(ctx.author), inline=False)
        embed.add_field(name="Reason", value=reason, inline=False)
        embed.set_footer(text=f"Guild: {ctx.guild.name}")

        await ctx.send(embed=embed)
        await send_log(ctx.guild, embed)

    @commands.command(name="ban", help="Permanently ban a member. Usage: !ban @user [reason]")
    @commands.has_permissions(ban_members=True)
    @commands.guild_only()
    async def ban(self, ctx, member: discord.Member, *, reason: str = "No reason provided"):
        if member.top_role >= ctx.author.top_role and ctx.author != ctx.guild.owner:
            return await ctx.send("❌ You cannot ban someone with a role equal to or higher than yours.")

        try:
            await member.send(
                f"🔨 You have been **permanently banned** from **{ctx.guild.name}**.\nReason: {reason}"
            )
        except discord.Forbidden:
            pass

        await member.ban(reason=f"{reason} | By {ctx.author}", delete_message_days=1)
        await db.add_ban(str(member.id), str(ctx.guild.id), reason, str(ctx.author.id))
        await db.log_mod_action(str(ctx.guild.id), "BAN", str(member.id), str(ctx.author.id), reason)

        embed = discord.Embed(title="🔨 Member Banned", color=discord.Color.red(), timestamp=datetime.now(timezone.utc))
        embed.add_field(name="User", value=f"{member} (`{member.id}`)", inline=False)
        embed.add_field(name="Moderator", value=str(ctx.author), inline=False)
        embed.add_field(name="Reason", value=reason, inline=False)
        embed.add_field(name="Type", value="🔴 Permanent", inline=False)
        embed.set_footer(text=f"Guild: {ctx.guild.name}")

        await ctx.send(embed=embed)
        await send_log(ctx.guild, embed)

    @commands.command(name="tempban", help="Temporarily ban a member. Usage: !tempban @user 1h/1d/1w [reason]")
    @commands.has_permissions(ban_members=True)
    @commands.guild_only()
    async def tempban(self, ctx, member: discord.Member, duration_str: str, *, reason: str = "No reason provided"):
        if member.top_role >= ctx.author.top_role and ctx.author != ctx.guild.owner:
            return await ctx.send("❌ You cannot ban someone with a role equal to or higher than yours.")

        duration = parse_duration(duration_str)
        if not duration:
            return await ctx.send("❌ Invalid duration. Use formats like `30m`, `2h`, `3d`, `1w`.")

        expires_at = datetime.now(timezone.utc) + duration
        expires_str = expires_at.strftime("%Y-%m-%d %H:%M UTC")

        try:
            await member.send(
                f"⏳ You have been **temporarily banned** from **{ctx.guild.name}**.\n"
                f"Duration: `{duration_str}` (until {expires_str})\nReason: {reason}"
            )
        except discord.Forbidden:
            pass

        await member.ban(reason=f"[TEMPBAN {duration_str}] {reason} | By {ctx.author}", delete_message_days=1)
        await db.add_ban(str(member.id), str(ctx.guild.id), reason, str(ctx.author.id), expires_at.isoformat())
        await db.log_mod_action(str(ctx.guild.id), "TEMPBAN", str(member.id), str(ctx.author.id), reason, duration_str)

        embed = discord.Embed(title="⏳ Member Temp-Banned", color=discord.Color.gold(), timestamp=datetime.now(timezone.utc))
        embed.add_field(name="User", value=f"{member} (`{member.id}`)", inline=False)
        embed.add_field(name="Moderator", value=str(ctx.author), inline=False)
        embed.add_field(name="Duration", value=f"`{duration_str}` — expires {expires_str}", inline=False)
        embed.add_field(name="Reason", value=reason, inline=False)
        embed.set_footer(text=f"Guild: {ctx.guild.name}")

        await ctx.send(embed=embed)
        await send_log(ctx.guild, embed)

        await asyncio.sleep(duration.total_seconds())
        try:
            await ctx.guild.unban(member, reason="Temporary ban expired")
            await db.remove_ban(str(member.id), str(ctx.guild.id))
            unban_embed = discord.Embed(
                title="✅ Temp-Ban Expired",
                description=f"{member} (`{member.id}`) has been automatically unbanned.",
                color=discord.Color.green(),
                timestamp=datetime.now(timezone.utc)
            )
            await send_log(ctx.guild, unban_embed)
        except Exception:
            pass

    @commands.command(name="unban", help="Unban a user by ID. Usage: !unban <user_id> [reason]")
    @commands.has_permissions(ban_members=True)
    @commands.guild_only()
    async def unban(self, ctx, user_id: int, *, reason: str = "No reason provided"):
        try:
            user = await self.bot.fetch_user(user_id)
            await ctx.guild.unban(user, reason=f"{reason} | By {ctx.author}")
            await db.remove_ban(str(user_id), str(ctx.guild.id))
            await db.log_mod_action(str(ctx.guild.id), "UNBAN", str(user_id), str(ctx.author.id), reason)

            embed = discord.Embed(title="✅ User Unbanned", color=discord.Color.green(), timestamp=datetime.now(timezone.utc))
            embed.add_field(name="User", value=f"{user} (`{user_id}`)", inline=False)
            embed.add_field(name="Moderator", value=str(ctx.author), inline=False)
            embed.add_field(name="Reason", value=reason, inline=False)

            await ctx.send(embed=embed)
            await send_log(ctx.guild, embed)
        except discord.NotFound:
            await ctx.send("❌ User not found or is not banned.")

    @commands.command(name="mute", help="Timeout a member. Usage: !mute @user 1h [reason]")
    @commands.has_permissions(moderate_members=True)
    @commands.guild_only()
    async def mute(self, ctx, member: discord.Member, duration_str: str, *, reason: str = "No reason provided"):
        duration = parse_duration(duration_str)
        if not duration:
            return await ctx.send("❌ Invalid duration. Use formats like `30m`, `2h`, `3d`.")

        if duration.total_seconds() > 2419200:
            return await ctx.send("❌ Maximum timeout duration is 28 days.")

        until = discord.utils.utcnow() + duration
        await member.timeout(until, reason=f"{reason} | By {ctx.author}")
        await db.log_mod_action(str(ctx.guild.id), "MUTE", str(member.id), str(ctx.author.id), reason, duration_str)

        embed = discord.Embed(title="🔇 Member Muted", color=discord.Color.dark_grey(), timestamp=datetime.now(timezone.utc))
        embed.add_field(name="User", value=f"{member} (`{member.id}`)", inline=False)
        embed.add_field(name="Duration", value=f"`{duration_str}`", inline=False)
        embed.add_field(name="Moderator", value=str(ctx.author), inline=False)
        embed.add_field(name="Reason", value=reason, inline=False)

        await ctx.send(embed=embed)
        await send_log(ctx.guild, embed)

    @commands.command(name="unmute", help="Remove timeout from a member. Usage: !unmute @user")
    @commands.has_permissions(moderate_members=True)
    @commands.guild_only()
    async def unmute(self, ctx, member: discord.Member):
        await member.timeout(None, reason=f"Unmuted by {ctx.author}")
        await db.log_mod_action(str(ctx.guild.id), "UNMUTE", str(member.id), str(ctx.author.id), "Manual unmute")

        embed = discord.Embed(title="🔊 Member Unmuted", color=discord.Color.green(), timestamp=datetime.now(timezone.utc))
        embed.add_field(name="User", value=f"{member} (`{member.id}`)", inline=False)
        embed.add_field(name="Moderator", value=str(ctx.author), inline=False)
        await ctx.send(embed=embed)

    @commands.command(name="purge", help="Delete messages. Usage: !purge <amount> [@user]")
    @commands.has_permissions(manage_messages=True)
    @commands.guild_only()
    async def purge(self, ctx, amount: int, member: discord.Member = None):
        if amount < 1 or amount > 200:
            return await ctx.send("❌ Amount must be between 1 and 200.")

        await ctx.message.delete()

        def check(m):
            if member:
                return m.author == member
            return True

        deleted = await ctx.channel.purge(limit=amount, check=check)
        msg = await ctx.send(f"✅ Deleted **{len(deleted)}** messages.")
        await asyncio.sleep(4)
        await msg.delete()

    @commands.command(name="modlog", help="Show recent moderation actions. Usage: !modlog")
    @commands.has_permissions(kick_members=True)
    @commands.guild_only()
    async def modlog(self, ctx, limit: int = 10):
        rows = await db.get_mod_log(str(ctx.guild.id), min(limit, 20))
        if not rows:
            return await ctx.send("📋 No moderation actions recorded yet.")

        embed = discord.Embed(title="📋 Moderation Log", color=discord.Color.blurple(), timestamp=datetime.now(timezone.utc))
        for action, target_id, moderator_id, reason, extra, executed_at in rows:
            value = f"Target: <@{target_id}>\nModerator: <@{moderator_id}>\nReason: {reason}"
            if extra:
                value += f"\nExtra: {extra}"
            embed.add_field(name=f"[{executed_at[:16]}] {action}", value=value, inline=False)

        await ctx.send(embed=embed)

    @commands.command(name="banlist", help="Show all banned users. Usage: !banlist")
    @commands.has_permissions(ban_members=True)
    @commands.guild_only()
    async def banlist(self, ctx):
        rows = await db.get_all_bans(str(ctx.guild.id))
        if not rows:
            return await ctx.send("📋 No bans recorded in database.")

        embed = discord.Embed(title="🔨 Ban List", color=discord.Color.red(), timestamp=datetime.now(timezone.utc))
        for user_id, reason, banned_by, banned_at, expires_at, permanent in rows[:15]:
            ban_type = "Permanent" if permanent else f"Until {expires_at[:16] if expires_at else 'N/A'}"
            embed.add_field(
                name=f"ID: {user_id}",
                value=f"Reason: {reason}\nBy: <@{banned_by}>\nType: {ban_type}",
                inline=False
            )

        await ctx.send(embed=embed)

    @kick.error
    @ban.error
    @tempban.error
    @unban.error
    @mute.error
    @unmute.error
    @purge.error
    async def mod_error(self, ctx, error):
        if isinstance(error, commands.MissingPermissions):
            await ctx.send("❌ You don't have permission to use this command.")
        elif isinstance(error, commands.MemberNotFound):
            await ctx.send("❌ Member not found.")
        elif isinstance(error, commands.BadArgument):
            await ctx.send("❌ Invalid argument. Check the command usage with `!help`.")
        else:
            await ctx.send(f"❌ An error occurred: {error}")


async def setup(bot):
    await bot.add_cog(Moderation(bot))
