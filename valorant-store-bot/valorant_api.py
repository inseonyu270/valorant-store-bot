import aiohttp
import logging
from typing import Dict, Any, Optional

from config import VALORANT_API_BASE, LANGUAGE, TIER_COLORS

logger = logging.getLogger("valorant_bot")

class ValorantAPI:
    """valorant-api.com 한국어 메타데이터 캐싱 및 조회 클래스"""
    def __init__(self):
        self.skins: Dict[str, Dict[str, Any]] = {}
        self.tiers: Dict[str, Dict[str, Any]] = {}
        self.bundles: Dict[str, Dict[str, Any]] = {}
        self.client_version: str = "release-08.11-shipping-17-2591605"
        self.is_initialized: bool = False

    async def initialize(self):
        """메타데이터 초기화 및 메모리 캐싱"""
        async with aiohttp.ClientSession() as session:
            # 1. 최신 클라이언트 버전 가져오기
            try:
                async with session.get(f"{VALORANT_API_BASE}/version") as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        self.client_version = data.get("data", {}).get("riotClientVersion", self.client_version)
            except Exception as e:
                logger.warning(f"Failed to fetch client version: {e}")

            # 2. 스킨 메타데이터 (한국어)
            try:
                async with session.get(f"{VALORANT_API_BASE}/weapons/skins?language={LANGUAGE}") as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        for skin in data.get("data", []):
                            # 스킨 level / chroma UUID도 인덱싱
                            skin_uuid = skin.get("uuid")
                            display_name = skin.get("displayName")
                            display_icon = skin.get("displayIcon")
                            tier_uuid = skin.get("contentTierUuid")
                            
                            # 레벨 정보에서 첫 번째 아이콘 백업
                            if not display_icon and skin.get("levels"):
                                display_icon = skin["levels"][0].get("displayIcon")

                            skin_info = {
                                "uuid": skin_uuid,
                                "name": display_name,
                                "icon": display_icon,
                                "tierUuid": tier_uuid,
                                "levels": skin.get("levels", []),
                                "chromas": skin.get("chromas", []),
                            }
                            self.skins[skin_uuid] = skin_info
                            
                            # skin level uuid 매핑
                            for lvl in skin.get("levels", []):
                                if lvl.get("uuid"):
                                    self.skins[lvl["uuid"]] = skin_info
            except Exception as e:
                logger.error(f"Failed to fetch skins: {e}")

            # 3. 등급(Tier) 메타데이터
            try:
                async with session.get(f"{VALORANT_API_BASE}/contenttiers?language={LANGUAGE}") as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        for tier in data.get("data", []):
                            t_uuid = tier.get("uuid")
                            self.tiers[t_uuid] = {
                                "uuid": t_uuid,
                                "name": tier.get("displayName"),
                                "icon": tier.get("displayIcon"),
                                "color": TIER_COLORS.get(t_uuid, 0xff4655)
                            }
            except Exception as e:
                logger.error(f"Failed to fetch tiers: {e}")

            # 4. 컬렉션(Bundle) 메타데이터
            try:
                async with session.get(f"{VALORANT_API_BASE}/bundles?language={LANGUAGE}") as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        for bundle in data.get("data", []):
                            b_uuid = bundle.get("uuid")
                            self.bundles[b_uuid] = {
                                "uuid": b_uuid,
                                "name": bundle.get("displayName"),
                                "description": bundle.get("extraDescription") or bundle.get("displayNameSubText"),
                                "icon": bundle.get("displayIcon") or bundle.get("verticalPromoImage"),
                                "banner": bundle.get("displayIcon2") or bundle.get("verticalPromoImage") or bundle.get("displayIcon")
                            }
            except Exception as e:
                logger.error(f"Failed to fetch bundles: {e}")

        self.is_initialized = True
        logger.info("ValorantAPI metadata cached successfully.")

    def get_skin(self, uuid: str) -> Optional[Dict[str, Any]]:
        """UUID로 스킨 정보 검색"""
        return self.skins.get(uuid)

    def get_tier(self, tier_uuid: Optional[str]) -> Dict[str, Any]:
        """Tier UUID로 등급 정보 검색"""
        if tier_uuid and tier_uuid in self.tiers:
            return self.tiers[tier_uuid]
        return {
            "uuid": tier_uuid or "",
            "name": "일반",
            "icon": None,
            "color": 0x909090
        }

    def get_bundle(self, uuid: str) -> Optional[Dict[str, Any]]:
        """UUID로 컬렉션 세트 정보 검색"""
        return self.bundles.get(uuid)

# 싱글톤 인스턴스 생성
valorant_api_client = ValorantAPI()
