from __future__ import annotations

from compat import AstrAgentContext, ContextWrapper, Field, FunctionTool, ToolExecResult, dataclass


@dataclass
class DotaProTool(FunctionTool[AstrAgentContext]):
    name: str = "dota_pro_matches"
    description: str = (
        "查看近期 Dota2 职业比赛结果，包括战队、比分、赛事名称。"
        "当用户想了解职业比赛、赛事结果、战队表现时调用。"
    )
    parameters: dict = Field(
        default_factory=lambda: {
            "type": "object",
            "properties": {
                "limit": {
                    "type": "integer",
                    "description": "返回比赛数量，默认 10",
                },
            },
            "required": [],
        }
    )
    client: object = Field(default=None, exclude=True)

    async def call(self, context: ContextWrapper[AstrAgentContext], **kwargs) -> ToolExecResult:
        from core.formatter import format_pro_matches

        limit = kwargs.get("limit", 10)
        try:
            limit = int(limit) if limit else 10
        except (TypeError, ValueError):
            limit = 10

        try:
            matches = await self.client.get_pro_matches(limit=limit)
            result = format_pro_matches(matches)
            return f"以下是近期 Dota2 职业比赛数据，请据此给用户生成简洁总结：\n\n{result}"
        except Exception as exc:
            return f"查询职业比赛失败：{exc}"
