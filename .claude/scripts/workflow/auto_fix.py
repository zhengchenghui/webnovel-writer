#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Workflow Script: Auto Fix
=========================
自动修复章节格式问题工具。
主要用于标准化标点符号、去除多余空格、修正排版。

Usage:
    python -m workflow.auto_fix --file <path/to/chapter.md> [--inplace]
"""

import sys
import re
import argparse
from pathlib import Path

class TextPolisher:
    def __init__(self):
        pass

    def fix_ellipsis(self, text: str) -> str:
        """... -> ……"""
        # Replace 3+ dots with ……
        # But be careful of code blocks (unlikely in novel)
        return re.sub(r'\.{3,}', '……', text)

    def fix_punctuation(self, text: str) -> str:
        """English punct -> Chinese punct (Context aware)"""
        # Comma: replace , with ， if preceded by Chinese
        text = re.sub(r'(?<=[\u4e00-\u9fa5]),', '，', text)
        # Question: ? -> ？
        text = re.sub(r'(?<=[\u4e00-\u9fa5])\?', '？', text)
        # Exclamation: ! -> ！
        text = re.sub(r'(?<=[\u4e00-\u9fa5])!', '！', text)
        # Colon: : -> ：
        text = re.sub(r'(?<=[\u4e00-\u9fa5]):', '：', text)
        
        # Semicolon
        text = re.sub(r'(?<=[\u4e00-\u9fa5]);', '；', text)
        
        return text

    def fix_quotes(self, text: str) -> str:
        """Straight quotes to Curly quotes"""
        # This is complex to do perfectly with regex.
        # We process paragraph by paragraph.
        lines = text.split('\n')
        new_lines = []
        for line in lines:
            # Count quotes
            if '"' in line:
                # Naive replacement: Odd = Open, Even = Close
                # This works if paragraphs are self-contained
                chars = list(line)
                quote_count = 0
                for i, char in enumerate(chars):
                    if char == '"':
                        quote_count += 1
                        if quote_count % 2 == 1:
                            chars[i] = '“'
                        else:
                            chars[i] = '”'
                line = "".join(chars)
            new_lines.append(line)
        return "\n".join(new_lines)
    
    def normalize_layout(self, text: str) -> str:
        """Remove full-width spaces at start, strip lines"""
        lines = text.split('\n')
        cleaned = []
        for line in lines:
            s = line.strip()
            # Remove Markdown bold markers/headers? No, keep them.
            if s:
                cleaned.append(s)
            else:
                cleaned.append("") # Keep empty lines?
        
        # Ensure max 1 empty line between paragraphs
        result = []
        last_empty = False
        for line in cleaned:
            if not line:
                if not last_empty:
                    result.append(line)
                    last_empty = True
            else:
                result.append(line)
                last_empty = False
                
        return "\n".join(result)

    def run(self, text: str) -> str:
        text = self.fix_ellipsis(text)
        text = self.fix_punctuation(text)
        text = self.fix_quotes(text)
        text = self.normalize_layout(text)
        return text

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--file", required=True, help="File path")
    parser.add_argument("--inplace", action="store_true", help="Overwrite file")
    args = parser.parse_args()
    
    path = Path(args.file)
    if not path.exists():
        print(f"File not found: {path}")
        sys.exit(1)
        
    content = path.read_text(encoding='utf-8')
    polisher = TextPolisher()
    new_content = polisher.run(content)
    
    if args.inplace:
        path.write_text(new_content, encoding='utf-8')
        print(f"Fixed: {path}")
    else:
        print(new_content)

if __name__ == "__main__":
    main()
