# WeChat Group Assistant - 微信群助手

半自动化工具，用于统计微信群成员、记录添加历史、辅助添加好友。

## 功能特性

- 自动读取微信群成员列表
- 识别未添加的好友
- 记录添加历史和次数
- 每日添加上限提醒（20次）
- 操作日志追溯

## 技术栈

- Python 3.10+
- uiautomation2 - Windows UI 自动化
- SQLite - 数据存储
- Tkinter - GUI 界面（Python 内置）

## 安装依赖

```bash
pip install uiautomation2 pyinstaller
```

## 运行

```bash
python main.py
```

## 打包为 exe

```bash
pyinstaller --onefile --windowed --name "微信群助手" main.py
```

## 使用说明

1. 确保微信已登录并打开
2. 点击目标群聊进入聊天界面
3. 点击群名称 → 查看群成员
4. 在工具中点击"刷新群成员"
5. 选择未添加的成员，点击"添加选中"

## 注意事项

- 建议设置添加间隔（建议10秒以上）
- 每日添加不要超过20次，避免封号
- 操作时保持微信窗口在前台
