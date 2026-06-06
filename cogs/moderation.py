import asyncio
import re
from datetime import timedelta
import discord
from discord.ext import commands

class Moderation(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    def parse_time(self, time_str: str):
        """시간 문자열(s, m, h, d)을 초 단위 정수로 변환합니다."""
        if not time_str:
            return None
        if time_str.isdigit():
            return int(time_str)
        match = re.match(r"(\d+)([smhd])", time_str.lower())
        if not match:
            return None
        amount, unit = int(match.group(1)), match.group(2)
        unit_map = {'s': 1, 'm': 60, 'h': 3600, 'd': 86400}
        return amount * unit_map[unit]

    async def cog_check(self, ctx):
        """명령어 실행 전 채널 및 권한을 확인합니다."""
        if not ctx.guild:
            return False
        settings = self.bot.get_cog('Settings')
        if settings:
            data = settings.get_server_data(ctx.guild)
            cmd_id = data.get("command_channel_id")
            if cmd_id and ctx.channel.id != cmd_id:
                return ctx.author.guild_permissions.administrator
        return True

    @commands.command(name="mute")
    @commands.has_permissions(administrator=True)
    async def server_mute(self, ctx, member: discord.Member = None, time: str = None):
        if not member:
            return await ctx.send(embed=discord.Embed(description="❌ 대상을 지정해주세요.", color=0x808080))
        if not member.voice:
            return await ctx.send(embed=discord.Embed(description="❌ 대상이 음성 채널에 없습니다.", color=0x808080))

        seconds = self.parse_time(time)
        
        try:
            await member.edit(mute=True, reason=f"실행자: {ctx.author} ({time or '무기한'})")
        except discord.Forbidden:
            return await ctx.send(embed=discord.Embed(description="❌ 봇의 권한이 부족하거나 대상의 역할이 더 높습니다.", color=0x808080))
        except discord.HTTPException as e:
            return await ctx.send(embed=discord.Embed(description=f"❌ 차단 실패: {e}", color=0x808080))

        embed = discord.Embed(description=f"🔇 {member.mention} 마이크 차단 ({time or '무기한'})", color=0x808080)
        await ctx.send(embed=embed)
        
        logger = self.bot.get_cog('Logger')
        if logger:
            await logger.send_log(ctx.guild, embed, type="punish")

        if seconds:
            await asyncio.sleep(seconds)
            try:
                if member.guild.get_member(member.id) and member.voice:
                    await member.edit(mute=False, reason="시간 종료로 인한 뮤트 해제")
                    unmute_embed = discord.Embed(description=f"🔊 {member.mention} 뮤트 해제 (시간 종료)", color=0x808080)
                    if logger: 
                        await logger.send_log(ctx.guild, unmute_embed, type="punish")
            except Exception:
                pass

    @commands.command(name="unmute")
    @commands.has_permissions(administrator=True)
    async def server_unmute(self, ctx, member: discord.Member = None):
        if not member:
            return await ctx.send(embed=discord.Embed(description="❌ 대상을 지정해주세요.", color=0x808080))
        if not member.voice:
            return await ctx.send(embed=discord.Embed(description="❌ 대상이 음성 채널에 없습니다.", color=0x808080))

        try:
            await member.edit(mute=False, reason=f"실행자: {ctx.author}")
        except discord.Forbidden:
            return await ctx.send(embed=discord.Embed(description="❌ 권한이 없습니다.", color=0x808080))

        embed = discord.Embed(description=f"🔊 {member.mention} 마이크 차단 해제", color=0x808080)
        await ctx.send(embed=embed)
        logger = self.bot.get_cog('Logger')
        if logger:
            await logger.send_log(ctx.guild, embed, type="punish")

    @commands.command(name="deafen")
    @commands.has_permissions(administrator=True)
    async def server_deafen(self, ctx, member: discord.Member = None, time: str = None):
        if not member:
            return await ctx.send(embed=discord.Embed(description="❌ 대상을 지정해주세요.", color=0x808080))
        if not member.voice:
            return await ctx.send(embed=discord.Embed(description="❌ 대상이 음성 채널에 없습니다.", color=0x808080))

        seconds = self.parse_time(time)
        try:
            await member.edit(deafen=True, reason=f"실행자: {ctx.author} ({time or '무기한'})")
        except discord.Forbidden:
            return await ctx.send(embed=discord.Embed(description="❌ 봇의 권한이 부족합니다.", color=0x808080))

        embed = discord.Embed(description=f"🔇 {member.mention} 헤드셋 차단 ({time or '무기한'})", color=0x808080)
        await ctx.send(embed=embed)
        logger = self.bot.get_cog('Logger')
        if logger: 
            await logger.send_log(ctx.guild, embed, type="punish")

        if seconds:
            await asyncio.sleep(seconds)
            try:
                if member.guild.get_member(member.id) and member.voice:
                    await member.edit(deafen=False, reason="시간 종료로 인한 헤드셋 차단 해제")
                    undeafen_embed = discord.Embed(description=f"🔊 {member.mention} 헤드셋 차단 해제 (시간 종료)", color=0x808080)
                    if logger:
                        await logger.send_log(ctx.guild, undeafen_embed, type="punish")
            except Exception:
                pass

    @commands.command(name="undeafen")
    @commands.has_permissions(administrator=True)
    async def server_undeafen(self, ctx, member: discord.Member = None):
        if not member:
            return await ctx.send(embed=discord.Embed(description="❌ 대상을 지정해주세요.", color=0x808080))
        if not member.voice:
            return await ctx.send(embed=discord.Embed(description="❌ 대상이 음성 채널에 없습니다.", color=0x808080))

        try:
            await member.edit(deafen=False, reason=f"실행자: {ctx.author}")
        except discord.Forbidden:
            return await ctx.send(embed=discord.Embed(description="❌ 권한이 없습니다.", color=0x808080))

        embed = discord.Embed(description=f"🔊 {member.mention} 헤드셋 차단 해제", color=0x808080)
        await ctx.send(embed=embed)
        logger = self.bot.get_cog('Logger')
        if logger:
            await logger.send_log(ctx.guild, embed, type="punish")

    @commands.command(name="vckick")
    @commands.has_permissions(administrator=True)
    async def server_vckick(self, ctx, member: discord.Member = None, *, reason="사유 없음"):
        if not member:
            return await ctx.send(embed=discord.Embed(description="❌ 대상을 지정해주세요.", color=0x808080))
        if not member.voice:
            return await ctx.send(embed=discord.Embed(description="❌ 대상이 음성 채널에 없습니다.", color=0x808080))

        try:
            await member.move_to(None, reason=f"실행자: {ctx.author} | {reason}")
        except discord.Forbidden:
            return await ctx.send(embed=discord.Embed(description="❌ 권한이 없습니다.", color=0x808080))

        embed = discord.Embed(
            title="👟 음성 강제 퇴장",
            description=f"{member.mention} 퇴장됨\n사유: {reason}",
            color=0x808080
        )
        await ctx.send(embed=embed)
        logger = self.bot.get_cog('Logger')
        if logger:
            await logger.send_log(ctx.guild, embed, type="punish")

    @commands.command(name="timeout")
    @commands.has_permissions(administrator=True)
    async def server_timeout(self, ctx, member: discord.Member = None, time: str = None, *, reason="사유 없음"):
        seconds = self.parse_time(time)
        if not member or not seconds:
            embed = discord.Embed(
                description=f"❓ 사용법: `{ctx.prefix}timeout @유저 [시간] [사유]`\n"
                            f"예: `{ctx.prefix}timeout @유저 10m 도배`",
                color=0x808080
            )
            return await ctx.send(embed=embed)

        try:
            await member.timeout(timedelta(seconds=seconds), reason=f"실행자: {ctx.author} | {reason}")
            embed = discord.Embed(
                title="⏳ 타임아웃",
                description=f"{member.mention} ({time} 동안 채팅/음성 제한)\n사유: {reason}",
                color=0x808080
            )
            await ctx.send(embed=embed)
            logger = self.bot.get_cog('Logger')
            if logger: 
                await logger.send_log(ctx.guild, embed, type="punish")
        except discord.Forbidden:
            await ctx.send(embed=discord.Embed(description="❌ 이 유저에게 타임아웃을 적용할 권한이 없습니다 (역할 서열 확인).", color=0x808080))
        except Exception as e:
            await ctx.send(embed=discord.Embed(description=f"❌ 오류: {e}", color=0x808080))

    @commands.command(name="untimeout")
    @commands.has_permissions(administrator=True)
    async def server_untimeout(self, ctx, member: discord.Member = None, *, reason="관리자에 의한 해제"):
        if not member:
            embed = discord.Embed(description=f"❓ 사용법: `{ctx.prefix}untimeout @유저`", color=0x808080)
            return await ctx.send(embed=embed)

        if not member.timed_out_until:
            embed = discord.Embed(description=f"❌ {member.mention} 님은 현재 타임아웃 상태가 아닙니다.", color=0x808080)
            return await ctx.send(embed=embed)

        try:
            await member.timeout(None, reason=f"실행자: {ctx.author} | {reason}")
            embed = discord.Embed(
                title="✅ 타임아웃 해제",
                description=f"{member.mention} 님의 타임아웃이 해제되었습니다.",
                color=0x808080
            )
            await ctx.send(embed=embed)
            logger = self.bot.get_cog('Logger')
            if logger:
                await logger.send_log(ctx.guild, embed, type="punish")
        except discord.Forbidden:
            await ctx.send(embed=discord.Embed(description="❌ 권한이 없어 타임아웃을 해제할 수 없습니다.", color=0x808080))
        except Exception as e:
            await ctx.send(embed=discord.Embed(description=f"❌ 오류 발생: {e}", color=0x808080))

    @commands.command(name="kick")
    @commands.has_permissions(kick_members=True)
    async def server_kick(self, ctx, member: discord.Member = None, *, reason="사유 없음"):
        if not member:
            embed = discord.Embed(description=f"❓ 사용법: `{ctx.prefix}kick @유저 [사유]`", color=0x808080)
            return await ctx.send(embed=embed)
            
        try:
            await member.kick(reason=f"실행자: {ctx.author} | {reason}")
            embed = discord.Embed(title="👞 추방 완료", description=f"{member.mention} 추방됨\n사유: {reason}", color=0x808080)
            await ctx.send(embed=embed)
            logger = self.bot.get_cog('Logger')
            if logger:
                await logger.send_log(ctx.guild, embed, type="punish")
        except discord.Forbidden:
            await ctx.send(embed=discord.Embed(description="❌ 이 유저를 추방할 권한이 없습니다.", color=0x808080))

    @commands.command(name="ban")
    @commands.has_permissions(ban_members=True)
    async def server_ban(self, ctx, member: discord.Member = None, *, reason="사유 없음"):
        if not member:
            embed = discord.Embed(description=f"❓ 사용법: `{ctx.prefix}ban [유저멘션/ID] [사유]`", color=0x808080)
            return await ctx.send(embed=embed)

        try:
            await member.ban(reason=f"실행자: {ctx.author} | {reason}", delete_message_seconds=86400)
            embed = discord.Embed(title="🚫 차단 완료", description=f"{member.mention} 차단됨\n사유: {reason}", color=0x808080)
            await ctx.send(embed=embed)
            logger = self.bot.get_cog('Logger')
            if logger:
                await logger.send_log(ctx.guild, embed, type="punish")
        except discord.Forbidden:
            await ctx.send(embed=discord.Embed(description="❌ 이 유저를 차단할 권한이 없습니다.", color=0x808080))

    @commands.command(name="unban")
    @commands.has_permissions(ban_members=True)
    async def server_unban(self, ctx, *, user_spec: str = None):
        if not user_spec:
            embed = discord.Embed(description=f"❓ 사용법: `{ctx.prefix}unban [이름#태그] 또는 [ID]`", color=0x808080)
            return await ctx.send(embed=embed)

        if user_spec.isdigit():
            try:
                user_id = int(user_spec)
                await ctx.guild.unban(discord.Object(id=user_id))
                embed = discord.Embed(title="✅ 차단 해제", description=f"ID: {user_id} 유저 해제됨", color=0x808080)
                await ctx.send(embed=embed)
                logger = self.bot.get_cog('Logger')
                if logger:
                    await logger.send_log(ctx.guild, embed, type="punish")
                return
            except discord.NotFound:
                return await ctx.send(embed=discord.Embed(description="❌ 차단 목록에서 해당 ID를 찾을 수 없습니다.", color=0x808080))
            except discord.Forbidden:
                return await ctx.send(embed=discord.Embed(description="❌ 권한이 부족하여 차단을 해제할 수 없습니다.", color=0x808080))

        try:
            async for entry in ctx.guild.bans():
                if user_spec == str(entry.user):
                    await ctx.guild.unban(entry.user)
                    embed = discord.Embed(title="✅ 차단 해제", description=f"{entry.user} 해제됨", color=0x808080)
                    await ctx.send(embed=embed)
                    logger = self.bot.get_cog('Logger')
                    if logger:
                        await logger.send_log(ctx.guild, embed, type="punish")
                    return
            await ctx.send(embed=discord.Embed(description="❌ 차단 목록에서 찾을 수 없습니다.", color=0x808080))
        except discord.Forbidden:
            await ctx.send(embed=discord.Embed(description="❌ 봇에게 서버 차단 해제 권한이 없습니다.", color=0x808080))


async def setup(bot):
    await bot.add_cog(Moderation(bot))