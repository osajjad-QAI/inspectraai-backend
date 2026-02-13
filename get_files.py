import os
import shutil
import fnmatch

IGNORE_FILE = ".ignore"


# --------------------------------------------------
# Ignore Rules
# --------------------------------------------------
def load_ignore_rules(base_path):
    rules = {
        "folders": set(),     # folder names
        "files": set(),       # exact filenames
        "patterns": []        # glob patterns (*.zip)
    }

    ignore_path = os.path.join(base_path, IGNORE_FILE)

    if not os.path.exists(ignore_path):
        return rules

    with open(ignore_path, "r") as f:
        for line in f:
            rule = line.strip()

            if not rule or rule.startswith("#"):
                continue

            if rule.endswith("/"):
                rules["folders"].add(rule.rstrip("/"))
            elif "*" in rule or "?" in rule:
                rules["patterns"].append(rule)
            else:
                rules["files"].add(rule)

    return rules


def should_ignore_dir(dir_name, rules):
    return dir_name in rules["folders"]


def should_ignore_file(filename, rules):
    if filename in rules["files"]:
        return True

    for pattern in rules["patterns"]:
        if fnmatch.fnmatch(filename, pattern):
            return True

    return False


# --------------------------------------------------
# Inspectra Structure
# --------------------------------------------------
def setup_inspectra_structure(base_path):
    inspectra_path = os.path.join(base_path, ".inspectra")
    code_path = os.path.join(inspectra_path, "code")
    other_path = os.path.join(inspectra_path, "other")

    os.makedirs(code_path, exist_ok=True)
    os.makedirs(other_path, exist_ok=True)

    return code_path, other_path


# --------------------------------------------------
# Safe Copy
# --------------------------------------------------
def safe_copy(src, dst):
    base, ext = os.path.splitext(dst)
    counter = 1
    final_dst = dst

    while os.path.exists(final_dst):
        final_dst = f"{base}_{counter}{ext}"
        counter += 1

    shutil.copy2(src, final_dst)


# --------------------------------------------------
# Main Processing
# --------------------------------------------------
def process_files(root_path, rules, code_dir, other_dir):
    py_count = 0
    other_count = 0

    for dirpath, dirnames, filenames in os.walk(root_path):
        # Skip .inspectra completely
        if ".inspectra" in dirpath:
            continue

        # Remove ignored folders (IMPORTANT)
        dirnames[:] = [
            d for d in dirnames
            if not should_ignore_dir(d, rules)
        ]

        folder_name = os.path.basename(dirpath) or "root"

        for filename in filenames:
            if should_ignore_file(filename, rules):
                continue

            src_path = os.path.join(dirpath, filename)
            _, ext = os.path.splitext(filename)

            new_name = f"{folder_name}_{filename}"

            if ext.lower() == ".py":
                dest = os.path.join(code_dir, new_name)
                safe_copy(src_path, dest)
                py_count += 1
            else:
                dest = os.path.join(other_dir, new_name)
                safe_copy(src_path, dest)
                other_count += 1

    return py_count, other_count


# --------------------------------------------------
# Entry Point (BAT SAFE)
# --------------------------------------------------
def get_files():
    root_path = os.getcwd()
    print(f"[Inspectra] Root directory: {root_path}")

    ignore_rules = load_ignore_rules(root_path)

    if ignore_rules["folders"] or ignore_rules["files"] or ignore_rules["patterns"]:
        print("[Inspectra] Ignore rules loaded")
    else:
        print("[Inspectra] No ignore rules found")

    code_dir, other_dir = setup_inspectra_structure(root_path)

    py_count, other_count = process_files(
        root_path,
        ignore_rules,
        code_dir,
        other_dir
    )

    print(f"[Inspectra] Python files copied : {py_count}")
    print(f"[Inspectra] Other files copied  : {other_count}")
    print("[Inspectra] Completed successfully")