# -*- coding: utf-8 -*-
"""
微信助手 - 数据库模块
使用 SQLite 存储群成员信息和添加历史
"""

import sqlite3
import logging
from datetime import datetime, date
from typing import List, Optional, Dict

from config import DATABASE_PATH

logger = logging.getLogger(__name__)


class Database:
    def __init__(self, db_path: str = DATABASE_PATH):
        self.db_path = db_path
        self.conn = None
        self._connect()
        self._create_tables()

    def _connect(self):
        """连接数据库"""
        try:
            self.conn = sqlite3.connect(self.db_path, check_same_thread=False)
            self.conn.row_factory = sqlite3.Row
            logger.info(f"数据库连接成功: {self.db_path}")
        except Exception as e:
            logger.error(f"数据库连接失败: {e}")
            raise

    def _create_tables(self):
        """创建表"""
        cursor = self.conn.cursor()

        # 群信息表
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS `groups` (
                `id` INTEGER PRIMARY KEY AUTOINCREMENT,
                `group_name` TEXT UNIQUE NOT NULL,
                `created_at` TEXT DEFAULT CURRENT_TIMESTAMP,
                `updated_at` TEXT DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # 群成员表
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS `members` (
                `id` INTEGER PRIMARY KEY AUTOINCREMENT,
                `group_id` INTEGER NOT NULL,
                `member_name` TEXT NOT NULL,
                `member_nickname` TEXT,
                `member_wxid` TEXT,
                `is_added` INTEGER DEFAULT 0,
                `add_count` INTEGER DEFAULT 0,
                `last_add_time` TEXT,
                `created_at` TEXT DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (`group_id`) REFERENCES `groups`(`id`)
            )
        """)

        # 添加历史表
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS `add_history` (
                `id` INTEGER PRIMARY KEY AUTOINCREMENT,
                `member_name` TEXT NOT NULL,
                `member_wxid` TEXT,
                `result` TEXT NOT NULL,
                `error_message` TEXT,
                `created_at` TEXT DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # 每日统计表
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS `daily_stats` (
                `id` INTEGER PRIMARY KEY AUTOINCREMENT,
                `date` TEXT UNIQUE NOT NULL,
                `add_count` INTEGER DEFAULT 0,
                `success_count` INTEGER DEFAULT 0,
                `fail_count` INTEGER DEFAULT 0,
                `updated_at` TEXT DEFAULT CURRENT_TIMESTAMP
            )
        """)

        self.conn.commit()
        logger.info("数据库表创建成功")

    def add_group(self, group_name: str) -> int:
        """添加群"""
        cursor = self.conn.cursor()
        try:
            cursor.execute(
                "INSERT OR IGNORE INTO `groups` (`group_name`) VALUES (?)",
                (group_name,)
            )
            self.conn.commit()
            cursor.execute("SELECT `id` FROM `groups` WHERE `group_name` = ?", (group_name,))
            result = cursor.fetchone()
            return result['id'] if result else None
        except Exception as e:
            logger.error(f"添加群失败: {e}")
            return None

    def get_group_id(self, group_name: str) -> Optional[int]:
        """获取群ID"""
        cursor = self.conn.cursor()
        cursor.execute("SELECT `id` FROM `groups` WHERE `group_name` = ?", (group_name,))
        result = cursor.fetchone()
        return result['id'] if result else None

    def get_group_names(self) -> List[str]:
        """获取所有群名称"""
        cursor = self.conn.cursor()
        cursor.execute("SELECT `group_name` FROM `groups` ORDER BY `updated_at` DESC")
        return [row['group_name'] for row in cursor.fetchall()]

    def add_member(self, group_name: str, member_name: str, wxid: str = None) -> bool:
        """添加成员"""
        group_id = self.get_group_id(group_name)
        if not group_id:
            group_id = self.add_group(group_name)

        cursor = self.conn.cursor()
        try:
            cursor.execute("""
                INSERT INTO `members` (`group_id`, `member_name`, `member_nickname`, `member_wxid`)
                VALUES (?, ?, ?, ?)
            """, (group_id, member_name, member_name, wxid))
            self.conn.commit()

            # 更新群更新时间
            cursor.execute(
                "UPDATE `groups` SET `updated_at` = CURRENT_TIMESTAMP WHERE `id` = ?",
                (group_id,)
            )
            self.conn.commit()
            return True
        except Exception as e:
            logger.error(f"添加成员失败: {e}")
            return False

    def clear_group_members(self, group_name: str):
        """清空群成员"""
        group_id = self.get_group_id(group_name)
        if not group_id:
            return

        cursor = self.conn.cursor()
        cursor.execute("DELETE FROM `members` WHERE `group_id` = ?", (group_id,))
        self.conn.commit()

    def get_members(self, group_name: str, filter_status: str = "all") -> List[Dict]:
        """获取群成员"""
        group_id = self.get_group_id(group_name)
        if not group_id:
            return []

        cursor = self.conn.cursor()

        if filter_status == "added":
            cursor.execute("""
                SELECT * FROM `members` WHERE `group_id` = ? AND `is_added` = 1
                ORDER BY `member_name`
            """, (group_id,))
        elif filter_status == "not_added":
            cursor.execute("""
                SELECT * FROM `members` WHERE `group_id` = ? AND `is_added` = 0
                ORDER BY `member_name`
            """, (group_id,))
        else:
            cursor.execute("""
                SELECT * FROM `members` WHERE `group_id` = ?
                ORDER BY `is_added`, `member_name`
            """, (group_id,))

        return [dict(row) for row in cursor.fetchall()]

    def get_unadded_members(self, group_name: str) -> List[Dict]:
        """获取未添加的成员"""
        group_id = self.get_group_id(group_name)
        if not group_id:
            return []

        cursor = self.conn.cursor()
        cursor.execute("""
            SELECT * FROM `members` WHERE `group_id` = ? AND `is_added` = 0
            ORDER BY `add_count`, `last_add_time`
        """, (group_id,))

        return [dict(row) for row in cursor.fetchall()]

    def update_member_added(self, group_name: str, member_name: str, is_added: bool):
        """更新成员添加状态"""
        group_id = self.get_group_id(group_name)
        if not group_id:
            return

        cursor = self.conn.cursor()
        cursor.execute("""
            UPDATE `members`
            SET `is_added` = ?, `last_add_time` = CURRENT_TIMESTAMP, `add_count` = `add_count` + 1
            WHERE `group_id` = ? AND (`member_name` = ? OR `member_nickname` = ?)
        """, (1 if is_added else 0, group_id, member_name, member_name))
        self.conn.commit()

    def record_add_result(self, member_name: str, wxid: str, result: str, error: str = None):
        """记录添加结果"""
        cursor = self.conn.cursor()
        cursor.execute("""
            INSERT INTO `add_history` (`member_name`, `member_wxid`, `result`, `error_message`)
            VALUES (?, ?, ?, ?)
        """, (member_name, wxid, result, error))
        self.conn.commit()

    def increment_daily_count(self, success: bool):
        """增加每日统计"""
        today = date.today().isoformat()
        cursor = self.conn.cursor()

        cursor.execute("""
            INSERT INTO `daily_stats` (`date`, `add_count`, `success_count`, `fail_count`)
            VALUES (?, 1, ?, ?)
            ON CONFLICT(`date`) DO UPDATE SET
                `add_count` = `add_count` + 1,
                `success_count` = `success_count` + ?,
                `fail_count` = `fail_count` + ?,
                `updated_at` = CURRENT_TIMESTAMP
        """, (today, 1 if success else 0, 0 if success else 1, 1 if success else 0, 0 if success else 1))

        self.conn.commit()

    def get_today_add_count(self) -> int:
        """获取今日添加次数"""
        today = date.today().isoformat()
        cursor = self.conn.cursor()
        cursor.execute("SELECT `add_count` FROM `daily_stats` WHERE `date` = ?", (today,))
        result = cursor.fetchone()
        return result['add_count'] if result else 0

    def get_stats(self) -> Dict:
        """获取统计信息"""
        cursor = self.conn.cursor()

        # 总成员数
        cursor.execute("SELECT COUNT(*) as count FROM `members`")
        total_members = cursor.fetchone()['count']

        # 已添加
        cursor.execute("SELECT COUNT(*) as count FROM `members` WHERE `is_added` = 1")
        added_members = cursor.fetchone()['count']

        # 今日添加
        today_count = self.get_today_add_count()

        return {
            'total_members': total_members,
            'added_members': added_members,
            'not_added_members': total_members - added_members,
            'today_add': today_count
        }

    def close(self):
        """关闭数据库连接"""
        if self.conn:
            self.conn.close()
            logger.info("数据库连接已关闭")


if __name__ == "__main__":
    # 测试数据库
    db = Database()
    print("数据库测试:")
    print(f"  群列表: {db.get_group_names()}")
    print(f"  统计: {db.get_stats()}")
    db.close()
