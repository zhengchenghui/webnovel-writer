#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
NovelGod CLI
============
Unified entry point for AI Novel Assistant tools.

Commands:
  context <N>       Generate context package for Chapter N
  fix <file>        Auto-format text file
  link check        Check for duplicate entities
  stats             Show project statistics
"""

import sys
import argparse
from pathlib import Path
import asyncio

# Setup Path
current_dir = Path(__file__).parent
sys.path.append(str(current_dir))

from workflow import get_context, process_chapter, auto_fix
from data_modules import index_manager, entity_linker, config

def cmd_context(args):
    """Generate Context"""
    gen = get_context.ContextGenerator(args.chapter)
    asyncio.run(gen.generate_full_xml())

def cmd_process(args):
    """Process Chapter Data"""
    processor = process_chapter.ChapterProcessor(args.json, args.chapter_file)
    asyncio.run(processor.run())

def cmd_fix(args):
    """Auto Fix Formatting"""
    path = Path(args.file)
    if not path.exists():
        print(f"File not found: {path}")
        return
    
    content = path.read_text(encoding='utf-8')
    polisher = auto_fix.TextPolisher()
    new_content = polisher.run(content)
    
    if args.inplace:
        path.write_text(new_content, encoding='utf-8')
        print(f"Fixed: {path}")
    else:
        print(new_content)

def cmd_link(args):
    """Entity Linking"""
    linker = entity_linker.EntityLinker()
    if args.action == "check":
        candidates = linker.find_candidates(args.threshold)
        for c in candidates:
            print(f"{c.primary_name} vs {c.secondary_name} (Score: {c.score:.2f}) -> Suggest Merge")
    elif args.action == "merge":
        linker.merge_entities(args.primary, args.secondary)

def cmd_stats(args):
    """Show Stats"""
    cfg = config.get_config()
    idx = index_manager.IndexManager(cfg)
    stats = idx.get_stats()
    print("Project Statistics:")
    print(f"  Chapters: {stats.get('chapters', 0)}")
    print(f"  Entities: {stats.get('entities', 0)}")
    print(f"  Scenes:   {stats.get('scenes', 0)}")

def main():
    parser = argparse.ArgumentParser(prog="novelgod", description="AI Novel Assistant CLI")
    subparsers = parser.add_subparsers(dest="command", help="Available commands")
    
    # context
    p_ctx = subparsers.add_parser("context", help="Generate context")
    p_ctx.add_argument("chapter", type=int)
    
    # process
    p_proc = subparsers.add_parser("ingest", help="Ingest chapter analysis")
    p_proc.add_argument("--json", required=True)
    p_proc.add_argument("--file", required=True, dest="chapter_file")
    
    # fix
    p_fix = subparsers.add_parser("fix", help="Auto-fix formatting")
    p_fix.add_argument("file")
    p_fix.add_argument("-i", "--inplace", action="store_true")

    # link
    p_link = subparsers.add_parser("link", help="Entity linking")
    p_link.add_argument("action", choices=["check", "merge"])
    p_link.add_argument("--threshold", type=float, default=0.8)
    p_link.add_argument("--primary")
    p_link.add_argument("--secondary")

    # stats
    p_stats = subparsers.add_parser("stats", help="Project statistics")

    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        return

    if args.command == "context":
        cmd_context(args)
    elif args.command == "ingest":
        cmd_process(args)
    elif args.command == "fix":
        cmd_fix(args)
    elif args.command == "link":
        cmd_link(args)
    elif args.command == "stats":
        cmd_stats(args)

if __name__ == "__main__":
    main()
