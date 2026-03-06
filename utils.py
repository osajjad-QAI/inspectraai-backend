import os
import re
import asyncio
from pathlib import Path
from typing import Optional, List
from fastapi import HTTPException
from schemas import DirectoryNode, UploadStatus
from build_rag import build_and_save_vectorstore, load_vectorstore


# ==================== Global State ====================
# Store upload status for each task
upload_status: dict[str, dict] = {}


# ==================== Ignore File Handler ====================

class IgnorePattern:
    """Handles ignore patterns similar to .gitignore"""
    
    def __init__(self, patterns: List[str], root_path: Path):
        self.patterns = []
        self.root_path = root_path
        
        for pattern in patterns:
            pattern = pattern.strip()
            if not pattern or pattern.startswith('#'):
                continue
            
            negated = pattern.startswith('!')
            if negated:
                pattern = pattern[1:]
            
            regex = self._pattern_to_regex(pattern)
            if regex:
                self.patterns.append({
                    'pattern': pattern,
                    'regex': regex,
                    'negated': negated,
                    'is_dir': pattern.endswith('/')
                })
    
    def _pattern_to_regex(self, pattern: str) -> Optional[re.Pattern]:
        """Convert gitignore pattern to regex"""
        pattern = pattern.replace('.', r'\.')
        pattern = pattern.replace('+', r'\+')
        pattern = pattern.replace('(', r'\(')
        pattern = pattern.replace(')', r'\)')
        pattern = pattern.replace('[', r'\[')
        pattern = pattern.replace(']', r'\]')
        pattern = pattern.replace('{', r'\{')
        pattern = pattern.replace('}', r'\}')
        
        pattern = pattern.replace('**/', '.*/')
        pattern = pattern.replace('/**', '/.*')
        pattern = pattern.replace('**', '.*')
        pattern = pattern.replace('*', '[^/]*')
        pattern = pattern.replace('?', '[^/]')
        
        if pattern.startswith('/'):
            pattern = '^' + pattern[1:]
        else:
            pattern = '.*' + pattern
        
        if pattern.endswith('/'):
            pattern = pattern[:-1] + '(/.*)?$'
        else:
            pattern = pattern + '$'
        
        try:
            return re.compile(pattern)
        except:
            return None
    
    def should_ignore(self, file_path: Path, is_dir: bool = False) -> bool:
        """Check if a file/directory should be ignored"""
        try:
            rel_path = file_path.relative_to(self.root_path)
            rel_str = str(rel_path).replace('\\', '/')
        except ValueError:
            return False
        
        for pattern_info in self.patterns:
            regex = pattern_info['regex']
            pattern_is_dir = pattern_info['is_dir']
            
            if pattern_is_dir and not is_dir:
                continue
            
            if regex.match(rel_str) or regex.match('/' + rel_str):
                if pattern_info['negated']:
                    return False
                return True
        
        return False


def load_ignore_patterns(root_path: Path) -> IgnorePattern:
    """Load ignore patterns from .gitignore, .ignore, and other common ignore files"""
    ignore_files = ['.gitignore', '.ignore', '.dockerignore', '.npmignore']
    all_patterns = []
    
    default_patterns = [
        '__pycache__/',
        '*.pyc',
        '*.pyo',
        '*.pyd',
        '.Python',
        '*.so',
        '.venv/',
        'venv/',
        'env/',
        '.env',
        '.git/',
        '.idea/',
        '.vscode/',
        'node_modules/',
        '.DS_Store',
        '*.log',
        'dist/',
        'build/',
        '.pytest_cache/',
        '.mypy_cache/',
        '.coverage',
        'htmlcov/',
    ]
    all_patterns.extend(default_patterns)
    
    for ignore_file in ignore_files:
        ignore_path = root_path / ignore_file
        if ignore_path.exists() and ignore_path.is_file():
            try:
                with open(ignore_path, 'r', encoding='utf-8', errors='ignore') as f:
                    patterns = f.readlines()
                    all_patterns.extend(patterns)
            except Exception as e:
                print(f"Warning: Could not read {ignore_file}: {e}")
    
    current = root_path.parent
    while current != current.parent:
        gitignore = current / '.gitignore'
        if gitignore.exists() and gitignore.is_file():
            try:
                with open(gitignore, 'r', encoding='utf-8', errors='ignore') as f:
                    patterns = f.readlines()
                    for pattern in patterns:
                        pattern = pattern.strip()
                        if pattern and not pattern.startswith('#'):
                            all_patterns.append(pattern)
            except Exception:
                pass
        current = current.parent
    
    return IgnorePattern(all_patterns, root_path)


# ==================== Helper Functions ====================

def build_directory_structure(root_path: str, ignore_patterns: Optional[IgnorePattern] = None) -> DirectoryNode:
    """Build a directory structure from a file system path."""
    root = Path(root_path).resolve()
    
    if not root.exists():
        raise HTTPException(status_code=404, detail=f"Project path not found: {root_path}")
    
    if not root.is_dir():
        raise HTTPException(status_code=400, detail=f"Path is not a directory: {root_path}")
    
    if ignore_patterns is None:
        ignore_patterns = load_ignore_patterns(root)
    
    def create_node(path: Path, relative_to: Path = None) -> Optional[DirectoryNode]:
        if relative_to is None:
            relative_to = root
        
        if ignore_patterns.should_ignore(path, is_dir=path.is_dir()):
            return None
        
        if path.is_file():
            return DirectoryNode(
                name=path.name,
                type="file",
                path=str(path),
                children=None
            )
        else:
            children = []
            try:
                for item in sorted(path.iterdir()):
                    if item.name.startswith('.') and item.name not in ['.gitignore', '.ignore', '.env', '.dockerignore', '.npmignore']:
                        if ignore_patterns.should_ignore(item, is_dir=item.is_dir()):
                            continue
                    
                    child_node = create_node(item, relative_to)
                    if child_node is not None:
                        children.append(child_node)
            except PermissionError:
                pass
            except Exception as e:
                print(f"Warning: Error reading directory {path}: {e}")
            
            return DirectoryNode(
                name=path.name,
                type="folder",
                path=str(path),
                children=children if children else None
            )
    
    return create_node(root) or DirectoryNode(
        name=root.name,
        type="folder",
        path=str(root),
        children=[]
    )


async def process_upload_background(task_id: str, path: str, source_type: str):
    """
    Background task to process the project upload.
    Calls build_and_save_vectorstore() and load_vectorstore() with progress updates.
    """
    try:
        # Update status to processing
        upload_status[task_id] = {
            "status": UploadStatus.processing,
            "message": "Starting vectorstore build...",
            "progress": 10,
            "path": path,
            "source": source_type
        }
        
        # Step 1: Build and save vectorstore
        upload_status[task_id].update({
            "message": "Building vectorstore from project files...",
            "progress": 30
        })
        
        # Run the synchronous function in a thread pool to avoid blocking
        import concurrent.futures
        loop = asyncio.get_event_loop()
        with concurrent.futures.ThreadPoolExecutor() as executor:
            await loop.run_in_executor(executor, build_and_save_vectorstore)
        
        upload_status[task_id].update({
            "message": "Vectorstore built successfully. Loading vectorstore...",
            "progress": 70
        })
        
        # Step 2: Load vectorstore
        with concurrent.futures.ThreadPoolExecutor() as executor:
            vs = await loop.run_in_executor(executor, load_vectorstore)
        
        # Mark as completed
        upload_status[task_id] = {
            "status": UploadStatus.completed,
            "message": "Project source processed and vectorstore loaded successfully",
            "progress": 100,
            "path": path,
            "source": source_type
        }
        
        # Print the received data
        print("=" * 50)
        print("PROJECT SOURCE PROCESSED")
        print("=" * 50)
        print(f"Task ID: {task_id}")
        print(f"Path: {path}")
        print(f"Source: {source_type.split('.')[0] if '.' in source_type else source_type}")
        print("Vectorstore built and loaded successfully")
        print("=" * 50)
        
    except Exception as e:
        upload_status[task_id] = {
            "status": UploadStatus.failed,
            "message": f"Error processing project: {str(e)}",
            "progress": 0,
            "path": path,
            "source": source_type
        }
        print(f"Error processing upload {task_id}: {str(e)}")
