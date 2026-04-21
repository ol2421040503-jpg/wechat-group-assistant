# -*- coding: utf-8 -*-
"""
微信群助手 - 数据库模块
"""

import sqlite3
from datetime import datetime, date
from typing import List, Optional, Tuple
from config import DB_PATH


class Database:
    def __init__(self):
        self.conn = sqlite3.connect(DB_PATH, check_same_thread=False)
        self.conn.row_factory = sqlite3.Row
        self._init_tables()

    def _init_tables(self):
        """初始化数据库表"""
        cursor = self.conn.cursor()

        # 群组成员表
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS group_members (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                group_name TEXT NOT NULL,
                member_name TEXT NOT NULL,
                member_nickname TEXT,
                is_added INTEGER DEFAULT 0,
                add_count INTEGER DEFAULT 0,
                last_add_time TEXT,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(group_name, member_name)
            )
        """)

        # 添加记录表
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS add_records (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                member_name TEXT NOT NULL,
                member_nickname TEXT,
                status TEXT,
                error_msg TEXT,
                add_time TEXT DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # 每日统计表
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS daily_stats (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                stat_date TEXT NOT NULL UNIQUE,
                add_count INTEGER DEFAULT 0,
                success_count INTEGER DEFAULT 0,
                fail_count INTEGER DEFAULT 0
            )
        """)

        self.conn.commit()

    def get_today_add_count(self) -> int:
        """获取今日添加次数"""
        today = date.today().isoformat()
        cursor = self.conn.cursor()
        cursor.execute("SELECT add_count FROM daily_stats WHERE stat_date = ?", (today,))
        row = cursor.fetchone()
        return row['add_count'] if row else 0

    def increment_daily_count(self, success: bool = True):
        """增加今日计数"""
        today = date.today().isoformat()
        cursor = self.conn.cursor()
        cursor.execute("""
            INSERT INTO daily_stats (stat_date, add_count, success_count, fail_count)
            VALUES (?, 1, ?, ?)
            ON CONFLICT(stat_date) DO UPDATE SET
                add_count = add_count + 1,
                success_count = success_count + ?,
                fail_count = fail_count + ?
        """, (today, 1 if success else 0, 0 if success else 1,
              1 if success else 0, 0 if success else 1))
        self.conn.commit()

    def add_member(self, group_name: str, member_name: str, member_nickname: str = None):
        """添加群成员到数据库"""
        cursor = self.conn.cursor()
        cursor.execute("""
            INSERT INTO group_members (group_name, member_name, member_nickname, is_added, add_count)
            VALUES (?, ?, ?, 0, 0)
            ON CONFLICT(group_name, member_name) DO UPDATE SET
                member_nickname = excluded.member_nickname
        """, (group_name, member_name, member_nickname))
        self.conn.commit()

    def update_member_added(self, group_name: str, member_name: str, success: bool = True):
        """更新成员添加状态"""
        cursor = self.conn.cursor()
        now = datetime.now().isoformat()

        if success:
            cursor.execute("""
                UPDATE group_members
                SET is_added = 1, add_count = add_count + 1, last_add_time = ?
                WHERE group_name = ? AND member_name = ?
            """, (now, group_name, member_name))
        else:
            cursor.execute("""
                UPDATE group_members
                SET add_count = add_count + 1, last_add_time = ?
                WHERE group_name = ? AND member_name = ?
            """, (now, group_name, member_name))

        self.conn.commit()

    def get_members(self, group_name: str, filter_status: str = "all") -> List[sqlite3.Row]:
        """获取群成员列表"""
        cursor = self.conn.cursor()

        if filter_status == "not_added":
            cursor.execute("""
                SELECT * FROM group_members
                WHERE group_name = ? AND is_added = 0
                ORDER BY add_count ASC
            """, (group_name,))
        elif filter_status == "added":
            cursor.execute("""
                SELECT * FROM group_members
                WHERE group_name = ? AND is_added = 1
                ORDER BY last_add_time DESC
            """, (group_name,))
        else:
            cursor.execute("""
                SELECT * FROM group_members
                WHERE group_name = ?
                ORDER BY is_added ASC, add_count ASC
            """, (group_name,))

        return cursor.fetchall()

    def get_unadded_members(self, group_name: str) -> List[sqlite3.Row]:
        """获取未添加的成员"""
        return self.get_members(group_name, "not_added")

    def record_add_result(self, member_name: str, member_nickname: str, status: str, error_msg: str = None):
        """记录添加结果"""
        cursor = self.conn.cursor()
        now = datetime.now().isoformat()
        cursor.execute("""
            INSERT INTO add_records (member_name, member_nickname, status, error_msg, add_time)
            VALUES (?, ?, ?, ?, ?)
        """, (member_name, member_nickname, status, error_msg, now))
        self.conn.commit()

    def get_group_names(self) -> List[str]:
        """获取所有群名称"""
        cursor = self.conn.cursor()
        cursor.execute("SELECT DISTINCT group_name FROM group_members ORDER BY group_name")
        return [row['group_name'] for row in cursor.fetchall()]

    def get_stats(self) -> dict:
        """获取统计数据"""
        cursor = self.conn.cursor()
        today = date.today().isoformat()

        # 今日统计
        cursor.execute("SELECT * FROM daily_stats WHERE stat_date = ?", (today,))
        today_stats = cursor.fetchone()

        # 总统计
        cursor.execute("""
            SELECT
                COUNT(*) as total_members,
                SUM(is_added) as added_members,
                SUM(CASE WHEN is_added = 0 THEN 1 ELSE 0 END) as not_added_members,
                SUM(add_count) as total_add_count
            FROM group_members
        """)
        total_stats = cursor.fetchone()

        return {
            "today_add": today_stats['add_count'] if today_stats else 0,
            "today_success": today_stats['success_count'] if today_stats else 0,
            "today_fail": today_stats['fail_count'] if today_stats else 0,
            "total_members": total_stats['total_members'] or 0,
            "added_members": total_stats['added_members'] or 0,
            "not_added_members": total_stats['not_added_members'] or 0,
            "total_add_count": total_stats['total_add_count'] or 0
        }

    def clear_group_members(self, group_name: str):
        """清空群成员（用于刷新）"""
        cursor = self.conn.cursor()
        cursor.execute("DELETE FROM group_members WHERE group_name = ?", (group_name,))
        self.conn.commit()

    def close(self):
        """关闭数据库连接"""
        self.conn.close()
