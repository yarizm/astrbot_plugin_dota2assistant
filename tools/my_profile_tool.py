from __future__ import annotations

from compat import AstrAgentContext, ContextWrapper, Field, FunctionTool, ToolExecResult, dataclass


@dataclass
class DotaMyProfileTool(FunctionTool[AstrAgentContext]):
    name: str = "dota_my_profile"
    description: str = (
        "查询当前用户自己绑定的 Dota2 账号资料、段位和近期战绩。"
        "当用户说「我的战绩」「我的天梯分」「我最近打得怎么样」「查一下我的dota」时调用。"
        "注意：此工具仅在用户已绑定 Steam ID 时有效。"
    )
    parameters: dict = Field(
        default_factory=lambda: {
            "type": "object",
            "properties": {},
            "required": [],
        }
    )
    client: object = Field(default=None, exclude=True)
    store: object = Field(default=None, exclude=True)

    async def call(self, context: ContextWrapper[AstrAgentContext], **kwargs) -> ToolExecResult:
        from core.templates import fmt_avg_kda, fmt_rank, render_player_profile

        event = context.context.event
        sender_id = event.get_sender_id()

        if not sender_id:
            return "无法获取用户身份信息。"

        try:
            account_id = self.store.get_bound_account(sender_id)
            if not account_id:
                return "你还没有绑定 Steam ID。请使用 /dota bind <Steam ID> 命令绑定。"

            profile = await self.client.get_player_profile(account_id)
            if not profile:
                return f"获取绑定账号 #{account_id} 的资料失败，请检查绑定的 ID 是否正确。"

            recent = await self.client.get_player_recent_matches(account_id, limit=10)

            rank_str = fmt_rank(profile.rank_tier, profile.leaderboard_rank)
            avg_kda = fmt_avg_kda(recent)
            return render_player_profile(profile, recent, rank_str, avg_kda)
        except Exception as exc:
            return f"查询失败：{exc}"
