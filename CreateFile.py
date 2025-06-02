import os
import tkinter as tk
from tkinter import ttk, filedialog, messagebox


class FileCreatorApp:
    def __init__(self, root):
        self.root = root
        self.root.title("文件创建工具 - 专业版")
        self.root.geometry("600x650")
        self.root.resizable(False, False)

        # 苹果风格设置
        self.style = ttk.Style()
        self.style.configure('TFrame', background='#f5f5f7')
        self.style.configure('TLabel', background='#f5f5f7', font=('SF Pro', 11))
        self.style.configure('TButton', font=('SF Pro', 11), padding=6)
        self.style.configure('TEntry', font=('SF Pro', 11), padding=5)
        self.style.configure('Header.TLabel', font=('SF Pro', 14, 'bold'))

        # 主框架
        self.main_frame = ttk.Frame(root)
        self.main_frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=20)

        # 标题
        self.header = ttk.Label(self.main_frame, text="文件创建工具", style='Header.TLabel')
        self.header.pack(pady=(0, 20))

        # 文件名输入区域
        self.file_name_frame = ttk.Frame(self.main_frame)
        self.file_name_frame.pack(fill=tk.X, pady=5)

        self.label_file_name = ttk.Label(self.file_name_frame, text="文件名:")
        self.label_file_name.pack(side=tk.LEFT, padx=(0, 10))

        self.entry_file_name = ttk.Entry(self.file_name_frame)
        self.entry_file_name.pack(side=tk.LEFT, expand=True, fill=tk.X)

        # 目录选择区域
        self.directory_frame = ttk.Frame(self.main_frame)
        self.directory_frame.pack(fill=tk.X, pady=5)

        self.label_directory = ttk.Label(self.directory_frame, text="目录:")
        self.label_directory.pack(side=tk.LEFT, padx=(0, 10))

        self.entry_directory = ttk.Entry(self.directory_frame)
        self.entry_directory.pack(side=tk.LEFT, expand=True, fill=tk.X)

        self.button_choose = ttk.Button(self.directory_frame, text="选择...", command=self.choose_directory)
        self.button_choose.pack(side=tk.LEFT, padx=(10, 0))

        # 模板选择区域
        self.template_frame = ttk.LabelFrame(self.main_frame, text="预设模板", padding=10)
        self.template_frame.pack(fill=tk.X, pady=10)

        self.template_buttons_frame = ttk.Frame(self.template_frame)
        self.template_buttons_frame.pack()

        self.java_button = ttk.Button(self.template_buttons_frame, text="Java",
                                      command=lambda: self.set_template(['java']))
        self.java_button.pack(side=tk.LEFT, padx=5)

        self.vue_button = ttk.Button(self.template_buttons_frame, text="Vue",
                                     command=lambda: self.set_template(['vue', 'js', 'css']))
        self.vue_button.pack(side=tk.LEFT, padx=5)

        self.wechat_button = ttk.Button(self.template_buttons_frame, text="微信小程序",
                                        command=lambda: self.set_template(['wxml', 'wxss', 'json', 'js']))
        self.wechat_button.pack(side=tk.LEFT, padx=5)

        self.python_button = ttk.Button(self.template_buttons_frame, text="Python",
                                        command=lambda: self.set_template(['py', 'requirements.txt']))
        self.python_button.pack(side=tk.LEFT, padx=5)

        # 自定义扩展名区域
        self.custom_frame = ttk.LabelFrame(self.main_frame, text="自定义扩展名", padding=10)
        self.custom_frame.pack(fill=tk.BOTH, expand=True, pady=10)

        self.custom_top_frame = ttk.Frame(self.custom_frame)
        self.custom_top_frame.pack(fill=tk.X, pady=5)

        self.label_extension = ttk.Label(self.custom_top_frame, text="扩展名:")
        self.label_extension.pack(side=tk.LEFT, padx=(0, 10))

        self.entry_extension = ttk.Entry(self.custom_top_frame, width=10)
        self.entry_extension.pack(side=tk.LEFT)

        self.button_add = ttk.Button(self.custom_top_frame, text="+ 添加", command=self.add_extension)
        self.button_add.pack(side=tk.LEFT, padx=10)

        self.button_clear = ttk.Button(self.custom_top_frame, text="清空", command=self.clear_extensions)
        self.button_clear.pack(side=tk.LEFT)

        # 扩展名列表
        self.extensions_listbox = tk.Listbox(self.custom_frame, height=8, font=('SF Pro', 11),
                                             selectbackground='#007aff', selectmode=tk.SINGLE)
        self.extensions_listbox.pack(fill=tk.BOTH, expand=True, pady=(5, 0))

        self.scrollbar = ttk.Scrollbar(self.extensions_listbox)
        self.scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        self.extensions_listbox.config(yscrollcommand=self.scrollbar.set)
        self.scrollbar.config(command=self.extensions_listbox.yview)

        # 创建按钮
        self.button_create = ttk.Button(self.main_frame, text="创建文件", command=self.create_files,
                                        style='Accent.TButton')
        self.button_create.pack(pady=20)

        # 初始化变量
        self.extensions = []

        # 自定义样式
        self.style.configure('Accent.TButton', foreground='white', background='#007aff')
        self.style.map('Accent.TButton',
                       background=[('active', '#0062cc'), ('pressed', '#0052b3')])

        # 绑定回车键
        self.entry_extension.bind('<Return>', lambda e: self.add_extension())

    def choose_directory(self):
        """选择目录"""
        folder_selected = filedialog.askdirectory()
        if folder_selected:
            self.entry_directory.delete(0, tk.END)
            self.entry_directory.insert(0, folder_selected)

    def set_template(self, extensions):
        """设置预设模板"""
        self.clear_extensions()
        for ext in extensions:
            self.extensions.append(ext)
            self.extensions_listbox.insert(tk.END, ext)

    def add_extension(self):
        """添加自定义扩展名"""
        ext = self.entry_extension.get().strip().lower()
        if not ext:
            return

        if ext in self.extensions:
            messagebox.showwarning("警告", f"扩展名 '{ext}' 已存在!")
            return

        if len(self.extensions) >= 100:
            messagebox.showwarning("警告", "已达到最大扩展名数量(100个)!")
            return

        self.extensions.append(ext)
        self.extensions_listbox.insert(tk.END, ext)
        self.entry_extension.delete(0, tk.END)

    def clear_extensions(self):
        """清空扩展名列表"""
        self.extensions.clear()
        self.extensions_listbox.delete(0, tk.END)

    def create_files(self):
        """创建文件和文件夹"""
        file_name = self.entry_file_name.get().strip()
        directory = self.entry_directory.get().strip()

        if not file_name:
            messagebox.showerror("错误", "请输入文件名!")
            return

        if not directory:
            messagebox.showerror("错误", "请选择目录!")
            return

        if not self.extensions:
            messagebox.showerror("错误", "请添加至少一个文件扩展名!")
            return

        folder_path = os.path.join(directory, file_name)

        try:
            # 创建文件夹
            if not os.path.exists(folder_path):
                os.makedirs(folder_path)
                print(f"文件夹创建成功: {folder_path}")
            else:
                print(f"文件夹已存在: {folder_path}")

            # 创建文件
            for ext in self.extensions:
                file_path = os.path.join(folder_path, f"{file_name}.{ext}")

                # 特殊处理 requirements.txt
                if ext == 'requirements.txt':
                    file_path = os.path.join(folder_path, "requirements.txt")

                with open(file_path, 'w', encoding='utf-8') as f:
                    pass
                print(f"文件创建成功: {file_path}")

            messagebox.showinfo("成功", "文件和文件夹创建成功!")
        except Exception as e:
            messagebox.showerror("错误", f"创建失败: {str(e)}")


if __name__ == "__main__":
    root = tk.Tk()
    app = FileCreatorApp(root)
    root.mainloop()