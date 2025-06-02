import tkinter as tk
from tkinter import filedialog, messagebox, scrolledtext, ttk
import subprocess
import logging
import datetime
from pathlib import Path
from typing import Dict, List, Tuple, Optional, Any
import re
import os
import json
import threading

# 配置日志
logging.basicConfig(level=logging.INFO, 
                   format='%(asctime)s - %(levelname)s - %(message)s',
                   handlers=[
                       logging.FileHandler('code_review.log', encoding='utf-8'),
                       logging.StreamHandler()
                   ])

class LanguageDetector:
    """多语言检测器"""
    
    @staticmethod
    def detect_by_extension(file_path: str) -> str:
        """根据文件扩展名识别语言"""
        ext_map = {
            '.java': 'Java',
            '.py': 'Python',
            '.js': 'JavaScript', 
            '.ts': 'TypeScript',
            '.go': 'Go',
            '.cpp': 'C++', 
            '.c': 'C',
            '.h': 'C/C++头文件',
            '.hpp': 'C++头文件',
            '.html': 'HTML',
            '.css': 'CSS',
            '.vue': 'Vue',
            '.wxml': '微信小程序',
            '.wxss': '微信小程序样式',
            '.wxs': '微信小程序脚本',
            '.json': 'JSON',
            '.xml': 'XML',
            '.sql': 'SQL',
            '.md': 'Markdown',
            '.php': 'PHP',
            '.rb': 'Ruby',
            '.kt': 'Kotlin',
            '.swift': 'Swift'
        }
        
        ext = os.path.splitext(file_path)[1].lower()
        return ext_map.get(ext, "未知")

    @staticmethod
    def detect_by_content(content: str) -> str:
        """根据文件内容识别语言"""
        # 提取前200个字符用于分析
        content_sample = content[:200].lower()
        
        # Java特征
        if re.search(r'^\s*package\s+[\w.]+\s*;', content, re.MULTILINE) and 'class' in content:
            return 'Java'
            
        # Python特征
        if re.search(r'^\s*def\s+\w+\s*\(', content, re.MULTILINE) or re.search(r'^\s*import\s+\w+', content, re.MULTILINE):
            return 'Python'
            
        # JavaScript/TypeScript特征
        if 'function' in content_sample or 'const' in content_sample or 'let' in content_sample:
            # TypeScript特有特征
            if re.search(r':\s*\w+', content_sample) and 'interface' in content:
                return 'TypeScript'
            return 'JavaScript'
            
        # Go特征
        if re.search(r'^\s*package\s+\w+', content, re.MULTILINE) and 'func' in content:
            return 'Go'
            
        # C/C++特征
        if '#include' in content_sample:
            # C++特有特征
            if 'namespace' in content or 'class' in content or 'template' in content:
                return 'C++'
            return 'C'
            
        # Vue特征
        if '<template>' in content and '<script>' in content:
            return 'Vue'
            
        # 微信小程序特征
        if '<view' in content and 'wx:' in content:
            return '微信小程序'
            
        return "未知"

class EnhancedPathResolver:
    """多语言文件路径解析器"""

    def __init__(self, project_root: str):
        self.project_root = Path(project_root)
        # 支持的文件类型映射
        self.file_type_map = {
            '.java': 'Java',
            '.py': 'Python',
            '.js': 'JavaScript', 
            '.ts': 'TypeScript',
            '.go': 'Go',
            '.cpp': 'C++', 
            '.c': 'C',
            '.h': 'C/C++',
            '.hpp': 'C++',
            '.html': 'HTML',
            '.css': 'CSS',
            '.vue': 'Vue',
            '.wxml': '微信小程序',
            '.wxss': '微信小程序',
            '.wxs': '微信小程序',
            '.json': 'JSON',
            '.xml': 'XML',
            '.md': 'Markdown',
            '.php': 'PHP',
            '.rb': 'Ruby',
            '.kt': 'Kotlin',
            '.swift': 'Swift'
        }
        
        # 添加路径识别模式
        self.path_patterns = {
            'windows_abs': r'^[A-Za-z]:\\[^\\].*$',  # Windows绝对路径
            'unix_abs': r'^/[^/].*$',                # Unix绝对路径
            'relative': r'^[^/\\].*$',               # 相对路径
            'module': r'^[a-zA-Z_][a-zA-Z0-9_]*(\.[a-zA-Z_][a-zA-Z0-9_]*)*$'  # 模块路径
        }
        
        # 添加常见项目结构
        self.common_structures = {
            'java': ['src/main/java', 'src/test/java', 'src/main/resources'],
            'python': ['src', 'app', 'modules', 'tests'],
            'go': ['src', 'pkg', 'cmd', 'internal'],
            'js': ['src', 'public', 'assets', 'components'],
            'cpp': ['src', 'include', 'lib', 'test']
        }

    def resolve(self, original_path: str, content: str) -> Tuple[str, List[str]]:
        """解析文件路径并返回警告信息"""
        warnings = []
        path = Path(original_path)

        # 1. 检查是否是绝对路径
        if os.path.isabs(original_path):
            # 检查绝对路径中是否有重复段
            duplicates = self._find_duplicate_path_segments(original_path)
            if duplicates:
                clean_path = self._remove_duplicate_segments(original_path, duplicates)
                warnings.append(f"路径重复段修正: {original_path} → {clean_path}")
                
                # 如果修正后路径存在，直接返回
                if Path(clean_path).exists():
                    return clean_path, warnings
                    
                # 否则继续处理
                path = Path(clean_path)
            elif Path(original_path).exists():
                return original_path, warnings
            else:
                # 绝对路径不存在，尝试从内容推断路径
                guessed_path = self._guess_path_from_content(path, content)
                if guessed_path:
                    warnings.append(f"路径自动修正: {original_path} → {guessed_path}")
                    return str(guessed_path), warnings
                return original_path, warnings

        # 2. 检查路径是否包含常见的冗余模式
        path_str = str(path)
        redundant_patterns = [
            ("src/main/java/src/main/java", "src/main/java"),
            ("src/main/java/com/main/src/main/java/com/main", "src/main/java/com/main"),
            ("com/main/src/main", "src/main"),
            ("src/main/java/com/main/model/src/main/java/com/main/model", "src/main/java/com/main/model")
        ]
        
        for pattern, replacement in redundant_patterns:
            if pattern in path_str:
                fixed_path = path_str.replace(pattern, replacement)
                fixed_path_obj = Path(fixed_path)
                warnings.append(f"路径冗余修正: {path_str} → {fixed_path}")
                path = fixed_path_obj
                break

        # 3. 检查相对路径是否存在
        full_path = self.project_root / path
        
        # 4. 检查完整路径是否有重复段
        full_path_str = str(full_path).replace('\\', '/')
        duplicates = self._find_duplicate_path_segments(full_path_str)
        if duplicates:
            clean_full_path = self._remove_duplicate_segments(full_path_str, duplicates)
            warnings.append(f"路径重复段修正: {full_path} → {clean_full_path}")
            
            # 获取相对于项目根目录的路径
            if clean_full_path.startswith(str(self.project_root)):
                rel_clean_path = os.path.relpath(clean_full_path, str(self.project_root))
                return rel_clean_path, warnings
            else:
                # 如果不在项目根目录下，返回清理后的完整路径
                return clean_full_path, warnings
                
        if full_path.exists():
            return str(path), warnings
            
        # 5. 基于内容尝试推断路径
        guessed_path = self._guess_path_from_content(path, content)
        if guessed_path:
            # 检查推断路径是否包含重复部分
            guessed_str = str(guessed_path).replace('\\', '/')
            duplicates = self._find_duplicate_path_segments(guessed_str)
            if duplicates:
                clean_guessed = self._remove_duplicate_segments(guessed_str, duplicates)
                warnings.append(f"路径自动修正(修复重复段): {original_path} → {clean_guessed}")
                return clean_guessed, warnings
                
            # 检查推断路径是否包含冗余模式
            for pattern, replacement in redundant_patterns:
                if pattern in guessed_str:
                    fixed_guessed = guessed_str.replace(pattern, replacement)
                    warnings.append(f"路径自动修正(修复冗余): {original_path} → {fixed_guessed}")
                    return fixed_guessed, warnings
                    
            warnings.append(f"路径自动修正: {original_path} → {guessed_path}")
            return str(guessed_path), warnings

        # 6. 尝试在常见项目结构中查找
        common_path = self._find_in_common_structures(path)
        if common_path:
            warnings.append(f"在常见项目结构中找到路径: {common_path}")
            return str(common_path), warnings

        return str(path), warnings

    def _find_in_common_structures(self, path: Path) -> Optional[Path]:
        """在常见项目结构中查找文件"""
        ext = path.suffix.lower()
        lang = self.file_type_map.get(ext)
        
        if lang and lang.lower() in self.common_structures:
            structures = self.common_structures[lang.lower()]
            for structure in structures:
                potential_path = self.project_root / structure / path
                if potential_path.exists():
                    return potential_path
                    
        # 如果特定语言的结构没找到，尝试所有常见结构
        for structures in self.common_structures.values():
            for structure in structures:
                potential_path = self.project_root / structure / path
                if potential_path.exists():
                    return potential_path
                    
        return None

    def _normalize_path(self, path: str) -> str:
        """标准化路径格式"""
        # 统一使用正斜杠
        path = path.replace('\\', '/')
        
        # 移除重复的斜杠
        path = re.sub(r'/+', '/', path)
        
        # 移除末尾的斜杠
        path = path.rstrip('/')
        
        return path

    def _is_valid_path(self, path: str) -> bool:
        """检查路径是否有效"""
        # 检查基本语法
        if not path:
            return False
            
        # 检查Windows路径格式
        if re.match(self.path_patterns['windows_abs'], path):
            return True
            
        # 检查Unix路径格式
        if re.match(self.path_patterns['unix_abs'], path):
            return True
            
        # 检查相对路径格式
        if re.match(self.path_patterns['relative'], path):
            return True
            
        # 检查模块路径格式
        if re.match(self.path_patterns['module'], path):
            return True
            
        return False

    def _convert_to_absolute(self, path: str) -> Optional[str]:
        """将相对路径转换为绝对路径"""
        try:
            if os.path.isabs(path):
                return path
                
            # 尝试相对于项目根目录
            abs_path = os.path.abspath(os.path.join(str(self.project_root), path))
            if os.path.exists(abs_path):
                return abs_path
                
            # 尝试相对于当前工作目录
            abs_path = os.path.abspath(path)
            if os.path.exists(abs_path):
                return abs_path
                
            return None
        except Exception:
            return None

    def _convert_to_relative(self, path: str) -> Optional[str]:
        """将绝对路径转换为相对路径"""
        try:
            if not os.path.isabs(path):
                return path
                
            # 尝试相对于项目根目录
            rel_path = os.path.relpath(path, str(self.project_root))
            if not rel_path.startswith('..'):
                return rel_path
                
            return None
        except Exception:
            return None

    def _guess_path_from_content(self, path: Path, content: str) -> Optional[str]:
        """基于文件内容推断正确路径"""
        suffix = path.suffix.lower()
        
        # Java文件处理
        if suffix == '.java':
            result = self._process_java_file(path, content)
            if result:
                return str(result)
            
        # Python文件处理
        elif suffix == '.py':
            result = self._process_python_file(path, content)
            if result:
                return str(result)
            
        # Go文件处理
        elif suffix == '.go':
            result = self._process_go_file(path, content)
            if result:
                return str(result)
            
        # JavaScript/TypeScript处理
        elif suffix in ['.js', '.ts']:
            result = self._process_js_ts_file(path, content)
            if result:
                return str(result)
            
        # Vue文件处理
        elif suffix == '.vue':
            result = self._process_vue_file(path, content)
            if result:
                return str(result)
            
        # 微信小程序文件
        elif suffix in ['.wxml', '.wxss', '.wxs']:
            result = self._process_wechat_miniprogram_file(path, content)
            if result:
                return str(result)
            
        # C/C++文件
        elif suffix in ['.cpp', '.c', '.h', '.hpp']:
            result = self._process_cpp_file(path, content)
            if result:
                return str(result)

        # 通用处理：在常见目录下查找
        result = self._find_in_common_directories(path)
        if result:
            return str(result)
            
        return None
        
    def _process_java_file(self, path: Path, content: str) -> Optional[Path]:
        """处理Java文件路径"""
        package = self._extract_java_package(content)
        if package:
            # 判断是否需要替换包名
            if package.startswith("com.web"):
                # 将com.web替换为com.main
                package = "com.main" + package[7:]
                
            package_path = package.replace('.', '/')
            
            # 检查项目根目录是否已包含Java标准目录结构
            standard_java_path = "src/main/java"
            proj_str = str(self.project_root)
            
            # 检查根路径中是否存在重复路径段
            # 例如：D:\Java_code\project\cakeshop\src\main\java\com\main\src\main\java\com\main\
            duplicate_segments = self._find_duplicate_path_segments(proj_str)
            if duplicate_segments:
                # 如果有重复段，使用去重后的路径
                clean_root = self._remove_duplicate_segments(proj_str, duplicate_segments)
                base_dir = Path(clean_root)
                
                # 检查清理后的路径是否已包含Java和包路径
                if standard_java_path in clean_root and package_path in clean_root:
                    # 如果已包含完整路径，直接拼接文件名
                    if clean_root.endswith(f"{standard_java_path}/{package_path}"):
                        return base_dir / path.name
                    else:
                        # 找到java目录位置
                        java_pos = clean_root.rindex(standard_java_path) + len(standard_java_path)
                        java_base = Path(clean_root[:java_pos])
                        return java_base / package_path / path.name
                else:
                    # 不包含完整路径，添加标准结构
                    return base_dir / standard_java_path / package_path / path.name
            else:
                # 无重复段，使用常规处理
                # 检查路径冗余问题
                if standard_java_path in proj_str:
                    # 如果项目根目录已经包含了Java标准路径，避免重复添加
                    if proj_str.endswith(standard_java_path):
                        # 根目录已经是到Java目录，直接添加包路径
                        return self.project_root / package_path / path.name
                    elif proj_str.endswith(f"{standard_java_path}/{package_path}"):
                        # 根目录已经到达包路径
                        return self.project_root / path.name
                    else:
                        # 根目录包含标准Java路径但未到达包路径
                        java_pos = proj_str.rindex(standard_java_path) + len(standard_java_path)
                        base_dir = Path(proj_str[:java_pos])
                        return base_dir / package_path / path.name
                else:
                    # 项目根目录不包含Java标准路径，需要添加完整路径
                    return self.project_root / standard_java_path / package_path / path.name
        
        return None
        
    def _process_python_file(self, path: Path, content: str) -> Optional[Path]:
        """处理Python文件路径"""
        # 1. 尝试从模块注释中提取
        module_match = re.search(r'^#\s*module[:：]\s*([\w.]+)', content, re.MULTILINE)
        if module_match:
            module = module_match.group(1)
            return self.project_root / module.replace('.', '/') / path.name
            
        # 2. 尝试从import语句推断
        imports = re.findall(r'^(?:from|import)\s+([\w.]+)', content, re.MULTILINE)
        for imp in imports:
            if '.' in imp:
                base_module = imp.split('.')[0]
                potential_paths = [
                    self.project_root / base_module / path.name,
                    self.project_root / "src" / base_module / path.name,
                    self.project_root / "app" / base_module / path.name
                ]
                for p in potential_paths:
                    if p.exists():
                        return p
                        
        # 3. 查找常见Python项目结构
        potential_paths = [
            self.project_root / path.name,
            self.project_root / "src" / path.name,
            self.project_root / "app" / path.name,
            self.project_root / "modules" / path.name,
            self.project_root / "lib" / path.name
        ]
        
        for p in potential_paths:
            if p.exists():
                return p
                
        return None

    def _process_go_file(self, path: Path, content: str) -> Optional[Path]:
        """处理Go文件路径"""
        # 1. 从package声明推断
        package_match = re.search(r'^package\s+(\w+)', content, re.MULTILINE)
        if package_match:
            package_name = package_match.group(1)
            # 在常见Go项目结构中查找
            potential_paths = [
                self.project_root / "src" / package_name / path.name,
                self.project_root / "pkg" / package_name / path.name,
                self.project_root / "internal" / package_name / path.name,
                self.project_root / "cmd" / package_name / path.name
            ]
            for p in potential_paths:
                if p.exists():
                    return p
                    
        # 2. 从import语句推断
        imports = re.findall(r'^import\s+[\'"]([^"\']+)[\'"]', content, re.MULTILINE)
        for imp in imports:
            if '/' in imp:
                base_pkg = imp.split('/')[0]
                potential_paths = [
                    self.project_root / "src" / base_pkg / path.name,
                    self.project_root / "pkg" / base_pkg / path.name
                ]
                for p in potential_paths:
                    if p.exists():
                        return p
                        
        return None

    def _process_js_ts_file(self, path: Path, content: str) -> Optional[Path]:
        """处理JavaScript/TypeScript文件路径"""
        # 1. 从import/require语句推断
        imports = re.findall(r'(?:import|require)\s+[\'"]([^"\']+)[\'"]', content)
        for imp in imports:
            if '/' in imp:
                potential_dir = imp.split('/')[0]
                potential_paths = [
                    self.project_root / "src" / potential_dir / path.name,
                    self.project_root / potential_dir / path.name,
                    self.project_root / "components" / potential_dir / path.name,
                    self.project_root / "pages" / potential_dir / path.name
                ]
                for p in potential_paths:
                    if p.exists():
                        return p
                        
        # 2. 查找常见JS/TS项目结构
        potential_paths = [
            self.project_root / "src" / path.name,
            self.project_root / "public" / path.name,
            self.project_root / "assets" / path.name,
            self.project_root / "components" / path.name,
            self.project_root / "pages" / path.name
        ]
        
        for p in potential_paths:
            if p.exists():
                return p
                
        return None

    def _process_vue_file(self, path: Path, content: str) -> Optional[Path]:
        """处理Vue文件路径"""
        # 查找常见Vue项目结构
        potential_paths = [
            self.project_root / "src" / "components" / path.name,
            self.project_root / "src" / "views" / path.name,
            self.project_root / "src" / "pages" / path.name
        ]
        for p in potential_paths:
            if p.exists():
                return p
        return None
        
    def _process_wechat_miniprogram_file(self, path: Path, content: str) -> Optional[Path]:
        """处理微信小程序文件路径"""
        # 微信小程序通常放在pages目录下
        potential_paths = [
            self.project_root / "pages" / path.stem / path.name,
            self.project_root / "components" / path.stem / path.name,
            self.project_root / "miniprogram" / "pages" / path.stem / path.name
        ]
        for p in potential_paths:
            if p.exists():
                return p
        return None
        
    def _process_cpp_file(self, path: Path, content: str) -> Optional[Path]:
        """处理C/C++文件路径"""
        # 1. 从头文件包含推断
        includes = re.findall(r'#include\s+[<"]([\w/.]+)[>"]', content)
        if includes:
            # 尝试推断项目结构
            potential_paths = [
                self.project_root / "src" / path.name,
                self.project_root / "include" / path.name,
                self.project_root / "lib" / path.name,
                self.project_root / "test" / path.name
            ]
            for p in potential_paths:
                if p.exists():
                    return p
                    
        # 2. 根据文件类型选择目录
        if path.suffix in ['.h', '.hpp']:
            # 头文件通常放在include目录
            potential_paths = [
                self.project_root / "include" / path.name,
                self.project_root / "include" / path.parent.name / path.name
            ]
        else:
            # 源文件通常放在src目录
            potential_paths = [
                self.project_root / "src" / path.name,
                self.project_root / "src" / path.parent.name / path.name
            ]
            
        for p in potential_paths:
            if p.exists():
                return p
                
        return None
        
    def _find_in_common_directories(self, path: Path) -> Optional[Path]:
        """在常见目录结构中查找文件"""
        common_dirs = [
            'src/main', 'src/test', 'src', 'app', 
            'src/main/resources', 'resources',
            'public', 'static', 'assets',
            'lib', 'libs', 'include'
        ]
        
        for base in common_dirs:
            new_path = self.project_root / base / path
            if new_path.exists():
                return new_path
                
        return None

    def _extract_java_package(self, content: str) -> Optional[str]:
        """提取Java包声明"""
        match = re.search(r'^package\s+([\w.]+)\s*;', content, re.MULTILINE)
        return match.group(1) if match else None

    def _extract_python_module(self, content: str) -> Optional[str]:
        """提取Python模块信息"""
        # 检查Django/Flask应用
        module_match = re.search(r'^app_name\s*=\s*[\'"]([\w.]+)[\'"]', content, re.MULTILINE)
        if module_match:
            return module_match.group(1)
            
        # 检查模块注释
        comment_match = re.search(r'^#\s*module[:：]\s*([\w.]+)', content, re.MULTILINE)
        if comment_match:
            return comment_match.group(1)
            
        return None

    def get_file_language(self, file_path: str) -> str:
        """获取文件语言类型"""
        ext = Path(file_path).suffix.lower()
        return self.file_type_map.get(ext, "Unknown")
        
    def _ask_ai_for_path(self, original_path: str, content_sample: str) -> Optional[str]:
        """使用AI推荐文件路径"""
        try:
            # 提取文件名和扩展名
            file_name = Path(original_path).name
            file_ext = Path(original_path).suffix
            
            # 构建提示词
            prompt = f"""请根据以下信息推荐一个合适的文件路径:
原始路径: {original_path}
文件名: {file_name}
文件类型: {self.file_type_map.get(file_ext, '未知')}

代码片段:
```
{content_sample}
```

只返回一个文件路径，不要有任何解释。"""

            # 调用本地AI API
            result = subprocess.run([
                "curl", "http://localhost:11434/api/chat",
                "-d", f'{{"model": "gemma3:4b", "messages": [{{"role": "user", "content": "{prompt}"}}]}}'
            ], capture_output=True, text=True)

            if result.returncode == 0 and result.stdout:
                try:
                    # 尝试解析JSON响应
                    response_data = json.loads(result.stdout)
                    content = response_data.get("message", {}).get("content", "")
                    # 清理和验证路径
                    path = content.strip().strip('`"\' \n')
                    if path and "/" in path:
                        return path
                except Exception as e:
                    logging.error(f"解析AI响应失败: {e}")
                    
            return None
        except Exception as e:
            logging.error(f"AI推荐路径失败: {e}")
            return None
            
    def _find_best_target_directory(self, file_name: str, content: str) -> Optional[str]:
        """查找最适合的目标目录"""
        ext = Path(file_name).suffix.lower()
        language = self.get_file_language(file_name)
        
        # 特定语言的目标目录映射
        lang_dir_map = {
            'Java': ['src/main/java', 'src/java', 'java'],
            'Python': ['src', 'app', 'modules'],
            'JavaScript': ['src/js', 'js', 'public/js', 'assets/js'],
            'TypeScript': ['src/ts', 'ts', 'src'],
            'Go': ['src', 'pkg', 'internal'],
            'C++': ['src', 'include', 'lib'],
            'C': ['src', 'include', 'lib'],
            'Vue': ['src/components', 'src/views', 'src/pages'],
            '微信小程序': ['pages', 'components', 'miniprogram']
        }
        
        # 获取语言对应的目录
        target_dirs = lang_dir_map.get(language, ['src'])
        
        # 如果是Java文件，尝试从包名确定精确目录
        if ext == '.java':
            package = self._extract_java_package(content)
            if package:
                # 处理com.web -> com.main的转换
                if package.startswith("com.web"):
                    package = "com.main" + package[7:]
                package_path = package.replace('.', '/')
                return f"src/main/java/{package_path}/{file_name}"
                
        # 扫描项目结构，查找最匹配的目录
        for base_dir in target_dirs:
            potential_path = f"{base_dir}/{file_name}"
            if (self.project_root / base_dir).exists():
                return potential_path
                
        # 默认返回第一个目录的路径
        return f"{target_dirs[0]}/{file_name}" 

    def _find_duplicate_path_segments(self, path_str: str) -> List[str]:
        """查找路径中的重复段"""
        # 将路径分割为段
        path_str = self._normalize_path(path_str)
        segments = path_str.split('/')
        duplicates = []
        
        # 常见的可能重复的路径段组合
        patterns = [
            "src/main/java",
            "src/main/resources",
            "com/main",
            "com/web",
            "src/main",
            "src/test",
            "src/app",
            "src/components",
            "src/pages"
        ]
        
        for pattern in patterns:
            pattern_parts = pattern.split('/')
            pattern_len = len(pattern_parts)
            
            # 检查路径中是否有连续的模式重复
            for i in range(len(segments) - pattern_len * 2 + 1):
                segment1 = '/'.join(segments[i:i+pattern_len])
                segment2 = '/'.join(segments[i+pattern_len:i+pattern_len*2])
                
                if segment1 == segment2 == pattern:
                    duplicates.append(pattern)
                    break
                    
            # 检查非连续重复
            if pattern in path_str:
                count = path_str.count(pattern)
                if count > 1:
                    duplicates.append(pattern)
        
        return duplicates
        
    def _remove_duplicate_segments(self, path_str: str, duplicate_segments: List[str]) -> str:
        """从路径中移除重复段"""
        clean_path = path_str
        
        # 特殊处理常见的Java路径问题
        if 'src/main/java/com/main' in clean_path:
            # 查找重复的Java路径模式 (src/main/java/com/main/src/main/java/com/main)
            pattern = r'(.*?/src/main/java/com/main)/src/main/java/com/main(.*)'
            match = re.match(pattern, clean_path)
            if match:
                # 保留第一个出现的路径
                clean_path = f"{match.group(1)}{match.group(2)}"
                return self._normalize_path(clean_path)
                
        # 通用处理方法
        for segment in duplicate_segments:
            # 替换重复的路径段为单个段
            double_segment = f"{segment}/{segment}"
            clean_path = clean_path.replace(double_segment, segment)
            
            # 处理更复杂的情况，如连续三次重复
            triple_segment = f"{segment}/{segment}/{segment}"
            clean_path = clean_path.replace(triple_segment, segment)
            
            # 处理非连续重复
            if clean_path.count(segment) > 1:
                # 分析路径结构
                parts = clean_path.split('/')
                result_parts = []
                segment_parts = segment.split('/')
                
                i = 0
                while i < len(parts):
                    # 检查是否匹配段模式
                    if i + len(segment_parts) <= len(parts):
                        cur_segment = '/'.join(parts[i:i+len(segment_parts)])
                        if cur_segment == segment:
                            # 找到匹配段
                            if not any(s == segment for s in result_parts):
                                # 第一次出现，保留
                                result_parts.append(segment)
                            i += len(segment_parts)
                            continue
                    # 不匹配，添加当前部分
                    result_parts.append(parts[i])
                    i += 1
                
                clean_path = '/'.join(p for p in result_parts if p)
        
        return self._normalize_path(clean_path)

class DependencyChecker:
    """多语言依赖检查器"""

    def __init__(self, project_root: str):
        self.project_root = Path(project_root)
        self.available_imports = self._scan_project_imports()
        # 支持检查的文件类型
        self.supported_extensions = [
            '.java', '.py', '.js', '.ts', '.go', '.cpp', '.c', '.h', '.hpp', 
            '.vue', '.wxs', '.php', '.rb', '.kt', '.swift'
        ]

    def _scan_project_imports(self) -> Dict[str, str]:
        """扫描项目中所有可用的导入"""
        imports = {}
        
        # 扫描Java文件
        for file in self.project_root.rglob('*.java'):
            content = self._read_file_safely(file)
            package = self._extract_java_package(content)
            if package:
                class_name = file.stem
                imports[f"{package}.{class_name}"] = str(file)
                
        # 扫描Python文件
        for file in self.project_root.rglob('*.py'):
            if file.name.startswith('__'):  # 跳过 __init__.py 等特殊文件
                continue
            module = self._get_python_module_path(file)
            if module:
                imports[module] = str(file)
                
        # 扫描JavaScript/TypeScript文件
        for ext in ['.js', '.ts']:
            for file in self.project_root.rglob(f'*{ext}'):
                module_name = self._get_js_module_name(file)
                if module_name:
                    imports[module_name] = str(file)
                    
        # 扫描Go文件
        for file in self.project_root.rglob('*.go'):
            content = self._read_file_safely(file)
            package = self._extract_go_package(content)
            if package:
                imports[package] = str(file)
                
        # 扫描C/C++文件
        for ext in ['.cpp', '.c', '.h', '.hpp']:
            for file in self.project_root.rglob(f'*{ext}'):
                header_name = file.name
                imports[header_name] = str(file)

        # 扫描微信小程序文件
        for ext in ['.wxs', '.wxml']:
            for file in self.project_root.rglob(f'*{ext}'):
                module_name = file.stem
                imports[module_name] = str(file)
                
        # 扫描Vue文件
        for file in self.project_root.rglob('*.vue'):
            component_name = file.stem
            imports[component_name] = str(file)
                
        return imports

    def _read_file_safely(self, file_path: Path) -> str:
        """安全读取文件内容"""
        try:
            return file_path.read_text(encoding='utf-8', errors='ignore')
        except Exception as e:
            logging.error(f"读取文件失败: {file_path}, 错误: {str(e)}")
            return ""

    def _get_python_module_path(self, file: Path) -> Optional[str]:
        """获取Python模块导入路径"""
        try:
            rel_path = file.relative_to(self.project_root)
            module_path = str(rel_path.with_suffix('')).replace('/', '.').replace('\\', '.')
            return module_path
        except ValueError:
            return None

    def _get_js_module_name(self, file: Path) -> Optional[str]:
        """获取JS/TS模块名称"""
        try:
            rel_path = file.relative_to(self.project_root)
            # 移除扩展名，转换路径分隔符
            module_name = str(rel_path.with_suffix('')).replace('\\', '/').replace('../', '')
            return module_name
        except ValueError:
            return None
            
    def _extract_go_package(self, content: str) -> Optional[str]:
        """提取Go包名"""
        match = re.search(r'^package\s+(\w+)', content, re.MULTILINE)
        return match.group(1) if match else None
        
    def _extract_java_package(self, content: str) -> Optional[str]:
        """提取Java包声明"""
        match = re.search(r'^package\s+([\w.]+)\s*;', content, re.MULTILINE)
        return match.group(1) if match else None

    def check_imports(self, content: str, file_ext: str = '') -> Tuple[Dict[str, List[str]], List[str]]:
        """检查文件内容中的导入语句"""
        missing = {}
        messages = []
        
        # 判断文件类型
        file_type = self._detect_file_type(content, file_ext)
        
        if file_type == "java":
            # 检查Java导入
            imports = self._extract_java_imports(content)
            for imp in imports:
                if imp not in self.available_imports:
                    if imp.startswith(("java.", "javax.", "org.springframework", "lombok.", "org.junit", "org.apache.")):
                        continue  # 跳过标准库和常见第三方库
                    missing[imp] = self._get_import_suggestion(imp, "java")
                    messages.append(f"⚠️ 缺失导入: {imp}")
                    
        elif file_type == "python":
            # 检查Python导入
            imports = self._extract_python_imports(content)
            for imp in imports:
                if imp not in self.available_imports:
                    if imp in ["os", "sys", "re", "json", "math", "time", "datetime", "typing", "logging"]:
                        continue  # 跳过标准库
                        
                    # 检查是否在requirements.txt中
                    has_req = False
                    
                    # 检查同目录下的requirements.txt
                    req_file = self.project_root / "requirements.txt"
                    if not req_file.exists():
                        # 向上查找两级目录
                        req_file = self.project_root.parent / "requirements.txt"
                        if not req_file.exists():
                            req_file = self.project_root.parent.parent / "requirements.txt"
                    
                    if req_file.exists():
                        try:
                            req_content = req_file.read_text(encoding='utf-8', errors='ignore')
                            if imp in req_content or imp.split('.')[0] in req_content:
                                has_req = True
                        except:
                            pass
                    
                    if not has_req:
                        missing[imp] = self._get_import_suggestion(imp, "python")
                        messages.append(f"⚠️ 缺失导入: {imp}")
                    
        elif file_type == "javascript":
            # 检查JS/TS导入
            imports = self._extract_js_imports(content)
            for imp in imports:
                if imp not in self.available_imports:
                    missing[imp] = self._get_import_suggestion(imp, "javascript")
                    messages.append(f"⚠️ 缺失导入: {imp}")
                    
        elif file_type == "go":
            # 检查Go导入
            imports = self._extract_go_imports(content)
            for imp in imports:
                if imp not in self.available_imports:
                    missing[imp] = self._get_import_suggestion(imp, "go")
                    messages.append(f"⚠️ 缺失导入: {imp}")
                    
        elif file_type == "cpp":
            # 检查C/C++导入
            includes = self._extract_cpp_includes(content)
            for inc in includes:
                if inc not in self.available_imports and not inc.endswith(('.h', '.hpp')):
                    missing[inc] = self._get_import_suggestion(inc, "cpp")
                    messages.append(f"⚠️ 缺失包含: {inc}")
                    
        elif file_type == "vue":
            # 检查Vue组件导入
            imports = self._extract_vue_imports(content)
            for imp in imports:
                if imp not in self.available_imports:
                    missing[imp] = self._get_import_suggestion(imp, "vue")
                    messages.append(f"⚠️ 缺失组件: {imp}")
                    
        elif file_type == "wxs":
            # 检查微信小程序导入
            imports = self._extract_wechat_imports(content)
            for imp in imports:
                if imp not in self.available_imports:
                    missing[imp] = self._get_import_suggestion(imp, "wechat.txt")
                    messages.append(f"⚠️ 缺失模块: {imp}")

        return missing, messages

    def _detect_file_type(self, content: str, file_ext: str = '') -> str:
        """检测文件类型"""
        # 如果传入了有效的扩展名，优先根据扩展名判断
        if file_ext:
            ext_map = {
                '.java': 'java',
                '.py': 'python',
                '.js': 'javascript',
                '.ts': 'javascript',  # TypeScript也用javascript检查器
                '.go': 'go',
                '.cpp': 'cpp', '.c': 'cpp', '.h': 'cpp', '.hpp': 'cpp',
                '.vue': 'vue',
                '.wxs': 'wxs', '.wxml': 'wxs'
            }
            if file_ext.lower() in ext_map:
                return ext_map[file_ext.lower()]
        
        # 否则根据内容判断
        content_start = content.lstrip()[:100].lower()
        
        if content_start.startswith("package ") and ";" in content_start:
            return "java"
        elif content_start.startswith("package ") and "import" in content:
            return "go"
        elif "import " in content_start or "from " in content_start:
            return "python"
        elif "function" in content_start or "const" in content_start or "let" in content_start:
            return "javascript"
        elif "#include" in content_start:
            return "cpp"
        elif "<template" in content and "<script" in content:
            return "vue"
        elif "require" in content and "module.exports" in content:
            return "wxs"
        
        return "unknown"

    def _extract_java_imports(self, content: str) -> List[str]:
        """提取Java导入语句"""
        imports = re.findall(r'^import\s+([\w.]+)(?:\s*\*\s*)?;', content, re.MULTILINE)
        return [imp for imp in imports if not imp.endswith('*')]

    def _extract_python_imports(self, content: str) -> List[str]:
        """提取Python导入语句"""
        imports = []
        # 简单导入
        imports.extend(re.findall(r'^import\s+([\w.]+)', content, re.MULTILINE))
        # from导入
        from_imports = re.findall(r'^from\s+([\w.]+)\s+import', content, re.MULTILINE)
        imports.extend(from_imports)
        return imports
        
    def _extract_js_imports(self, content: str) -> List[str]:
        """提取JavaScript/TypeScript导入语句"""
        # ES6 import
        es6_imports = re.findall(r'import\s+.+\s+from\s+[\'"]([^\'"]+)[\'"]', content)
        # require导入
        require_imports = re.findall(r'require\s*\(\s*[\'"]([^\'"]+)[\'"]', content)
        return es6_imports + require_imports
        
    def _extract_go_imports(self, content: str) -> List[str]:
        """提取Go导入语句"""
        # 多行导入
        multi_imports = re.findall(r'import\s*\(\s*(.*?)\s*\)', content, re.DOTALL)
        imports = []
        for block in multi_imports:
            imports.extend(re.findall(r'[\'"]([^\'"]+)[\'"]', block))
        # 单行导入
        single_imports = re.findall(r'import\s+[\'"]([^\'"]+)[\'"]', content)
        return imports + single_imports
        
    def _extract_cpp_includes(self, content: str) -> List[str]:
        """提取C/C++包含语句"""
        # 系统头文件 <file.h>
        system_includes = re.findall(r'#include\s*<([^>]+)>', content)
        # 本地头文件 "file.h"
        local_includes = re.findall(r'#include\s*"([^"]+)"', content)
        return system_includes + local_includes
        
    def _extract_vue_imports(self, content: str) -> List[str]:
        """提取Vue组件导入"""
        # 在<script>部分中提取导入
        script_part = re.search(r'<script[^>]*>(.*?)</script>', content, re.DOTALL)
        if script_part:
            script_content = script_part.group(1)
            # 提取组件导入
            component_imports = re.findall(r'import\s+(\w+)\s+from', script_content)
            return component_imports
        return []
        
    def _extract_wechat_imports(self, content: str) -> List[str]:
        """提取微信小程序导入"""
        # 提取require导入
        require_imports = re.findall(r'require\s*\(\s*[\'"]([^\'"]+)[\'"]', content)
        # 提取include组件
        include_imports = re.findall(r'<import\s+src=[\'"]([^\'"]+)[\'"]', content)
        return require_imports + include_imports

    def _get_import_suggestion(self, missing_import: str, lang_type: str = "java") -> List[str]:
        """获取AI生成的导入建议"""
        try:
            # 构建提示词
            lang_map = {
                "java": "Java", 
                "python": "Python", 
                "javascript": "JavaScript/TypeScript",
                "go": "Go",
                "cpp": "C++",
                "vue": "Vue",
                "wechat.txt": "微信小程序"
            }
            
            lang_name = lang_map.get(lang_type, "代码")
            
            prompt = f"""在{lang_name}项目中，导入 '{missing_import}' 不可用。
请提供3个可能的替代方案，并简要说明每个替代方案的作用。
只需返回替代方案，每行一个。"""

            # 调用本地AI API
            result = subprocess.run([
                "curl", "http://localhost:11434/api/chat",
                "-d", f'{{"model": "gemma3:4b", "messages": [{{"role": "user", "content": "{prompt}"}}]}}'
            ], capture_output=True, text=True)

            if result.returncode == 0 and result.stdout:
                # 解析AI回复，从JSON中提取结果
                try:
                    response_data = json.loads(result.stdout)
                    content = response_data.get("message", {}).get("content", "")
                    suggestions = [line.strip() for line in content.splitlines() if line.strip()]
                    return suggestions[:3]  # 最多返回3个建议
                except json.JSONDecodeError:
                    # 如果不是JSON格式，直接按行分割
                    return [line.strip() for line in result.stdout.splitlines() if line.strip()][:3]
        except Exception as e:
            logging.error(f"AI导入建议失败: {e}")
        
        return []
        
    def get_dependency_info(self, missing_import: str, lang_type: str) -> str:
        """获取依赖信息详细说明"""
        try:
            # 构建提示词
            prompt = f"""请提供关于'{missing_import}'的详细说明：

1. 这个导入/包/模块的主要功能是什么？
2. 它通常在什么情况下使用？
3. 安装或获取它的方法是什么？
4. 有无代码示例展示其基本用法？

请简明扼要地回答，总长度控制在200字以内。"""

            # 调用本地AI API
            result = subprocess.run([
                "curl", "http://localhost:11434/api/chat",
                "-d", f'{{"model": "gemma3:4b", "messages": [{{"role": "user", "content": "{prompt}"}}]}}'
            ], capture_output=True, text=True)

            if result.returncode == 0 and result.stdout:
                try:
                    response_data = json.loads(result.stdout)
                    content = response_data.get("message", {}).get("content", "")
                    return content.strip()
                except:
                    return "无法获取详细信息"
        except Exception as e:
            logging.error(f"获取依赖信息失败: {e}")
            
        return "无法获取详细信息" 

class CodeChangeProcessor:
    """多语言代码变更处理器"""

    def __init__(self, project_root: str):
        self.path_resolver = EnhancedPathResolver(project_root)
        self.dependency_checker = DependencyChecker(project_root)
        self.project_root = Path(project_root)
        # 文件类型映射 - 使用emoji增强可视化
        self.file_type_map = {
            '.java': '☕ Java',
            '.py': '🐍 Python',
            '.js': '📜 JavaScript', 
            '.ts': '📘 TypeScript',
            '.go': '🐹 Go',
            '.cpp': '⚙️ C++', 
            '.c': '🔧 C',
            '.h': '📑 C/C++头文件',
            '.hpp': '📑 C++头文件',
            '.html': '🌐 HTML',
            '.css': '🎨 CSS',
            '.vue': '💚 Vue',
            '.wxml': '📱 微信小程序',
            '.wxss': '🎭 微信小程序样式',
            '.wxs': '📋 微信小程序脚本',
            '.json': '📦 JSON',
            '.xml': '📝 XML',
            '.md': '📔 Markdown',
            '.php': '🌀 PHP',
            '.rb': '💎 Ruby',
            '.kt': '🏝️ Kotlin',
            '.swift': '🦅 Swift'
        }

    def process_change(self, original_path: str, new_content: str) -> Dict:
        """处理代码变更"""
        result = {
            "original_path": original_path,
            "warnings": [],
            "resolved_path": None,
            "missing_imports": {},
            "requires_confirmation": False,
            "language": "Unknown",
            "file_exists": False,
            "has_content_changes": False,
            "risk_operations": [],
            "new_content": new_content,
            "is_multi_file": False,
            "additional_files": []
        }

        # 检查是否有多文件数据传入
        is_multi_file = hasattr(self.path_resolver, 'multiple_files_data') and len(getattr(self.path_resolver, 'multiple_files_data', [])) > 1
        
        # 处理多文件情况
        if is_multi_file:
            result["is_multi_file"] = True
            multi_files = getattr(self.path_resolver, 'multiple_files_data', [])
            
            # 处理第一个文件
            main_file = multi_files[0]
            main_result = self._process_single_file(main_file['path'], main_file['content'])
            
            # 合并主文件结果到总结果
            for key in main_result:
                if key != 'additional_files':
                    result[key] = main_result[key]
                    
            # 处理剩余文件
            for i in range(1, len(multi_files)):
                file_data = multi_files[i]
                file_result = self._process_single_file(file_data['path'], file_data['content'])
                result["additional_files"].append(file_result)
                
                # 累积警告和风险
                result["warnings"].extend(file_result["warnings"])
                result["risk_operations"].extend(file_result["risk_operations"])
                
                # 如果任何附加文件需要确认，整体也需要确认
                if file_result["requires_confirmation"]:
                    result["requires_confirmation"] = True
        else:
            # 单文件处理
            single_result = self._process_single_file(original_path, new_content)
            for key in single_result:
                result[key] = single_result[key]

        return result
        
    def _process_single_file(self, original_path: str, new_content: str) -> Dict:
        """处理单个文件变更"""
        processor_version = "3.1"  # 更新版本号
        result = {
            'processor_version': processor_version,
            'is_valid': True,
            'original_path': original_path,
            'resolved_path': '',
            'warnings': [],
            'errors': [],
            'is_new_file': False,
            'is_multi_file': False,
            'path_fixed': False,
            'language': '',
            'statistics': {
                'line_count': 0,
                'char_count': 0
            },
            'actions': [],
            'duplicate_path_segments': []
        }

        # 1. 路径解析
        resolved_path, path_warnings = self.path_resolver.resolve(original_path, new_content)
        result["resolved_path"] = resolved_path
        result["warnings"].extend(path_warnings)
        
        # 检查并修复路径中的重复段 - 重点检查Java路径
        # 先检查是否是Java文件且存在路径问题
        if resolved_path.endswith('.java') and 'src/main/java/com' in resolved_path:
            # 特殊处理Java重复路径问题
            pattern = r'(.*?/src/main/java/com/main)/src/main/java/com/main(.*)'
            match = re.match(pattern, resolved_path)
            if match:
                # 修复重复的Java路径
                clean_path = f"{match.group(1)}{match.group(2)}"
                if clean_path != resolved_path:
                    result["warnings"].append(f"路径自动修正(修复Java路径): {original_path} → {clean_path}")
                    result["path_fixed"] = True
                    result["resolved_path"] = clean_path
                    resolved_path = clean_path
                    result["duplicate_path_segments"].append("src/main/java/com/main")
        
        # 通用重复段检查
        duplicates = self.path_resolver._find_duplicate_path_segments(resolved_path)
        if duplicates:
            result["duplicate_path_segments"].extend([d for d in duplicates if d not in result["duplicate_path_segments"]])
            # 修复重复段
            clean_path = self.path_resolver._remove_duplicate_segments(resolved_path, duplicates)
            if clean_path != resolved_path:
                result["warnings"].append(f"路径自动修正(修复重复段): {original_path} → {clean_path}")
                result["path_fixed"] = True
                result["resolved_path"] = clean_path
                resolved_path = clean_path
                
        # 判断路径是否有变更
        if resolved_path != original_path:
            result["actions"].append(f"路径变更: {original_path} -> {resolved_path}")

        # 获取文件类型
        file_ext = Path(resolved_path).suffix.lower()
        result["language"] = self.path_resolver.get_file_language(resolved_path)
        
        # 2. 检查文件是否存在
        full_path = self.project_root / resolved_path
        parent_dir = full_path.parent
        
        if not parent_dir.exists():
            result["actions"].append(f"创建新目录: {parent_dir}")
        
        file_exists = full_path.exists()
        if file_exists:
            # 读取原始内容
            try:
                with open(full_path, 'r', encoding='utf-8', errors='ignore') as f:
                    original_content = f.read()
                
                # 保存原始内容用于撤销功能
                result["original_content"] = original_content
                
                # 检查内容是否有变更
                has_content_changes = original_content != new_content
                result["has_content_changes"] = has_content_changes
                
                if has_content_changes:
                    result["actions"].append("修改现有文件内容")
            except Exception as e:
                result["warnings"].append(f"读取文件失败: {str(e)}")
        else:
            result["is_new_file"] = True
            result["actions"].append("创建新文件")
            
        # 修正Java文件包名 - 确保路径和包名一致
        if file_ext == '.java':
            # 检查Java包声明是否与路径一致
            pkg_match = re.search(r'^package\s+([\w.]+)\s*;', new_content, re.MULTILINE)
            if pkg_match:
                current_pkg = pkg_match.group(1)
                corrected_content = self._correct_java_package(new_content, resolved_path, original_path)
                if corrected_content != new_content:
                    # 包名被修正，更新内容
                    new_content = corrected_content
                    # 添加警告信息
                    new_pkg_match = re.search(r'^package\s+([\w.]+)\s*;', new_content, re.MULTILINE)
                    if new_pkg_match and new_pkg_match.group(1) != current_pkg:
                        result["warnings"].append(f"自动修正Java包名: {current_pkg} → {new_pkg_match.group(1)}")
            
        # 3. 检查导入依赖
        missing_imports, import_warnings = self.dependency_checker.check_imports(new_content, file_ext)
        result["missing_imports"] = missing_imports
        result["warnings"].extend(import_warnings)
        
        # 4. 语言特定检查
        specific_warnings = self._perform_language_specific_checks(resolved_path, new_content)
        result["warnings"].extend(specific_warnings)
        
        # 5. 统计信息
        result["statistics"]["line_count"] = len(new_content.splitlines())
        result["statistics"]["char_count"] = len(new_content)
        
        # 6. 风险评估
        if result["is_new_file"] or not file_exists:
            result["requires_confirmation"] = True
        elif result["duplicate_path_segments"]:
            result["requires_confirmation"] = True
            result["warnings"].append("检测到路径中存在重复段，建议使用\"批量编辑路径\"工具修复")
            
        # 更新修改后的内容    
        result["new_content"] = new_content
        
        return result
        
    def _perform_language_specific_checks(self, file_path: str, content: str) -> List[str]:
        """执行特定语言的检查"""
        warnings = []
        ext = Path(file_path).suffix.lower()
        
        if ext == '.java':
            warnings.extend(self._check_java_file(file_path, content))
        elif ext == '.py':
            warnings.extend(self._check_python_file(content))
        elif ext in ['.js', '.ts']:
            warnings.extend(self._check_js_ts_file(content, ext))
        elif ext == '.go':
            warnings.extend(self._check_go_file(content))
        elif ext in ['.cpp', '.c', '.h', '.hpp']:
            warnings.extend(self._check_cpp_file(content, ext))
        elif ext == '.vue':
            warnings.extend(self._check_vue_file(content))
        elif ext in ['.wxml', '.wxss', '.wxs']:
            warnings.extend(self._check_wechat_file(content, ext))
        elif ext == '.php':
            warnings.extend(self._check_php_file(content))
        elif ext == '.kt':
            warnings.extend(self._check_kotlin_file(content))
            
        return warnings
        
    def _check_java_file(self, file_path: str, content: str) -> List[str]:
        """检查Java文件"""
        warnings = []
        
        # 检查包名是否与路径匹配
        package_match = re.search(r'^package\s+([\w.]+)\s*;', content, re.MULTILINE)
        if not package_match:
            warnings.append("⚠️ Java文件缺少package声明")
        else:
            package = package_match.group(1)
            # 检查包名是否与路径匹配
            expected_path = package.replace('.', '/') 
            if expected_path not in file_path and not file_path.endswith(expected_path):
                warnings.append(f"⚠️ 包名 {package} 与文件路径不匹配")
        
        # 检查类名与文件名是否匹配
        file_name = os.path.basename(file_path).replace('.java', '')
        class_match = re.search(r'public\s+(?:class|interface|enum)\s+(\w+)', content)
        if class_match:
            class_name = class_match.group(1)
            if class_name != file_name:
                warnings.append(f"⚠️ 类名 {class_name} 与文件名 {file_name} 不匹配")
        else:
            warnings.append("⚠️ Java文件缺少public class/interface/enum声明")
            
        # 检查JSR303注解
        if '@Valid' in content or '@NotNull' in content:
            if 'import javax.validation.constraints' not in content:
                warnings.append("提示: 使用了JSR303注解但缺少相关导入")
                
        # 检查Lombok注解
        if '@Data' in content or '@Getter' in content or '@Setter' in content:
            if 'import lombok' not in content:
                warnings.append("提示: 使用了Lombok注解但缺少相关导入")
            
        return warnings
        
    def _check_python_file(self, content: str) -> List[str]:
        """检查Python文件"""
        warnings = []
        
        # 检查编码声明
        if "# -*- coding: utf-8 -*-" not in content and "# coding=utf-8" not in content:
            warnings.append("提示: Python文件缺少UTF-8编码声明")
            
        # 检查主函数
        if "if __name__ == '__main__':" in content and "def main():" not in content:
            warnings.append("提示: 建议将主逻辑封装在main()函数中")
            
        # 检查类型注解
        if re.search(r'def\s+\w+\(\w+\s*:\s*\w+', content):
            if 'from typing import' not in content:
                warnings.append("提示: 使用了类型注解但未导入typing模块")
                
        # 检查f-string
        if re.search(r'f[\'"]', content) and not self._is_python_version_hint(content, '3.6+'):
            warnings.append("提示: 使用了f-string特性，需要Python 3.6+")
            
        return warnings
        
    def _check_js_ts_file(self, content: str, ext: str) -> List[str]:
        """检查JavaScript/TypeScript文件"""
        warnings = []
        
        # 检查strict模式
        if "'use strict';" not in content and '"use strict";' not in content:
            warnings.append("提示: 考虑添加'use strict';声明")
            
        # TypeScript特有检查
        if ext == '.ts':
            # 检查类型定义
            if 'interface' in content and not re.search(r'export\s+interface', content):
                warnings.append("提示: 考虑导出接口定义 (export interface)")
                
            # 检查tsconfig引用
            if '/// <reference' not in content and 'import' not in content:
                warnings.append("提示: 考虑添加模块导入或引用")
                
        # ES模块检查
        if 'import' in content and 'export' not in content:
            warnings.append("提示: 导入模块但未导出任何内容")
            
        return warnings
        
    def _check_go_file(self, content: str) -> List[str]:
        """检查Go文件"""
        warnings = []
        
        # 检查包名
        if not re.search(r'^package\s+\w+', content, re.MULTILINE):
            warnings.append("⚠️ Go文件缺少package声明")
            
        # 检查未使用的导入
        imports = re.findall(r'import\s+[\'"]([^\'"]+)[\'"]', content)
        for imp in imports:
            if imp and not re.search(r'\b' + re.escape(imp.split('/')[-1]) + r'\b', content):
                warnings.append(f"⚠️ 可能存在未使用的导入: {imp}")
                
        # 检查错误处理
        if 'err :=' in content and 'if err != nil' not in content:
            warnings.append("⚠️ 存在错误变量赋值但缺少错误检查")
            
        return warnings
        
    def _check_cpp_file(self, content: str, ext: str) -> List[str]:
        """检查C/C++文件"""
        warnings = []
        
        # 检查头文件保护
        if ext in ['.h', '.hpp'] and not self._has_header_guard(content):
            warnings.append("⚠️ C/C++头文件缺少头文件保护宏")
            
        # 检查Visual Studio安全警告
        if "#define _CRT_SECURE_NO_WARNINGS" not in content:
            warnings.append("提示: 考虑添加#define _CRT_SECURE_NO_WARNINGS")
            
        # 检查内存管理
        if 'malloc(' in content and 'free(' not in content:
            warnings.append("⚠️ 使用了malloc但未见到free，可能存在内存泄漏")
            
        # 检查C++特有特性
        if ext in ['.cpp', '.hpp']:
            if 'using namespace std;' in content:
                warnings.append("提示: 避免在头文件中使用'using namespace std;'")
                
            if 'new ' in content and 'delete ' not in content:
                warnings.append("⚠️ 使用了new但未见到delete，可能存在内存泄漏")
                
        return warnings
        
    def _check_vue_file(self, content: str) -> List[str]:
        """检查Vue文件"""
        warnings = []
        
        # 检查基本结构
        if "<template>" not in content:
            warnings.append("⚠️ Vue文件缺少<template>标签")
        if "<script>" not in content:
            warnings.append("⚠️ Vue文件缺少<script>标签")
            
        # 检查组件名称
        component_match = re.search(r'name:\s*[\'"](\w+)[\'"]', content)
        if component_match:
            component_name = component_match.group(1)
            # 检查组件命名是否符合规范(大驼峰或带连字符)
            if not (component_name[0].isupper() or '-' in component_name):
                warnings.append(f"提示: Vue组件名'{component_name}'应使用大驼峰或带连字符")
                
        # 检查Vue版本
        if 'defineComponent' in content:
            if 'vue3' not in content.lower() and '@vue/composition-api' not in content:
                warnings.append("提示: 使用了Vue 3 API但未明确标记Vue版本")
                
        return warnings
        
    def _check_wechat_file(self, content: str, ext: str) -> List[str]:
        """检查微信小程序文件"""
        warnings = []
        
        # 微信小程序样式文件
        if ext == '.wxss':
            if "page{" not in content.lower() and "page {" not in content.lower():
                warnings.append("提示: 微信小程序样式文件缺少页面基本样式")
                
        # 微信小程序脚本文件
        elif ext == '.wxs':
            if "module.exports" not in content:
                warnings.append("⚠️ 微信小程序脚本文件缺少导出语句")
                
        # 微信小程序页面文件
        elif ext == '.wxml':
            if not re.search(r'<\w+\s+[^>]*wx:', content):
                warnings.append("提示: 未使用微信小程序指令(如wx:for, wx:if等)")
                
        return warnings
        
    def _check_php_file(self, content: str) -> List[str]:
        """检查PHP文件"""
        warnings = []
        
        # 检查PHP标签
        if not content.strip().startswith('<?php'):
            warnings.append("⚠️ PHP文件应以<?php标签开始")
            
        # 检查命名空间
        if 'class' in content and 'namespace' not in content:
            warnings.append("提示: PHP类应定义在命名空间中")
            
        # 检查错误报告级别
        if 'error_reporting' not in content and 'function' in content:
            warnings.append("提示: 考虑设置适当的错误报告级别")
            
        return warnings
        
    def _check_kotlin_file(self, content: str) -> List[str]:
        """检查Kotlin文件"""
        warnings = []
        
        # 检查包声明
        if not re.search(r'^package\s+[\w.]+', content, re.MULTILINE):
            warnings.append("⚠️ Kotlin文件缺少package声明")
            
        # 检查空安全
        if '!!' in content:
            warnings.append("提示: 使用了非空断言(!!)，考虑使用更安全的方式处理空值")
            
        # 检查函数式API
        has_collections = 'List' in content or 'Map' in content or 'Set' in content
        if has_collections and not any(x in content for x in ['map', 'filter', 'forEach']):
            warnings.append("提示: 使用集合类但未利用Kotlin函数式API")
            
        return warnings
    
    def _has_header_guard(self, content: str) -> bool:
        """检查C/C++头文件是否有头文件保护"""
        # 检查传统的#ifndef保护
        if re.search(r'#ifndef\s+\w+\s+#define\s+\w+', content, re.DOTALL):
            return True
            
        # 检查#pragma once
        if '#pragma once' in content:
            return True
            
        return False
        
    def _is_python_version_hint(self, content: str, version: str) -> bool:
        """检查Python版本提示"""
        return f"# requires Python {version}" in content or f"# Python {version} required" in content

    def generate_report(self, processing_result: Dict) -> str:
        """生成变更报告"""
        report = []

        # 检查路径中的重复段
        has_duplicate_segments = False
        fixed_paths = {}
        
        # 检查主文件路径是否有重复段
        if hasattr(self.path_resolver, '_find_duplicate_path_segments'):
            main_path = processing_result.get('resolved_path', '')
            duplicates = self.path_resolver._find_duplicate_path_segments(main_path)
            if duplicates:
                has_duplicate_segments = True
                fixed_main_path = self.path_resolver._remove_duplicate_segments(main_path, duplicates)
                fixed_paths[main_path] = fixed_main_path
                
            # 检查附加文件
            for file_data in processing_result.get('additional_files', []):
                file_path = file_data.get('resolved_path', '')
                if file_path:
                    duplicates = self.path_resolver._find_duplicate_path_segments(file_path)
                    if duplicates:
                        has_duplicate_segments = True
                        fixed_file_path = self.path_resolver._remove_duplicate_segments(file_path, duplicates)
                        fixed_paths[file_path] = fixed_file_path

        # 文件信息
        ext = Path(processing_result['resolved_path']).suffix.lower()
        file_type = self.file_type_map.get(ext, "📄 文件")
        
        # 多文件处理
        if processing_result.get('is_multi_file', False):
            report.append(f"🔄 多文件变更 ({len(processing_result.get('additional_files', [])) + 1} 个文件)")
            report.append(f"主文件: {file_type} {processing_result['original_path']}")
            
            # 显示修正后的路径，如果发现路径重复段，显示修正结果
            resolved_path = processing_result['resolved_path']
            if resolved_path in fixed_paths:
                report.append(f"   → 修正为: {fixed_paths[resolved_path]}")
                report.append(f"   → 检测到路径重复段并已自动修正")
            elif processing_result['resolved_path'] != processing_result['original_path']:
                report.append(f"   → 修正为: {processing_result['resolved_path']}")
                
            report.append(f"   → 语言类型: {processing_result['language']}")
            
            # 附加文件
            for i, file_data in enumerate(processing_result.get('additional_files', [])):
                f_ext = Path(file_data['resolved_path']).suffix.lower()
                f_type = self.file_type_map.get(f_ext, "📄 文件")
                report.append(f"\n附加文件 #{i+1}: {f_type} {file_data['original_path']}")
                
                # 显示修正后的路径，处理重复段情况
                resolved_path = file_data['resolved_path']
                if resolved_path in fixed_paths:
                    report.append(f"   → 修正为: {fixed_paths[resolved_path]}")
                    report.append(f"   → 检测到路径重复段并已自动修正")
                elif file_data['resolved_path'] != file_data['original_path']:
                    report.append(f"   → 修正为: {file_data['resolved_path']}")
                    
                report.append(f"   → 语言类型: {file_data['language']}")
        else:
            # 单文件模式
            report.append(f"{file_type} 文件路径: {processing_result['original_path']}")
            
            # 如果检测到路径重复段，使用修正后的路径
            resolved_path = processing_result['resolved_path']
            if resolved_path in fixed_paths:
                report.append(f"   → 修正为: {fixed_paths[resolved_path]}")
                report.append(f"   → 检测到路径重复段并已自动修正")
            elif processing_result['resolved_path'] != processing_result['original_path']:
                report.append(f"   → 修正为: {processing_result['resolved_path']}")
                
            report.append(f"   → 语言类型: {processing_result['language']}")
            
        # 文件状态
        if processing_result.get('file_exists', False):
            if processing_result.get('has_content_changes', False):
                report.append("   → 状态: ⚠️ 将覆盖现有文件")
            else:
                report.append("   → 状态: ℹ️ 文件无变化")
        else:
            report.append("   → 状态: 🆕 新建文件")

            # 如果发现重复路径段，添加特殊警告
        if has_duplicate_segments:
            # 添加警告标题
            report.append("\n⚠️ 路径重复段警告:")
            # 添加警告说明，使用中文全角引号避免冲突
            report.append("  • 检测到路径中存在重复段，建议使用\"批量编辑路径\"工具修复")
            # 针对每个重复的原路径，给出简化后的建议
            for original, fixed in fixed_paths.items():
                report.append(f"  • 路径 '{original}' 可以简化为 '{fixed}'")

        # 风险操作
        if processing_result.get('risk_operations', []):
            report.append("\n🔴 风险操作:")
            for risk in processing_result['risk_operations']:
                # 检查风险操作中的路径是否包含重复段
                if "路径变更:" in risk or "创建新目录:" in risk:
                    parts = risk.split("->")
                    if len(parts) > 1 and parts[1].strip() in fixed_paths:
                        # 替换为修正后的路径
                        fixed_path = fixed_paths[parts[1].strip()]
                        risk = f"{parts[0]}-> {fixed_path}"
                report.append(f"  • {risk}")

        # 警告
        if processing_result['warnings']:
            report.append("\n⚠️ 警告:")
            for warning in processing_result['warnings']:
                # 检查警告中的路径是否包含重复段
                if "路径自动修正:" in warning:
                    parts = warning.split("→")
                    if len(parts) > 1 and parts[1].strip() in fixed_paths:
                        # 替换为修正后的路径
                        fixed_path = fixed_paths[parts[1].strip()]
                        warning = f"{parts[0]}→ {fixed_path}"
                report.append(f"  • {warning}")

        # 缺失导入
        if processing_result['missing_imports']:
            report.append("\n❌ 缺失导入:")
            for imp, suggestions in processing_result['missing_imports'].items():
                report.append(f"  • {imp}")
                if suggestions:
                    report.append("    可能替代方案:")
                    for sug in suggestions:
                        report.append(f"      - {sug}")

        # 确认提示
        if processing_result['requires_confirmation']:
            report.append("\n🚨 需要确认: 此变更包含风险操作，请仔细检查后再应用!")
            
        # 如果发现路径重复段，添加修复建议
        if has_duplicate_segments:
            report.append("\n💡 建议: 点击\"批量编辑路径\"按钮修复路径中的重复段")

        return "\n".join(report)
        
    def apply_change(self, processing_result: Dict) -> bool:
        """应用变更"""
        try:
            # 处理多文件情况
            if processing_result.get('is_multi_file', False):
                # 主文件
                success = self._apply_single_file_change(
                    processing_result['resolved_path'], 
                    processing_result['new_content'], 
                    processing_result['original_path']
                )
                
                if not success:
                    return False
                    
                # 附加文件
                for file_data in processing_result.get('additional_files', []):
                    file_success = self._apply_single_file_change(
                        file_data['resolved_path'], 
                        file_data['new_content'], 
                        file_data['original_path']
                    )
                    if not file_success:
                        logging.warning(f"附加文件 {file_data['resolved_path']} 应用失败")
                        
                return True
            else:
                # 单文件处理
                return self._apply_single_file_change(
                    processing_result['resolved_path'], 
                    processing_result['new_content'],
                    processing_result['original_path']
                )
        except Exception as e:
            logging.error(f"应用变更失败: {str(e)}")
            return False
            
    def _apply_single_file_change(self, resolved_path: str, new_content: str, original_path: str) -> bool:
        """应用单个文件变更"""
        try:
            full_path = self.project_root / resolved_path
            
            # 确保目录存在
            os.makedirs(full_path.parent, exist_ok=True)
            
            # 如果是Java文件，检查并修正包名
            if resolved_path.endswith('.java'):
                new_content = self._correct_java_package(new_content, resolved_path, original_path)
            
            # 写入文件
            with open(full_path, 'w', encoding='utf-8') as f:
                f.write(new_content)
                
            return True
        except Exception as e:
            logging.error(f"应用变更到 {resolved_path} 失败: {str(e)}")
            return False
            
    def _correct_java_package(self, content: str, resolved_path: str, original_path: str) -> str:
        """修正Java包名"""
        # 提取当前包名
        pkg_match = re.search(r'^package\s+([\w.]+)\s*;', content, re.MULTILINE)
        if not pkg_match:
            return content
            
        current_pkg = pkg_match.group(1)
        
        # 从路径中判断正确的包名
        path_parts = Path(resolved_path).parts
        java_idx = -1
        for i, part in enumerate(path_parts):
            if part == 'java':
                java_idx = i
                break
                
        if java_idx >= 0 and java_idx < len(path_parts) - 2:  # 确保java后还有至少两部分(包和文件名)
            # 从java之后到文件名之前的部分组成包名
            correct_pkg_parts = path_parts[java_idx + 1:-1]
            
            # 修复包名 - 规则：com.main是根目录
            # 检查com/main是否包含在路径中
            com_main_idx = -1
            for i, part in enumerate(correct_pkg_parts):
                if part == 'com' and i+1 < len(correct_pkg_parts) and correct_pkg_parts[i+1] == 'main':
                    com_main_idx = i
                    break
                    
            if com_main_idx >= 0:
                # 只保留com.main之后的包路径部分
                correct_pkg_parts = correct_pkg_parts[com_main_idx:] 
            
            correct_pkg = '.'.join(correct_pkg_parts)
            
            # 如果包名不同，进行替换
            if correct_pkg and correct_pkg != current_pkg:
                logging.info(f"自动修正Java包名: {current_pkg} -> {correct_pkg}")
                return content.replace(f"package {current_pkg};", f"package {correct_pkg};", 1)
                
        # 检查是否需要com.web到com.main的转换
        if current_pkg.startswith("com.web"):
            corrected_pkg = "com.main" + current_pkg[7:]
            return content.replace(f"package {current_pkg};", f"package {corrected_pkg};", 1)
            
        return content
        
    def create_backup(self, file_path: str) -> str:
        """创建文件备份"""
        try:
            full_path = self.project_root / file_path
            if not full_path.exists():
                return ""
                
            # 创建备份目录
            backup_dir = self.project_root / "backups"
            os.makedirs(backup_dir, exist_ok=True)
            
            # 生成备份文件名
            timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_file = backup_dir / f"{full_path.name}.{timestamp}.bak"
            
            # 复制文件
            with open(full_path, 'r', encoding='utf-8', errors='ignore') as src:
                with open(backup_file, 'w', encoding='utf-8') as dst:
                    dst.write(src.read())
                    
            return str(backup_file)
        except Exception as e:
            logging.error(f"创建备份失败: {str(e)}")
            return "" 

class EnhancedCodeReviewApp(tk.Tk):
    """增强的代码审查应用"""
    
    def __init__(self):
        super().__init__()
        self.title("多语言代码审查分析工具 v3.0")
        self.geometry("1000x800")
        
        # 初始化变量
        self.project_path = ""
        self.processor = None
        self.current_analysis = None
        self.backup_active = True
        self.is_analyzing = False
        self.multiple_files_data = []
        
        # 创建UI
        self._setup_ui()
        
        # 绑定关闭事件
        self.protocol("WM_DELETE_WINDOW", self._on_closing)
        
    def _setup_ui(self):
        """设置用户界面"""
        # 创建主框架
        main_frame = tk.Frame(self)
        main_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        # 项目路径选择
        path_frame = tk.Frame(main_frame)
        path_frame.pack(fill=tk.X, pady=5)
        tk.Label(path_frame, text="项目根目录:").pack(side=tk.LEFT)
        self.path_entry = tk.Entry(path_frame, width=80)
        self.path_entry.pack(side=tk.LEFT, expand=True, fill=tk.X, padx=5)
        tk.Button(path_frame, text="浏览...", command=self._browse_project).pack(side=tk.LEFT)
        
        # 语言和选项框架
        options_frame = tk.Frame(main_frame)
        options_frame.pack(fill=tk.X, pady=5)
        
        # 语言选择
        lang_frame = tk.Frame(options_frame)
        lang_frame.pack(side=tk.LEFT, fill=tk.X, expand=True)
        tk.Label(lang_frame, text="主要语言:").pack(side=tk.LEFT)
        self.lang_var = tk.StringVar(value="自动检测")
        langs = ["自动检测", "Java", "Python", "JavaScript", "TypeScript", "Go", "C++", "Vue", "微信小程序"]
        self.lang_combo = ttk.Combobox(lang_frame, textvariable=self.lang_var, values=langs, state="readonly", width=12)
        self.lang_combo.pack(side=tk.LEFT, padx=5)
        
        # 备份选项
        self.backup_var = tk.BooleanVar(value=True)
        backup_check = tk.Checkbutton(options_frame, text="创建备份", variable=self.backup_var)
        backup_check.pack(side=tk.LEFT, padx=20)
        
        # 自动修复选项
        self.autofix_var = tk.BooleanVar(value=True)
        autofix_check = tk.Checkbutton(options_frame, text="自动修复路径", variable=self.autofix_var)
        autofix_check.pack(side=tk.LEFT, padx=5)
        
        # AI模型选择
        ai_frame = tk.Frame(options_frame)
        ai_frame.pack(side=tk.LEFT, padx=20)
        tk.Label(ai_frame, text="AI模型:").pack(side=tk.LEFT)
        self.ai_model_var = tk.StringVar(value="gemma3:4b")
        ai_models = ["gemma3:4b", "gemma3:1b", "llama3:70b", "mixtral"]
        self.ai_model_combo = ttk.Combobox(ai_frame, textvariable=self.ai_model_var, values=ai_models, width=15)
        self.ai_model_combo.pack(side=tk.LEFT, padx=5)

        # 代码输入区
        input_frame = tk.Frame(main_frame)
        input_frame.pack(fill=tk.BOTH, expand=True, pady=5)
        tk.Label(input_frame, text="代码建议变更:").pack(anchor=tk.W)
        
        # 创建输入文本区
        self.code_input = scrolledtext.ScrolledText(input_frame, height=15, font=("Consolas", 10))
        self.code_input.pack(fill=tk.BOTH, expand=True)
        
        # 按钮区
        button_frame = tk.Frame(main_frame)
        button_frame.pack(fill=tk.X, pady=5)
        
        analyze_btn = tk.Button(button_frame, text="分析变更", command=self.analyze_changes, bg="#e7f3fe")
        analyze_btn.pack(side=tk.LEFT, padx=5)
        
        preview_btn = tk.Button(button_frame, text="预览变更", command=self.preview_changes)
        preview_btn.pack(side=tk.LEFT, padx=5)
        
        edit_paths_btn = tk.Button(button_frame, text="批量编辑路径", command=self._batch_edit_paths)
        edit_paths_btn.pack(side=tk.LEFT, padx=5)
        
        apply_btn = tk.Button(button_frame, text="应用变更", command=self.apply_changes, bg="#e0f7e0")
        apply_btn.pack(side=tk.LEFT, padx=5)
        
        clear_btn = tk.Button(button_frame, text="清除", command=self.clear_all)
        clear_btn.pack(side=tk.LEFT, padx=5)

        # 分析结果区
        output_frame = tk.Frame(main_frame)
        output_frame.pack(fill=tk.BOTH, expand=True, pady=5)
        tk.Label(output_frame, text="分析结果:").pack(anchor=tk.W)
        
        # 创建结果显示区
        self.result_text = scrolledtext.ScrolledText(output_frame, height=15, state=tk.DISABLED, font=("Consolas", 10))
        self.result_text.pack(fill=tk.BOTH, expand=True)
        
        # 配置结果区标签样式
        self.result_text.tag_configure("error", foreground="red", font=("Consolas", 10, "bold"))
        self.result_text.tag_configure("warning", foreground="orange")
        self.result_text.tag_configure("success", foreground="green")
        self.result_text.tag_configure("info", foreground="blue")
        self.result_text.tag_configure("link", foreground="blue", underline=1)
        
        # 状态栏
        self.status_var = tk.StringVar(value="就绪")
        status_bar = tk.Label(self, textvariable=self.status_var, bd=1, relief=tk.SUNKEN, anchor=tk.W)
        status_bar.pack(side=tk.BOTTOM, fill=tk.X)
        
        # 初始化标志
        self.is_analyzing = False

    def _browse_project(self):
        """浏览项目路径"""
        path = filedialog.askdirectory(title="选择项目根目录")
        if path:
            self.path_entry.delete(0, tk.END)
            self.path_entry.insert(0, path)
            self.project_path = path
            self.processor = CodeChangeProcessor(path)
            self.status_var.set(f"已加载项目: {path}")
            
            # 显示项目已加载信息
            self.show_output(f"✅ 已加载项目: {path}\n" +
                           f"主要语言: {self.lang_var.get()}\n" +
                           f"备份功能: {'启用' if self.backup_var.get() else '禁用'}\n" +
                           f"自动修复路径: {'启用' if self.autofix_var.get() else '禁用'}", tag="success")
            
            # 扫描项目结构
            self._scan_project_structure()
            
    def _scan_project_structure(self):
        """扫描项目结构"""
        if not self.project_path:
            return
            
        self.status_var.set("正在扫描项目结构...")
        
        # 在后台线程中执行扫描
        threading.Thread(target=self._do_scan_project, daemon=True).start()
        
    def _do_scan_project(self):
        """执行项目扫描"""
        try:
            # 扫描项目根目录结构
            dirs = []
            for root, directories, files in os.walk(self.project_path, topdown=True):
                if '.git' in directories:
                    directories.remove('.git')
                if 'node_modules' in directories:
                    directories.remove('node_modules')
                    
                # 限制深度
                rel_path = os.path.relpath(root, self.project_path)
                if rel_path != '.' and rel_path.count(os.sep) > 3:
                    continue
                    
                if rel_path != '.':
                    dirs.append(rel_path)
                
                # 限制目录数量
                if len(dirs) > 100:
                    break
                    
            # 显示扫描结果
            self.after(0, lambda: self.status_var.set(f"项目扫描完成，发现 {len(dirs)} 个目录"))
        except Exception as e:
            logging.error(f"扫描项目结构出错: {e}")
            self.after(0, lambda: self.status_var.set("项目扫描失败"))

    def analyze_changes(self):
        """分析代码变更"""
        if not self.project_path:
            messagebox.showerror("错误", "请先选择项目根目录")
            return
            
        # 获取代码输入
        code = self.code_input.get("1.0", tk.END).strip()
        if not code:
            messagebox.showerror("错误", "请输入要分析的代码")
            return
            
        # 检查是否有正在进行的分析
        if self.is_analyzing:
            messagebox.showinfo("提示", "分析正在进行中，请稍候...")
            return
            
        self.status_var.set("正在分析代码变更...")
        self.is_analyzing = True
        
        # 在后台线程中执行分析
        self.analysis_thread = threading.Thread(target=self._do_analyze, args=(code,), daemon=True)
        self.analysis_thread.start()
        
    def _do_analyze(self, code):
        """在后台线程中执行分析"""
        try:
            # 清除之前的多文件数据
            self.multiple_files_data = []
            
            # 解析文件路径和内容
            file_path, content = self._extract_file_path_content(code)
            if not file_path:
                self.after(0, lambda: self.show_output("❌ 无法解析文件路径", tag="error"))
                self.after(0, lambda: self.status_var.set("分析失败: 无法解析文件路径"))
                self.is_analyzing = False
                return
            
            # 将多文件数据传递给path_resolver
            if hasattr(self.processor, 'path_resolver') and self.multiple_files_data:
                self.processor.path_resolver.multiple_files_data = self.multiple_files_data
                
            # 处理变更
            result = self.processor.process_change(file_path, content)
            self.current_analysis = result
            
            # 如果是Java文件且包含com.web到com.main的转换，更新内容
            if file_path.endswith('.java') and "package com.web" in content:
                # 修正Java包名
                content_fixed = re.sub(r'package\s+com\.web', 'package com.main', content)
                result['new_content'] = content_fixed
                
                # 如果有多文件，也检查并更新附加文件
                if result.get('is_multi_file', False):
                    for i, file_data in enumerate(result.get('additional_files', [])):
                        if file_data['original_path'].endswith('.java') and "package com.web" in file_data['new_content']:
                            content_fixed = re.sub(r'package\s+com\.web', 'package com.main', file_data['new_content'])
                            result['additional_files'][i]['new_content'] = content_fixed
            
            # 生成报告
            report = self.processor.generate_report(result)
            
            # 在主线程中更新UI
            self.after(0, lambda: self.show_output(report))
            self.after(0, lambda: self.status_var.set(f"分析完成 - {file_path}"))
            
        except Exception as e:
            logging.exception("分析变更错误")
            self.after(0, lambda: self.show_output(f"❌ 分析失败: {str(e)}", tag="error"))
            self.after(0, lambda: self.status_var.set("分析失败"))
            
        finally:
            self.is_analyzing = False

    def preview_changes(self):
        """预览变更"""
        if not self.current_analysis:
            messagebox.showerror("错误", "请先分析变更")
            return
            
        # 创建预览窗口
        preview = tk.Toplevel(self)
        preview.title("变更预览")
        preview.geometry("1000x700")
        preview.grab_set()  # 模态窗口
        
        # 检查是否为多文件变更
        if self.current_analysis.get('is_multi_file', False):
            self._show_multi_file_preview(preview)
        else:
            self._show_single_file_preview(preview)
            
    def _show_single_file_preview(self, preview):
        """显示单文件预览"""
        # 原路径显示
        path_frame = tk.Frame(preview)
        path_frame.pack(fill=tk.X, padx=10, pady=5)
        original_path = self.current_analysis['original_path']
        resolved_path = self.current_analysis['resolved_path']
        
        if original_path != resolved_path:
            path_text = f"原始路径: {original_path}\n修正路径: {resolved_path}"
        else:
            path_text = f"文件路径: {original_path}"
            
        path_label = tk.Label(path_frame, text=path_text)
        path_label.pack(anchor=tk.W)
        
        # 添加路径编辑功能
        edit_frame = tk.Frame(path_frame)
        edit_frame.pack(fill=tk.X, pady=5)
        
        self.path_edit_var = tk.StringVar(value=resolved_path)
        path_edit = tk.Entry(edit_frame, textvariable=self.path_edit_var, width=80, state=tk.DISABLED)
        path_edit.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5)
        
        # 解锁和保存按钮
        self.unlock_btn = tk.Button(edit_frame, text="解锁路径", command=lambda: self._toggle_path_edit(path_edit))
        self.unlock_btn.pack(side=tk.LEFT, padx=5)
        
        # 对比区域
        paned = tk.PanedWindow(preview, orient=tk.HORIZONTAL)
        paned.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)
        
        # 原内容
        original_frame = tk.Frame(paned)
        tk.Label(original_frame, text="原始内容").pack()
        original_text = scrolledtext.ScrolledText(original_frame, wrap=tk.NONE)
        original_text.pack(fill=tk.BOTH, expand=True)
        
        # 填充原内容
        original_content = ""
        if self.current_analysis.get('file_exists', False):
            # 如果有保存的原始内容，直接使用
            if self.current_analysis.get('original_content'):
                original_content = self.current_analysis['original_content']
                original_text.insert("1.0", original_content)
            else:
                # 否则读取文件
                full_path = Path(self.project_path) / self.current_analysis['resolved_path']
                try:
                    with open(full_path, 'r', encoding='utf-8', errors='ignore') as f:
                        original_content = f.read()
                    original_text.insert("1.0", original_content)
                except Exception:
                    original_text.insert("1.0", "<无法读取原文件内容>")
        else:
            original_text.insert("1.0", "<新文件>")
            
        original_text.config(state=tk.DISABLED)
        
        # 新内容
        new_frame = tk.Frame(paned)
        tk.Label(new_frame, text="新内容 (支持编辑)").pack()
        new_text = scrolledtext.ScrolledText(new_frame, wrap=tk.NONE)
        new_text.pack(fill=tk.BOTH, expand=True)
        
        # 填充新内容并允许编辑
        new_text.insert("1.0", self.current_analysis['new_content'])
        # 允许编辑，支持Ctrl+Z撤销等操作
        new_text.focus_set()
        
        # 添加两个部分到paned窗口
        paned.add(original_frame)
        paned.add(new_frame)
        
        # 变化统计
        if self.current_analysis.get('file_exists', False):
            stats_frame = tk.Frame(preview)
            stats_frame.pack(fill=tk.X, padx=10, pady=5)
            
            # 简单统计变更
            old_lines = len(original_content.splitlines()) if original_content else 0
            new_lines = len(self.current_analysis['new_content'].splitlines())
            
            stats_text = f"统计: 原始行数: {old_lines}, 新行数: {new_lines}, "
            if old_lines > new_lines:
                stats_text += f"减少: {old_lines - new_lines} 行"
            elif new_lines > old_lines:
                stats_text += f"增加: {new_lines - old_lines} 行"
            else:
                stats_text += "行数无变化"
                
            tk.Label(stats_frame, text=stats_text).pack(anchor=tk.W)
        
        # 按钮区
        button_frame = tk.Frame(preview)
        button_frame.pack(fill=tk.X, padx=10, pady=5)
        
        close_btn = tk.Button(button_frame, text="关闭", command=preview.destroy)
        close_btn.pack(side=tk.RIGHT)
        
        # 添加撤销变更按钮
        if self.current_analysis.get('file_exists', False) and self.current_analysis.get('original_content'):
            revert_btn = tk.Button(button_frame, text="撤销变更", bg="#f7e0e0",
                                   command=lambda: self._revert_changes(preview))
            revert_btn.pack(side=tk.RIGHT, padx=5)
        
        # 修改应用变更按钮的功能，获取编辑框的最新内容
        apply_btn = tk.Button(button_frame, text="应用变更", bg="#e0f7e0",
                             command=lambda: self._apply_with_current_changes(preview, new_text))
        apply_btn.pack(side=tk.RIGHT, padx=5)
        
    def _show_multi_file_preview(self, preview):
        """显示多文件预览"""
        # 创建选项卡控件
        notebook = ttk.Notebook(preview)
        notebook.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)
        
        # 主文件选项卡
        main_tab = ttk.Frame(notebook)
        notebook.add(main_tab, text=f"主文件: {os.path.basename(self.current_analysis['resolved_path'])}")
        
        # 为主文件创建预览
        self._create_file_preview_tab(main_tab, self.current_analysis)
        
        # 附加文件选项卡
        for i, file_data in enumerate(self.current_analysis.get('additional_files', [])):
            file_tab = ttk.Frame(notebook)
            notebook.add(file_tab, text=f"文件 #{i+1}: {os.path.basename(file_data['resolved_path'])}")
            self._create_file_preview_tab(file_tab, file_data, is_additional=True, index=i)
            
        # 底部按钮区
        button_frame = tk.Frame(preview)
        button_frame.pack(fill=tk.X, padx=10, pady=5)
        
        close_btn = tk.Button(button_frame, text="关闭", command=preview.destroy)
        close_btn.pack(side=tk.RIGHT)
        
        apply_btn = tk.Button(button_frame, text="应用所有变更", bg="#e0f7e0",
                             command=lambda: self._apply_with_path_changes(preview))
        apply_btn.pack(side=tk.RIGHT, padx=5)
        
    def _create_file_preview_tab(self, tab, file_data, is_additional=False, index=None):
        """创建单个文件预览选项卡"""
        # 路径显示和编辑区
        path_frame = tk.Frame(tab)
        path_frame.pack(fill=tk.X, padx=5, pady=5)
        
        original_path = file_data['original_path']
        resolved_path = file_data['resolved_path']
        
        if original_path != resolved_path:
            path_text = f"原始路径: {original_path}\n修正路径: {resolved_path}"
        else:
            path_text = f"文件路径: {original_path}"
            
        path_label = tk.Label(path_frame, text=path_text)
        path_label.pack(anchor=tk.W)
        
        # 路径编辑框
        edit_frame = tk.Frame(path_frame)
        edit_frame.pack(fill=tk.X, pady=5)
        
        # 给每个文件创建对应的StringVar
        var_name = f"path_edit_var_{index}" if is_additional else "path_edit_var_main"
        setattr(self, var_name, tk.StringVar(value=resolved_path))
        var = getattr(self, var_name)
        
        path_edit = tk.Entry(edit_frame, textvariable=var, width=80, state=tk.DISABLED)
        path_edit.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5)
        
        # 解锁按钮
        btn_name = f"unlock_btn_{index}" if is_additional else "unlock_btn_main"
        btn = tk.Button(edit_frame, text="解锁路径", 
                       command=lambda e=path_edit: self._toggle_path_edit(e))
        setattr(self, btn_name, btn)
        btn.pack(side=tk.LEFT, padx=5)
        
        # 对比区域
        paned = tk.PanedWindow(tab, orient=tk.HORIZONTAL)
        paned.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # 原内容
        original_frame = tk.Frame(paned)
        tk.Label(original_frame, text="原始内容").pack()
        original_text = scrolledtext.ScrolledText(original_frame, wrap=tk.NONE)
        original_text.pack(fill=tk.BOTH, expand=True)
        
        # 填充原内容
        if file_data.get('file_exists', False):
            full_path = Path(self.project_path) / file_data['resolved_path']
            try:
                with open(full_path, 'r', encoding='utf-8', errors='ignore') as f:
                    original_content = f.read()
                original_text.insert("1.0", original_content)
            except Exception:
                original_text.insert("1.0", "<无法读取原文件内容>")
        else:
            original_text.insert("1.0", "<新文件>")
            
        original_text.config(state=tk.DISABLED)
        
        # 新内容
        new_frame = tk.Frame(paned)
        tk.Label(new_frame, text="新内容").pack()
        new_text = scrolledtext.ScrolledText(new_frame, wrap=tk.NONE)
        new_text.pack(fill=tk.BOTH, expand=True)
        
        # 填充新内容
        new_text.insert("1.0", file_data['new_content'])
        new_text.config(state=tk.DISABLED)
        
        # 添加两个部分到paned窗口
        paned.add(original_frame)
        paned.add(new_frame)
        
    def _toggle_path_edit(self, entry_widget):
        """切换路径编辑状态"""
        if entry_widget['state'] == tk.DISABLED:
            entry_widget.config(state=tk.NORMAL)
            if hasattr(self, 'unlock_btn'):
                self.unlock_btn.config(text="保存更改")
        else:
            entry_widget.config(state=tk.DISABLED)
            if hasattr(self, 'unlock_btn'):
                self.unlock_btn.config(text="解锁路径")
                
    def _apply_with_path_changes(self, preview_window):
        """应用路径变更并应用代码变更"""
        # 检查是否为多文件变更
        if self.current_analysis.get('is_multi_file', False):
            # 更新主文件路径
            if hasattr(self, 'path_edit_var_main'):
                new_path = self.path_edit_var_main.get()
                if new_path != self.current_analysis['resolved_path']:
                    self.current_analysis['resolved_path'] = new_path
                    
            # 更新附加文件路径
            for i, _ in enumerate(self.current_analysis.get('additional_files', [])):
                var_name = f'path_edit_var_{i}'
                if hasattr(self, var_name):
                    new_path = getattr(self, var_name).get()
                    if new_path != self.current_analysis['additional_files'][i]['resolved_path']:
                        self.current_analysis['additional_files'][i]['resolved_path'] = new_path
        else:
            # 单文件路径更新
            if hasattr(self, 'path_edit_var'):
                new_path = self.path_edit_var.get()
                if new_path != self.current_analysis['resolved_path']:
                    self.current_analysis['resolved_path'] = new_path
                    
        # 关闭预览窗口并应用变更
        preview_window.destroy()
        self.apply_changes()

    def apply_changes(self):
        """应用变更"""
        if not self.current_analysis:
            messagebox.showerror("错误", "请先分析变更")
            return
            
        # 确认应用
        if self.current_analysis.get('requires_confirmation', False):
            risk_info = "\n".join(self.current_analysis.get('risk_operations', []))
            confirmed = messagebox.askyesno(
                "确认风险操作", 
                f"此变更包含以下风险操作，确定要应用吗?\n\n{risk_info}"
            )
            if not confirmed:
                return
                
        # 备份文件
        if self.backup_var.get() and self.current_analysis.get('file_exists', False):
            backup_file = self.processor.create_backup(self.current_analysis['resolved_path'])
            if backup_file:
                self.status_var.set(f"已创建备份: {backup_file}")
        
        # 应用变更
        self.status_var.set("正在应用变更...")
        success = self.processor.apply_change(self.current_analysis)
        
        if success:
            self.show_output(f"✅ 成功应用变更: {self.current_analysis['resolved_path']}", tag="success")
            self.status_var.set("变更应用成功")
        else:
            self.show_output("❌ 应用变更失败", tag="error")
            self.status_var.set("变更应用失败")

    def clear_all(self):
        """清除所有输入和结果"""
        self.code_input.delete("1.0", tk.END)
        self.show_output("")
        self.current_analysis = None
        self.status_var.set("已清除")
        
    def check_imports_with_ai(self):
        """使用AI检查导入"""
        if not self.current_analysis:
            messagebox.showerror("错误", "请先分析变更")
            return
            
        self.status_var.set("正在使用AI检查导入...")
        
        # 在后台线程中执行检查
        threading.Thread(target=self._do_check_imports, daemon=True).start()
        
    def _do_check_imports(self):
        """在后台执行导入检查"""
        try:
            missing_imports = self.current_analysis.get('missing_imports', {})
            if not missing_imports:
                self.after(0, lambda: self.show_output("✅ 未发现缺失导入", tag="success"))
                self.after(0, lambda: self.status_var.set("导入检查完成 - 未发现问题"))
                return
                
            # 对每个缺失导入获取详细信息
            results = []
            for imp, _ in missing_imports.items():
                info = self._get_import_info_from_ai(imp)
                if info:
                    results.append(f"🔍 {imp}:\n{info}\n")
                    
            # 显示结果
            if results:
                self.after(0, lambda: self.show_output("📚 导入详细信息:\n\n" + "\n".join(results)))
                self.after(0, lambda: self.status_var.set("导入检查完成"))
            else:
                self.after(0, lambda: self.show_output("❌ 无法获取导入信息", tag="error"))
                self.after(0, lambda: self.status_var.set("导入检查失败"))
                
        except Exception as e:
            logging.exception("AI导入检查错误")
            self.after(0, lambda: self.show_output(f"❌ 导入检查失败: {str(e)}", tag="error"))
            self.after(0, lambda: self.status_var.set("导入检查失败"))

    def show_output(self, message, tag=None):
        """显示输出结果"""
        self.result_text.config(state=tk.NORMAL)
        self.result_text.delete("1.0", tk.END)
        
        if tag:
            self.result_text.insert("1.0", message, tag)
        else:
            # 处理不同行的标签
            lines = message.split('\n')
            for line in lines:
                if line.startswith("❌"):
                    self.result_text.insert(tk.END, line + "\n", "error")
                elif line.startswith("⚠️"):
                    self.result_text.insert(tk.END, line + "\n", "warning")
                elif line.startswith("✅"):
                    self.result_text.insert(tk.END, line + "\n", "success")
                elif line.startswith(("ℹ️", "🔍", "📚")):
                    self.result_text.insert(tk.END, line + "\n", "info")
                elif "路径:" in line or "修正为:" in line:
                    self.result_text.insert(tk.END, line + "\n", "link")
                else:
                    self.result_text.insert(tk.END, line + "\n")
                    
        self.result_text.config(state=tk.DISABLED)

    def _extract_file_path_content(self, code):
        """从代码中提取文件路径和内容"""
        # 检查是否包含多个文件
        multiple_files = self._extract_multiple_files(code)
        if multiple_files:
            # 如果有多个文件，返回第一个文件用于分析
            if multiple_files:
                first_file = multiple_files[0]
                self.multiple_files_data = multiple_files  # 保存多文件信息到实例变量
                return first_file['path'], first_file['content']
        
        # 1. 尝试通过多种格式提取文件路径
        path_patterns = [
            r'(?:^|\n)(?:#\s*)?文件路径[:：]\s*([^\n]+)',  # 文件路径：
            r'(?:^|\n)(?:#\s*)?文件名[:：]\s*([^\n]+)',    # 文件名：
            r'(?:^|\n)(?:#\s*)?File[:：]\s*([^\n]+)',      # File:
            r'(?:^|\n)(?:#\s*)?Path[:：]\s*([^\n]+)',      # Path:
            r'(?:^|\n)(?:#\s*)?#\s*([A-Za-z]:\\[^\n]+)',   # Windows绝对路径
            r'(?:^|\n)(?:#\s*)?#\s*([/][^\n]+)',          # Unix绝对路径
            r'(?:^|\n)(?:#\s*)?#\s*([a-zA-Z0-9_/\\]+\.(?:py|java|js|ts|go|cpp|c|h|hpp|vue|wxml|wxss|wxs|json|xml|md|php|rb|kt|swift))'  # 带扩展名的相对路径
        ]
        
        for pattern in path_patterns:
            path_match = re.search(pattern, code)
            if path_match:
                path = path_match.group(1).strip()
                # 去除路径部分，保留内容
                content_start = re.search(f'(?:^|\n)(?:#\s*)?{path_match.group(0)}\n', code)
                if content_start:
                    content = code[content_start.end():].strip()
                    return path, content
                return path, code
        
        # 2. 尝试提取Java包和类名
        java_match = re.search(r'package\s+([\w.]+);.*?public\s+class\s+(\w+)', code, re.DOTALL)
        if java_match:
            package = java_match.group(1)
            class_name = java_match.group(2)
            path = f"src/main/java/{package.replace('.', '/')}/{class_name}.java"
            return path, self._extract_java_code_block(code)
        
        # 3. 尝试从代码块中提取
        code_block_match = re.search(r'```(?:\w+)?\s*(?:#\s*)?(?:文件路径|文件名|File|Path)[:：]\s*([^\n]+)\n(.*?)```', code, re.DOTALL)
        if code_block_match:
            path = code_block_match.group(1).strip()
            content = code_block_match.group(2).strip()
            return path, content
        
        # 4. 尝试从标准格式的三个反引号中提取
        standard_blocks = re.findall(r'```(?:java|python|javascript|go|cpp|c|ts|html|css|vue|json|xml)?\s*\n(.*?)```', code, re.DOTALL)
        if standard_blocks:
            # 假设第一个代码块是要保存的内容
            content = standard_blocks[0].strip()
            
            # 尝试从周围文本推断路径
            filename_match = re.search(r'[文件名文件路径File Path][:：]\s*(\S+)', code)
            if filename_match:
                return filename_match.group(1).strip(), content
                
            # 尝试从代码内容推断Java路径
            java_pkg_match = re.search(r'package\s+([\w.]+);', content)
            java_class_match = re.search(r'public\s+class\s+(\w+)', content)
            if java_pkg_match and java_class_match:
                package = java_pkg_match.group(1)
                class_name = java_class_match.group(1)
                path = f"src/main/java/{package.replace('.', '/')}/{class_name}.java"
                return path, content
                
        # 5. 尝试从Python模块注释中提取
        python_module_match = re.search(r'^#\s*module[:：]\s*([\w.]+)', code, re.MULTILINE)
        if python_module_match:
            module = python_module_match.group(1)
            path = f"{module.replace('.', '/')}.py"
            return path, code
            
        # 6. 尝试从Go包声明中提取
        go_package_match = re.search(r'^package\s+(\w+)', code, re.MULTILINE)
        if go_package_match:
            package = go_package_match.group(1)
            path = f"src/{package}/main.go"
            return path, code
            
        # 如果都没找到，使用AI帮助提取
        try:
            path = self._ask_ai_for_path(code[:500])  # 只发送前500个字符
            if path:
                return path, self._extract_code_content(code)
        except Exception as e:
            logging.error(f"AI路径提取失败: {str(e)}")
            
        # 如果所有方法都失败，返回None
        return None, code
        
    def _extract_java_code_block(self, code):
        """从完整文本中提取Java代码块内容"""
        # 如果已经是代码块格式，直接返回
        if code.strip().startswith('package ') and '}' in code:
            return code
            
        # 尝试从markdown代码块中提取
        java_block_match = re.search(r'```(?:java)?\s*\n(package[\s\S]*?(?:class|interface|enum)[\s\S]*?})\s*```', code, re.DOTALL)
        if java_block_match:
            return java_block_match.group(1)
            
        # 尝试提取package到最后一个大括号的内容
        full_code_match = re.search(r'(package[\s\S]*?(?:class|interface|enum)[\s\S]*?})\s*$', code, re.DOTALL)
        if full_code_match:
            return full_code_match.group(1)
            
        return code
        
    def _extract_code_content(self, code):
        """从文本中提取代码内容，跳过注释和描述"""
        # 尝试从代码块中提取
        code_block_match = re.search(r'```(?:\w+)?\s*\n(.*?)```', code, re.DOTALL)
        if code_block_match:
            return code_block_match.group(1).strip()
            
        # 尝试删除文档头部的描述
        lines = code.split('\n')
        code_start = 0
        for i, line in enumerate(lines):
            if line.strip() and not line.startswith('#') and not line.startswith('//') and not line.startswith('/*'):
                code_start = i
                break
                
        return '\n'.join(lines[code_start:])
        
    def _extract_multiple_files(self, code):
        """检测并提取多个文件"""
        files = []
        
        # 1. 检查是否使用'---'分隔多个文件定义
        if '---' in code:
            # 按分隔符拆分代码块
            sections = re.split(r'-{3,}', code)
            
            for section in sections:
                if not section.strip():
                    continue
                
                # 从每个部分提取文件路径和内容
                file_info = self._extract_file_info_from_section(section)
                if file_info:
                    files.append(file_info)
        
        # 2. 如果分隔符方法未找到，尝试查找标准格式的文件路径标记和代码块
        if not files:
            # 查找文件路径标记和代码块
            file_blocks = re.finditer(r'###\s*文件路径[:：]\s*([^\n]+)\s*```(?:\w+)?\s*\n(.*?)```', code, re.DOTALL)
            for match in file_blocks:
                files.append({
                    'path': match.group(1).strip(),
                    'content': match.group(2).strip()
                })
                
            # 查找其他格式的文件块
            if not files:
                file_blocks = re.finditer(r'文件(?:路径|名)[:：]\s*([^\n]+)\s*```(?:\w+)?\s*\n(.*?)```', code, re.DOTALL)
                for match in file_blocks:
                    files.append({
                        'path': match.group(1).strip(),
                        'content': match.group(2).strip()
                    })
            
            # 识别Markdown格式的文件路径表示，如"# 文件路径：src/main/java/com/main/dto/CategoryDto.java"
            if not files:
                md_path_blocks = re.finditer(r'#\s*文件路径[:：]\s*([^\n]+)[\n\s]+(.*?)(?=(?:\Z|^\s*#))', code, re.DOTALL | re.MULTILINE)
                for match in md_path_blocks:
                    content = match.group(2).strip()
                    # 如果内容被代码块包裹，提取代码块内容
                    code_match = re.search(r'```(?:\w+)?\s*\n(.*?)```', content, re.DOTALL)
                    if code_match:
                        content = code_match.group(1).strip()
                    files.append({
                        'path': match.group(1).strip(),
                        'content': content
                    })
                    
            # 识别Java注释格式，如"// mapper/admin/CouponMapper.java"
            if not files:
                java_comment_blocks = re.finditer(r'//\s*((?:[\w/.-]+)?\.java)\s*\n(package[\s\S]*?)(?=(?:\Z|^\s*//\s*[\w/.-]+\.(?:java|xml)))', code, re.DOTALL | re.MULTILINE)
                for match in java_comment_blocks:
                    files.append({
                        'path': match.group(1).strip(),
                        'content': match.group(2).strip()
                    })
                    
            # 识别XML注释格式，如"<!-- resources/mapper/admin/CouponMapper.xml -->"
            if not files:
                xml_comment_blocks = re.finditer(r'<!--\s*((?:[\w/.-]+)?\.xml)\s*-->\s*\n([\s\S]*?)(?=(?:\Z|^\s*<!--\s*[\w/.-]+\.xml))', code, re.DOTALL | re.MULTILINE)
                for match in xml_comment_blocks:
                    files.append({
                        'path': match.group(1).strip(),
                        'content': match.group(2).strip()
                    })
            
            # Java专用格式识别
            if not files:
                java_blocks = re.finditer(r'###\s*([^#\n]+\.java)\s*```(?:java)?\s*\n(.*?)```', code, re.DOTALL)
                for match in java_blocks:
                    # 从内容提取包名
                    content = match.group(2).strip()
                    pkg_match = re.search(r'package\s+([\w.]+);', content)
                    if pkg_match:
                        package = pkg_match.group(1)
                        # 将路径和包名结合
                        file_name = match.group(1).strip()
                        path = f"src/main/java/{package.replace('.', '/')}/{os.path.basename(file_name)}"
                        files.append({
                            'path': path,
                            'content': content
                        })
                    else:
                        files.append({
                            'path': match.group(1).strip(),
                            'content': content
                        })
        
        # 如果只有一种文件类型（如全部是Java），自动设置多文件标志
        if len(files) > 1:
            # 检查是否都是同一类型
            extensions = set(Path(f['path']).suffix for f in files)
            if len(extensions) == 1:
                # 同一类型文件，可能是批量生成的实体类
                logging.info(f"检测到多个{list(extensions)[0]}文件: {len(files)}个")
            
            # 自动检测包名一致性
            if all(f['path'].endswith('.java') for f in files):
                # 提取包名
                packages = []
                for f in files:
                    pkg_match = re.search(r'package\s+([\w.]+);', f['content'])
                    if pkg_match:
                        packages.append(pkg_match.group(1))
                
                # 检查包名是否一致
                if packages and len(set(packages)) == 1:
                    logging.info(f"所有Java文件使用相同包名: {packages[0]}")
            
        return files
        
    def _extract_file_info_from_section(self, section):
        """从代码块部分提取文件信息"""
        section = section.strip()
        if not section:
            return None
            
        # 查找文件路径标记
        path_match = re.search(r'(?:###\s*)?文件路径[:：]\s*([^\n]+)', section)
        if not path_match:
            # 尝试其他常见格式
            path_match = re.search(r'###\s*([^#\n]+\.\w+)', section)
            if not path_match:
                return None
                
        file_path = path_match.group(1).strip()
        
        # 查找代码块
        code_match = re.search(r'```(?:\w+)?\s*\n(.*?)```', section, re.DOTALL)
        if code_match:
            content = code_match.group(1).strip()
        else:
            # 如果没有代码块标记，尝试使用路径后面的所有内容
            path_pos = section.find(file_path)
            if path_pos >= 0:
                remaining = section[path_pos + len(file_path):].strip()
                # 去除可能的前导部分
                content_start = re.search(r'(?:package|import|/\*\*|public|class|interface)\s', remaining)
                if content_start:
                    content = remaining[content_start.start():].strip()
                else:
                    content = remaining
            else:
                return None
                
        # 如果是Java文件，检查并处理包名路径
        if file_path.endswith('.java'):
            pkg_match = re.search(r'package\s+([\w.]+);', content)
            if pkg_match:
                package = pkg_match.group(1)
                
                # 如果路径不包含包信息，添加标准Java路径
                if '/' not in file_path:
                    file_path = f"src/main/java/{package.replace('.', '/')}/{file_path}"
                elif not re.search(fr'{package.replace(".", "/")}', file_path):
                    # 文件路径中没有包路径
                    dir_path = os.path.dirname(file_path)
                    file_name = os.path.basename(file_path)
                    if not dir_path or dir_path == '.':
                        file_path = f"src/main/java/{package.replace('.', '/')}/{file_name}"
                    else:
                        file_path = f"{dir_path}/{package.replace('.', '/')}/{file_name}"
                        
        return {
            'path': file_path,
            'content': content
        }
        
    def _ask_ai_for_path(self, code_snippet):
        """询问AI获取文件路径"""
        try:
            prompt = f"""请分析以下代码片段，判断它应该保存在什么文件路径下:
```
{code_snippet}
```
只需返回一个文件路径，不要有任何解释。"""

            result = subprocess.run([
                "curl", self.ai_api_url,
                "-d", f'{{"model": "{self.ai_model_var.get()}", "messages": [{{"role": "user", "content": "{prompt}"}}]}}'
            ], capture_output=True, text=True)

            if result.returncode == 0 and result.stdout:
                # 尝试解析结果
                try:
                    response_data = json.loads(result.stdout)
                    content = response_data.get("message", {}).get("content", "")
                    # 提取路径
                    path_match = re.search(r'[\w/.-]+\.\w+', content)
                    if path_match:
                        return path_match.group(0)
                except:
                    # 直接尝试从文本中提取路径
                    path_match = re.search(r'[\w/.-]+\.\w+', result.stdout)
                    if path_match:
                        return path_match.group(0)
        except Exception as e:
            logging.error(f"AI路径提取失败: {str(e)}")
            
        return None
        
    def _get_import_info_from_ai(self, import_name):
        """从AI获取导入信息"""
        try:
            # 构建提示词
            prompt = f"""请提供关于'{import_name}'的详细信息：
1. 这个导入/包/模块的主要功能是什么？
2. 它通常在什么情况下使用？
3. 有没有替代方案？
4. 提供一个简单的使用示例。

请简洁回答，控制在200字以内。"""

            # 调用本地AI API
            result = subprocess.run([
                "curl", self.ai_api_url,
                "-d", f'{{"model": "{self.ai_model_var.get()}", "messages": [{{"role": "user", "content": "{prompt}"}}]}}'
            ], capture_output=True, text=True)

            if result.returncode == 0 and result.stdout:
                try:
                    response_data = json.loads(result.stdout)
                    content = response_data.get("message", {}).get("content", "")
                    return content.strip()
                except:
                    return None
        except Exception as e:
            logging.error(f"获取导入信息失败: {e}")
            
        return None
        
    def _on_closing(self):
        """关闭窗口时的处理"""
        if self.is_analyzing:
            confirmed = messagebox.askyesno("确认", "分析正在进行中，确定要退出吗？")
            if not confirmed:
                return
                
        self.destroy()

    def _batch_edit_paths(self):
        """批量编辑路径窗口"""
        if not self.current_analysis:
            messagebox.showerror("错误", "请先分析变更")
            return
        
        # 获取所有需要处理的文件路径
        files = []
        if self.current_analysis.get('resolved_path'):
            files.append(self.current_analysis['resolved_path'])
        if self.current_analysis.get('is_multi_file', False):
            for file_data in self.current_analysis.get('additional_files', []):
                if file_data.get('resolved_path'):
                    files.append(file_data['resolved_path'])
                
        if not files:
            messagebox.showinfo("提示", "没有需要编辑的文件路径")
            return
            
        # 创建批量编辑窗口
        edit_window = tk.Toplevel(self)
        edit_window.title("批量路径编辑")
        edit_window.geometry("900x700")
        edit_window.grab_set()  # 模态窗口
        
        # 创建路径编辑界面
        tk.Label(edit_window, text="修改多个文件的路径：", font=("Arial", 12, "bold")).pack(pady=10, padx=10, anchor=tk.W)
        
        # 检测重复段
        duplicates_found = False
        for path in files:
            if hasattr(self.processor, 'path_resolver'):
                duplicates = self.processor.path_resolver._find_duplicate_path_segments(path)
                if duplicates:
                    duplicates_found = True
                    break
                    
        if duplicates_found:
            warn_frame = tk.Frame(edit_window, bg="#fff3cd", bd=1, relief=tk.SOLID)
            warn_frame.pack(fill=tk.X, padx=10, pady=5)
            tk.Label(warn_frame, text="⚠️ 检测到路径中存在重复段，建议进行修正", 
                     bg="#fff3cd", fg="#856404", font=("Arial", 10, "bold")).pack(pady=5, padx=5)
        
        # 分析公共路径前缀 - 使用os.path.commonpath获取最准确的共同前缀
        if len(files) > 1:
            common_prefix = os.path.commonpath(files)
        else:
            common_prefix = os.path.dirname(files[0])
        
        if not common_prefix:
            common_prefix = ""
            
        # 创建根目录编辑框
        root_frame = tk.Frame(edit_window)
        root_frame.pack(fill=tk.X, padx=10, pady=5)
        
        tk.Label(root_frame, text="项目根目录:", width=12, anchor=tk.W).pack(side=tk.LEFT)
        root_var = tk.StringVar(value=self.project_path)
        root_entry = tk.Entry(root_frame, textvariable=root_var, width=70)
        root_entry.pack(side=tk.LEFT, padx=5, fill=tk.X, expand=True)
        
        # 创建公共前缀编辑框
        prefix_frame = tk.Frame(edit_window)
        prefix_frame.pack(fill=tk.X, padx=10, pady=5)
        
        tk.Label(prefix_frame, text="公共路径前缀:", width=12, anchor=tk.W).pack(side=tk.LEFT)
        prefix_var = tk.StringVar(value=common_prefix)
        prefix_entry = tk.Entry(prefix_frame, textvariable=prefix_var, width=70)
        prefix_entry.pack(side=tk.LEFT, padx=5, fill=tk.X, expand=True)
        
        # 创建完整路径显示框
        full_path_frame = tk.Frame(edit_window)
        full_path_frame.pack(fill=tk.X, padx=10, pady=5)
        
        tk.Label(full_path_frame, text="完整目标路径:", width=12, anchor=tk.W).pack(side=tk.LEFT)
        full_path_var = tk.StringVar()
        full_path_entry = tk.Entry(full_path_frame, textvariable=full_path_var, width=70, state='readonly')
        full_path_entry.pack(side=tk.LEFT, padx=5, fill=tk.X, expand=True)
        
        # 当根目录或前缀变更时，更新完整路径显示
        def update_full_path(*args):
            try:
                root = root_var.get()
                prefix = prefix_var.get()
                if root and prefix:
                    if os.path.isabs(prefix):
                        full_path = prefix
                    else:
                        full_path = os.path.normpath(os.path.join(root, prefix))
                    full_path_var.set(full_path)
            except Exception as e:
                logging.error(f"计算完整路径出错: {e}")
                
        root_var.trace("w", update_full_path)
        prefix_var.trace("w", update_full_path)
        
        # 初始化完整路径
        update_full_path()
        
        # 创建Java包名编辑选项
        java_frame = tk.Frame(edit_window)
        java_frame.pack(fill=tk.X, padx=10, pady=5)
        
        # 是否自动将Java包名从com.web改为com.main
        auto_fix_pkg = tk.BooleanVar(value=True)
        pkg_check = tk.Checkbutton(java_frame, text="自动修正Java包名 (com.web -> com.main)", variable=auto_fix_pkg)
        pkg_check.pack(anchor=tk.W)
        
        # 自动修复重复路径段选项
        auto_fix_dups = tk.BooleanVar(value=True)
        dups_check = tk.Checkbutton(java_frame, text="自动修复路径中的重复段", variable=auto_fix_dups)
        dups_check.pack(anchor=tk.W)
        
        # 创建路径列表框架
        list_frame = tk.LabelFrame(edit_window, text="文件列表")
        list_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)
        
        # 创建路径列表框
        path_list = tk.Listbox(list_frame, width=80, height=10, selectmode=tk.SINGLE)
        path_list.pack(fill=tk.BOTH, expand=True, side=tk.LEFT, padx=5, pady=5)
        
        # 添加滚动条
        scrollbar = tk.Scrollbar(list_frame, orient=tk.VERTICAL, command=path_list.yview)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y, pady=5)
        path_list.config(yscrollcommand=scrollbar.set)
        
        # 填充文件列表
        for file_path in files:
            path_list.insert(tk.END, file_path)
            
        # 单个文件编辑框架
        edit_label_frame = tk.LabelFrame(edit_window, text="单个文件编辑")
        edit_label_frame.pack(fill=tk.X, padx=10, pady=5)
        
        edit_frame = tk.Frame(edit_label_frame)
        edit_frame.pack(fill=tk.X, padx=5, pady=5)
        
        tk.Label(edit_frame, text="选中文件路径:", width=12, anchor=tk.W).pack(side=tk.LEFT)
        selected_path_var = tk.StringVar()
        selected_path_entry = tk.Entry(edit_frame, textvariable=selected_path_var, width=70)
        selected_path_entry.pack(side=tk.LEFT, padx=5, fill=tk.X, expand=True)
        
        # 按钮区
        btn_frame = tk.Frame(edit_label_frame)
        btn_frame.pack(fill=tk.X, padx=5, pady=5)
        
        # 当选择项变化时，更新选中路径
        def on_select(event):
            if path_list.curselection():
                index = path_list.curselection()[0]
                selected_path_var.set(path_list.get(index))
                
        path_list.bind('<<ListboxSelect>>', on_select)
        
        # 更新选中文件路径
        def update_selected_path():
            if path_list.curselection():
                index = path_list.curselection()[0]
                new_path = selected_path_var.get()
                path_list.delete(index)
                path_list.insert(index, new_path)
                path_list.selection_set(index)
                
        update_btn = tk.Button(btn_frame, text="更新选中路径", command=update_selected_path)
        update_btn.pack(side=tk.LEFT, padx=5)
        
        # 自动修复选中路径
        def auto_fix_selected_path():
            if path_list.curselection() and auto_fix_dups.get():
                index = path_list.curselection()[0]
                path = path_list.get(index)
                if hasattr(self.processor, 'path_resolver'):
                    duplicates = self.processor.path_resolver._find_duplicate_path_segments(path)
                    if duplicates:
                        fixed_path = self.processor.path_resolver._remove_duplicate_segments(path, duplicates)
                        selected_path_var.set(fixed_path)
                        path_list.delete(index)
                        path_list.insert(index, fixed_path)
                        path_list.selection_set(index)
                        messagebox.showinfo("路径修复", f"已修复路径中的重复段:\n{path}\n->\n{fixed_path}")
                    else:
                        messagebox.showinfo("路径修复", "选中路径没有检测到重复段")
                        
        fix_btn = tk.Button(btn_frame, text="修复选中路径", command=auto_fix_selected_path)
        fix_btn.pack(side=tk.LEFT, padx=5)
        
        # 应用批量更改
        def apply_prefix_change():
            old_prefix = common_prefix
            new_prefix = prefix_var.get()
            
            if old_prefix and new_prefix and old_prefix != new_prefix:
                for i in range(path_list.size()):
                    old_path = path_list.get(i)
                    if old_path.startswith(old_prefix):
                        # 替换前缀
                        new_path = os.path.normpath(os.path.join(new_prefix, os.path.relpath(old_path, old_prefix)))
                        path_list.delete(i)
                        path_list.insert(i, new_path)
            
        apply_prefix_btn = tk.Button(prefix_frame, text="应用前缀变更", command=apply_prefix_change)
        apply_prefix_btn.pack(side=tk.RIGHT)
        
        # 自动修复所有路径
        def auto_fix_all_paths():
            if not auto_fix_dups.get():
                return
                
            fixed_count = 0
            for i in range(path_list.size()):
                path = path_list.get(i)
                if hasattr(self.processor, 'path_resolver'):
                    duplicates = self.processor.path_resolver._find_duplicate_path_segments(path)
                    if duplicates:
                        fixed_path = self.processor.path_resolver._remove_duplicate_segments(path, duplicates)
                        path_list.delete(i)
                        path_list.insert(i, fixed_path)
                        fixed_count += 1
                        
            if fixed_count > 0:
                messagebox.showinfo("批量修复", f"已修复 {fixed_count} 个路径中的重复段")
            else:
                messagebox.showinfo("批量修复", "没有检测到需要修复的路径")
                
        fix_all_btn = tk.Button(prefix_frame, text="修复所有路径", command=auto_fix_all_paths)
        fix_all_btn.pack(side=tk.RIGHT, padx=5)
        
        # 恢复默认路径
        def restore_original_paths():
            path_list.delete(0, tk.END)
            
            # 填充原始文件路径
            if self.current_analysis.get('original_path'):
                path_list.insert(tk.END, self.current_analysis['original_path'])
                
            if self.current_analysis.get('is_multi_file', False):
                for file_data in self.current_analysis.get('additional_files', []):
                    if file_data.get('original_path'):
                        path_list.insert(tk.END, file_data['original_path'])
                        
        restore_btn = tk.Button(btn_frame, text="恢复原始路径", command=restore_original_paths)
        restore_btn.pack(side=tk.LEFT, padx=5)
        
        # 批量应用路径变更
        def apply_all_path_changes():
            # 检查是否需要修复重复路径段
            if auto_fix_dups.get():
                auto_fix_all_paths()
                
            # 更新主文件路径
            new_paths = [path_list.get(i) for i in range(path_list.size())]
            if new_paths:
                # 路径重复段的最终检查与修复
                if hasattr(self.processor, 'path_resolver'):
                    for i, path in enumerate(new_paths):
                        duplicates = self.processor.path_resolver._find_duplicate_path_segments(path)
                        if duplicates:
                            new_paths[i] = self.processor.path_resolver._remove_duplicate_segments(path, duplicates)
                
                self.current_analysis['resolved_path'] = new_paths[0]
                
                # 更新附加文件路径
                if self.current_analysis.get('is_multi_file', False) and len(new_paths) > 1:
                    for i, new_path in enumerate(new_paths[1:]):
                        if i < len(self.current_analysis.get('additional_files', [])):
                            self.current_analysis['additional_files'][i]['resolved_path'] = new_path
                            
            # 更新项目根目录
            new_root = root_var.get()
            if new_root and new_root != self.project_path:
                self.project_path = new_root
                self.path_entry.delete(0, tk.END)
                self.path_entry.insert(0, new_root)
                self.processor = CodeChangeProcessor(new_root)
                
            # 自动修复Java包名
            if auto_fix_pkg.get():
                self._auto_fix_java_packages()
                
            # 关闭编辑窗口
            edit_window.destroy()
            
            # 刷新分析结果
            self.analyze_changes()
            
        # 底部按钮区
        button_frame = tk.Frame(edit_window)
        button_frame.pack(fill=tk.X, padx=10, pady=10)
        
        cancel_btn = tk.Button(button_frame, text="取消", command=edit_window.destroy)
        cancel_btn.pack(side=tk.RIGHT, padx=5)
        
        apply_btn = tk.Button(button_frame, text="应用所有变更", bg="#e0f7e0", 
                             font=("Arial", 10, "bold"), command=apply_all_path_changes)
        apply_btn.pack(side=tk.RIGHT, padx=5)
        
    def _auto_fix_java_packages(self):
        """自动修正Java文件的包名"""
        # 处理主文件
        if self.current_analysis['original_path'].endswith('.java'):
            content = self.current_analysis['new_content']
            if "package com.web" in content:
                content = re.sub(r'package\s+com\.web', 'package com.main', content)
                self.current_analysis['new_content'] = content
                
        # 处理附加文件
        for i, file_data in enumerate(self.current_analysis.get('additional_files', [])):
            if file_data['original_path'].endswith('.java'):
                content = file_data['new_content']
                if "package com.web" in content:
                    content = re.sub(r'package\s+com\.web', 'package com.main', content)
                    self.current_analysis['additional_files'][i]['new_content'] = content

    def _apply_with_current_changes(self, preview_window, text_widget=None):
        """应用当前编辑的路径和内容变更"""
        # 更新路径
        if hasattr(self, 'path_edit_var'):
            new_path = self.path_edit_var.get()
            if new_path != self.current_analysis['resolved_path']:
                self.current_analysis['resolved_path'] = new_path
        
        # 更新新内容（如果文本框可编辑）
        if text_widget:
            new_content = text_widget.get("1.0", tk.END)
            # 比较内容是否有变化
            if new_content.strip() != self.current_analysis['new_content'].strip():
                # 检查是否超过5行变更
                orig_lines = len(self.current_analysis['new_content'].strip().split('\n'))
                new_lines = len(new_content.strip().split('\n'))
                line_diff = abs(new_lines - orig_lines)
                
                if line_diff > 5:
                    if not messagebox.askyesno("警告", 
                                            f"检测到较大变更：{line_diff}行\n是否仍要应用变更？"):
                        return
                
                self.current_analysis['new_content'] = new_content
        
        # 关闭预览窗口
        preview_window.destroy()
        
        # 应用变更
        self.apply_changes()

    def _revert_changes(self, preview_window):
        """撤销变更，恢复到原始文件状态"""
        if not messagebox.askyesno("确认", "确定要撤销所有变更吗？"):
            return
            
        # 如果有原始内容，直接恢复
        if self.current_analysis.get('original_content'):
            self.current_analysis['new_content'] = self.current_analysis['original_content']
            
        # 关闭预览窗口
        preview_window.destroy()
        
        # 提示用户
        messagebox.showinfo("撤销成功", "已恢复到原始文件状态")


if __name__ == "__main__":
    app = EnhancedCodeReviewApp()
    app.mainloop() 
    app.mainloop() 