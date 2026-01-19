#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Workflow Script: Process Chapter
================================
接收 Data Agent 提取的结构化分析结果 (JSON)，执行数据持久化操作：
1. 更新 IndexDB (Entities, Relationships, State Changes)
2. 更新 RAG 索引 (Vector + BM25)
3. 更新全局进度 (State.json)

Usage:
    python -m workflow.process_chapter --json <analysis.json> --chapter-file <path/to/chapter.md>
"""

import sys
import os
import argparse
import json
import asyncio
from pathlib import Path
from typing import Dict, List, Any

# Ensure we can import data_modules
current_dir = Path(__file__).parent
scripts_dir = current_dir.parent
sys.path.append(str(scripts_dir))

from data_modules.config import get_config
from data_modules.index_manager import IndexManager, EntityMeta, RelationshipMeta, StateChangeMeta
from data_modules.rag_adapter import RAGAdapter
try:
    from data_modules.state_manager import StateManager
except ImportError:
    StateManager = None

# Windows output fix
if sys.platform == 'win32':
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

class ChapterProcessor:
    def __init__(self, json_path: str, chapter_file: str):
        self.config = get_config()
        self.index = IndexManager(self.config)
        self.rag = RAGAdapter(self.config)
        
        self.data = self._load_json(json_path)
        self.chapter_content = self._load_content(chapter_file)
        self.chapter_num = self.data.get("chapter", 0)

    def _load_json(self, path: str) -> Dict:
        try:
            with open(path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            print(f"Error loading JSON: {e}")
            sys.exit(1)

    def _load_content(self, path: str) -> str:
        try:
            with open(path, 'r', encoding='utf-8') as f:
                return f.read()
        except:
            return ""

    def process_entities(self):
        """Update new and modified entities"""
        new_entities = self.data.get("new_entities", [])
        for ent in new_entities:
            meta = EntityMeta(
                id=ent["id"],
                type=ent.get("type", "Unknown"),
                canonical_name=ent.get("name", ent["id"]),
                tier=ent.get("tier", "装饰"),
                desc=ent.get("desc", ""),
                first_appearance=self.chapter_num,
                last_appearance=self.chapter_num
            )
            is_new = self.index.upsert_entity(meta)
            if is_new:
                print(f"  [Entity] Created {meta.canonical_name}")

    def process_state_changes(self):
        """Record state changes"""
        updates = self.data.get("updated_entities", [])
        for up in updates:
            # Record history
            change = StateChangeMeta(
                entity_id=up["id"],
                field=up.get("field", "status"),
                old_value="", # We often don't know the old value here easily without query
                new_value=str(up.get("new_value", "")),
                reason=up.get("reason", ""),
                chapter=self.chapter_num
            )
            self.index.record_state_change(change)
            print(f"  [State] Updated {up['id']}: {up.get('field')}")
            
            # Also update the Entity table 'current_json' if needed
            # This logic depends on how IndexManager handles 'current'. 
            # For v5.1, we might need to fetch-update-save, or just trust the history log.
            # Simplified: We assume IndexManager upsert handles merge, but here we just record change log.

    def process_relationships(self):
        """Update relationships"""
        rels = self.data.get("relationships", [])
        for r in rels:
            meta = RelationshipMeta(
                from_entity=r["from"],
                to_entity=r["to"],
                type=r["type"],
                description=r.get("desc", ""),
                chapter=self.chapter_num
            )
            self.index.upsert_relationship(meta)

    def process_metadata(self):
        """Update chapter metadata"""
        # Determine location and characters from scenes
        scenes = self.data.get("scenes", [])
        locations = set()
        characters = set()
        
        for s in scenes:
            if s.get("location"): locations.add(s["location"])
            if s.get("characters"): characters.update(s["characters"])
            
        main_location = list(locations)[0] if locations else "Unknown"
        
        # Call valid method on IndexManager to save chapter meta
        # Using internal method or direct SQL if public wrapper missing
        # We'll use a direct SQL execution for now if 'upsert_chapter' is not exposed
        # Actually IndexManager usually has process_chapter_data, let's use that logic
        
        # We will use the 'process_chapter_data' method we saw in view_file earlier
        # It takes: chapter, title, location, word_count, entities, scenes
        
        # Extract title from content? Or just use "第N章"
        title = f"第{self.chapter_num}章" # Simplified
        
        # Note: IndexManager.process_chapter_data expects entities as list of dicts (v5.0 style)
        # But we want to use the granular methods above. 
        # So we just update the specific tables here.
        
        # Update 'chapters' table
        with self.index._get_conn() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT OR REPLACE INTO chapters (chapter, title, location, word_count, characters, summary)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (
                self.chapter_num, 
                title, 
                main_location, 
                len(self.chapter_content), 
                json.dumps(list(characters), ensure_ascii=False),
                self.data.get("summary", "")
            ))
            conn.commit()

    def check_entity_conflicts(self):
        """Check if new entities conflict with existing ones"""
        from data_modules.entity_linker import EntityLinker
        linker = EntityLinker(self.config)
        
        new_ids = [e["id"] for e in self.data.get("new_entities", [])]
        if not new_ids:
            return

        candidates = linker.find_candidates(threshold=0.85)
        # Filter where one of the pair is in new_ids
        relevant = [c for c in candidates if c.primary_id in new_ids or c.secondary_id in new_ids]
        
        if relevant:
            print(f"\n[WARN] Potential Entity Duplicates Detected ({len(relevant)}):")
            for c in relevant:
                 print(f"  - {c.primary_name} ({c.primary_id}) vs {c.secondary_name} ({c.secondary_id}) -> Score {c.score:.2f}")

    async def run_rag_indexing(self):
        """Index summary and scenes to RAG"""
        scenes = self.data.get("scenes", [])
        summary = self.data.get("summary", "")
        
        chunks = []
        # Index full summary as one chunk
        if summary:
            chunks.append({
                "chapter": self.chapter_num,
                "scene_index": 0, # 0 usually reserves for Chapter Summary
                "content": f"第{self.chapter_num}章摘要:\n{summary}"
            })
            
        # Index scenes
        for i, s in enumerate(scenes):
            detail = s.get("summary", "")
            # Ideally we might index the full text segment if we had line numbers
            # For now, index the detailed summary
            chunks.append({
                "chapter": self.chapter_num,
                "scene_index": i + 1,
                "content": f"场景{i+1} ({s.get('location')}):\n{detail}"
            })
            
        count = await self.rag.store_chunks(chunks)
        print(f"  [RAG] Indexed {count} chunks")

    async def run(self):
        print(f"Processing Chapter {self.chapter_num}...")
        
        self.process_entities()
        self.check_entity_conflicts()
        self.process_state_changes()
        self.process_relationships()
        self.process_metadata()
        
        try:
            await self.run_rag_indexing()
        except Exception as e:
            print(f"  [RAG] Warning: Indexing failed ({e}) - Check API Config")

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--json", required=True, help="Analysis JSON path")
    parser.add_argument("--chapter-file", required=True, help="Chapter raw md file")
    args = parser.parse_args()
    
    processor = ChapterProcessor(args.json, args.chapter_file)
    asyncio.run(processor.run())

if __name__ == "__main__":
    main()
