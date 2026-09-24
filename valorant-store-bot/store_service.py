import os
import ssl
import certifi
import aiohttp
import logging
from typing import Dict, Any, List, Optional, Tuple
from datetime import timedelta

from valorant_api import valorant_api_client
from riot_auth import RiotAuth

logger = logging.getLogger("valorant_bot")

os.environ['SSL_CERT_FILE'] = certifi.where()
ssl_context = ssl.create_default_context(cafile=certifi.where())

# Valorant Points Currency ID in Riot Store API
VP_CURRENCY_ID = "85ad2610-4c01-4c50-a75e-664e2776c5b0"
# Standard Client Platform String Base64 Header for Valorant Client
CLIENT_PLATFORM = "ewogICJwbGF0Zm9ybVR5cGUiOiAiUEMiLAogICJwbGF0Zm9ybU9TIjogIldpbmRvd3MiLAogICJwbGF0Zm9ybU9TVmVyc2lvbiI6ICIxMC4wLjE5MDQ1LjEuMjU2LjY0Yml0IiwKICAicGxhdGZvcm1DaGlwc2V0IjogIlVua25vd24iCn0="

class StoreService:
    """발로란트 상점 API 요청 및 정보 매핑 서비스"""

    @staticmethod
    def format_duration(seconds: int) -> str:
        """초 단위 시간을 [OO시간 OO분] 형식으로 변환"""
        if seconds <= 0:
            return "초기화 진행 중..."
        td = timedelta(seconds=seconds)
        hours, remainder = divmod(td.seconds, 3600)
        minutes, _ = divmod(remainder, 60)
        days = td.days
        if days > 0:
            return f"{days}일 {hours}시간 {minutes}분"
        return f"{hours}시간 {minutes}분"

    async def get_daily_store(self, session_data: Dict[str, Any]) -> Tuple[bool, str, Optional[Dict[str, Any]]]:
        """
        일일 4개 추천 상점 무기 스킨 목록 조회
        """
        region = session_data.get("region", "kr").lower()
        puuid = session_data["puuid"]
        access_token = session_data["access_token"]
        entitlements_token = session_data["entitlements_token"]

        url = f"https://pd.{region}.a.pvp.net/store/v2/storefront/{puuid}"
        headers = {
            "Authorization": f"Bearer {access_token}",
            "X-Riot-Entitlements-JWT": entitlements_token,
            "X-Riot-ClientVersion": valorant_api_client.client_version,
            "X-Riot-ClientPlatform": CLIENT_PLATFORM
        }

        connector = aiohttp.TCPConnector(ssl=ssl_context)
        async with aiohttp.ClientSession(connector=connector) as session:
            try:
                async with session.get(url, headers=headers) as resp:
                    if resp.status == 400 or resp.status == 401:
                        return False, "인증 세션이 만료되었습니다. 다시 로그인해 주세요.", None
                    if resp.status != 200:
                        return False, f"상점 정보를 불러오지 못했습니다. (응답 코드: {resp.status})", None

                    store_raw = await resp.json()
            except Exception as e:
                return False, f"상점 서버 통신 오류: {str(e)}", None

        # 1. 일일 스킨 UUID 및 가격 매핑
        skins_panel = store_raw.get("SkinsPanelLayout", {})
        single_offers = skins_panel.get("SingleItemOffers", [])
        store_offers = skins_panel.get("SingleItemStoreOffers", [])
        remaining_seconds = skins_panel.get("SingleItemOffersRemainingDurationInSeconds", 0)

        offer_prices: Dict[str, int] = {}
        for offer in store_offers:
            offer_id = offer.get("OfferID")
            cost_dict = offer.get("Cost", {})
            vp_price = cost_dict.get(VP_CURRENCY_ID, 0)
            if offer_id:
                offer_prices[offer_id] = vp_price

        items: List[Dict[str, Any]] = []
        for skin_uuid in single_offers:
            skin_meta = valorant_api_client.get_skin(skin_uuid)
            price = offer_prices.get(skin_uuid, 0)
            
            if skin_meta:
                tier_info = valorant_api_client.get_tier(skin_meta.get("tierUuid"))
                items.append({
                    "uuid": skin_uuid,
                    "name": skin_meta.get("name", "알 수 없는 스킨"),
                    "icon": skin_meta.get("icon"),
                    "price": price,
                    "tier": tier_info
                })
            else:
                items.append({
                    "uuid": skin_uuid,
                    "name": "알 수 없는 스킨",
                    "icon": None,
                    "price": price,
                    "tier": valorant_api_client.get_tier(None)
                })

        result_data = {
            "items": items,
            "remaining_seconds": remaining_seconds,
            "remaining_time_str": self.format_duration(remaining_seconds)
        }

        return True, "성공", result_data

    async def get_featured_bundle(self, session_data: Dict[str, Any]) -> Tuple[bool, str, Optional[Dict[str, Any]]]:
        """
        현재 진행 중인 추천 컬렉션 세트(Bundle) 조회
        """
        region = session_data.get("region", "kr").lower()
        puuid = session_data["puuid"]
        access_token = session_data["access_token"]
        entitlements_token = session_data["entitlements_token"]

        url = f"https://pd.{region}.a.pvp.net/store/v2/storefront/{puuid}"
        headers = {
            "Authorization": f"Bearer {access_token}",
            "X-Riot-Entitlements-JWT": entitlements_token,
            "X-Riot-ClientVersion": valorant_api_client.client_version,
            "X-Riot-ClientPlatform": CLIENT_PLATFORM
        }

        connector = aiohttp.TCPConnector(ssl=ssl_context)
        async with aiohttp.ClientSession(connector=connector) as session:
            try:
                async with session.get(url, headers=headers) as resp:
                    if resp.status != 200:
                        return False, "컬렉션 정보를 불러오지 못했습니다.", None
                    store_raw = await resp.json()
            except Exception as e:
                return False, f"통신 오류: {str(e)}", None

        featured_bundle = store_raw.get("FeaturedBundle", {})
        bundles_list = featured_bundle.get("Bundles", [])
        if not bundles_list:
            return False, "현재 판매 중인 추천 컬렉션 세트가 없습니다.", None

        active_bundle = bundles_list[0]
        bundle_uuid = active_bundle.get("DataAssetID")
        remaining_seconds = active_bundle.get("SecondsRemaining", 0)
        
        total_vp = 0
        items_list = active_bundle.get("Items", [])
        for item in items_list:
            total_vp += item.get("DiscountedPrice", 0)

        bundle_meta = valorant_api_client.get_bundle(bundle_uuid)
        if not bundle_meta:
            bundle_meta = {
                "name": "추천 컬렉션 세트",
                "description": "발로란트 한정 패키지 세트",
                "banner": None,
                "icon": None
            }

        result_data = {
            "uuid": bundle_uuid,
            "name": bundle_meta.get("name"),
            "description": bundle_meta.get("description"),
            "banner": bundle_meta.get("banner"),
            "price": total_vp,
            "item_count": len(items_list),
            "remaining_time_str": self.format_duration(remaining_seconds)
        }

        return True, "성공", result_data

    async def get_night_market(self, session_data: Dict[str, Any]) -> Tuple[bool, str, Optional[Dict[str, Any]]]:
        """
        야시장(Bonus Store) 할인 상품 조회
        """
        region = session_data.get("region", "kr").lower()
        puuid = session_data["puuid"]
        access_token = session_data["access_token"]
        entitlements_token = session_data["entitlements_token"]

        url = f"https://pd.{region}.a.pvp.net/store/v2/storefront/{puuid}"
        headers = {
            "Authorization": f"Bearer {access_token}",
            "X-Riot-Entitlements-JWT": entitlements_token,
            "X-Riot-ClientVersion": valorant_api_client.client_version,
            "X-Riot-ClientPlatform": CLIENT_PLATFORM
        }

        connector = aiohttp.TCPConnector(ssl=ssl_context)
        async with aiohttp.ClientSession(connector=connector) as session:
            try:
                async with session.get(url, headers=headers) as resp:
                    if resp.status != 200:
                        return False, "야시장 정보를 불러올 수 없습니다.", None
                    store_raw = await resp.json()
            except Exception as e:
                return False, f"통신 오류: {str(e)}", None

        bonus_store = store_raw.get("BonusStore")
        if not bonus_store or "BonusStoreOffers" not in bonus_store:
            return False, "현재 진행 중인 야시장이 없습니다.", None

        offers = bonus_store.get("BonusStoreOffers", [])
        remaining_seconds = bonus_store.get("BonusStoreRemainingDurationInSeconds", 0)

        items: List[Dict[str, Any]] = []
        for offer_item in offers:
            offer = offer_item.get("Offer", {})
            offer_id = offer.get("OfferID")
            cost_dict = offer.get("Cost", {})
            original_price = cost_dict.get(VP_CURRENCY_ID, 0)

            discount_costs = offer_item.get("DiscountCosts", {})
            discounted_price = discount_costs.get(VP_CURRENCY_ID, original_price)
            discount_percent = offer_item.get("DiscountPercent", 0)
            is_purchased = offer_item.get("IsPurchased", False)

            skin_meta = valorant_api_client.get_skin(offer_id)
            if skin_meta:
                tier_info = valorant_api_client.get_tier(skin_meta.get("tierUuid"))
                items.append({
                    "name": skin_meta.get("name"),
                    "icon": skin_meta.get("icon"),
                    "original_price": original_price,
                    "discounted_price": discounted_price,
                    "discount_percent": discount_percent,
                    "is_purchased": is_purchased,
                    "tier": tier_info
                })

        result_data = {
            "items": items,
            "remaining_time_str": self.format_duration(remaining_seconds)
        }

        return True, "성공", result_data

store_service = StoreService()
