from __future__ import annotations

from datetime import datetime, timezone

from core.models import (
    HeroInfo,
    ItemInfo,
    LiveGame,
    MatchDetail,
    PlayerProfile,
    ProMatch,
    RecentMatch,
)


def format_player_profile(profile: PlayerProfile, recent_matches: list[RecentMatch] | None = None) -> str:
    """格式化玩家资料，供 LLM 总结。"""
    lines = [f"# 玩家：{profile.persona_name or profile.account_id}"]

    if profile.profile_url:
        lines.append(f"[Steam 主页]({profile.profile_url})")

    rank_str = _format_rank(profile.rank_tier, profile.leaderboard_rank)
    lines.append(f"- **段位**: {rank_str}")
    if profile.estimated_mmr:
        lines.append(f"- **估算 MMR**: {profile.estimated_mmr}")
    lines.append("")

    if recent_matches:
        lines.append("## 近期战绩")
        wins = sum(1 for m in recent_matches if m.win)
        losses = len(recent_matches) - wins
        lines.append(f"- 胜负: {wins}胜 {losses}负 (胜率 {wins / len(recent_matches) * 100:.0f}%)")
        avg_kda = _avg_kda(recent_matches)
        lines.append(f"- 平均 KDA: {avg_kda}")
        lines.append("")

        lines.append("最近比赛：")
        for m in recent_matches[:5]:
            result = "✅" if m.win else "❌"
            duration = _format_duration(m.duration_seconds)
            kda = f"{m.kills}/{m.deaths}/{m.assists}"
            lines.append(f"  {result} {m.hero_name} — {kda} ({duration})")
        lines.append("")

    return "\n".join(lines)


def format_hero_info(hero: HeroInfo) -> str:
    """格式化英雄信息，供 LLM 总结。"""
    attr_map = {"str": "力量", "agi": "敏捷", "int": "智力", "all": "全能"}
    attr_str = attr_map.get(hero.primary_attr, hero.primary_attr)

    lines = [
        f"# {hero.localized_name}",
        f"- **主属性**: {attr_str}",
        f"- **攻击类型**: {hero.attack_type}",
        f"- **定位**: {', '.join(hero.roles)}",
        "",
        "## 基础属性",
        f"- 力量: {hero.base_str} (+{hero.str_gain}/级)",
        f"- 敏捷: {hero.base_agi} (+{hero.agi_gain}/级)",
        f"- 智力: {hero.base_int} (+{hero.int_gain}/级)",
        f"- 基础生命: {hero.base_health}",
        f"- 基础魔法: {hero.base_mana}",
        f"- 基础护甲: {hero.base_armor}",
        f"- 攻击力: {hero.base_attack_min}-{hero.base_attack_max}",
        f"- 移动速度: {hero.move_speed}",
        "",
    ]

    if hero.pub_pick > 0:
        win_rate = hero.pub_win / hero.pub_pick * 100
        lines.append("## 天梯数据")
        lines.append(f"- 选取次数: {hero.pub_pick:,}")
        lines.append(f"- 胜率: {win_rate:.1f}%")
        lines.append("")

    if hero.pro_pick > 0:
        pro_win_rate = hero.pro_win / hero.pro_pick * 100
        lines.append("## 职业数据")
        lines.append(f"- 选取次数: {hero.pro_pick:,}")
        lines.append(f"- 胜率: {pro_win_rate:.1f}%")
        lines.append("")

    return "\n".join(lines)


def format_hero_list(heroes: list[HeroInfo], filter_attr: str = "", filter_role: str = "") -> str:
    """格式化英雄列表，供 LLM 总结。"""
    filtered = heroes
    if filter_attr:
        filtered = [h for h in filtered if h.primary_attr == filter_attr]
    if filter_role:
        filtered = [h for h in filtered if filter_role in h.roles]

    if not filtered:
        return "没有找到符合条件的英雄。"

    lines = [f"# 英雄列表（共 {len(filtered)} 个）"]
    if filter_attr:
        attr_map = {"str": "力量", "agi": "敏捷", "int": "智力", "all": "全能"}
        lines.append(f"筛选：主属性={attr_map.get(filter_attr, filter_attr)}")
    if filter_role:
        lines.append(f"筛选：定位={filter_role}")
    lines.append("")

    # Group by attribute
    attr_order = ["str", "agi", "int", "all"]
    attr_names = {"str": "力量英雄", "agi": "敏捷英雄", "int": "智力英雄", "all": "全能英雄"}
    for attr in attr_order:
        group = [h for h in filtered if h.primary_attr == attr]
        if not group:
            continue
        lines.append(f"## {attr_names[attr]}")
        names = ", ".join(h.localized_name for h in sorted(group, key=lambda x: x.localized_name))
        lines.append(names)
        lines.append("")

    return "\n".join(lines)


def format_item_info(item: ItemInfo) -> str:
    """格式化物品信息，供 LLM 总结。"""
    lines = [
        f"# {item.display_name}",
        f"- **价格**: {item.cost}",
    ]
    if item.item_type:
        lines.append(f"- **类型**: {item.item_type}")
    if item.description:
        lines.append(f"- **效果**: {item.description}")
    if item.components:
        lines.append(f"- **合成需要**: {', '.join(item.components)}")
    lines.append("")
    return "\n".join(lines)


def format_match_detail(match: MatchDetail) -> str:
    """格式化比赛详情，供 LLM 总结。"""
    result = "天辉胜" if match.radiant_win else "夜魇胜"
    duration = _format_duration(match.duration_seconds)
    start = datetime.fromtimestamp(match.start_time, tz=timezone.utc).strftime("%Y-%m-%d %H:%M") if match.start_time else ""

    lines = [
        f"# 比赛 #{match.match_id}",
        f"- **结果**: {result}",
        f"- **比分**: {match.radiant_score} : {match.dire_score}",
        f"- **时长**: {duration}",
    ]
    if start:
        lines.append(f"- **时间**: {start}")
    lines.append("")

    # Split players by team
    radiant = [p for p in match.players if p.is_radiant]
    dire = [p for p in match.players if not p.is_radiant]

    lines.append("## 天辉")
    for p in radiant:
        result_icon = "✅" if p.win else "❌"
        kda = f"{p.kills}/{p.deaths}/{p.assists}"
        lines.append(f"  {result_icon} {p.hero_name} — {kda} | GPM:{p.gpm} 伤害:{p.hero_damage:,}")
    lines.append("")

    lines.append("## 夜魇")
    for p in dire:
        result_icon = "✅" if p.win else "❌"
        kda = f"{p.kills}/{p.deaths}/{p.assists}"
        lines.append(f"  {result_icon} {p.hero_name} — {kda} | GPM:{p.gpm} 伤害:{p.hero_damage:,}")
    lines.append("")

    return "\n".join(lines)


def format_live_games(games: list[LiveGame]) -> str:
    """格式化实时比赛列表，供 LLM 总结。"""
    if not games:
        return "当前没有正在进行的比赛数据。"

    lines = [f"# 实时比赛（共 {len(games)} 场）", ""]

    for g in games:
        radiant_name = g.team_name_radiant or "天辉"
        dire_name = g.team_name_dire or "夜魇"
        score = f"{g.radiant_score} : {g.dire_score}"
        game_time = _format_duration(g.game_time)
        mmr_str = f" (平均 {g.average_mmr} MMR)" if g.average_mmr else ""
        spectators_str = f" | {g.spectators} 观战" if g.spectators else ""

        lines.append(f"- **{radiant_name}** vs **{dire_name}** — {score} ({game_time}){mmr_str}{spectators_str}")

    lines.append("")
    return "\n".join(lines)


def format_pro_matches(matches: list[ProMatch]) -> str:
    """格式化职业比赛列表，供 LLM 总结。"""
    if not matches:
        return "暂无职业比赛数据。"

    lines = [f"# 近期职业比赛（共 {len(matches)} 场）", ""]

    for m in matches:
        radiant = m.radiant_team_name or "天辉"
        dire = m.dire_team_name or "夜魇"
        score = f"{m.radiant_score} : {m.dire_score}"
        winner = radiant if m.radiant_win else dire
        duration = _format_duration(m.duration_seconds)
        start = datetime.fromtimestamp(m.start_time, tz=timezone.utc).strftime("%m-%d %H:%M") if m.start_time else ""
        league = f" | {m.league_name}" if m.league_name else ""

        lines.append(f"- **{radiant}** vs **{dire}** — {score} | 胜者: {winner} ({duration}){league} {start}")

    lines.append("")
    return "\n".join(lines)


# --- Helpers ---

def _format_rank(rank_tier: int, leaderboard_rank: int) -> str:
    if not rank_tier:
        return "未知"
    tier = rank_tier // 10
    star = rank_tier % 10
    tier_names = {1: "先锋", 2: "卫士", 3: "中军", 4: "统帅", 5: "传奇", 6: "万古流芳", 7: "超凡入圣", 8: "冠绝一世"}
    name = tier_names.get(tier, f"段位{tier}")
    result = f"{name} {star}星" if star else name
    if leaderboard_rank:
        result += f" (排名 #{leaderboard_rank})"
    return result


def _format_duration(seconds: int) -> str:
    if seconds <= 0:
        return "未知"
    m, s = divmod(seconds, 60)
    h, m = divmod(m, 60)
    if h > 0:
        return f"{h}:{m:02d}:{s:02d}"
    return f"{m}:{s:02d}"


def _avg_kda(matches: list[RecentMatch]) -> str:
    if not matches:
        return "N/A"
    total_k = sum(m.kills for m in matches)
    total_d = sum(m.deaths for m in matches)
    total_a = sum(m.assists for m in matches)
    n = len(matches)
    kda_ratio = (total_k + total_a) / max(total_d, 1)
    return f"{total_k / n:.1f}/{total_d / n:.1f}/{total_a / n:.1f} ({kda_ratio:.2f})"
