from arka.skills.decorators import arka_tool
import os
import time
import stat
from typing import Dict, List

@arka_tool(
    name="analyze_disk_usage",
    description="Analyze disk usage of a directory.",
    parameters={
        "type": "object",
        "properties": {
            "path": {"type": "string", "description": "Microscope target path"}
        },
        "required": ["path"]
    }
)
def analyze_disk_usage(path: str) -> str:
    """Returns top 20 largest files/folders in the path."""
    if not os.path.exists(path):
        return "Path not found."
        
    items = []
    try:
        total_size = 0
        for entry in os.scandir(path):
            try:
                if entry.is_file():
                    size = entry.stat().st_size
                    items.append((entry.name, size, "File"))
                    total_size += size
                elif entry.is_dir():
                    # Quick recursive size (optional, can be slow - simple for now)
                    size = _get_dir_size(entry.path)
                    items.append((entry.name, size, "Dir"))
                    total_size += size
            except PermissionError:
                continue
                
        # Sort by size desc
        items.sort(key=lambda x: x[1], reverse=True)
        
        output = [f"Disk Usage Analysis for: {path}", f"Total: {_format_size(total_size)}", "-"*30]
        for name, size, context in items[:20]:
            output.append(f"{_format_size(size):<10} [{context}] {name}")
            
        return "\n".join(output)
    except Exception as e:
        return f"Error: {e}"

def _get_dir_size(path):
    total = 0
    try:
        for entry in os.scandir(path):
            if entry.is_file(follow_symlinks=False):
                total += entry.stat().st_size
            elif entry.is_dir(follow_symlinks=False):
                total += _get_dir_size(entry.path)
    except Exception:
        pass
    return total

def _format_size(bytes):
    for unit in ['B', 'KB', 'MB', 'GB']:
        if bytes < 1024:
            return f"{bytes:.2f}{unit}"
        bytes /= 1024
    return f"{bytes:.2f}TB"

@arka_tool(
    name="get_detailed_metadata",
    description="Get detailed file metadata (stat, permissions, times).",
    parameters={
        "type": "object",
        "properties": {
            "path": {"type": "string", "description": "Target file path"}
        },
        "required": ["path"]
    }
)
def get_detailed_metadata(path: str) -> str:
    try:
        s = os.stat(path)
        mode = stat.filemode(s.st_mode)
        
        def fmt_time(ts):
            return time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(ts))
            
        return f"""
File: {path}
Size: {_format_size(s.st_size)}
Permissions: {mode} ({oct(s.st_mode)[-3:]})
Owner ID: {s.st_uid} : {s.st_gid}
Access Time:  {fmt_time(s.st_atime)}
Modify Time:  {fmt_time(s.st_mtime)}
Change Time:  {fmt_time(s.st_ctime)}
Inode: {s.st_ino}
Links: {s.st_nlink}
"""
    except Exception as e:
        return f"Error: {e}"
