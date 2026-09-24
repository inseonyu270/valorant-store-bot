import discord
import urllib.parse
from typing import Dict, Any, List, Optional

from config import DEFAULT_EMBED_COLOR, DEFAULT_REGION
from riot_auth import riot_auth_client
from store_service import store_service

# ─────────────────────────────────────────────────────────────────────────────
# 로그인 모달들
# ─────────────────────────────────────────────────────────────────────────────

class LoginModal(discord.ui.Modal, title="라이엇 계정 로그인"):
    """라이엇 계정 로그인 입력 폼 모달"""

    username_input = discord.ui.TextInput(
        label="라이엇 계정 아이디 (닉네임#TAG ❌)",
        placeholder="게임 닉네임이 아닌 런처 로그인용 아이디 입력",
        required=True,
        max_length=64
    )

    password_input = discord.ui.TextInput(
        label="비밀번호 (Password)",
        placeholder="비밀번호를 입력하세요",
        style=discord.TextStyle.short,
        required=True,
        max_length=64
    )

    region_input = discord.ui.TextInput(
        label="서버 지역 (kr, ap, na, eu)",
        placeholder="기본값: kr",
        default=DEFAULT_REGION,
        required=False,
        max_length=5
    )

    async def on_submit(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)

        username = self.username_input.value.strip()
        password = self.password_input.value
        region = (self.region_input.value or DEFAULT_REGION).strip().lower()

        success, message, extra_data = await riot_auth_client.authenticate(interaction.user.id, username, password, region)

        if not success:
            if message == "2FA_REQUIRED":
                email_info = extra_data.get("email", "이메일") if extra_data else "이메일"
                embed = discord.Embed(
                    title="🔐 2단계 인증(2FA) 코드 입력 필요",
                    description=(
                        f"등록된 이메일(**{email_info}**) 또는 **라이엇 모바일(Riot Mobile) 앱** 화면의 6자리 인증 코드를 확인해 주세요.\n"
                        "아래 **[🔑 2차 인증 코드 입력]** 버튼을 눌러 6자리 코드를 입력하시면 로그인이 완료됩니다."
                    ),
                    color=0xffa500
                )
                view = MFAView(user_id=interaction.user.id)
                await interaction.followup.send(embed=embed, view=view, ephemeral=True)
                return

            embed = discord.Embed(
                title="❌ 로그인 실패",
                description=message,
                color=0xff4655
            )
            await interaction.followup.send(embed=embed, ephemeral=True)
            return

        embed = discord.Embed(
            title="✅ 라이엇 계정 로그인 성공!",
            description=f"**{username}** 님으로 성공적으로 인증되었습니다.\n이제 `/상점` 커맨드를 사용하여 오늘의 일일 상점을 확인할 수 있습니다.",
            color=0x00ff7f
        )
        embed.set_footer(text="세션 토큰은 안전하게 관리됩니다.")
        await interaction.followup.send(embed=embed, ephemeral=True)


class MFALoginModal(discord.ui.Modal, title="라이엇 2FA 로그인 (아이디 + 인증코드)"):
    """
    2FA 활성화 계정: 아이디/비밀번호 입력 후 자동으로 2FA 코드를 받아서 처리
    """

    username_input = discord.ui.TextInput(
        label="라이엇 계정 아이디",
        placeholder="런처 로그인용 계정 아이디 (닉네임#TAG ❌)",
        required=True,
        max_length=64
    )

    password_input = discord.ui.TextInput(
        label="비밀번호",
        placeholder="라이엇 계정 비밀번호",
        style=discord.TextStyle.short,
        required=True,
        max_length=64
    )

    region_input = discord.ui.TextInput(
        label="서버 지역 (kr, ap, na, eu)",
        placeholder="기본값: kr",
        default=DEFAULT_REGION,
        required=False,
        max_length=5
    )

    async def on_submit(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)

        username = self.username_input.value.strip()
        password = self.password_input.value
        region = (self.region_input.value or DEFAULT_REGION).strip().lower()

        # 1단계: 아이디/비밀번호로 인증 시도
        success, message, extra_data = await riot_auth_client.authenticate(interaction.user.id, username, password, region)

        if not success:
            if message == "2FA_REQUIRED":
                # 2FA가 필요하면 코드 입력 창 표시
                email_info = extra_data.get("email", "이메일") if extra_data else "이메일"
                embed = discord.Embed(
                    title="🔐 2단계 인증(2FA) 코드를 입력하세요",
                    description=(
                        f"✅ **아이디/비밀번호 확인 완료!**\n\n"
                        f"📧 **{email_info}** 또는 **라이엇 모바일 앱**에서 6자리 코드를 확인하세요.\n\n"
                        "아래 **[🔑 2FA 코드 입력]** 버튼을 눌러 인증 코드를 제출하세요."
                    ),
                    color=0xffa500
                )
                view = MFAView(user_id=interaction.user.id)
                await interaction.followup.send(embed=embed, view=view, ephemeral=True)
                return

            # 일반 오류
            embed = discord.Embed(
                title="❌ 로그인 실패",
                description=message,
                color=0xff4655
            )
            await interaction.followup.send(embed=embed, ephemeral=True)
            return

        # 2FA 없이 바로 성공
        embed = discord.Embed(
            title="✅ 로그인 성공!",
            description=f"**{username}** 님으로 성공적으로 인증되었습니다.\n이제 `/상점` 커맨드를 사용하세요!",
            color=0x00ff7f
        )
        await interaction.followup.send(embed=embed, ephemeral=True)


class MFACodeModal(discord.ui.Modal, title="라이엇 2차 인증(2FA) 코드 입력"):
    """2단계 인증 코드 입력 모달"""

    code_input = discord.ui.TextInput(
        label="6자리 인증 코드",
        placeholder="이메일 또는 라이엇 모바일 앱의 6자리 숫자 입력",
        required=True,
        max_length=10
    )

    async def on_submit(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        mfa_code = self.code_input.value.strip()

        success, message, session_data = await riot_auth_client.complete_2fa(interaction.user.id, mfa_code)
        if not success:
            embed = discord.Embed(
                title="❌ 2차 인증 실패",
                description=message,
                color=0xff4655
            )
            await interaction.followup.send(embed=embed, ephemeral=True)
            return

        username = session_data.get("username", "사용자")
        embed = discord.Embed(
            title="✅ 2단계 인증 및 로그인 성공!",
            description=f"**{username}** 님으로 성공적으로 연동되었습니다.\n이제 `/상점` 커맨드를 사용하여 오늘의 일일 상점을 확인해 보세요!",
            color=0x00ff7f
        )
        await interaction.followup.send(embed=embed, ephemeral=True)


class TokenLoginModal(discord.ui.Modal, title="라이엇 웹 연동 URL 제출"):
    """라이엇 공식 브라우저 로그인 URL/토큰 제출 모달"""

    token_input = discord.ui.TextInput(
        label="로그인 후 주소창의 전체 URL 붙여넣기",
        placeholder="https://playvalorant.com/opt_in#access_token=eyJ...",
        style=discord.TextStyle.paragraph,
        required=True
    )

    async def on_submit(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        input_str = self.token_input.value.strip()

        success, message, session_data = await riot_auth_client.authenticate_via_token(interaction.user.id, input_str)
        if not success:
            embed = discord.Embed(
                title="❌ 연동 실패",
                description=message,
                color=0xff4655
            )
            await interaction.followup.send(embed=embed, ephemeral=True)
            return

        embed = discord.Embed(
            title="✅ 라이엇 공식 웹연동 성공!",
            description="성공적으로 라이엇 계정이 동기화되었습니다.\n이제 `/상점` 커맨드를 사용하여 오늘의 일일 상점을 확인해 보세요!",
            color=0x00ff7f
        )
        await interaction.followup.send(embed=embed, ephemeral=True)


# ─────────────────────────────────────────────────────────────────────────────
# View 클래스들
# ─────────────────────────────────────────────────────────────────────────────

class MFAView(discord.ui.View):
    """2차 인증 코드 입력을 유도하는 버튼 View"""

    def __init__(self, user_id: int):
        super().__init__(timeout=300)
        self.user_id = user_id

    @discord.ui.button(label="🔑 2FA 코드 입력", style=discord.ButtonStyle.primary)
    async def enter_code_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("본인의 인증 세션만 조작할 수 있습니다.", ephemeral=True)
            return
        modal = MFACodeModal()
        await interaction.response.send_modal(modal)


class UnifiedLoginView(discord.ui.View):
    """통합 로그인 방식 선택 버튼 View"""

    def __init__(self, user_id: int):
        super().__init__(timeout=300)
        self.user_id = user_id
        # 라이엇 로그인 페이지 직접 열기 버튼 (URL 버튼 - 마크다운 파싱 문제 없음)
        self.add_item(discord.ui.Button(
            label="🔗 라이엇 로그인 페이지 열기",
            url="https://auth.riotgames.com/authorize?redirect_uri=https%3A%2F%2Fplayvalorant.com%2Fopt_in&client_id=play-valorant-web-prod&response_type=token%20id_token&nonce=1&scope=account%20openid",
            style=discord.ButtonStyle.link,
            row=2
        ))

    @discord.ui.button(label="🌐 웹사이트 100% 안심 연동", style=discord.ButtonStyle.success, row=0)
    async def enter_token_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("본인의 로그인 세션만 조작할 수 있습니다.", ephemeral=True)
            return
        modal = TokenLoginModal()
        await interaction.response.send_modal(modal)

    @discord.ui.button(label="📱 2FA(라이엇 모바일) 로그인", style=discord.ButtonStyle.primary, row=0)
    async def enter_mfa_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("본인의 로그인 세션만 조작할 수 있습니다.", ephemeral=True)
            return
        modal = MFALoginModal()
        await interaction.response.send_modal(modal)

    @discord.ui.button(label="👤 아이디/비밀번호 로그인", style=discord.ButtonStyle.secondary, row=1)
    async def enter_login_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("본인의 로그인 세션만 조작할 수 있습니다.", ephemeral=True)
            return
        modal = LoginModal()
        await interaction.response.send_modal(modal)


class QRLoginView(discord.ui.View):
    """QR 및 모바일 2FA 로그인을 위한 버튼 View (하위 호환)"""

    def __init__(self, user_id: int):
        super().__init__(timeout=300)
        self.user_id = user_id

    @discord.ui.button(label="📱 2FA(라이엇 모바일) 로그인", style=discord.ButtonStyle.primary, row=0)
    async def enter_mfa_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("본인의 인증 세션만 조작할 수 있습니다.", ephemeral=True)
            return
        modal = MFALoginModal()
        await interaction.response.send_modal(modal)

    @discord.ui.button(label="🌐 웹사이트 100% 안심 연동", style=discord.ButtonStyle.success, row=0)
    async def enter_token_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("본인의 인증 세션만 조작할 수 있습니다.", ephemeral=True)
            return
        modal = TokenLoginModal()
        await interaction.response.send_modal(modal)

    @discord.ui.button(label="👤 아이디/비밀번호 로그인", style=discord.ButtonStyle.secondary, row=1)
    async def enter_login_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("본인의 인증 세션만 조작할 수 있습니다.", ephemeral=True)
            return
        modal = LoginModal()
        await interaction.response.send_modal(modal)


# ─────────────────────────────────────────────────────────────────────────────
# 상점 관련 View / Embed
# ─────────────────────────────────────────────────────────────────────────────

class StorePaginationView(discord.ui.View):
    """일일 상점 스킨 슬라이드 및 전체보기 조작 버튼 View"""

    def __init__(self, user_name: str, store_data: Dict[str, Any], user_id: int):
        super().__init__(timeout=180)
        self.user_name = user_name
        self.items: List[Dict[str, Any]] = store_data["items"]
        self.remaining_time_str = store_data["remaining_time_str"]
        self.user_id = user_id
        self.current_index: int = -1 # -1은 전체 요약보기, 0~3은 개별 스킨 상세보기

    def create_embed(self) -> discord.Embed:
        """현재 인덱스에 맞는 Embed 생성"""
        if self.current_index == -1:
            embed = discord.Embed(
                title=f"🛒 {self.user_name} 님의 발로란트 일일 상점",
                description=f"⏰ **상점 갱신까지 남은 시간:** `{self.remaining_time_str}`\n\n아래 스킨 버튼을 눌러 개별 스킨 이미지를 크게 확인하세요!",
                color=DEFAULT_EMBED_COLOR
            )

            total_vp = 0
            for idx, item in enumerate(self.items, 1):
                tier_name = item["tier"]["name"]
                price_str = f"{item['price']:,} VP" if item['price'] > 0 else "가격 미상정"
                total_vp += item['price']

                embed.add_field(
                    name=f"[{idx}] {item['name']}",
                    value=f"✨ **등급**: `{tier_name}`\n💰 **가격**: `{price_str}`",
                    inline=True
                )

            embed.set_footer(text=f"총 4개 스킨 합계: {total_vp:,} VP | 봇 조작 버튼 3분간 유지")
            if len(self.items) > 0 and self.items[0].get("icon"):
                embed.set_thumbnail(url=self.items[0]["icon"])

            return embed

        else:
            item = self.items[self.current_index]
            tier_info = item["tier"]
            embed_color = tier_info.get("color", DEFAULT_EMBED_COLOR)

            embed = discord.Embed(
                title=f"🎯 [{self.current_index + 1}/4] {item['name']}",
                description=f"✨ **등급**: `{tier_info['name']}`\n💰 **가격**: `{item['price']:,} VP`\n⏰ **남은 시간**: `{self.remaining_time_str}`",
                color=embed_color
            )
            if item.get("icon"):
                embed.set_image(url=item["icon"])
            if tier_info.get("icon"):
                embed.set_thumbnail(url=tier_info["icon"])

            embed.set_footer(text=f"요약 버튼을 누르면 전체 4개 스킨 목록으로 돌아갑니다.")
            return embed

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("자신의 상점만 조작할 수 있습니다.", ephemeral=True)
            return False
        return True

    @discord.ui.button(label="전체 요약", style=discord.ButtonStyle.primary, row=0)
    async def summary_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.current_index = -1
        await interaction.response.edit_message(embed=self.create_embed(), view=self)

    @discord.ui.button(label="◀ 이전", style=discord.ButtonStyle.secondary, row=0)
    async def prev_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        if self.current_index <= 0:
            self.current_index = len(self.items) - 1
        else:
            self.current_index -= 1
        await interaction.response.edit_message(embed=self.create_embed(), view=self)

    @discord.ui.button(label="다음 ▶", style=discord.ButtonStyle.secondary, row=0)
    async def next_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        if self.current_index >= len(self.items) - 1 or self.current_index == -1:
            self.current_index = 0
        else:
            self.current_index += 1
        await interaction.response.edit_message(embed=self.create_embed(), view=self)

    @discord.ui.button(label="📦 추천 컬렉션 보기", style=discord.ButtonStyle.success, row=1)
    async def bundle_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.defer(ephemeral=False)
        session_data = riot_auth_client.get_session(interaction.user.id)
        if not session_data:
            await interaction.followup.send("인증 정보가 없습니다. 다시 로그인해 주세요.", ephemeral=True)
            return

        success, msg, bundle_data = await store_service.get_featured_bundle(session_data)
        if not success or not bundle_data:
            await interaction.followup.send(f"❌ {msg}", ephemeral=True)
            return

        embed = create_bundle_embed(bundle_data)
        await interaction.followup.send(embed=embed)


# ─────────────────────────────────────────────────────────────────────────────
# Embed 생성 함수들
# ─────────────────────────────────────────────────────────────────────────────

def create_bundle_embed(bundle_data: Dict[str, Any]) -> discord.Embed:
    """추천 컬렉션 세트 Embed 생성"""
    embed = discord.Embed(
        title=f"📦 추천 메인 컬렉션: {bundle_data['name']}",
        description=f"📝 **설명**: {bundle_data['description'] or '한정판 패키지 세트'}\n💰 **세트 가격**: `{bundle_data['price']:,} VP`\n🧩 **구성 품목 수**: `{bundle_data['item_count']}개`\n⏰ **남은 시간**: `{bundle_data['remaining_time_str']}`",
        color=0xffd700
    )
    if bundle_data.get("banner"):
        embed.set_image(url=bundle_data["banner"])

    embed.set_footer(text="발로란트 한정 패키지 메인 상점")
    return embed


def create_night_market_embed(user_name: str, night_market_data: Dict[str, Any]) -> discord.Embed:
    """야시장 Embed 생성"""
    embed = discord.Embed(
        title=f"🌙 {user_name} 님의 야시장 (Bonus Store)",
        description=f"⏰ **야시장 남은 기간:** `{night_market_data['remaining_time_str']}`",
        color=0x4b0082
    )

    for idx, item in enumerate(night_market_data["items"], 1):
        tier_name = item["tier"]["name"]
        status_str = " (구매 완료)" if item["is_purchased"] else ""
        price_text = f"~~{item['original_price']:,} VP~~ ➔ **{item['discounted_price']:,} VP** (`-{item['discount_percent']}%`){status_str}"

        embed.add_field(
            name=f"[{idx}] {item['name']}",
            value=f"✨ **등급**: `{tier_name}`\n🏷️ **할인가**: {price_text}",
            inline=False
        )

    embed.set_footer(text="야시장 할인 스킨 목록")
    return embed


AUTH_URL = "https://auth.riotgames.com/authorize?redirect_uri=https%3A%2F%2Fplayvalorant.com%2Fopt_in&client_id=play-valorant-web-prod&response_type=token%20id_token&nonce=1&scope=account%20openid"
QR_URL = "https://api.qrserver.com/v1/create-qr-code/?size=300x300&data=" + urllib.parse.quote(AUTH_URL, safe='')


def create_unified_login_embed() -> discord.Embed:
    """통합 로그인 메인 Embed 카드 생성"""
    embed = discord.Embed(
        title="🔐 발로란트 상점 봇 통합 로그인",
        description=(
            "원하시는 방식을 선택하여 라이엇 계정을 연동해 주세요!\n\n"
            "━━━━━━━━━━━━━━━━━━━━━━\n"
            "🟢 **[방식 1] 웹사이트 100% 안심 연동** ⭐ 강력 추천\n"
            f"**STEP 1** 👉 [라이엇 공식 로그인 페이지]({AUTH_URL}) 클릭\n"
            "**STEP 2** 라이엇 계정으로 로그인\n"
            "**STEP 3** ⚠️ **'페이지 없음' 화면이 떠도 정상!** 주소창의 긴 URL 전체를 복사\n"
            "**STEP 4** 아래 **[🌐 웹사이트 100% 안심 연동]** 버튼 클릭 후 URL 붙여넣기!\n\n"
            "━━━━━━━━━━━━━━━━━━━━━━\n"
            "🔵 **[방식 2] 라이엇 모바일 2FA 로그인**\n"
            "아이디/비밀번호 입력 → 자동으로 모바일 앱 또는 이메일 6자리 코드 입력창 표시\n"
            "**📱 2FA(라이엇 모바일) 로그인** 버튼 클릭!\n\n"
            "━━━━━━━━━━━━━━━━━━━━━━\n"
            "⚪ **[방식 3] 일반 아이디/비밀번호 로그인**\n"
            "**👤 아이디/비밀번호 로그인** 버튼 클릭!"
        ),
        color=0x00ff7f
    )
    embed.set_thumbnail(url=QR_URL)
    embed.set_footer(text="⚠️ 로그인 후 '페이지 없음'이 떠도 정상! 주소창 URL을 복사하세요.")
    return embed


def create_qr_login_embed() -> discord.Embed:
    """QR 및 모바일 인증 안내 Embed 생성"""
    embed = discord.Embed(
        title="📱 라이엇 모바일 QR / 2FA 로그인",
        description=(
            "━━━━━━━━━━━━━━━━━━━━━━\n"
            "📷 **[방법 1] QR코드 스캔으로 모바일 로그인**\n"
            "오른쪽 QR코드를 스마트폰으로 스캔하면 라이엇 로그인 페이지가 열립니다.\n"
            "로그인 후 **주소창 URL이 바뀌면** 그 URL을 복사하여\n"
            "**[🌐 웹사이트 100% 안심 연동]** 버튼에 붙여넣으세요!\n\n"
            "⚠️ **로그인 후 '페이지 없음'이 떠도 정상입니다!**\n"
            "그 상태에서 주소창의 URL을 복사하면 됩니다.\n\n"
            "━━━━━━━━━━━━━━━━━━━━━━\n"
            "🔑 **[방법 2] 2FA 인증코드 로그인**\n"
            "아래 **[📱 2FA 로그인]** 버튼 클릭 → 아이디/비번 입력 →\n"
            "자동으로 Riot Mobile 앱 또는 이메일의 6자리 코드 입력창 표시!"
        ),
        color=0x00b0f0
    )
    embed.set_thumbnail(url=QR_URL)
    embed.set_footer(text="⚠️ 로그인 후 '페이지 없음'은 정상! 주소창 URL을 복사하세요.")
    return embed


def create_token_login_embed() -> discord.Embed:
    """100% 성공 보장 라이엇 공식 브라우저 로그인 가이드 Embed (하위 호환)"""
    embed = discord.Embed(
        title="🌐 라이엇 공식 웹사이트를 통한 100% 안심 연동",
        description=(
            "비밀번호 유출 걱정 없이 **라이엇 공식 홈페이지에서 100% 안전하게 연동하는 방법**입니다.\n\n"
            f"**STEP 1** 👉 **[라이엇 공식 로그인 페이지 클릭]({AUTH_URL})**\n"
            "**STEP 2** 브라우저에서 라이엇 계정으로 로그인\n"
            "**STEP 3** ⚠️ **로그인 후 '페이지 없음' 화면이 떠도 정상입니다!**\n"
            "　　　　주소창에 표시된 긴 URL 전체를 복사하세요\n"
            "　　　　*(예: `https://playvalorant.com/opt_in#access_token=eyJ...`)*\n"
            "**STEP 4** 아래 **[🌐 웹사이트 100% 안심 연동]** 버튼을 눌러 복사한 URL을 붙여넣기!"
        ),
        color=0x00ff7f
    )
    embed.set_footer(text="⚠️ '페이지 없음'은 정상! 주소창의 URL을 복사하는 게 핵심입니다.")
    return embed
