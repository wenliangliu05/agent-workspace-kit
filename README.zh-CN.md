# agent-workspace-kit（中文说明）

**Agent 每次新会话都会「失忆」。这套东西给它一个能活过会话的记忆：一个 JSON 索引 + 每个项目一份六段式接管包，任何 agent 一条命令就能接上手。**

无服务、无数据库、无第三方依赖：一个 JSON、一堆 Markdown、一个只用标准库的 Python CLI（约 560 行）。

> English README: [README.md](README.md)

## 问题

新会话，熟悉的对话：

> **你：** 接着上周那个导入脚本做。
> **Agent：** 哪个项目？现在什么状态？之前试过什么？

于是它开始 `ls`、`tree`、`grep`、打开五个文件，把你周二已经定下的决定重新推一遍，偶尔还把你周三修好的 bug 再引入一次。**问题从来不在文件，而在上下文。**

## 思路

| 原则 | 落地 |
| --- | --- |
| **稳定的 id** | 项目永远叫 `demo-api`，改标题不影响任何东西 |
| **要留就立项** | 需要活过会话的东西 → `projects/<id>/` + 一份接管包，不是散落在根目录的文件 |
| **一个入口** | `ws.py find` / `ws.py handoff`，而不是 `ls` + `find` + `cat` 考古 |

## 安装

没有依赖，也不需要编译。

```bash
# 装成一个命令（推荐）
pipx install git+https://github.com/wenliangliu05/agent-workspace-kit

# 或者 venv 里用 pip
python3 -m venv .venv
.venv/bin/pip install git+https://github.com/wenliangliu05/agent-workspace-kit
```

装好后只有一个命令：

```bash
ws init ~/my-workspace     # 建工作区
ws handoff demo-api        # 在工作区里：动它之前我需要知道什么？
ws --version
```

不想装也行 —— clone 本仓库即可，它本身就是一个能跑的工作区。

## 60 秒试用

本仓库**本身就是一个可用工作区**（内含两个示例项目），不用安装任何东西：

```bash
git clone https://github.com/wenliangliu05/agent-workspace-kit
cd agent-workspace-kit
python3 assets/tools/ws.py handoff demo-api
```

输出（节选）：

```
# handoff: demo-api
# Order API (demo)  (active, backend)

== 1. project memory ==
## Goal ...  ## State ...  ## Gotchas ...
== 2. file map (depth 2) ==
  projects/demo-api/src/
== 3. skills (load on demand) ==
  debugging  ->  skills/debugging/SKILL.md
```

## 建自己的工作区

```bash
python3 assets/tools/ws.py init ~/my-workspace --title "我的工作区"
cd ~/my-workspace
python3 assets/tools/ws.py new "发票导入器" --type backend --stack python --tag etl
# 然后填 projects/invoice-importer/project_memory.md
python3 assets/tools/ws.py handoff invoice-importer
```

`init` 会把 CLI 复制进新工作区，同时生成 `AGENTS.md`（告诉 agent 动任何项目前先跑 `handoff`）。

## 六段式接管包

`## Goal` · `## State` · `## Key files` · `## Gotchas` · `## Skills` · `## Next steps`

新接手的 agent 只需要六件事：为什么存在、现在到哪了、去哪看、别重复什么、该加载什么、下一步做什么。**一份包控制在 60 行以内** —— 没人读的包比没有包更糟。

### 为什么文件地图只到两层

ETH Zurich 的研究（[arXiv 2602.11988]）实测：架构总览、仓库结构说明**并不能**减少 agent 找文件的时间，多余上下文反而让它探索更多；真正有用的是**不可推断的信息**（坑、试过但被否决的方案、不能动的文件）。所以预算花在 `## Gotchas`，文件地图只到两层。

## 命令

| 命令 | 作用 |
| --- | --- |
| `ws.py init <dir>` | 建工作区骨架（并把 CLI 复制进去） |
| `ws.py new "<标题>"` | 建项目 + 接管包，写入索引 |
| `ws.py list [--status] [--type]` | 列项目 |
| `ws.py find <关键词>` | 在 id/标题/标签/类型/路径里搜 |
| `ws.py show <id>` | 索引条目 + 包的开头 |
| `ws.py handoff <id>` | 打印接管包 + 文件地图 + 匹配的 skill |
| `ws.py check [--fix]` | 校验索引与磁盘是否一致 |

全局参数：`--root <dir>`（默认向上找 `_index.json`）、`--json`（机器可读）。
退出码：`0` 正常 · `1` 校验问题 · `2` 用法错误 · `3` 找不到 —— 所以 `check` 可以直接放进 CI 或 pre-commit。

## 和 agent 配合

把这段贴进 agent 的指令文件（`AGENTS.md` / `CLAUDE.md` / `.cursorrules`）：

```text
本工作区状态在 _index.json，每个项目一份接管包。
动任何项目前先跑：python3 assets/tools/ws.py handoff <项目id>
收工前更新包里的 ## State 与 ## Next steps，把踩过的坑写进 ## Gotchas。
不要用 ls/tree/find 找项目 —— 问索引。
```

## 设计取舍

| 决定 | 原因 |
| --- | --- |
| JSON 索引，不用 SQLite | 要能在 PR 里 diff、能手改 |
| 只用标准库 | 有 agent 的地方就能跑，裸容器也行 |
| 稳定 slug id | 改标题不该把链接和习惯弄断 |
| 六段固定、硬性上限 | 固定形状才扫得动 |
| 不靠 mtime 判新旧 | `git clone` 之后 mtime 全是检出时间；用包里的 `last touched:` |
| CLI 而不是长提示词 | 工具输出只在用时付一次；提示词每轮都付 |

## FAQ

**支持 Claude Code / Codex / Cursor 吗？** 支持 —— 它只是文件和 CLI，没有集成成本。
**非代码项目能用吗？** 能，这正是价值的一半（研究、写作、运维记录）。
**Windows？** 纯 Python 3.10+，直接用 `python3 assets/tools/ws.py`；`init.sh` 只是方便。
**加 skill？** 建 `skills/<名字>/SKILL.md`（带 front-matter），`handoff` 会把匹配的列出来。

## 许可

[MIT](LICENSE)
