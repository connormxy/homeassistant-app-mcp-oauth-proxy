import os
import re

configs = [
    'mcp-server-oauth-proxy/config.yaml',
    'mcp-client-oauth-proxy/config.yaml'
]

print("Bumping dev version tags...")

def bump_version(match):
    base_version = match.group(1)
    dev_tag = match.group(2)
    
    if dev_tag:
        # Increment existing dev tag (e.g., "-dev.34" becomes "-dev.35")
        current_num = int(dev_tag.replace("-dev.", "").replace("-", ""))
        new_tag = f"-dev.{current_num + 1}"
    else:
        # No dev tag exists, append "-dev.1"
        new_tag = "-dev.1"
        
    return f'version: "{base_version}{new_tag}"'

for config in configs:
    if os.path.exists(config):
        with open(config, 'r', encoding='utf-8') as f:
            content = f.read()
        
        new_content = re.sub(r'^version:\s*"([0-9\.]+)(-dev\.\d+|-\d+)?"', bump_version, content, flags=re.MULTILINE)
        
        if new_content != content:
            with open(config, 'w', encoding='utf-8') as f:
                f.write(new_content)
            print(f"Bumped version in {config}")
        else:
            print(f"No version bump needed or found in {config}")

print("Done!")
