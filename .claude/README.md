# Webnovel Writer - .claude 目录说明

> 版本: v1.1.0 (Skill System Optimization)
> 本文档说明 `.claude` 目录下各子目录的用途和关系。

---

## 📁 目录结构

```
.claude/
├── agents/           # Agent 定义文件
├── genres/           # 详细题材参考库
├── references/       # 全局参考文档
├── scripts/          # Python 脚本
├── shared-references/# 公共引用文件
├── skills/           # Skill 定义
└── templates/        # 快速入门模板
```

---

## 🎯 目录用途详解

### `agents/` - Agent 定义

包含 7 个专用 Agent 的提示词定义：
- `context-agent.md` - 上下文收集
- `data-agent.md` - 数据提取
- `ooc-checker.md` - 人物 OOC 检查
- 等等...

**使用时机**：在 `/webnovel-write` 和 `/webnovel-review` 流程中被调用。

---

### `genres/` vs `templates/genres/` - 核心区别

| 目录 | 用途 | 文件数量 | 使用场景 |
|------|------|----------|----------|
| `genres/` | **详细参考库** | 每题材 5-7 个文件 | 深入创作时查阅 |
| `templates/genres/` | **快速入门模板** | 每题材 1 个文件 | 项目初始化时加载 |

#### `genres/` - 详细题材参考库

为每种题材提供**深度参考**，适合在创作过程中按需查阅：

```
genres/
├── xuanhuan/           # 玄幻/修仙
│   ├── cultivation-levels.md   # 境界体系
│   ├── power-systems.md        # 力量系统
│   ├── xuanhuan-cool-points.md # 题材爽点
│   └── xuanhuan-plot-patterns.md # 常见套路
├── dog-blood-romance/  # 狗血言情
├── period-drama/       # 古言/宫斗
├── realistic/          # 现实题材
├── rules-mystery/      # 规则怪谈
└── zhihu-short/        # 知乎短篇
```

#### `templates/genres/` - 快速入门模板

每种题材提供**单文件模板**，在 `/webnovel-init` 时自动加载：

```
templates/genres/
├── 修仙.md
├── 系统流.md
├── 都市异能.md
├── 狗血言情.md
├── 古言.md
├── 现实题材.md
├── 规则怪谈.md
└── 知乎短篇.md
```

**内容**：包含该题材的核心套路、常见金手指、开篇钩子模板等。

---

### `shared-references/` - 公共引用文件

被多个 Skill 共同引用的文件，避免重复维护：

- `naming-guide.md` - 人物命名指南
- `cool-points-guide.md` - 爽点设计指南
- `strand-weave-pattern.md` - Strand 节奏规范
- `core-constraints.md` - 三大定律核心约束
- `system-data-flow.md` - 数据流说明

---

### `skills/` - Skill 定义

每个 Skill 对应一个用户命令：

| Skill | 命令 | 用途 |
|-------|------|------|
| `webnovel-init` | `/webnovel-init` | 初始化项目 |
| `webnovel-plan` | `/webnovel-plan` | 大纲规划 |
| `webnovel-write` | `/webnovel-write` | 章节写作 |
| `webnovel-review` | `/webnovel-review` | 质量审查 |
| `webnovel-edit` | `/webnovel-edit` | 章节修改 |
| `webnovel-status` | `/webnovel-status` | 状态查看 |
| `webnovel-query` | `/webnovel-query` | 信息查询 |
| `webnovel-resume` | `/webnovel-resume` | 恢复中断 |

---

### `scripts/` - Python 脚本

核心数据处理脚本：

- `init_project.py` - 项目初始化
- `update_state.py` - 状态更新
- `extract_entities.py` - 实体提取
- `data_modules/` - 数据处理模块（RAG、索引等）

---

## 💡 使用建议

1. **初始化项目**时：只需加载 `templates/genres/` 的单文件模板
2. **深入创作**时：按需查阅 `genres/` 下的详细参考
3. **查找公共规范**：优先在 `shared-references/` 中查找
