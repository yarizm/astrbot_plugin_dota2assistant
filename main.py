from __future__ import annotations

import json
import sys
from pathlib import Path

# 确保插件目录在 sys.path 中（AstrBot 运行时加载插件需要）
_plugin_dir = str(Path(__file__).parent)
if _plugin_dir not in sys.path:
    sys.path.insert(0, _plugin_dir)

from compat import AstrMessageEvent, Context, Star, filter, logger  # noqa: E402
from core.opendota import OpenDotaClient  # noqa: E402
from core.store import DotaStore  # noqa: E402

_ASSETS_DIR = Path(__file__).parent / "assets"


class Dota2AssistantPlugin(Star):
    def __init__(self, context: Context, config: dict | None = None):
        super().__init__(context)

        plugin_config = config or {}
        self.enable_fallback = plugin_config.get("enable_fallback_commands", True)
        timeout = plugin_config.get("request_timeout", 15)

        # 数据目录
        try:
            from astrbot.core.utils.astrbot_path import get_astrbot_data_path
            data_dir = Path(get_astrbot_data_path()) / "plugin_data" / "dota2assistant"
        except Exception:
            data_dir = Path(__file__).parent / "data"

        self.client = OpenDotaClient(timeout=timeout)
        self.store = DotaStore(data_dir / "dota2.db")
        self.hero_map = _load_json_map(_ASSETS_DIR / "heroes.json")
        self.item_name_map = _load_json_map(_ASSETS_DIR / "items.json")

        self._register_llm_tools()

        logger.info(f"Dota2 助手插件已加载（英雄映射 {len(self.hero_map)} 条，物品映射 {len(self.item_name_map)} 条）。")

    def _register_llm_tools(self) -> None:
        from tools.hero_build_tool import DotaHeroBuildTool
        from tools.hero_tool import DotaHeroListTool, DotaHeroTool
        from tools.item_tool import DotaItemTool
        from tools.live_tool import DotaLiveTool
        from tools.match_tool import DotaMatchTool
        from tools.my_profile_tool import DotaMyProfileTool
        from tools.player_tool import DotaPlayerTool
        from tools.pro_tool import DotaProTool

        tools = (
            DotaPlayerTool(client=self.client),
            DotaMyProfileTool(client=self.client, store=self.store),
            DotaHeroTool(client=self.client, hero_map=self.hero_map),
            DotaHeroListTool(client=self.client),
            DotaHeroBuildTool(client=self.client, hero_map=self.hero_map),
            DotaItemTool(client=self.client, item_name_map=self.item_name_map),
            DotaMatchTool(client=self.client),
            DotaLiveTool(client=self.client),
            DotaProTool(client=self.client),
        )

        add_llm_tools = getattr(self.context, "add_llm_tools", None)
        if callable(add_llm_tools):
            add_llm_tools(*tools)
            return

        tool_manager = getattr(getattr(self.context, "provider_manager", None), "llm_tools", None)
        func_list = getattr(tool_manager, "func_list", None)
        if isinstance(func_list, list):
            func_list.extend(tools)
            return

        logger.warning("当前 AstrBot Context 不支持 LLM Tool 注册，已跳过 Dota2 工具注册。")

    # --- Fallback commands ---

    @filter.command_group("dota")
    def dota(self):
        """Dota2 查询命令组"""

    @dota.command("player")
    async def dota_player(self, event: AstrMessageEvent):
        '''查询玩家资料和近期战绩: /dota player <玩家名>'''
        if not self.enable_fallback:
            return

        player_name = event.message_str.strip()
        if not player_name:
            yield event.plain_result("请输入玩家名称，例如：/dota player Miracle")
            return

        yield event.plain_result(f"正在查询玩家 [{player_name}] ...")
        try:
            from core.templates import fmt_avg_kda, fmt_rank, render_player_profile

            profiles = await self.client.search_players(player_name)
            if not profiles:
                yield event.plain_result(f"找不到名为 '{player_name}' 的玩家。")
                return

            profile = profiles[0]
            full_profile = await self.client.get_player_profile(profile.account_id)
            if full_profile:
                profile = full_profile

            recent = await self.client.get_player_recent_matches(profile.account_id, limit=10)
            rank_str = fmt_rank(profile.rank_tier, profile.leaderboard_rank)
            avg_kda = fmt_avg_kda(recent)
            yield event.plain_result(render_player_profile(profile, recent, rank_str, avg_kda))
        except Exception as exc:
            logger.error(f"Dota2 玩家查询失败: {exc}")
            yield event.plain_result("查询失败：Dota2 服务暂时不可用，请稍后再试。")

    @dota.command("hero")
    async def dota_hero(self, event: AstrMessageEvent):
        '''查询英雄信息: /dota hero <英雄名>'''
        if not self.enable_fallback:
            return

        hero_name = event.message_str.strip().lower()
        if not hero_name:
            yield event.plain_result("请输入英雄名称，例如：/dota hero 反恐怖利刃")
            return

        yield event.plain_result(f"正在查询英雄 [{hero_name}] ...")
        try:
            from core.templates import render_hero_info

            heroes = await self.client.get_heroes()
            hero = None
            for h in heroes:
                if (hero_name == h.localized_name.lower()
                        or hero_name == h.name.lower()
                        or hero_name == h.name.replace("npc_dota_hero_", "").lower()):
                    hero = h
                    break

            if not hero and self.hero_map:
                internal = self.hero_map.get(hero_name)
                if internal:
                    for h in heroes:
                        if h.name == internal:
                            hero = h
                            break

            if not hero:
                matches = [h for h in heroes if hero_name in h.localized_name.lower()]
                if len(matches) == 1:
                    hero = matches[0]
                elif len(matches) > 1:
                    names = ", ".join(h.localized_name for h in matches[:5])
                    yield event.plain_result(f"找到多个英雄：{names}，请提供更精确的名称。")
                    return

            if not hero:
                yield event.plain_result(f"找不到名为 '{hero_name}' 的英雄。")
                return

            yield event.plain_result(render_hero_info(hero))
        except Exception as exc:
            logger.error(f"Dota2 英雄查询失败: {exc}")
            yield event.plain_result("查询失败：Dota2 服务暂时不可用，请稍后再试。")

    @dota.command("match")
    async def dota_match(self, event: AstrMessageEvent):
        '''查询比赛详情: /dota match <比赛ID>'''
        if not self.enable_fallback:
            return

        match_id_str = event.message_str.strip()
        if not match_id_str or not match_id_str.isdigit():
            yield event.plain_result("请输入比赛 ID（数字），例如：/dota match 8831125663")
            return

        match_id = int(match_id_str)
        yield event.plain_result(f"正在查询比赛 #{match_id} ...")
        try:
            from core.templates import render_match_detail

            match = await self.client.get_match_detail(match_id)
            if not match:
                yield event.plain_result(f"获取比赛 #{match_id} 失败，比赛可能不存在。")
                return

            yield event.plain_result(render_match_detail(match))
        except Exception as exc:
            logger.error(f"Dota2 比赛查询失败: {exc}")
            yield event.plain_result("查询失败：Dota2 服务暂时不可用，请稍后再试。")

    @dota.command("live")
    async def dota_live(self, event: AstrMessageEvent):
        '''查看实时比赛: /dota live'''
        if not self.enable_fallback:
            return

        yield event.plain_result("正在查询实时比赛 ...")
        try:
            from core.templates import render_live_games

            games = await self.client.get_live_games()
            yield event.plain_result(render_live_games(games))
        except Exception as exc:
            logger.error(f"Dota2 实时比赛查询失败: {exc}")
            yield event.plain_result("查询失败：Dota2 服务暂时不可用，请稍后再试。")

    @dota.command("pro")
    async def dota_pro(self, event: AstrMessageEvent):
        '''查看职业比赛: /dota pro'''
        if not self.enable_fallback:
            return

        yield event.plain_result("正在查询职业比赛 ...")
        try:
            from core.templates import render_pro_matches

            matches = await self.client.get_pro_matches(limit=10)
            yield event.plain_result(render_pro_matches(matches))
        except Exception as exc:
            logger.error(f"Dota2 职业比赛查询失败: {exc}")
            yield event.plain_result("查询失败：Dota2 服务暂时不可用，请稍后再试。")

    @dota.command("bind")
    async def dota_bind(self, event: AstrMessageEvent):
        '''绑定 Steam ID: /dota bind <Steam ID>'''
        sender_id = event.get_sender_id()
        if not sender_id:
            yield event.plain_result("无法获取用户身份信息。")
            return

        # 从消息中提取数字（兼容各种格式）
        import re
        numbers = re.findall(r"\d+", event.message_str.strip())
        if not numbers:
            yield event.plain_result(
                "请提供 Steam ID，支持两种格式：\n"
                "- Steam ID 32-bit（数字），例如：/dota bind 899428504\n"
                "- Steam ID 64-bit（17位数字），例如：/dota bind 76561198859694232"
            )
            return

        steam_id_str = numbers[0]

        account_id = int(steam_id_str)
        # Steam ID 64-bit 转 32-bit
        if len(steam_id_str) == 17 and steam_id_str.startswith("76561198"):
            account_id = account_id - 76561197960265728

        # 验证 ID 是否有效
        yield event.plain_result(f"正在验证 Steam ID #{account_id} ...")
        try:
            profile = await self.client.get_player_profile(account_id)
            if not profile:
                yield event.plain_result(f"Steam ID #{account_id} 无效，请检查后重试。")
                return

            self.store.bind_account(sender_id, account_id, profile.persona_name or "")
            name = profile.persona_name or str(account_id)
            yield event.plain_result(f"绑定成功！已将你的 Dota2 账号绑定为 {name} (#{account_id})。\n之后可以说「查一下我的战绩」来查询。")
        except Exception as exc:
            logger.error(f"Dota2 绑定失败: {exc}")
            yield event.plain_result(f"绑定失败：{exc}")

    @dota.command("unbind")
    async def dota_unbind(self, event: AstrMessageEvent):
        '''解除 Steam ID 绑定: /dota unbind'''
        sender_id = event.get_sender_id()
        if not sender_id:
            yield event.plain_result("无法获取用户身份信息。")
            return

        try:
            existing = self.store.get_bound_account(sender_id)
            if not existing:
                yield event.plain_result("你还没有绑定过 Steam ID。")
                return

            self.store.unbind_account(sender_id)
            yield event.plain_result("已解除 Steam ID 绑定。")
        except Exception as exc:
            logger.error(f"Dota2 解绑失败: {exc}")
            yield event.plain_result(f"解绑失败：{exc}")

    async def terminate(self):
        """插件卸载时清理。"""


def _load_json_map(path: Path) -> dict[str, str]:
    """加载 JSON 映射文件，失败返回空 dict。"""
    try:
        if path.exists():
            return json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:
        logger.warning(f"加载映射文件 {path.name} 失败: {exc}")
    return {}
