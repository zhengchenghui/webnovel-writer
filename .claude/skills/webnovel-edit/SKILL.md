---
name: webnovel-edit
description: 基于审查报告定向修改已有章节，支持局部修复和增量索引更新。触发条件：用户请求修改章节或 /webnovel-edit。
allowed-tools: Read Write Edit Bash
---

# Chapter Edit Skill

> **核心原则**：精准修复，最小改动。只修复报告中的问题，不随意发挥。

## Workflow Checklist

Copy and track progress:

```
章节修改进度：
- [ ] Step 1: 加载审查报告
- [ ] Step 2: 加载目标章节
- [ ] Step 3: 加载必要 references
- [ ] Step 4: 定向修复问题
- [ ] Step 5: 润色（去 AI 味）
- [ ] Step 6: Data Agent 增量更新
- [ ] Step 7: Git 提交
```

---

## Step 1: 加载审查报告（必须执行）

```bash
cat "审查报告/第{chapter_id}章_审查报告.md"
```

**解析报告结构**：
```json
{
  "overall_score": 85,
  "issues": [
    {"agent": "ooc-checker", "type": "OOC", "severity": "critical", "location": "第3段", "suggestion": "..."},
    {"agent": "consistency-checker", "type": "POWER_CONFLICT", "severity": "high", "location": "第5段", "suggestion": "..."}
  ],
  "pass": true
}
```

**提取修复清单**：
- [ ] Critical 问题（必须修复）
- [ ] High 问题（优先修复）
- [ ] Medium 问题（建议修复）

---

## Step 2: 加载目标章节

```bash
cat "正文/第{volume_id}卷/第{chapter_id}章.md"
```

**标记问题位置**：
根据审查报告中的 `location` 字段，定位需要修改的段落。

---

## Step 3: 加载必要 References

**根据问题类型加载对应参考**：

| 问题类型 | 需要加载的文件 |
|---------|---------------|
| OOC | `cat "设定集/角色库/{角色名}.md"` |
| POWER_CONFLICT | `cat "设定集/力量体系.md"` + `cat .webnovel/state.json` (protagonist_state) |
| PACING_IMBALANCE | `cat "${CLAUDE_PLUGIN_ROOT}/shared-references/strand-weave-pattern.md"` |
| LOW_COOL_POINTS | `cat "${CLAUDE_PLUGIN_ROOT}/shared-references/cool-points-guide.md"` |

**润色阶段必须加载**：
```bash
cat "${CLAUDE_PLUGIN_ROOT}/skills/webnovel-write/references/polish-guide.md"
```

---

## Step 4: 定向修复问题

### 修复优先级

1. **Critical** → 必须修复，否则章节无法发布
2. **High** → 优先修复
3. **Medium** → 建议修复
4. **Low** → 可选修复

### 修复原则

- **最小改动**：只修改问题段落，不动其他内容
- **保持风格**：修复后的文字风格应与原文一致
- **记录变更**：每个修改点需要记录原因

### 修复示例

**OOC 修复**：
```
问题：林天（隐忍冷静）突然暴怒，缺少触发原因
原文：林天怒吼一声："你找死！"冲向对手
修复：对方的话触及了林天的底线——那是关于他家人的羞辱。
      林天眼中闪过一丝寒芒，"你找死。"声音平静，却让人毛骨悚然。
```

**POWER_CONFLICT 修复**：
```
问题：筑基3层使用金丹期技能"破空斩"
原文：林天使出破空斩，剑芒划破虚空
修复：林天运起全身斗气，使出了筑基期的极限一击——裂地斩
```

---

## Step 5: 润色（去 AI 味）

**加载润色指南**：
```bash
cat "${CLAUDE_PLUGIN_ROOT}/skills/webnovel-write/references/polish-guide.md"
```

**检查清单**：
- [ ] 无"综合/总之/此外"等 AI 高频词
- [ ] 无"首先/其次/最后"结构
- [ ] 情绪使用动作/细节表达，非形容词
- [ ] 对话口语化，非书面语

---

## Step 6: Data Agent 增量更新

**检测修复后的变化**：
- 是否有新增实体？
- 是否有实体属性变更？
- 是否有关系变更？

**如有变化，调用 Data Agent**：

```
输入：修改后的章节内容
任务：增量提取变更，更新 index.db
```

---

## Step 7: Git 提交

```bash
git add "正文/第{volume_id}卷/第{chapter_id}章.md"
git commit -m "修复第{chapter_id}章：{修复内容摘要}"
```

**提交信息示例**：
- `修复第45章：修复林天OOC问题，补充情绪触发原因`
- `修复第12章：修复战力体系漏洞，替换金丹期技能为筑基期技能`

---

## 输出格式

修改完成后，输出以下报告：

```markdown
# 章节修改报告

## 修改摘要
- 修改章节：第 {chapter_id} 章
- 原始评分：{original_score}
- 修复问题数：{count}

## 修复详情

### Critical 问题
| 编号 | 问题类型 | 位置 | 修复内容 |
|------|---------|------|----------|
| 1 | OOC | 第3段 | 补充情绪触发原因 |

### High 问题
| 编号 | 问题类型 | 位置 | 修复内容 |
|------|---------|------|----------|
| 1 | POWER_CONFLICT | 第5段 | 替换技能名称 |

## 未修复问题（如有）
- {问题描述} - 原因：{为什么没修}

## Git 提交
- Commit: `修复第{chapter_id}章：{摘要}`
```

---

## Anti-Patterns（禁止行为）

❌ 重写整章（只应定向修复）
❌ 忽略 Critical 问题
❌ 修复后不更新索引
❌ 修改时引入新的 OOC
❌ 修改时改变情节走向
