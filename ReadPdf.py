import os
import platform
import shutil
import threading
import traceback
import logging
from time import strftime, localtime, perf_counter
from tkinter import *
from tkinter import ttk, filedialog, messagebox

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
    # 未安装 pytesseract 库
    print("警告：未找到 pytesseract 库，Tesseract 相关功能不可用。")
    TESSERACT_AVAILABLE = False
    TesseractError = Exception       # 定义通用异常占位
    TesseractNotFoundError = Exception

# PaddleOCR PP-Structure
try:
    import paddle
    # 尝试导入 PPStructure，若底层 DLL 加载失败会抛出 OSError
    from paddleocr import PPStructure
    PPSTRUCTURE_AVAILABLE = True
    print("PaddleOCR PP-Structure 可用。")
except ImportError:
    # 未安装 paddle 或 paddleocr
    print("警告：未找到 paddlepaddle 或 paddleocr 库，PP-Structure 功能不可用。")
    PPSTRUCTURE_AVAILABLE = False
    PPStructure = None               # 定义空占位，避免后续 NameError
except OSError as e:
    # 底层依赖加载失败（如 torch\lib\shm.dll）
    print(f"警告：加载 PP-Structure 底层依赖失败: {e}，已禁用 PP-Structure 功能。")
    PPSTRUCTURE_AVAILABLE = False
    PPStructure = None
# --- PyTorch 和 CARN 超分辨率 ---
try:
    import torch
    from torchvision.transforms import ToTensor, ToPILImage
    TORCH_AVAILABLE = True
    print("PyTorch 可用。")

    # 尝试导入 CARN 模型定义 (假设 carn.py 在同目录或 PYTHONPATH)
    try:
        from carn import CARN
        CARN_MODEL_DEF_AVAILABLE = True
        print("CARN 模型定义可用。")
    except ImportError:
        print("警告：未找到 CARN 模型定义文件 (carn.py)，超分辨率功能不可用。")
        CARN_MODEL_DEF_AVAILABLE = False
        CARN = None

except ImportError:
    # 未安装 torch 或 torchvision
    print("警告：未找到 torch 或 torchvision 库，超分辨率功能不可用。")
    TORCH_AVAILABLE = False
    CARN_MODEL_DEF_AVAILABLE = False
    CARN = None

except OSError as e:
    # 底层 DLL 加载失败（如 shm.dll）
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
        # ... (省略 Tesseract 路径查找代码，与之前相同) ...
        if platform.system() == "Windows":
            tesseract_cmd_env = os.getenv('TESSERACT_CMD')
            if tesseract_cmd_env and os.path.exists(tesseract_cmd_env): TESSERACT_PATH = tesseract_cmd_env
            else:
                possible_paths = [r'C:\Program Files\Tesseract-OCR\tesseract.exe', r'C:\Program Files (x86)\Tesseract-OCR\tesseract.exe']
                TESSERACT_PATH = next((p for p in possible_paths if os.path.exists(p)), None)
                if not TESSERACT_PATH: TESSERACT_PATH = shutil.which('tesseract')
        else: TESSERACT_PATH = shutil.which('tesseract')

        if not TESSERACT_PATH or not os.path.exists(TESSERACT_PATH): raise FileNotFoundError("错误：未能找到 Tesseract 可执行文件。")
        print(f"找到 Tesseract: {TESSERACT_PATH}")
        pytesseract.pytesseract.tesseract_cmd = TESSERACT_PATH
        print(f"已设置 pytesseract 命令路径。")

        # --- 查找 Tessdata 目录 ---
        tesseract_dir = os.path.dirname(TESSERACT_PATH)
        potential_tessdata = os.path.join(tesseract_dir, 'tessdata')
        if os.path.isdir(potential_tessdata): TESSDATA_DIR = potential_tessdata
        elif platform.system() == "Windows":
            potential_tessdata_alt = os.path.abspath(os.path.join(tesseract_dir, '..', 'tessdata'))
            if os.path.isdir(potential_tessdata_alt): TESSDATA_DIR = potential_tessdata_alt
        if not TESSDATA_DIR:
            tessdata_prefix_env = os.getenv('TESSDATA_PREFIX')
            if tessdata_prefix_env:
                 potential_tessdata_env = os.path.join(tessdata_prefix_env, 'tessdata')
                 if os.path.isdir(potential_tessdata_env): TESSDATA_DIR = potential_tessdata_env
                 elif os.path.basename(tessdata_prefix_env).lower() == 'tessdata' and os.path.isdir(tessdata_prefix_env): TESSDATA_DIR = tessdata_prefix_env

        if TESSDATA_DIR and os.path.isdir(TESSDATA_DIR):
            print(f"找到 tessdata 目录: {TESSDATA_DIR}")
            TESSDATA_PREFIX = os.path.abspath(os.path.join(TESSDATA_DIR, '..'))
            os.environ['TESSDATA_PREFIX'] = TESSDATA_PREFIX
            print(f"已设置环境变量 TESSDATA_PREFIX = {TESSDATA_PREFIX}")
        else: print("警告：未能自动找到有效的 'tessdata' 目录。")
    except FileNotFoundError as e: print(e); TESSERACT_PATH = None
    except Exception as e: print(f"初始化 Tesseract 路径时发生未知错误: {e}"); TESSERACT_PATH = None
# -----------------------------------------------------------

class PDFOCRApp:
    """
    PDF OCR 工具 (v4 - 集成 CARN 超分 + PP-Structure + Tesseract 备选)
    """
    def __init__(self, root):
        self.root = root
        self.root.title("智能 PDF OCR 工具 (PP-Structure + CARN)")
        # 恢复之前的窗口大小
        self.root.geometry("850x650")
        self.style = ttk.Style()
        # 尝试设置通用主题，避免过小的字体
        try:
            if platform.system() == "Windows": self.style.theme_use('vista')
            elif platform.system() == "Darwin": self.style.theme_use('aqua') # aqua 可能仍有问题
            else: self.style.theme_use('clam')
        except TclError:
            print("无法设置 ttk 主题，使用默认主题。")

        self.input_files = []
        self.output_folder = StringVar(value=os.getcwd())
        self.running = False

        # --- 处理选项 ---
        self.ocr_engine_choice = StringVar(value="PP-Structure" if PPSTRUCTURE_AVAILABLE else "Tesseract") # 默认选 PP-Structure
        self.ocr_language = StringVar(value="ch") # PP-Structure 通常用 'ch', 'en' 等，Tesseract 用 'chi_sim+eng'
        self.perform_osd = BooleanVar(value=True if TESSERACT_AVAILABLE else False) # OSD 依赖 Tesseract
        self.perform_crop = BooleanVar(value=True)
        self.perform_clahe = BooleanVar(value=True)
        self.perform_denoise = BooleanVar(value=False)
        self.use_super_res = BooleanVar(value=False) # 超分辨率默认关闭
        self.carn_model_path = StringVar(value="carn.pth") # CARN 权重路径

        # --- 模型实例 (延迟加载) ---
        self.ppstructure_model_instance = None
        self.carn_model_instance = None

        # --- 启动检查 ---
        if not TESSERACT_AVAILABLE and not PPSTRUCTURE_AVAILABLE:
            messagebox.showerror("严重错误", "未找到 Tesseract 和 PaddleOCR 库，无法执行 OCR。请安装至少一个库。")
            # 此处可以考虑退出程序 root.destroy()
        elif not TESSERACT_AVAILABLE:
             messagebox.showwarning("配置警告", "未找到 Tesseract，Tesseract 相关功能（如 OSD、备选 OCR）不可用。")
             if self.ocr_engine_choice.get() == "Tesseract": self.ocr_engine_choice.set("PP-Structure")
        elif not PPSTRUCTURE_AVAILABLE:
             messagebox.showwarning("配置警告", "未找到 PaddleOCR，PP-Structure 功能不可用。")
             if self.ocr_engine_choice.get() == "PP-Structure": self.ocr_engine_choice.set("Tesseract")
        if TESSERACT_AVAILABLE and not TESSDATA_PREFIX and not os.getenv('TESSDATA_PREFIX'):
            messagebox.showwarning("Tesseract警告", "未能确认 TESSDATA_PREFIX，Tesseract OCR 可能因缺少语言文件失败。")
        if not TORCH_AVAILABLE or not CARN_MODEL_DEF_AVAILABLE:
            messagebox.showwarning("超分警告", "未找到 PyTorch 或 CARN 模型定义，超分辨率功能不可用。")


        self.setup_ui()

    def setup_ui(self):
        """初始化界面控件 - 使用 ttk 默认风格"""
        main_frame = ttk.Frame(self.root, padding="10 10 10 10") # 恢复内边距
        main_frame.pack(fill=BOTH, expand=True)

        # --- 文件选择区 ---
        file_frame = ttk.Frame(main_frame, padding="0 0 0 5")
        file_frame.pack(fill=X)
        ttk.Button(file_frame, text="选择单个 PDF", command=self.select_single_file).pack(side=LEFT, padx=(0, 5))
        self.single_file_label = ttk.Label(file_frame, text="未选择文件", anchor=W, width=45) # 调整宽度
        self.single_file_label.pack(side=LEFT, fill=X, expand=True, padx=5)
        ttk.Button(file_frame, text="选择多个 PDF", command=self.select_multiple_files).pack(side=LEFT, padx=(5, 0))
        self.multi_file_label = ttk.Label(file_frame, text="", width=15, anchor=W) # 调整宽度
        self.multi_file_label.pack(side=LEFT, padx=5)

        # --- 输出目录区 ---
        output_frame = ttk.Frame(main_frame, padding="0 5 0 5")
        output_frame.pack(fill=X, pady=8)
        ttk.Button(output_frame, text="选择输出目录", command=self.select_output_folder).pack(side=LEFT, padx=(0, 5))
        self.output_dir_label = ttk.Label(output_frame, textvariable=self.output_folder, anchor=W)
        self.output_dir_label.pack(side=LEFT, fill=X, expand=True, padx=5)

        # --- 选项区 ---
        opts_notebook = ttk.Notebook(main_frame, padding="2.txt 5 2.txt 2.txt")
        opts_notebook.pack(fill=X, pady=5)

        # OCR 引擎与语言
        ocr_opts_frame = ttk.Frame(opts_notebook, padding=10)
        opts_notebook.add(ocr_opts_frame, text='OCR 引擎')

        engine_frame = ttk.Frame(ocr_opts_frame)
        engine_frame.pack(fill=X, pady=3)
        ttk.Label(engine_frame, text="选择引擎:").pack(side=LEFT, padx=(0, 5))
        pp_radio = ttk.Radiobutton(engine_frame, text="PP-Structure (推荐)", variable=self.ocr_engine_choice, value="PP-Structure")
        pp_radio.pack(side=LEFT, padx=5)
        ts_radio = ttk.Radiobutton(engine_frame, text="Tesseract (备选)", variable=self.ocr_engine_choice, value="Tesseract")
        ts_radio.pack(side=LEFT, padx=5)
        if not PPSTRUCTURE_AVAILABLE: pp_radio.config(state=DISABLED)
        if not TESSERACT_AVAILABLE: ts_radio.config(state=DISABLED)

        lang_frame = ttk.Frame(ocr_opts_frame)
        lang_frame.pack(fill=X, pady=3)
        ttk.Label(lang_frame, text="识别语言:").pack(side=LEFT, padx=(0, 5))
        lang_entry = ttk.Entry(lang_frame, textvariable=self.ocr_language, width=15)
        lang_entry.pack(side=LEFT, padx=5)
        ttk.Label(lang_frame, text="(PP用ch/en, Tess用chi_sim+eng)").pack(side=LEFT)

        # 预处理选项
        preproc_opts_frame = ttk.Frame(opts_notebook, padding=10)
        opts_notebook.add(preproc_opts_frame, text='图像预处理')

        cb_osd = ttk.Checkbutton(preproc_opts_frame, text="自动旋转方向 (OSD, 需Tesseract)", variable=self.perform_osd)
        cb_osd.pack(anchor=W)
        cb_crop = ttk.Checkbutton(preproc_opts_frame, text="裁剪图像边界", variable=self.perform_crop)
        cb_crop.pack(anchor=W)
        cb_clahe = ttk.Checkbutton(preproc_opts_frame, text="增强对比度 (CLAHE)", variable=self.perform_clahe)
        cb_clahe.pack(anchor=W)
        cb_denoise = ttk.Checkbutton(preproc_opts_frame, text="降噪 (较慢)", variable=self.perform_denoise)
        cb_denoise.pack(anchor=W)
        if not TESSERACT_AVAILABLE: cb_osd.config(state=DISABLED) # OSD 依赖 Tesseract

        # 超分辨率选项
        sr_opts_frame = ttk.Frame(opts_notebook, padding=10)
        opts_notebook.add(sr_opts_frame, text='超分辨率 (实验性)')
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


        # --- 进度与控制区 ---
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

        # --- 日志区 ---
        log_frame = ttk.LabelFrame(main_frame, text="运行日志", padding=10)
        log_frame.pack(fill=BOTH, expand=True, pady=(5, 0))
        # 使用默认字体大小
        self.log_text = Text(log_frame, wrap=WORD, height=10, state=DISABLED, borderwidth=1, relief="sunken")
        self.log_text.pack(side=LEFT, fill=BOTH, expand=True)
        sb = ttk.Scrollbar(log_frame, orient=VERTICAL, command=self.log_text.yview)
        sb.pack(side=RIGHT, fill=Y)
        self.log_text.config(yscrollcommand=sb.set)

    # --- UI 更新方法 (保持不变) ---
    def log_message(self, m, level=logging.INFO):
        def update_log():
            self.log_text.config(state=NORMAL)
            timestamp = strftime("%H:%M:%S", localtime())
            level_str = logging.getLevelName(level)
            prefix = f"{timestamp} [{level_str}] " if level > logging.INFO else f"{timestamp} - "
            self.log_text.insert(END, f"{prefix}{m}\n")
            self.log_text.see(END)
            self.log_text.config(state=DISABLED)
            if level == logging.ERROR: logging.error(m)
            elif level == logging.WARNING: logging.warning(m)
            else: logging.info(m)
        try: self.root.after(0, update_log)
        except RuntimeError: print(f"日志(UI关闭?): {m}")

    def update_progress(self, value, text):
         def update_ui():
              safe_value = max(0, min(100, int(value)))
              self.total_progress['value'] = safe_value
              self.total_progress_label.config(text=text)
         try: self.root.after(0, update_ui)
         except RuntimeError: print(f"进度(UI关闭?): {text} ({value}%)")

    def update_button_state(self, is_running):
         def update_ui():
              self.start_button.config(state=DISABLED if is_running else NORMAL)
              self.cancel_button.config(state=NORMAL if is_running else DISABLED)
         try: self.root.after(0, update_ui)
         except RuntimeError: pass

    # --- 文件选择 ---
    def select_single_file(self):
        p = filedialog.askopenfilename(title="选择单个 PDF 文件", filetypes=[("PDF", "*.pdf")])
        if p: self.input_files = [p]; self.single_file_label.config(text=os.path.basename(p)); self.multi_file_label.config(text=""); self.log_message(f"已选单个文件: {p}")

    def select_multiple_files(self):
        ps = filedialog.askopenfilenames(title="选择多个 PDF 文件", filetypes=[("PDF", "*.pdf")])
        if ps: self.input_files = list(ps); self.multi_file_label.config(text=f"已选 {len(ps)} 个文件"); self.single_file_label.config(text=""); self.log_message(f"已选 {len(ps)} 个文件")

    def select_output_folder(self):
        d = filedialog.askdirectory(title="选择输出文件夹");
        if d: self.output_folder.set(d); self.log_message(f"输出目录: {d}")

    def select_carn_model(self):
        """选择 CARN 模型权重文件"""
        p = filedialog.askopenfilename(title="选择 CARN 模型权重 (.pth)", filetypes=[("PyTorch Model", "*.pth")])
        if p:
            self.carn_model_path.set(p)
            self.log_message(f"CARN 模型路径设置为: {p}")

    # --- OCR 控制 ---
    def start_ocr(self):
        # 检查至少有一个 OCR 引擎可用
        if not TESSERACT_AVAILABLE and not PPSTRUCTURE_AVAILABLE: messagebox.showerror("错误", "未安装 Tesseract 或 PaddleOCR，无法执行 OCR。"); return
        # 如果选择了 Tesseract，检查其依赖
        if self.ocr_engine_choice.get() == "Tesseract":
            if not TESSERACT_PATH: messagebox.showerror("错误", "Tesseract 未找到。"); return
            if not TESSDATA_PREFIX and not os.getenv('TESSDATA_PREFIX'):
                 if not messagebox.askyesno("警告", "未能确认 TESSDATA_PREFIX，Tesseract 可能失败。\n是否继续？"): return
        # 如果选择了 PP-Structure，检查其依赖
        elif self.ocr_engine_choice.get() == "PP-Structure" and not PPSTRUCTURE_AVAILABLE:
             messagebox.showerror("错误", "PaddleOCR (PP-Structure) 未安装或导入失败。"); return
        # 如果启用超分，检查其依赖
        if self.use_super_res.get() and (not TORCH_AVAILABLE or not CARN_MODEL_DEF_AVAILABLE):
             messagebox.showerror("错误", "PyTorch 或 CARN 模型定义未找到，无法启用超分辨率。")
             self.use_super_res.set(False) # 取消勾选
             return
        if self.use_super_res.get() and not os.path.exists(self.carn_model_path.get()):
             messagebox.showerror("错误", f"CARN 模型文件未找到: {self.carn_model_path.get()}")
             return

        if not self.input_files: messagebox.showerror("错误", "请先选择 PDF 文件。"); return
        if self.running: messagebox.showwarning("提示", "任务已在运行中。"); return

        self.running = True
        self.update_button_state(True)
        self.update_progress(0, "准备开始...")
        self.log_text.config(state=NORMAL); self.log_text.delete(1.0, END); self.log_text.config(state=DISABLED)
        self.log_message(">>> 开始 OCR 任务 <<<")
        self.log_message(f"引擎: {self.ocr_engine_choice.get()}, 语言: {self.ocr_language.get()}, 超分={self.use_super_res.get()}, OSD={self.perform_osd.get()}, 裁剪={self.perform_crop.get()}, CLAHE={self.perform_clahe.get()}, 去噪={self.perform_denoise.get()}")

        threading.Thread(target=self.process_files_thread, daemon=True).start()

    def cancel_ocr(self):
        if self.running:
             if messagebox.askyesno("确认", "确定要取消当前任务吗？"):
                  self.running = False; self.log_message(">>> 正在尝试取消任务... <<<", logging.WARNING)
        else: self.log_message("没有正在运行的任务。")

    # --- 模型加载与释放 ---
    def _load_ppstructure_model(self):
        """按需加载 PP-Structure 模型"""
        if self.ppstructure_model_instance is None and PPSTRUCTURE_AVAILABLE:
            self.log_message("首次使用，正在加载 PP-Structure 模型...", logging.INFO)
            try:
                # 检查 GPU 可用性
                use_gpu = paddle.device.is_compiled_with_cuda() and paddle.device.cuda.device_count() > 0
                self.log_message(f"PP-Structure 将使用 {'GPU' if use_gpu else 'CPU'}。", logging.INFO)
                # 初始化模型
                self.ppstructure_model_instance = PPStructure(
                    show_log=False, # 关闭 paddleocr 的日志
                    use_gpu=use_gpu,
                    lang=self.ocr_language.get().split('+')[0] # PPStructure 通常用单语言 'ch' 或 'en'
                )
                self.log_message("PP-Structure 模型加载成功。", logging.INFO)
                return True
            except Exception as e:
                self.log_message(f"错误：加载 PP-Structure 模型失败: {e}", logging.ERROR)
                traceback.print_exc()
                self.ppstructure_model_instance = None
                return False
        elif self.ppstructure_model_instance:
             return True # 已加载
        else:
             return False # 不可用

    def _load_carn_model(self):
        """按需加载 CARN 模型"""
        if self.carn_model_instance is None and TORCH_AVAILABLE and CARN_MODEL_DEF_AVAILABLE:
             model_path = self.carn_model_path.get()
             if not os.path.exists(model_path):
                  self.log_message(f"错误：CARN 模型权重文件不存在: {model_path}", logging.ERROR)
                  return False
             self.log_message(f"首次使用，正在加载 CARN 超分模型: {model_path}", logging.INFO)
             try:
                 self.carn_model_instance = CARN() # 假设 CARN 类在 carn.py 中
                 # 强制在 CPU 上加载和运行
                 device = torch.device('cpu')
                 self.carn_model_instance.load_state_dict(torch.load(model_path, map_location=device))
                 self.carn_model_instance.eval() # 设置为评估模式
                 self.carn_model_instance.to(device) # 确保模型在 CPU 上
                 self.log_message("CARN 模型加载成功 (CPU)。", logging.INFO)
                 return True
             except Exception as e:
                  self.log_message(f"错误：加载 CARN 模型失败: {e}", logging.ERROR)
                  traceback.print_exc()
                  self.carn_model_instance = None
                  return False
        elif self.carn_model_instance:
             return True # 已加载
        else:
             return False # 不可用


    # --- 核心处理线程 ---
    def process_files_thread(self):
        """后台线程处理所有选定的 PDF 文件"""
        total_files = len(self.input_files)
        processed_count = 0
        error_count = 0
        thread_start_time = perf_counter()
        engine_choice = self.ocr_engine_choice.get()
        use_sr = self.use_super_res.get()

        # --- 预加载模型 (如果需要) ---
        ppstructure_ready = False
        if engine_choice == "PP-Structure":
             ppstructure_ready = self._load_ppstructure_model()
             if not ppstructure_ready:
                  self.log_message("PP-Structure 加载失败，将自动切换到 Tesseract 备选方案。", logging.ERROR)
                  engine_choice = "Tesseract" # 切换到备选

        carn_ready = False
        if use_sr:
             carn_ready = self._load_carn_model()
             if not carn_ready:
                  self.log_message("CARN 模型加载失败，超分辨率功能已禁用。", logging.ERROR)
                  use_sr = False # 禁用超分

        # --- Tesseract 检查 (如果需要作为备选) ---
        if engine_choice == "Tesseract" and not TESSERACT_PATH:
             self.log_message("错误: Tesseract 未配置，无法作为备选方案。", logging.CRITICAL)
             self.running = False # 停止运行
             self.update_button_state(False)
             self.update_progress(0, "错误：OCR引擎不可用")
             return # 退出线程

        # --- 文件处理循环 ---
        try:
            for idx, file_path in enumerate(self.input_files):
                if not self.running: self.log_message("任务已被用户取消。"); break
                file_num = idx + 1
                base_name = os.path.basename(file_path)
                self.log_message(f"\n>> 文件 {file_num}/{total_files}: {base_name}", logging.INFO)
                file_start_time = perf_counter()
                self.update_progress((idx / total_files) * 100, f"处理中: {base_name} ({file_num}/{total_files})")

                # --- 选择处理流程 ---
                if engine_choice == "PP-Structure" and ppstructure_ready:
                    result_text = self.process_pdf_with_ppstructure(file_path, file_num, total_files, use_sr and carn_ready)
                elif TESSERACT_AVAILABLE: # 使用 Tesseract 作为备选
                    result_text = self.process_pdf_with_tesseract(file_path, file_num, total_files, use_sr and carn_ready)
                else: # 没有可用的引擎
                    result_text = "[错误：没有可用的 OCR 引擎]"
                    error_count += 1

                if not self.running: self.log_message(f"处理 {base_name} 期间任务被取消。"); break

                # --- 保存结果 ---
                if result_text is not None:
                    if "失败" in result_text or "错误" in result_text: error_count += 1; logging.warning(f"文件 {base_name} 处理中遇到问题。")
                    output_filename = os.path.splitext(base_name)[0] + "_ocr.txt"
                    output_path = os.path.join(self.output_folder.get(), output_filename)
                    try:
                        with open(output_path, "w", encoding="utf-8") as fw: fw.write(result_text)
                        file_end_time = perf_counter()
                        self.log_message(f"结果已保存 (耗时 {file_end_time - file_start_time:.2f} 秒): {output_path}")
                        processed_count += 1
                    except IOError as e: self.log_message(f"错误：无法保存文件 {output_path}: {e}", logging.ERROR); error_count += 1
                else: error_count += 1; self.log_message(f"文件 {base_name} 未能处理或被跳过。", logging.WARNING)

        except Exception as e:
            self.log_message(f"处理文件过程中发生严重错误: {e}\n{traceback.format_exc()}", logging.CRITICAL)
            error_count = total_files
        finally:
            # --- 任务结束 ---
            thread_end_time = perf_counter()
            duration = thread_end_time - thread_start_time
            final_message = ""
            if not self.running and processed_count < total_files: final_message = f"任务已取消。成功处理 {processed_count} 个文件。"
            elif error_count > 0: final_message = f"处理完成，共 {total_files} 文件，其中 {error_count} 个失败或含错误。"
            else: final_message = f"所有 {total_files} 个文件处理完成！"
            self.log_message(f"\n{final_message} 总耗时: {duration:.2f} 秒。", logging.INFO)
            self.update_progress(100, final_message)
            self.running = False
            self.update_button_state(False)
            # 可选：清理模型以释放内存 (如果模型很大)
            # self.ppstructure_model_instance = None
            # self.carn_model_instance = None
            # torch.cuda.empty_cache() # 如果用了 GPU

    # --- 基于 PP-Structure 的处理流程 ---
    def process_pdf_with_ppstructure(self, path, file_num, total_files, apply_sr):
        """使用 PP-Structure 处理单个 PDF 文件"""
        if not self.ppstructure_model_instance: return "[错误: PP-Structure 模型未加载]"
        doc = None
        all_page_texts = []
        try:
            doc = fitz.open(path)
            num_pages = len(doc)
            self.log_message(f"  [PP-Structure] 共 {num_pages} 页")

            for i in range(num_pages):
                if not self.running: return None
                page_num = i + 1
                self.log_message(f"  处理页面 {page_num}/{num_pages} (引擎: PP-Structure)...")
                page_start_time = perf_counter()
                progress_val = ((file_num - 1) / total_files + (page_num / num_pages) / total_files) * 100
                self.update_progress(progress_val, f"文件 {file_num}/{total_files} - 页面 {page_num}/{num_pages} (PP-Structure)...")

                page_content = f"\n--- 第 {page_num} 页 (PP-Structure 处理失败) ---\n"
                try:
                    # 1. 获取图像
                    page = doc.load_page(i)
                    pix = page.get_pixmap(dpi=300)
                    img_pil = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
                    img_cv_bgr = cv2.cvtColor(np.array(img_pil), cv2.COLOR_RGB2BGR)
                    img_to_process = img_cv_bgr

                    # 2.txt. 应用超分辨率 (如果启用且模型可用)
                    if apply_sr:
                        self.log_message("    应用 CARN 超分辨率...")
                        sr_start_time = perf_counter()
                        img_to_process = self._apply_carn_super_resolution(img_cv_bgr)
                        if img_to_process is None:
                            self.log_message("    CARN 超分失败，使用原始图像。", logging.WARNING)
                            img_to_process = img_cv_bgr # Fallback
                        else:
                             sr_end_time = perf_counter()
                             self.log_message(f"    CARN 超分完成 (耗时 {sr_end_time - sr_start_time:.2f} 秒)。")

                    # 3. 调用 PP-Structure 模型
                    self.log_message("    调用 PP-Structure 分析...")
                    pp_start_time = perf_counter()
                    # **注意:** PP-Structure 内部可能自带 OSD 和预处理，我们先不进行外部预处理
                    results = self.ppstructure_model_instance(img_to_process)
                    pp_end_time = perf_counter()
                    self.log_message(f"    PP-Structure 分析完成 (耗时 {pp_end_time - pp_start_time:.2f} 秒)。")


                    # 4. 解析并格式化结果
                    page_blocks_text = []
                    if results:
                         for item in results:
                              block_type = item.get('type', 'Unknown').lower()
                              # PP-Structure 返回的 res 已经是识别结果或表格HTML
                              res_content = item.get('res', '')
                              # bbox = item.get('bbox') # 边界框信息

                              if block_type in ['text', 'title', 'list']:
                                   if isinstance(res_content, tuple) and len(res_content) == 2: # paddleocr >= 2.txt.6 返回 (text, confidence)
                                       page_blocks_text.append(res_content[0])
                                   elif isinstance(res_content, str): # 旧版本可能直接返回 str
                                        page_blocks_text.append(res_content)
                              elif block_type == 'table':
                                   # 直接包含表格的 HTML
                                   page_blocks_text.append(f"\n[表格开始]\n{res_content}\n[表格结束]\n")
                              elif block_type == 'figure':
                                   page_blocks_text.append("[图片区域]")
                              else: # 其他或未知类型
                                   if isinstance(res_content, tuple) and len(res_content) == 2:
                                       page_blocks_text.append(f"[{block_type.upper()}]: {res_content[0]}")
                                   elif isinstance(res_content, str) and res_content:
                                        page_blocks_text.append(f"[{block_type.upper()}]: {res_content}")

                         page_content = "\n".join(page_blocks_text)
                    else:
                         page_content = f"\n--- 第 {page_num} 页 (PP-Structure 未返回结果) ---\n"


                except Exception as page_err:
                    self.log_message(f"  处理页面 {page_num} (PP-Structure) 时发生错误: {page_err}", logging.ERROR)
                    traceback.print_exc()
                    page_content = f"\n--- 第 {page_num} 页 (PP-Structure 处理时发生错误: {page_err}) ---\n"
                finally:
                    page_end_time = perf_counter()
                    self.log_message(f"  页面 {page_num} 处理完成 (耗时 {page_end_time - page_start_time:.2f} 秒)。")
                    all_page_texts.append(page_content)

            return "".join(all_page_texts)

        except fitz.fitz.FileNotFoundError: self.log_message(f"错误：文件未找到 {path}", logging.ERROR); return None
        except Exception as e: self.log_message(f"处理 PDF (PP-Structure) 时发生严重错误: {e}", logging.CRITICAL); return None
        finally:
            if doc: doc.close()

    # --- 基于 Tesseract 的处理流程 (备选) ---
    def process_pdf_with_tesseract(self, path, file_num, total_files, apply_sr):
        """使用 Tesseract 处理单个 PDF 文件 (备选方案)"""
        doc = None
        all_page_texts = []
        try:
            doc = fitz.open(path)
            num_pages = len(doc)
            self.log_message(f"  [Tesseract] 共 {num_pages} 页")

            for i in range(num_pages):
                if not self.running: return None
                page_num = i + 1
                self.log_message(f"  处理页面 {page_num}/{num_pages} (引擎: Tesseract)...")
                page_start_time = perf_counter()
                progress_val = ((file_num - 1) / total_files + (page_num / num_pages) / total_files) * 100
                self.update_progress(progress_val, f"文件 {file_num}/{total_files} - 页面 {page_num}/{num_pages} (Tesseract)...")

                page_content = f"\n--- 第 {page_num} 页 (Tesseract 处理失败) ---\n"
                try:
                    # 1. 获取图像
                    page = doc.load_page(i)
                    pix = page.get_pixmap(dpi=300)
                    img_pil = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
                    img_cv_bgr = cv2.cvtColor(np.array(img_pil), cv2.COLOR_RGB2BGR)
                    img_to_process = img_cv_bgr

                     # 2.txt. 应用超分辨率 (如果启用且模型可用)
                    if apply_sr:
                        self.log_message("    应用 CARN 超分辨率...")
                        sr_start_time = perf_counter()
                        img_to_process = self._apply_carn_super_resolution(img_cv_bgr)
                        if img_to_process is None:
                            self.log_message("    CARN 超分失败，使用原始图像。", logging.WARNING)
                            img_to_process = img_cv_bgr # Fallback
                        else:
                             sr_end_time = perf_counter()
                             self.log_message(f"    CARN 超分完成 (耗时 {sr_end_time - sr_start_time:.2f} 秒)。")


                    # 3. 预处理 I: 旋转和裁剪 (依赖 Tesseract OSD)
                    if TESSERACT_AVAILABLE: # 只有 Tesseract 可用时才执行 Tesseract 的预处理
                        img_layout = self._preprocess_for_layout(img_to_process)
                        if img_layout is None: raise ValueError("布局预处理失败 (旋转/裁剪)")
                    else: # 如果 Tesseract 不可用，无法执行 OSD/裁剪
                         img_layout = img_to_process
                         self.log_message("    跳过旋转和裁剪 (Tesseract 不可用)。", logging.WARNING)


                    # 4. 预处理 II: OCR 准备
                    self.log_message("    进行 OCR 预处理...")
                    img_ocr_ready_pil = self._preprocess_for_ocr(img_layout)

                    if img_ocr_ready_pil is None:
                        page_content = f"\n--- 第 {page_num} 页 (图像预处理失败) ---\n"
                    else:
                        # 5. 执行整页 OCR (Tesseract)
                        self.log_message("    执行整页 Tesseract OCR...")
                        ocr_start_time = perf_counter()
                        # 整页 OCR 建议使用 PSM 3 或 11
                        ocr_result = self._ocr_text_block_tesseract(img_ocr_ready_pil, psm=3)
                        ocr_end_time = perf_counter()
                        self.log_message(f"    Tesseract OCR 完成 (耗时 {ocr_end_time - ocr_start_time:.2f} 秒)。")

                        # 6. (可选) 公式处理
                        # if self.include_formulas.get() and "错误" not in ocr_result:
                        #    self.log_message("    尝试检测公式...")
                        #    fm = self.detect_formulas_tesseract(img_ocr_ready_pil) # 公式检测可能需要 PIL
                        #    ocr_result = self.replace_formulas(ocr_result, fm)

                        page_content = f"\n--- 第 {page_num} 页 ---\n{ocr_result}\n"

                except Exception as page_err:
                    self.log_message(f"  处理页面 {page_num} (Tesseract) 时发生错误: {page_err}", logging.ERROR)
                    traceback.print_exc()
                    page_content = f"\n--- 第 {page_num} 页 (Tesseract 处理时发生错误: {page_err}) ---\n"
                finally:
                    page_end_time = perf_counter()
                    self.log_message(f"  页面 {page_num} 处理完成 (耗时 {page_end_time - page_start_time:.2f} 秒)。")
                    all_page_texts.append(page_content)

            return "".join(all_page_texts)

        except fitz.fitz.FileNotFoundError: self.log_message(f"错误：文件未找到 {path}", logging.ERROR); return None
        except Exception as e: self.log_message(f"处理 PDF (Tesseract) 时发生严重错误: {e}", logging.CRITICAL); return None
        finally:
            if doc: doc.close()


    # --- 超分辨率辅助方法 ---
    def _apply_carn_super_resolution(self, img_cv_bgr):
        """应用 CARN 模型进行超分辨率处理"""
        if not self.carn_model_instance: return None
        try:
            device = torch.device('cpu') # 强制使用 CPU
            # 将 OpenCV BGR 图像转换为 PyTorch Tensor
            # 注意：ToTensor() 会将 HWC [0,255] 转换为 CHW [0,1]
            img_pil = Image.fromarray(cv2.cvtColor(img_cv_bgr, cv2.COLOR_BGR2RGB))
            lr_tensor = ToTensor()(img_pil).unsqueeze(0).to(device)

            with torch.no_grad():
                sr_tensor = self.carn_model_instance(lr_tensor)

            # 将结果 Tensor 转回 OpenCV BGR 图像
            # ToPILImage() 需要 CHW [0,1] Tensor
            sr_image_pil = ToPILImage()(sr_tensor.squeeze(0).cpu())
            sr_image_cv_bgr = cv2.cvtColor(np.array(sr_image_pil), cv2.COLOR_RGB2BGR)
            return sr_image_cv_bgr
        except Exception as e:
            self.log_message(f"    CARN 超分辨率处理失败: {e}", logging.ERROR)
            return None


    # --- Tesseract 相关辅助方法 (如果需要备选) ---
    def _preprocess_for_layout(self, img_cv_bgr):
        """Tesseract 流程的预处理 I: 旋转和裁剪"""
        processed_img = img_cv_bgr.copy()
        if self.perform_osd.get() and TESSERACT_AVAILABLE:
            rotated_img = self._run_osd_and_rotate(processed_img)
            if rotated_img is not None: processed_img = rotated_img
            else: self.log_message("    OSD 旋转失败，跳过。", logging.WARNING)
        if self.perform_crop.get():
            cropped_img = self._crop_borders(processed_img)
            if cropped_img is not None and cropped_img.shape[0] > 10 and cropped_img.shape[1] > 10: processed_img = cropped_img
            else: self.log_message("    边界裁剪失败或区域过小，跳过。", logging.WARNING)
        return processed_img

    def _preprocess_for_ocr(self, img_cv_bgr):
        """Tesseract 流程的预处理 II: 灰度, CLAHE, 去噪, 二值化"""
        try:
            gray = cv2.cvtColor(img_cv_bgr, cv2.COLOR_BGR2GRAY)
            processed_gray = gray
            if self.perform_clahe.get():
                clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8)); processed_gray = clahe.apply(processed_gray)
            if self.perform_denoise.get():
                processed_gray = cv2.fastNlMeansDenoising(processed_gray, None, h=10, templateWindowSize=7, searchWindowSize=21)
            binary = cv2.adaptiveThreshold(processed_gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, 15, 7)
            return Image.fromarray(binary)
        except Exception as e: self.log_message(f"      OCR 预处理失败: {e}", logging.ERROR); return None

    def _run_osd_and_rotate(self, image_cv_bgr):
        """Tesseract OSD 检测方向并旋转"""
        if not TESSERACT_AVAILABLE: return image_cv_bgr # 如果 Tesseract 不可用，返回原图
        try:
            self.log_message("    步骤 1/2.txt: 方向检测与旋转 (OSD)...")
            gray = cv2.cvtColor(image_cv_bgr, cv2.COLOR_BGR2GRAY)
            osd_data = pytesseract.image_to_osd(gray, config='--psm 0', output_type=Output.DICT)
            angle = osd_data.get('rotate', 0); script = osd_data.get('script', 'Unknown')
            self.log_message(f"    OSD: 角度={angle}, 脚本={script}")
            if angle != 0 and abs(angle) < 90: # 仅旋转非 90/180/270 的小角度？或全部旋转
                self.log_message(f"    旋转 {-angle} 度...")
                (h, w) = image_cv_bgr.shape[:2]; center = (w // 2, h // 2)
                M = cv2.getRotationMatrix2D(center, -angle, 1.0)
                rotated = cv2.warpAffine(image_cv_bgr, M, (w, h), flags=cv2.INTER_CUBIC, borderMode=cv2.BORDER_CONSTANT, borderValue=(255, 255, 255))
                return rotated
            else: self.log_message("    无需旋转或角度无效。"); return image_cv_bgr
        except (TesseractNotFoundError, TesseractError) as e: self.log_message(f"    Tesseract OSD 失败: {str(e).split(None,1)[0]}", logging.ERROR); return image_cv_bgr
        except Exception as e: self.log_message(f"    OSD 或旋转出错: {e}", logging.ERROR); return image_cv_bgr

    def _crop_borders(self, image_cv_bgr, border_threshold=200, min_area_ratio=0.5):
        """检测并裁剪图像边框"""
        try:
            self.log_message("    步骤 2.txt/2.txt: 裁剪边界...")
            gray = cv2.cvtColor(image_cv_bgr, cv2.COLOR_BGR2GRAY)
            _, thresh = cv2.threshold(gray, border_threshold, 255, cv2.THRESH_BINARY_INV)
            contours, _ = cv2.findContours(thresh, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
            if not contours: self.log_message("    边界裁剪：未找到轮廓。"); return image_cv_bgr
            max_contour = max(contours, key=cv2.contourArea); area = cv2.contourArea(max_contour); img_area = image_cv_bgr.shape[0] * image_cv_bgr.shape[1]
            if area / img_area < min_area_ratio: self.log_message(f"    边界裁剪：内容区域过小 ({area/img_area:.2f})，跳过。"); return image_cv_bgr
            x, y, w, h = cv2.boundingRect(max_contour); padding = 5
            x1, y1 = max(0, x - padding), max(0, y - padding)
            x2, y2 = min(image_cv_bgr.shape[1], x + w + padding), min(image_cv_bgr.shape[0], y + h + padding)
            cropped = image_cv_bgr[y1:y2, x1:x2]
            self.log_message("    边界裁剪完成。")
            return cropped
        except Exception as e: self.log_message(f"    边界裁剪出错: {e}", logging.ERROR); return image_cv_bgr

    def _ocr_text_block_tesseract(self, img_block_pil, psm=3):
        """使用 Tesseract 对图像块执行 OCR"""
        if not TESSERACT_AVAILABLE: return "[错误: Tesseract 不可用]"
        try:
            lang = self.ocr_language.get()
            # 注意：Tesseract 语言格式是 chi_sim+eng
            lang_tess = lang if '+' in lang else lang.replace('ch','chi_sim') # 简单转换
            config = f'--oem 3 --psm {psm}'
            text = pytesseract.image_to_string(img_block_pil, lang=lang_tess, config=config)
            return text.strip() if text else "[空]"
        except (TesseractNotFoundError, TesseractError) as e:
            error_detail = str(e).split('\n', 1)[0]; self.log_message(f"    OCR (Tesseract) 失败: {error_detail}", logging.ERROR); return f"[OCR 错误: {error_detail}]"
        except Exception as e: self.log_message(f"    OCR (Tesseract) 意外错误: {e}", logging.ERROR); return f"[OCR 错误: {e}]"


# --- 主程序入口 ---
if __name__ == "__main__":
    root = Tk()
    if platform.system() == "Windows":
        try: from ctypes import windll; windll.shcore.SetProcessDpiAwareness(1)
        except Exception as e: print(f"无法设置 DPI 感知: {e}")
    app = PDFOCRApp(root)
    root.mainloop()