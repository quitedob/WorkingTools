import os
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from tkinter.font import Font

# 定义多语言资源（英文和中文）
languages = {
    'en': {
        'title': 'File Processor',
        'select_language': 'Select Language',
        'select_output': 'Select Output Folder',
        'select_all_file': 'Select Any File',
        'select_all_folder': 'Select a Folder (All Files)',
        'select_read_folder': 'Select a Folder (Read Mode)',
        'operation_completed': 'Operation completed successfully.',
        'error': 'An error occurred:',
        'output_path': 'Output Path:'
    },
    'zh': {
        'title': '文件处理器',
        'select_language': '选择语言',
        'select_output': '选择输出文件夹',
        'select_all_file': '选择任意文件',
        'select_all_folder': '选择包含所有文件的文件夹',
        'select_read_folder': '选择文件夹(读取模式)',
        'operation_completed': '操作成功完成。',
        'error': '发生错误：',
        'output_path': '输出路径：'
    }
}

class Application(tk.Tk):
    def __init__(self):
        super().__init__()
        self.language = 'en'
        self.output_path = os.path.join(os.path.expanduser('~'), 'Desktop')
        
        # 设置苹果风格
        self.configure_apple_style()
        
        self.title(languages[self.language]['title'])
        self.geometry('500x450')
        self.create_widgets()

    def configure_apple_style(self):
        """配置苹果风格的界面"""
        self.configure(bg='#f5f5f7')  # 苹果典型的浅灰色背景
        
        # 设置窗口圆角
        self.attributes('-alpha', 0.98)  # 轻微透明效果
        self.overrideredirect(False)  # 保留窗口装饰
        
        # 自定义字体
        self.default_font = Font(family='Helvetica', size=12)
        self.title_font = Font(family='Helvetica', size=14, weight='bold')
        self.button_font = Font(family='Helvetica', size=12)
        
        # 创建样式
        self.style = ttk.Style()
        
        # 配置按钮样式
        self.style.configure('TButton', 
                           font=self.button_font,
                           padding=10,
                           relief='flat',
                           background='#007aff',  # 苹果蓝
                           foreground='black')
        self.style.map('TButton',
                      background=[('active', '#0062cc')])  # 点击时变深
        
        # 配置标签样式
        self.style.configure('TLabel', 
                           font=self.default_font,
                           background='#f5f5f7',
                           foreground='#333333')
        
        # 配置组合框样式
        self.style.configure('TCombobox',
                            font=self.default_font,
                            padding=5)

    def create_widgets(self):
        # 主容器
        main_frame = ttk.Frame(self, padding="20")
        main_frame.pack(expand=True, fill=tk.BOTH)
        
        # 标题
        title_label = ttk.Label(main_frame, 
                               text=languages[self.language]['title'],
                               font=self.title_font)
        title_label.pack(pady=(0, 15))
        
        # 语言选择
        lang_frame = ttk.Frame(main_frame)
        lang_frame.pack(fill=tk.X, pady=5)
        
        self.lang_label = ttk.Label(lang_frame, text=languages[self.language]['select_language'])
        self.lang_label.pack(side=tk.LEFT, padx=(0, 10))
        
        self.lang_combobox = ttk.Combobox(lang_frame, values=['English', '中文'], state='readonly')
        self.lang_combobox.current(0 if self.language == 'en' else 1)
        self.lang_combobox.pack(side=tk.LEFT, expand=True, fill=tk.X)
        self.lang_combobox.bind('<<ComboboxSelected>>', self.change_language)
        
        # 输出路径显示
        self.output_label = ttk.Label(main_frame, 
                                    text=f"{languages[self.language]['output_path']} {self.output_path}",
                                    wraplength=400,
                                    justify=tk.LEFT)
        self.output_label.pack(pady=10, anchor=tk.W)
        
        # 按钮容器
        button_frame = ttk.Frame(main_frame)
        button_frame.pack(fill=tk.X, pady=10)
        
        # 修改输出路径按钮
        self.output_button = ttk.Button(button_frame, 
                                      text=languages[self.language]['select_output'], 
                                      command=self.select_output_folder)
        self.output_button.pack(fill=tk.X, pady=5)
        
        # 处理任意文件（单个文件）的按钮
        self.all_file_button = ttk.Button(button_frame, 
                                       text=languages[self.language]['select_all_file'], 
                                       command=self.select_any_file)
        self.all_file_button.pack(fill=tk.X, pady=5)
        
        # 处理任意文件夹（所有文件）的按钮
        self.all_folder_button = ttk.Button(button_frame, 
                                         text=languages[self.language]['select_all_folder'], 
                                         command=self.select_any_folder)
        self.all_folder_button.pack(fill=tk.X, pady=5)
        
        # 处理文件夹（读取模式）的按钮
        self.read_folder_button = ttk.Button(button_frame, 
                                          text=languages[self.language]['select_read_folder'], 
                                          command=self.select_read_folder)
        self.read_folder_button.pack(fill=tk.X, pady=5)
        
        # 添加底部空间
        ttk.Label(main_frame).pack(expand=True)

    def change_language(self, event):
        selected_lang = self.lang_combobox.get()
        self.language = 'en' if selected_lang == 'English' else 'zh'
        self.update_texts()

    def update_texts(self):
        self.title(languages[self.language]['title'])
        self.lang_label.config(text=languages[self.language]['select_language'])
        self.output_button.config(text=languages[self.language]['select_output'])
        self.all_file_button.config(text=languages[self.language]['select_all_file'])
        self.all_folder_button.config(text=languages[self.language]['select_all_folder'])
        self.read_folder_button.config(text=languages[self.language]['select_read_folder'])
        self.output_label.config(text=f"{languages[self.language]['output_path']} {self.output_path}")

    def select_output_folder(self):
        folder_path = filedialog.askdirectory(title=languages[self.language]['select_output'])
        if folder_path:
            self.output_path = folder_path
            self.output_label.config(text=f"{languages[self.language]['output_path']} {self.output_path}")

    def process_single_file(self, file_path):
        combined_content = f"File: {os.path.basename(file_path)}\n\n"
        file_content = self.read_file_content(file_path)
        if file_content:
            combined_content += file_content
        base_name = os.path.splitext(os.path.basename(file_path))[0]
        output_filename = f"{base_name}.txt"
        self.save_to_output(output_filename, combined_content)
        messagebox.showinfo(languages[self.language]['operation_completed'], self.output_path)

    def select_any_file(self):
        file_path = filedialog.askopenfilename(
            title=languages[self.language]['select_all_file'],
            filetypes=[('All Files', '*.*')]
        )
        if file_path:
            self.process_single_file(file_path)

    def select_any_folder(self):
        folder_path = filedialog.askdirectory(title=languages[self.language]['select_all_folder'])
        if folder_path:
            self.process_all_files_folder(folder_path)

    def select_read_folder(self):
        folder_path = filedialog.askdirectory(title=languages[self.language]['select_read_folder'])
        if folder_path:
            self.process_folder_read(folder_path)

    def process_all_files_folder(self, folder_path):
        files_dict = self.get_all_files(folder_path)
        main_folder_name = os.path.basename(folder_path)
        main_save_path = os.path.join(self.output_path, main_folder_name)
        folder_structure = self.generate_folder_structure(folder_path)
        self.save_to_path(main_save_path, "folder_structure.txt", folder_structure)
        for subfolder, files in files_dict.items():
            combined_content = []
            for file in files:
                combined_content.append(f"File: {os.path.basename(file)}\n\n")
                file_content = self.read_file_content(file)
                if file_content:
                    combined_content.append(file_content)
                    combined_content.append('\n\n')
            subfolder_name = os.path.basename(subfolder)
            self.save_to_path(main_save_path, f"{subfolder_name}.txt", ''.join(combined_content))
        messagebox.showinfo(languages[self.language]['operation_completed'], self.output_path)

    def process_folder_read(self, folder_path):
        main_folder_name = os.path.basename(folder_path)
        main_save_path = os.path.join(self.output_path, f"{main_folder_name}_read")
        os.makedirs(main_save_path, exist_ok=True)
        folder_structure = self.generate_folder_structure(folder_path)
        self.save_to_path(main_save_path, "folder_structure.txt", folder_structure)
        for item in os.listdir(folder_path):
            item_path = os.path.join(folder_path, item)
            if os.path.isfile(item_path):
                content = f"File: {item}\n\n"
                file_content = self.read_file_content(item_path)
                if file_content:
                    content += file_content
                output_filename = f"{os.path.splitext(item)[0]}.txt"
                self.save_to_path(main_save_path, output_filename, content)
            elif os.path.isdir(item_path):
                content = f"Folder: {item}\n\n"
                for root, _, files in os.walk(item_path):
                    for file in files:
                        file_full_path = os.path.join(root, file)
                        rel_path = os.path.relpath(file_full_path, item_path)
                        content += f"File: {rel_path}\n\n"
                        file_content = self.read_file_content(file_full_path)
                        if file_content:
                            content += file_content + "\n\n"
                output_filename = f"{item}.txt"
                self.save_to_path(main_save_path, output_filename, content)
        messagebox.showinfo(languages[self.language]['operation_completed'], main_save_path)

    def get_all_files(self, folder_path):
        files_dict = {}
        for root, _, files in os.walk(folder_path):
            all_files = [os.path.join(root, file) for file in files]
            if all_files:
                files_dict[root] = all_files
        return files_dict

    def generate_folder_structure(self, folder_path, indent=""):
        structure = ""
        for item in os.listdir(folder_path):
            item_path = os.path.join(folder_path, item)
            if os.path.isdir(item_path):
                structure += f"{indent}[Folder] {item}\n"
                structure += self.generate_folder_structure(item_path, indent + "  ")
            else:
                structure += f"{indent}[File] {item}\n"
        return structure

    def read_file_content(self, file_path):
        try:
            with open(file_path, 'r', encoding='utf-8') as file:
                return file.read()
        except UnicodeDecodeError:
            try:
                with open(file_path, 'rb') as file:
                    data = file.read()
                    return f"<Binary file: {len(data)} bytes>"
            except Exception as e:
                messagebox.showerror(languages[self.language]['error'], str(e))
                return None
        except Exception as e:
            messagebox.showerror(languages[self.language]['error'], str(e))
            return None

    def save_to_output(self, file_name, content):
        try:
            os.makedirs(self.output_path, exist_ok=True)
            full_path = os.path.join(self.output_path, file_name)
            with open(full_path, 'w', encoding='utf-8') as file:
                file.write(content)
        except Exception as e:
            messagebox.showerror(languages[self.language]['error'], str(e))

    def save_to_path(self, save_path, file_name, content):
        try:
            os.makedirs(save_path, exist_ok=True)
            full_path = os.path.join(save_path, file_name)
            with open(full_path, 'w', encoding='utf-8') as file:
                file.write(content)
        except Exception as e:
            messagebox.showerror(languages[self.language]['error'], str(e))

if __name__ == '__main__':
    app = Application()
    app.mainloop()