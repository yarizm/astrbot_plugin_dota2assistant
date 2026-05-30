from __future__ import annotations

from compat import AstrAgentContext, ContextWrapper, Field, FunctionTool, ToolExecResult, dataclass


@dataclass
class DotaHeroTool(FunctionTool[AstrAgentContext]):
    name: str = "dota_hero_query"
    description: str = (
        "查询 Dota2 英雄属性、技能数据、天梯胜率和职业选取率。"
        "当用户想了解某个英雄时调用，例如英雄属性、胜率、定位。"
    )
    parameters: dict = Field(
        default_factory=lambda: {
            "type": "object",
            "properties": {
                "hero_name": {
                    "type": "string",
                    "description": "英雄名称，中文或英文均可，例如：反恐怖利刃、Anti-Mage、火猫",
                },
            },
            "required": ["hero_name"],
        }
    )
    client: object = Field(default=None, exclude=True)
    hero_map: object = Field(default=None, exclude=True)

    async def call(self, context: ContextWrapper[AstrAgentContext], **kwargs) -> ToolExecResult:
        from core.formatter import format_hero_info

        hero_name = str(kwargs.get("hero_name") or "").strip().lower()
        if not hero_name:
            return "请提供英雄名称。"

        try:
            heroes = await self.client.get_heroes()
            if not heroes:
                return "获取英雄数据失败。"

            # Search by localized name or internal name
            hero = None
            for h in heroes:
                if (hero_name == h.localized_name.lower()
                        or hero_name == h.name.lower()
                        or hero_name == h.name.replace("npc_dota_hero_", "").lower()):
                    hero = h
                    break

            # Try Chinese name mapping
            if not hero and self.hero_map:
                internal = self.hero_map.get(hero_name)
                if internal:
                    for h in heroes:
                        if h.name == internal:
                            hero = h
                            break

            if not hero:
                # Fuzzy match
                matches = [h for h in heroes if hero_name in h.localized_name.lower() or hero_name in h.name.lower()]
                if len(matches) == 1:
                    hero = matches[0]
                elif len(matches) > 1:
                    names = ", ".join(h.localized_name for h in matches[:5])
                    return f"找到多个匹配的英雄：{names}。请提供更精确的名称。"

            if not hero:
                return f"找不到名为 '{hero_name}' 的英雄。"

            result = format_hero_info(hero)
            return f"以下是该英雄的 Dota2 数据，请据此给用户生成简洁总结：\n\n{result}"
        except Exception as exc:
            return f"查询英雄失败：{exc}"


@dataclass
class DotaHeroListTool(FunctionTool[AstrAgentContext]):
    name: str = "dota_hero_list"
    description: str = (
        "列出 Dota2 英雄，可按属性或定位筛选。"
        "当用户想看英雄列表、某个属性的英雄、某个定位的英雄时调用。"
    )
    parameters: dict = Field(
        default_factory=lambda: {
            "type": "object",
            "properties": {
                "attribute": {
                    "type": "string",
                    "description": "主属性筛选：str(力量)、agi(敏捷)、int(智力)、all(全能)，留空则全部",
                    "enum": ["str", "agi", "int", "all", ""],
                },
                "role": {
                    "type": "string",
                    "description": "定位筛选：Carry、Support、Nuker、Disabler、Initiator、Escape、Pusher，留空则全部",
                },
            },
            "required": [],
        }
    )
    client: object = Field(default=None, exclude=True)

    async def call(self, context: ContextWrapper[AstrAgentContext], **kwargs) -> ToolExecResult:
        from core.formatter import format_hero_list

        attribute = str(kwargs.get("attribute") or "").strip()
        role = str(kwargs.get("role") or "").strip()

        try:
            heroes = await self.client.get_heroes()
            if not heroes:
                return "获取英雄数据失败。"

            result = format_hero_list(heroes, filter_attr=attribute, filter_role=role)
            return f"以下是 Dota2 英雄列表数据，请据此给用户生成简洁总结：\n\n{result}"
        except Exception as exc:
            return f"查询英雄列表失败：{exc}"
