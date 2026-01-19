#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Data Module: Entity Linker
==========================
主动实体链接与清洗模块。
用于发现数据库中潜在的重复实体（如“药老”与“药尘”），并提供合并建议。

功能：
1. 计算实体相似度 (Name, Pinyin, Desc)
2. 生成合并建议报告
3. 执行实体合并操作 (Update References)
"""

import sys
import json
import sqlite3
from pathlib import Path
from typing import List, Dict, Tuple, Optional
from dataclasses import dataclass, asdict
from difflib import SequenceMatcher
try:
    from pypinyin import lazy_pinyin
except ImportError:
    lazy_pinyin = None

from .config import get_config
from .index_manager import IndexManager, EntityMeta

@dataclass
class MergeCandidate:
    primary_id: str
    primary_name: str
    secondary_id: str
    secondary_name: str
    score: float
    reason: str

class EntityLinker:
    def __init__(self, config=None):
        self.config = config or get_config()
        self.index = IndexManager(self.config)

    def _get_similarity(self, s1: str, s2: str) -> float:
        """计算字符串相似度 (0-1)"""
        if not s1 or not s2:
            return 0.0
        return SequenceMatcher(None, s1, s2).ratio()

    def _check_pinyin_match(self, name1: str, name2: str) -> bool:
        """检查拼音是否匹配 (需安装 pypinyin)"""
        if not lazy_pinyin:
            return False
        py1 = "".join(lazy_pinyin(name1))
        py2 = "".join(lazy_pinyin(name2))
        return py1 == py2 or py1 in py2 or py2 in py1

    def find_candidates(self, threshold: float = 0.8) -> List[MergeCandidate]:
        """查找合并候选"""
        entities = []
        # Get all entities from DB
        with self.index._get_conn() as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM entities WHERE is_archived = 0")
            rows = cursor.fetchall()
            entities = [dict(r) for r in rows]

        candidates = []
        seen_pairs = set()

        # O(N^2) comparison - acceptable for small N (< 2000), otherwise need indexing
        for i in range(len(entities)):
            for j in range(i + 1, len(entities)):
                a = entities[i]
                b = entities[j]
                
                # Only compare same type
                if a['type'] != b['type']:
                    continue
                
                # Check ID pair to avoid duplicates
                pair_key = tuple(sorted([a['id'], b['id']]))
                if pair_key in seen_pairs:
                    continue
                seen_pairs.add(pair_key)

                # 1. Exact canonical name match (High risk of duplication)
                if a['canonical_name'] == b['canonical_name']:
                    score = 1.0
                    reason = "Same Name"
                else:
                    # 2. Fuzzy name match
                    score = self._get_similarity(a['canonical_name'], b['canonical_name'])
                    reason = "Name Similarity"
                    
                    # 3. Pinyin match boost
                    if score > 0.5 and self._check_pinyin_match(a['canonical_name'], b['canonical_name']):
                         score = min(1.0, score + 0.2)
                         reason += " + Pinyin"

                if score >= threshold:
                    # Determine primary (Keep the one with more content or appearances)
                    # Heuristic: Lower tiers are secondary; fewer appearances are secondary
                    
                    # Simple rule: Older > Newer? No, Usually the one with proper ID > generated ID
                    # Here we just pick A as primary for prompt, user decides
                    
                    # Heuristic: 'first_appearance' smaller is likely 'older' and more stable
                    is_a_primary = a.get('first_appearance', 9999) <= b.get('first_appearance', 9999)
                    if a.get('tier') == '核心' and b.get('tier') != '核心':
                        is_a_primary = True
                    elif b.get('tier') == '核心' and a.get('tier') != '核心':
                        is_a_primary = False
                        
                    p, s = (a, b) if is_a_primary else (b, a)
                    
                    candidates.append(MergeCandidate(
                        primary_id=p['id'],
                        primary_name=p['canonical_name'],
                        secondary_id=s['id'],
                        secondary_name=s['canonical_name'],
                        score=score,
                        reason=reason
                    ))
        
        candidates.sort(key=lambda x: x.score, reverse=True)
        return candidates

    def merge_entities(self, primary_id: str, secondary_id: str):
        """
        合并实体：
        1. 将 Secondary 的别名移交给 Primary
        2. 将 Secondary 的出场记录 (appearances) 归并到 Primary
        3. 将 Secondary 的状态变化 (state_changes) 归并到 Primary
        4. 将 Secondary 的关系 (relationships) 归并到 Primary
        5. 将 Secondary 标记为已归档 (is_archived=1) 或物理删除
        """
        with self.index._get_conn() as conn:
            cursor = conn.cursor()
            
            try:
                # 1. Update Aliases
                cursor.execute("""
                    UPDATE aliases SET entity_id = ? WHERE entity_id = ?
                """, (primary_id, secondary_id))
                
                # 2. Update Appearances
                # Need to handle duplicate primary+chapter unique constraint
                # If primary already appeared in that chapter, we just merge mentions?
                # SQLite 'ON CONFLICT' might be tricky with UPDATE.
                # Logic: For each appearances of secondary:
                #   If primary has appearance in same chapter: append mentions, update confidence
                #   Else: update entity_id to primary
                
                cursor.execute("SELECT * FROM appearances WHERE entity_id = ?", (secondary_id,))
                rows = cursor.fetchall() # Tuple rows
                
                # Need column mapping
                # id, entity_id, chapter, mentions, confidence
                
                for row in rows:
                    row_id = row[0]
                    chapter = row[2]
                    mentions = row[3]
                    
                    # Check primary
                    cursor.execute("SELECT id, mentions FROM appearances WHERE entity_id = ? AND chapter = ?", (primary_id, chapter))
                    p_row = cursor.fetchone()
                    
                    if p_row:
                        # Merge
                        p_id = p_row[0]
                        p_mentions = p_row[1]
                        # JSON list merge
                        try:
                            m1 = json.loads(mentions) if mentions else []
                            m2 = json.loads(p_mentions) if p_mentions else []
                            merged = list(set(m1 + m2))
                            new_json = json.dumps(merged, ensure_ascii=False)
                            cursor.execute("UPDATE appearances SET mentions = ? WHERE id = ?", (new_json, p_id))
                            # Delete secondary row
                            cursor.execute("DELETE FROM appearances WHERE id = ?", (row_id,))
                        except:
                            pass
                    else:
                        # Move
                        cursor.execute("UPDATE appearances SET entity_id = ? WHERE id = ?", (primary_id, row_id))

                # 3. Update Relationships
                # direction: from
                cursor.execute("UPDATE relationships SET from_entity = ? WHERE from_entity = ?", (primary_id, secondary_id))
                # direction: to
                cursor.execute("UPDATE relationships SET to_entity = ? WHERE to_entity = ?", (primary_id, secondary_id))

                # 4. Update State Changes
                cursor.execute("UPDATE state_changes SET entity_id = ? WHERE entity_id = ?", (primary_id, secondary_id))
                
                # 5. Archive Secondary
                cursor.execute("UPDATE entities SET is_archived = 1 WHERE id = ?", (secondary_id,))
                
                conn.commit()
                return True
            except Exception as e:
                print(f"Merge failed: {e}")
                conn.rollback()
                return False

def main():
    import argparse
    parser = argparse.ArgumentParser()
    subparsers = parser.add_subparsers(dest="command")
    
    # Check
    check_parser = subparsers.add_parser("check")
    check_parser.add_argument("--threshold", type=float, default=0.8)
    
    # Merge
    merge_parser = subparsers.add_parser("merge")
    merge_parser.add_argument("--primary", required=True)
    merge_parser.add_argument("--secondary", required=True)
    
    args = parser.parse_args()
    
    linker = EntityLinker()
    
    if args.command == "check":
        candidates = linker.find_candidates(args.threshold)
        print(json.dumps([asdict(c) for c in candidates], ensure_ascii=False, indent=2))
        
    elif args.command == "merge":
        success = linker.merge_entities(args.primary, args.secondary)
        if success:
            print(f"Merged {args.secondary} into {args.primary}")
        else:
            print("Merge failed")

if __name__ == "__main__":
    main()
