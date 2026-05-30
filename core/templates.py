"""工具输出模板，统一格式并引导 LLM 生成有价值的解读。"""

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


# ──────────────────────────────────────────────
# 辅助函数
# ──────────────────────────────────────────────


def fmt_duration(seconds: int) -> str:
    """格式化秒数为 H:MM:SS 或 M:SS。"""
    if seconds <= 0:
        return "未知"
    m, s = divmod(seconds, 60)
    h, m = divmod(m, 60)
    if h > 0:
        return f"{h}:{m:02d}:{s:02d}"
    return f"{m}:{s:02d}"


def fmt_rank(rank_tier: int, leaderboard_rank: int = 0) -> str:
    """格式化段位信息。"""
    if not rank_tier:
        return "未知"
    tier = rank_tier // 10
    star = rank_tier % 10
    tier_names = {
        1: "先锋", 2: "卫士", 3: "中军", 4: "统帅",
        5: "传奇", 6: "万古流芳", 7: "超凡入圣", 8: "冠绝一世",
    }
    name = tier_names.get(tier, f"段位{tier}")
    result = f"{name} {star}星" if star else name
    if leaderboard_rank:
        result += f" (排名 #{leaderboard_rank})"
    return result


def fmt_avg_kda(matches: list[RecentMatch]) -> str:
    """计算平均 KDA。"""
    if not matches:
        return "N/A"
    total_k = sum(m.kills for m in matches)
    total_d = sum(m.deaths for m in matches)
    total_a = sum(m.assists for m in matches)
    n = len(matches)
    kda_ratio = (total_k + total_a) / max(total_d, 1)
    return f"{total_k / n:.1f}/{total_d / n:.1f}/{total_a / n:.1f} ({kda_ratio:.2f})"


# ──────────────────────────────────────────────
# 玩家资料 + 近期战绩
# ──────────────────────────────────────────────

_PLAYER_TEMPLATE = """\
# 玩家资料：{persona_name}

| 项目 | 数据 |
|------|------|
| Steam ID | {account_id} |
| 段位 | {rank} |
| 估算 MMR | {mmr} |

## 近期战绩（最近 {match_count} 场）

**总体**: {wins}胜 {losses}负（胜率 {win_rate}%）
**平均 KDA**: {avg_kda}

| 结果 | 英雄 | KDA | 时长 | GPM | 伤害 |
|------|------|-----|------|-----|------|
{match_rows}

---
**解读指引**：
1. 根据胜率和 KDA 评价该玩家近期状态（上升/稳定/下滑）
2. 指出表现突出或需改进的方面
3. 如果近期常用英雄集中，点评英雄池特点
4. 语气友好，适合聊天场景
"""


def render_player_profile(
    profile: PlayerProfile,
    recent_matches: list[RecentMatch],
    rank_str: str,
    avg_kda_str: str,
) -> str:
    """渲染玩家资料 + 近期战绩模板。"""
    wins = sum(1 for m in recent_matches if m.win)
    losses = len(recent_matches) - wins
    win_rate = f"{wins / len(recent_matches) * 100:.0f}" if recent_matches else "N/A"

    match_rows = []
    for m in recent_matches[:5]:
        result = "✅" if m.win else "❌"
        duration = fmt_duration(m.duration_seconds)
        kda = f"{m.kills}/{m.deaths}/{m.assists}"
        match_rows.append(f"| {result} | {m.hero_name} | {kda} | {duration} | {m.gpm} | {m.hero_damage:,} |")

    return _PLAYER_TEMPLATE.format(
        persona_name=profile.persona_name or str(profile.account_id),
        account_id=profile.account_id,
        rank=rank_str,
        mmr=profile.estimated_mmr or "未知",
        match_count=len(recent_matches),
        wins=wins,
        losses=losses,
        win_rate=win_rate,
        avg_kda=avg_kda_str,
        match_rows="\n".join(match_rows) if match_rows else "| - | 暂无数据 | - | - | - | - |",
    )


# ──────────────────────────────────────────────
# 英雄信息
# ──────────────────────────────────────────────

_HERO_TEMPLATE = """\
# 英雄：{localized_name}

| 属性 | 值 |
|------|-----|
| 主属性 | {primary_attr} |
| 攻击类型 | {attack_type} |
| 定位 | {roles} |
| 力量 | {base_str} (+{str_gain}/级) |
| 敏捷 | {base_agi} (+{agi_gain}/级) |
| 智力 | {base_int} (+{int_gain}/级) |
| 基础生命/魔法 | {base_health} / {base_mana} |
| 基础护甲 | {base_armor} |
| 攻击力 | {base_attack_min}-{base_attack_max} |
| 移动速度 | {move_speed} |

{stats_section}

---
**解读指引**：
1. 根据属性成长分析该英雄的核心定位（前期/中期/后期强势）
2. 结合天梯胜率和职业数据点评当前版本强度
3. 推荐适合的打法思路（1-2 句话）
4. 如果有职业数据，对比天梯和职业的表现差异
"""


def render_hero_info(hero: HeroInfo) -> str:
    """渲染英雄信息模板。"""
    attr_map = {"str": "力量", "agi": "敏捷", "int": "智力", "all": "全能"}

    stats_parts = []
    if hero.pub_pick > 0:
        win_rate = hero.pub_win / hero.pub_pick * 100
        stats_parts.append(f"## 天梯数据\n- 选取次数: {hero.pub_pick:,}\n- 胜率: {win_rate:.1f}%")
    if hero.pro_pick > 0:
        pro_win_rate = hero.pro_win / hero.pro_pick * 100
        stats_parts.append(f"## 职业数据\n- 选取次数: {hero.pro_pick:,}\n- 胜率: {pro_win_rate:.1f}%")
    stats_section = "\n\n".join(stats_parts) if stats_parts else ""

    return _HERO_TEMPLATE.format(
        localized_name=hero.localized_name,
        primary_attr=attr_map.get(hero.primary_attr, hero.primary_attr),
        attack_type=hero.attack_type,
        roles=", ".join(hero.roles),
        base_str=hero.base_str,
        str_gain=hero.str_gain,
        base_agi=hero.base_agi,
        agi_gain=hero.agi_gain,
        base_int=hero.base_int,
        int_gain=hero.int_gain,
        base_health=hero.base_health,
        base_mana=hero.base_mana,
        base_armor=hero.base_armor,
        base_attack_min=hero.base_attack_min,
        base_attack_max=hero.base_attack_max,
        move_speed=hero.move_speed,
        stats_section=stats_section,
    )


# ──────────────────────────────────────────────
# 英雄列表
# ──────────────────────────────────────────────

_HERO_LIST_TEMPLATE = """\
# 英雄列表（共 {count} 个）
{filter_desc}

{grouped_section}

---
**解读指引**：
1. 如果有筛选条件，简要说明筛选结果的特点
2. 如果用户问"推荐英雄"，根据列表推荐 2-3 个适合当前版本的英雄
"""


def render_hero_list(heroes: list[HeroInfo], filter_attr: str = "", filter_role: str = "") -> str:
    """渲染英雄列表模板。"""
    filtered = heroes
    if filter_attr:
        filtered = [h for h in filtered if h.primary_attr == filter_attr]
    if filter_role:
        filtered = [h for h in filtered if filter_role in h.roles]

    if not filtered:
        return "没有找到符合条件的英雄。"

    attr_map = {"str": "力量", "agi": "敏捷", "int": "智力", "all": "全能"}
    filter_parts = []
    if filter_attr:
        filter_parts.append(f"主属性={attr_map.get(filter_attr, filter_attr)}")
    if filter_role:
        filter_parts.append(f"定位={filter_role}")
    filter_desc = f"\n筛选：{', '.join(filter_parts)}" if filter_parts else ""

    attr_order = ["str", "agi", "int", "all"]
    attr_names = {"str": "力量英雄", "agi": "敏捷英雄", "int": "智力英雄", "all": "全能英雄"}
    groups = []
    for attr in attr_order:
        group = [h for h in filtered if h.primary_attr == attr]
        if not group:
            continue
        names = ", ".join(h.localized_name for h in sorted(group, key=lambda x: x.localized_name))
        groups.append(f"## {attr_names[attr]}\n{names}")
    grouped_section = "\n\n".join(groups)

    return _HERO_LIST_TEMPLATE.format(
        count=len(filtered),
        filter_desc=filter_desc,
        grouped_section=grouped_section,
    )


# ──────────────────────────────────────────────
# 英雄出装
# ──────────────────────────────────────────────

_HERO_BUILD_TEMPLATE = """\
# {hero_name} 出装推荐

{build_section}

---
**解读指引**：
1. 按阶段（出门装→前中后期）简要说明出装思路
2. 指出核心装备和可选装备
3. 如果有 situational 装备，说明适用场景
"""


def render_hero_build(hero_name: str, build_data: dict, id_map: dict) -> str:
    """渲染英雄出装模板。"""
    phase_names = {
        "start_game_items": "出门装",
        "early_game_items": "前期",
        "mid_game_items": "中期",
        "late_game_items": "后期",
    }
    sections = []
    for phase_key, phase_label in phase_names.items():
        items = build_data.get(phase_key)
        if not items:
            continue
        sorted_items = sorted(items.items(), key=lambda x: int(x[1]), reverse=True)[:5]
        rows = [f"| {id_map.get(int(item_id), f'Item#{item_id}')} | {count}% |" for item_id, count in sorted_items]
        sections.append(f"## {phase_label}\n| 装备 | 选取率 |\n|------|--------|\n" + "\n".join(rows))

    return _HERO_BUILD_TEMPLATE.format(
        hero_name=hero_name,
        build_section="\n\n".join(sections) if sections else "暂无出装数据",
    )


# ──────────────────────────────────────────────
# 物品信息
# ──────────────────────────────────────────────

_ITEM_TEMPLATE = """\
# 物品：{display_name}

| 属性 | 值 |
|------|-----|
| 价格 | {cost} |
| 类型 | {item_type} |
| 效果 | {description} |
| 合成需要 | {components} |

---
**解读指引**：
1. 简要说明该物品的核心作用
2. 推荐适合什么类型的英雄/什么局势出
3. 如果是合成件，说明合成路线的性价比
"""


def render_item_info(item: ItemInfo) -> str:
    """渲染物品信息模板。"""
    return _ITEM_TEMPLATE.format(
        display_name=item.display_name,
        cost=item.cost,
        item_type=item.item_type or "基础",
        description=item.description or "无",
        components=", ".join(item.components) if item.components else "无（基础物品）",
    )


# ──────────────────────────────────────────────
# 比赛详情
# ──────────────────────────────────────────────

_MATCH_TEMPLATE = """\
# 比赛详情 #{match_id}

| 项目 | 数据 |
|------|------|
| 结果 | {result} |
| 比分 | {radiant_score} : {dire_score} |
| 时长 | {duration} |
| 时间 | {start_time} |

## 天辉
| 英雄 | KDA | GPM | 伤害 |
|------|-----|-----|------|
{radiant_rows}

## 夜魇
| 英雄 | KDA | GPM | 伤害 |
|------|-----|-----|------|
{dire_rows}

---
**解读指引**：
1. 分析比赛胜负关键（哪方经济领先、关键团战等）
2. 指出表现突出的玩家（MVP 候选）
3. 如果用户指定了玩家，重点分析该玩家的表现
"""


def render_match_detail(match: MatchDetail) -> str:
    """渲染比赛详情模板。"""
    result = "天辉胜" if match.radiant_win else "夜魇胜"
    duration = fmt_duration(match.duration_seconds)
    start_time = (
        datetime.fromtimestamp(match.start_time, tz=timezone.utc).strftime("%Y-%m-%d %H:%M")
        if match.start_time else "未知"
    )

    radiant = [p for p in match.players if p.is_radiant]
    dire = [p for p in match.players if not p.is_radiant]

    def player_rows(players):
        rows = []
        for p in players:
            icon = "✅" if p.win else "❌"
            kda = f"{p.kills}/{p.deaths}/{p.assists}"
            rows.append(f"| {icon} {p.hero_name} | {kda} | {p.gpm} | {p.hero_damage:,} |")
        return "\n".join(rows) if rows else "| - | - | - | - |"

    return _MATCH_TEMPLATE.format(
        match_id=match.match_id,
        result=result,
        radiant_score=match.radiant_score,
        dire_score=match.dire_score,
        duration=duration,
        start_time=start_time,
        radiant_rows=player_rows(radiant),
        dire_rows=player_rows(dire),
    )


# ──────────────────────────────────────────────
# 实时比赛
# ──────────────────────────────────────────────

_LIVE_TEMPLATE = """\
# 实时比赛（共 {count} 场）

| 天辉 | 夜魇 | 比分 | 进行时间 | MMR | 观战 |
|------|------|------|----------|-----|------|
{game_rows}

---
**解读指引**：
1. 如果有高 MMR 或职业选手的比赛，重点提及
2. 指出正在进行的精彩对决
"""


def render_live_games(games: list[LiveGame]) -> str:
    """渲染实时比赛模板。"""
    if not games:
        return "当前没有正在进行的比赛。"

    rows = []
    for g in games:
        radiant = g.team_name_radiant or "天辉"
        dire = g.team_name_dire or "夜魇"
        score = f"{g.radiant_score}:{g.dire_score}"
        game_time = fmt_duration(g.game_time)
        mmr = g.average_mmr or "-"
        spectators = g.spectators or "-"
        rows.append(f"| {radiant} | {dire} | {score} | {game_time} | {mmr} | {spectators} |")

    return _LIVE_TEMPLATE.format(
        count=len(games),
        game_rows="\n".join(rows),
    )


# ──────────────────────────────────────────────
# 职业比赛
# ──────────────────────────────────────────────

_PRO_TEMPLATE = """\
# 近期职业比赛（共 {count} 场）

| 天辉 | 夜魇 | 比分 | 胜者 | 时长 | 赛事 | 时间 |
|------|------|------|------|------|------|------|
{match_rows}

---
**解读指引**：
1. 指出重要的比赛结果（决赛、爆冷等）
2. 如果用户关注特定战队，重点点评该战队表现
"""


def render_pro_matches(matches: list[ProMatch]) -> str:
    """渲染职业比赛模板。"""
    if not matches:
        return "暂无职业比赛数据。"

    rows = []
    for m in matches:
        radiant = m.radiant_team_name or "天辉"
        dire = m.dire_team_name or "夜魇"
        score = f"{m.radiant_score}:{m.dire_score}"
        winner = radiant if m.radiant_win else dire
        duration = fmt_duration(m.duration_seconds)
        start = (
            datetime.fromtimestamp(m.start_time, tz=timezone.utc).strftime("%m-%d %H:%M")
            if m.start_time else ""
        )
        league = m.league_name or "-"
        rows.append(f"| {radiant} | {dire} | {score} | {winner} | {duration} | {league} | {start} |")

    return _PRO_TEMPLATE.format(
        count=len(matches),
        match_rows="\n".join(rows),
    )
