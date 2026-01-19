---
name: webnovel-status
description: 快速查看项目进度、健康度和待办事项。触发条件：用户请求查看状态或 /webnovel-status。
allowed-tools: Read Bash
---

# Project Status Skill

> **目标**：一眼掌握项目全貌，快速发现问题。

## Workflow Checklist

```
项目状态检查：
- [ ] Step 1: 读取 state.json
- [ ] Step 2: 查询 index.db 统计
- [ ] Step 3: 检查健康度指标
- [ ] Step 4: 生成格式化报告
```

---

## Step 1: 读取 state.json

```bash
cat .webnovel/state.json
```

**提取关键信息**：
- `progress.current_chapter` - 当前章节
- `progress.total_words` - 总字数
- `progress.current_volume` - 当前卷
- `protagonist_state` - 主角状态
- `strand_tracker` - Strand 追踪

---

## Step 2: 查询 index.db 统计

```bash
python -c "
import sqlite3
from pathlib import Path

db_path = Path('.webnovel/index.db')
if db_path.exists():
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # 章节统计
    cursor.execute('SELECT COUNT(*) FROM chapters')
    chapter_count = cursor.fetchone()[0]
    
    # 实体统计
    cursor.execute('SELECT type, COUNT(*) FROM entities GROUP BY type')
    entity_stats = cursor.fetchall()
    
    # 待确认消歧
    cursor.execute('SELECT COUNT(*) FROM entities WHERE tier = \"待确认\"')
    pending_count = cursor.fetchone()[0]
    
    # 紧急伏笔
    cursor.execute('SELECT COUNT(*) FROM foreshadowing WHERE status = \"pending\" AND urgency = \"urgent\"')
    urgent_foreshadowing = cursor.fetchone()[0]
    
    conn.close()
    
    print(f'章节数: {chapter_count}')
    print(f'实体统计: {dict(entity_stats)}')
    print(f'待确认消歧: {pending_count}')
    print(f'紧急伏笔: {urgent_foreshadowing}')
else:
    print('index.db 不存在')
"
```

---

## Step 3: 检查健康度指标

### Strand 比例检查

| Strand | 目标比例 | 警告条件 |
|--------|---------|----------|
| Quest (主线) | 55-65% | 连续 5+ 章 |
| Fire (感情线) | 20-30% | >10 章未出现 |
| Constellation (世界观) | 10-20% | >15 章未出现 |

### 爽点密度检查

- 每章 ≥1 个爽点
- 每 5 章 ≥1 个大爽点
- 避免连续 3 章同类型

### 待办事项检查

- 待确认消歧项 > 0 → ⚠️ 需要处理
- 紧急伏笔 > 0 → ⚠️ 需要收回

---

## Step 4: 生成格式化报告

```markdown
# 📊 项目状态报告

> 生成时间: {datetime}

---

## 📈 进度概览

| 指标 | 数值 | 目标 |
|------|------|------|
| 当前章节 | 第 {current_chapter} 章 | {target_chapters} 章 |
| 总字数 | {total_words} 字 | {target_words} 字 |
| 完成度 | {percentage}% | 100% |
| 当前卷 | 第 {current_volume} 卷 | - |

---

## 👤 主角状态

| 属性 | 当前值 |
|------|--------|
| 姓名 | {protagonist.name} |
| 境界 | {protagonist.realm} |
| 位置 | {protagonist.location} |
| 金手指等级 | Lv.{golden_finger.level} |

---

## 🧵 Strand 健康度

| Strand | 占比 | 状态 | 上次出现 |
|--------|------|------|----------|
| Quest (主线) | {quest_ratio}% | {status} | 第 {last_quest} 章 |
| Fire (感情线) | {fire_ratio}% | {status} | 第 {last_fire} 章 |
| Constellation (世界观) | {constellation_ratio}% | {status} | 第 {last_const} 章 |

---

## 📦 实体统计

| 类型 | 数量 |
|------|------|
| 角色 | {count} |
| 地点 | {count} |
| 物品 | {count} |
| 势力 | {count} |
| 招式 | {count} |

---

## ⚠️ 待办事项

### 🔴 紧急
- [ ] 紧急伏笔待收回: {count} 个
  {list_urgent_foreshadowing}

### 🟡 需关注
- [ ] 待确认消歧项: {count} 个
  {list_pending_disambiguation}

### 🟢 建议
- [ ] Strand 比例偏离警告
- [ ] 爽点密度不足章节

---

## 📝 最近活动

| 时间 | 操作 | 详情 |
|------|------|------|
| {datetime} | 写作 | 第 X 章完成 |
| {datetime} | 审查 | 第 X 章评分 85 分 |
| {datetime} | 修改 | 第 X 章修复 2 个问题 |
```

---

## 快速状态（简洁版）

如果用户只需要简洁信息：

```
📊 项目: {title}
━━━━━━━━━━━━━━━━━━━━━━━━
📖 进度: 第 {current} / {target} 章 ({percentage}%)
✍️ 字数: {words} 万字
👤 主角: {name} | {realm}
━━━━━━━━━━━━━━━━━━━━━━━━
⚠️ 待办: {urgent_count} 项紧急 | {pending_count} 项待确认
```

---

## Anti-Patterns（禁止行为）

❌ 输出过于冗长的报告
❌ 遗漏紧急待办事项
❌ 不检查 Strand 健康度
