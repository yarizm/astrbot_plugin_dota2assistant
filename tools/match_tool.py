from __future__ import annotations

from compat import AstrAgentContext, ContextWrapper, Field, FunctionTool, ToolExecResult, dataclass


@dataclass
class DotaMatchTool(FunctionTool[AstrAgentContext]):
    name: str = "dota_match_detail"
    description: str = (
        "查询 Dota2 比赛详情，包括双方阵容、KDA、经济、伤害等数据。"
        "当用户想了解某场比赛时调用，例如比赛分析、对局回顾。"
        "返回数据后，请根据以下要点为用户生成简洁分析：\n"
        "1. 分析比赛胜负关键（哪方经济领先、关键团战等）\n"
        "2. 指出表现突出的玩家（MVP 候选）\n"
        "3. 如果用户指定了玩家，重点分析该玩家的表现"
    )
    parameters: dict = Field(
        default_factory=lambda: {
            "type": "object",
            "properties": {
                "match_id": {
                    "type": "integer",
                    "description": "比赛 ID（数字），例如 8831125663",
                },
            },
            "required": ["match_id"],
        }
    )
    client: object = Field(default=None, exclude=True)

    async def call(self, context: ContextWrapper[AstrAgentContext], **kwargs) -> ToolExecResult:
        from core.templates import render_match_detail

        match_id = kwargs.get("match_id")
        if not match_id:
            return "请提供比赛 ID。"

        try:
            match_id = int(match_id)
        except (TypeError, ValueError):
            return "比赛 ID 必须是数字。"

        try:
            match = await self.client.get_match_detail(match_id)
            if not match:
                return f"获取比赛 #{match_id} 的数据失败，比赛可能不存在或数据尚未解析。"

            return render_match_detail(match)
        except Exception as exc:
            return f"查询比赛失败：{exc}"
