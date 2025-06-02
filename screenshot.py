# 文件路径：screenshot.py
# -*- coding: utf-8 -*-

"""
screenshot.py — 网页元素完整截图工具 (V4.6 - 针对父容器内滚动元素优化)
主要功能：
1. capture_element_precise_v4_6:
   - 针对目标元素在其父容器（如 .main-content-area）内滚动的情况进行优化。
   - 正确计算目标元素的完整尺寸作为画布大小。
   - 通过滚动父容器来逐段捕获目标元素内容。
   - 从浏览器视口截图中精确裁剪每段内容并拼接到最终图像。
   - 继承 V4.5 的显式等待等特性。
"""

from selenium import webdriver
from selenium.webdriver.edge.options import Options
from selenium.webdriver.edge.service import Service
from selenium.webdriver.common.by import By
from selenium.common.exceptions import NoSuchElementException, TimeoutException
from selenium.webdriver.support.ui import WebDriverWait
from PIL import Image
from io import BytesIO
import time
import math
import traceback

# EdgeDriver 路径
EDGE_DRIVER_PATH = r"D:\python\edgedriver_win32\msedgedriver.exe"  # 确保路径正确

# 要隐藏的元素
HIDE_ELEMENT_SELECTOR = ".toolbar"
HIDE_ELEMENT_ORIGINAL_DISPLAY = "flex"

# --- 显式等待配置 ---
WAIT_TIMEOUT = 15
MIN_SCROLL_HEIGHT_THRESHOLD = 100

# --- 新增：定义目标元素的滚动父容器 ---
# 根据您的 HTML 结构，#content 元素在 .main-content-area 内滚动
SCROLL_PARENT_SELECTOR = ".main-content-area"


def capture_element_precise_v4_6(url, element_id, output_path="element_precise_v4_6.png", width_buffer=20):
    """
    截取指定 ID 的 HTML 元素的完整内容 (V4.6 - 父容器内滚动优化)。

    Args:
        url (str): 目标网页的 URL.
        element_id (str): 需要截图的元素的 HTML ID (例如 'content').
        output_path (str): 截图保存路径.
        width_buffer (int): 在元素 scrollWidth 基础上增加的浏览器窗口额外宽度（像素）。
                            这有助于确保元素在具有边距或居中对齐时完整显示。
    Returns:
        bool: 截图成功返回 True, 失败返回 False.
    """
    options = Options()
    options.add_argument('--headless')
    options.add_argument('--disable-gpu')
    options.add_argument('--no-sandbox')
    options.add_argument('--hide-scrollbars')
    options.add_argument("--force-device-scale-factor=1")
    options.add_argument("--high-dpi-support=1")
    # 初始窗口大小设置得比较大，确保布局，后续会根据内容调整
    options.add_argument("--window-size=1920,1080")
    options.add_argument("--disable-extensions")
    options.add_argument("--disable-blink-features=AutomationControlled")
    options.use_chromium = True

    service = Service(executable_path=EDGE_DRIVER_PATH)
    driver = None
    element_to_hide = None
    original_display_value = HIDE_ELEMENT_ORIGINAL_DISPLAY
    screenshot_successful = False

    try:
        print("中文日志：初始化 WebDriver ...")
        driver = webdriver.Edge(service=service, options=options)
        driver.set_page_load_timeout(45)

        print(f"中文日志：导航到 URL: {url}")
        driver.get(url)

        # --- 隐藏工具栏元素 ---
        try:
            print(f"中文日志：查找并隐藏元素 ({HIDE_ELEMENT_SELECTOR})...")
            element_to_hide = driver.find_element(By.CSS_SELECTOR, HIDE_ELEMENT_SELECTOR)
            # 记录原始 display 值以便恢复
            original_display_value = driver.execute_script("return arguments[0].style.display;", element_to_hide)
            if not original_display_value:  # 如果 style.display 为空，尝试获取计算样式 (更复杂，暂用默认)
                original_display_value = HIDE_ELEMENT_ORIGINAL_DISPLAY
            driver.execute_script("arguments[0].style.display = 'none';", element_to_hide)
            time.sleep(0.2)
        except NoSuchElementException:
            print(f"中文日志：警告：未找到要隐藏的元素 '{HIDE_ELEMENT_SELECTOR}'。")
            element_to_hide = None
        except Exception as hide_err:
            print(f"中文日志：警告：隐藏元素时出错: {hide_err}")
            element_to_hide = None

        # --- 显式等待内容基本加载 ---
        print(
            f"中文日志：开始显式等待内容加载 (最长 {WAIT_TIMEOUT} 秒, 等待 #{element_id} scrollHeight > {MIN_SCROLL_HEIGHT_THRESHOLD}px)...")
        wait = WebDriverWait(driver, WAIT_TIMEOUT)
        try:
            wait.until(lambda d: d.execute_script(
                f"var elem = document.getElementById('{element_id}'); return elem && elem.scrollHeight > {MIN_SCROLL_HEIGHT_THRESHOLD};"
            ))
            print(f"中文日志：内容加载条件满足 (scrollHeight > {MIN_SCROLL_HEIGHT_THRESHOLD}px)。")
            time.sleep(1.0)  # 等待渲染稳定
        except TimeoutException:
            current_height_js = f"var elem = document.getElementById('{element_id}'); return elem ? elem.scrollHeight : 0;"
            current_height = driver.execute_script(current_height_js)
            print(
                f"中文日志：**错误**：等待超时！在 {WAIT_TIMEOUT} 秒内元素 #{element_id} 的 scrollHeight ({current_height}px) 未超过阈值 {MIN_SCROLL_HEIGHT_THRESHOLD}px。")
            raise
        except Exception as wait_err:
            print(f"中文日志：**错误**：在显式等待过程中发生错误: {wait_err}")
            traceback.print_exc()
            raise

        # --- 获取目标元素和其滚动父容器的引用 ---
        try:
            target_element = driver.find_element(By.ID, element_id)
            scroll_parent_element = driver.find_element(By.CSS_SELECTOR, SCROLL_PARENT_SELECTOR)
            print(f"中文日志：成功获取目标元素 #{element_id} 和滚动父容器 {SCROLL_PARENT_SELECTOR}")
        except NoSuchElementException as e:
            print(f"中文日志：**错误**：无法找到目标元素 #{element_id} 或其滚动父容器 {SCROLL_PARENT_SELECTOR}。错误：{e}")
            raise

        # --- 获取关键尺寸 ---
        try:
            content_scrollHeight = driver.execute_script("return arguments[0].scrollHeight;", target_element)
            content_scrollWidth = driver.execute_script("return arguments[0].scrollWidth;", target_element)
            scroll_parent_clientHeight = driver.execute_script("return arguments[0].clientHeight;",
                                                               scroll_parent_element)

            # 获取目标元素在视口中的初始位置，这对于计算浏览器窗口所需宽度很重要
            content_rect_initial = driver.execute_script("return arguments[0].getBoundingClientRect();", target_element)
            content_initial_x_in_viewport = content_rect_initial['left']

            print(
                f"中文日志：目标元素 #{element_id} 尺寸: scrollWidth={content_scrollWidth}, scrollHeight={content_scrollHeight}")
            print(f"中文日志：滚动父容器 {SCROLL_PARENT_SELECTOR} 尺寸: clientHeight={scroll_parent_clientHeight}")
            print(f"中文日志：目标元素初始视口左边距: {content_initial_x_in_viewport:.2f}px")

            if content_scrollHeight <= 0 or content_scrollWidth <= 0:
                raise ValueError(
                    f"目标元素 #{element_id} 的 scrollWidth ({content_scrollWidth}) 或 scrollHeight ({content_scrollHeight}) 为零或无效。")
            if scroll_parent_clientHeight <= 0:
                raise ValueError(
                    f"滚动父容器 {SCROLL_PARENT_SELECTOR} 的 clientHeight ({scroll_parent_clientHeight}) 为零或无效。")

        except Exception as e:
            print(f"中文日志：**错误**：获取元素尺寸时出错: {e}")
            traceback.print_exc()
            raise

        # --- 调整浏览器窗口大小 ---
        # 宽度应能容纳目标元素的左边距 + 宽度 + 右侧一些缓冲
        # 高度应至少是滚动父容器的高度加上浏览器 UI 的高度
        # 确保 content_initial_x_in_viewport 是非负数
        effective_content_x = max(0, content_initial_x_in_viewport)
        # 如果 X 是 320，宽度是 506，那么至少需要 320+506 = 826px
        required_browser_width = int(effective_content_x + content_scrollWidth + width_buffer)  # width_buffer 作为右侧的额外空间

        # 使用一个合理的最小宽度，或基于检测到的宽度
        target_browser_width = max(1200, required_browser_width)  # 例如最小1200px
        current_window_size = driver.get_window_size()
        # 浏览器窗口高度至少是滚动父容器的高度 + 额外空间给浏览器框架
        target_browser_height = max(current_window_size['height'],
                                    scroll_parent_clientHeight + 180)  # 180px for browser chrome and some buffer

        print(f"中文日志：尝试调整浏览器窗口尺寸至: {target_browser_width}w x {target_browser_height}h ...")
        try:
            driver.set_window_size(target_browser_width, target_browser_height)
            time.sleep(1.5)  # 等待布局稳定
            # 调整大小后，重新获取关键尺寸，因为它们可能已改变
            scroll_parent_clientHeight = driver.execute_script("return arguments[0].clientHeight;",
                                                               scroll_parent_element)
            content_rect_after_resize = driver.execute_script("return arguments[0].getBoundingClientRect();",
                                                              target_element)
            print(
                f"中文日志：尺寸调整后，滚动父容器 clientHeight={scroll_parent_clientHeight}, 目标元素视口 верх={content_rect_after_resize['top']:.2f}")
        except Exception as e:
            print(f"中文日志：警告：设置浏览器窗口大小到 {target_browser_width}x{target_browser_height} 时出错。错误: {e}")

        # --- 滚动与截图拼接逻辑 ---
        stitched_image = Image.new('RGB', (content_scrollWidth, content_scrollHeight))
        print(f"中文日志：创建拼接画布 (基于 #{element_id} 尺寸): {content_scrollWidth}w x {content_scrollHeight}h")

        # 重置滚动父容器的滚动位置到顶部
        driver.execute_script(f"document.querySelector('{SCROLL_PARENT_SELECTOR}').scrollTop = 0;")
        time.sleep(0.5)  # 等待滚动生效

        captured_height = 0
        loop_count = 0
        max_loops = math.ceil(content_scrollHeight / (
            scroll_parent_clientHeight * 0.8 if scroll_parent_clientHeight > 0 else content_scrollHeight)) + 5  # 启发式最大循环次数

        while captured_height < content_scrollHeight:
            loop_count += 1
            if loop_count > max_loops:
                print(f"中文日志：**错误**：截图循环次数 ({loop_count}) 过多，可能存在问题。提前终止。")
                break

            print(f"中文日志：截图循环 {loop_count}: 已捕获高度 {captured_height}/{content_scrollHeight}")

            # 获取目标元素当前在浏览器视口中的位置和尺寸
            current_content_rect = driver.execute_script("return arguments[0].getBoundingClientRect();", target_element)

            try:
                viewport_screenshot_png = driver.get_screenshot_as_png()
                viewport_image = Image.open(BytesIO(viewport_screenshot_png))
            except Exception as screenshot_err:
                print(f"中文日志：**错误**：截取浏览器视口截图时出错: {screenshot_err}")
                traceback.print_exc()
                # 如果截图失败，可能无法继续，尝试跳过或终止
                if loop_count == 1: raise  # 第一次就失败则抛出
                break  # 后续失败则终止循环

            # --- 计算从视口截图中间裁剪目标元素的部分 ---
            # 目标元素在视口中的X坐标 (相对于视口左上角)
            crop_x_on_viewport = int(current_content_rect['left'])
            # 目标元素在视口中的Y坐标 (相对于视口左上角)
            crop_y_on_viewport = int(current_content_rect['top'])

            # 要从视口截图中裁剪的宽度就是目标元素的scrollWidth
            crop_w_on_viewport = content_scrollWidth
            # 要从视口截图中裁剪的高度是目标元素当前在视口中可见的高度
            # 它受到视口底部和目标元素剩余高度的限制

            # 确保裁剪区域的起始点不为负 (元素可能部分在视口外)
            actual_crop_x = max(0, crop_x_on_viewport)
            actual_crop_y = max(0, crop_y_on_viewport)

            # 调整裁剪宽度，使其不超过从actual_crop_x开始的视口可用宽度
            actual_crop_w = min(crop_w_on_viewport, viewport_image.width - actual_crop_x)

            # 计算裁剪高度：
            # 1. 目标元素剩余未捕获的高度
            remaining_content_height = content_scrollHeight - captured_height
            # 2. 目标元素从其当前视口顶部(actual_crop_y)到底部在视口中可见的高度
            visible_height_in_viewport = viewport_image.height - actual_crop_y

            actual_crop_h = int(min(remaining_content_height, visible_height_in_viewport))
            actual_crop_h = max(0, actual_crop_h)  # 确保不为负

            if actual_crop_w <= 0 or actual_crop_h <= 0:
                print(
                    f"  中文日志：计算出的裁剪区域无效 (W:{actual_crop_w}, H:{actual_crop_h})。可能元素已完全滚动出视口或计算错误。")
                # 如果已经捕获了足够的高度，这可能是正常的结束
                if captured_height >= content_scrollHeight - 10:  # 允许少量像素误差
                    print("  中文日志：已接近或达到总高度，判断为正常结束。")
                    break
                # 如果是早期循环且裁剪无效，则可能存在问题
                if loop_count < 3:  # 任意选择的小数目
                    print(f"  中文日志：**警告**：在循环早期 ({loop_count}) 裁剪区域无效。检查元素定位。")
                # 尝试继续滚动，看是否能找到元素
                current_scroll_parent_scrollTop = driver.execute_script(
                    f"return document.querySelector('{SCROLL_PARENT_SELECTOR}').scrollTop;")
                next_scroll_position = current_scroll_parent_scrollTop + scroll_parent_clientHeight
                if next_scroll_position < content_scrollHeight:
                    driver.execute_script(
                        f"document.querySelector('{SCROLL_PARENT_SELECTOR}').scrollTop = {next_scroll_position};")
                    time.sleep(0.6)
                else:  # 无法再滚动
                    break
                continue

            print(
                f"  中文日志：从视口截图裁剪: src_xy=({actual_crop_x},{actual_crop_y}), src_wh=({actual_crop_w},{actual_crop_h})")
            segment_to_paste = viewport_image.crop((
                actual_crop_x,
                actual_crop_y,
                actual_crop_x + actual_crop_w,
                actual_crop_y + actual_crop_h
            ))

            # 粘贴到最终画布上的位置
            paste_x_on_canvas = 0  # 因为画布是基于目标元素自身的宽度
            paste_y_on_canvas = captured_height

            print(
                f"  中文日志：粘贴裁剪后的段到拼接图 (x={paste_x_on_canvas}, y={paste_y_on_canvas}) 尺寸 {segment_to_paste.size}")
            stitched_image.paste(segment_to_paste, (paste_x_on_canvas, paste_y_on_canvas))

            captured_height += segment_to_paste.height  # 使用实际粘贴的高度更新

            if captured_height >= content_scrollHeight:
                print(f"中文日志：已捕获并粘贴总高度 {captured_height} >= {content_scrollHeight}。完成。")
                break

            # --- 滚动父容器以显示下一部分 ---
            # 下一个滚动位置应该是当前捕获高度（这代表目标元素内已经处理过的部分）
            next_scroll_target_in_parent = captured_height
            # 但要确保不超过最大滚动距离
            max_scroll_top_for_parent = content_scrollHeight - scroll_parent_clientHeight
            # (如果元素比父容器还矮，则最大滚动为0)
            max_scroll_top_for_parent = max(0, max_scroll_top_for_parent)

            actual_next_scroll = min(next_scroll_target_in_parent, max_scroll_top_for_parent)

            # 检查是否真的需要滚动 (如果剩余部分已在视口内)
            # current_content_bottom_y_in_rect = current_content_rect['top'] + segment_to_paste.height
            # scroll_parent_bottom_y_in_rect = driver.execute_script("return arguments[0].getBoundingClientRect().bottom;", scroll_parent_element)
            # if current_content_bottom_y_in_rect >= scroll_parent_bottom_y_in_rect and captured_height < content_scrollHeight :
            #   print("滚动父容器")

            current_scrollTop_in_parent = driver.execute_script(
                f"return document.querySelector('{SCROLL_PARENT_SELECTOR}').scrollTop;")
            if actual_next_scroll > current_scrollTop_in_parent:  # 仅当需要向下滚动时执行
                print(f"  中文日志：滚动父容器到: {actual_next_scroll} (当前: {current_scrollTop_in_parent})")
                driver.execute_script(
                    f"document.querySelector('{SCROLL_PARENT_SELECTOR}').scrollTop = {actual_next_scroll};")
                time.sleep(0.6)  # 等待滚动和可能的懒加载/渲染
            elif captured_height < content_scrollHeight:
                print(
                    f"  中文日志：计算出的下一个滚动位置 ({actual_next_scroll}) 不大于当前 ({current_scrollTop_in_parent})，但内容未完。可能存在问题或已达底部。")
                # 如果父容器无法再滚动，但内容未完，说明父容器太小或有其他问题
                if abs(current_scrollTop_in_parent - max_scroll_top_for_parent) < 5:  # 已经在底部附近
                    print("  中文日志：父容器已在滚动底部。剩余内容可能无法通过滚动父容器来完全展现。")
                    # 这种情况下，可能最后一部分内容需要特殊处理或会截断
                # 强制结束，因为无法再通过滚动父容器来获取更多内容
                break
            else:
                print(f"  中文日志：无需进一步滚动或已完成。")

        print("中文日志：元素滚动与截图拼接完成。")
        final_image = stitched_image
        print(f"中文日志：最终图片尺寸: {final_image.size}")

        # 验证最终尺寸
        width_diff = abs(final_image.width - content_scrollWidth)
        height_diff = abs(final_image.height - content_scrollHeight)
        if width_diff > 10 or height_diff > 20:  # 允许一定的像素差异
            print(
                f"中文日志：**警告**：最终图片尺寸 {final_image.size} 与测量的目标元素滚动尺寸 ({content_scrollWidth}x{content_scrollHeight}) 相差较大。W_diff={width_diff}, H_diff={height_diff}")

        final_image.save(output_path)
        print(f"中文日志：成功精确截取元素 '{element_id}' 到 {output_path} (V4.6)")
        screenshot_successful = True

    except TimeoutException:
        print(f"中文日志：**截图失败 (V4.6)**，因为等待元素 '{element_id}' 内容加载超时。")
        screenshot_successful = False
    except NoSuchElementException as e:
        print(f"中文日志：**截图失败 (V4.6)**，无法找到必要的元素: {e}")
        screenshot_successful = False
    except ValueError as e:
        print(f"中文日志：**截图失败 (V4.6)**，获取的尺寸无效或计算错误: {e}")
        screenshot_successful = False
    except Exception as e:
        print(f"中文日志：在截图函数 capture_element_precise_v4_6 执行过程中发生未知错误: {e}")
        traceback.print_exc()
        screenshot_successful = False
    finally:
        if driver:
            # --- 恢复隐藏的元素 ---
            if element_to_hide:
                try:
                    print(
                        f"中文日志：恢复元素 '{HIDE_ELEMENT_SELECTOR}' 的显示 (原始 display: '{original_display_value}')...")
                    driver.execute_script(f"arguments[0].style.display = '{original_display_value}';", element_to_hide)
                except Exception as restore_err:
                    print(f"中文日志：警告：恢复元素 '{HIDE_ELEMENT_SELECTOR}' 时出错: {restore_err}")

            print("中文日志：关闭 WebDriver。")
            driver.quit()

        print(f"中文日志：截图函数 capture_element_precise_v4_6 执行完毕，返回: {screenshot_successful}")
        return screenshot_successful


if __name__ == '__main__':
    # --- 测试 ---
    # 确保 Flask 应用正在运行，并且 URL 和文件名正确
    # 例如: python app.py
    # 然后在另一个终端运行: python screenshot.py

    # 从你的日志中获取的 URL 示例
    test_url = "http://127.0.0.1:23424/?file=编译原理复习.txt"
    test_element_id = "content"  # 你的目标元素 ID
    output_file_path = "test_screenshot_v4_6.png"

    print(f"中文测试：开始测试截图功能，URL: {test_url}, Element ID: {test_element_id}")
    success = capture_element_precise_v4_6(test_url, test_element_id, output_file_path)
    if success:
        print(f"中文测试：截图成功保存到: {output_file_path}")
    else:
        print(f"中文测试：截图失败。请检查日志。")