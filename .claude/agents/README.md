# Webnovel Writer Agents

> 本目录包含 7 个专用 Agent，用于章节写作和审查流程。

---

## 📦 Agent 列表

| Agent | 职责 | 调用阶段 |
|-------|------|----------|
| [context-agent](context-agent.md) | 上下文收集 | `/webnovel-write` Step 1 |
| [data-agent](data-agent.md) | 数据提取与索引 | `/webnovel-write` Step 5 |
| [ooc-checker](ooc-checker.md) | 人物 OOC 检查 | `/webnovel-review` Step 2 |
| [consistency-checker](consistency-checker.md) | 设定一致性检查 | `/webnovel-review` Step 2 |
| [continuity-checker](continuity-checker.md) | 剧情连贯性检查 | `/webnovel-review` Step 2 |
| [high-point-checker](high-point-checker.md) | 爽点密度检查 | `/webnovel-review` Step 2 |
| [pacing-checker](pacing-checker.md) | 节奏 Strand 检查 | `/webnovel-review` Step 2 |

---

## 🔄 调用规范

### 调用方式

Agents 不是独立可执行的脚本，而是**提示词模板**。当需要执行 Agent 任务时：

1. **加载 Agent 定义**：
   ```bash
   cat "${CLAUDE_PLUGIN_ROOT}/agents/{agent-name}.md"
   ```

2. **准备输入数据**：按照 Agent 文档中的 `Input` 格式准备数据

3. **执行 Agent 逻辑**：AI 根据 Agent 定义执行相应检查/处理

4. **获取输出**：按照 Agent 文档中的 `Output` 格式生成结果

### 并行 vs 串行调用

| 场景 | 调用方式 | 说明 |
|------|---------|------|
| `/webnovel-review` 审查 | **并行** | 5 个 checker 同时执行 |
| `/webnovel-write` 上下文收集 | **串行** | context-agent 先执行 |
| `/webnovel-write` 数据提取 | **串行** | data-agent 在写作完成后执行 |

---

## 📋 Agent 详细说明

### Context Agent (上下文收集)

**职责**：为章节写作收集必要的上下文信息

**输入**：
- 目标章节 ID
- 大纲文件路径

**输出**：
```json
{
  "protagonist_state": {...},
  "recent_chapters_summary": "...",
  "relevant_entities": [...],
  "active_foreshadowing": [...],
  "strand_tracker": {...}
}
```

**调用位置**：`/webnovel-write` Step 1

---

### Data Agent (数据提取)

**职责**：从完成的章节中提取实体、关系、状态变更，更新 index.db

**输入**：
- 章节内容（纯文本）
- 章节 ID

**输出**：
```json
{
  "new_entities": [...],
  "updated_entities": [...],
  "new_relationships": [...],
  "state_changes": [...],
  "foreshadowing": [...]
}
```

**调用位置**：`/webnovel-write` Step 5, `/webnovel-edit` Step 6

---

### OOC Checker (人物失真检查)

**职责**：检测角色行为是否符合人设

**输入**：
- 目标章节范围
- 角色设定文件

**输出**：
```json
{
  "violations": [
    {"character": "林天", "type": "OOC", "severity": "moderate", "location": "第3段", "suggestion": "..."}
  ],
  "verdict": "PASS/WARNING/FAIL"
}
```

**调用位置**：`/webnovel-review` Step 2（并行）

---

### Consistency Checker (设定一致性检查)

**职责**：检测战力体系、时间线、地点等设定是否一致

**输入**：
- 目标章节范围
- state.json
- 力量体系设定

**输出**：
```json
{
  "violations": [
    {"type": "POWER_CONFLICT", "severity": "critical", "location": "第5段", "suggestion": "..."}
  ],
  "verdict": "PASS/FAIL"
}
```

**调用位置**：`/webnovel-review` Step 2（并行）

---

### Continuity Checker (连贯性检查)

**职责**：检测场景转换、时间线跳跃是否平滑

**输入**：
- 目标章节范围
- 前序章节摘要

**输出**：
```json
{
  "issues": [
    {"type": "SCENE_JUMP", "severity": "medium", "location": "第2-3段之间", "suggestion": "..."}
  ],
  "verdict": "PASS/WARNING"
}
```

**调用位置**：`/webnovel-review` Step 2（并行）

---

### High-Point Checker (爽点密度检查)

**职责**：检测章节爽点数量和质量

**输入**：
- 目标章节范围

**输出**：
```json
{
  "cool_points": [
    {"chapter": 45, "type": "打脸型", "quality": "A", "description": "..."}
  ],
  "density": {"current": 1.2, "target": 1.0},
  "type_distribution": {...},
  "verdict": "PASS/WARNING"
}
```

**调用位置**：`/webnovel-review` Step 2（并行）

---

### Pacing Checker (节奏 Strand 检查)

**职责**：检测 Quest/Fire/Constellation 比例是否健康

**输入**：
- 目标章节范围
- strand_tracker

**输出**：
```json
{
  "strand_analysis": {
    "quest_ratio": 0.6,
    "fire_ratio": 0.25,
    "constellation_ratio": 0.15
  },
  "warnings": ["Quest 连续 6 章超过限制"],
  "verdict": "WARNING"
}
```

**调用位置**：`/webnovel-review` Step 2（并行）

---

## 📊 审查报告合并

当 5 个 checker 并行执行完成后，需要合并生成统一的审查报告：

```json
{
  "chapter_range": "45-46",
  "overall_score": 85,
  "issues": [
    // 来自各 checker 的问题合并
  ],
  "pacing_analysis": {
    // 来自 pacing-checker
  },
  "cool_point_analysis": {
    // 来自 high-point-checker
  },
  "pass": true,
  "priority_fixes": [
    // severity = critical 的问题
  ]
}
```

---

## ⚠️ 注意事项

1. **Agent 不是独立程序**：它们是 AI 的"角色切换"提示词
2. **必须加载才能执行**：每次使用前都要 `cat` 对应的 Agent 文件
3. **输出格式必须标准化**：便于 `/webnovel-edit` 解析和修复
4. **并行执行提升效率**：5 个 checker 应同时执行
