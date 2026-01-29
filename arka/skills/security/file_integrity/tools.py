from arka.skills.decorators import arka_tool
import os
import random
import string

@arka_tool(
    name="secure_delete_file",
    description="Securely delete a file by overwriting content.",
    parameters={
        "type": "object",
        "properties": {
            "path": {"type": "string", "description": "Target file path"},
            "passes": {"type": "integer", "description": "Number of overwrite passes (default 1)"}
        },
        "required": ["path"]
    }
)
def secure_delete_file(path: str, passes: int = 1) -> str:
    """Securely deletes a file."""
    if not os.path.exists(path):
        return "File not found."
    if not os.path.isfile(path):
        return "Target is not a file."
        
    try:
        length = os.path.getsize(path)
        
        with open(path, "wb") as f:
            for i in range(passes):
                # Random data
                f.seek(0)
                f.write(os.urandom(length))
                f.flush()
                os.fsync(f.fileno())
                
            # Zero out
            f.seek(0)
            f.write(b'\x00' * length)
            f.flush()
            os.fsync(f.fileno())
            
        # Scramble name before unlink (to hide filename in metadata sometimes)
        dir_name = os.path.dirname(path)
        new_name = "".join(random.choices(string.ascii_letters, k=15))
        new_path = os.path.join(dir_name, new_name)
        os.rename(path, new_path)
        
        # Delete
        os.remove(new_path)
        return f"Successfully securely deleted: {path}"
        
    except Exception as e:
        return f"Secure delete failed: {e}"
