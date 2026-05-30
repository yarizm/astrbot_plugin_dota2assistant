from __future__ import annotations

from compat import AstrAgentContext, ContextWrapper, Field, FunctionTool, ToolExecResult, dataclass


@dataclass
class DotaHeroBuildTool(FunctionTool[AstrAgentContext]):
    name: str = "dota_hero_item_build"
    description: str = (
        "查询 Dota2 英雄的出装推荐，包括出门装、前中后期装备。"
        "当用户想了解某个英雄怎么出装、出装推荐、装备路线时调用。"
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

            # Format output
            result = self._format_build(hero.localized_name, build_data, id_map)
            return f"以下是 {hero.localized_name} 的出装推荐数据，请据此给用户生成简洁总结：\n\n{result}"
        except Exception as exc:
            return f"查询英雄出装失败：{exc}"

    @staticmethod
    def _format_build(hero_name: str, build_data: dict, id_map: dict) -> str:
        phase_names = {
            "start_game_items": "出门装",
            "early_game_items": "前期",
            "mid_game_items": "中期",
            "late_game_items": "后期",
        }
        lines = [f"# {hero_name} 出装推荐", ""]

        for phase_key, phase_label in phase_names.items():
            items = build_data.get(phase_key)
            if not items:
                continue
            lines.append(f"## {phase_label}")
            sorted_items = sorted(items.items(), key=lambda x: int(x[1]), reverse=True)[:5]
            for item_id, count in sorted_items:
                item_id = int(item_id)
                name = id_map.get(item_id, f"Item#{item_id}")
                lines.append(f"- {name}: {count}%")
            lines.append("")

        return "\n".join(lines)
