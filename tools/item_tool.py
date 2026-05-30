from __future__ import annotations

from compat import AstrAgentContext, ContextWrapper, Field, FunctionTool, ToolExecResult, dataclass


@dataclass
class DotaItemTool(FunctionTool[AstrAgentContext]):
    name: str = "dota_item_query"
    description: str = (
        "查询 Dota2 物品价格、效果、合成配方。"
        "当用户想了解某个物品时调用，例如物品价格、效果、合成路线。"
    )
    parameters: dict = Field(
        default_factory=lambda: {
            "type": "object",
            "properties": {
                "item_name": {
                    "type": "string",
                    "description": "物品名称，中文或英文均可，例如：Blink Dagger、跳刀、黑皇杖",
                },
            },
            "required": ["item_name"],
        }
    )
    client: object = Field(default=None, exclude=True)
    item_name_map: object = Field(default=None, exclude=True)

    async def call(self, context: ContextWrapper[AstrAgentContext], **kwargs) -> ToolExecResult:
        from core.formatter import format_item_info

        item_name = str(kwargs.get("item_name") or "").strip().lower()
        if not item_name:
            return "请提供物品名称。"

        try:
            items = await self.client.get_items()
            if not items:
                return "获取物品数据失败。"

            # Search by display name or internal name
            item = None
            for key, val in items.items():
                if (item_name == val.display_name.lower()
                        or item_name == key.lower()
                        or item_name in val.display_name.lower()):
                    item = val
                    break

            # Try Chinese name mapping
            if not item and self.item_name_map:
                internal = self.item_name_map.get(item_name)
                if internal and internal in items:
                    item = items[internal]

            if not item:
                # Fuzzy match
                matches = [
                    val for val in items.values()
                    if item_name in val.display_name.lower() or item_name in val.name.lower()
                ]
                if len(matches) == 1:
                    item = matches[0]
                elif len(matches) > 1:
                    names = ", ".join(m.display_name for m in matches[:5])
                    return f"找到多个匹配的物品：{names}。请提供更精确的名称。"

            if not item:
                return f"找不到名为 '{item_name}' 的物品。"

            result = format_item_info(item)
            return f"以下是该物品的 Dota2 数据，请据此给用户生成简洁总结：\n\n{result}"
        except Exception as exc:
            return f"查询物品失败：{exc}"
