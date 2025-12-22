import os

env_path = ".env"

def fix_env():
    if not os.path.exists(env_path):
        print(f"{env_path} not found.")
        return

    # Read binary to detect encoding issues or mixed content
    with open(env_path, "rb") as f:
        raw_content = f.read()

    text = ""
    try:
        # Try UTF-8 first
        text = raw_content.decode("utf-8")
    except UnicodeDecodeError:
        try:
            # Try UTF-16 (common PowerShell output)
            text = raw_content.decode("utf-16")
        except UnicodeDecodeError:
            print("Could not decode .env file. It might be binary or mixed.")
            return

    lines = [line.strip() for line in text.splitlines() if line.strip()]
    
    # Filter out potentially corrupted lines from previous appends (e.g. joined lines)
    # and split them if possible, or just clean up.
    # For now, let's just map existing keys.
    
    clean_lines = []
    existing_keys = set()
    
    for line in lines:
        if "=" in line:
            if line.startswith("#"):
                clean_lines.append(line)
                continue
                
            key = line.split("=", 1)[0].strip()
            # If we appended to a line without newline, it might look like OLD_VALNEW_KEY=...
            # This is hard to recover automatically without heuristics. 
            # We will assume simple structure for now.
            existing_keys.add(key)
            clean_lines.append(line)
    
    # Add missing keys
    updates = []
    if "BACKEND_PUBLIC_URL" not in existing_keys:
        updates.append("BACKEND_PUBLIC_URL=http://localhost:8000")
    
    if "FRONTEND_BASE_URL" not in existing_keys:
        updates.append("FRONTEND_BASE_URL=http://localhost:3000")
        
    if updates:
        print("Adding missing keys:", updates)
        clean_lines.extend(updates)
    else:
        print("Required keys already appear to be present.")

    # Write back as clean UTF-8
    with open(env_path, "w", encoding="utf-8") as f:
        f.write("\n".join(clean_lines) + "\n")
    
    print("Successfully normalized .env to UTF-8.")

if __name__ == "__main__":
    fix_env()
