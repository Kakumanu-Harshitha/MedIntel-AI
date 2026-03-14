import os
import re

def get_imports(directory):
    external_pkgs = set()
    std_lib = set(['os', 'sys', 're', 'json', 'datetime', 'time', 'uuid', 'io', 'typing', 'math', 'base64', 'hashlib', 'collections', 'threading', 'logging', 'argparse', 'shutil', 'glob', 'pathlib', 'abc', 'enum', 'traceback', 're', 'smtplib', 'email', 'copy', 'functools', 'inspect', 'itertools'])
    internal_pkgs = set(['app'])
    
    # Improved regex to capture the top-level package name
    import_regex = re.compile(r'^\s*(?:import|from)\s+([a-zA-Z0-9_]+)', re.M)
    
    for root, dirs, files in os.walk(directory):
        for file in files:
            if file.endswith('.py'):
                path = os.path.join(root, file)
                try:
                    with open(path, 'r', encoding='utf-8') as f:
                        lines = f.readlines()
                        for line in lines:
                            match = import_regex.match(line)
                            if match:
                                pkg = match.group(1)
                                if pkg not in std_lib and pkg not in internal_pkgs:
                                    external_pkgs.add(pkg)
                except Exception as e:
                    print(f"Error reading {path}: {e}")
                            
    return sorted(list(external_pkgs))

if __name__ == "__main__":
    imports = get_imports('app')
    print("Top-level External Packages found:")
    for imp in imports:
        print(imp)
