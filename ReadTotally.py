import os
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import time
import shutil
import threading

# 全局排除设置
EXCLUDED_FOLDERS = [".idea", ".git", ".mvn", "node_modules",".vscode","db_rag_cumulative","__pycache__",".venv",".cursor",".kiro"]
EXCLUDED_FILES = [".gitignore",".env"]
EXCLUDED_SUFFIX = [ ".ico",".jpg",".JPG",".json",".xml",".png",".mp4",".jpeg",".pth",".pyc",".pt"]

def parse_gitignore(gitignore_path):
    """解析 .gitignore 文件，返回需要排除的文件夹、文件和后缀

    参数:
    - gitignore_path: .gitignore 文件路径

    返回:
    - tuple: (folders_to_exclude, files_to_exclude, suffixes_to_exclude)
    """
    folders_to_exclude = set()
    files_to_exclude = set()
    suffixes_to_exclude = set()

    if not os.path.exists(gitignore_path):
        return folders_to_exclude, files_to_exclude, suffixes_to_exclude

    try:
        with open(gitignore_path, 'r', encoding='utf-8') as file:
            for line in file:
                line = line.strip()

                # 跳过空行和注释
                if not line or line.startswith('#'):
                    continue

                # 处理通配符模式 *.ext
                if line.startswith('*.') and line.count('*') == 1 and not line[2:].startswith('.'):
                    suffix = '.' + line[2:].lower()  # 去掉 *，保留 .ext 并转为小写
                    if suffix not in [s.lower() for s in EXCLUDED_SUFFIX]:  # 避免与现有冲突
                        suffixes_to_exclude.add(suffix)
                    continue

                # 处理包含路径分隔符的模式
                if '/' in line:
                    if line.endswith('/'):
                        # 以 / 结尾的文件夹模式，如 build/
                        folder_name = line[:-1]
                        if '/' in folder_name:
                            # 路径模式，如 src/build/，提取最后一部分
                            folder_name = folder_name.split('/')[-1]
                        if folder_name and not folder_name.startswith('.') and '*' not in folder_name and '?' not in folder_name:
                            folders_to_exclude.add(folder_name)
                    else:
                        # 带路径的文件模式，如 logs/error.log，提取文件名
                        file_name = line.split('/')[-1]
                        if file_name and '.' in file_name and not file_name.startswith('.') and '*' not in file_name and '?' not in file_name:
                            files_to_exclude.add(file_name)
                    continue

                # 处理不带路径分隔符的模式
                if '*' in line or '?' in line:
                    # 跳过复杂的通配符模式
                    continue

                # 判断是文件夹还是文件（基于是否有扩展名）
                if '.' in line:
                    # 包含点，可能是文件
                    if not line.startswith('.'):
                        files_to_exclude.add(line)
                else:
                    # 不包含点，可能是文件夹
                    if not line.startswith('.'):
                        folders_to_exclude.add(line)

    except Exception as e:
        print(f"解析 .gitignore 文件时出错: {e}")

    return folders_to_exclude, files_to_exclude, suffixes_to_exclude

# 多语言资源
languages = {
    'en': {
        'title': 'File Processor',
        'select_language': 'Select Language',
        'select_output': 'Select Output Folder',
        'select_all_file': 'Process Single File',
        'select_all_folder': 'Process Folder (Recursive)',
        'select_read_folder': 'Process Folder (1 Level)',
        'operation_completed': 'Operation completed successfully.',
        'error': 'Error:',
        'auto_delete': 'Auto delete after 5 mins',
        'output_to': 'Output to:',
        'processing': 'Processing...',
        'delete_notice': 'Files will auto delete after 5 minutes',
        'delete_disabled': 'Auto delete disabled'
    },
    'zh': {
        'title': '文件处理器',
        'select_language': '选择语言',
        'select_output': '选择输出文件夹',
        'select_all_file': '处理单个文件',
        'select_all_folder': '处理文件夹(递归)',
        'select_read_folder': '处理文件夹(单层)',
        'operation_completed': '操作成功完成。',
        'error': '错误:',
        'auto_delete': '5分钟后自动删除',
        'output_to': '输出到:',
        'processing': '处理中...',
        'delete_notice': '文件将在5分钟后自动删除',
        'delete_disabled': '已禁用自动删除'
    }
}

class AutoDeleteManager:
    """管理自动删除任务的类"""
    def __init__(self):
        self.tasks = {}
        self.lock = threading.Lock()
        self.enabled = True
    
    def add_task(self, path, delay=300):
        """添加自动删除任务"""
        if not self.enabled:
            return
            
        with self.lock:
            # 取消已有的相同路径任务
            if path in self.tasks:
                self.cancel_task(path)
            
            # 创建新任务
            task = threading.Timer(delay, self._delete_path, args=[path])
            self.tasks[path] = {
                'timer': task,
                'time': time.time() + delay
            }
            task.start()
    
    def cancel_task(self, path):
        """取消自动删除任务"""
        with self.lock:
            if path in self.tasks:
                self.tasks[path]['timer'].cancel()
                del self.tasks[path]
    
    def _delete_path(self, path):
        """实际执行删除操作"""
        try:
            if os.path.isfile(path):
                os.remove(path)
            elif os.path.isdir(path):
                shutil.rmtree(path)
        except Exception as e:
            print(f"Delete failed: {e}")
        finally:
            with self.lock:
                if path in self.tasks:
                    del self.tasks[path]
    
    def disable(self):
        """禁用所有自动删除"""
        with self.lock:
            self.enabled = False
            for task in list(self.tasks.values()):
                task['timer'].cancel()
            self.tasks.clear()
    
    def enable(self):
        """启用自动删除"""
        self.enabled = True

class Application(tk.Tk):
    def __init__(self):
        super().__init__()
        self.language = 'zh'
        self.output_path = os.path.join(os.path.expanduser('~'), 'Desktop')
        self.auto_delete_mgr = AutoDeleteManager()

        # 临时排除集合（任务级，不修改全局常量）
        self.temp_excluded_folders = set()
        self.temp_excluded_files = set()
        self.temp_excluded_suffixes = set()
        
        # 苹果风格设置
        self.style = ttk.Style()
        self.style.configure('TFrame', background='#f5f5f7')
        self.style.configure('TLabel', background='#f5f5f7', font=('Helvetica', 11))
        self.style.configure('TButton', font=('Helvetica', 11), padding=6)
        self.style.configure('TEntry', font=('Helvetica', 11), padding=5)
        self.style.configure('Header.TLabel', font=('Helvetica', 14, 'bold'))
        self.style.configure('Accent.TButton', foreground='black', background='#007aff')
        self.style.map('Accent.TButton', 
                      background=[('active', '#0062cc'), ('pressed', '#0052b3')])
        
        self.title(languages[self.language]['title'])
        self.geometry('560x560')
        self.create_widgets()
        
        # 5分钟自动关闭程序
        self.auto_close_job = self.after(300000, self.auto_close)
        self.bind_all("<Key>", self.reset_timer)
        self.bind_all("<Button>", self.reset_timer)
    
    def auto_close(self):
        """自动关闭程序"""
        self.destroy()
    
    def reset_timer(self, event=None):
        """重置自动关闭计时器"""
        if hasattr(self, 'auto_close_job'):
            self.after_cancel(self.auto_close_job)
        self.auto_close_job = self.after(300000, self.auto_close)
    
    def create_widgets(self):
        """创建界面组件"""
        # 主框架
        main_frame = ttk.Frame(self)
        main_frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=20)
        
        # 标题
        header = ttk.Label(main_frame, text=languages[self.language]['title'], style='Header.TLabel')
        header.pack(pady=(0, 16))

        # 分隔线（标题下）
        ttk.Separator(main_frame, orient='horizontal').pack(fill=tk.X, pady=10)
        
        # 语言选择
        lang_frame = ttk.Frame(main_frame)
        lang_frame.pack(fill=tk.X, pady=5)
        
        ttk.Label(lang_frame, text=languages[self.language]['select_language']).pack(side=tk.LEFT, padx=(0, 10))
        
        self.lang_combobox = ttk.Combobox(lang_frame, values=['English', '中文'], state='readonly')
        self.lang_combobox.current(1 if self.language == 'zh' else 0)
        self.lang_combobox.pack(side=tk.LEFT)
        self.lang_combobox.bind('<<ComboboxSelected>>', self.change_language)
        
        # 分隔线（语言选择下）
        ttk.Separator(main_frame, orient='horizontal').pack(fill=tk.X, pady=10)
        
        # 输出路径显示
        output_frame = ttk.Frame(main_frame)
        output_frame.pack(fill=tk.X, pady=5)
        
        ttk.Label(output_frame, text=languages[self.language]['output_to']).pack(side=tk.LEFT, padx=(0, 10))
        
        self.output_label = ttk.Label(output_frame, text=self.output_path, wraplength=400)
        self.output_label.pack(side=tk.LEFT, fill=tk.X, expand=True)
        
        # 分隔线（输出路径下）
        ttk.Separator(main_frame, orient='horizontal').pack(fill=tk.X, pady=10)
        
        # 按钮区域
        btn_frame = ttk.Frame(main_frame)
        btn_frame.pack(fill=tk.X, pady=10)
        
        ttk.Button(btn_frame, text=languages[self.language]['select_output'], 
                  command=self.select_output_folder).pack(fill=tk.X, pady=5)
        
        ttk.Button(btn_frame, text=languages[self.language]['select_all_file'], 
                  command=self.select_any_file, style='Accent.TButton').pack(fill=tk.X, pady=5)
        
        ttk.Button(btn_frame, text=languages[self.language]['select_all_folder'], 
                  command=self.select_any_folder, style='Accent.TButton').pack(fill=tk.X, pady=5)
        
        ttk.Button(btn_frame, text=languages[self.language]['select_read_folder'], 
                  command=self.select_read_folder, style='Accent.TButton').pack(fill=tk.X, pady=5)
        
        # 分隔线（按钮区域下）
        ttk.Separator(main_frame, orient='horizontal').pack(fill=tk.X, pady=10)
        
        # 自动删除选项
        self.auto_delete_var = tk.BooleanVar(value=True)
        auto_delete_frame = ttk.Frame(main_frame)
        auto_delete_frame.pack(fill=tk.X, pady=10)
        
        self.auto_delete_btn = ttk.Checkbutton(
            auto_delete_frame, 
            text=languages[self.language]['auto_delete'],
            variable=self.auto_delete_var,
            command=self.toggle_auto_delete
        )
        self.auto_delete_btn.pack(side=tk.LEFT)
        
        self.delete_status = ttk.Label(auto_delete_frame, text=languages[self.language]['delete_notice'])
        self.delete_status.pack(side=tk.LEFT, padx=10)
    
    def toggle_auto_delete(self):
        """切换自动删除功能"""
        if self.auto_delete_var.get():
            self.auto_delete_mgr.enable()
            self.delete_status.config(text=languages[self.language]['delete_notice'])
        else:
            self.auto_delete_mgr.disable()
            self.delete_status.config(text=languages[self.language]['delete_disabled'])
    
    def change_language(self, event):
        """切换语言"""
        selected_lang = self.lang_combobox.get()
        self.language = 'zh' if selected_lang == '中文' else 'en'
        self.update_texts()
    
    def update_texts(self):
        """更新界面文本"""
        self.title(languages[self.language]['title'])
        # 重新创建界面组件以更新文本
        self.create_widgets()
    
    def select_output_folder(self):
        """选择输出文件夹"""
        folder_path = filedialog.askdirectory(title=languages[self.language]['select_output'])
        if folder_path:
            self.output_path = folder_path
            self.output_label.config(text=folder_path)
    
    def select_any_file(self):
        """处理单个文件"""
        file_path = filedialog.askopenfilename(title=languages[self.language]['select_all_file'])
        if file_path:
            self.process_with_progress(self.process_single_file, file_path)
    
    def select_any_folder(self):
        """递归处理文件夹"""
        folder_path = filedialog.askdirectory(title=languages[self.language]['select_all_folder'])
        if folder_path:
            self.process_with_progress(self.process_all_files_folder, folder_path)
    
    def select_read_folder(self):
        """单层处理文件夹"""
        folder_path = filedialog.askdirectory(title=languages[self.language]['select_read_folder'])
        if folder_path:
            self.process_with_progress(self.process_folder_read, folder_path)
    
    def process_with_progress(self, func, *args):
        """带进度提示的处理方法"""
        progress = tk.Toplevel(self)
        progress.title(languages[self.language]['processing'])
        progress.geometry('300x100')
        
        label = ttk.Label(progress, text=languages[self.language]['processing'])
        label.pack(pady=20)
        
        progress_bar = ttk.Progressbar(progress, mode='indeterminate')
        progress_bar.pack(fill=tk.X, padx=20)
        progress_bar.start()
        
        def run():
            try:
                result = func(*args)
                self.after(0, lambda: self.show_result(progress, result))
            except Exception as e:
                self.after(0, lambda: self.show_error(progress, str(e)))
        
        threading.Thread(target=run, daemon=True).start()
    
    def show_result(self, progress, result):
        """显示处理结果"""
        progress.destroy()
        messagebox.showinfo(languages[self.language]['operation_completed'], result)
    
    def show_error(self, progress, error):
        """显示错误"""
        progress.destroy()
        messagebox.showerror(languages[self.language]['error'], error)
    
    # 以下是原有的处理函数，保持不变但添加自动删除功能
    def process_single_file(self, file_path):
        """处理单个文件"""
        combined_content = f"File: {os.path.basename(file_path)}\n\n"
        file_content = self.read_file_content(file_path)
        if file_content:
            combined_content += file_content
        
        base_name = os.path.splitext(os.path.basename(file_path))[0]
        output_filename = f"{base_name}.txt"
        output_path = os.path.join(self.output_path, output_filename)
        
        self.save_to_path(output_path, combined_content)
        
        # 添加自动删除任务
        if self.auto_delete_var.get():
            self.auto_delete_mgr.add_task(output_path)
        
        return output_path
    
    def process_all_files_folder(self, folder_path):
        """递归处理文件夹"""
        # 解析根目录的 .gitignore 文件
        gitignore_path = os.path.join(folder_path, '.gitignore')
        folders_from_gitignore, files_from_gitignore, suffixes_from_gitignore = parse_gitignore(gitignore_path)

        # 设置临时排除集合
        self.set_temp_exclusions(folders_from_gitignore, files_from_gitignore, suffixes_from_gitignore)

        try:
            files_dict = self.get_all_files(folder_path)
            main_folder_name = os.path.basename(folder_path)
            main_save_path = os.path.join(self.output_path, main_folder_name)

            os.makedirs(main_save_path, exist_ok=True)

            folder_structure = self.generate_folder_structure(folder_path)
            self.save_to_path(os.path.join(main_save_path, "folder_structure.txt"), folder_structure)

            all_txt_content = ""
            for subfolder, files in files_dict.items():
                combined_content = []
                subfolder_name = os.path.basename(subfolder)
                combined_content.append(f"==== {subfolder_name} ====\n\n")
            
                for file in files:
                    if self.should_exclude(file):
                        continue

                    combined_content.append(f"---- {os.path.basename(file)} ----\n\n")
                    file_content = self.read_file_content(file)
                    if file_content:
                        combined_content.append(file_content)
                        combined_content.append('\n\n')

                subfolder_text = ''.join(combined_content)
                output_filename = f"{subfolder_name}.txt"
                output_path = os.path.join(main_save_path, output_filename)
                self.save_to_path(output_path, subfolder_text)
                all_txt_content += subfolder_text + "\n"

            # 生成不重名的 All 汇总文件路径：{文件夹名}_All[数字].txt
            all_output_path = self.generate_unique_all_output_path(main_save_path, main_folder_name)
            self.save_to_path(all_output_path, all_txt_content)

            # 添加自动删除任务
            if self.auto_delete_var.get():
                self.auto_delete_mgr.add_task(main_save_path)

            return main_save_path

        finally:
            # 清除临时排除集合
            self.clear_temp_exclusions()

    def generate_unique_all_output_path(self, base_dir, base_name):
        """为 All 汇总文件生成不重名路径

        参数:
        - base_dir: 保存目录
        - base_name: 基础名称（通常为主文件夹名）

        返回:
        - 一个在 base_dir 下不与现有文件冲突的路径，规则为
          {base_name}_All.txt 或 {base_name}_All{数字}.txt
        """
        # 期望的初始文件名：{base_name}_All.txt
        desired_filename = f"{base_name}_All.txt"
        candidate_path = os.path.join(base_dir, desired_filename)

        # 若无重名，直接返回
        if not os.path.exists(candidate_path):
            return candidate_path

        # 存在重名则追加数字后缀
        index = 1
        while True:
            numbered_filename = f"{base_name}_All{index}.txt"
            candidate_path = os.path.join(base_dir, numbered_filename)
            if not os.path.exists(candidate_path):
                return candidate_path
            index += 1
    
    def process_folder_read(self, folder_path):
        """单层处理文件夹"""
        # 解析根目录的 .gitignore 文件
        gitignore_path = os.path.join(folder_path, '.gitignore')
        folders_from_gitignore, files_from_gitignore, suffixes_from_gitignore = parse_gitignore(gitignore_path)

        # 设置临时排除集合
        self.set_temp_exclusions(folders_from_gitignore, files_from_gitignore, suffixes_from_gitignore)

        try:
            main_folder_name = os.path.basename(folder_path)
            main_save_path = os.path.join(self.output_path, f"{main_folder_name}_read")

            os.makedirs(main_save_path, exist_ok=True)
            folder_structure = self.generate_folder_structure(folder_path)
            self.save_to_path(os.path.join(main_save_path, "folder_structure.txt"), folder_structure)

            for item in os.listdir(folder_path):
                if self.should_exclude(item):
                    continue

                item_path = os.path.join(folder_path, item)
                if os.path.isfile(item_path):
                    content = f"File: {item}\n\n"
                    file_content = self.read_file_content(item_path)
                    if file_content:
                        content += file_content

                    output_filename = f"{os.path.splitext(item)[0]}.txt"
                    output_path = os.path.join(main_save_path, output_filename)
                    self.save_to_path(output_path, content)

                elif os.path.isdir(item_path):
                    content = f"Folder: {item}\n\n"
                    for root, dirs, files in os.walk(item_path):
                        # 过滤dirs列表，移除需要排除的目录
                        dirs[:] = [d for d in dirs if not self.should_exclude(d)]

                        for file in files:
                            if self.should_exclude(file):
                                continue

                            file_full_path = os.path.join(root, file)
                            rel_path = os.path.relpath(file_full_path, item_path)
                            content += f"File: {rel_path}\n\n"
                            file_content = self.read_file_content(file_full_path)
                            if file_content:
                                content += file_content + "\n\n"

                    output_filename = f"{item}.txt"
                    output_path = os.path.join(main_save_path, output_filename)
                    self.save_to_path(output_path, content)

            # 添加自动删除任务
            if self.auto_delete_var.get():
                self.auto_delete_mgr.add_task(main_save_path)

            return main_save_path

        finally:
            # 清除临时排除集合
            self.clear_temp_exclusions()

    def should_exclude(self, name):
        """判断是否应该排除

        参数:
        - name: 文件名或路径（会自动提取basename）

        返回:
        - bool: 是否应该排除
        """
        # 提取basename并转为小写
        base_name = os.path.basename(name).lower()

        # 检查是否以 . 开头（隐藏文件/文件夹）
        if base_name.startswith('.'):
            return True

        # 检查全局排除列表（小写比较）
        if base_name in [f.lower() for f in EXCLUDED_FOLDERS]:
            return True
        if base_name in [f.lower() for f in EXCLUDED_FILES]:
            return True

        # 检查临时排除列表
        if base_name in [f.lower() for f in self.temp_excluded_folders]:
            return True
        if base_name in [f.lower() for f in self.temp_excluded_files]:
            return True

        # 检查后缀（小写比较）
        _, ext = os.path.splitext(base_name)
        if ext in [s.lower() for s in EXCLUDED_SUFFIX]:
            return True
        if ext in [s.lower() for s in self.temp_excluded_suffixes]:
            return True

        return False

    def set_temp_exclusions(self, folders=None, files=None, suffixes=None):
        """设置临时排除集合

        参数:
        - folders: 要临时排除的文件夹集合
        - files: 要临时排除的文件集合
        - suffixes: 要临时排除的后缀集合
        """
        if folders:
            self.temp_excluded_folders.update(folders)
        if files:
            self.temp_excluded_files.update(files)
        if suffixes:
            self.temp_excluded_suffixes.update(suffixes)

    def clear_temp_exclusions(self):
        """清除临时排除集合"""
        self.temp_excluded_folders.clear()
        self.temp_excluded_files.clear()
        self.temp_excluded_suffixes.clear()

    def get_all_files(self, folder_path):
        """获取所有文件"""
        files_dict = {}
        for root, dirs, files in os.walk(folder_path):
            dirs[:] = [d for d in dirs if not self.should_exclude(d)]
            all_files = [os.path.join(root, f) for f in files if not self.should_exclude(f)]
            if all_files:
                files_dict[root] = all_files
        return files_dict
    
    def generate_folder_structure(self, folder_path, indent=""):
        """生成文件夹结构"""
        structure = ""
        for item in os.listdir(folder_path):
            if self.should_exclude(item):
                continue
            
            item_path = os.path.join(folder_path, item)
            if os.path.isdir(item_path):
                structure += f"{indent}[Folder] {item}\n"
                structure += self.generate_folder_structure(item_path, indent + "  ")
            else:
                structure += f"{indent}[File] {item}\n"
        return structure
    
    def read_file_content(self, file_path):
        """读取文件内容"""
        try:
            with open(file_path, 'r', encoding='utf-8') as file:
                return file.read()
        except UnicodeDecodeError:
            try:
                with open(file_path, 'rb') as file:
                    data = file.read()
                    return f"<Binary file: {len(data)} bytes>"
            except Exception as e:
                print(f"Error reading file {file_path}: {e}")
                return None
        except Exception as e:
            print(f"Error reading file {file_path}: {e}")
            return None
    
    def save_to_path(self, path, content):
        """保存到路径"""
        try:
            os.makedirs(os.path.dirname(path), exist_ok=True)
            with open(path, 'w', encoding='utf-8') as file:
                file.write(content)
            print(f"Saved to: {path}")
        except Exception as e:
            print(f"Error saving file {path}: {e}")
            raise

def test_gitignore_parsing():
    """测试 .gitignore 解析功能"""
    import tempfile
    import os

    # 创建临时目录和 .gitignore 文件
    with tempfile.TemporaryDirectory() as temp_dir:
        gitignore_path = os.path.join(temp_dir, '.gitignore')

        # 创建测试 .gitignore 内容
        gitignore_content = """# 注释行
node_modules
*.log
*.tmp
build/
dist/
.env
package-lock.json
__pycache__/
*.pyc
.DS_Store
"""

        with open(gitignore_path, 'w', encoding='utf-8') as f:
            f.write(gitignore_content)

        print("=== .gitignore 文件内容 ===")
        with open(gitignore_path, 'r', encoding='utf-8') as f:
            for i, line in enumerate(f, 1):
                print(f"{i}: '{line.strip()}'")

        print("\n=== 解析过程 ===")
        # 解析 .gitignore
        folders, files, suffixes = parse_gitignore(gitignore_path)

        print("解析结果:")
        print(f"文件夹: {sorted(folders)}")
        print(f"文件: {sorted(files)}")
        print(f"后缀: {sorted(suffixes)}")

        # 验证结果
        expected_folders = {'node_modules', 'build', 'dist', '__pycache__'}
        expected_files = {'package-lock.json'}
        expected_suffixes = {'.log', '.tmp'}  # .pyc 被跳过因为已在 EXCLUDED_SUFFIX 中

        assert folders == expected_folders, f"文件夹不匹配: {folders} != {expected_folders}"
        assert files == expected_files, f"文件不匹配: {files} != {expected_files}"
        assert suffixes == expected_suffixes, f"后缀不匹配: {suffixes} != {expected_suffixes}"

        print("✅ .gitignore 解析测试通过！")

if __name__ == '__main__':
    # 运行测试
    test_gitignore_parsing()

    # 启动GUI应用
    app = Application()
    app.mainloop()
