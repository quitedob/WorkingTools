# ./pdf_image_ocr_app.py
# -*- coding: UTF-8 -*-
# defina_CRT_SCURE.NO-WARNING
import os
import platform
import shutil
import threading
import traceback
import logging
from time import strftime, localtime, perf_counter
from tkinter import *
from tkinter import ttk, filedialog, messagebox
from tkinter.tcl import TclError  # 明确导入 TclError

# --- 依赖导入与检查 ---
# 图像基础库
from PIL import Image, ImageEnhance, ImageFilter
import fitz  # PyMuPDF
import cv2
import numpy as np

# --- OCR 依赖导入与可用性检查 ---
# Tesseract OCR
try:
    import pytesseract
    from pytesseract import Output, TesseractError, TesseractNotFoundError

    TESSERACT_AVAILABLE = True
    print("Tesseract OCR 可用。")
except ImportError:
    print("警告：未找到 pytesseract 库，Tesseract 相关功能不可用。")
    TESSERACT_AVAILABLE = False
    TesseractError = Exception  # 定义通用异常占位
    TesseractNotFoundError = Exception  # 定义通用异常占位

# PaddleOCR PP-Structure
try:
    import paddle  # 尝试导入 PPStructure，若底层 DLL 加载失败会抛出 OSError
    from paddleocr import PPStructure

    PPSTRUCTURE_AVAILABLE = True
    print("PaddleOCR PP-Structure 可用。")
except ImportError:
    print("警告：未找到 paddlepaddle 或 paddleocr 库，PP-Structure 功能不可用。")
    PPSTRUCTURE_AVAILABLE = False
    PPStructure = None  # 定义空占位，避免后续 NameError
except OSError as e:
    print(f"警告：加载 PP-Structure 底层依赖失败: {e}，已禁用 PP-Structure 功能。")
    PPSTRUCTURE_AVAILABLE = False
    PPStructure = None

# --- PyTorch 和 CARN 超分辨率 ---
try:
    import torch
    from torchvision.transforms import ToTensor, ToPILImage

    TORCH_AVAILABLE = True
    print("PyTorch 可用。")
    try:
        from carn import CARN  # 假设 carn.py 在同目录或 PYTHONPATH

        CARN_MODEL_DEF_AVAILABLE = True
        print("CARN 模型定义可用。")
    except ImportError:
        print("警告：未找到 CARN 模型定义文件 (carn.py)，超分辨率功能不可用。")
        CARN_MODEL_DEF_AVAILABLE = False
        CARN = None
except ImportError:
    print("警告：未找到 torch 或 torchvision 库，超分辨率功能不可用。")
    TORCH_AVAILABLE = False
    CARN_MODEL_DEF_AVAILABLE = False
    CARN = None
except OSError as e:
    print(f"警告：加载 PyTorch 底层依赖失败: {e}，已禁用超分辨率功能。")
    TORCH_AVAILABLE = False
    CARN_MODEL_DEF_AVAILABLE = False
    CARN = None

# --- 日志配置 ---
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# --- 全局 Tesseract 路径查找 (如果 Tesseract 可用) ---
TESSERACT_PATH = None
TESSDATA_DIR = None
TESSDATA_PREFIX = None
if TESSERACT_AVAILABLE:
    try:
        print("开始查找 Tesseract OCR...")
        if platform.system() == "Windows":
            tesseract_cmd_env = os.getenv('TESSERACT_CMD')
            if tesseract_cmd_env and os.path.exists(tesseract_cmd_env):
                TESSERACT_PATH = tesseract_cmd_env
            else:
                possible_paths = [
                    r'C:\Program Files\Tesseract-OCR\tesseract.exe',
                    r'C:\Program Files (x86)\Tesseract-OCR\tesseract.exe'
                ]
                TESSERACT_PATH = next((p for p in possible_paths if os.path.exists(p)), None)
            if not TESSERACT_PATH:  # 如果通过环境变量和默认路径都找不到，尝试 shutil.which
                TESSERACT_PATH = shutil.which('tesseract')
        else:  # macOS, Linux
            TESSERACT_PATH = shutil.which('tesseract')

        if not TESSERACT_PATH or not os.path.exists(TESSERACT_PATH):
            raise FileNotFoundError(
                "错误：未能找到 Tesseract 可执行文件。请确保已安装并配置到系统 PATH，或设置 TESSERACT_CMD 环境变量。")
        print(f"找到 Tesseract: {TESSERACT_PATH}")
        pytesseract.pytesseract.tesseract_cmd = TESSERACT_PATH
        print(f"已设置 pytesseract 命令路径。")

        # --- 查找 Tessdata 目录 ---
        tesseract_dir = os.path.dirname(TESSERACT_PATH)
        # 优先检查 TESSERACT_PATH 同级或上级的 'tessdata'
        potential_tessdata_paths = [
            os.path.join(tesseract_dir, 'tessdata'),
            os.path.abspath(os.path.join(tesseract_dir, '..', 'tessdata'))  # 有些安装方式tessdata在上一级
        ]
        for p_path in potential_tessdata_paths:
            if os.path.isdir(p_path):
                TESSDATA_DIR = p_path
                break

        # 如果没找到，再检查环境变量 TESSDATA_PREFIX
        if not TESSDATA_DIR:
            tessdata_prefix_env = os.getenv('TESSDATA_PREFIX')
            if tessdata_prefix_env:
                # TESSDATA_PREFIX 可能直接指向 tessdata 目录，或者其父目录
                if os.path.basename(tessdata_prefix_env).lower() == 'tessdata' and os.path.isdir(tessdata_prefix_env):
                    TESSDATA_DIR = tessdata_prefix_env
                else:
                    potential_tessdata_env = os.path.join(tessdata_prefix_env, 'tessdata')
                    if os.path.isdir(potential_tessdata_env):
                        TESSDATA_DIR = potential_tessdata_env

        if TESSDATA_DIR and os.path.isdir(TESSDATA_DIR):
            print(f"找到 tessdata 目录: {TESSDATA_DIR}")
            # 设置 TESSDATA_PREFIX 为 tessdata 目录的父目录
            TESSDATA_PREFIX = os.path.abspath(os.path.join(TESSDATA_DIR, '..'))
            os.environ['TESSDATA_PREFIX'] = TESSDATA_PREFIX  # 确保 Tesseract 能找到
            print(f"已设置环境变量 TESSDATA_PREFIX = {TESSDATA_PREFIX}")
        else:
            print(
                "警告：未能自动找到有效的 'tessdata' 目录。Tesseract OCR 可能因缺少语言文件而失败。请尝试设置 TESSDATA_PREFIX 环境变量指向 'tessdata' 文件夹的父目录。")

    except FileNotFoundError as e:
        print(e)
        TESSERACT_PATH = None  # 标记为不可用
    except Exception as e:
        print(f"初始化 Tesseract 路径时发生未知错误: {e}")
        TESSERACT_PATH = None  # 标记为不可用


# -----------------------------------------------------------

class FileOCRApp:  # 重命名类名以反映其更广泛的功能
    """ 文件 OCR 工具 (支持 PDF 和图像, 集成 CARN 超分 + PP-Structure + Tesseract 备选) """

    def __init__(self, root):
        self.root = root
        self.root.title("智能文件 OCR 工具 (支持PDF/图像, PP-Structure + CARN)")  # 修改标题
        self.root.geometry("850x700")  # 略微增加高度以容纳新选项（如果添加）
        self.style = ttk.Style()
        try:
            if platform.system() == "Windows":
                self.style.theme_use('vista')
            elif platform.system() == "Darwin":
                self.style.theme_use('aqua')
            else:
                self.style.theme_use('clam')
        except TclError:
            print("无法设置 ttk 主题，使用默认主题。")

        self.input_files = []
        self.output_folder = StringVar(value=os.getcwd())
        self.running = False

        self.ocr_engine_choice = StringVar(value="PP-Structure" if PPSTRUCTURE_AVAILABLE else "Tesseract")
        self.ocr_language = StringVar(value="ch")
        self.perform_osd = BooleanVar(value=True if TESSERACT_AVAILABLE else False)
        self.perform_crop = BooleanVar(value=True)
        self.perform_clahe = BooleanVar(value=True)
        self.perform_denoise = BooleanVar(value=False)
        self.use_super_res = BooleanVar(value=False)
        self.carn_model_path = StringVar(value="carn.pth")

        # 新增：是否保存提取/输入的图像
        self.save_extracted_images = BooleanVar(value=True)

        self.ppstructure_model_instance = None
        self.carn_model_instance = None

        # --- 启动检查 ---
        # (与原代码类似，保持不变，但确保 APP 能启动即使只有一种 OCR 引擎可用)
        if not TESSERACT_AVAILABLE and not PPSTRUCTURE_AVAILABLE:
            messagebox.showerror("严重错误", "未找到 Tesseract 和 PaddleOCR 库，无法执行 OCR。请安装至少一个库。")
            root.destroy()
            return  # 确保在destroy后返回
        elif not TESSERACT_AVAILABLE:
            messagebox.showwarning("配置警告", "未找到 Tesseract，Tesseract 相关功能（如 OSD、备选 OCR）不可用。")
            if self.ocr_engine_choice.get() == "Tesseract":
                if PPSTRUCTURE_AVAILABLE:
                    self.ocr_engine_choice.set("PP-Structure")
                else:
                    self.ocr_engine_choice.set("")  # 无可用引擎
        elif not PPSTRUCTURE_AVAILABLE:
            messagebox.showwarning("配置警告", "未找到 PaddleOCR，PP-Structure 功能不可用。")
            if self.ocr_engine_choice.get() == "PP-Structure":
                if TESSERACT_AVAILABLE:
                    self.ocr_engine_choice.set("Tesseract")
                else:
                    self.ocr_engine_choice.set("")  # 无可用引擎

        if TESSERACT_AVAILABLE and not TESSDATA_PREFIX and not os.getenv('TESSDATA_PREFIX') and not TESSDATA_DIR:
            messagebox.showwarning("Tesseract警告",
                                   "未能确认 TESSDATA_PREFIX 或找到 tessdata 目录，Tesseract OCR 可能因缺少语言文件失败。")

        if not TORCH_AVAILABLE or not CARN_MODEL_DEF_AVAILABLE:
            messagebox.showwarning("超分警告", "未找到 PyTorch 或 CARN 模型定义，超分辨率功能不可用。")
            self.use_super_res.set(False)  # 确保禁用

        self.setup_ui()

    def setup_ui(self):
        main_frame = ttk.Frame(self.root, padding="10 10 10 10")
        main_frame.pack(fill=BOTH, expand=True)

        file_frame = ttk.Frame(main_frame, padding="0 0 0 5")
        file_frame.pack(fill=X)
        # 修改按钮文本和标签
        ttk.Button(file_frame, text="选择单个文件 (PDF/图片)", command=self.select_single_file).pack(side=LEFT,
                                                                                                     padx=(0, 5))
        self.single_file_label = ttk.Label(file_frame, text="未选择文件", anchor=W, width=40)  # 稍微调整宽度
        self.single_file_label.pack(side=LEFT, fill=X, expand=True, padx=5)
        ttk.Button(file_frame, text="选择多个文件 (PDF/图片)", command=self.select_multiple_files).pack(side=LEFT,
                                                                                                        padx=(5, 0))
        self.multi_file_label = ttk.Label(file_frame, text="", width=20, anchor=W)  # 稍微调整宽度
        self.multi_file_label.pack(side=LEFT, padx=5)

        output_frame = ttk.Frame(main_frame, padding="0 5 0 5")
        output_frame.pack(fill=X, pady=8)
        ttk.Button(output_frame, text="选择输出目录", command=self.select_output_folder).pack(side=LEFT, padx=(0, 5))
        self.output_dir_label = ttk.Label(output_frame, textvariable=self.output_folder, anchor=W)
        self.output_dir_label.pack(side=LEFT, fill=X, expand=True, padx=5)

        opts_notebook = ttk.Notebook(main_frame, padding="2 5 2 2")
        opts_notebook.pack(fill=X, pady=5)

        ocr_opts_frame = ttk.Frame(opts_notebook, padding=10)
        opts_notebook.add(ocr_opts_frame, text='OCR 引擎')
        # ... (OCR 引擎和语言部分保持不变)
        engine_frame = ttk.Frame(ocr_opts_frame)
        engine_frame.pack(fill=X, pady=3)
        ttk.Label(engine_frame, text="选择引擎:").pack(side=LEFT, padx=(0, 5))
        pp_radio = ttk.Radiobutton(engine_frame, text="PP-Structure (推荐)", variable=self.ocr_engine_choice,
                                   value="PP-Structure")
        pp_radio.pack(side=LEFT, padx=5)
        ts_radio = ttk.Radiobutton(engine_frame, text="Tesseract (备选)", variable=self.ocr_engine_choice,
                                   value="Tesseract")
        ts_radio.pack(side=LEFT, padx=5)
        if not PPSTRUCTURE_AVAILABLE: pp_radio.config(state=DISABLED)
        if not TESSERACT_AVAILABLE: ts_radio.config(state=DISABLED)

        lang_frame = ttk.Frame(ocr_opts_frame)
        lang_frame.pack(fill=X, pady=3)
        ttk.Label(lang_frame, text="识别语言:").pack(side=LEFT, padx=(0, 5))
        lang_entry = ttk.Entry(lang_frame, textvariable=self.ocr_language, width=15)
        lang_entry.pack(side=LEFT, padx=5)
        ttk.Label(lang_frame, text="(PP用ch/en, Tess用chi_sim+eng)").pack(side=LEFT)

        # 新增：保存图像选项
        cb_save_images = ttk.Checkbutton(ocr_opts_frame, text="保存提取/输入的图像到子文件夹",
                                         variable=self.save_extracted_images)
        cb_save_images.pack(anchor=W, pady=(5, 0))

        preproc_opts_frame = ttk.Frame(opts_notebook, padding=10)
        opts_notebook.add(preproc_opts_frame, text='图像预处理 (主要影响Tesseract)')
        # ... (预处理选项部分保持不变)
        cb_osd = ttk.Checkbutton(preproc_opts_frame, text="自动旋转方向 (OSD, 需Tesseract)", variable=self.perform_osd)
        cb_osd.pack(anchor=W)
        cb_crop = ttk.Checkbutton(preproc_opts_frame, text="裁剪图像边界 (Tesseract流程)", variable=self.perform_crop)
        cb_crop.pack(anchor=W)
        cb_clahe = ttk.Checkbutton(preproc_opts_frame, text="增强对比度 (CLAHE, Tesseract流程)",
                                   variable=self.perform_clahe)
        cb_clahe.pack(anchor=W)
        cb_denoise = ttk.Checkbutton(preproc_opts_frame, text="降噪 (较慢, Tesseract流程)",
                                     variable=self.perform_denoise)
        cb_denoise.pack(anchor=W)
        if not TESSERACT_AVAILABLE:
            cb_osd.config(state=DISABLED)
            # Crop, CLAHE, Denoise 理论上可以用于任何图像，但当前代码主要在Tesseract流程中使用
            # 如果希望它们通用，需要调整 _preprocess_for_ocr 等函数的调用位置

        sr_opts_frame = ttk.Frame(opts_notebook, padding=10)
        opts_notebook.add(sr_opts_frame, text='超分辨率 (实验性)')
        # ... (超分辨率选项部分保持不变)
        cb_sr = ttk.Checkbutton(sr_opts_frame, text="启用超分辨率 (CARN, 需PyTorch)", variable=self.use_super_res)
        cb_sr.pack(anchor=W)
        sr_model_frame = ttk.Frame(sr_opts_frame)
        sr_model_frame.pack(fill=X, pady=3)
        ttk.Label(sr_model_frame, text="CARN模型路径:").pack(side=LEFT, padx=(0, 5))
        sr_entry = ttk.Entry(sr_model_frame, textvariable=self.carn_model_path, width=40)
        sr_entry.pack(side=LEFT, fill=X, expand=True, padx=5)
        ttk.Button(sr_model_frame, text="浏览...", command=self.select_carn_model).pack(side=LEFT)
        if not TORCH_AVAILABLE or not CARN_MODEL_DEF_AVAILABLE:
            cb_sr.config(state=DISABLED)
            sr_entry.config(state=DISABLED)
            # 找到按钮并禁用
            for child in sr_model_frame.winfo_children():
                if isinstance(child, ttk.Button) and child.cget('text') == "浏览...":
                    child.config(state=DISABLED)
                    break

        control_frame = ttk.Frame(main_frame, padding="0 5 0 0")
        control_frame.pack(fill=X, pady=5)
        self.total_progress = ttk.Progressbar(control_frame, orient=HORIZONTAL, length=100, mode='determinate')
        self.total_progress.pack(fill=X, pady=(0, 5))
        self.total_progress_label = ttk.Label(control_frame, text="准备就绪", anchor=W)
        self.total_progress_label.pack(fill=X)

        button_frame = ttk.Frame(main_frame, padding="0 10 0 0")
        button_frame.pack(pady=10)
        self.start_button = ttk.Button(button_frame, text="开始识别", command=self.start_ocr, width=15)
        self.start_button.pack(side=LEFT, padx=20)
        self.cancel_button = ttk.Button(button_frame, text="取消", command=self.cancel_ocr, width=15, state=DISABLED)
        self.cancel_button.pack(side=LEFT, padx=20)

        log_frame = ttk.LabelFrame(main_frame, text="运行日志", padding=10)
        log_frame.pack(fill=BOTH, expand=True, pady=(5, 0))
        self.log_text = Text(log_frame, wrap=WORD, height=10, state=DISABLED, borderwidth=1, relief="sunken")
        self.log_text.pack(side=LEFT, fill=BOTH, expand=True)
        sb = ttk.Scrollbar(log_frame, orient=VERTICAL, command=self.log_text.yview)
        sb.pack(side=RIGHT, fill=Y)
        self.log_text.config(yscrollcommand=sb.set)

    # --- 日志和UI更新方法 (保持不变) ---
    def log_message(self, m, level=logging.INFO):
        def update_log():
            if not self.root.winfo_exists(): return  # 检查窗口是否存在
            self.log_text.config(state=NORMAL)
            timestamp = strftime("%H:%M:%S", localtime())
            level_str = logging.getLevelName(level)
            prefix = f"{timestamp} [{level_str}] " if level > logging.INFO else f"{timestamp} - "
            self.log_text.insert(END, f"{prefix}{m}\n")
            self.log_text.see(END)
            self.log_text.config(state=DISABLED)

            # 同步到Python标准日志
            if level == logging.ERROR:
                logging.error(m)
            elif level == logging.WARNING:
                logging.warning(m)
            else:
                logging.info(m)

        try:
            self.root.after(0, update_log)
        except RuntimeError:  # 通常在窗口关闭后发生
            print(f"日志(UI关闭?): {m}")

    def update_progress(self, value, text):
        def update_ui():
            if not self.root.winfo_exists(): return  # 检查窗口是否存在
            safe_value = max(0, min(100, int(value)))
            self.total_progress['value'] = safe_value
            self.total_progress_label.config(text=text)

        try:
            self.root.after(0, update_ui)
        except RuntimeError:
            print(f"进度(UI关闭?): {text} ({value}%)")

    def update_button_state(self, is_running):
        def update_ui():
            if not self.root.winfo_exists(): return  # 检查窗口是否存在
            self.start_button.config(state=DISABLED if is_running else NORMAL)
            self.cancel_button.config(state=NORMAL if is_running else DISABLED)

        try:
            self.root.after(0, update_ui)
        except RuntimeError:
            pass  # 忽略窗口关闭后的错误

    # --- 文件选择 (修改支持图像) ---
    def select_single_file(self):
        # 修改 filetypes 以包含图像
        filetypes = [
            ("所有支持的文件", "*.pdf *.png *.jpg *.jpeg *.bmp *.tif *.tiff"),
            ("PDF 文件", "*.pdf"),
            ("图像文件", "*.png *.jpg *.jpeg *.bmp *.tif *.tiff")
        ]
        p = filedialog.askopenfilename(title="选择单个 PDF 或图像文件", filetypes=filetypes)
        if p:
            self.input_files = [p]
            self.single_file_label.config(text=os.path.basename(p))
            self.multi_file_label.config(text="")
            self.log_message(f"已选单个文件: {p}")

    def select_multiple_files(self):
        # 修改 filetypes 以包含图像
        filetypes = [
            ("所有支持的文件", "*.pdf *.png *.jpg *.jpeg *.bmp *.tif *.tiff"),
            ("PDF 文件", "*.pdf"),
            ("图像文件", "*.png *.jpg *.jpeg *.bmp *.tif *.tiff")
        ]
        ps = filedialog.askopenfilenames(title="选择多个 PDF 或图像文件", filetypes=filetypes)
        if ps:
            self.input_files = list(ps)
            self.multi_file_label.config(text=f"已选 {len(ps)} 个文件")
            self.single_file_label.config(text="")
            self.log_message(f"已选 {len(ps)} 个文件")

    def select_output_folder(self):
        # (保持不变)
        d = filedialog.askdirectory(title="选择输出文件夹")
        if d:
            self.output_folder.set(d)
            self.log_message(f"输出目录: {d}")

    def select_carn_model(self):
        # (保持不变)
        p = filedialog.askopenfilename(title="选择 CARN 模型权重 (.pth)", filetypes=[("PyTorch Model", "*.pth")])
        if p:
            self.carn_model_path.set(p)
            self.log_message(f"CARN 模型路径设置为: {p}")

    # --- OCR 控制 (start_ocr, cancel_ocr 基本保持不变, 内部检查可能微调) ---
    def start_ocr(self):
        # 检查引擎可用性
        if self.ocr_engine_choice.get() == "":
            messagebox.showerror("错误", "没有可用的 OCR 引擎被选中或配置成功。");
            return
        if not TESSERACT_AVAILABLE and not PPSTRUCTURE_AVAILABLE:
            messagebox.showerror("错误", "未安装 Tesseract 或 PaddleOCR，无法执行 OCR。");
            return

        # 特定引擎的依赖检查
        if self.ocr_engine_choice.get() == "Tesseract":
            if not TESSERACT_PATH:
                messagebox.showerror("错误", "Tesseract 未找到或未正确配置路径。");
                return
            if not TESSDATA_PREFIX and not os.getenv('TESSDATA_PREFIX') and not TESSDATA_DIR:  # 进一步检查
                if not messagebox.askyesno("Tesseract警告",
                                           "未能确认 TESSDATA_PREFIX 或找到 tessdata 目录，Tesseract 可能因语言文件缺失而失败。\n是否继续？"):
                    return
        elif self.ocr_engine_choice.get() == "PP-Structure" and not PPSTRUCTURE_AVAILABLE:
            messagebox.showerror("错误", "PaddleOCR (PP-Structure) 未安装或导入失败。");
            return

        # 超分依赖检查
        if self.use_super_res.get():
            if not TORCH_AVAILABLE or not CARN_MODEL_DEF_AVAILABLE:
                messagebox.showerror("错误", "PyTorch 或 CARN 模型定义未找到，无法启用超分辨率。")
                self.use_super_res.set(False);
                return
            if not os.path.exists(self.carn_model_path.get()):
                messagebox.showerror("错误", f"CARN 模型文件未找到: {self.carn_model_path.get()}");
                return

        if not self.input_files:
            messagebox.showerror("错误", "请先选择待识别的文件。");
            return
        if self.running:
            messagebox.showwarning("提示", "任务已在运行中。");
            return

        self.running = True
        self.update_button_state(True)
        self.update_progress(0, "准备开始...")
        if self.log_text.winfo_exists():  # 检查 Text 组件是否存在
            self.log_text.config(state=NORMAL);
            self.log_text.delete(1.0, END);
            self.log_text.config(state=DISABLED)

        self.log_message(">>> 开始 OCR 任务 <<<")
        self.log_message(
            f"引擎: {self.ocr_engine_choice.get()}, 语言: {self.ocr_language.get()}, 保存图像={self.save_extracted_images.get()}, 超分={self.use_super_res.get()}, OSD={self.perform_osd.get()}, 裁剪={self.perform_crop.get()}, CLAHE={self.perform_clahe.get()}, 去噪={self.perform_denoise.get()}")

        # 创建并启动处理线程
        thread = threading.Thread(target=self.process_files_thread, daemon=True)
        thread.start()

    def cancel_ocr(self):
        # (保持不变)
        if self.running:
            if messagebox.askyesno("确认", "确定要取消当前任务吗？"):
                self.running = False
                self.log_message(">>> 正在尝试取消任务... <<<", logging.WARNING)
        else:
            self.log_message("没有正在运行的任务。")

    # --- 模型加载与释放 (保持不变) ---
    def _load_ppstructure_model(self):
        if self.ppstructure_model_instance is None and PPSTRUCTURE_AVAILABLE:
            self.log_message("首次使用，正在加载 PP-Structure 模型...", logging.INFO)
            try:
                use_gpu = False  # 默认CPU，除非显式检测到CUDA
                if paddle.device.is_compiled_with_cuda():
                    try:
                        if paddle.device.cuda.device_count() > 0:
                            use_gpu = True
                    except Exception as e:  # 处理 paddle.device.cuda 不可用的情况
                        self.log_message(f"检测CUDA设备时出错: {e}，将使用CPU。", logging.WARNING)

                self.log_message(f"PP-Structure 将使用 {'GPU' if use_gpu else 'CPU'}。", logging.INFO)

                # 从 self.ocr_language 中提取主语言给 PPStructure
                # PPStructure 通常使用 'ch', 'en' 等，而不是 Tesseract 的 'chi_sim+eng'
                lang_for_pp = self.ocr_language.get().split('+')[0]
                if lang_for_pp == 'chi_sim': lang_for_pp = 'ch'  # 修正

                self.ppstructure_model_instance = PPStructure(
                    show_log=False,  # 通常在 PaddleOCR 内部关闭，我们用自己的日志
                    use_gpu=use_gpu,
                    lang=lang_for_pp  # 使用提取的语言
                )
                self.log_message("PP-Structure 模型加载成功。", logging.INFO)
                return True
            except Exception as e:
                self.log_message(f"错误：加载 PP-Structure 模型失败: {e}", logging.ERROR)
                traceback.print_exc()
                self.ppstructure_model_instance = None
                return False
        elif self.ppstructure_model_instance:
            return True
        else:
            return False

    def _load_carn_model(self):
        if self.carn_model_instance is None and TORCH_AVAILABLE and CARN_MODEL_DEF_AVAILABLE:
            model_path = self.carn_model_path.get()
            if not os.path.exists(model_path):
                self.log_message(f"错误：CARN 模型权重文件不存在: {model_path}", logging.ERROR)
                return False
            self.log_message(f"首次使用，正在加载 CARN 超分模型: {model_path}", logging.INFO)
            try:
                self.carn_model_instance = CARN()
                device = torch.device('cpu')  # 强制 CPU
                self.carn_model_instance.load_state_dict(torch.load(model_path, map_location=device))
                self.carn_model_instance.eval()
                self.carn_model_instance.to(device)
                self.log_message("CARN 模型加载成功 (CPU)。", logging.INFO)
                return True
            except Exception as e:
                self.log_message(f"错误：加载 CARN 模型失败: {e}", logging.ERROR)
                traceback.print_exc()
                self.carn_model_instance = None
                return False
        elif self.carn_model_instance:
            return True
        else:  # 不可用
            return False

    # --- 核心处理线程 (重大修改) ---
    def process_files_thread(self):
        total_files = len(self.input_files)
        processed_count = 0
        error_count = 0
        thread_start_time = perf_counter()

        engine_choice = self.ocr_engine_choice.get()
        use_sr = self.use_super_res.get()
        save_images_flag = self.save_extracted_images.get()  # 获取是否保存图像的标志

        ppstructure_ready = False
        if engine_choice == "PP-Structure":
            ppstructure_ready = self._load_ppstructure_model()
            if not ppstructure_ready:
                self.log_message("PP-Structure 加载失败，尝试切换到 Tesseract。", logging.ERROR)
                if TESSERACT_AVAILABLE:
                    engine_choice = "Tesseract"
                    self.ocr_engine_choice.set("Tesseract")  # 更新UI反映切换
                    self.log_message("已切换到 Tesseract 引擎。", logging.INFO)
                else:
                    self.log_message("Tesseract 也不可用，无法继续。", logging.CRITICAL)
                    self.running = False
                    self.update_button_state(False)
                    self.update_progress(0, "错误：OCR引擎加载失败")
                    return

        carn_ready = False
        if use_sr:  # 只有在勾选了超分时才加载
            carn_ready = self._load_carn_model()
            if not carn_ready:
                self.log_message("CARN 模型加载失败，超分辨率功能已禁用。", logging.ERROR)
                use_sr = False  # 禁用超分，即使之前勾选了
                self.use_super_res.set(False)  # 更新UI反映禁用

        if engine_choice == "Tesseract" and not TESSERACT_PATH:
            self.log_message("错误: Tesseract 未配置，无法作为处理方案。", logging.CRITICAL)
            self.running = False
            self.update_button_state(False)
            self.update_progress(0, "错误：Tesseract引擎不可用")
            return

        try:
            for idx, file_path in enumerate(self.input_files):
                if not self.running:
                    self.log_message("任务已被用户取消。")
                    break

                file_num = idx + 1
                base_name_with_ext = os.path.basename(file_path)
                base_name_no_ext = os.path.splitext(base_name_with_ext)[0]
                file_ext = os.path.splitext(file_path)[1].lower()

                self.log_message(f"\n>> 文件 {file_num}/{total_files}: {base_name_with_ext}", logging.INFO)
                file_start_time = perf_counter()
                self.update_progress((idx / total_files) * 100,
                                     f"处理中: {base_name_with_ext} ({file_num}/{total_files})")

                # 创建用于存放该文件相关图片的子文件夹
                image_output_subfolder = None
                if save_images_flag:
                    image_output_subfolder = os.path.join(self.output_folder.get(), f"{base_name_no_ext}_images")
                    try:
                        os.makedirs(image_output_subfolder, exist_ok=True)
                        self.log_message(f"  图像将保存到: {image_output_subfolder}")
                    except OSError as e:
                        self.log_message(f"  无法创建图像子文件夹 {image_output_subfolder}: {e}", logging.ERROR)
                        image_output_subfolder = None  # 创建失败则不保存

                current_file_text_results = []

                # --- 根据文件类型处理 ---
                if file_ext == ".pdf":
                    doc = None
                    try:
                        doc = fitz.open(file_path)
                        num_pages = len(doc)
                        self.log_message(f"  PDF 共 {num_pages} 页。")
                        for i in range(num_pages):
                            if not self.running: break
                            page_num_actual = i + 1  # 1-based
                            self.log_message(
                                f"  处理 PDF 页面 {page_num_actual}/{num_pages} (引擎: {engine_choice})...")
                            page_ocr_start_time = perf_counter()

                            page_progress = ((file_num - 1) / total_files + (
                                        page_num_actual / num_pages) / total_files) * 100
                            self.update_progress(page_progress,
                                                 f"文件 {file_num}/{total_files} - PDF页 {page_num_actual}/{num_pages} ({engine_choice})...")

                            page_image_cv = None
                            try:
                                page = doc.load_page(i)
                                pix = page.get_pixmap(dpi=300)  # 提高DPI获取更高质量图像
                                img_pil = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
                                page_image_cv = cv2.cvtColor(np.array(img_pil), cv2.COLOR_RGB2BGR)

                                if image_output_subfolder:
                                    img_save_path = os.path.join(image_output_subfolder, f"page_{page_num_actual}.png")
                                    try:
                                        cv2.imwrite(img_save_path, page_image_cv)
                                        self.log_message(f"    已保存页面图像: {img_save_path}", level=logging.DEBUG)
                                    except Exception as e_save:
                                        self.log_message(f"    保存页面图像失败: {e_save}", logging.WARNING)

                                # 对提取的页面图像进行 OCR
                                page_text = ""
                                if engine_choice == "PP-Structure" and ppstructure_ready:
                                    page_text = self._process_single_image_with_ppstructure(page_image_cv,
                                                                                            use_sr and carn_ready,
                                                                                            f"PDF页 {page_num_actual}")
                                elif engine_choice == "Tesseract" and TESSERACT_AVAILABLE:
                                    page_text = self._process_single_image_with_tesseract(page_image_cv,
                                                                                          use_sr and carn_ready,
                                                                                          f"PDF页 {page_num_actual}")
                                else:
                                    page_text = f"\n--- PDF 第 {page_num_actual} 页 (无可用 OCR 引擎) ---\n"
                                    error_count += 1
                                current_file_text_results.append(page_text)

                            except Exception as page_err:
                                self.log_message(f"    处理 PDF 页面 {page_num_actual} 时发生错误: {page_err}",
                                                 logging.ERROR)
                                traceback.print_exc()
                                current_file_text_results.append(
                                    f"\n--- PDF 第 {page_num_actual} 页 (处理错误: {page_err}) ---\n")
                                error_count += 1
                            finally:
                                page_ocr_end_time = perf_counter()
                                self.log_message(
                                    f"    PDF 页面 {page_num_actual} 处理完成 (耗时 {page_ocr_end_time - page_ocr_start_time:.2f} 秒)。")

                        if doc: doc.close()
                    except fitz.fitz.FileNotFoundError:
                        self.log_message(f"错误：文件未找到 {file_path}", logging.ERROR);
                        error_count += 1
                        current_file_text_results.append(f"[错误: 文件 {base_name_with_ext} 未找到]")
                    except Exception as pdf_err:
                        self.log_message(f"处理 PDF {base_name_with_ext} 时发生严重错误: {pdf_err}", logging.CRITICAL)
                        traceback.print_exc()
                        current_file_text_results.append(f"[错误: 处理 PDF {base_name_with_ext} 失败]")
                        error_count += 1
                    finally:
                        if doc: doc.close()

                elif file_ext in ['.png', '.jpg', '.jpeg', '.bmp', '.tif', '.tiff']:
                    self.log_message(f"  处理图像文件 (引擎: {engine_choice})...")
                    img_ocr_start_time = perf_counter()
                    try:
                        # 使用 OpenCV 读取图像，因为它返回 BGR numpy 数组，与后续处理一致
                        input_image_cv = cv2.imread(file_path)
                        if input_image_cv is None:
                            raise IOError(f"无法加载图像文件: {file_path}")

                        if image_output_subfolder:
                            # 直接保存原始图像或一个副本
                            img_save_path = os.path.join(image_output_subfolder, base_name_with_ext)
                            try:
                                cv2.imwrite(img_save_path, input_image_cv)
                                self.log_message(f"    已保存输入图像: {img_save_path}", level=logging.DEBUG)
                            except Exception as e_save:
                                self.log_message(f"    保存输入图像失败: {e_save}", logging.WARNING)

                        # 对图像文件进行 OCR
                        image_text = ""
                        if engine_choice == "PP-Structure" and ppstructure_ready:
                            image_text = self._process_single_image_with_ppstructure(input_image_cv,
                                                                                     use_sr and carn_ready, "图像文件")
                        elif engine_choice == "Tesseract" and TESSERACT_AVAILABLE:
                            image_text = self._process_single_image_with_tesseract(input_image_cv,
                                                                                   use_sr and carn_ready, "图像文件")
                        else:
                            image_text = f"\n--- 图像文件 {base_name_with_ext} (无可用 OCR 引擎) ---\n"
                            error_count += 1
                        current_file_text_results.append(image_text)

                    except Exception as img_err:
                        self.log_message(f"  处理图像文件 {base_name_with_ext} 时发生错误: {img_err}", logging.ERROR)
                        traceback.print_exc()
                        current_file_text_results.append(f"[错误: 处理图像 {base_name_with_ext} 失败: {img_err}]")
                        error_count += 1
                    finally:
                        img_ocr_end_time = perf_counter()
                        self.log_message(
                            f"  图像文件 {base_name_with_ext} 处理完成 (耗时 {img_ocr_end_time - img_ocr_start_time:.2f} 秒)。")
                else:
                    self.log_message(f"  不支持的文件类型: {file_ext}。跳过文件 {base_name_with_ext}。", logging.WARNING)
                    current_file_text_results.append(f"[信息: 文件 {base_name_with_ext} 类型不受支持，已跳过]")
                    # 不计为错误，但也不计为成功处理
                    # 如果希望计为错误，可以 error_count += 1

                if not self.running:
                    self.log_message(f"处理 {base_name_with_ext} 期间任务被取消。")
                    break

                # --- 保存单个文件的聚合文本结果 ---
                final_text_for_file = "".join(current_file_text_results)
                if final_text_for_file and not (
                        "[错误:" in final_text_for_file or "处理错误" in final_text_for_file or "失败" in final_text_for_file):
                    output_filename_txt = f"{base_name_no_ext}_ocr.txt"
                    output_path_txt = os.path.join(self.output_folder.get(), output_filename_txt)
                    try:
                        with open(output_path_txt, "w", encoding="utf-8") as fw:
                            fw.write(final_text_for_file)
                        file_end_time = perf_counter()
                        self.log_message(
                            f"文本结果已保存 (耗时 {file_end_time - file_start_time:.2f} 秒): {output_path_txt}")
                        processed_count += 1
                    except IOError as e:
                        self.log_message(f"错误：无法保存文本文件 {output_path_txt}: {e}", logging.ERROR)
                        error_count += 1
                elif not final_text_for_file.strip() and not any(
                        err_indicator in final_text_for_file for err_indicator in ["[错误:", "失败", "处理错误"]):
                    self.log_message(f"文件 {base_name_with_ext} 未产生有效文本输出 (可能为空白或无内容)。",
                                     logging.WARNING)
                    # 可以选择是否将这种情况视为错误
                else:  # 存在错误指示或文本为空但之前已有错误日志
                    if not any(err_indicator in final_text_for_file for err_indicator in
                               ["[错误:", "失败", "处理错误"]):  # 如果错误信息未写入文本
                        self.log_message(f"文件 {base_name_with_ext} 处理失败或跳过，未生成有效文本。", logging.WARNING)
                    # error_count 已在发生具体错误时递增

            # 循环结束
        except Exception as e:
            self.log_message(f"处理文件过程中发生严重意外错误: {e}\n{traceback.format_exc()}", logging.CRITICAL)
            error_count = total_files  # 标记所有文件失败
        finally:
            thread_end_time = perf_counter()
            duration = thread_end_time - thread_start_time
            final_message = ""
            if not self.running and processed_count < total_files:
                final_message = f"任务已取消。成功处理 {processed_count} 个文件。"
            elif error_count > 0:
                final_message = f"处理完成，共 {total_files} 文件，成功 {processed_count} 个，失败或含错误 {error_count} 个。"
            else:
                final_message = f"所有 {total_files} 个文件处理完成！"

            self.log_message(f"\n{final_message} 总耗时: {duration:.2f} 秒。", logging.INFO)
            self.update_progress(100, final_message)
            self.running = False
            self.update_button_state(False)

            # 可选：清理模型
            # self.ppstructure_model_instance = None
            # self.carn_model_instance = None
            # if TORCH_AVAILABLE and torch.cuda.is_available(): torch.cuda.empty_cache()

    # --- 单个图像处理函数 (基于原PDF页面处理函数修改) ---
    # 这些函数现在接收 cv2 图像数据 (BGR格式)

    def _process_single_image_with_ppstructure(self, img_cv_bgr, apply_sr, image_description="图像"):
        """使用 PP-Structure 处理单个图像 (cv2 BGR格式)"""
        if not self.ppstructure_model_instance:
            return f"[错误: PP-Structure 模型未加载 ({image_description})]"

        page_content = f"\n--- {image_description} (PP-Structure 处理失败) ---\n"
        try:
            img_to_process = img_cv_bgr.copy()  # 操作副本

            # 1. 应用超分辨率 (如果启用且模型可用)
            if apply_sr and self.carn_model_instance:  # 确保模型实例存在
                self.log_message(f"    对 {image_description} 应用 CARN 超分辨率...")
                sr_start_time = perf_counter()
                resolved_img = self._apply_carn_super_resolution(img_to_process)  # _apply_carn_super_resolution 已有日志
                if resolved_img is not None:
                    img_to_process = resolved_img
                    sr_end_time = perf_counter()
                    self.log_message(f"      CARN 超分完成 (耗时 {sr_end_time - sr_start_time:.2f} 秒)。")
                else:  # 超分失败
                    self.log_message(f"      CARN 超分失败，对 {image_description} 使用原始图像。", logging.WARNING)

            # 2. 调用 PP-Structure 模型
            self.log_message(f"    调用 PP-Structure 分析 {image_description}...")
            pp_start_time = perf_counter()
            # PP-Structure 输入通常是 BGR numpy 数组
            results = self.ppstructure_model_instance(img_to_process)
            pp_end_time = perf_counter()
            self.log_message(f"      PP-Structure 分析完成 (耗时 {pp_end_time - pp_start_time:.2f} 秒)。")

            # 3. 解析并格式化结果
            page_blocks_text = []
            if results:
                for item in results:
                    block_type = item.get('type', 'Unknown').lower()
                    res_content = item.get('res', '')  # paddleocr >=2.6, res 是(text, score)或表格html

                    # 统一处理 res_content，如果是元组取第一个元素（文本）
                    actual_text = ""
                    if isinstance(res_content, tuple) and len(res_content) > 0:
                        actual_text = str(res_content[0])  # 确保是字符串
                    elif isinstance(res_content, str):
                        actual_text = res_content

                    if block_type in ['text', 'title', 'list', 'header', 'footer']:
                        page_blocks_text.append(actual_text)
                    elif block_type == 'table':
                        page_blocks_text.append(f"\n[表格开始]\n{actual_text}\n[表格结束]\n")
                    elif block_type == 'figure':
                        page_blocks_text.append(f"[图片区域: {item.get('img_idx', '')}]")  # PP-Structure 可能返回图片索引
                    else:  # 其他或未知类型
                        if actual_text:  # 只添加有内容的未知块
                            page_blocks_text.append(f"[{block_type.upper()}]: {actual_text}")

                if page_blocks_text:
                    page_content = f"\n--- {image_description} (PP-Structure) ---\n" + "\n".join(
                        page_blocks_text) + "\n"
                else:
                    page_content = f"\n--- {image_description} (PP-Structure 未识别到内容) ---\n"
            else:
                page_content = f"\n--- {image_description} (PP-Structure 未返回结果) ---\n"
            return page_content

        except Exception as page_err:
            self.log_message(f"    处理 {image_description} (PP-Structure) 时发生错误: {page_err}", logging.ERROR)
            traceback.print_exc()
            return f"\n--- {image_description} (PP-Structure 处理时发生错误: {page_err}) ---\n"

    def _process_single_image_with_tesseract(self, img_cv_bgr, apply_sr, image_description="图像"):
        """使用 Tesseract 处理单个图像 (cv2 BGR格式)"""
        if not TESSERACT_AVAILABLE:
            return f"[错误: Tesseract 不可用 ({image_description})]"

        page_content = f"\n--- {image_description} (Tesseract 处理失败) ---\n"
        try:
            img_to_process = img_cv_bgr.copy()

            # 1. 应用超分辨率
            if apply_sr and self.carn_model_instance:
                self.log_message(f"    对 {image_description} 应用 CARN 超分辨率...")
                sr_start_time = perf_counter()
                resolved_img = self._apply_carn_super_resolution(img_to_process)
                if resolved_img is not None:
                    img_to_process = resolved_img
                    sr_end_time = perf_counter()
                    self.log_message(f"      CARN 超分完成 (耗时 {sr_end_time - sr_start_time:.2f} 秒)。")
                else:
                    self.log_message(f"      CARN 超分失败，对 {image_description} 使用原始图像。", logging.WARNING)

            # 2. 预处理 I: 旋转和裁剪 (OSD依赖Tesseract自身)
            # 注意: _preprocess_for_layout 内部已有日志
            img_layout_processed = self._preprocess_for_layout(img_to_process)  # 这个函数内部检查TESSERACT_AVAILABLE
            if img_layout_processed is None:  # 预处理失败
                self.log_message(f"    {image_description} 布局预处理失败，跳过后续Tesseract处理。", logging.WARNING)
                return f"\n--- {image_description} (Tesseract 布局预处理失败) ---\n"

            # 3. 预处理 II: OCR 准备 (灰度, CLAHE, 去噪, 二值化)
            self.log_message(f"    对 {image_description} 进行 OCR 预处理 (Tesseract)...")
            # _preprocess_for_ocr 返回 PIL Image
            img_ocr_ready_pil = self._preprocess_for_ocr(img_layout_processed)
            if img_ocr_ready_pil is None:
                self.log_message(f"    {image_description} OCR预处理失败，跳过Tesseract OCR。", logging.WARNING)
                return f"\n--- {image_description} (Tesseract OCR预处理失败) ---\n"

            # 4. 执行整页 OCR (Tesseract)
            self.log_message(f"    对 {image_description} 执行整页 Tesseract OCR...")
            ocr_start_time = perf_counter()
            # _ocr_text_block_tesseract 内部有日志
            ocr_result = self._ocr_text_block_tesseract(img_ocr_ready_pil,
                                                        psm=3)  # PSM 3: Auto page segmentation with OSD
            ocr_end_time = perf_counter()
            self.log_message(f"      Tesseract OCR 完成 (耗时 {ocr_end_time - ocr_start_time:.2f} 秒)。")

            page_content = f"\n--- {image_description} (Tesseract) ---\n{ocr_result}\n"
            return page_content

        except Exception as page_err:
            self.log_message(f"    处理 {image_description} (Tesseract) 时发生错误: {page_err}", logging.ERROR)
            traceback.print_exc()
            return f"\n--- {image_description} (Tesseract 处理时发生错误: {page_err}) ---\n"

    # --- 超分辨率辅助方法 (保持不变, 但日志中可以指明是对哪一页/图像操作) ---
    def _apply_carn_super_resolution(self, img_cv_bgr):
        if not self.carn_model_instance:
            self.log_message("      CARN 模型未加载，无法超分。", logging.WARNING)
            return None
        try:
            device = torch.device('cpu')
            img_pil = Image.fromarray(cv2.cvtColor(img_cv_bgr, cv2.COLOR_BGR2RGB))
            lr_tensor = ToTensor()(img_pil).unsqueeze(0).to(device)
            with torch.no_grad():
                sr_tensor = self.carn_model_instance(lr_tensor)
            sr_image_pil = ToPILImage()(sr_tensor.squeeze(0).cpu())
            sr_image_cv_bgr = cv2.cvtColor(np.array(sr_image_pil), cv2.COLOR_RGB2BGR)
            return sr_image_cv_bgr
        except Exception as e:
            self.log_message(f"      CARN 超分辨率处理失败: {e}", logging.ERROR)
            # traceback.print_exc() # 可能过于详细，视情况启用
            return None

    # --- Tesseract 相关辅助方法 (保持不变) ---
    def _preprocess_for_layout(self, img_cv_bgr):
        """Tesseract 流程的预处理 I: 旋转和裁剪. 返回处理后的CV2 BGR图像或None"""
        processed_img = img_cv_bgr.copy()
        if self.perform_osd.get() and TESSERACT_AVAILABLE:
            self.log_message("      执行 OSD 与旋转 (Tesseract)...")
            rotated_img = self._run_osd_and_rotate(processed_img)  # 内部有日志
            if rotated_img is not None:
                processed_img = rotated_img
            # else: OSD失败，使用原图或之前处理的图

        if self.perform_crop.get():  # 裁剪不依赖 Tesseract 本身，但逻辑上通常与 Tesseract 流程结合
            self.log_message("      执行边界裁剪...")
            cropped_img = self._crop_borders(processed_img)  # 内部有日志
            if cropped_img is not None and cropped_img.shape[0] > 10 and cropped_img.shape[1] > 10:
                processed_img = cropped_img
            # else: 裁剪失败或区域过小，使用原图或之前处理的图

        return processed_img

    def _preprocess_for_ocr(self, img_cv_bgr):
        """Tesseract 流程的预处理 II: 灰度, CLAHE, 去噪, 二值化. 返回 PIL Image 或 None"""
        try:
            gray = cv2.cvtColor(img_cv_bgr, cv2.COLOR_BGR2GRAY)
            processed_gray = gray

            if self.perform_clahe.get():
                self.log_message("        应用 CLAHE...", level=logging.DEBUG)
                clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
                processed_gray = clahe.apply(processed_gray)

            if self.perform_denoise.get():
                self.log_message("        应用降噪...", level=logging.DEBUG)
                # 参数可以调整, h 值影响去噪强度
                processed_gray = cv2.fastNlMeansDenoising(processed_gray, None, h=10, templateWindowSize=7,
                                                          searchWindowSize=21)

            # 二值化对于Tesseract通常是推荐的
            self.log_message("        应用自适应二值化...", level=logging.DEBUG)
            # ADAPTIVE_THRESH_MEAN_C 有时对于背景复杂图像效果更好
            binary = cv2.adaptiveThreshold(processed_gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
                                           cv2.THRESH_BINARY, 15, 7)  # blockSize 和 C 值可调

            return Image.fromarray(binary)  # Tesseract 通常接收 PIL Image
        except Exception as e:
            self.log_message(f"        OCR 预处理 (灰度/CLAHE/去噪/二值化) 失败: {e}", logging.ERROR)
            return None

    def _run_osd_and_rotate(self, image_cv_bgr):
        if not TESSERACT_AVAILABLE:
            self.log_message("        Tesseract OSD 跳过 (Tesseract 不可用)。", logging.WARNING)
            return image_cv_bgr
        try:
            # OSD通常在灰度图上效果更好
            gray = cv2.cvtColor(image_cv_bgr, cv2.COLOR_BGR2GRAY)
            # 使用 psm 0 进行 OSD
            osd_data = pytesseract.image_to_osd(gray, config='--psm 0', output_type=Output.DICT)
            angle = osd_data.get('rotate', 0)
            script = osd_data.get('script', 'Unknown')
            confidence = osd_data.get('orientation_conf', 0)  # 获取方向置信度
            self.log_message(f"        OSD结果: 旋转角度={angle}, 文字={script}, 方向置信度={confidence:.2f}")

            # 根据置信度决定是否旋转，例如置信度大于某个阈值
            # Tesseract 的角度是逆时针的，cv2.getRotationMatrix2D 的 angle 是顺时针的
            # 所以如果Tesseract说旋转90度，意味着图像内容需要逆时针转90度才能正过来，
            # 即图像本身需要顺时针旋转 -90 度。
            # 但 pytesseract image_to_osd 返回的 'rotate' 是图像需要被旋转的角度以使其 upright.
            # 所以我们直接使用 -angle。
            if angle != 0 and confidence > 1.0:  # 设定一个置信度阈值，比如1.0
                self.log_message(f"        根据OSD旋转图像 {-angle} 度...")
                (h, w) = image_cv_bgr.shape[:2]
                center = (w // 2, h // 2)
                # 使用 pytesseract 返回的 angle, 但cv2旋转是逆时针为正，所以用-angle
                M = cv2.getRotationMatrix2D(center, -angle, 1.0)
                # 使用白色填充旋转后的边界
                rotated = cv2.warpAffine(image_cv_bgr, M, (w, h),
                                         flags=cv2.INTER_CUBIC,
                                         borderMode=cv2.BORDER_CONSTANT,
                                         borderValue=(255, 255, 255))
                return rotated
            else:
                self.log_message("        无需旋转或OSD置信度低。")
                return image_cv_bgr
        except (TesseractNotFoundError, TesseractError) as e:
            # 提取错误信息的第一行，避免过长日志
            error_detail = str(e).split('\n', 1)[0]
            self.log_message(f"        Tesseract OSD 失败: {error_detail}", logging.ERROR)
            return image_cv_bgr  # 返回原图
        except Exception as e:
            self.log_message(f"        OSD或旋转过程中发生意外错误: {e}", logging.ERROR)
            return image_cv_bgr  # 返回原图

    def _crop_borders(self, image_cv_bgr, border_threshold=200, min_area_ratio=0.5, padding=5):
        """检测并裁剪图像边框. 返回处理后的CV2 BGR图像或原图"""
        try:
            gray = cv2.cvtColor(image_cv_bgr, cv2.COLOR_BGR2GRAY)
            # 反转二值化，使内容为白色，背景为黑色，以便寻找最大轮廓（内容区域）
            _, thresh = cv2.threshold(gray, border_threshold, 255, cv2.THRESH_BINARY_INV)

            contours, _ = cv2.findContours(thresh, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
            if not contours:
                self.log_message("        边界裁剪：未找到轮廓。", logging.DEBUG)
                return image_cv_bgr

            # 找到最大的轮廓，假设它是主要内容区域
            max_contour = max(contours, key=cv2.contourArea)
            area = cv2.contourArea(max_contour)
            img_area = image_cv_bgr.shape[0] * image_cv_bgr.shape[1]

            if area / img_area < min_area_ratio:
                self.log_message(
                    f"        边界裁剪：最大轮廓区域过小 ({area / img_area:.2f} < {min_area_ratio})，跳过裁剪。",
                    logging.DEBUG)
                return image_cv_bgr

            x, y, w, h = cv2.boundingRect(max_contour)

            # 添加一些内边距，避免裁剪到文字
            x1 = max(0, x - padding)
            y1 = max(0, y - padding)
            x2 = min(image_cv_bgr.shape[1], x + w + padding)
            y2 = min(image_cv_bgr.shape[0], y + h + padding)

            # 确保裁剪后的区域有效
            if x2 > x1 and y2 > y1:
                cropped = image_cv_bgr[y1:y2, x1:x2]
                self.log_message("        边界裁剪完成。", logging.DEBUG)
                return cropped
            else:
                self.log_message("        边界裁剪：计算得到的裁剪区域无效，跳过。", logging.DEBUG)
                return image_cv_bgr
        except Exception as e:
            self.log_message(f"        边界裁剪出错: {e}", logging.ERROR)
            return image_cv_bgr  # 出错时返回原图

    def _ocr_text_block_tesseract(self, img_block_pil, psm=3):
        """使用 Tesseract 对 PIL 图像块执行 OCR"""
        if not TESSERACT_AVAILABLE:
            return "[错误: Tesseract 不可用]"
        try:
            lang_orig = self.ocr_language.get()
            # 确保语言格式正确 Tesseract: 'chi_sim+eng' 或 'eng'
            # 如果是 'ch' 或类似，尝试转换为 'chi_sim'
            if '+' in lang_orig:  # 已经是组合语言
                lang_tess = lang_orig
            elif lang_orig.lower() == 'ch':
                lang_tess = 'chi_sim'
            elif lang_orig.lower() == 'en':
                lang_tess = 'eng'
            else:  # 其他单语言直接使用，或根据需要添加转换规则
                lang_tess = lang_orig

            # oem 3 是默认的 LSTM 引擎
            # psm 可以根据具体情况调整，3 (auto page seg with OSD) 或 6 (assume a single uniform block of text) 或 11 (sparse text with OSD)
            # 对于已经预处理和分割的块，psm 6 可能更好，但这里是整页，用 psm 3 或 11
            config = f'--oem 3 --psm {psm}'
            text = pytesseract.image_to_string(img_block_pil, lang=lang_tess, config=config)
            return text.strip() if text else "[Tesseract识别为空]"
        except (TesseractNotFoundError, TesseractError) as e:
            error_detail = str(e).split('\n', 1)[0]
            self.log_message(f"        OCR (Tesseract) 失败: {error_detail} (语言: {lang_tess})", logging.ERROR)
            return f"[OCR 错误: {error_detail}]"
        except Exception as e:
            self.log_message(f"        OCR (Tesseract) 发生意外错误: {e}", logging.ERROR)
            return f"[OCR 错误: {e}]"


# --- 主程序入口 ---
if __name__ == "__main__":
    root = Tk()
    if platform.system() == "Windows":
        try:
            from ctypes import windll

            windll.shcore.SetProcessDpiAwareness(1)  # 尝试设置DPI感知
        except Exception as e:
            print(f"无法设置 DPI 感知 (仅Windows相关): {e}")

    app = FileOCRApp(root)  # 使用新的类名
    root.mainloop()