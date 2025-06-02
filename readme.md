# 综合文件处理与分析工具集 🧰

本项目汇集了多个独立的 Python 应用程序，旨在提供文件创建、代码审查、光学字符识别（OCR）、在线文档编辑以及文件内容聚合等功能。

## ✨ 工具概览

* 📁 **文件创建工具 (`CreateFile.py`)**: 一个图形化工具，用于根据预设模板（Java、Vue、微信小程序、Python）或自定义扩展名批量创建文件和文件夹结构。
* 🧑‍💻 **多语言代码审查分析工具 (`multi_language_code_review.py`)**: 一个高级的图形化工具，用于代码审查、智能路径解析、依赖项检查以及应用代码变更。它还集成了本地 AI 模型辅助进行代码分析和建议。
* 📄 **智能文件 OCR 工具 (`ocr.py`)**: 一个强大的图形化 OCR 工具，支持处理 PDF 和多种图像文件。它集成了 PP-Structure 和 Tesseract OCR 引擎，并可选配 CARN 模型进行图像超分辨率处理，以提升识别准确率。
* 📝 **Markdown/文本在线编辑器 (`read.py` & `screenshot.py`)**: 一个基于 Flask 的 Web 应用，允许用户在线查看和编辑 `templates` 目录下的 Markdown 和文本文件。支持实时预览，并包含一个基于 Selenium 的网页元素截图功能。
* 📚 **文件内容聚合工具 (`ReadTotally.py`)**: 一个图形化工具，用于递归地读取指定文件夹内的文件内容，并将其聚合成单个或多个文本文件。支持排除特定文件夹和文件，并提供输出文件自动删除的选项。

## 🚀 先决条件与设置

1.  **Python**: 确保您已安装 Python 3.7 或更高版本。
2.  **依赖库**: 安装所有必要的 Python 库。建议在项目根目录下创建一个 `requirements.txt` 文件（内容如下），然后运行：
    ```bash
    pip install -r requirements.txt
    ```
3.  **特定工具设置**:
    * **智能文件 OCR 工具 (`ocr.py`)**:
        * **Tesseract OCR**: 如果选择使用 Tesseract 引擎，请先[安装 Tesseract OCR](https://github.com/tesseract-ocr/tessdoc)，并将其添加到系统的 PATH环境变量中。同时，根据需要识别的语言下载相应的[语言数据包](https://github.com/tesseract-ocr/tessdata)并放置到 Tesseract 的 `tessdata` 目录下。脚本会尝试自动查找 Tesseract 和 `tessdata` 目录。
        * **PP-Structure**: 如果选择使用 PP-Structure 引擎，相关依赖 (`paddlepaddle`, `paddleocr`) 已包含在 `requirements.txt` 中。初次运行时会自动下载模型文件。
        * **CARN 超分辨率**: 如果希望使用图像超分辨率功能，请确保 `carn.pth` 模型文件与 `carn.py` 和 `ocr.py` 位于同一目录，或者在 OCR 工具界面中正确指定其路径。
    * **多语言代码审查分析工具 (`multi_language_code_review.py`)**:
        * 此工具依赖一个本地运行的 AI 模型（例如通过 Ollama 部署的 `gemma3:4b` 模型）。请确保本地 AI 服务在 `http://localhost:11434/api/chat` 上可用。
    * **Markdown/文本在线编辑器 (`read.py`)**:
        * **EdgeDriver**: 截图功能 (`screenshot.py`) 需要 Microsoft Edge 浏览器和对应的 EdgeDriver。请[下载 EdgeDriver](https://developer.microsoft.com/en-us/microsoft-edge/tools/webdriver/) 并将其路径配置在 `screenshot.py` 文件顶部的 `EDGE_DRIVER_PATH` 变量中。
        * **`templates` 目录**: `read.py` 应用会读取和写入位于其同级 `templates` 目录下的文件。如果该目录不存在，应用首次运行时会自动创建，并可能生成一个示例 `readme.md` 和 `example.png`。

## 🛠️ 使用说明

以下是各个主要图形化工具的启动和基本使用方法：

### 📁 文件创建工具 (`CreateFile.py`)

* **启动**:
    ```bash
    python CreateFile.py
    ```
* **使用**:
    1.  启动应用后，会显示一个图形界面。
    2.  在“文件名”字段输入你想要创建的基础文件名（例如 `MyComponent`）。
    3.  点击“目录”旁的“选择...”按钮选择文件和文件夹将被创建的目标父目录。
    4.  您可以点击“预设模板”下方的按钮（如 "Java", "Vue", "微信小程序", "Python"）来快速选择一组常用的文件扩展名。选择模板会自动填充下方的自定义扩展名列表。
    5.  您也可以在“自定义扩展名”区域手动输入文件扩展名（如 `html`, `css`，无需带点），然后点击“+ 添加”按钮。
    6.  添加的扩展名会显示在下方的列表中。您可以通过“清空”按钮清除列表。
    7.  确认无误后，点击“创建文件”按钮。应用会在指定的目录下创建一个与“文件名”同名的文件夹，然后在该文件夹内创建所有指定扩展名的文件。例如，如果文件名为 `Test`，扩展名为 `js` 和 `html`，则会创建 `.../所选目录/Test/Test.js` 和 `.../所选目录/Test/Test.html`。

### 🧑‍💻 多语言代码审查分析工具 (`multi_language_code_review.py`)

* **启动**:
    ```bash
    python multi_language_code_review.py
    ```
* **使用**:
    1.  启动后，首先点击“浏览...”选择您的项目根目录。
    2.  （可选）选择主要语言、是否创建备份、是否自动修复路径以及使用的 AI 模型。
    3.  在“代码建议变更”文本框中粘贴包含文件路径和新代码内容的文本。工具支持多种格式自动解析文件路径和内容，包括：
        * `文件路径：your/file/path.java` 后跟代码块。
        * `# 文件路径: your/file/path.py` 后跟代码块。
        * Markdown 代码块格式，其中路径在代码块声明之前（例如 `### 文件路径: src/main/App.vue`）。
        * 通过 `---` 分隔的多个文件定义。
    4.  点击“分析变更”按钮。工具会：
        * 解析文件路径，如果路径不规范或包含重复段（如 `src/main/java/src/main/java`），会尝试自动修正。
        * 检测文件是否存在，是新建还是修改。
        * 检查导入依赖是否完整，并对缺失的导入使用 AI 提供建议（如果 AI 模型可用）。
        * 执行特定语言的静态检查。
    5.  分析结果会显示在下方的文本区域，包括警告、错误、风险操作等。
    6.  点击“预览变更”可以在新窗口中对比原始文件内容和修改后内容。在此窗口中，您可以编辑最终要应用的内容和文件路径。
    7.  点击“批量编辑路径”可以对分析涉及的所有文件的路径进行统一修改，例如更改公共前缀或自动修复路径中的重复段。
    8.  确认无误后，点击“应用变更”将修改写入文件系统。如果启用了备份，会先创建备份。

### 📄 智能文件 OCR 工具 (`ocr.py`)

* **启动**:
    ```bash
    python ocr.py
    ```
* **使用**:
    1.  启动应用。
    2.  点击“选择单个文件 (PDF/图片)”或“选择多个文件 (PDF/图片)”来选择需要进行 OCR 的文件。
    3.  点击“选择输出目录”来指定识别结果文本文件的保存位置。
    4.  在“OCR 引擎”选项卡中：
        * 选择 OCR 引擎：“PP-Structure (推荐)” 或 “Tesseract (备选)”。只有正确安装和配置的引擎才可选择。
        * 输入识别语言：例如，PP-Structure 使用 `ch` (中文)、`en` (英文)；Tesseract 使用 `chi_sim` (简体中文)、`eng` (英文)，或组合如 `chi_sim+eng`。
        * （可选）勾选“保存提取/输入的图像到子文件夹”，这会将从 PDF 中提取的每一页图像或输入的原始图像保存到输出目录下一个以原文件名命名的子文件夹中。
    5.  在“图像预处理”选项卡中，可以为 Tesseract 引擎流程选择预处理步骤，如自动旋转方向 (OSD)、裁剪图像边界、增强对比度 (CLAHE) 和降噪。这些选项对 PP-Structure 影响较小。
    6.  在“超分辨率 (实验性)”选项卡中：
        * （可选）勾选“启用超分辨率 (CARN, 需PyTorch)”。
        * 如果启用，确保 “CARN模型路径” 指向正确的 `carn.pth` 模型文件（默认为同目录下的 `carn.pth`，可通过“浏览...”修改）。
    7.  点击“开始识别”按钮。处理进度和日志会显示在界面下方。
    8.  每个输入文件处理完毕后，会在指定的输出目录下生成一个 `_ocr.txt` 后缀的文本文件，包含识别出的文字内容。

### 📝 Markdown/文本在线编辑器 (`read.py`)

* **启动**:
    ```bash
    python read.py
    ```
* **使用**:
    1.  启动后，Flask 应用会在本地 `http://127.0.0.1:23424/` (或启动时指定的其他端口) 上运行。
    2.  在浏览器中打开该地址。
    3.  左侧边栏会列出 `templates` 目录下的所有 `.md` 和 `.txt` 文件。
    4.  点击文件名即可在右侧查看和编辑其内容。Markdown 文件会自动渲染预览。
    5.  编辑后，点击内容区下方的“保存”按钮即可保存更改。
    6.  点击“截图”按钮可以对当前显示的 Markdown 内容区域（ID 为 `content` 的元素）进行截图，并下载为 PNG 图片。此功能依赖 `screenshot.py` 和正确配置的 EdgeDriver。
    7.  您可以在 `templates` 目录下直接添加、修改或删除文件，刷新网页即可看到更新。

### 📚 文件内容聚合工具 (`ReadTotally.py`)

* **启动**:
    ```bash
    python ReadTotally.py
    ```
* **使用**:
    1.  启动应用。
    2.  （可选）通过下拉菜单选择界面语言（英文/中文）。
    3.  点击“选择输出文件夹”按钮指定处理结果的保存位置。默认是桌面。
    4.  提供三种主要处理模式：
        * **处理单个文件**: 点击此按钮，选择任意一个文件。工具会读取该文件内容，并在输出文件夹下创建一个同名（但后缀为 `.txt`）的文件，包含原始文件名和内容。
        * **处理文件夹(递归)**: 点击此按钮，选择一个文件夹。工具会：
            * 在输出文件夹下创建一个与所选文件夹同名的子文件夹。
            * 在该子文件夹内创建一个 `folder_structure.txt` 文件，记录原始文件夹的结构。
            * 递归遍历所选文件夹，对于每个子文件夹（包括顶层选择的文件夹本身），将其中的所有文件内容（会排除预设的文件夹、文件和后缀名，如 `.git`, `.idea`, `node_modules`, `.md`, `.png` 等）合并到一个以该子文件夹命名的 `.txt` 文件中。
            * 同时，还会生成一个 `All.txt` 文件，包含所有子文件夹处理结果的汇总。
        * **处理文件夹(单层)**: 点击此按钮，选择一个文件夹。工具会：
            * 在输出文件夹下创建一个与所选文件夹同名且后缀为 `_read` 的子文件夹。
            * 在该子文件夹内创建一个 `folder_structure.txt` 文件。
            * 遍历所选文件夹的第一层项目：
                * 如果是文件，则创建一个同名（后缀为 `.txt`）的文件，包含其内容。
                * 如果是子文件夹，则将其下所有文件（递归，但同样应用排除规则）的内容合并到以该子文件夹命名的单个 `.txt` 文件中。
    5.  （可选）勾选或取消勾选“5分钟后自动删除”复选框。如果勾选，所有本次操作生成的输出文件/文件夹将在创建5分钟后被自动删除。
    6.  操作完成后会弹出提示。

## ⚙️ 核心模块 (辅助脚本)

* **`carn.py`**: 定义了 CARN (Cascading Residual Network) 超分辨率模型。被 `ocr.py` 调用以提升低分辨率图像的识别效果。需要 `carn.pth` 权重文件。
* **`screenshot.py`**: 提供了 `capture_element_precise_v4_6` 函数，使用 Selenium WebDriver (Edge) 精确截取网页中指定ID的HTML元素的完整内容。被 `read.py` 用于其截图功能。

## 📦 依赖项 (`requirements.txt`)

```text
Pillow>=9.0.0
PyMuPDF>=1.19.0
opencv-python>=4.5.0
numpy>=1.20.0
pytesseract>=0.3.8
# 对于 paddlepaddle 和 paddleocr，请访问其官网获取与您环境（CPU/GPU, CUDA版本等）匹配的最新安装命令。
# CPU 版本示例:
paddlepaddle>=2.5.0
paddleocr>=2.6.0
# GPU 版本示例 (根据您的 CUDA 版本选择，例如 CUDA 11.2.txt):
# paddlepaddle-gpu==2.5.0.post112.txt -f [https://www.paddlepaddle.org.cn/whl/linux/mkl/avx/stable.html](https://www.paddlepaddle.org.cn/whl/linux/mkl/avx/stable.html)
torch>=1.9.0
torchvision>=0.10.0
Flask>=2.0.0
selenium>=4.0.0
# Werkzeug (通常随 Flask 安装)
# tkinter (Python 标准库)