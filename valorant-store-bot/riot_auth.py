import os
import ssl
import certifi
import aiohttp
import re
import json
import base64
import logging
from typing import Dict, Any, Tuple, Optional

from config import RIOT_AUTH_URL, RIOT_ENTITLEMENTS_URL, DEFAULT_REGION, CLIENT_VERSION_URL

logger = logging.getLogger("valorant_bot")

os.environ['SSL_CERT_FILE'] = certifi.where()
ssl_context = ssl.create_default_context(cafile=certifi.where())

# Official Valorant Web OAuth Configuration
AUTH_CONFIG = {
    "client_id": "play-valorant-web-prod",
    "redirect_uri": "https://playvalorant.com/opt_in",
    "scope": "account openid",
    "user_agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
}

class RiotAuth:
    """Riot Games 사용자 인증 및 세션 관리 클래스 (2FA & 공식 Web Auth 토큰 수집 지원)"""

    def __init__(self):
        # Discord User ID -> Auth Session Data
        self.user_sessions: Dict[int, Dict[str, Any]] = {}
        # Discord User ID -> Pending 2FA Data
        self.pending_2fa: Dict[int, Dict[str, Any]] = {}

    @staticmethod
    def _extract_puuid(access_token: str) -> Optional[str]:
        """JWT Access Token에서 PUUID (sub) 파싱"""
        try:
            parts = access_token.split('.')
            if len(parts) >= 2:
                payload = parts[1]
                padded = payload + '=' * (-len(payload) % 4)
                decoded = base64.urlsafe_b64decode(padded)
                data = json.loads(decoded)
                return data.get('sub')
        except Exception as e:
            logger.error(f"Error parsing PUUID from access token: {e}")
        return None

    @staticmethod
    def _extract_token_from_url(input_str: str) -> Optional[str]:
        """
        URL 또는 access_token 문자열에서 액세스 토큰 추출
        - https://playvalorant.com/opt_in#access_token=eyJ...
        - https://playvalorant.com/opt_in?access_token=eyJ...
        - eyJ로 시작하는 raw token
        """
        input_str = input_str.strip()

        # Fragment(#) 또는 query(?) 방식 모두 처리
        # access_token= 이후의 값을 추출 (& 혹은 문자열 끝까지)
        match = re.search(r'access_token=([A-Za-z0-9._\-]+)', input_str)
        if match:
            return match.group(1)

        # 순수 JWT 토큰인 경우 (eyJ로 시작)
        if input_str.startswith('eyJ') and len(input_str) > 20:
            return input_str

        return None

    async def authenticate(self, discord_user_id: int, username: str, password: str, region: str = DEFAULT_REGION) -> Tuple[bool, str, Optional[Dict[str, Any]]]:
        """
        Riot 계정 1단계 아이디/비밀번호 로그인 시도
        """
        if "#" in username:
            return False, "⚠️ 라이엇 닉네임(예: 닉네임#KR1)이 아닌, 런처 로그인 시 사용하는 **'계정 아이디'**를 입력해 주세요.", None

        headers = {
            "Accept": "application/json",
            "Content-Type": "application/json",
            "User-Agent": AUTH_CONFIG["user_agent"],
            "Accept-Language": "ko-KR,ko;q=0.9,en-US;q=0.8,en;q=0.7"
        }

        jar = aiohttp.CookieJar(unsafe=True)
        connector = aiohttp.TCPConnector(ssl=ssl_context)
        async with aiohttp.ClientSession(cookie_jar=jar, headers=headers, connector=connector) as session:
            # 1. Auth 세션 초기화 (POST)
            body_init = {
                "client_id": AUTH_CONFIG["client_id"],
                "nonce": "1",
                "redirect_uri": AUTH_CONFIG["redirect_uri"],
                "response_type": "token id_token",
                "scope": AUTH_CONFIG["scope"]
            }
            try:
                async with session.post(RIOT_AUTH_URL, json=body_init) as resp:
                    if resp.status != 200:
                        logger.warning(f"Riot auth init POST failed with status {resp.status}")
                        return False, "인증 서버에 연결할 수 없습니다. 잠시 후 다시 시도해 주세요.", None
                    init_data = await resp.json()
                    logger.info(f"Riot auth init POST success: {init_data}")
            except Exception as e:
                logger.error(f"Riot auth init network error: {e}")
                return False, f"네트워크 오류가 발생했습니다: {str(e)}", None

            # 2. 로그인 정보 제출 (PUT)
            body_login = {
                "type": "auth",
                "username": username.strip(),
                "password": password,
                "remember": True
            }

            try:
                async with session.put(RIOT_AUTH_URL, json=body_login) as resp:
                    data = await resp.json()
                    logger.info(f"Riot auth PUT response type: {data.get('type')}, error: {data.get('error')}")

                    # 2FA (다요소 인증) 요구 시
                    if data.get("type") == "multifactor":
                        mf = data.get("multifactor", {})
                        email_info = mf.get("email", "이메일")
                        methods = mf.get("methods", [])
                        self.pending_2fa[discord_user_id] = {
                            "cookie_jar": jar,
                            "region": region.lower(),
                            "username": username,
                            "user_agent": AUTH_CONFIG["user_agent"]
                        }
                        return False, "2FA_REQUIRED", {"email": email_info, "methods": methods}

                    # 에러 처리
                    if data.get("error") or data.get("type") == "error":
                        error_type = data.get("error")
                        if error_type == "auth_failure":
                            return False, "아이디 또는 비밀번호가 올바르지 않습니다.\n\n💡 **대안**: 웹사이트 100% 안심연동 버튼을 사용하면 비밀번호 없이 안전하게 로그인할 수 있습니다!", None
                        elif error_type == "rate_limited":
                            return False, "너무 많은 로그인 시도가 있었습니다. 잠시 후 다시 시도해 주세요.", None
                        return False, f"인증 실패: {error_type}", None

                    # 성공 응답 확인
                    response_type = data.get("type")
                    if response_type != "response":
                        return False, f"인증 응답 형식 오류 ({response_type})", None

                    redirect_uri = data.get("response", {}).get("parameters", {}).get("uri", "")
                    access_token = self._extract_token_from_url(redirect_uri)
                    if not access_token:
                        return False, "Access Token 파싱 실패", None

            except Exception as e:
                return False, f"로그인 처리 예외 발생: {str(e)}", None

            # 3. Entitlements Token 취득
            return await self._finish_token_exchange(session, access_token, region, username, discord_user_id)

    async def authenticate_via_token(self, discord_user_id: int, input_str: str, region: str = DEFAULT_REGION) -> Tuple[bool, str, Optional[Dict[str, Any]]]:
        """
        라이엇 공식 웹사이트 URL 또는 access_token 입력 기반 100% 안심 연동
        URL 예시: https://playvalorant.com/opt_in#access_token=eyJ...
        """
        access_token = self._extract_token_from_url(input_str)

        if not access_token:
            return False, (
                "❌ 올바른 URL이나 토큰을 찾지 못했습니다.\n\n"
                "**올바른 형식:**\n"
                "`https://playvalorant.com/opt_in#access_token=eyJ...` 전체 주소를 복사해 주세요.\n\n"
                "**주의:** 로그인 후 리다이렉트된 주소창의 **전체 URL**을 복사해야 합니다."
            ), None

        logger.info(f"Token auth attempt for user {discord_user_id}, token length: {len(access_token)}")

        headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json",
            "User-Agent": AUTH_CONFIG["user_agent"]
        }

        connector = aiohttp.TCPConnector(ssl=ssl_context)
        async with aiohttp.ClientSession(connector=connector) as session:
            try:
                async with session.post(RIOT_ENTITLEMENTS_URL, headers=headers, json={}) as resp:
                    resp_text = await resp.text()
                    logger.info(f"Entitlements response status: {resp.status}, body: {resp_text[:200]}")
                    if resp.status == 401:
                        return False, (
                            "❌ 토큰이 만료되었거나 유효하지 않습니다.\n\n"
                            "**해결 방법:**\n"
                            "1. 아래 링크를 다시 클릭하여 브라우저에서 로그인하세요.\n"
                            "2. 로그인 완료 후 **주소창**에 표시된 전체 URL을 복사하세요.\n"
                            "3. 복사한 URL을 이 창에 붙여넣으세요.\n\n"
                            "⚠️ 토큰은 발급 후 **1시간** 이내에 사용해야 합니다."
                        ), None
                    if resp.status != 200:
                        return False, f"서버 오류가 발생했습니다 (코드: {resp.status}). 잠시 후 다시 시도해 주세요.", None
                    ent_data = json.loads(resp_text)
                    entitlements_token = ent_data.get("entitlements_token")
            except Exception as e:
                logger.error(f"Entitlements token exchange error: {e}")
                return False, f"서버 연결 오류: {str(e)}", None

        puuid = self._extract_puuid(access_token)
        if not puuid:
            return False, "사용자 식별자(PUUID) 추출에 실패했습니다. 토큰이 올바른지 확인해 주세요.", None

        auth_session = {
            "access_token": access_token,
            "entitlements_token": entitlements_token,
            "puuid": puuid,
            "region": region.lower(),
            "username": "ValorantUser"
        }

        self.save_session(discord_user_id, auth_session)
        logger.info(f"Token auth success for user {discord_user_id}, puuid: {puuid[:8]}...")
        return True, "성공", auth_session

    async def complete_2fa(self, discord_user_id: int, mfa_code: str) -> Tuple[bool, str, Optional[Dict[str, Any]]]:
        """
        2차 인증(2FA) 6자리 코드 제출 및 인증 완료
        """
        pending_data = self.pending_2fa.get(discord_user_id)
        if not pending_data:
            return False, "2차 인증 세션이 만료되었습니다. `/로그인`을 다시 진행해 주세요.", None

        jar = pending_data["cookie_jar"]
        region = pending_data["region"]
        username = pending_data["username"]
        user_agent = pending_data.get("user_agent", AUTH_CONFIG["user_agent"])

        headers = {
            "Accept": "application/json",
            "Content-Type": "application/json",
            "User-Agent": user_agent,
            "Accept-Language": "ko-KR,ko;q=0.9,en-US;q=0.8,en;q=0.7"
        }

        connector = aiohttp.TCPConnector(ssl=ssl_context)
        async with aiohttp.ClientSession(cookie_jar=jar, headers=headers, connector=connector) as session:
            body_mfa = {
                "type": "multifactor",
                "code": mfa_code.strip(),
                "rememberDevice": True
            }

            try:
                async with session.put(RIOT_AUTH_URL, json=body_mfa) as resp:
                    data = await resp.json()
                    logger.info(f"Riot 2FA response type: {data.get('type')}, error: {data.get('error')}")

                    if data.get("error") or data.get("type") == "error":
                        error_type = data.get("error")
                        if error_type == "multifactor_attempt_failed":
                            return False, "2차 인증 코드가 올바르지 않습니다. 다시 입력해 주세요.", None
                        return False, f"2차 인증 실패: {error_type}", None

                    response_type = data.get("type")
                    if response_type != "response":
                        return False, f"2차 인증 실패 (응답 유형: {response_type})", None

                    redirect_uri = data.get("response", {}).get("parameters", {}).get("uri", "")
                    access_token = self._extract_token_from_url(redirect_uri)
                    if not access_token:
                        return False, "Access Token 파싱 실패", None

            except Exception as e:
                return False, f"2차 인증 처리 중 오류 발생: {str(e)}", None

            del self.pending_2fa[discord_user_id]
            return await self._finish_token_exchange(session, access_token, region, username, discord_user_id)

    async def _finish_token_exchange(self, session: aiohttp.ClientSession, access_token: str, region: str, username: str, discord_user_id: int) -> Tuple[bool, str, Optional[Dict[str, Any]]]:
        """Entitlements Token 및 PUUID 취득 후 최종 세션 저장"""
        entitlements_headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json"
        }
        try:
            async with session.post(RIOT_ENTITLEMENTS_URL, headers=entitlements_headers, json={}) as resp:
                if resp.status != 200:
                    return False, "Entitlements 토큰을 발급받지 못했습니다.", None
                ent_data = await resp.json()
                entitlements_token = ent_data.get("entitlements_token")
        except Exception as e:
            return False, f"Entitlements 토큰 요청 오류: {str(e)}", None

        puuid = self._extract_puuid(access_token)
        if not puuid:
            return False, "사용자 식별자(PUUID) 추출에 실패했습니다.", None

        auth_session = {
            "access_token": access_token,
            "entitlements_token": entitlements_token,
            "puuid": puuid,
            "region": region.lower(),
            "username": username
        }

        self.save_session(discord_user_id, auth_session)
        return True, "성공", auth_session

    def save_session(self, discord_user_id: int, session_data: Dict[str, Any]):
        """사용자의 디스코드 ID별 세션 데이터 세팅"""
        self.user_sessions[discord_user_id] = session_data

    def get_session(self, discord_user_id: int) -> Optional[Dict[str, Any]]:
        """사용자의 세션 데이터 반환"""
        return self.user_sessions.get(discord_user_id)

    def logout(self, discord_user_id: int) -> bool:
        """세션 삭제"""
        if discord_user_id in self.user_sessions:
            del self.user_sessions[discord_user_id]
        if discord_user_id in self.pending_2fa:
            del self.pending_2fa[discord_user_id]
        return True

# 싱글톤 인스턴스
riot_auth_client = RiotAuth()
