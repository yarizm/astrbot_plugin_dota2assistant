# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## 项目概述

AstrBot 平台的 Dota2 数据查询插件。通过 OpenDota API 获取数据，支持 Valve API 作为备选数据源。同时支持两种交互方式：
1. **LLM 工具调用**（主要）— 注册为 AstrBot 的 FunctionTool，LLM 根据用户自然语言自动调用
2. **斜杠命令**（fallback）— `/dota player`、`/dota hero` 等直接命令

## 常用命令

```bash
# 安装依赖
pip install -r requirements.txt

# 运行测试
python -m pytest tests/ -v

# 代码检查
ruff check .
```

## 架构

```
main.py              # 入口，Dota2AssistantPlugin(Star) 子类
compat.py            # AstrBot API 兼容层，无 AstrBot 环境时提供 stub
core/
  opendota.py        # OpenDotaClient — 主数据源，含 Valve API fallback 逻辑
  valve_client.py    # ValveClient — Valve 官方 API 客户端（备选数据源）
  templates.py       # 统一输出模板，Markdown 表格格式 + LLM 解读指引
  models.py          # dataclass 数据模型（HeroInfo, PlayerProfile, MatchDetail 等）
  store.py           # SQLite 存储，管理用户 Steam ID 绑定
tools/               # LLM FunctionTool 实现，每个文件一个工具类
assets/              # heroes.json / items.json — 中文名→内部名映射
tests/               # unittest 测试
```

### 关键设计决策

- **compat.py 双模式**：所有 AstrBot API（`Star`、`Context`、`AstrMessageEvent`、`FunctionTool`、`filter` 等）都通过 try/except 导入，失败时提供 stub 类。这使得代码可在无 AstrBot 环境下导入和测试。
- **工具注册兼容**：`_register_llm_tools()` 同时兼容 `context.add_llm_tools()` 和旧版 `provider_manager.llm_tools.func_list` 两种注册方式。
- **英雄/物品名称映射**：`assets/heroes.json` 和 `assets/items.json` 提供中文别名到 OpenDota 内部名的映射，支持"水人"→"npc_dota_hero_morphling"这类查询。
- **templates 统一输出**：所有工具输出使用 `core/templates.py` 中的模板函数，输出 Markdown 表格格式 + LLM 解读指引。
- **Valve API fallback**：当 OpenDota 返回空数据时，自动切换到 Valve 官方 API。需要配置 `steam_api_key`。

### 新增工具的模式

在 `tools/` 下新建文件，继承 `FunctionTool[AstrAgentContext]`，用 `@dataclass` 装饰。实现 `call()` 方法，返回格式化的字符串。然后在 `main.py` 的 `_register_llm_tools()` 中实例化并注册。

## 配置项

通过 AstrBot 插件管理页面配置，`main.py` 构造函数中读取：
- `enable_fallback_commands` — 是否启用 `/dota` 斜杠命令（默认 true）
- `request_timeout` — API 超时秒数（默认 15）
- `cache_ttl_seconds` — 缓存时间（默认 86400）
- `default_language` — 英雄/物品语言（默认 cn）
- `steam_api_key` — Steam API Key（可选，用于 Valve API 备选数据源）
