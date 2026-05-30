# AstrBot Dota2 助手插件

Dota2 数据查询插件，支持自然语言触发，通过 LLM 工具自动调用 OpenDota API 返回结果。

## 功能

| 功能 | 自然语言示例 | 命令 |
|------|-------------|------|
| 玩家查询 | "查一下 miracle 的战绩" | `/dota player miracle` |
| 我的战绩 | "查一下我的天梯分" | 需先绑定 |
| 英雄查询 | "水人属性是什么" | `/dota hero 水人` |
| 出装推荐 | "水人怎么出装" | - |
| 物品查询 | "跳刀多少钱" | - |
| 比赛详情 | "分析比赛 8831125663" | `/dota match 8831125663` |
| 实时比赛 | "现在有什么比赛在打" | `/dota live` |
| 职业赛事 | "最近 TI 结果" | `/dota pro` |
| 英雄列表 | "有哪些力量英雄" | - |

## 绑定 Steam ID

```
/dota bind 899428504          # 32-bit Steam ID
/dota bind 76561198859694232  # 64-bit Steam ID
/dota unbind                  # 解除绑定
```

绑定后可以说"查一下我的战绩"直接查询。

## 安装

1. 将插件目录放入 AstrBot 的 `data/plugins/` 目录
2. 安装依赖：`pip install aiohttp`
3. 重启 AstrBot 或在插件管理页面重载

## 配置

在 AstrBot 插件管理页面可配置：

| 配置项 | 说明 | 默认值 |
|--------|------|--------|
| `default_language` | 英雄/物品名称默认语言 | `cn` |
| `enable_fallback_commands` | 是否启用 `/dota` 命令 | `true` |
| `request_timeout` | API 请求超时（秒） | `15` |
| `cache_ttl_seconds` | 数据缓存时间（秒） | `86400` |
| `steam_api_key` | Steam API Key（可选，用于获取比赛数据） | 空 |

### Steam API Key（可选）

如果 OpenDota 无法获取某些玩家的比赛数据，可以配置 Steam API Key 作为备选数据源：

1. 访问 https://steamcommunity.com/dev/apikey 申请 API Key
2. 在插件管理页面配置 `steam_api_key`
3. 当 OpenDota 返回空数据时，会自动切换到 Valve API

## 数据源

| API | 说明 | 链接 |
|-----|------|------|
| OpenDota API | Dota2 数据查询（玩家、英雄、物品、比赛、实时、职业赛事） | [文档](https://docs.opendota.com/) / [仓库](https://github.com/odota/core) |
| Valve Steam Web API | 备选数据源，当 OpenDota 返回空数据时自动切换 | [文档](https://developer.valvesoftware.com/wiki/Steam_Web_API) |

本插件默认使用 OpenDota API 获取数据，无需申请 API Key。如果需要获取比赛数据（当 OpenDota 返回空时），可以配置 Steam API Key 作为备选数据源。

感谢 OpenDota 项目的开源贡献。

## 开发

```bash
# 安装依赖
pip install -r requirements.txt

# 运行测试
python -m pytest tests/ -v

# 代码检查
ruff check .
```

## License

MIT
