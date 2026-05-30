from __future__ import annotations

from compat import AstrAgentContext, ContextWrapper, Field, FunctionTool, ToolExecResult, dataclass


@dataclass
class DotaLiveTool(FunctionTool[AstrAgentContext]):
    name: str = "dota_live_games"
    description: str = (
        "查看当前正在进行的 Dota2 比赛，包括比分、进行时间、观战人数。"
        "当用户想看正在进行的比赛、当前有哪些比赛时调用。"
    )
    parameters: dict = Field(
        default_factory=lambda: {
            "type": "object",
            "properties": {},
            "required": [],
        }
    )
    client: object = Field(default=None, exclude=True)

    async def call(self, context: ContextWrapper[AstrAgentContext], **kwargs) -> ToolExecResult:
        from core.formatter import format_live_games

        try:
            games = await self.client.get_live_games()
            result = format_live_games(games)
            return f"以下是当前 Dota2 实时比赛数据，请据此给用户生成简洁总结：\n\n{result}"
        except Exception as exc:
            return f"查询实时比赛失败：{exc}"
