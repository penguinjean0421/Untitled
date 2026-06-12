import json
import os
import discord
from discord.ext import commands


class Settings(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        base_path = os.path.dirname(os.path.abspath(__file__))
        self.config_file = os.path.join(base_path, "..", "config.json")
        self.server_configs = {}
        self.load_config()

    def load_config(self):
        """설정 파일(.json) 로드"""
        if os.path.exists(self.config_file):
            try:
                with open(self.config_file, "r", encoding="utf-8") as f:
                    self.server_configs = json.load(f)
            except (json.JSONDecodeError, IOError):
                self.server_configs = {}
        else:
            self.server_configs = {}

    def save_config(self):
        """현재 설정을 파일에 저장"""
        try:
            with open(self.config_file, "w", encoding="utf-8") as f:
                json.dump(self.server_configs, f, indent=4, ensure_ascii=False)
        except Exception as e:
            print(f"파일 저장 중 오류 발생: {e}")

    def get_server_data(self, guild):
        """서버별 데이터 구조를 반환, 없을 경우 초기화"""
        gid = str(guild.id)

        if gid not in self.server_configs:
            self.server_configs[gid] = {
                "server_name": guild.name,
                "owner_id": guild.owner_id,
                "owner_name": str(guild.owner),
                "server_log_channel_id": None,
                "punish_log_channel_id": None,
                "ticket_log_channel_id": None,
                "command_channel_id": None,
                "emoji_command_channel_id": None,
                "ticket_panel_channel_id": None,
                "ticket_panel_msg_id": None,
                "ticket_count": 0,
            }
        else:
            keys = [
                "server_log_channel_id",
                "punish_log_channel_id",
                "ticket_log_channel_id",
                "command_channel_id",
                "emoji_command_channel_id",
                "ticket_panel_channel_id",
                "ticket_panel_msg_id",
            ]
            for key in keys:
                if key not in self.server_configs[gid]:
                    self.server_configs[gid][key] = None

            if "ticket_count" not in self.server_configs[gid]:
                self.server_configs[gid]["ticket_count"] = 0

            self.server_configs[gid]["server_name"] = guild.name

        self.save_config()
        return self.server_configs[gid]

    def get_db_target(self, category: str, target: str) -> str:
        """카테고리와 타겟을 검증하여 매핑할 내부 키 이름 반환"""
        log_targets = ["server", "punish", "ticket"]
        command_targets = ["bot", "emoji", "ticket"]

        if category == "log" and target in log_targets:
            return "log_ticket" if target == "ticket" else target
        elif category == "command" and target in command_targets:
            return "cmd_ticket" if target == "ticket" else target
        return None

    async def delete_ticket_panel(self, guild):
        """저장된 티켓 패널 메시지를 물리적으로 삭제"""
        gid = str(guild.id)
        config = self.server_configs.get(gid)
        if not config:
            return

        msg_id = config.get("ticket_panel_msg_id")
        chn_id = config.get("ticket_panel_channel_id")

        if msg_id and chn_id:
            channel = self.bot.get_channel(chn_id)
            if not channel:
                try:
                    channel = await self.bot.fetch_channel(chn_id)
                except Exception:
                    return

            try:
                msg = await channel.fetch_message(msg_id)
                await msg.delete()
            except discord.NotFound:
                pass
            except Exception as e:
                print(f"패널 삭제 오류: {e}")

    @commands.command(name="set")
    @commands.has_permissions(administrator=True)
    async def set_command(self, ctx, category: str = None, target: str = None, channel: discord.TextChannel = None):
        """서버의 각종 로그 및 패널 채널 설정"""
        key_map = {
            "server": "server_log_channel_id",
            "punish": "punish_log_channel_id",
            "log_ticket": "ticket_log_channel_id",
            "bot": "command_channel_id",
            "emoji": "emoji_command_channel_id",
            "cmd_ticket": "ticket_panel_channel_id",
        }

        usage_embed = discord.Embed(
            title="❓ set 명령어 사용법",
            description=(
                f"예시 1: `{ctx.prefix}set log [server/punish/ticket] [#채널]`\n"
                f"예시 2: `{ctx.prefix}set command [bot/emoji/ticket] [#채널]`"
            ),
            color=0x808080
        )

        if not category or not target:
            return await ctx.send(embed=usage_embed)

        category = category.lower()
        target = target.lower()

        db_target = self.get_db_target(category, target)

        if not db_target:
            if category == "log":
                right_target = "server/punish/ticket"
            elif category == "command":
                right_target = "bot/emoji/ticket"
            else:
                right_target = None

            if not right_target:
                return await ctx.send(embed=usage_embed)

            embed = discord.Embed(
                title="❓ 정확한 타겟을 입력하세요.",
                description=f"예시: `{ctx.prefix}set {category} {right_target} [#채널]`",
                color=0x808080
            )
            return await ctx.send(embed=embed)

        target_channel = channel or ctx.channel
        gid = str(ctx.guild.id)

        self.get_server_data(ctx.guild)

        config_key = key_map.get(db_target)
        if not config_key:
            embed = discord.Embed(
                title="❌ 내부 오류",
                description=f"잘못된 설정 타겟입니다. ({db_target})",
                color=0x808080
            )
            return await ctx.send(embed=embed)

        if db_target == "cmd_ticket":
            ticket_cog = self.bot.get_cog("Ticket")
            if not ticket_cog:
                embed = discord.Embed(
                    title="❌ 로드 실패",
                    description="Ticket Cog가 로드되지 않았습니다.",
                    color=0x808080
                )
                return await ctx.send(embed=embed)

            await self.delete_ticket_panel(ctx.guild)

            panel_msg = await ticket_cog.send_ticket_panel(target_channel)
            if not panel_msg:
                embed = discord.Embed(
                    title="❌ 생성 실패",
                    description="티켓 메시지 생성에 실패했습니다.",
                    color=0x808080
                )
                return await ctx.send(embed=embed)


            self.server_configs[gid][config_key] = target_channel.id
            self.server_configs[gid]["ticket_panel_msg_id"] = panel_msg.id

            embed = discord.Embed(
                title="✅ 패널 생성 성공",
                description=(
                    f"티켓 패널 채널이 {target_channel.mention}로 설정되었습니다.\n"
                    f"[패널 바로가기](https://discord.com/channels/{ctx.guild.id}/{target_channel.id}/{panel_msg.id})"
                ),
                color=0x808080
            )
        else:
            self.server_configs[gid][config_key] = target_channel.id
            embed = discord.Embed(
                title="✅ 설정 완료",
                description=f"[**{category.upper()} - {target.upper()}**] 채널이 {target_channel.mention}로 설정되었습니다.",
                color=0x808080
            )

        self.save_config()
        await ctx.send(embed=embed)

    @commands.command(name="reset")
    @commands.has_permissions(administrator=True)
    async def reset_command(self, ctx, category: str = None, target: str = None):
        """서버 설정을 초기화하거나 특정 채널 설정을 제거"""
        gid = str(ctx.guild.id)

        key_map = {
            "server": "server_log_channel_id",
            "punish": "punish_log_channel_id",
            "log_ticket": "ticket_log_channel_id",
            "bot": "command_channel_id",
            "emoji": "emoji_command_channel_id",
            "cmd_ticket": "ticket_panel_channel_id",
        }

        usage_embed = discord.Embed(
            title="❓ reset 명령어 사용법",
            description=(
                f"예시 1: `{ctx.prefix}reset log [server/punish/ticket]`\n"
                f"예시 2: `{ctx.prefix}reset command [bot/emoji/ticket]`\n"
                f"예시 3: `{ctx.prefix}reset all` (모든 설정 초기화)"
            ),
            color=0x808080
        )

        if not category:
            return await ctx.send(embed=usage_embed)

        category = category.lower()

        if category == "all":
            await self.delete_ticket_panel(ctx.guild)

            if gid in self.server_configs:
                for key in key_map.values():
                    self.server_configs[gid][key] = None
                self.server_configs[gid]["ticket_panel_msg_id"] = None
            else:
                self.get_server_data(ctx.guild)

            embed = discord.Embed(
                title="✅ 모든 설정 초기화",
                description=f"{ctx.guild.name}의 모든 채널 설정이 초기화 되었습니다.",
                color=0x808080
            )
            self.save_config()
            return await ctx.send(embed=embed)

        if not target:
            return await ctx.send(embed=usage_embed)

        target = target.lower()
        db_target = self.get_db_target(category, target)

        if not db_target:
            if category == "log":
                right_target = "server/punish/ticket"
            elif category == "command":
                right_target = "bot/emoji/ticket"
            else:
                right_target = None

            if not right_target:
                return await ctx.send(embed=usage_embed)

            embed = discord.Embed(
                title="❓ 정확한 타겟을 입력하세요.",
                description=(
                    f"Ex1. `{ctx.prefix}reset {category} [{right_target}]`\n"
                    f"Ex2. `{ctx.prefix}reset all`\n"),
                color=0x808080
            )
            return await ctx.send(embed=embed)

        self.get_server_data(ctx.guild)

        if gid in self.server_configs:
            config_key = key_map.get(db_target)
            if not config_key:
                embed=discord.Embed(
                    title="❌ 내부 오류",
                    description=f"잘못된 설정 타겟입니다. ({db_target})",
                    color=0x808080
                )
                return await ctx.send(embed=embed)

            if db_target == "cmd_ticket":
                await self.delete_ticket_panel(ctx.guild)
                self.server_configs[gid]["ticket_panel_msg_id"] = None
                self.server_configs[gid][config_key] = None
            else:
                self.server_configs[gid][config_key] = None

            embed = discord.Embed(
                title="✅ 초기화 완료",
                description=f"**{category.upper()} [{target.upper()}]** 설정이 제거되었습니다.",
                color=0x808080
            )
        else:
            embed = discord.Embed(
                title="❌ 데이터 없음",
                description="설정된 데이터가 없습니다.",
                color=0x808080
            )

        self.save_config()
        await ctx.send(embed=embed)


async def setup(bot):
    await bot.add_cog(Settings(bot))