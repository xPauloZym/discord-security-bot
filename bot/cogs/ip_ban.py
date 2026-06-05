import discord
from discord.ext import commands
from datetime import datetime, timezone
from bot import database as db
from bot.cogs.moderation import send_log


class IPBan(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(name="registerip", help="Link an IP to a user. Usage: !registerip @user <ip>")
    @commands.has_permissions(administrator=True)
    @commands.guild_only()
    async def register_ip(self, ctx, member: discord.Member, ip: str):
        await db.register_ip(str(member.id), ip, str(ctx.guild.id), str(ctx.author.id))

        is_banned = await db.is_ip_banned(ip, str(ctx.guild.id))
        if is_banned:
            embed = discord.Embed(
                title="🚨 Banned IP Detected on Registration!",
                description=f"{member.mention} was linked to a **banned IP**: `{ip}`",
                color=discord.Color.dark_red(),
                timestamp=datetime.now(timezone.utc)
            )
            embed.add_field(name="Action", value="Consider banning this user immediately.", inline=False)
            await ctx.send(embed=embed)
            await send_log(ctx.guild, embed)
            return

        users_on_ip = await db.get_users_by_ip(ip, str(ctx.guild.id))
        banned_users = []
        for uid in users_on_ip:
            if uid != str(member.id):
                ban_record = await db.is_banned(uid, str(ctx.guild.id))
                if ban_record:
                    banned_users.append(uid)

        embed = discord.Embed(
            title="🗂️ IP Registered",
            color=discord.Color.green() if not banned_users else discord.Color.red(),
            timestamp=datetime.now(timezone.utc)
        )
        embed.add_field(name="User", value=f"{member} (`{member.id}`)", inline=False)
        embed.add_field(name="IP", value=f"`{ip}`", inline=False)
        embed.add_field(name="Registered By", value=str(ctx.author), inline=False)

        if banned_users:
            embed.title = "⚠️ IP Registered — Banned Accounts Found on Same IP!"
            embed.add_field(
                name="⚠️ Banned accounts on this IP",
                value="\n".join(f"<@{uid}> (`{uid}`)" for uid in banned_users),
                inline=False
            )
            embed.color = discord.Color.dark_red()

        await ctx.send(embed=embed)
        await send_log(ctx.guild, embed)

    @commands.command(name="ipban", help="Ban an IP address. Usage: !ipban <ip> [reason]")
    @commands.has_permissions(administrator=True)
    @commands.guild_only()
    async def ip_ban(self, ctx, ip: str, *, reason: str = "No reason provided"):
        existing = await db.is_ip_banned(ip, str(ctx.guild.id))
        if existing:
            return await ctx.send(f"⚠️ IP `{ip}` is already banned.")

        await db.add_ip_ban(ip, str(ctx.guild.id), reason, str(ctx.author.id))
        await db.log_mod_action(str(ctx.guild.id), "IP_BAN", ip, str(ctx.author.id), reason)

        affected_users = await db.get_users_by_ip(ip, str(ctx.guild.id))

        embed = discord.Embed(
            title="🚫 IP Banned",
            color=discord.Color.dark_red(),
            timestamp=datetime.now(timezone.utc)
        )
        embed.add_field(name="IP Address", value=f"`{ip}`", inline=False)
        embed.add_field(name="Reason", value=reason, inline=False)
        embed.add_field(name="Banned By", value=str(ctx.author), inline=False)

        if affected_users:
            embed.add_field(
                name=f"⚠️ {len(affected_users)} known account(s) on this IP",
                value="\n".join(f"<@{uid}> (`{uid}`)" for uid in affected_users[:10]),
                inline=False
            )
            auto_banned = []
            for uid in affected_users:
                try:
                    member = ctx.guild.get_member(int(uid))
                    if member:
                        await member.ban(
                            reason=f"[IP BAN] {reason} | IP: {ip} | By {ctx.author}",
                            delete_message_days=1
                        )
                        await db.add_ban(uid, str(ctx.guild.id), f"[IP BAN] {reason}", str(ctx.author.id))
                        auto_banned.append(uid)
                except Exception:
                    pass
            if auto_banned:
                embed.add_field(
                    name="✅ Auto-banned from server",
                    value="\n".join(f"<@{uid}>" for uid in auto_banned),
                    inline=False
                )

        await ctx.send(embed=embed)
        await send_log(ctx.guild, embed)

    @commands.command(name="ipunban", help="Remove an IP ban. Usage: !ipunban <ip>")
    @commands.has_permissions(administrator=True)
    @commands.guild_only()
    async def ip_unban(self, ctx, ip: str):
        existing = await db.is_ip_banned(ip, str(ctx.guild.id))
        if not existing:
            return await ctx.send(f"⚠️ IP `{ip}` is not banned.")

        await db.remove_ip_ban(ip, str(ctx.guild.id))

        embed = discord.Embed(
            title="✅ IP Unbanned",
            color=discord.Color.green(),
            timestamp=datetime.now(timezone.utc)
        )
        embed.add_field(name="IP Address", value=f"`{ip}`", inline=False)
        embed.add_field(name="Removed By", value=str(ctx.author), inline=False)

        await ctx.send(embed=embed)
        await send_log(ctx.guild, embed)

    @commands.command(name="checkip", help="Check what users are linked to an IP. Usage: !checkip <ip>")
    @commands.has_permissions(administrator=True)
    @commands.guild_only()
    async def check_ip(self, ctx, ip: str):
        users = await db.get_users_by_ip(ip, str(ctx.guild.id))
        is_banned = await db.is_ip_banned(ip, str(ctx.guild.id))

        embed = discord.Embed(
            title=f"🔍 IP Lookup: `{ip}`",
            color=discord.Color.red() if is_banned else discord.Color.blurple(),
            timestamp=datetime.now(timezone.utc)
        )
        embed.add_field(name="Status", value="🚫 **BANNED**" if is_banned else "✅ Not banned", inline=False)

        if users:
            embed.add_field(
                name=f"Linked Accounts ({len(users)})",
                value="\n".join(f"<@{uid}> (`{uid}`)" for uid in users[:15]),
                inline=False
            )
        else:
            embed.add_field(name="Linked Accounts", value="None registered", inline=False)

        await ctx.send(embed=embed)

    @commands.command(name="checkuser", help="Check what IPs are linked to a user. Usage: !checkuser @user")
    @commands.has_permissions(administrator=True)
    @commands.guild_only()
    async def check_user(self, ctx, member: discord.Member):
        ips = await db.get_ips_by_user(str(member.id), str(ctx.guild.id))
        alts, mains = await db.get_alts(str(member.id), str(ctx.guild.id))
        ban_record = await db.is_banned(str(member.id), str(ctx.guild.id))

        embed = discord.Embed(
            title=f"🔍 User Lookup: {member}",
            color=discord.Color.red() if ban_record else discord.Color.blurple(),
            timestamp=datetime.now(timezone.utc)
        )
        embed.set_thumbnail(url=member.display_avatar.url)
        embed.add_field(name="ID", value=f"`{member.id}`", inline=True)
        embed.add_field(name="Account Created", value=f"<t:{int(member.created_at.timestamp())}:R>", inline=True)
        embed.add_field(name="Joined Server", value=f"<t:{int(member.joined_at.timestamp())}:R>" if member.joined_at else "Unknown", inline=True)
        embed.add_field(name="Ban Status", value="🔴 **BANNED**" if ban_record else "✅ Not banned", inline=False)

        if ips:
            ip_status = []
            for ip in ips:
                banned = await db.is_ip_banned(ip, str(ctx.guild.id))
                status = "🚫 BANNED" if banned else "✅"
                ip_status.append(f"`{ip}` {status}")
            embed.add_field(name="Registered IPs", value="\n".join(ip_status), inline=False)
        else:
            embed.add_field(name="Registered IPs", value="None", inline=False)

        if alts:
            embed.add_field(name="Known Alt Accounts", value="\n".join(f"<@{a}>" for a in alts), inline=False)
        if mains:
            embed.add_field(name="Main Account(s)", value="\n".join(f"<@{m}>" for m in mains), inline=False)

        await ctx.send(embed=embed)

    @commands.command(name="ipbanlist", help="List all banned IPs. Usage: !ipbanlist")
    @commands.has_permissions(administrator=True)
    @commands.guild_only()
    async def ip_ban_list(self, ctx):
        rows = await db.get_all_ip_bans(str(ctx.guild.id))
        if not rows:
            return await ctx.send("📋 No IPs are currently banned.")

        embed = discord.Embed(
            title="🚫 Banned IPs",
            color=discord.Color.dark_red(),
            timestamp=datetime.now(timezone.utc)
        )
        for ip, reason, banned_by, banned_at in rows[:15]:
            embed.add_field(
                name=f"`{ip}`",
                value=f"Reason: {reason}\nBy: <@{banned_by}>\nAt: {banned_at[:16]}",
                inline=False
            )

        await ctx.send(embed=embed)

    @commands.command(name="registeralt", help="Register an alt account. Usage: !registeralt @main @alt")
    @commands.has_permissions(administrator=True)
    @commands.guild_only()
    async def register_alt(self, ctx, main: discord.Member, alt: discord.Member):
        await db.register_alt(str(main.id), str(alt.id), str(ctx.guild.id), str(ctx.author.id))

        ban_record = await db.is_banned(str(main.id), str(ctx.guild.id))

        embed = discord.Embed(
            title="🔗 Alt Account Registered",
            color=discord.Color.orange() if ban_record else discord.Color.green(),
            timestamp=datetime.now(timezone.utc)
        )
        embed.add_field(name="Main Account", value=f"{main} (`{main.id}`)", inline=False)
        embed.add_field(name="Alt Account", value=f"{alt} (`{alt.id}`)", inline=False)
        embed.add_field(name="Registered By", value=str(ctx.author), inline=False)

        if ban_record:
            embed.add_field(
                name="⚠️ Warning",
                value=f"The main account **{main}** is BANNED. Consider banning the alt too!",
                inline=False
            )

        await ctx.send(embed=embed)
        await send_log(ctx.guild, embed)

    @register_ip.error
    @ip_ban.error
    @ip_unban.error
    @check_ip.error
    @check_user.error
    @register_alt.error
    async def ip_error(self, ctx, error):
        if isinstance(error, commands.MissingPermissions):
            await ctx.send("❌ You need **Administrator** permission to use this command.")
        else:
            await ctx.send(f"❌ Error: {error}")


async def setup(bot):
    await bot.add_cog(IPBan(bot))
