# -*- coding: utf-8 -*-
# 文件路径：read.py (V5.2 - 无需修改，确认 traceback 导入)

from flask import Flask, render_template, request, jsonify, send_file, abort
from werkzeug.utils import safe_join 
import os
import glob 
import tempfile
import uuid
import traceback # <--- 确认此行存在
# 导入 V4.5 截图函数
from screenshot import capture_element_precise_v4_6

app = Flask(__name__)
DATA_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'templates')

# --- Functions: get_data_files, index, switch_file, save_file, serve_template_asset ---
# (这些函数保持 V5.1 版本不变)
# ... (粘贴 V5.1 中的这些函数代码) ...
def get_data_files():
    """获取 templates 目录下所有的 .md 和 .txt 文件列表"""
    if not os.path.exists(DATA_DIR):
        os.makedirs(DATA_DIR)
        print(f"中文日志：创建了 templates 目录: {DATA_DIR}")
    md_files = glob.glob(os.path.join(DATA_DIR, '*.md'))
    txt_files = glob.glob(os.path.join(DATA_DIR, '*.txt'))
    all_files_paths = md_files + txt_files
    all_files_basenames = [os.path.basename(p) for p in all_files_paths]
    unique_files = sorted(list(set(all_files_basenames))) 
    print(f"中文日志：在 templates 中找到的文件: {unique_files}")
    return unique_files

@app.route('/')
def index():
    """主页路由，显示文件列表和选定文件的内容"""
    all_files = get_data_files() 
    current = request.args.get('file')
    if not current and all_files: 
        current = all_files[0]
    elif not all_files: 
        current = '' 
        default_filename = 'readme.md' 
        default_path = os.path.join(DATA_DIR, default_filename)
        if not os.path.exists(default_path):
             try:
                 with open(default_path, 'w', encoding='utf-8') as f:
                     f.write('# 欢迎使用\n\n这是一个示例文件。\n\n请在 `templates` 目录下创建 `.md` 或 `.txt` 文件。\n\n## 图片示例\n\n(请确保图片 `example.png` 在 `templates` 目录下)\n\n![示例图片](/templates/example.png)\n\n## 公式示例\n\n行内公式：$E=mc^2$\n\n块级公式：\n$$\\sum_{i=1}^{n} i = \\frac{n(n+1)}{2}$$')
                 print(f"中文日志：创建了默认文件: {default_filename}")
                 all_files.append(default_filename)
                 if not current: current = default_filename
             except Exception as create_err:
                 print(f"中文日志：创建默认文件失败: {create_err}")

    content = "" 
    if current and current in all_files: 
        try:
             path = safe_join(DATA_DIR, current) 
             if not path or not os.path.exists(path) or not os.path.abspath(path).startswith(os.path.abspath(DATA_DIR)):
                  print(f"中文日志：错误：尝试访问无效或不允许的文件路径: {path}")
                  content = f"# 错误：无法访问文件 {current}"
                  current = '' 
             else:
                 with open(path, 'r', encoding='utf-8') as f:
                     content = f.read()
        except FileNotFoundError:
             print(f"中文日志：错误：文件未找到 {current}")
             content = f"# 文件 {current} 未找到"
             current = '' 
        except Exception as e:
             print(f"中文日志：错误：读取文件 {current} 时出错: {e}")
             content = f"# 加载文件 {current} 时出错\n\n{e}"
             current = '' 
             
    return render_template('index.html',
                           files=all_files,
                           content=content,
                           current_file=current)

@app.route('/switch_file', methods=['POST'])
def switch_file():
    """处理切换文件的 AJAX 请求"""
    fname = request.form.get('filename')
    if not fname:
        return jsonify({'error': '未提供文件名'}), 400
    try:
        path = safe_join(DATA_DIR, fname) 
        if not path or not os.path.exists(path) or not os.path.abspath(path).startswith(os.path.abspath(DATA_DIR)):
            print(f"中文日志：切换文件错误：尝试访问无效或不允许的文件路径: {path}")
            return jsonify({'error': f'文件未找到或不允许访问: {fname}'}), 404
        with open(path, 'r', encoding='utf-8') as f:
            txt = f.read()
        return jsonify({'content': txt}) 
    except FileNotFoundError:
        return jsonify({'error': f'文件未找到: {fname}'}), 404
    except Exception as e:
        print(f"中文日志：错误：切换到文件 {fname} 时读取错误: {e}")
        return jsonify({'error': f'无法读取文件: {e}'}), 500

@app.route('/save_file', methods=['POST'])
def save_file():
    """处理保存文件的 AJAX 请求"""
    fname = request.form.get('filename')
    content = request.form.get('content')
    if not fname:
        return jsonify({'status': 'error', 'message': '未提供文件名'}), 400
    if content is None:
         return jsonify({'status': 'error', 'message': '未提供内容'}), 400
    try:
        path = safe_join(DATA_DIR, fname) 
        allowed_extensions = ('.md', '.txt')
        if not path or not fname.lower().endswith(allowed_extensions) or not os.path.abspath(path).startswith(os.path.abspath(DATA_DIR)):
             print(f"中文日志：保存文件错误：尝试写入无效或不允许的文件路径/类型: {path}")
             return jsonify({'status': 'error', 'message': '无效的文件名或路径'}), 403 
        with open(path, 'w', encoding='utf-8') as f:
            f.write(content)
        return jsonify({'status': 'success'}) 
    except Exception as e:
        print(f"中文日志：错误：保存文件 {fname} 时出错: {e}")
        return jsonify({'status': 'error', 'message': f'无法保存文件: {e}'}), 500

@app.route('/templates/<path:filename>')
def serve_template_asset(filename):
    """提供 templates 目录下的静态文件"""
    try:
        safe_path = safe_join(DATA_DIR, filename) 
    except (ValueError, TypeError):
         print(f"中文日志：警告：无效的文件名请求: {filename}")
         abort(404)
    if not safe_path or not os.path.abspath(safe_path).startswith(os.path.abspath(DATA_DIR)):
        print(f"中文日志：警告：尝试访问 templates 目录外的文件: {filename}")
        abort(404) 
    if not os.path.isfile(safe_path):
        print(f"中文日志：未找到 templates 下的文件: {safe_path}")
        abort(404)
    try:
        return send_file(safe_path)
    except Exception as e:
        print(f"中文日志：发送文件 {safe_path} 时出错: {e}")
        abort(500)
# --- End of unchanged functions ---


@app.route('/take_screenshot', methods=['POST'])
def take_screenshot_route():
    """处理截图请求"""
    temp_dir = tempfile.gettempdir()
    name = f"content_screenshot_v4.5_{uuid.uuid4().hex}.png" 
    output_path = os.path.join(temp_dir, name)

    current_file = request.form.get('current_file', '')
    base_url = request.url_root.rstrip('/')
    target_base = base_url
    target_url = f"{target_base}/?file={current_file}" if current_file else f"{target_base}/"

    element_to_capture = 'content' 

    print(f"中文日志：尝试 V4.5 (显式等待) 精确元素截图 #{element_to_capture} 来自 URL: {target_url}")

    try:
        ok = capture_element_precise_v4_6(target_url, element_to_capture, output_path)

        if not ok:
            print(f"中文日志：截图函数 capture_element_precise_v4_6 返回 False，URL: {target_url}")
            return jsonify({'status': 'error', 'message': f'无法精确截取元素 #{element_to_capture}。内容可能未完全加载或过短。'}), 500
            
        print(f"中文日志：V4.5 精确元素截图成功: {output_path}")
        return send_file(output_path, mimetype='image/png',
                        as_attachment=True, download_name=name)
                        
    except Exception as e:
        print(f"中文日志：截图路由 /take_screenshot 发生意外错误: {e}")
        traceback.print_exc() # 确保打印 traceback
        return jsonify({'status': 'error', 'message': '截图过程中发生意外服务器错误。'}), 500

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=23424)