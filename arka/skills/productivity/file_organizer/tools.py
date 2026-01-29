from arka.skills.decorators import arka_tool
import os
import shutil
import datetime
import mimetypes

@arka_tool(
    name="organize_directory",
    description="Organize files in a directory into subfolders.",
    parameters={
        "type": "object",
        "properties": {
            "path": {"type": "string", "description": "Target directory"},
            "strategy": {"type": "string", "enum": ["extension", "date"], "description": "Sorting strategy"}
        },
        "required": ["path", "strategy"]
    }
)
def organize_directory(path: str, strategy: str) -> str:
    """Organizes files into subfolders."""
    if not os.path.isdir(path):
        return "Target is not a directory."
        
    log = []
    moved_count = 0
    
    try:
        for item in os.listdir(path):
            item_path = os.path.join(path, item)
            
            # Skip directories and hidden files
            if os.path.isdir(item_path) or item.startswith("."):
                continue
                
            # Determine target subfolder
            target_subfolder = "Misc"
            
            if strategy == "extension":
                # Categorize by mime type or extension
                ext = os.path.splitext(item)[1].lower()
                if ext in ['.jpg', '.png', '.gif', '.jpeg', '.svg']:
                    target_subfolder = "Images"
                elif ext in ['.pdf', '.doc', '.docx', '.txt', '.md', '.xlsx']:
                    target_subfolder = "Documents"
                elif ext in ['.zip', '.tar', '.gz', '.rar']:
                    target_subfolder = "Archives"
                elif ext in ['.mp3', '.wav', '.flac']:
                    target_subfolder = "Audio"
                elif ext in ['.mp4', '.mov', '.avi']:
                    target_subfolder = "Video"
                elif ext in ['.py', '.js', '.html', '.css', '.json']:
                    target_subfolder = "Code"
                else:
                    target_subfolder = f"Other_{ext.strip('.')}"
                    
            elif strategy == "date":
                # Year/Month
                ts = os.path.getmtime(item_path)
                dt = datetime.datetime.fromtimestamp(ts)
                target_subfolder = os.path.join(str(dt.year), f"{dt.month:02d}")
                
            # Create subfolder
            target_dir = os.path.join(path, target_subfolder)
            os.makedirs(target_dir, exist_ok=True)
            
            # Move
            # Handle duplicates by renaming
            dest_path = os.path.join(target_dir, item)
            if os.path.exists(dest_path):
                base, extension = os.path.splitext(item)
                counter = 1
                while os.path.exists(dest_path):
                    dest_path = os.path.join(target_dir, f"{base}_{counter}{extension}")
                    counter += 1
            
            shutil.move(item_path, dest_path)
            moved_count += 1
            
        return f"Organization Complete. Moved {moved_count} files using '{strategy}' strategy."
        
    except Exception as e:
        return f"Error occurred: {e}"
