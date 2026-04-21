# -*- coding: utf-8 -*-
"""
微信群助手 - 微信自动化操作模块
基于 pyautogui + pywin32 实现 Windows 自动化
"""

import time
import logging
import os
import json
from typing import List, Optional, Tuple

try:
    import pyautogui
    import win32gui
    import win32con
    import win32api
except ImportError:
    pyautogui = None

from config import ADD_INTERVAL

logger = logging.getLogger(__name__)

# 禁用 pyautogui 的安全特性
if pyautogui:
    pyautogui.FAILSAFE = True
    pyautogui.PAUSE = 0.3


class WeChatAutomation:
    def __init__(self):
        self.wechat_hwnd = None
        self.is_connected = False
        self.screenshot_folder = "screenshots"

        # 创建截图保存目录
        if not os.path.exists(self.screenshot_folder):
            os.makedirs(self.screenshot_folder)

        # 按钮截图保存位置
        self.button_screenshots = {
            "search": f"{self.screenshot_folder}/btn_search.png",
            "add_friend": f"{self.screenshot_folder}/btn_add.png",
            "send": f"{self.screenshot_folder}/btn_send.png",
            "contact_info": f"{self.screenshot_folder}/btn_contact_info.png",
        }

    def connect(self) -> bool:
        """连接微信窗口"""
        if pyautogui is None:
            logger.error("请安装依赖: pip install pyautogui pywin32 Pillow")
            return False

        try:
            # 查找微信窗口
            self.wechat_hwnd = win32gui.FindWindow("Qt51514QWindowIcon", "微信")

            if self.wechat_hwnd:
                # 确保窗口可见
                win32gui.ShowWindow(self.wechat_hwnd, win32con.SW_RESTORE)
                win32gui.SetForegroundWindow(self.wechat_hwnd)
                time.sleep(0.5)

                self.is_connected = True
                logger.info("成功连接到微信窗口")
                return True
            else:
                logger.warning("未找到微信窗口，请确保微信已启动")
                return False

        except Exception as e:
            logger.error(f"连接微信失败: {e}")
            return False

    def get_current_chat_name(self) -> Optional[str]:
        """获取当前聊天窗口的名称"""
        if not self.is_connected:
            return None

        try:
            # 获取窗口标题
            title = win32gui.GetWindowText(self.wechat_hwnd)
            logger.info(f"窗口标题: {title}")

            # 微信窗口标题格式通常是 "群名 - 微信" 或 "联系人昵称"
            if " - " in title:
                return title.split(" - ")[0].strip()
            elif title and title != "微信":
                return title

            return None

        except Exception as e:
            logger.error(f"获取聊天名称失败: {e}")
            return None

    def click_on_screen(self, image_path: str, confidence: float = 0.8) -> bool:
        """在屏幕上查找并点击图片"""
        if not os.path.exists(image_path):
            logger.warning(f"截图不存在: {image_path}")
            return False

        try:
            location = pyautogui.locateOnScreen(image_path, confidence=confidence)
            if location:
                center = pyautogui.center(location)
                pyautogui.click(center.x, center.y)
                logger.info(f"点击位置: {center}")
                return True
            else:
                logger.warning(f"未找到图片: {image_path}")
                return False
        except Exception as e:
            logger.error(f"点击失败: {e}")
            return False

    def find_on_screen(self, image_path: str, confidence: float = 0.8):
        """在屏幕上查找图片位置"""
        if not os.path.exists(image_path):
            return None

        try:
            return pyautogui.locateOnScreen(image_path, confidence=confidence)
        except Exception as e:
            logger.error(f"查找图片失败: {e}")
            return None

    def type_text(self, text: str, interval: float = 0.05):
        """输入文本"""
        try:
            pyautogui.write(text, interval=interval)
        except Exception as e:
            logger.error(f"输入文本失败: {e}")

    def press_key(self, key: str):
        """按键"""
        try:
            pyautogui.press(key)
        except Exception as e:
            logger.error(f"按键失败: {e}")

    def open_group_members(self) -> bool:
        """打开群成员列表"""
        if not self.is_connected:
            return False

        try:
            # 查找聊天信息按钮
            btn_path = self.button_screenshots.get("contact_info")
            if btn_path and os.path.exists(btn_path):
                if self.click_on_screen(btn_path):
                    time.sleep(1)
                    logger.info("已点击群信息按钮")
                    return True

            logger.warning("未找到群信息按钮截图，请先截图保存")
            return False

        except Exception as e:
            logger.error(f"打开群成员列表失败: {e}")
            return False

    def get_group_members_list(self) -> List[Tuple[str, str]]:
        """获取群成员列表 - 需要手动截图识别"""
        if not self.is_connected:
            return []

        # 由于微信界面复杂性，建议用户手动复制成员列表
        # 这里返回一个空列表，用户需要手动导入
        logger.info("建议手动导入群成员列表")
        return []

    def search_and_add(self, member_name: str) -> Tuple[bool, str]:
        """搜索并添加好友"""
        if not self.is_connected:
            return False, "未连接到微信"

        try:
            # 点击搜索框
            search_btn_path = self.button_screenshots.get("search")
            if search_btn_path and os.path.exists(search_btn_path):
                if not self.click_on_screen(search_btn_path):
                    logger.warning("未找到搜索按钮")
            else:
                # 备用：使用快捷键
                self.press_key('f')
                time.sleep(0.3)

            time.sleep(0.5)

            # 输入搜索内容
            self.type_text(member_name, interval=0.05)
            time.sleep(1)

            # 点击第一个搜索结果（需要用户手动设置截图）
            # 查找添加按钮
            add_btn_path = self.button_screenshots.get("add_friend")
            if add_btn_path and os.path.exists(add_btn_path):
                if self.click_on_screen(add_btn_path):
                    time.sleep(0.5)
                    # 点击发送
                    send_btn_path = self.button_screenshots.get("send")
                    if send_btn_path and os.path.exists(send_btn_path):
                        self.click_on_screen(send_btn_path)
                    return True, ""

            logger.warning("未找到添加按钮截图，请先截图保存")
            return False, "请手动添加"

        except Exception as e:
            logger.error(f"添加好友失败: {e}")
            return False, str(e)

    def get_wechat_focused(self):
        """确保微信窗口获得焦点"""
        if self.wechat_hwnd:
            try:
                win32gui.SetForegroundWindow(self.wechat_hwnd)
                time.sleep(0.3)
            except Exception:
                pass


def test_connection() -> bool:
    """测试连接"""
    if pyautogui is None:
        print("❌ 请安装依赖")
        print("请运行: pip install pywin32 pyautogui Pillow")
        return False

    try:
        wechat_hwnd = win32gui.FindWindow("Qt51514QWindowIcon", "微信")
        if wechat_hwnd:
            # 获取窗口标题
            title = win32gui.GetWindowText(wechat_hwnd)
            print(f"✅ 成功连接到微信")
            print(f"   窗口标题: {title}")

            # 截图保存提示
            print("\n📸 建议截图保存按钮位置:")
            print("   1. 搜索按钮 - 保存为 screenshots/btn_search.png")
            print("   2. 添加按钮 - 保存为 screenshots/btn_add.png")
            print("   3. 发送按钮 - 保存为 screenshots/btn_send.png")
            print("   4. 群信息按钮 - 保存为 screenshots/btn_contact_info.png")
            print("\n   截图越清晰，识别越准确！")

            return True
        else:
            print("❌ 未找到微信窗口")
            print("请确保微信已启动并登录")
            return False
    except Exception as e:
        print(f"❌ 连接失败: {e}")
        return False


if __name__ == "__main__":
    print("=== 微信群助手连接测试 ===\n")
    test_connection()
