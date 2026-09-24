import os
import sys
import ssl
import certifi

# macOS SSL certificate fix
os.environ['SSL_CERT_FILE'] = certifi.where()
ssl_context = ssl.create_default_context(cafile=certifi.where())

import logging
import discord
from discord import app_commands
from discord.ext import commands

from config import DISCORD_BOT_TOKEN
from valorant_api import valorant_api_client
from riot_auth import riot_auth_client
from store_service import store_service
from ui_components import (
    LoginModal,
    StorePaginationView,
    create_bundle_embed,
    create_night_market_embed,
    QRLoginView,
    create_qr_login_embed,
    TokenLoginModal,
    create_token_login_embed,
    UnifiedLoginView,
    create_unified_login_embed
)

# 로깅 설정
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger("valorant_bot")

# 디스코드 봇 클라이언트 생성 (슬래시 커맨드 전용기반)
intents = discord.Intents.default()

class ValorantStoreBot(commands.Bot):
    def __init__(self):
        super().__init__(command_prefix="!", intents=intents)

    async def setup_hook(self):
        """봇 시작 시 실행되는 연동 작업"""
        logger.info("Initializing Valorant API metadata...")
        await valorant_api_client.initialize()
        
        logger.info("Syncing slash commands...")
        await self.tree.sync()
        logger.info("Slash commands synced successfully!")

    async def on_ready(self):
        logger.info(f"Bot logged in as {self.user} (ID: {self.user.id})")
        await self.change_presence(
            activity=discord.Game(name="/상점 | 발로란트 일일 상점 봇")
        )

bot = ValorantStoreBot()

# --- 슬래시 커맨드 (Slash Commands) ---

@bot.tree.command(name="로그인", description="라이엇 계정 통합 로그인 센터 (웹사이트 연동 / 2FA OTP / 아이디 로그인 선택)")
async def login_command(interaction: discord.Interaction):
    """통합 로그인 센터 카드를 호출합니다."""
    embed = create_unified_login_embed()
    view = UnifiedLoginView(user_id=interaction.user.id)
    await interaction.response.send_message(embed=embed, view=view, ephemeral=True)


@bot.tree.command(name="토큰로그인", description="라이엇 공식 웹사이트 링크로 100% 안전하게 계정을 연동합니다.")
async def token_login_command(interaction: discord.Interaction):
    """통합 로그인 센터 카드를 호출합니다."""
    embed = create_unified_login_embed()
    view = UnifiedLoginView(user_id=interaction.user.id)
    await interaction.response.send_message(embed=embed, view=view, ephemeral=True)


@bot.tree.command(name="qr로그인", description="라이엇 모바일 앱 2단계 인증(2FA) 및 간편 로그인 센터를 호출합니다.")
async def qr_login_command(interaction: discord.Interaction):
    """통합 로그인 센터 카드를 호출합니다."""
    embed = create_unified_login_embed()
    view = UnifiedLoginView(user_id=interaction.user.id)
    await interaction.response.send_message(embed=embed, view=view, ephemeral=True)


@bot.tree.command(name="상점", description="내 계정의 오늘 일일 상점 4가지 총기 스킨을 확인합니다.")
async def store_command(interaction: discord.Interaction):
    """일일 상점 확인"""
    session_data = riot_auth_client.get_session(interaction.user.id)
    if not session_data:
        embed = discord.Embed(
            title="🔒 라이엇 계정 연동 필요",
            description="상점을 확인하려면 먼저 `/로그인` 명령어를 통해 라이엇 계정에 로그인해 주세요.",
            color=0xff4655
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)
        return

    await interaction.response.defer(ephemeral=False)

    success, msg, store_data = await store_service.get_daily_store(session_data)
    if not success or not store_data:
        embed = discord.Embed(
            title="❌ 상점 조회 실패",
            description=msg,
            color=0xff4655
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)
        return

    user_name = session_data.get("username", str(interaction.user))
    view = StorePaginationView(user_name=user_name, store_data=store_data, user_id=interaction.user.id)
    embed = view.create_embed()

    await interaction.followup.send(embed=embed, view=view)


@bot.tree.command(name="컬렉션", description="현재 메인 상점에서 판매 중인 추천 세트(컬렉션) 패키지를 확인합니다.")
async def bundle_command(interaction: discord.Interaction):
    """추천 컬렉션 세트 확인"""
    session_data = riot_auth_client.get_session(interaction.user.id)
    if not session_data:
        embed = discord.Embed(
            title="🔒 라이엇 계정 연동 필요",
            description="컬렉션을 확인하려면 먼저 `/로그인` 명령어를 통해 라이엇 계정에 로그인해 주세요.",
            color=0xff4655
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)
        return

    await interaction.response.defer(ephemeral=False)

    success, msg, bundle_data = await store_service.get_featured_bundle(session_data)
    if not success or not bundle_data:
        embed = discord.Embed(
            title="❌ 컬렉션 조회 실패",
            description=msg,
            color=0xff4655
        )
        await interaction.followup.send(embed=embed)
        return

    embed = create_bundle_embed(bundle_data)
    await interaction.followup.send(embed=embed)


@bot.tree.command(name="야시장", description="현재 열려있는 야시장(Bonus Store) 할인 스킨 목록을 확인합니다.")
async def nightmarket_command(interaction: discord.Interaction):
    """야시장 확인"""
    session_data = riot_auth_client.get_session(interaction.user.id)
    if not session_data:
        embed = discord.Embed(
            title="🔒 라이엇 계정 연동 필요",
            description="야시장을 확인하려면 먼저 `/로그인` 명령어를 통해 라이엇 계정에 로그인해 주세요.",
            color=0xff4655
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)
        return

    await interaction.response.defer(ephemeral=False)

    success, msg, night_market_data = await store_service.get_night_market(session_data)
    if not success or not night_market_data:
        embed = discord.Embed(
            title="🌙 야시장 조회 실패",
            description=msg,
            color=0xff4655
        )
        await interaction.followup.send(embed=embed)
        return

    user_name = session_data.get("username", str(interaction.user))
    embed = create_night_market_embed(user_name, night_market_data)
    await interaction.followup.send(embed=embed)


@bot.tree.command(name="로그아웃", description="저장된 라이엇 계정 인증 세션을 삭제합니다.")
async def logout_command(interaction: discord.Interaction):
    """로그아웃"""
    success = riot_auth_client.logout(interaction.user.id)
    if success:
        embed = discord.Embed(
            title="👋 로그아웃 완료",
            description="저장된 로그인 세션이 삭제되었습니다.",
            color=0x00ff7f
        )
    else:
        embed = discord.Embed(
            title="⚠️ 알림",
            description="저장된 로그인 세션 정보가 없습니다.",
            color=0xffa500
        )
    await interaction.response.send_message(embed=embed, ephemeral=True)


@bot.tree.command(name="도움말", description="발로란트 상점 봇 커맨드 목록 및 사용법을 확인합니다.")
async def help_command(interaction: discord.Interaction):
    """도움말 명령어"""
    embed = discord.Embed(
        title="🎮 발로란트 일일 상점 디스코드 봇 도움말",
        description="이 봇은 라이엇 계정 상점 정보와 `valorant-api.com` 한국어 메타데이터를 매핑하여 보여줍니다.",
        color=0xff4655
    )
    embed.add_field(name="🔑 `/로그인`", value="라이엇 계정 아이디와 비밀번호를 입력하여 봇과 연동합니다.", inline=False)
    embed.add_field(name="🛒 `/상점`", value="오늘의 일일 상점 4가지 무기 스킨, 가격, 등급, 이미지, 초기화 시간을 확인합니다.", inline=False)
    embed.add_field(name="📦 `/컬렉션`", value="현재 판매 중인 추천 세트 패키지(Bundle) 배너와 구성을 확인합니다.", inline=False)
    embed.add_field(name="🌙 `/야시장`", value="현재 진행 중인 야시장의 할인가 스킨들을 확인합니다.", inline=False)
    embed.add_field(name="🚪 `/로그아웃`", value="저장된 세션을 안전하게 삭제합니다.", inline=False)
    embed.set_footer(text="Valorant Store Discord Bot | Powered by valorant-api.com")

    await interaction.response.send_message(embed=embed)


def main():
    token = DISCORD_BOT_TOKEN
    if not token or token == "your_discord_bot_token_here":
        print("❌ Error: DISCORD_BOT_TOKEN이 설정되지 않았습니다.")
        print(".env 파일에 올바른 Discord Bot Token을 작성해 주세요.")
        sys.exit(1)

    bot.run(token)

if __name__ == "__main__":
    main()
