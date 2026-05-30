from __future__ import annotations

from compat import AstrAgentContext, ContextWrapper, Field, FunctionTool, ToolExecResult, dataclass


@dataclass
class DotaPlayerTool(FunctionTool[AstrAgentContext]):
    name: str = "dota_player_query"
    description: str = (
        "查询 Dota2 玩家资料、段位、MMR 和近期战绩。"
        "当用户想了解某个 Dota2 玩家时调用，例如查询战绩、段位、最近表现。"
    )
    parameters: dict = Field(
        default_factory=lambda: {
            "type": "object",
            "properties": {
                "player_name": {
                    "type": "string",
                    "description": "玩家名称或 Steam ID，例如 Miracle、yarizm、899428504",
                },
            },
            "required": ["player_name"],
        }
    )
    client: object = Field(default=None, exclude=True)
    formatter: object = Field(default=None, exclude=True)

    async def call(self, context: ContextWrapper[AstrAgentContext], **kwargs) -> ToolExecResult:
        from core.formatter import format_player_profile

        player_name = str(kwargs.get("player_name") or "").strip()
        if not player_name:
            return "请提供玩家名称或 Steam ID。"

        try:
            # Search for player
            profiles = await self.client.search_players(player_name)
            if not profiles:
                return f"找不到名为 '{player_name}' 的 Dota2 玩家。"

            # Use first match
            profile = profiles[0]

            # Get full profile
            full_profile = await self.client.get_player_profile(profile.account_id)
            if full_profile:
                profile = full_profile

            # Get recent matches
            recent = await self.client.get_player_recent_matches(profile.account_id, limit=10)

            result = format_player_profile(profile, recent)
            return f"以下是该玩家的 Dota2 数据，请据此给用户生成简洁总结：\n\n{result}"
        except Exception as exc:
            return f"查询玩家失败：{exc}"
