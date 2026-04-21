# -*- coding: utf-8 -*-
"""
微信群助手 - 主程序
半自动化工具，用于统计微信群成员、记录添加历史
"""

import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import threading
import logging
from datetime import datetime
from typing import List, Optional

from database import Database
from wechat import WeChatAutomation
from config import DAILY_LIMIT, ADD_INTERVAL

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('wechat_assistant.log', encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


class WeChatAssistantApp:
    def __init__(self, root: tk.Tk):
        self.root = root
        self.root.title("微信群助手 v1.0")
        self.root.geometry("900x700")
        self.root.resizable(True, True)

        # 初始化组件
        self.db = Database()
        self.wechat = WeChatAutomation()

        # 状态变量
        self.current_group = tk.StringVar(value="")
        self.selected_members = []
        self.is_running = False
        self.add_thread = None

        # 创建界面
        self._create_widgets()
        self._update_stats()

        # 绑定关闭事件
        self.root.protocol("WM_DELETE_WINDOW", self._on_close)

    def _create_widgets(self):
        """创建界面组件"""
        # 顶部信息栏
        info_frame = ttk.LabelFrame(self.root, text="状态信息", padding=10)
        info_frame.pack(fill=tk.X, padx=10, pady=5)

        # 统计信息
        stats_frame = ttk.Frame(info_frame)
        stats_frame.pack(fill=tk.X)

        self.today_label = ttk.Label(stats_frame, text="今日添加: 0/20")
        self.today_label.pack(side=tk.LEFT, padx=10)

        self.total_label = ttk.Label(stats_frame, text="总成员: 0 | 已添加: 0 | 未添加: 0")
        self.total_label.pack(side=tk.LEFT, padx=10)

        self.connection_label = ttk.Label(stats_frame, text="⚫ 未连接", foreground="red")
        self.connection_label.pack(side=tk.RIGHT, padx=10)

        # 连接按钮
        btn_frame = ttk.Frame(info_frame)
        btn_frame.pack(fill=tk.X, pady=5)

        ttk.Button(btn_frame, text="连接微信", command=self._connect_wechat).pack(side=tk.LEFT, padx=5)
        ttk.Button(btn_frame, text="获取当前群", command=self._get_current_chat).pack(side=tk.LEFT, padx=5)
        ttk.Button(btn_frame, text="刷新群成员", command=self._refresh_members).pack(side=tk.LEFT, padx=5)

        # 群选择下拉框
        group_frame = ttk.Frame(info_frame)
        group_frame.pack(fill=tk.X, pady=5)

        ttk.Label(group_frame, text="当前群:").pack(side=tk.LEFT, padx=5)
        self.group_combo = ttk.Combobox(group_frame, textvariable=self.current_group, state="readonly", width=40)
        self.group_combo.pack(side=tk.LEFT, padx=5)
        self.group_combo.bind('<<ComboboxSelected>>', self._on_group_selected)

        # 中部 - 成员列表
        list_frame = ttk.LabelFrame(self.root, text="群成员列表", padding=10)
        list_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)

        # 工具栏
        toolbar_frame = ttk.Frame(list_frame)
        toolbar_frame.pack(fill=tk.X, pady=(0, 5))

        # 过滤选项
        ttk.Label(toolbar_frame, text="筛选:").pack(side=tk.LEFT, padx=5)
        self.filter_var = tk.StringVar(value="all")
        ttk.Radiobutton(toolbar_frame, text="全部", variable=self.filter_var, value="all",
                        command=self._filter_members).pack(side=tk.LEFT, padx=5)
        ttk.Radiobutton(toolbar_frame, text="未添加", variable=self.filter_var, value="not_added",
                        command=self._filter_members).pack(side=tk.LEFT, padx=5)
        ttk.Radiobutton(toolbar_frame, text="已添加", variable=self.filter_var, value="added",
                        command=self._filter_members).pack(side=tk.LEFT, padx=5)

        ttk.Button(toolbar_frame, text="全选未添加", command=self._select_all_not_added).pack(side=tk.RIGHT, padx=5)
        ttk.Button(toolbar_frame, text="取消全选", command=self._deselect_all).pack(side=tk.RIGHT, padx=5)

        # 表格
        table_frame = ttk.Frame(list_frame)
        table_frame.pack(fill=tk.BOTH, expand=True)

        # 创建表格
        columns = ('select', 'name', 'wxid', 'is_added', 'add_count', 'last_time')
        self.tree = ttk.Treeview(table_frame, columns=columns, show='headings', selectmode='extended')

        self.tree.heading('select', text='选择')
        self.tree.heading('name', text='昵称/备注')
        self.tree.heading('wxid', text='微信号')
        self.tree.heading('is_added', text='状态')
        self.tree.heading('add_count', text='添加次数')
        self.tree.heading('last_time', text='最后添加时间')

        self.tree.column('select', width=50, anchor='center')
        self.tree.column('name', width=150)
        self.tree.column('wxid', width=180)
        self.tree.column('is_added', width=80, anchor='center')
        self.tree.column('add_count', width=80, anchor='center')
        self.tree.column('last_time', width=150)

        # 滚动条
        scrollbar = ttk.Scrollbar(table_frame, orient=tk.VERTICAL, command=self.tree.yview)
        self.tree.configure(yscrollcommand=scrollbar.set)

        self.tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        # 复选框支持
        self.checkboxes = {}

        # 底部操作区
        action_frame = ttk.LabelFrame(self.root, text="操作", padding=10)
        action_frame.pack(fill=tk.X, padx=10, pady=5)

        # 添加设置
        settings_frame = ttk.Frame(action_frame)
        settings_frame.pack(side=tk.LEFT)

        ttk.Label(settings_frame, text="添加间隔(秒):").pack(side=tk.LEFT, padx=5)
        self.interval_var = tk.IntVar(value=ADD_INTERVAL)
        ttk.Spinbox(settings_frame, from_=5, to=60, textvariable=self.interval_var, width=5).pack(side=tk.LEFT, padx=5)

        # 操作按钮
        btn_frame = ttk.Frame(action_frame)
        btn_frame.pack(side=tk.RIGHT)

        self.add_selected_btn = ttk.Button(btn_frame, text="添加选中 (0)", command=self._add_selected, state='disabled')
        self.add_selected_btn.pack(side=tk.LEFT, padx=5)

        self.add_all_btn = ttk.Button(btn_frame, text="添加所有未添加", command=self._add_all_not_added, state='disabled')
        self.add_all_btn.pack(side=tk.LEFT, padx=5)

        self.stop_btn = ttk.Button(btn_frame, text="停止", command=self._stop_add, state='disabled')
        self.stop_btn.pack(side=tk.LEFT, padx=5)

        # 日志区域
        log_frame = ttk.LabelFrame(self.root, text="操作日志", padding=5)
        log_frame.pack(fill=tk.X, padx=10, pady=5, height=100)

        self.log_text = tk.Text(log_frame, height=4, font=('Consolas', 9))
        self.log_text.pack(fill=tk.X, padx=5, pady=5)

        log_scroll = ttk.Scrollbar(log_frame, orient=tk.VERTICAL, command=self.log_text.yview)
        self.log_text.configure(yscrollcommand=log_scroll.set)
        log_scroll.pack(side=tk.RIGHT, fill=tk.Y)

        # 加载已有群列表
        self._load_groups()

    def _log(self, message: str):
        """添加日志"""
        timestamp = datetime.now().strftime("%H:%M:%S")
        self.log_text.insert(tk.END, f"[{timestamp}] {message}\n")
        self.log_text.see(tk.END)
        logger.info(message)

    def _load_groups(self):
        """加载群列表"""
        groups = self.db.get_group_names()
        self.group_combo['values'] = groups
        if groups:
            self.current_group.set(groups[0])
            self._load_members()

    def _update_stats(self):
        """更新统计信息"""
        stats = self.db.get_stats()
        self.today_label.config(text=f"今日添加: {stats['today_add']}/{DAILY_LIMIT}")
        self.total_label.config(
            text=f"总成员: {stats['total_members']} | 已添加: {stats['added_members']} | 未添加: {stats['not_added_members']}"
        )

    def _connect_wechat(self):
        """连接微信"""
        self._log("正在连接微信...")
        if self.wechat.connect():
            self.connection_label.config(text="🟢 已连接", foreground="green")
            self._log("✅ 微信连接成功")
            self.add_all_btn.config(state='normal')
        else:
            self.connection_label.config(text="🔴 连接失败", foreground="red")
            self._log("❌ 微信连接失败，请确保微信已启动")

    def _get_current_chat(self):
        """获取当前聊天"""
        if not self.wechat.is_connected:
            messagebox.showwarning("未连接", "请先连接微信")
            return

        self._log("正在获取当前聊天...")
        chat_name = self.wechat.get_current_chat_name()

        if chat_name:
            self.current_group.set(chat_name)
            self._log(f"✅ 获取到群聊: {chat_name}")

            # 检查是否在列表中
            groups = self.db.get_group_names()
            if chat_name not in groups:
                self._log(f"📋 新群聊，将创建数据记录")

            self._load_members()
        else:
            self._log("⚠️ 未获取到群聊名称")
            messagebox.showinfo("提示", "请确保已打开群聊窗口并点击群名查看群成员")

    def _refresh_members(self):
        """刷新群成员"""
        if not self.current_group.get():
            messagebox.showwarning("未选择群", "请先选择或获取群聊")
            return

        if not self.wechat.is_connected:
            messagebox.showwarning("未连接", "请先连接微信")
            return

        self._log("正在刷新群成员...")

        # 打开群成员列表
        if not self.wechat.open_group_members():
            messagebox.showinfo("提示", "请手动点击群名进入群信息页面")
            return

        # 等待用户操作
        if messagebox.askyesno("确认", "请确保群成员列表已打开，然后点击确定继续"):
            members = self.wechat.get_group_members_list()

            if members:
                group_name = self.current_group.get()
                self.db.clear_group_members(group_name)

                for name, wxid in members:
                    self.db.add_member(group_name, name, wxid)

                self._log(f"✅ 成功获取 {len(members)} 个群成员")
                self._load_members()
                self._update_stats()
            else:
                self._log("⚠️ 未获取到群成员，请确保群成员列表已完全展开")

    def _on_group_selected(self, event=None):
        """群选择改变"""
        self._load_members()

    def _load_members(self):
        """加载成员列表"""
        # 清空表格
        for item in self.tree.get_children():
            self.tree.delete(item)
        self.checkboxes = {}

        group_name = self.current_group.get()
        if not group_name:
            return

        filter_status = self.filter_var.get()
        members = self.db.get_members(group_name, filter_status)

        for member in members:
            member_id = member['id']
            name = member['member_name']
            wxid = member['member_nickname'] or member['member_name']
            is_added = "✓ 已添加" if member['is_added'] else "○ 未添加"
            add_count = member['add_count']
            last_time = member['last_add_time'] or "-"

            # 创建行
            item_id = self.tree.insert('', tk.END, values=('', name, wxid, is_added, add_count, last_time))

            # 为未添加的成员创建复选框
            if not member['is_added']:
                self.checkboxes[item_id] = tk.BooleanVar(value=False)

    def _filter_members(self):
        """筛选成员"""
        self._load_members()

    def _select_all_not_added(self):
        """全选未添加"""
        for item_id, var in self.checkboxes.items():
            var.set(True)
        self._update_selected_count()

    def _deselect_all(self):
        """取消全选"""
        for item_id, var in self.checkboxes.items():
            var.set(False)
        self._update_selected_count()

    def _update_selected_count(self):
        """更新选中数量"""
        selected = sum(1 for var in self.checkboxes.values() if var.get())
        self.add_selected_btn.config(text=f"添加选中 ({selected})")

    def _get_selected_members(self) -> List[tuple]:
        """获取选中的成员"""
        selected = []
        for item_id, var in self.checkboxes.items():
            if var.get():
                values = self.tree.item(item_id)['values']
                member_name = values[1]  # name
                member_wxid = values[2]  # wxid
                selected.append((member_name, member_wxid))
        return selected

    def _add_selected(self):
        """添加选中的成员"""
        members = self._get_selected_members()
        if not members:
            messagebox.showwarning("未选择", "请选择要添加的成员")
            return

        self._start_add(members)

    def _add_all_not_added(self):
        """添加所有未添加的成员"""
        group_name = self.current_group.get()
        if not group_name:
            return

        members = self.db.get_unadded_members(group_name)
        if not members:
            messagebox.showinfo("提示", "所有成员都已添加")
            return

        member_list = [(m['member_name'], m['member_nickname'] or m['member_name']) for m in members]
        self._start_add(member_list)

    def _start_add(self, members: List[tuple]):
        """开始添加"""
        today_count = self.db.get_today_add_count()

        if today_count >= DAILY_LIMIT:
            messagebox.showwarning("已达上限", f"今日添加次数已达 {DAILY_LIMIT} 次上限")
            return

        remaining = DAILY_LIMIT - today_count
        if len(members) > remaining:
            if not messagebox.askyesno("确认",
                                        f"今日还能添加 {remaining} 次，\n"
                                        f"你选择了 {len(members)} 个成员，\n"
                                        f"是否只添加前 {remaining} 个？"):
                return
            members = members[:remaining]

        self.is_running = True
        self.add_selected_btn.config(state='disabled')
        self.add_all_btn.config(state='disabled')
        self.stop_btn.config(state='normal')

        self._log(f"🚀 开始添加 {len(members)} 个成员...")

        # 启动添加线程
        self.add_thread = threading.Thread(target=self._add_worker, args=(members,))
        self.add_thread.daemon = True
        self.add_thread.start()

    def _add_worker(self, members: List[tuple]):
        """添加工作线程"""
        group_name = self.current_group.get()
        interval = self.interval_var.get()
        success_count = 0
        fail_count = 0

        self.wechat.get_wechat_focused()

        for i, (member_name, _) in enumerate(members):
            if not self.is_running:
                self._log("⏹️ 用户停止添加")
                break

            today_count = self.db.get_today_add_count()
            if today_count >= DAILY_LIMIT:
                self._log(f"⚠️ 今日添加次数已达上限 ({DAILY_LIMIT})")
                break

            self._log(f"[{i+1}/{len(members)}] 正在添加: {member_name}...")

            # 执行添加
            success, error = self.wechat.search_and_add(member_name)

            if success:
                self.db.update_member_added(group_name, member_name, True)
                self.db.increment_daily_count(True)
                self.db.record_add_result(member_name, member_name, "success")
                self._log(f"  ✅ 添加成功")
                success_count += 1
            else:
                self.db.record_add_result(member_name, member_name, "failed", error)
                if error != "对方已是好友":
                    self.db.update_member_added(group_name, member_name, False)
                    self.db.increment_daily_count(False)
                    self._log(f"  ❌ 添加失败: {error}")
                else:
                    self._log(f"  ⚠️ {error}")

            # 更新UI
            self.root.after(0, self._update_stats)

            # 等待间隔
            if i < len(members) - 1 and self.is_running:
                self._log(f"  ⏳ 等待 {interval} 秒...")
                time.sleep(interval)

        self.is_running = False
        self.root.after(0, self._on_add_complete, success_count, fail_count)

    def _stop_add(self):
        """停止添加"""
        self.is_running = False
        self._log("⏹️ 正在停止...")

    def _on_add_complete(self, success: int, fail: int):
        """添加完成"""
        self.add_selected_btn.config(state='normal')
        self.add_all_btn.config(state='normal')
        self.stop_btn.config(state='disabled')

        self._log(f"✅ 添加完成: 成功 {success}, 失败 {fail}")
        self._load_members()
        self._update_stats()

        messagebox.showinfo("完成", f"添加完成\n成功: {success}\n失败: {fail}")

    def _on_close(self):
        """关闭窗口"""
        if self.is_running:
            if not messagebox.askyesno("确认", "正在添加中，确定要退出吗？"):
                return

        self.db.close()
        self.root.destroy()


def main():
    """主函数"""
    import time

    root = tk.Tk()

    # 设置样式
    style = ttk.Style()
    try:
        style.theme_use('vista')
    except:
        pass

    app = WeChatAssistantApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
