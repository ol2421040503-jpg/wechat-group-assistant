# -*- coding: utf-8 -*-
"""
微信群助手 - 微信自动化操作模块
基于 uiautomation2 实现 Windows UI 自动化
"""

import time
import logging
from typing import List, Optional, Tuple

try:
    import uiautomation as auto
except ImportError:
    auto = None

from config import ADD_INTERVAL

logger = logging.getLogger(__name__)


class WeChatAutomation:
    def __init__(self):
        self.wechat_window = None
        self.is_connected = False

    def connect(self) -> bool:
        """连接微信窗口"""
        if auto is None:
            logger.error("uiautomation2 未安装，请运行: pip install uiautomation2")
            return False

        try:
            # 查找微信主窗口
            self.wechat_window = auto.WindowControl(Name="微信", ClassName="WeChatMainWndForPC")
            if self.wechat_window.Exists(maxWaitSeconds=5):
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
        """获取当前聊天窗口的名称（群名或好友名）"""
        if not self.is_connected:
            return None

        try:
            # 聊天窗口的标题通常在顶部
            chat_name_control = self.wechat_window.TextControl(
                foundIndex=1,
                Name=lambda n: n and len(n) > 1
            )

            # 尝试多种方式获取聊天名称
            # 方法1: 查找标题栏
            title_control = self.wechat_window.Control(
                ControlType=auto.ControlType.TitleBarControl,
                foundIndex=1
            )
            if title_control.Exists(maxWaitSeconds=1):
                name = title_control.Name
                if name and name != "微信":
                    return name

            # 方法2: 查找聊天信息区域
            chat_info_control = self.wechat_window.TextControl(
                SubName="聊天信息",
                foundIndex=1
            )
            if chat_info_control.Exists(maxWaitSeconds=1):
                parent = chat_info_control.GetParentControl()
                if parent:
                    # 向上查找群名
                    for _ in range(5):
                        parent = parent.GetParentControl()
                        if parent and parent.Name:
                            name = parent.Name.strip()
                            if name and len(name) > 1 and name != "微信":
                                return name

            return None

        except Exception as e:
            logger.error(f"获取聊天名称失败: {e}")
            return None

    def open_group_members(self) -> bool:
        """打开群成员列表"""
        if not self.is_connected:
            return False

        try:
            # 查找聊天窗口顶部的群名/联系人名称并点击
            # 通常需要先点击群名进入群信息页面

            # 方式1: 点击聊天标题
            chat_title = self.wechat_window.ButtonControl(
                Name="聊天信息",
                foundIndex=1
            )

            if not chat_title.Exists(maxWaitSeconds=2):
                # 尝试查找更多聊天信息按钮
                chat_title = self.wechat_window.HyperlinkControl(
                    SubName="聊天信息",
                    foundIndex=1
                )

            if chat_title.Exists(maxWaitSeconds=2):
                chat_title.Click()
                time.sleep(1)
                logger.info("已点击群成员按钮")
                return True

            logger.warning("未找到群成员按钮，请手动点击群名进入群信息")
            return False

        except Exception as e:
            logger.error(f"打开群成员列表失败: {e}")
            return False

    def get_group_members_list(self) -> List[Tuple[str, str]]:
        """
        获取群成员列表
        返回: [(备注名/昵称, 微信号/ID), ...]
        """
        if not self.is_connected:
            return []

        members = []

        try:
            # 等待群成员列表加载
            time.sleep(1)

            # 查找群成员列表区域
            # 通常是一个 ListControl 或 多个 ListItemControl

            # 方式1: 查找成员列表容器
            member_list = self.wechat_window.ListControl(
                foundIndex=1
            )

            if not member_list.Exists(maxWaitSeconds=3):
                # 尝试滚动查找
                scroll_control = self.wechat_window.ScrollViewerControl(
                    foundIndex=1
                )
                if scroll_control.Exists(maxWaitSeconds=2):
                    member_list = scroll_control

            # 遍历所有成员项
            if member_list.Exists(maxWaitSeconds=2):
                # 获取所有成员名称
                member_items = member_list.GetChildren()

                for item in member_items:
                    try:
                        # 尝试获取成员名称
                        name = None
                        wxid = None

                        # 获取控件的名称
                        if item.Name and len(item.Name.strip()) > 0:
                            name = item.Name.strip()

                        # 查找子控件获取更多信息
                        texts = item.Texts()
                        if texts:
                            for text in texts:
                                if text and len(text.strip()) > 0:
                                    if not name:
                                        name = text.strip()
                                    # 判断是否是微信号（通常是wxid开头或纯数字）
                                    if text.startswith('wxid') or text.isdigit():
                                        wxid = text.strip()

                        if name:
                            # 过滤掉非成员的项（如搜索框、按钮等）
                            if name not in ['搜索', '成员', '群聊名称', '群二维码', '群公告']:
                                members.append((name, wxid or ""))

                    except Exception as e:
                        continue

            logger.info(f"获取到 {len(members)} 个群成员")
            return members

        except Exception as e:
            logger.error(f"获取群成员列表失败: {e}")
            return []

    def search_and_add(self, member_name: str) -> Tuple[bool, str]:
        """
        搜索并添加好友
        返回: (是否成功, 错误信息)
        """
        if not self.is_connected:
            return False, "未连接到微信"

        try:
            # 返回到聊天窗口
            # 按 Escape 或点击返回
            self._press_escape()
            time.sleep(0.5)

            # 点击搜索框
            search_control = self.wechat_window.EditControl(
                SubName="搜索",
                foundIndex=1
            )

            if not search_control.Exists(maxWaitSeconds=2):
                search_control = self.wechat_window.EditControl(
                    Name="搜索",
                    foundIndex=1
                )

            if search_control.Exists(maxWaitSeconds=2):
                search_control.Click()
                time.sleep(0.3)

                # 输入搜索内容
                search_control.TypeText(member_name, interval=0.05)
                time.sleep(1)

                # 从搜索结果中选择
                # 查找联系人列表
                contact_list = self.wechat_window.ListControl(
                    foundIndex=1
                )

                if contact_list.Exists(maxWaitSeconds=3):
                    # 点击第一个搜索结果
                    first_contact = contact_list.GetFirstChildControl()
                    if first_contact:
                        first_contact.Click()
                        time.sleep(1)

                        # 点击添加按钮
                        return self._click_add_button()

            # 如果找不到搜索结果，尝试其他方式
            self._press_escape()
            return False, "未找到联系人"

        except Exception as e:
            logger.error(f"添加好友失败: {e}")
            self._press_escape()
            return False, str(e)

    def _click_add_button(self) -> Tuple[bool, str]:
        """点击添加按钮"""
        try:
            # 查找添加按钮
            add_button = self.wechat_window.ButtonControl(
                SubName="添加",
                foundIndex=1
            )

            if not add_button.Exists(maxWaitSeconds=2):
                add_button = self.wechat_window.ButtonControl(
                    Name="添加",
                    foundIndex=1
                )

            if add_button.Exists(maxWaitSeconds=2):
                add_button.Click()
                time.sleep(0.5)

                # 查找发送验证消息按钮
                send_button = self.wechat_window.ButtonControl(
                    SubName="发送",
                    foundIndex=1
                )

                if send_button.Exists(maxWaitSeconds=2):
                    send_button.Click()
                    logger.info("添加请求已发送")
                    return True, ""

                return True, "请手动发送验证消息"

            # 可能已经添加过了
            already_added = self.wechat_window.TextControl(
                SubName="已添加",
                foundIndex=1
            )

            if already_added.Exists(maxWaitSeconds=1):
                return False, "对方已是好友"

            return False, "未找到添加按钮"

        except Exception as e:
            return False, str(e)

    def _press_escape(self):
        """按 Escape 键返回"""
        try:
            self.wechat_window.SendKeys('{Escape}', interval=0.1)
        except Exception:
            pass

    def get_wechat_focused(self):
        """确保微信窗口获得焦点"""
        if self.wechat_window and self.wechat_window.Exists(maxWaitSeconds=1):
            self.wechat_window.SetFocus()
            time.sleep(0.3)


def test_connection() -> bool:
    """测试连接"""
    if auto is None:
        print("❌ uiautomation2 未安装")
        print("请运行: pip install uiautomation2")
        return False

    try:
        # 查找微信窗口
        wechat_window = auto.WindowControl(Name="微信", ClassName="WeChatMainWndForPC")
        if wechat_window.Exists(maxWaitSeconds=5):
            print("✅ 成功连接到微信")
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
