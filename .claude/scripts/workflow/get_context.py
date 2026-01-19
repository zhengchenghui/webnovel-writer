#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Workflow Script: Get Context
============================
为 Context Agent 生成所有必要的上下文信息。
输出格式为 XML，包含项目配置、近期剧情、大纲规划、RAG 检索结果等。

Usage:
    python -m workflow.get_context --chapter <N>
"""

import sys
import os
import argparse
import json
import asyncio
from pathlib import Path
from typing import Dict, List, Any

# Ensure we can import data_modules
# Assuming this script is at .claude/scripts/workflow/get_context.py
# We want to import from .claude/scripts/data_modules
current_dir = Path(__file__).parent
scripts_dir = current_dir.parent
sys.path.append(str(scripts_dir))

from data_modules.config import get_config
from data_modules.index_manager import IndexManager
from data_modules.rag_adapter import RAGAdapter
try:
    from data_modules.state_manager import StateManager
except ImportError:
    # If StateManager is not available, we read state.json directly
    StateManager = None

# Windows output fix
if sys.platform == 'win32':
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

class ContextGenerator:
    def __init__(self, chapter_num: int):
        self.chapter_num = chapter_num
        self.config = get_config()
        self.index = IndexManager(self.config)
        self.rag = RAGAdapter(self.config)
        self.state_file = self.config.state_file
        self.state = self._load_state()

    def _load_state(self) -> Dict:
        if not self.state_file.exists():
            return {}
        with open(self.state_file, 'r', encoding='utf-8') as f:
            return json.load(f)

    def get_project_context(self) -> str:
        """<project_context>: Basic project info & config"""
        proj = self.state.get("project_info", {})
        
        # Format constraints/level system if available
        # Ideally this comes from a markdown file, but for now we summarize
        lines = [
            f"<book_title>{proj.get('title', 'Unknown')}</book_title>",
            f"<genre>{proj.get('genre', 'Unknown')}</genre>",
            f"<target_words>{proj.get('target_words', 2000000)}</target_words>",
            f"<current_chapter>{self.chapter_num}</current_chapter>",
            "<style_guidelines>",
            "  1. 拒绝流水账，注重画面感和沉浸感。",
            "  2. 哪怕是升级文，也要有细腻的情感和人际互动。",
            "  3. 严格遵守'黄金三章'法则，开篇即矛盾。",
            "</style_guidelines>"
        ]
        return "\n".join(lines)

    def get_story_context(self) -> str:
        """<story_context>: Dynamic Window (Immediate + Volume Flow)"""
        # Fetch recent 13 chapters to cover immediate (3) and volume flow (10)
        all_recent = self.index.get_recent_chapters(limit=13, before_chapter=self.chapter_num)
        
        # Split into Immediate (Last 3) and Flow (Previous 10)
        # all_recent is DESC (N-1, N-2...)
        immediate_nodes = all_recent[:3]
        older_nodes = all_recent[3:]
        
        lines = []
        
        # Immediate Context (Detailed)
        lines.append("<immediate_context>")
        if not immediate_nodes:
            lines.append("  <info>No previous chapters found.</info>")
        else:
            for ch in reversed(immediate_nodes): # Chronological
                lines.append(f"  <chapter id=\"{ch['chapter']}\">")
                lines.append(f"    <title>{ch['title']}</title>")
                lines.append(f"    <summary>{ch['summary']}</summary>")
                lines.append(f"  </chapter>")
        lines.append("</immediate_context>")
        
        # Volume Flow (Condensed)
        if older_nodes:
            lines.append("<volume_flow_context>")
            for ch in reversed(older_nodes):
                # Truncate summary for density
                summary = ch['summary'][:100] + "..." if len(ch['summary']) > 100 else ch['summary']
                lines.append(f"  <event chapter=\"{ch['chapter']}\" title=\"{ch['title']}\">{summary}</event>")
            lines.append("</volume_flow_context>")
            
        return "\n".join(lines)

    def get_outline_context(self) -> str:
        """<outline_context>: Identifying current plot point"""
        # Simple implementation: Read from a yaml/md file if exists, 
        # or just prompt the agent to look at the '大纲' folder.
        # For this script, we'll try to find the specific chapter outline in '大纲' folder if it exists as separate files
        # Or parse a monolithic outline.
        
        # Strategy: Look for "第X章" in outline directory files
        # This is complex to implement robustly in one step without a structured OutlineManager.
        # For Phase 1, we will provide a placeholder instructing the Agent to check constraints,
        # OR we try to grep the outline file.
        
        outline_file = self.config.outline_dir / "full_outline.md" # Assuming this name or similar
        if not outline_file.exists():
            # Try finding any md file
            md_files = list(self.config.outline_dir.glob("*.md"))
            if md_files:
                outline_file = md_files[0]
                
        content = ""
        if outline_file and outline_file.exists():
             # Read file and try to find relevant section (naive approach)
             # In a real system, OutlineManager would return the specific node.
             # Here we return a guidance.
             content = f"outline_file: {outline_file.name}\n(Agent should verify chapter goals in outline)"
        else:
             content = "No outline file found."
             
        # Also return plot_threads from state
        threads = self.state.get("plot_threads", {})
        active_arcs = threads.get("active_arcs", [])
        
        lines = [
            "<current_arcs>",
            *[f"  <arc>{arc}</arc>" for arc in active_arcs],
            "</current_arcs>",
            "<outline_source>",
            f"  {content}",
            "</outline_source>"
        ]
        return "\n".join(lines)
        
    def get_previous_text(self) -> str:
        """<previous_text>: Last 800 chars of previous chapter"""
        prev_num = self.chapter_num - 1
        if prev_num < 1:
            return ""
            
        # Try to find the file
        # Check standard path
        pattern = f"第{prev_num:03d}章*.md" # Try 3 digits
        files = list(self.config.chapters_dir.rglob(pattern))
        if not files:
            pattern = f"第{prev_num:04d}章*.md" # Try 4 digits
            files = list(self.config.chapters_dir.rglob(pattern))
            
        if files:
            try:
                text = files[0].read_text(encoding='utf-8')
                return text[-1000:]
            except:
                return "Error reading previous chapter."
        return "Previous chapter file not found."

    async def get_ref_context(self) -> str:
        """<ref_context>: RAG results"""
        # Generate query based on outline or recent summary
        # For simplicity, we query "Chapter N plot"
        query = f"第{self.chapter_num}章 剧情 伏笔"
        
        results = await self.rag.hybrid_search(query, vector_top_k=5, bm25_top_k=3, rerank_top_n=5)
        
        lines = []
        for r in results:
             lines.append(f"<ref source=\"{r.source}\" score=\"{r.score:.2f}\">")
             lines.append(f"  <content>...{r.content}...</content>")
             lines.append(f"</ref>")
             
        if not lines:
            lines.append("<info>No RAG results (System might need API Key).</info>")
            
        return "\n".join(lines)
        
    def get_entity_context(self) -> str:
        """<entity_context>: Protagonist status"""
        # From index.db or state.json
        meta = self.state.get("protagonist_state", {})
        
        lines = []
        lines.append(f"<protagonist>")
        lines.append(f"  <name>{meta.get('name', 'Unknown')}</name>")
        lines.append(f"  <level>{meta.get('level', 'Unknown')}</level>")
        lines.append(f"  <location>{meta.get('location', 'Unknown')}</location>")
        lines.append(f"  <status>{meta.get('status', 'Unknown')}</status>")
        lines.append(f"</protagonist>")
        return "\n".join(lines)

    async def generate_full_xml(self):
        print("<root>")
        
        print("  <project_context>")
        print(self.get_project_context())
        print("  </project_context>")
        
        print("  <story_context>")
        print(self.get_story_context())
        print("  </story_context>")
        
        print("  <previous_text>")
        print(self.get_previous_text())
        print("  </previous_text>")
        
        print("  <outline_context>")
        print(self.get_outline_context())
        print("  </outline_context>")
        
        print("  <entity_context>")
        print(self.get_entity_context())
        print("  </entity_context>")
        
        print("  <ref_context>")
        print(await self.get_ref_context())
        print("  </ref_context>")
        
        print("</root>")

def main():
    parser = argparse.ArgumentParser(description="Get Context Workflow")
    parser.add_argument("--chapter", type=int, required=True, help="Chapter number")
    args = parser.parse_args()
    
    gen = ContextGenerator(args.chapter)
    asyncio.run(gen.generate_full_xml())

if __name__ == "__main__":
    main()
