import os
import re
import subprocess

def run_cmd(cmd):
    print(f"Running: {cmd}")
    subprocess.run(cmd, shell=True, check=True)

print("Starting Release Preparation Script...")

configs = [
    'mcp-server-oauth-proxy/config.yaml',
    'mcp-client-oauth-proxy/config.yaml'
]

print("Stripping DEV labels from config.yaml files...")
for config in configs:
    if os.path.exists(config):
        with open(config, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Strip (DEV) prefix or suffix from names
        content = re.sub(r'^(name:\s*"?)\(DEV\)\s*', r'\1', content, flags=re.MULTILINE)
        content = re.sub(r'^(name:.*?)\s*\(DEV\)', r'\1', content, flags=re.MULTILINE)
        
        # Strip DEV from descriptions
        content = re.sub(r'^(description:\s*"?)\(DEV\)\s*', r'\1', content, flags=re.MULTILINE)
        content = re.sub(r'^(description:.*?)\s*\(DEV\)', r'\1', content, flags=re.MULTILINE)
        
        # Fallback for any other loose (DEV) tags
        content = content.replace(' (DEV)', '')
        content = content.replace('"(DEV) ', '"')
        
        # Clean slugs
        content = content.replace('slug: "mcp_server_oauth_proxy-dev"', 'slug: "mcp_server_oauth_proxy"')
        content = content.replace('slug: "mcp-client-oauth-proxy-dev"', 'slug: "mcp-client-oauth-proxy"')
        content = content.replace('slug: mcp_server_oauth_proxy-dev', 'slug: mcp_server_oauth_proxy')
        content = content.replace('slug: mcp-client-oauth-proxy-dev', 'slug: mcp-client-oauth-proxy')
        content = content.replace('_dev\n', '\n')
        content = content.replace('-dev\n', '\n')
        
        # Strip URL dev suffixes
        content = content.replace('#dev', '')
        
        # Remove experimental stage
        content = re.sub(r'^stage:\s*experimental[\r\n]*', '', content, flags=re.MULTILINE)
        
        # Strip trailing modifiers like -dev.X or -X from the version string
        content = re.sub(r'^(version:\s*".*?)-dev\..*?"', r'\1"', content, flags=re.MULTILINE)
        content = re.sub(r'^(version:\s*".*?)-.*?"', r'\1"', content, flags=re.MULTILINE)
        
        # Transform dev image to release image
        folder_name = config.split('/')[0]
        if f'image: "ghcr.io/connormxy/{folder_name}-dev"' in content:
            content = content.replace(f'image: "ghcr.io/connormxy/{folder_name}-dev"', f'image: "ghcr.io/connormxy/{folder_name}"')
        elif 'image:' not in content:
            content += f'\nimage: "ghcr.io/connormxy/{folder_name}"\n'
        
        with open(config, 'w', encoding='utf-8') as f:
            f.write(content)

repo_json_path = 'repository.json'
if os.path.exists(repo_json_path):
    print("Stripping DEV references from repository.json...")
    with open(repo_json_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    content = re.sub(r'("name":\s*".*?)\s*\(DEV\)', r'\1', content)
    content = content.replace('#dev', '')
    
    with open(repo_json_path, 'w', encoding='utf-8') as f:
        f.write(content)

readme_path = 'README.md'
if os.path.exists(readme_path):
    print("Stripping DEV references from README.md...")
    with open(readme_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    content = content.replace('# Dev Branch\n\n', '')
    content = content.replace('#dev', '')
    
    with open(readme_path, 'w', encoding='utf-8') as f:
        f.write(content)

print("Done! Files ready for main release.")
