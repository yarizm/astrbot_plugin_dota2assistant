from __future__ import annotations

from compat import AstrAgentContext, ContextWrapper, Field, FunctionTool, ToolExecResult, dataclass


@dataclass
class DotaHeroBuildTool(FunctionTool[AstrAgentContext]):
    name: str = "dota_hero_item_build"
    description: str = (
        "查询 Dota2 英雄的出装推荐，包括出门装、前中后期装备。"
        "当用户想了解某个英雄怎么出装、出装推荐、装备路线时调用。"
        "返回数据后，请根据以下要点为用户生成简洁分析：\n"
        "1. 按阶段（出门装→前中后期）简要说明出装思路\n"
        "2. 指出核心装备和可选装备\n"
        "3. 如果有 situational 装备，说明适用场景"
    )
    parameters: dict = Field(
        default_factory=lambda: {
            "type": "object",
            "properties": {
                "hero_name": {
                    "type": "string",
                    "description": "英雄名称，中文或英文均可，例如：水人、Morphling、火猫",
                },
            },
            "required": ["hero_name"],
        }
    )
    client: object = Field(default=None, exclude=True)
    hero_map: object = Field(default=None, exclude=True)

    async def call(self, context: ContextWrapper[AstrAgentContext], **kwargs) -> ToolExecResult:
        from core.templates import render_hero_build

        hero_name = str(kwargs.get("hero_name") or "").strip().lower()
        if not hero_name:
            return "请提供英雄名称。"

        try:
            # Find hero
            heroes = await self.client.get_heroes()
            if not heroes:
                return "获取英雄数据失败。"

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
                matches = [h for h in heroes if hero_name in h.localized_name.lower() or hero_name in h.name.lower()]
                if len(matches) == 1:
                    hero = matches[0]
                elif len(matches) > 1:
                    names = ", ".join(h.localized_name for h in matches[:5])
                    return f"找到多个英雄：{names}。请提供更精确的名称。"

            if not hero:
                return f"找不到名为 '{hero_name}' 的英雄。"

            # Get item builds
            build_data = await self.client._get(f"/heroes/{hero.id}/itemPopularity", context="英雄出装")
            if not isinstance(build_data, dict):
                return f"获取 {hero.localized_name} 的出装数据失败。"

            # Fetch full item constants for ID mapping
            item_constants = await self.client._get("/constants/items", context="物品常量")
            id_map = {}
            if isinstance(item_constants, dict):
                for key, val in item_constants.items():
                    item_id = val.get("id")
                    dname = val.get("dname", key)
                    if item_id:
                        id_map[item_id] = dname

            return render_hero_build(hero.localized_name, build_data, id_map)
        except Exception as exc:
            return f"查询英雄出装失败：{exc}"
