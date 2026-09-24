import os
from dotenv import load_dotenv

load_dotenv()

DISCORD_BOT_TOKEN = os.getenv("DISCORD_BOT_TOKEN", "")
DEFAULT_REGION = os.getenv("DEFAULT_REGION", "kr")

# Valorant API (공식 static 데이터)
VALORANT_API_BASE = "https://valorant-api.com/v1"
LANGUAGE = "ko-KR"

# Riot Auth & Client 정보 (Unofficial Client Headers)
CLIENT_VERSION_URL = "https://valorant-api.com/v1/version"
RIOT_AUTH_URL = "https://auth.riotgames.com/api/v1/authorization"
RIOT_ENTITLEMENTS_URL = "https://entitlements.auth.riotgames.com/api/token/v1"

# 무기 등급별 색상 (Hex & RGB for Discord Embeds)
TIER_COLORS = {
    "00000000-0000-0000-0000-000000000000": 0x909090, # Default / Select (하늘색/회색)
    "126016fa-456d-4736-96a3-0d8e2192408f": 0x5a9fe2, # Select (스탠다드)
    "60b37308-4c23-460f-8614-37146352c45d": 0x00b0f0, # Deluxe (디럭스)
    "60b37308-4c23-460f-8614-37146352c45e": 0x00b0f0, 
    "d18776db-4731-4e8e-a612-6dbb4776b0cf": 0xd1548d, # Premium (프리미엄 - 핑크/보라)
    "e0408772-444e-43b1-8636-12841b126486": 0xf5a623, # Exclusive (익스클루시브 - 주황/골드)
    "411e4a5a-4e82-421e-a40c-a35b120c8633": 0xffff00, # Ultra (울트라 - 노랑)
}

# 기본 fallback 색상
DEFAULT_EMBED_COLOR = 0xff4655 # 라이엇 발로란트 레드
