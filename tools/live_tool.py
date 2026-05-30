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
        from core.templates import render_live_games

        try:
            games = await self.client.get_live_games()
            return render_live_games(games)
        except Exception as exc:
            return f"查询实时比赛失败：{exc}"
