from __future__ import annotations

import asyncio
from typing import Any

try:
    import aiohttp

    _AIOHTTP_AVAILABLE = True
except ModuleNotFoundError:
    _AIOHTTP_AVAILABLE = False

    class _MissingAiohttp:
        class ClientError(Exception):
            pass

        class ClientTimeout:
            def __init__(self, total: int):
                self.total = total

        class ClientSession:
            def __init__(self, *_args, **_kwargs):
                raise RuntimeError("aiohttp is required to make OpenDota API requests")

    aiohttp = _MissingAiohttp()

from compat import logger
from core.models import (
    HeroInfo,
    ItemInfo,
    LiveGame,
    MatchDetail,
    MatchPlayer,
    PlayerProfile,
    ProMatch,
    RecentMatch,
)

BASE_URL = "https://api.opendota.com/api"


class OpenDotaClient:
    def __init__(self, timeout: int = 15):
        self.timeout = aiohttp.ClientTimeout(total=timeout)

    # --- Player ---

    async def search_players(self, query: str) -> list[PlayerProfile]:
        # 数字输入直接按 account_id 查询
        if query.isdigit():
            account_id = int(query)
            profile = await self.get_player_profile(account_id)
            if profile:
                return [profile]
            # 可能是 Steam ID 64-bit (76561198xxxxxxxxx)，转为 32-bit
            if len(query) == 17 and query.startswith("76561198"):
                account_id_32 = account_id - 76561197960265728
                profile = await self.get_player_profile(account_id_32)
                if profile:
                    return [profile]
            return []

        # 非数字走名称搜索
        data = await self._get("/search", params={"q": query}, context="玩家搜索")
        if not isinstance(data, list):
            return []
        return [
            PlayerProfile(
                account_id=item.get("account_id", 0),
                persona_name=item.get("personaname", ""),
                avatar_url=item.get("avatarfull", ""),
            )
            for item in data[:10]
        ]

    async def get_player_profile(self, account_id: int) -> PlayerProfile | None:
        data = await self._get(f"/players/{account_id}", context="玩家资料")
        if not isinstance(data, dict):
            return None
        profile = data.get("profile", {})
        return PlayerProfile(
            account_id=account_id,
            persona_name=profile.get("personaname", ""),
            profile_url=profile.get("profileurl", ""),
            avatar_url=profile.get("avatarfull", ""),
            rank_tier=data.get("rank_tier") or 0,
            leaderboard_rank=data.get("leaderboard_rank") or 0,
            estimated_mmr=data.get("mmr_estimate", {}).get("estimate", 0),
        )

    async def get_player_recent_matches(self, account_id: int, limit: int = 10) -> list[RecentMatch]:
        data = await self._get(f"/players/{account_id}/recentMatches", context="近期比赛")
        if not isinstance(data, list):
            return []
        # Build hero lookup
        heroes = await self.get_heroes()
        hero_map = {h.id: h.localized_name for h in heroes}

        matches = []
        for item in data[:limit]:
            hero_id = item.get("hero_id", 0)
            matches.append(RecentMatch(
                match_id=item.get("match_id", 0),
                hero_id=hero_id,
                hero_name=hero_map.get(hero_id, f"Hero#{hero_id}"),
                kills=item.get("kills", 0),
                deaths=item.get("deaths", 0),
                assists=item.get("assists", 0),
                duration_seconds=item.get("duration", 0),
                win=_is_radiant_win(item),
                game_mode=item.get("game_mode", 0),
                start_time=item.get("start_time", 0),
                gpm=item.get("gold_per_min", 0),
                xpm=item.get("xp_per_min", 0),
                hero_damage=item.get("hero_damage", 0),
                tower_damage=item.get("tower_damage", 0),
                last_hits=item.get("last_hits", 0),
            ))
        return matches

    # --- Heroes ---

    async def get_heroes(self) -> list[HeroInfo]:
        data = await self._get("/heroStats", context="英雄数据")
        if not isinstance(data, list):
            return []
        return [
            HeroInfo(
                id=h.get("id", 0),
                name=h.get("name", ""),
                localized_name=h.get("localized_name", ""),
                primary_attr=h.get("primary_attr", ""),
                attack_type=h.get("attack_type", ""),
                roles=h.get("roles", []),
                base_health=h.get("base_health", 0),
                base_mana=h.get("base_mana", 0),
                base_armor=h.get("base_armor", 0),
                base_attack_min=h.get("base_attack_min", 0),
                base_attack_max=h.get("base_attack_max", 0),
                base_str=h.get("base_str", 0),
                base_agi=h.get("base_agi", 0),
                base_int=h.get("base_int", 0),
                str_gain=h.get("str_gain", 0),
                agi_gain=h.get("agi_gain", 0),
                int_gain=h.get("int_gain", 0),
                move_speed=h.get("move_speed", 0),
                pro_pick=h.get("pro_pick", 0),
                pro_win=h.get("pro_win", 0),
                pub_pick=h.get("pub_pick", 0),
                pub_win=h.get("pub_win", 0),
            )
            for h in data
        ]

    # --- Items ---

    async def get_items(self) -> dict[str, ItemInfo]:
        data = await self._get("/constants/items", context="物品数据")
        if not isinstance(data, dict):
            return {}
        items = {}
        for key, val in data.items():
            items[key] = ItemInfo(
                name=key,
                display_name=val.get("dname", key),
                cost=val.get("cost", 0),
                description=_extract_item_description(val),
                behavior=str(val.get("behavior", "")),
                item_type=val.get("qual", ""),
                components=[c for c in (val.get("components") or []) if c],
            )
        return items

    # --- Match ---

    async def get_match_detail(self, match_id: int) -> MatchDetail | None:
        data = await self._get(f"/matches/{match_id}", context="比赛详情")
        if not isinstance(data, dict):
            return None

        heroes = await self.get_heroes()
        hero_map = {h.id: h.localized_name for h in heroes}

        players = []
        for p in data.get("players", []):
            hero_id = p.get("hero_id", 0)
            items = []
            for i in range(6):
                item_key = f"item_{i}"
                item_val = p.get(item_key)
                if item_val:
                    items.append(str(item_val))

            players.append(MatchPlayer(
                account_id=p.get("account_id") or p.get("player_slot", 0),
                persona_name=p.get("personaname") or "",
                hero_id=hero_id,
                hero_name=hero_map.get(hero_id, f"Hero#{hero_id}"),
                kills=p.get("kills", 0),
                deaths=p.get("deaths", 0),
                assists=p.get("assists", 0),
                gpm=p.get("gold_per_min", 0),
                xpm=p.get("xp_per_min", 0),
                hero_damage=p.get("hero_damage", 0),
                tower_damage=p.get("tower_damage", 0),
                hero_healing=p.get("hero_healing", 0),
                last_hits=p.get("last_hits", 0),
                denies=p.get("denies", 0),
                net_worth=p.get("net_worth", 0),
                level=p.get("level", 0),
                items=items,
                is_radiant=p.get("isRadiant", False),
                win=p.get("win", False),
            ))

        return MatchDetail(
            match_id=match_id,
            duration_seconds=data.get("duration", 0),
            radiant_win=data.get("radiant_win", False),
            radiant_score=data.get("radiant_score", 0),
            dire_score=data.get("dire_score", 0),
            game_mode=data.get("game_mode", 0),
            start_time=data.get("start_time", 0),
            patch=data.get("patch", ""),
            region=str(data.get("region", "")),
            players=players,
            picks_bans=data.get("picks_bans") or [],
        )

    # --- Live ---

    async def get_live_games(self) -> list[LiveGame]:
        data = await self._get("/live", context="实时比赛")
        if not isinstance(data, list):
            return []
        return [
            LiveGame(
                match_id=g.get("match_id", 0),
                game_time=g.get("game_time", 0),
                average_mmr=g.get("average_mmr", 0),
                radiant_score=g.get("radiant_score", 0),
                dire_score=g.get("dire_score", 0),
                radiant_lead=g.get("radiant_lead", 0),
                spectators=g.get("spectators", 0),
                league_id=g.get("league_id", 0),
                team_name_radiant=g.get("team_name_radiant", ""),
                team_name_dire=g.get("team_name_dire", ""),
                players=g.get("players") or [],
            )
            for g in data[:20]
        ]

    # --- Pro ---

    async def get_pro_matches(self, limit: int = 10) -> list[ProMatch]:
        data = await self._get("/proMatches", context="职业比赛")
        if not isinstance(data, list):
            return []
        return [
            ProMatch(
                match_id=m.get("match_id", 0),
                duration_seconds=m.get("duration", 0),
                start_time=m.get("start_time", 0),
                radiant_team_name=m.get("radiant_name", ""),
                dire_team_name=m.get("dire_name", ""),
                radiant_score=m.get("radiant_score", 0),
                dire_score=m.get("dire_score", 0),
                radiant_win=m.get("radiant_win", False),
                league_name=m.get("league_name", ""),
                series_type=m.get("series_type", 0),
            )
            for m in data[:limit]
        ]

    # --- Internal ---

    async def _get(self, path: str, params: dict[str, Any] | None = None, context: str = "OpenDota") -> Any | None:
        if not _AIOHTTP_AVAILABLE:
            logger.warning(f"{context} 请求跳过：当前环境未安装 aiohttp。")
            return None

        url = f"{BASE_URL}{path}"
        try:
            async with aiohttp.ClientSession(timeout=self.timeout) as session:
                async with session.get(url, params=params) as response:
                    if response.status == 429:
                        logger.warning(f"{context} 请求触发频率限制。")
                        return None
                    if response.status >= 400:
                        logger.warning(f"{context} 请求失败，HTTP {response.status}。")
                        return None
                    return await response.json(content_type=None)
        except (TimeoutError, asyncio.TimeoutError):
            logger.warning(f"{context} 请求超时。")
        except aiohttp.ClientError:
            logger.warning(f"{context} 网络请求失败。")
        except ValueError:
            logger.warning(f"{context} JSON 解析失败。")
        return None


def _is_radiant_win(match_data: dict) -> bool:
    """判断玩家是否胜利。recentMatches 中通过 player_slot + radiant_win 推断。"""
    radiant_win = match_data.get("radiant_win", False)
    player_slot = match_data.get("player_slot", 0)
    is_radiant = player_slot < 128
    return radiant_win == is_radiant


def _extract_item_description(item_data: dict) -> str:
    """提取物品描述（abilities 中的 description）。"""
    abilities = item_data.get("abilities") or []
    parts = []
    for ab in abilities:
        desc = ab.get("description", "")
        if desc:
            parts.append(desc)
    hint = item_data.get("hint") or []
    for h in hint:
        if h:
            parts.append(h)
    return " ".join(parts)[:300]
