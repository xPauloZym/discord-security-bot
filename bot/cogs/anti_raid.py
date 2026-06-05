import discord
from discord.ext import commands
from datetime import datetime, timezone, timedelta
from collections import defaultdict
import asyncio
from bot import database as db
from bot.config import (
    ANTI_RAID_JOIN_THRESHOLD,
    ANTI_RAID_JOIN_WINDOW,
    ANTI_RAID_MENTION_THRESHOLD,
    ANTI_RAID_MENTION_WINDOW,
    ACCOUNT_AGE_THRESHOLD_DAYS,
    LOG_CHANNEL_NAME,
)
from bot.cogs.moderation import send_log


class AntiRaid(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self._join_times: dict[int, list[datetime]] = defaultdict(list)
        self._mention_times: dict[int, list[datetime]] = defaultdict(list)
        self._raid_mode: set[int] = set()
        self._raid_lock_task: dict[int, asyncio.Task] = {}

    async def _enable_raid_mode(self, guild: discord.Guild, reason: str):
        if guild.id in self._raid_mode:
            return
        self._raid_mode.add(guild.id)

        await db.log_raid_event(str(guild.id), "RAID_MODE_ENABLED", details=reason)

        try:
            old_level = guild.verification_level
            await guild.edit(verification_level=discord.VerificationLevel.high)
        except discord.Forbidden:
            old_level = None

        log_channel = discord.utils.get(guild.text_channels, name=LOG_CHANNEL_NAME)
        if log_channel:
            embed = discord.Embed(
                title="🚨 RAID MODE ACTIVATED",
                description=f"**Reason:** {reason}\n\nVerification level raised to **High**. New accounts will have a harder time joining.",
                color=discord.Color.dark_red(),
                timestamp=datetime.now(timezone.utc)
            )
            embed.set_footer(text="Raid mode will automatically disable in 10 minutes.")
            await log_channel.send("@here", embed=embed)

        if guild.id in self._raid_lock_task:
            self._raid_lock_task[guild.id].cancel()

        async def auto_disable():
            await asyncio.sleep(600)
            await self._disable_raid_mode(guild, old_level, auto=True)

        self._raid_lock_task[guild.id] = asyncio.create_task(auto_disable())

    async def _disable_raid_mode(self, guild: discord.Guild, old_level=None, auto=False):
        if guild.id not in self._raid_mode:
            return
        self._raid_mode.discard(guild.id)

        try:
            if old_level is not None:
                await guild.edit(verification_level=old_level)
        except discord.Forbidden:
            pass

        await db.log_raid_event(str(guild.id), "RAID_MODE_DISABLED", details="auto" if auto else "manual")

        log_channel = discord.utils.get(guild.text_channels, name=LOG_CHANNEL_NAME)
        if log_channel:
            embed = discord.Embed(
                title="✅ Raid Mode Deactivated",
                description="Server is back to normal. Verification level restored.",
                color=discord.Color.green(),
                timestamp=datetime.now(timezone.utc)
            )
            await log_channel.send(embed=embed)

    @commands.Cog.listener()
    async def on_member_join(self, member: discord.Member):
        guild = member.guild
        now = datetime.now(timezone.utc)

        account_age = now - member.created_at.replace(tzinfo=timezone.utc)
        if account_age.days < ACCOUNT_AGE_THRESHOLD_DAYS:
            await db.log_raid_event(
                str(guild.id), "NEW_ACCOUNT_JOIN",
                str(member.id),
                f"Account age: {account_age.days}d"
            )
            log_channel = discord.utils.get(guild.text_channels, name=LOG_CHANNEL_NAME)
            if log_channel:
                embed = discord.Embed(
                    title="⚠️ New Account Joined",
                    description=f"{member.mention} joined with a very new account.",
                    color=discord.Color.yellow(),
                    timestamp=now
                )
                embed.add_field(name="Account Age", value=f"{account_age.days} days old", inline=True)
                embed.add_field(name="User ID", value=f"`{member.id}`", inline=True)
                embed.set_thumbnail(url=member.display_avatar.url)
                await log_channel.send(embed=embed)

        user_ips = await db.get_ips_by_user(str(member.id), str(guild.id))
        for ip in user_ips:
            if await db.is_ip_banned(ip, str(guild.id)):
                try:
                    await member.ban(
                        reason=f"[AUTO IP BAN] Joined with banned IP: {ip}",
                        delete_message_days=1
                    )
                    await db.add_ban(str(member.id), str(guild.id), f"[AUTO IP BAN] Banned IP: {ip}", "BOT")
                    await db.log_raid_event(str(guild.id), "AUTO_IP_BAN", str(member.id), f"IP: {ip}")

                    log_channel = discord.utils.get(guild.text_channels, name=LOG_CHANNEL_NAME)
                    if log_channel:
                        embed = discord.Embed(
                            title="🚫 Auto IP-Ban on Join",
                            description=f"{member} (`{member.id}`) was **automatically banned** for joining with a banned IP.",
                            color=discord.Color.dark_red(),
                            timestamp=now
                        )
                        embed.add_field(name="Banned IP", value=f"`{ip}`", inline=False)
                        await log_channel.send(embed=embed)
                except Exception:
                    pass
                return

        _, mains = await db.get_alts(str(member.id), str(guild.id))
        for main_id in mains:
            ban_record = await db.is_banned(main_id, str(guild.id))
            if ban_record:
                try:
                    await member.ban(
                        reason=f"[AUTO ALT BAN] Alt of banned user {main_id}",
                        delete_message_days=1
                    )
                    await db.add_ban(str(member.id), str(guild.id), f"Alt of banned user {main_id}", "BOT")
                    await db.log_raid_event(str(guild.id), "AUTO_ALT_BAN", str(member.id), f"Main: {main_id}")

                    log_channel = discord.utils.get(guild.text_channels, name=LOG_CHANNEL_NAME)
                    if log_channel:
                        embed = discord.Embed(
                            title="🚫 Auto Alt-Ban on Join",
                            description=f"{member} (`{member.id}`) was **automatically banned** as an alt of a banned user.",
                            color=discord.Color.dark_red(),
                            timestamp=now
                        )
                        embed.add_field(name="Banned Main", value=f"<@{main_id}> (`{main_id}`)", inline=False)
                        await log_channel.send(embed=embed)
                except Exception:
                    pass
                return

        self._join_times[guild.id].append(now)
        self._join_times[guild.id] = [
            t for t in self._join_times[guild.id]
            if (now - t).total_seconds() <= ANTI_RAID_JOIN_WINDOW
        ]

        if len(self._join_times[guild.id]) >= ANTI_RAID_JOIN_THRESHOLD:
            await self._enable_raid_mode(
                guild,
                f"{len(self._join_times[guild.id])} joins in {ANTI_RAID_JOIN_WINDOW}s"
            )

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        if message.author.bot or not message.guild:
            return

        guild = message.guild
        now = datetime.now(timezone.utc)

        mention_count = len(message.mentions) + len(message.role_mentions)
        if mention_count >= 5:
            uid = message.author.id
            self._mention_times[uid].append(now)
            self._mention_times[uid] = [
                t for t in self._mention_times[uid]
                if (now - t).total_seconds() <= ANTI_RAID_MENTION_WINDOW
            ]

            total_mentions = sum(
                len(message.mentions) for _ in self._mention_times[uid]
            )

            if len(self._mention_times[uid]) >= 2 or mention_count >= ANTI_RAID_MENTION_THRESHOLD:
                try:
                    await message.delete()
                    timeout_until = discord.utils.utcnow() + timedelta(minutes=10)
                    await message.author.timeout(timeout_until, reason="Mass mention / spam")
                    await db.log_mod_action(
                        str(guild.id), "AUTO_MUTE", str(message.author.id),
                        "BOT", f"Mass mention: {mention_count} mentions"
                    )
                    await db.log_raid_event(
                        str(guild.id), "MASS_MENTION",
                        str(message.author.id),
                        f"{mention_count} mentions in one message"
                    )

                    log_channel = discord.utils.get(guild.text_channels, name=LOG_CHANNEL_NAME)
                    if log_channel:
                        embed = discord.Embed(
                            title="🔇 Auto-Mute: Mass Mention",
                            description=f"{message.author.mention} was **auto-muted** for mass mentioning.",
                            color=discord.Color.orange(),
                            timestamp=now
                        )
                        embed.add_field(name="Mentions in message", value=str(mention_count), inline=True)
                        embed.add_field(name="Duration", value="10 minutes", inline=True)
                        await log_channel.send(embed=embed)
                except Exception:
                    pass

    @commands.command(name="raidmode", help="Manually toggle raid mode. Usage: !raidmode on/off")
    @commands.has_permissions(administrator=True)
    @commands.guild_only()
    async def raid_mode(self, ctx, toggle: str):
        toggle = toggle.lower()
        if toggle in ("on", "enable", "ativar"):
            await self._enable_raid_mode(ctx.guild, f"Manually enabled by {ctx.author}")
            await ctx.send("🚨 **Raid mode ENABLED** manually.")
        elif toggle in ("off", "disable", "desativar"):
            await self._disable_raid_mode(ctx.guild)
            await ctx.send("✅ **Raid mode DISABLED** manually.")
        else:
            await ctx.send("❌ Use `!raidmode on` or `!raidmode off`.")

    @commands.command(name="raidstatus", help="Check if raid mode is active. Usage: !raidstatus")
    @commands.has_permissions(kick_members=True)
    @commands.guild_only()
    async def raid_status(self, ctx):
        active = ctx.guild.id in self._raid_mode
        embed = discord.Embed(
            title="🛡️ Raid Mode Status",
            description="🚨 **ACTIVE**" if active else "✅ **Inactive**",
            color=discord.Color.red() if active else discord.Color.green(),
            timestamp=datetime.now(timezone.utc)
        )
        embed.add_field(name="Account Age Filter", value=f"< {ACCOUNT_AGE_THRESHOLD_DAYS} days → flagged", inline=False)
        embed.add_field(name="Join Trigger", value=f"{ANTI_RAID_JOIN_THRESHOLD} joins in {ANTI_RAID_JOIN_WINDOW}s", inline=False)
        await ctx.send(embed=embed)

    @raid_mode.error
    async def raid_error(self, ctx, error):
        if isinstance(error, commands.MissingPermissions):
            await ctx.send("❌ You need **Administrator** permission.")
        else:
            await ctx.send(f"❌ Error: {error}")


async def setup(bot):
    await bot.add_cog(AntiRaid(bot))
