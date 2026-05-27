from datetime import datetime, timezone
import discord
from discord.ext import commands

class Logger(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    def escape_code_blocks(self, text: str) -> str:
        """메시지 내 코드 블록 부호가 임베드를 망가뜨리지 않게 이스케이프함"""
        if not text:
            return ""
        return text.replace("`", " \` ")

    def truncate_text(self, text: str, max_length: int = 1000) -> str:
        """디스코드 글자 수 제한으로 인한 에러를 방지하기 위해 텍스트를 잘라냄"""
        if not text:
            return ""
        if len(text) > max_length:
            return text[:max_length - 3] + "..."
        return text

    def get_log_channel(self, guild, type="general"):
        settings = self.bot.get_cog('Settings')
        if not settings:
            return guild.system_channel

        data = settings.get_server_data(guild)
        if type == "punish":
            chn_id = data.get("punish_log_channel_id") or data.get("server_log_channel_id")
        elif type == "ticket":
            chn_id = data.get("ticket_log_channel_id") or data.get("server_log_channel_id")
        else:
            chn_id = data.get("server_log_channel_id")

        return self.bot.get_channel(chn_id) if chn_id else guild.system_channel

    async def send_log(self, guild, embed, type="general"):
        log_channel = self.get_log_channel(guild, type)
        if log_channel and log_channel.permissions_for(guild.me).send_messages:
            if not embed.timestamp:
                embed.timestamp = datetime.now(timezone.utc)
            await log_channel.send(embed=embed)

    @commands.Cog.listener()
    async def on_member_join(self, member):
        embed = discord.Embed(
            title="📥 멤버 입장",
            description=f"{member.mention} **{member}** 님이 입장했습니다.",
            color=0x808080
        )
        embed.set_thumbnail(url=member.display_avatar.url)
        embed.set_footer(text=f"ID: {member.id} | 총 멤버: {member.guild.member_count}명")
        await self.send_log(member.guild, embed)

    @commands.Cog.listener()
    async def on_member_remove(self, member):
        embed = discord.Embed(
            title="📤 멤버 퇴장",
            description=f"**{member}** 님이 서버를 떠났습니다.",
            color=0x808080
        )
        embed.set_footer(text=f"ID: {member.id} | 남은 멤버: {member.guild.member_count}명")
        await self.send_log(member.guild, embed)

    @commands.Cog.listener()
    async def on_raw_message_edit(self, payload):
        if not payload.guild_id:
            return

        after_content = payload.data.get('content')
        if after_content is None:
            return

        guild = self.bot.get_guild(payload.guild_id)
        if not guild:
            return
        
        author_name = "알 수 없음"
        author_icon = None
        before_content = "캐시에 없음 (봇 재시작 전 메시지)"

        if payload.cached_message:
            if payload.cached_message.author.bot:
                return
            
            if payload.cached_message.content == after_content:
                return

            author = payload.cached_message.author
            author_name = str(author)
            author_icon = author.display_avatar.url
            before_content = self.escape_code_blocks(payload.cached_message.content)
        else:
            try:
                channel = guild.get_channel(payload.channel_id)
                msg = await channel.fetch_message(payload.message_id)
                if msg.author.bot: 
                    return
                author_name = str(msg.author)
                author_icon = msg.author.display_avatar.url
                before_content = "캐시에 없음 (수정 전 내용 확인 불가)"
            except Exception:
                pass

        before_content = self.truncate_text(before_content, 1000)
        after_content = self.truncate_text(self.escape_code_blocks(after_content), 1000)

        embed = discord.Embed(
            title="📝 메시지 수정됨", 
            description=f"[메시지 바로가기](https://discord.com/channels/{payload.guild_id}/{payload.channel_id}/{payload.message_id})",
            color=0x808080
        )

        embed.set_author(name=author_name, icon_url=author_icon)
        embed.add_field(name="수정 전", value=f"```{before_content or '내용 없음'}```", inline=False)
        embed.add_field(name="수정 후", value=f"```{after_content or '내용 없음'}```", inline=False)
        await self.send_log(guild, embed)

    @commands.Cog.listener()
    async def on_message_delete(self, message):
        if message.author.bot or not message.guild:
            return
            
        embed = discord.Embed(title="🗑️ 메시지 삭제됨", color=0x808080)
        content = self.truncate_text(self.escape_code_blocks(message.content), 1500) or "내용 없음"
        
        description = (
            f"**작성자:** {message.author.mention} ({message.author.id})\n"
            f"**채널:** {message.channel.mention}\n"
            f"**내용:** ```{content}```"
        )
        
        if message.attachments:
            files_log = "\n".join([f"📁 `{att.filename}`" for att in message.attachments])
            description += f"\n**첨부파일:**\n{files_log}"
            
        embed.description = description
        await self.send_log(message.guild, embed)

    @commands.Cog.listener()
    async def on_voice_state_update(self, member, before, after):
        if before.channel == after.channel:
            return
        user_info = f"{member.mention} **({member.id})**"
        
        if not before.channel:
            embed = discord.Embed(
                title="🔊 음성채널 입장",
                description=f"{user_info} 님이 **{after.channel.name}** 채널에 입장했습니다.",
                color=0x808080
            )
        elif not after.channel:
            embed = discord.Embed(
                title="🔇 음성채널 퇴장",
                description=f"{user_info} 님이 **{before.channel.name}** 채널에서 퇴장했습니다.",
                color=0x808080
            )
        else:
            embed = discord.Embed(
                title="🔄 음성채널 이동",
                description=(
                    f"{user_info} 님이 채널을 이동했습니다.\n"
                    f"**{before.channel.name}** ➡ **{after.channel.name}**"
                ),
                color=0x808080
            )

        await self.send_log(member.guild, embed=embed)

async def setup(bot):
    await bot.add_cog(Logger(bot))