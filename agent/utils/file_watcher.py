# File watcher/tailer utility for monitoring log file updates
# Follows log files in real-time and bookmarks the read offsets
import time
import os
import json

OFFSET_FILE = os.path.join(os.path.dirname(os.path.dirname(__file__)), ".offsets.json")

def load_offsets():
    if os.path.exists(OFFSET_FILE):
        try:
            with open(OFFSET_FILE, 'r') as f:
                return json.load(f)
        except Exception:
            return {}
    return {}

def save_offset(filepath, offset):
    offsets = load_offsets()
    abs_path = os.path.abspath(filepath)
    offsets[abs_path] = offset
    try:
        with open(OFFSET_FILE, 'w') as f:
            json.dump(offsets, f)
    except Exception as e:
        print(f"[!] Error saving offset: {e}")

def watch_file(filepath, poll_interval=0.5):
    """Yields new lines appended to a file, resuming from bookmarked offset."""
    abs_path = os.path.abspath(filepath)
    
    # Create file if it doesn't exist
    if not os.path.exists(abs_path):
        dir_name = os.path.dirname(abs_path)
        if dir_name and not os.path.exists(dir_name):
            os.makedirs(dir_name, exist_ok=True)
        open(abs_path, 'a').close()
        
    offsets = load_offsets()
    saved_offset = offsets.get(abs_path, 0)
    file_size = os.path.getsize(abs_path)
    
    # If the file was truncated or rotated, reset offset to 0
    if saved_offset > file_size:
        saved_offset = 0
        
    # Open in binary mode ('rb') to bypass text-mode buffering
    with open(abs_path, 'rb') as file:
        if saved_offset > 0:
            file.seek(saved_offset)
        else:
            # Start at the beginning (0) to ingest existing logs on first run
            file.seek(0)
            save_offset(abs_path, 0)
            
        while True:
            current_position = file.tell()
            line = file.readline()
            if not line:
                # Check for rotation or truncation
                try:
                    current_size = os.path.getsize(abs_path)
                    if current_size < current_position:
                        # File was rotated/truncated
                        file.seek(0)
                        save_offset(abs_path, 0)
                        continue
                except OSError:
                    pass
                time.sleep(poll_interval)
                continue
                
            save_offset(abs_path, file.tell())
            try:
                # Decode from bytes and strip trailing line breaks
                decoded_line = line.decode('utf-8', errors='ignore')
                yield decoded_line.rstrip('\r\n')
            except Exception:
                pass