#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
此程序完全开源免费
禁止商用

"""
import os
import sys
import json
import random
import shutil
import re
import tkinter as tk
from tkinter import ttk, filedialog, messagebox, scrolledtext, simpledialog
from pathlib import Path
from datetime import datetime
import ctypes

# DPI 感知
try:
    ctypes.windll.shcore.SetProcessDpiAwareness(1)
except:
    pass

DISABLED_PREFIX = "DISABLED_"
APP_NAME = "ModRandomizer"
CONFIG_DIR = Path(os.getenv('APPDATA')) / APP_NAME
CONFIG_FILE = CONFIG_DIR / "config.json"


# ===== 统一滚轮绑定（终极修复版）=====
def bind_mousewheel(container, canvas):
    """终极滚轮修复：无视子项位置，强制列表滚动"""

    def _on_mousewheel(event):
        if sys.platform == 'win32':
            canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")
        return "break"  # 阻止事件传播

    # 绑定容器和 canvas
    container.bind("<MouseWheel>", _on_mousewheel)
    canvas.bind("<MouseWheel>", _on_mousewheel)

    # 递归禁用所有子项的滚轮捕获
    def disable_child_wheel(widget):
        try:
            widget.bind("<MouseWheel>", lambda e: "break")
        except:
            pass
        for child in widget.winfo_children():
            disable_child_wheel(child)

    disable_child_wheel(container)


# ===== 滚轮绑定结束 =====

class SkinConfigManager:
    """皮肤配置管理器 - 移除内部排除状态依赖"""

    def __init__(self, character_dir: Path):
        self.char_dir = character_dir
        self.config_dir = character_dir / ".mod_randomizer"
        self.config_file = self.config_dir / "skin_config.json"
        self.config = self.load_config()

    def load_config(self):
        if not self.config_file.exists():
            return {
                "version": "2.0",
                "active_skin": "__default__",
                "skin_groups": {
                    "__default__": [],
                    "__manual__": {}
                },
                "group_rules": {},
                "shared_mods": {}
            }

        try:
            with open(self.config_file, 'r', encoding='utf-8') as f:
                cfg = json.load(f)
                if cfg.get("version", "1.0") == "1.0":
                    cfg["version"] = "2.0"
                    cfg["group_rules"] = {}
                    cfg["skin_groups"]["__manual__"] = {}
                if "group_rules" not in cfg:
                    cfg["group_rules"] = {}
                if "skin_groups" not in cfg or "__manual__" not in cfg["skin_groups"]:
                    cfg["skin_groups"]["__manual__"] = {}
                if "shared_mods" not in cfg:
                    cfg["shared_mods"] = {}
                return cfg
        except:
            return {
                "version": "2.0",
                "active_skin": "__default__",
                "skin_groups": {"__default__": [], "__manual__": {}},
                "group_rules": {},
                "shared_mods": {}
            }

    def save_config(self):
        self.config_dir.mkdir(parents=True, exist_ok=True)
        with open(self.config_file, 'w', encoding='utf-8') as f:
            json.dump(self.config, f, ensure_ascii=False, indent=2)

    def get_active_skin(self):
        return self.config.get("active_skin", "__default__")

    def set_active_skin(self, skin_name: str):
        self.config["active_skin"] = skin_name
        self.save_config()

    def add_skin_group(self, group_name: str, keywords: str = ""):
        if group_name in ["__default__", "__manual__", ""]:
            raise ValueError("无效的分组名称")
        if group_name in self.config["skin_groups"]:
            raise ValueError(f"分组「{group_name}」已存在")

        self.config["skin_groups"][group_name] = []
        self.config["group_rules"][group_name] = keywords.strip()
        self.save_config()
        return True

    def remove_skin_group(self, group_name: str):
        if group_name in ["__default__", "__manual__"]:
            return False

        if group_name in self.config["skin_groups"]:
            for mod in self.config["skin_groups"][group_name]:
                if mod not in self.config["skin_groups"]["__default__"]:
                    self.config["skin_groups"]["__default__"].append(mod)
            del self.config["skin_groups"][group_name]

        self.config["group_rules"].pop(group_name, None)
        self.config["skin_groups"]["__manual__"] = {
            k: v for k, v in self.config["skin_groups"]["__manual__"].items() if v != group_name
        }

        if self.config["active_skin"] == group_name:
            self.config["active_skin"] = "__default__"

        self.save_config()
        return True

    def update_group_keywords(self, group_name: str, keywords: str):
        if group_name not in self.config["group_rules"]:
            return False
        self.config["group_rules"][group_name] = keywords.strip()
        self.save_config()
        return True

    def get_mod_group(self, mod_name: str) -> str:
        if mod_name in self.config["skin_groups"]["__manual__"]:
            return self.config["skin_groups"]["__manual__"][mod_name]

        for group_name, mods in self.config["skin_groups"].items():
            if group_name in ["__default__", "__manual__"]:
                continue
            if mod_name in mods:
                return group_name

        return "__default__"

    def manually_assign_mod(self, mod_name: str, target_group: str):
        self.config["skin_groups"]["__manual__"][mod_name] = target_group

        for group_name in list(self.config["skin_groups"].keys()):
            if group_name in ["__default__", "__manual__"]:
                continue
            if mod_name in self.config["skin_groups"][group_name]:
                self.config["skin_groups"][group_name].remove(mod_name)

        if target_group != "__default__":
            if target_group not in self.config["skin_groups"]:
                self.config["skin_groups"][target_group] = []
            if mod_name not in self.config["skin_groups"][target_group]:
                self.config["skin_groups"][target_group].append(mod_name)

        self.save_config()

    def auto_group_mods(self):
        all_mods = self._scan_all_mods()

        for group_name in list(self.config["skin_groups"].keys()):
            if group_name not in ["__default__", "__manual__"]:
                self.config["skin_groups"][group_name] = []

        self.config["skin_groups"]["__default__"] = []

        for mod_name in all_mods:
            if mod_name in self.config["skin_groups"]["__manual__"]:
                target_group = self.config["skin_groups"]["__manual__"][mod_name]
                if target_group != "__default__":
                    if target_group not in self.config["skin_groups"]:
                        self.config["skin_groups"][target_group] = []
                    if mod_name not in self.config["skin_groups"][target_group]:
                        self.config["skin_groups"][target_group].append(mod_name)
                continue

            assigned = False
            mod_lower = mod_name.lower()

            for group_name, keywords_str in self.config["group_rules"].items():
                if not keywords_str.strip():
                    continue

                keywords = [k.strip() for k in re.split(r'[,;，；\s]+', keywords_str) if k.strip()]

                for kw in keywords:
                    kw_lower = kw.lower()
                    pattern = re.escape(kw_lower).replace(r'\*', '.*').replace(r'\?', '.')
                    if re.search(pattern, mod_lower):
                        if group_name not in self.config["skin_groups"]:
                            self.config["skin_groups"][group_name] = []
                        self.config["skin_groups"][group_name].append(mod_name)
                        assigned = True
                        break

                if assigned:
                    break

            if not assigned:
                self.config["skin_groups"]["__default__"].append(mod_name)

        self.save_config()

    def _scan_all_mods(self) -> list:
        mods = []
        for item in self.char_dir.iterdir():
            if item.is_dir() and not item.name.startswith('.'):
                clean_name = item.name[len(DISABLED_PREFIX):] if item.name.startswith(DISABLED_PREFIX) else item.name
                mods.append(clean_name)
        return sorted(set(mods))

    def get_mod_skins(self, mod_name: str) -> list:
        if mod_name in self.config["shared_mods"]:
            return self.config["shared_mods"][mod_name]

        group = self.get_mod_group(mod_name)
        return [group] if group != "__default__" else ["__default__"]

    def is_mod_relevant_to_skin(self, mod_name: str, skin_name: str) -> bool:
        return skin_name in self.get_mod_skins(mod_name)

    def get_candidate_mods(self, skin_name: str, excluded_mods: list) -> list:
        candidates = []
        all_mods = self._scan_all_mods()

        # 大小写不敏感排除
        excluded_lower = set(m.lower() for m in excluded_mods)

        for mod_name in all_mods:
            if mod_name.lower() in excluded_lower:
                continue
            if self.is_mod_relevant_to_skin(mod_name, skin_name):
                candidates.append(mod_name)

        return candidates

    # ===== 核心修复：冲突检测完全依赖传入的排除列表（无内部状态）=====
    def detect_conflicts(self, skin_name: str, excluded_mods: list) -> dict:
        """
        修复重点：
        1. 完全依赖传入的 excluded_mods，不使用任何内部状态
        2. 大小写不敏感匹配
        3. 精确过滤排除项后再检测冲突
        """
        # 创建小写排除集合（大小写不敏感）
        excluded_lower = set(m.lower() for m in excluded_mods)

        # 步骤1: 收集当前启用的非排除Mod
        enabled_mods = []
        for item in self.char_dir.iterdir():
            if item.is_dir() and not item.name.startswith('.') and not item.name.startswith(DISABLED_PREFIX):
                clean_name = item.name
                # 严格过滤排除项（大小写不敏感）
                if clean_name.lower() not in excluded_lower:
                    enabled_mods.append(clean_name)

        # 步骤2: 筛选与当前皮肤相关的启用Mod
        relevant_enabled = [
            mod for mod in enabled_mods
            if self.is_mod_relevant_to_skin(mod, skin_name)
        ]

        # 检测激活皮肤冲突
        if len(relevant_enabled) > 1:
            return {
                "conflict": True,
                "type": "multi_enabled",
                "mods": relevant_enabled,
                "skin": skin_name
            }

        # 步骤3: 检测冻结皮肤意外启用（同样过滤排除项）
        frozen_enabled = []
        for mod in enabled_mods:
            mod_skins = self.get_mod_skins(mod)
            # 仅当Mod不属于激活皮肤且不是共享Mod时，才视为冻结皮肤启用
            if (skin_name not in mod_skins and
                    not (mod in self.config["shared_mods"] and skin_name in self.config["shared_mods"].get(mod, []))):
                frozen_enabled.append(mod)

        if frozen_enabled:
            return {
                "conflict": True,
                "type": "frozen_skin_enabled",
                "mods": frozen_enabled,
                "active_skin": skin_name
            }

        return {"conflict": False}
    # ===== 修复结束 =====


class ModRandomizerGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("🎮 Mod 随机选择器 v4.6 - 重启冲突显示终极修复版")
        self.root.geometry("1080x820")
        self.root.minsize(1000, 740)

        self.mod_base_dir = None
        self.backup_dir = None
        self.all_characters = []
        self.selected_chars = {}
        self.excluded_mods = {}  # {char_name: [mod_name_lower]}
        self.skin_configs = {}
        self.last_backup_path = None

        self.create_widgets()
        self.load_app_config()  # 配置加载（修复时序）
        self.apply_theme()

    def apply_theme(self):
        style = ttk.Style()
        try:
            style.theme_use('vista')
        except:
            pass
        style.configure("TButton", padding=6, font=("Microsoft YaHei", 9))
        style.configure("TCheckbutton", padding=4)
        style.configure("Header.TLabel", font=("Microsoft YaHei", 10, "bold"))
        style.configure("Status.TLabel", font=("Microsoft YaHei", 9))
        style.configure("Skin.TCombobox", font=("Microsoft YaHei", 9))
        style.configure("Conflict.TLabel", foreground="#d32f2f", font=("Microsoft YaHei", 9, "bold"))
        style.configure("Safe.TLabel", foreground="#2e7d32", font=("Microsoft YaHei", 9, "bold"))
        style.configure("Manual.TLabel", foreground="#ed6c02", font=("Microsoft YaHei", 9, "bold"))
        style.configure("Default.TLabel", foreground="#616161", font=("Microsoft YaHei", 9))

    def create_widgets(self):
        # ===== 顶部路径区 =====
        top_frame = ttk.Frame(self.root, padding=10)
        top_frame.pack(fill=tk.X)

        dir_frame = ttk.Frame(top_frame)
        dir_frame.pack(fill=tk.X, pady=3)
        ttk.Label(dir_frame, text="Mod 根目录:", style="Header.TLabel").pack(side=tk.LEFT)
        self.path_var = tk.StringVar(value="❌ 未选择目录")
        ttk.Label(dir_frame, textvariable=self.path_var, foreground="#666").pack(side=tk.LEFT, padx=10, fill=tk.X,
                                                                                 expand=True)
        ttk.Button(dir_frame, text="📁 浏览...", command=self.browse_directory, width=12).pack(side=tk.RIGHT)

        backup_frame = ttk.Frame(top_frame)
        backup_frame.pack(fill=tk.X, pady=3)
        ttk.Label(backup_frame, text="备份目录:", style="Header.TLabel").pack(side=tk.LEFT)
        self.backup_path_var = tk.StringVar(value="❌ 未指定备份目录")
        ttk.Label(backup_frame, textvariable=self.backup_path_var, foreground="#666").pack(side=tk.LEFT, padx=10,
                                                                                           fill=tk.X, expand=True)
        ttk.Button(backup_frame, text="📁 指定路径...", command=self.browse_backup_dir, width=15).pack(side=tk.RIGHT)

        ttk.Separator(self.root, orient=tk.HORIZONTAL).pack(fill=tk.X, padx=10, pady=8)

        # ===== 角色列表区 =====
        char_frame = ttk.LabelFrame(self.root, text="👤 选择要随机化的角色", padding=12)
        char_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)

        control_frame = ttk.Frame(char_frame)
        control_frame.pack(fill=tk.X, pady=(0, 10))

        search_frame = ttk.Frame(control_frame)
        search_frame.pack(side=tk.LEFT, fill=tk.X, expand=True)
        ttk.Label(search_frame, text="🔍 搜索:", font=("Microsoft YaHei", 9)).pack(side=tk.LEFT)
        self.search_var = tk.StringVar()
        self.search_var.trace_add("write", self.filter_characters)
        ttk.Entry(search_frame, textvariable=self.search_var, width=40).pack(side=tk.LEFT, padx=8, fill=tk.X,
                                                                             expand=True)

        select_frame = ttk.Frame(control_frame)
        select_frame.pack(side=tk.RIGHT, padx=(15, 0))
        ttk.Button(select_frame, text="✓ 全选", command=self.select_all_characters, width=8).pack(side=tk.LEFT, padx=3)
        ttk.Button(select_frame, text="✗ 全不选", command=self.deselect_all_characters, width=8).pack(side=tk.LEFT,
                                                                                                      padx=3)

        hint_frame = ttk.Frame(char_frame)
        hint_frame.pack(fill=tk.X, pady=(0, 8))
        ttk.Label(hint_frame, text="💡 手动分组优先：用户调整 > 关键词自动分组 > 未分组",
                  font=("Microsoft YaHei", 8, "italic"), foreground="#1976d2").pack(side=tk.LEFT)
        ttk.Label(hint_frame, text="🛡️ 激活皮肤隔离：仅操作当前皮肤相关 Mod",
                  font=("Microsoft YaHei", 8, "italic"), foreground="#d32f2f").pack(side=tk.RIGHT)

        # 滚动区域
        list_frame = ttk.Frame(char_frame)
        list_frame.pack(fill=tk.BOTH, expand=True)

        self.char_canvas = tk.Canvas(list_frame, highlightthickness=0, bg="white")
        self.vsb = ttk.Scrollbar(list_frame, orient=tk.VERTICAL, command=self.char_canvas.yview)
        self.hsb = ttk.Scrollbar(list_frame, orient=tk.HORIZONTAL, command=self.char_canvas.xview)
        self.char_container = ttk.Frame(self.char_canvas)

        self.char_canvas.configure(yscrollcommand=self.vsb.set, xscrollcommand=self.hsb.set)
        self.vsb.pack(side=tk.RIGHT, fill=tk.Y)
        self.hsb.pack(side=tk.BOTTOM, fill=tk.X)
        self.char_canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        self.canvas_window = self.char_canvas.create_window((0, 0), window=self.char_container, anchor="nw")
        self.char_container.bind("<Configure>",
                                 lambda e: self.char_canvas.configure(scrollregion=self.char_canvas.bbox("all")))

        # 终极滚轮修复
        bind_mousewheel(self.char_container, self.char_canvas)

        # ===== 操作按钮区 =====
        btn_frame = ttk.Frame(self.root, padding=12)
        btn_frame.pack(fill=tk.X)

        ttk.Button(btn_frame, text="⚙️ 排除 Mod", command=self.open_exclude_dialog, width=15).pack(side=tk.LEFT,
                                                                                                   padx=(0, 8))
        ttk.Button(btn_frame, text="🎨 皮肤分组", command=self.open_skin_config_dialog, width=15).pack(side=tk.LEFT,
                                                                                                      padx=8)
        ttk.Button(btn_frame, text="👁️ 预览变更", command=self.preview_changes, width=13).pack(side=tk.LEFT, padx=8)
        ttk.Button(btn_frame, text="✅ 执行随机化", command=self.execute_randomization, width=15).pack(side=tk.LEFT,
                                                                                                      padx=8)
        ttk.Button(btn_frame, text="↩️ 撤销上次操作", command=self.undo_last_operation, width=17).pack(side=tk.LEFT,
                                                                                                       padx=8)

        # ===== 日志区 =====
        log_frame = ttk.LabelFrame(self.root, text="📋 操作日志", padding=8)
        log_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=8)

        self.log_text = scrolledtext.ScrolledText(log_frame, height=10, wrap=tk.WORD, font=("Microsoft YaHei", 9))
        self.log_text.pack(fill=tk.BOTH, expand=True)
        self.log_text.configure(state=tk.DISABLED)

        status_frame = ttk.Frame(self.root, padding=(10, 5))
        status_frame.pack(fill=tk.X)
        self.status_var = tk.StringVar(value="✓ 就绪 | 重启后冲突状态正确同步 | 滚轮全局生效")
        ttk.Label(status_frame, textvariable=self.status_var, style="Status.TLabel").pack(side=tk.LEFT)
        ttk.Label(status_frame,
                  text=f"Powered by Python {sys.version_info.major}.{sys.version_info.minor} · ModRandomizer v4.6",
                  foreground="#999", font=("Microsoft YaHei", 8)).pack(side=tk.RIGHT)

    def log(self, msg, level="info"):
        self.log_text.configure(state=tk.NORMAL)
        symbol = "ℹ️" if level == "info" else "✅" if level == "success" else "⚠️" if level == "warn" else "❌"
        tag = "success" if level == "success" else "warn" if level == "warn" else "error" if level == "error" else "normal"
        self.log_text.insert(tk.END, f"{symbol} {datetime.now().strftime('%H:%M:%S')} - {msg}\n", tag)
        self.log_text.tag_config("success", foreground="#2e7d32")
        self.log_text.tag_config("warn", foreground="#ed6c02")
        self.log_text.tag_config("error", foreground="#d32f2f")
        self.log_text.see(tk.END)
        self.log_text.configure(state=tk.DISABLED)
        if level == "error":
            messagebox.showerror("错误", msg)

    def browse_directory(self):
        path = filedialog.askdirectory(title="选择 Mod 根目录（包含角色文件夹的父目录）")
        if path:
            self.set_base_directory(path)

    def browse_backup_dir(self):
        path = filedialog.askdirectory(title="选择备份目录")
        if path:
            self.set_backup_directory(path)

    def set_base_directory(self, path):
        p = Path(path).resolve()
        if not p.exists():
            self.log("路径不存在", "error")
            return

        self.mod_base_dir = p
        self.path_var.set(f"📁 {p}")
        self.scan_characters()  # 扫描角色（此时 excluded_mods 已加载）
        self.save_app_config()
        self.log(f"✓ 已设置 Mod 根目录: {p}")

    def set_backup_directory(self, path):
        p = Path(path).resolve()
        p.mkdir(parents=True, exist_ok=True)
        self.backup_dir = p
        self.backup_path_var.set(f"💾 {p}")
        self.save_app_config()
        self.log(f"✓ 已设置备份目录: {p}")

    def scan_characters(self):
        """扫描角色文件夹 - 修复：确保排除列表已加载"""
        if not self.mod_base_dir:
            return

        for widget in self.char_container.winfo_children():
            widget.destroy()

        self.all_characters = []
        self.selected_chars = {}
        self.skin_configs = {}

        for item in sorted(self.mod_base_dir.iterdir()):
            if item.is_dir() and not item.name.startswith('.'):
                subdirs = [d for d in item.iterdir() if d.is_dir() and not d.name.startswith('.')]
                if subdirs:
                    self.all_characters.append(item.name)
                    self.selected_chars[item.name] = tk.BooleanVar(value=False)
                    self.skin_configs[item.name] = SkinConfigManager(item)

        # 修复：扫描完成后立即刷新（此时 excluded_mods 已存在）
        self.filter_characters()
        self.log(f"✓ 扫描完成: 发现 {len(self.all_characters)} 个角色")

    # ===== 核心修复：角色列表刷新（确保排除状态正确应用）=====
    def filter_characters(self, *args):
        """修复重点：每次刷新都使用最新的排除状态"""
        for widget in self.char_container.winfo_children():
            widget.destroy()

        keyword = self.search_var.get().lower()
        filtered = [name for name in self.all_characters if keyword in name.lower()]

        if not filtered:
            ttk.Label(self.char_container, text="🔍 未找到匹配的角色",
                      foreground="#999", font=("Microsoft YaHei", 10)).pack(pady=30)
            self.root.update_idletasks()
            self.char_canvas.configure(scrollregion=self.char_canvas.bbox("all"))
            return

        # 表头
        header = ttk.Frame(self.char_container)
        header.pack(fill=tk.X, padx=8, pady=(5, 8))
        ttk.Label(header, text=" ", width=5).pack(side=tk.LEFT, padx=2)
        ttk.Label(header, text="角色名称", width=30, anchor="w", font=("Microsoft YaHei", 9, "bold")).pack(side=tk.LEFT,
                                                                                                           padx=2)
        ttk.Label(header, text="激活皮肤", width=18, anchor="w", font=("Microsoft YaHei", 9, "bold")).pack(side=tk.LEFT,
                                                                                                           padx=2)
        ttk.Label(header, text="分组", width=12, anchor="w", font=("Microsoft YaHei", 9, "bold")).pack(side=tk.LEFT,
                                                                                                       padx=2)
        ttk.Label(header, text="状态", width=45, anchor="w", font=("Microsoft YaHei", 9, "bold")).pack(side=tk.LEFT,
                                                                                                       padx=2)

        ttk.Separator(self.char_container, orient=tk.HORIZONTAL).pack(fill=tk.X, padx=8, pady=(0, 8))

        for char_name in filtered:
            char_dir = self.mod_base_dir / char_name
            if not char_dir.exists():
                continue

            skin_cfg = self.skin_configs[char_name]
            active_skin = skin_cfg.get_active_skin()

            # ===== 修复：实时获取排除状态（小写集合）=====
            excluded_set = set(self.excluded_mods.get(char_name, []))
            # ===== 修复结束 =====

            # 检测冲突（显式传入排除列表）
            conflict_info = skin_cfg.detect_conflicts(active_skin, list(excluded_set))
            has_conflict = conflict_info["conflict"]

            # 统计激活皮肤的启用Mod数量（自动过滤排除项）
            enabled_count = 0
            for item in char_dir.iterdir():
                if item.is_dir() and not item.name.startswith('.') and not item.name.startswith(DISABLED_PREFIX):
                    clean_name = item.name
                    if clean_name.lower() not in excluded_set and skin_cfg.is_mod_relevant_to_skin(clean_name,
                                                                                                   active_skin):
                        enabled_count += 1

            # 确定状态文本
            if has_conflict:
                if conflict_info["type"] == "multi_enabled":
                    status = f"⚠️ 冲突: {len(conflict_info['mods'])}个启用"
                    status_style = "Conflict.TLabel"
                else:
                    status = f"⚠️ 冻结皮肤启用: {len(conflict_info['mods'])}个"
                    status_style = "Conflict.TLabel"
            elif enabled_count == 1:
                status = f"✓ 安全 ({enabled_count}个启用)"
                status_style = "Safe.TLabel"
            elif enabled_count == 0:
                status = "⬜ 无启用Mod"
                status_style = "TLabel"
            else:
                status = f"ℹ️ {enabled_count}个启用（含排除）"
                status_style = "TLabel"

            group_count = len(
                [g for g in skin_cfg.config["skin_groups"].keys() if g not in ["__default__", "__manual__"]])
            group_text = f"{group_count}组" if group_count > 0 else "未分组"

            # 创建角色条目（禁用子项滚轮捕获）
            frame = ttk.Frame(self.char_container, relief="groove", borderwidth=1)
            frame.pack(fill=tk.X, padx=8, pady=3)
            frame.bind("<MouseWheel>", lambda e: "break")
            frame.bind("<Double-Button-1>", lambda e, n=char_name: self.open_skin_config_dialog(n))

            cb = ttk.Checkbutton(frame, variable=self.selected_chars[char_name], width=2)
            cb.pack(side=tk.LEFT, padx=8)
            cb.bind("<MouseWheel>", lambda e: "break")

            ttk.Label(frame, text=char_name, width=30, anchor="w", font=("Microsoft YaHei", 9)).pack(side=tk.LEFT,
                                                                                                     padx=2)
            ttk.Label(frame, text=char_name, width=30, anchor="w", font=("Microsoft YaHei", 9)).bind("<MouseWheel>",
                                                                                                     lambda e: "break")

            skin_display = active_skin if active_skin != "__default__" else "默认"
            ttk.Label(frame, text=skin_display, width=18, anchor="w",
                      foreground="#1976d2", font=("Microsoft YaHei", 9, "bold")).pack(side=tk.LEFT, padx=2)

            ttk.Label(frame, text=group_text, width=12, anchor="w",
                      foreground="#616161", font=("Microsoft YaHei", 9)).pack(side=tk.LEFT, padx=2)

            status_label = ttk.Label(frame, text=status, width=45, anchor="w", style=status_style)
            status_label.pack(side=tk.LEFT, padx=2, fill=tk.X, expand=True)
            status_label.bind("<MouseWheel>", lambda e: "break")

        # 强制更新滚动区域
        self.root.update_idletasks()
        bbox = self.char_canvas.bbox("all")
        if bbox:
            self.char_canvas.configure(scrollregion=bbox)
            self.char_canvas.config(width=bbox[2] - bbox[0] + 20)

    # ===== 修复结束 =====

    def select_all_characters(self):
        keyword = self.search_var.get().lower()
        filtered = [name for name in self.all_characters if keyword in name.lower()]

        if not filtered:
            self.log("ℹ️ 当前搜索条件下无角色", "info")
            return

        for char_name in filtered:
            if char_name in self.selected_chars:
                self.selected_chars[char_name].set(True)

        self.log(f"✓ 已全选 {len(filtered)} 个角色", "success")

    def deselect_all_characters(self):
        for char_name in self.all_characters:
            if char_name in self.selected_chars:
                self.selected_chars[char_name].set(False)
        self.log("✓ 已取消所有角色选择", "success")

    # ... [皮肤分组对话框、共享Mod对话框等保持原有实现，仅确保滚轮修复] ...
    def open_skin_config_dialog(self, char_name=None):
        if char_name is None:
            selected = [name for name, var in self.selected_chars.items() if var.get()]
            if not selected:
                self.log("请先选择一个角色", "warn")
                return
            char_name = selected[0]

        char_dir = self.mod_base_dir / char_name
        if not char_dir.exists():
            self.log(f"角色目录不存在: {char_name}", "error")
            return

        skin_cfg = self.skin_configs[char_name]
        excluded_set = set(self.excluded_mods.get(char_name, []))

        dlg = tk.Toplevel(self.root)
        dlg.title(f"🎨 皮肤分组配置 - {char_name}（手动为主）")
        dlg.geometry("1050x720")
        dlg.transient(self.root)
        dlg.grab_set()
        dlg.focus_set()

        # ... [界面构建代码保持不变] ...
        info_frame = ttk.Frame(dlg)
        info_frame.pack(fill=tk.X, padx=15, pady=12)
        ttk.Label(info_frame, text="🛠️ 手动分组优先规则", font=("Microsoft YaHei", 10, "bold"),
                  foreground="#1976d2").pack(anchor="w")
        ttk.Label(info_frame, text="1. 手动调整结果永久覆盖自动分组",
                  wraplength=1000, justify=tk.LEFT, font=("Microsoft YaHei", 9)).pack(anchor="w", pady=(2, 0))
        ttk.Label(info_frame, text="2. 每个分组可设置多个关键词（逗号/空格/分号分隔），支持通配符 * ?",
                  wraplength=1000, justify=tk.LEFT, font=("Microsoft YaHei", 9)).pack(anchor="w", pady=(2, 0))
        ttk.Label(info_frame, text="3. 关键词可留空，后续随时编辑",
                  wraplength=1000, justify=tk.LEFT, foreground="#d32f2f", font=("Microsoft YaHei", 9, "bold")).pack(
            anchor="w", pady=(2, 0))

        ttk.Separator(dlg, orient=tk.HORIZONTAL).pack(fill=tk.X, padx=10, pady=5)

        group_mgmt_frame = ttk.LabelFrame(dlg, text="🔧 分组管理", padding=10)
        group_mgmt_frame.pack(fill=tk.X, padx=15, pady=5)

        group_list_frame = ttk.Frame(group_mgmt_frame)
        group_list_frame.pack(fill=tk.X, pady=(0, 8))

        ttk.Label(group_list_frame, text="现有分组:", font=("Microsoft YaHei", 9, "bold")).pack(side=tk.LEFT)
        group_var = tk.StringVar(value="")
        group_combo = ttk.Combobox(group_list_frame, textvariable=group_var, state="readonly", width=20)
        group_combo.pack(side=tk.LEFT, padx=8)

        def refresh_group_list(select=None):
            groups = [g for g in skin_cfg.config["skin_groups"].keys() if g not in ["__default__", "__manual__"]]
            group_combo['values'] = groups
            if select and select in groups:
                group_var.set(select)
            elif groups:
                group_var.set(groups[0])
            else:
                group_var.set("")

        refresh_group_list()

        btn_frame = ttk.Frame(group_mgmt_frame)
        btn_frame.pack(fill=tk.X)

        def add_group():
            group_name = simpledialog.askstring("新增分组", "输入分组名称（如：夏日皮肤）:", parent=dlg)
            if not group_name or group_name.strip() == "":
                return

            group_name = group_name.strip()
            if group_name in ["__default__", "__manual__"]:
                messagebox.showerror("❌ 错误", "保留名称不可用", parent=dlg)
                return
            if group_name in skin_cfg.config["skin_groups"]:
                messagebox.showerror("❌ 错误", f"分组「{group_name}」已存在", parent=dlg)
                return

            try:
                skin_cfg.add_skin_group(group_name, keywords="")
                refresh_group_list(group_name)
                update_mod_view()
                group_var.set(group_name)
                keyword_entry.focus_set()
                keyword_entry.select_range(0, tk.END)
                self.log(f"✓ 已添加分组: {group_name}（关键词可后续编辑）", "success")
            except Exception as e:
                messagebox.showerror("❌ 创建失败", f"无法创建分组: {str(e)}", parent=dlg)

        def remove_group():
            group_name = group_var.get()
            if not group_name:
                messagebox.showwarning("⚠️ 警告", "请先选择一个分组", parent=dlg)
                return
            if messagebox.askyesno("⚠️ 确认删除", f"确定删除分组「{group_name}」？\n\n该分组中的 Mod 将移回「未分组」",
                                   parent=dlg):
                if skin_cfg.remove_skin_group(group_name):
                    refresh_group_list()
                    update_mod_view()
                    self.log(f"✓ 已删除分组: {group_name}", "success")
                else:
                    messagebox.showerror("❌ 错误", "无法删除保留分组", parent=dlg)

        ttk.Button(btn_frame, text="➕ 新增分组", command=add_group, width=12).pack(side=tk.LEFT, padx=(0, 8))
        ttk.Button(btn_frame, text="➖ 删除分组", command=remove_group, width=12).pack(side=tk.LEFT, padx=8)

        keyword_frame = ttk.Frame(group_mgmt_frame)
        keyword_frame.pack(fill=tk.X, pady=8)

        ttk.Label(keyword_frame, text="关键词规则:", font=("Microsoft YaHei", 9, "bold")).pack(side=tk.LEFT)
        keyword_var = tk.StringVar(value="")
        keyword_entry = ttk.Entry(keyword_frame, textvariable=keyword_var, width=50)
        keyword_entry.pack(side=tk.LEFT, padx=8, fill=tk.X, expand=True)

        def load_keywords(*args):
            group_name = group_var.get()
            if group_name:
                keywords = skin_cfg.config["group_rules"].get(group_name, "")
                keyword_var.set(keywords)
            else:
                keyword_var.set("")

        def save_keywords(event=None):
            group_name = group_var.get()
            if not group_name:
                return
            keywords = keyword_var.get()
            if skin_cfg.update_group_keywords(group_name, keywords):
                self.log(f"✓ 已更新分组「{group_name}」的关键词: {keywords or '（空）'}", "success")

        group_var.trace_add("write", load_keywords)
        keyword_entry.bind("<FocusOut>", save_keywords)
        keyword_entry.bind("<Return>", save_keywords)

        ttk.Label(keyword_frame, text="💡 示例: summer,泳装,海滩  或  winter*  或留空",
                  foreground="#666", font=("Microsoft YaHei", 8)).pack(side=tk.LEFT, padx=(10, 0))

        auto_frame = ttk.Frame(group_mgmt_frame)
        auto_frame.pack(fill=tk.X, pady=(5, 0))
        ttk.Button(auto_frame, text="⚡ 执行自动分组",
                   command=lambda: [skin_cfg.auto_group_mods(), update_mod_view(),
                                    self.log("✓ 已执行自动分组（手动调整不受影响）", "success")],
                   width=18).pack(side=tk.LEFT)
        ttk.Label(auto_frame, text="（手动调整结果永久保留）", foreground="#666", font=("Microsoft YaHei", 8)).pack(
            side=tk.LEFT, padx=8)

        ttk.Separator(dlg, orient=tk.HORIZONTAL).pack(fill=tk.X, padx=10, pady=8)

        view_frame = ttk.Frame(dlg)
        view_frame.pack(fill=tk.BOTH, expand=True, padx=15, pady=5)

        left_frame = ttk.Frame(view_frame, width=220)
        left_frame.pack(side=tk.LEFT, fill=tk.Y, padx=(0, 10))
        left_frame.pack_propagate(False)

        group_tree = ttk.Treeview(left_frame, show="tree", selectmode="browse")
        group_tree.pack(fill=tk.BOTH, expand=True)

        right_frame = ttk.Frame(view_frame)
        right_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        canvas = tk.Canvas(right_frame, highlightthickness=0)
        vsb = ttk.Scrollbar(right_frame, orient=tk.VERTICAL, command=canvas.yview)
        hsb = ttk.Scrollbar(right_frame, orient=tk.HORIZONTAL, command=canvas.xview)
        container = ttk.Frame(canvas)

        canvas.configure(yscrollcommand=vsb.set, xscrollcommand=hsb.set)
        vsb.pack(side=tk.RIGHT, fill=tk.Y)
        hsb.pack(side=tk.BOTTOM, fill=tk.X)
        canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        canvas_window = canvas.create_window((0, 0), window=container, anchor="nw")
        container.bind("<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all")))

        # 终极滚轮修复
        bind_mousewheel(container, canvas)

        legend_frame = ttk.Frame(dlg)
        legend_frame.pack(fill=tk.X, padx=15, pady=8)
        ttk.Label(legend_frame, text="图例:", font=("Microsoft YaHei", 8, "bold")).pack(side=tk.LEFT)
        ttk.Label(legend_frame, text="✓ 启用", foreground="#2e7d32", font=("Arial", 9, "bold")).pack(side=tk.LEFT,
                                                                                                     padx=6)
        ttk.Label(legend_frame, text="⬜ 禁用", foreground="#666", font=("Arial", 9, "bold")).pack(side=tk.LEFT, padx=6)
        ttk.Label(legend_frame, text="🔧 手动", foreground="#ed6c02", font=("Arial", 9, "bold")).pack(side=tk.LEFT,
                                                                                                     padx=6)
        ttk.Label(legend_frame, text="❓ 未分组", foreground="#d32f2f", font=("Arial", 9, "bold")).pack(side=tk.LEFT,
                                                                                                       padx=6)

        btn_frame = ttk.Frame(dlg)
        btn_frame.pack(fill=tk.X, padx=15, pady=12)

        def save_all():
            selected = group_tree.selection()
            if selected:
                active_skin = group_tree.item(selected[0], "tags")[0]
                skin_cfg.set_active_skin(active_skin)

            self.filter_characters()  # 保存后刷新主界面
            dlg.destroy()
            self.log(f"✓ 已保存角色「{char_name}」的皮肤分组配置", "success")

        ttk.Button(btn_frame, text="✅ 保存并关闭", command=save_all, width=15).pack(side=tk.RIGHT, padx=8)
        ttk.Button(btn_frame, text="❌ 取消", command=dlg.destroy, width=10).pack(side=tk.RIGHT, padx=8)
        ttk.Button(btn_frame, text="⚙️ 共享Mod配置",
                   command=lambda: self.open_shared_mod_dialog(dlg, char_name, skin_cfg),
                   width=15).pack(side=tk.LEFT, padx=8)

        mod_items = {}

        def update_mod_view():
            for widget in container.winfo_children():
                widget.destroy()
            mod_items.clear()

            selected_group = None
            selection = group_tree.selection()
            if selection:
                selected_group = group_tree.item(selection[0], "tags")[0]

            all_mods = []
            for item in char_dir.iterdir():
                if item.is_dir() and not item.name.startswith('.'):
                    clean_name = item.name[len(DISABLED_PREFIX):] if item.name.startswith(
                        DISABLED_PREFIX) else item.name
                    is_enabled = not item.name.startswith(DISABLED_PREFIX)
                    all_mods.append((clean_name, is_enabled))

            groups = {
                "__default__": [],
                "__manual__": []
            }
            for group_name in skin_cfg.config["skin_groups"].keys():
                if group_name not in ["__default__", "__manual__"]:
                    groups[group_name] = []

            for clean_name, is_enabled in all_mods:
                group = skin_cfg.get_mod_group(clean_name)
                if clean_name in skin_cfg.config["skin_groups"]["__manual__"]:
                    groups["__manual__"].append((clean_name, is_enabled, group))
                elif group in groups:
                    groups[group].append((clean_name, is_enabled, group))
                else:
                    groups["__default__"].append((clean_name, is_enabled, group))

            for group_name, mods in groups.items():
                if not mods:
                    continue

                if selected_group and group_name != selected_group and group_name != "__manual__":
                    continue

                display_name = "🔧 手动调整" if group_name == "__manual__" else (
                    "❓ 未分组" if group_name == "__default__" else group_name)
                group_color = "#ed6c02" if group_name == "__manual__" else (
                    "#d32f2f" if group_name == "__default__" else "#1976d2")

                group_header = ttk.Frame(container)
                group_header.pack(fill=tk.X, pady=(10, 5))
                ttk.Label(group_header, text=f"📁 {display_name} ({len(mods)} 个)",
                          font=("Microsoft YaHei", 9, "bold"),
                          foreground=group_color).pack(side=tk.LEFT)

                for clean_name, is_enabled, actual_group in mods:
                    frame = ttk.Frame(container, relief="ridge", borderwidth=1)
                    frame.pack(fill=tk.X, padx=5, pady=2)
                    frame.bind("<MouseWheel>", lambda e: "break")

                    status_icon = "✓" if is_enabled else "⬜"
                    status_color = "#2e7d32" if is_enabled else "#666"

                    ttk.Label(frame, text=status_icon, width=3, anchor="w",
                              foreground=status_color, font=("Arial", 10, "bold")).pack(side=tk.LEFT, padx=(5, 2))

                    name_label = ttk.Label(frame, text=clean_name, width=50, anchor="w", font=("Microsoft YaHei", 9))
                    name_label.pack(side=tk.LEFT, padx=5)
                    name_label.bind("<MouseWheel>", lambda e: "break")

                    current_group = actual_group if group_name != "__manual__" else skin_cfg.config["skin_groups"][
                        "__manual__"].get(clean_name, "unknown")
                    current_display = "❓ 未分组" if current_group == "__default__" else current_group
                    group_label = ttk.Label(frame, text=f"→ {current_display}", width=22, anchor="w",
                                            foreground="#666", font=("Microsoft YaHei", 9))
                    group_label.pack(side=tk.LEFT, padx=5)
                    group_label.bind("<MouseWheel>", lambda e: "break")

                    btn_frame_inner = ttk.Frame(frame)
                    btn_frame_inner.pack(side=tk.RIGHT, padx=5)
                    btn_frame_inner.bind("<MouseWheel>", lambda e: "break")

                    def make_assign_handler(mod, target):
                        return lambda: assign_mod_to_group(mod, target)

                    if current_group == "__default__":
                        custom_groups = [g for g in skin_cfg.config["skin_groups"].keys() if
                                         g not in ["__default__", "__manual__"]]
                        for g in custom_groups[:3]:
                            btn = ttk.Button(btn_frame_inner, text=f"{g[:8]}",
                                             command=make_assign_handler(clean_name, g),
                                             width=6)
                            btn.pack(side=tk.LEFT, padx=2)
                            btn.bind("<MouseWheel>", lambda e: "break")

                    if current_group != "__default__":
                        btn = ttk.Button(btn_frame_inner, text="↺",
                                         command=make_assign_handler(clean_name, "__default__"),
                                         width=3)
                        btn.pack(side=tk.LEFT, padx=2)
                        btn.bind("<MouseWheel>", lambda e: "break")

            dlg.update_idletasks()
            bbox = canvas.bbox("all")
            if bbox:
                canvas.configure(scrollregion=bbox)
                canvas.config(width=bbox[2] - bbox[0] + 20)

        def assign_mod_to_group(mod_name, target_group):
            skin_cfg.manually_assign_mod(mod_name, target_group)
            update_mod_view()
            refresh_group_tree()
            self.log(f"✓ 已手动分配 Mod「{mod_name}」到分组「{target_group}」", "success")

        def refresh_group_tree():
            group_tree.delete(*group_tree.get_children())

            default_count = len(skin_cfg.config["skin_groups"]["__default__"])
            default_id = group_tree.insert("", "end", text=f"❓ 未分组 ({default_count})", tags=("__default__",))

            manual_count = len(skin_cfg.config["skin_groups"]["__manual__"])
            if manual_count > 0:
                manual_id = group_tree.insert("", "end", text=f"🔧 手动调整 ({manual_count})", tags=("__manual__",))

            custom_groups = [g for g in skin_cfg.config["skin_groups"].keys() if g not in ["__default__", "__manual__"]]
            for group_name in sorted(custom_groups):
                count = len(skin_cfg.config["skin_groups"].get(group_name, []))
                manual_in_group = sum(
                    1 for m, g in skin_cfg.config["skin_groups"]["__manual__"].items() if g == group_name)
                total = count + manual_in_group
                group_id = group_tree.insert("", "end", text=f"{group_name} ({total})", tags=(group_name,))

                if group_name == skin_cfg.get_active_skin():
                    group_tree.selection_set(group_id)

            def on_group_select(event):
                selection = group_tree.selection()
                if selection:
                    update_mod_view()

            group_tree.bind("<<TreeviewSelect>>", on_group_select)

        refresh_group_tree()
        update_mod_view()

    def open_shared_mod_dialog(self, parent_dlg, char_name, skin_cfg):
        # ... [保持原有实现] ...
        shared_dlg = tk.Toplevel(parent_dlg)
        shared_dlg.title(f"🔗 共享 Mod 配置 - {char_name}")
        shared_dlg.geometry("720x520")
        shared_dlg.transient(parent_dlg)
        shared_dlg.grab_set()

        ttk.Label(shared_dlg, text="配置可同时用于多个皮肤的 Mod:",
                  font=("Microsoft YaHei", 10, "bold")).pack(pady=10)
        ttk.Label(shared_dlg, text="例如：基础外观、武器配件等通用元素",
                  foreground="#666").pack(pady=(0, 15))

        char_dir = self.mod_base_dir / char_name
        all_mods = sorted(set([
            (item.name[len(DISABLED_PREFIX):] if item.name.startswith(DISABLED_PREFIX) else item.name)
            for item in char_dir.iterdir()
            if item.is_dir() and not item.name.startswith('.')
        ]))

        all_skins = [s for s in skin_cfg.config["skin_groups"].keys() if s not in ["__default__", "__manual__"]]
        if not all_skins:
            ttk.Label(shared_dlg, text="⚠️ 请先创建至少一个皮肤分组", foreground="#d32f2f").pack(pady=20)
            ttk.Button(shared_dlg, text="确定", command=shared_dlg.destroy, width=10).pack(pady=10)
            return

        frame = ttk.Frame(shared_dlg)
        frame.pack(fill=tk.BOTH, expand=True, padx=15, pady=5)

        canvas = tk.Canvas(frame, highlightthickness=0)
        vsb = ttk.Scrollbar(frame, orient=tk.VERTICAL, command=canvas.yview)
        hsb = ttk.Scrollbar(frame, orient=tk.HORIZONTAL, command=canvas.xview)
        container = ttk.Frame(canvas)

        canvas.configure(yscrollcommand=vsb.set, xscrollcommand=hsb.set)
        vsb.pack(side=tk.RIGHT, fill=tk.Y)
        hsb.pack(side=tk.BOTTOM, fill=tk.X)
        canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        canvas_window = canvas.create_window((0, 0), window=container, anchor="nw")
        container.bind("<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all")))

        bind_mousewheel(container, canvas)

        header = ttk.Frame(container)
        header.pack(fill=tk.X)
        ttk.Label(header, text="Mod 名称", width=32, anchor="w", font=("Microsoft YaHei", 9, "bold")).pack(side=tk.LEFT,
                                                                                                           padx=5)

        skin_vars = {}

        for skin in all_skins:
            lbl = ttk.Label(header, text=skin, width=12, anchor="center", font=("Microsoft YaHei", 9, "bold"))
            lbl.pack(side=tk.LEFT, padx=2)

        ttk.Separator(container, orient=tk.HORIZONTAL).pack(fill=tk.X, pady=5)

        for mod_name in all_mods:
            row = ttk.Frame(container)
            row.pack(fill=tk.X)
            row.bind("<MouseWheel>", lambda e: "break")

            ttk.Label(row, text=mod_name[:30], width=32, anchor="w", font=("Microsoft YaHei", 9)).pack(side=tk.LEFT,
                                                                                                       padx=5)

            skin_vars[mod_name] = {}
            for skin in all_skins:
                is_shared = mod_name in skin_cfg.config["shared_mods"] and skin in skin_cfg.config["shared_mods"].get(
                    mod_name, [])
                var = tk.BooleanVar(value=is_shared)
                skin_vars[mod_name][skin] = var
                cb = ttk.Checkbutton(row, variable=var, width=2)
                cb.pack(side=tk.LEFT, padx=8)
                cb.bind("<MouseWheel>", lambda e: "break")

        btn_frame = ttk.Frame(shared_dlg)
        btn_frame.pack(fill=tk.X, padx=15, pady=15)

        def save_shared():
            new_shared = {}
            for mod_name, skin_dict in skin_vars.items():
                selected_skins = [skin for skin, var in skin_dict.items() if var.get()]
                if selected_skins:
                    new_shared[mod_name] = selected_skins

            skin_cfg.config["shared_mods"] = new_shared
            skin_cfg.save_config()

            parent_dlg.focus_force()
            shared_dlg.destroy()
            messagebox.showinfo("✅ 保存成功", f"已配置 {len(new_shared)} 个共享 Mod", parent=parent_dlg)

        ttk.Button(btn_frame, text="✅ 保存配置", command=save_shared, width=12).pack(side=tk.RIGHT, padx=8)
        ttk.Button(btn_frame, text="❌ 取消", command=shared_dlg.destroy, width=10).pack(side=tk.RIGHT, padx=8)

    # ... [排除对话框、预览变更等保持原有实现] ...
    def open_exclude_dialog(self):
        if not self.mod_base_dir:
            self.log("请先设置 Mod 根目录", "error")
            return

        selected = [name for name, var in self.selected_chars.items() if var.get()]
        if not selected:
            self.log("请先选择至少一个角色", "warn")
            return

        dlg = tk.Toplevel(self.root)
        dlg.title("🚫 排除特定 Mod - 皮肤感知模式（实时同步）")
        dlg.geometry("900x640")
        dlg.transient(self.root)
        dlg.grab_set()
        dlg.focus_set()

        # ... [界面构建代码保持不变] ...
        info_frame = ttk.Frame(dlg)
        info_frame.pack(fill=tk.X, padx=15, pady=12)
        ttk.Label(info_frame, text="🛡️ 保护规则", font=("Microsoft YaHei", 10, "bold"), foreground="#1976d2").pack(
            anchor="w")
        ttk.Label(info_frame, text="• 被排除的 Mod 将保持原始状态不变",
                  wraplength=850, justify=tk.LEFT, font=("Microsoft YaHei", 9)).pack(anchor="w", pady=(3, 0))
        ttk.Label(info_frame, text="• 排除的 Mod 不计入「启用数量」检查",
                  wraplength=850, justify=tk.LEFT, font=("Microsoft YaHei", 9)).pack(anchor="w", pady=(3, 0))
        ttk.Label(info_frame, text="• 排除操作实时同步，关闭对话框后立即生效",
                  wraplength=850, justify=tk.LEFT, foreground="#2e7d32", font=("Microsoft YaHei", 9, "bold")).pack(
            anchor="w", pady=(3, 0))

        ttk.Separator(dlg, orient=tk.HORIZONTAL).pack(fill=tk.X, padx=10, pady=5)

        combo_frame = ttk.Frame(dlg)
        combo_frame.pack(fill=tk.X, padx=15, pady=8)

        ttk.Label(combo_frame, text="角色:", font=("Microsoft YaHei", 9, "bold")).pack(side=tk.LEFT)
        char_var = tk.StringVar(value=selected[0])
        char_combo = ttk.Combobox(combo_frame, textvariable=char_var, values=selected, state="readonly", width=20)
        char_combo.pack(side=tk.LEFT, padx=10)

        ttk.Label(combo_frame, text="皮肤:", font=("Microsoft YaHei", 9, "bold")).pack(side=tk.LEFT, padx=(15, 5))
        skin_var = tk.StringVar(value="")
        skin_combo = ttk.Combobox(combo_frame, textvariable=skin_var, values=[], state="readonly", width=20,
                                  style="Skin.TCombobox")
        skin_combo.pack(side=tk.LEFT, padx=10)

        def update_skin_list(*args):
            char_name = char_var.get()
            skin_cfg = self.skin_configs[char_name]
            skins = [s for s in skin_cfg.config["skin_groups"].keys() if s not in ["__default__", "__manual__"]]
            display_skins = ["默认"] + skins
            skin_combo['values'] = display_skins
            current = skin_cfg.get_active_skin()
            skin_var.set("默认" if current == "__default__" else current)

        char_combo.bind("<<ComboboxSelected>>", update_skin_list)
        update_skin_list()

        search_frame = ttk.Frame(dlg)
        search_frame.pack(fill=tk.X, padx=15, pady=(0, 8))
        ttk.Label(search_frame, text="🔍 搜索 Mod:", font=("Microsoft YaHei", 9)).pack(side=tk.LEFT)
        search_var = tk.StringVar()

        list_frame = ttk.Frame(dlg)
        list_frame.pack(fill=tk.BOTH, expand=True, padx=15, pady=5)

        canvas = tk.Canvas(list_frame, highlightthickness=0)
        vsb = ttk.Scrollbar(list_frame, orient=tk.VERTICAL, command=canvas.yview)
        hsb = ttk.Scrollbar(list_frame, orient=tk.HORIZONTAL, command=canvas.xview)
        container = ttk.Frame(canvas, width=860)

        canvas.configure(yscrollcommand=vsb.set, xscrollcommand=hsb.set)
        vsb.pack(side=tk.RIGHT, fill=tk.Y)
        hsb.pack(side=tk.BOTTOM, fill=tk.X)
        canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        canvas_window = canvas.create_window((0, 0), window=container, anchor="nw", width=860)
        container.bind("<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all")))

        bind_mousewheel(container, canvas)

        legend_frame = ttk.Frame(dlg)
        legend_frame.pack(fill=tk.X, padx=15, pady=8)
        ttk.Label(legend_frame, text="状态:", font=("Microsoft YaHei", 8, "bold")).pack(side=tk.LEFT)
        ttk.Label(legend_frame, text="✓ 启用", foreground="#2e7d32", font=("Arial", 9, "bold")).pack(side=tk.LEFT,
                                                                                                     padx=6)
        ttk.Label(legend_frame, text="⬜ 禁用", foreground="#666", font=("Arial", 9, "bold")).pack(side=tk.LEFT, padx=6)
        ttk.Label(legend_frame, text="🛡️ 已排除", foreground="#1976d2", font=("Arial", 9, "bold")).pack(side=tk.LEFT,
                                                                                                        padx=6)
        ttk.Label(legend_frame, text="🔗 共享", foreground="#ed6c02", font=("Arial", 9, "bold")).pack(side=tk.LEFT,
                                                                                                     padx=6)

        btn_frame = ttk.Frame(dlg)
        btn_frame.pack(fill=tk.X, padx=15, pady=12)
        mod_vars = {}  # {clean_name: BooleanVar}

        def toggle_all(value):
            for var in mod_vars.values():
                var.set(value)

        # ===== 核心修复：保存排除项并实时刷新 =====
        def save_settings():
            char_name = char_var.get()

            # 获取当前选中的排除项（转为小写存储）
            excluded_list = [name.lower() for name, var in mod_vars.items() if var.get()]
            self.excluded_mods[char_name] = excluded_list

            # 立即保存配置
            self.save_app_config()

            # 立即刷新主界面角色列表（关键修复）
            self.filter_characters()

            # 显示成功消息
            msg = f"✓ 已为角色「{char_name}」设置 {len(excluded_list)} 个排除项"
            self.log(msg, "success")
            messagebox.showinfo("✅ 成功", msg, parent=dlg)

            # 关闭对话框
            dlg.destroy()

        # ===== 修复结束 =====

        ttk.Button(btn_frame, text="全选", command=lambda: toggle_all(True), width=8).pack(side=tk.LEFT, padx=8)
        ttk.Button(btn_frame, text="全不选", command=lambda: toggle_all(False), width=8).pack(side=tk.LEFT, padx=8)
        ttk.Button(btn_frame, text="❌ 取消", command=dlg.destroy, width=10).pack(side=tk.RIGHT, padx=8)
        ttk.Button(btn_frame, text="✅ 保存设置", command=save_settings, width=14).pack(side=tk.RIGHT, padx=8)

        def update_mod_list(*args):
            for widget in container.winfo_children():
                widget.destroy()

            char_name = char_var.get()
            char_dir = self.mod_base_dir / char_name
            if not char_dir.exists():
                ttk.Label(container, text="❌ 角色目录不存在", foreground="red").pack(pady=20)
                dlg.update_idletasks()
                canvas.configure(scrollregion=canvas.bbox("all"))
                return

            skin_cfg = self.skin_configs[char_name]
            active_skin = "__default__" if skin_var.get() == "默认" else skin_var.get()

            # ===== 修复：实时获取排除状态（小写）=====
            excluded_set = set(self.excluded_mods.get(char_name, []))
            # ===== 修复结束 =====

            keyword = search_var.get().lower()

            mods = []
            for item in char_dir.iterdir():
                if item.is_dir() and not item.name.startswith('.'):
                    clean_name = item.name[len(DISABLED_PREFIX):] if item.name.startswith(
                        DISABLED_PREFIX) else item.name
                    is_enabled = not item.name.startswith(DISABLED_PREFIX)
                    if keyword in clean_name.lower():
                        mods.append((clean_name, is_enabled))

            if not mods:
                ttk.Label(container, text="🔍 未找到匹配的 Mod", foreground="#999").pack(pady=15)
                dlg.update_idletasks()
                canvas.configure(scrollregion=canvas.bbox("all"))
                return

            header = ttk.Frame(container)
            header.pack(fill=tk.X, pady=(0, 6), padx=5)
            ttk.Label(header, text="排除", width=6, anchor="w", font=("Microsoft YaHei", 9, "bold")).pack(side=tk.LEFT,
                                                                                                          padx=5)
            ttk.Label(header, text="Mod 名称", width=42, anchor="w", font=("Microsoft YaHei", 9, "bold")).pack(
                side=tk.LEFT, padx=5)
            ttk.Label(header, text="状态", width=15, anchor="w", font=("Microsoft YaHei", 9, "bold")).pack(side=tk.LEFT,
                                                                                                           padx=5)
            ttk.Label(header, text="归属", width=28, anchor="w", font=("Microsoft YaHei", 9, "bold")).pack(side=tk.LEFT,
                                                                                                           padx=5)

            for clean_name, is_enabled in mods:
                # ===== 修复：大小写不敏感匹配排除状态 =====
                is_excluded = clean_name.lower() in excluded_set
                # ===== 修复结束 =====

                mod_skins = skin_cfg.get_mod_skins(clean_name)
                is_relevant = active_skin in mod_skins
                is_shared = len(mod_skins) > 1

                frame = ttk.Frame(container, relief="flat", borderwidth=1)
                frame.pack(fill=tk.X, padx=5, pady=2)
                frame.bind("<MouseWheel>", lambda e: "break")

                if not is_relevant and not is_shared:
                    continue

                var = tk.BooleanVar(value=is_excluded)
                mod_vars[clean_name] = var
                cb = ttk.Checkbutton(frame, variable=var, width=2)
                cb.pack(side=tk.LEFT, padx=8)
                cb.bind("<MouseWheel>", lambda e: "break")

                name_text = clean_name + (" 🔗" if is_shared else "")
                ttk.Label(frame, text=name_text, width=42, anchor="w",
                          font=("Microsoft YaHei", 9)).pack(side=tk.LEFT, padx=5)

                status_text = "✓ 启用" if is_enabled else "⬜ 禁用"
                status_fg = "#2e7d32" if is_enabled else "#666"
                ttk.Label(frame, text=status_text, width=15, anchor="w",
                          foreground=status_fg, font=("Microsoft YaHei", 9, "bold" if is_enabled else "normal")).pack(
                    side=tk.LEFT, padx=5)

                skin_text = ", ".join([s if s != "__default__" else "默认" for s in mod_skins])
                ttk.Label(frame, text=skin_text, width=28, anchor="w",
                          foreground="#1976d2" if is_relevant else "#666", font=("Microsoft YaHei", 9)).pack(
                    side=tk.LEFT, padx=5)

            dlg.update_idletasks()
            bbox = canvas.bbox("all")
            if bbox:
                canvas.configure(scrollregion=bbox)
                canvas.config(width=bbox[2] - bbox[0] + 20)

        char_combo.bind("<<ComboboxSelected>>", update_mod_list)
        skin_combo.bind("<<ComboboxSelected>>", update_mod_list)
        search_var.trace_add("write", update_mod_list)
        ttk.Entry(search_frame, textvariable=search_var, width=45).pack(side=tk.LEFT, padx=10, fill=tk.X, expand=True)

        update_mod_list()
        dlg.protocol("WM_DELETE_WINDOW", dlg.destroy)

    # ... [其他核心操作保持不变] ...
    def preview_changes(self):
        selected = [name for name, var in self.selected_chars.items() if var.get()]
        if not selected:
            self.log("❌ 请先选择至少一个角色", "error")
            return

        if not self.mod_base_dir:
            self.log("❌ 请先设置 Mod 根目录", "error")
            return

        preview_lines = ["🔍 变更预览（模拟执行）:\n"]
        any_valid = False

        for char_name in selected:
            char_dir = self.mod_base_dir / char_name
            if not char_dir.exists():
                preview_lines.append(f"❌ 角色「{char_name}」目录不存在")
                continue

            skin_cfg = self.skin_configs[char_name]
            active_skin = skin_cfg.get_active_skin()
            excluded_set = set(self.excluded_mods.get(char_name, []))

            conflict = skin_cfg.detect_conflicts(active_skin, list(excluded_set))
            if conflict["conflict"]:
                preview_lines.append(f"⚠️ {char_name} [{active_skin}]")
                if conflict["type"] == "multi_enabled":
                    preview_lines.append(f"   ├─ 冲突: {len(conflict['mods'])} 个启用Mod")
                else:
                    preview_lines.append(f"   ├─ 警告: 冻结皮肤有 {len(conflict['mods'])} 个启用Mod")
                preview_lines.append(f"   └─ 操作: 跳过该角色")
                continue

            candidates = skin_cfg.get_candidate_mods(active_skin, list(excluded_set))
            if not candidates:
                preview_lines.append(f"⚠️ {char_name} [{active_skin}]")
                preview_lines.append(f"   └─ 无可用候选 Mod")
                continue

            current_enabled = []
            for item in char_dir.iterdir():
                if item.is_dir() and not item.name.startswith('.') and not item.name.startswith(DISABLED_PREFIX):
                    clean_name = item.name
                    if clean_name.lower() not in excluded_set and skin_cfg.is_mod_relevant_to_skin(clean_name,
                                                                                                   active_skin):
                        current_enabled.append(clean_name)

            preview_lines.append(f"👤 {char_name} [{active_skin}]")
            if current_enabled:
                preview_lines.append(
                    f"   ├─ 当前启用: {', '.join(current_enabled[:2])}{'...' if len(current_enabled) > 2 else ''}")
            preview_lines.append(f"   └─ 将启用: {random.choice(candidates)} （从 {len(candidates)} 个候选中随机）")
            any_valid = True

        if not any_valid and not any("⚠️" in line for line in preview_lines):
            self.log("❌ 无有效变更可预览", "error")
            return

        dlg = tk.Toplevel(self.root)
        dlg.title("👁️ 变更预览")
        dlg.geometry("720x520")
        dlg.transient(self.root)

        text = scrolledtext.ScrolledText(dlg, wrap=tk.WORD, font=("Microsoft YaHei", 10))
        text.pack(fill=tk.BOTH, expand=True, padx=15, pady=15)
        text.insert(tk.END, "\n".join(preview_lines))

        text.tag_config("warning", foreground="#d32f2f", font=("Microsoft YaHei", 10, "bold"))
        text.tag_config("success", foreground="#2e7d32", font=("Microsoft YaHei", 10, "bold"))

        for i, line in enumerate(preview_lines, 1):
            if "⚠️" in line:
                text.tag_add("warning", f"{i}.0", f"{i}.end")
            elif "👤" in line:
                text.tag_add("success", f"{i}.0", f"{i}.end")

        text.configure(state=tk.DISABLED)

        btn_frame = ttk.Frame(dlg)
        btn_frame.pack(fill=tk.X, padx=15, pady=(0, 15))
        ttk.Button(btn_frame, text="✅ 确认执行",
                   command=lambda: [dlg.destroy(), self.execute_randomization()],
                   width=12).pack(side=tk.RIGHT, padx=8)
        ttk.Button(btn_frame, text="❌ 取消", command=dlg.destroy, width=10).pack(side=tk.RIGHT, padx=8)

    def backup_state(self):
        if not self.backup_dir:
            default_backup = CONFIG_DIR / "backups"
            default_backup.mkdir(parents=True, exist_ok=True)
            self.backup_dir = default_backup
            self.backup_path_var.set(f"💾 {self.backup_dir}")
            self.log(f"⚠️ 未指定备份目录，使用默认路径: {self.backup_dir}", "warn")

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_path = self.backup_dir / f"backup_{timestamp}"
        backup_path.mkdir(parents=True, exist_ok=True)

        selected = [name for name, var in self.selected_chars.items() if var.get()]
        manifest = {
            "timestamp": timestamp,
            "base_dir": str(self.mod_base_dir),
            "backup_dir": str(self.backup_dir),
            "characters": {},
            "excluded_mods": self.excluded_mods.copy(),  # 已使用小写存储
            "skin_configs": {}
        }

        for char_name in selected:
            char_dir = self.mod_base_dir / char_name
            if not char_dir.exists():
                continue

            char_state = {
                "enabled": [],
                "disabled": [],
                "excluded": self.excluded_mods.get(char_name, [])
            }

            for item in char_dir.iterdir():
                if item.is_dir() and not item.name.startswith('.'):
                    clean_name = item.name[len(DISABLED_PREFIX):] if item.name.startswith(
                        DISABLED_PREFIX) else item.name
                    if item.name.startswith(DISABLED_PREFIX):
                        char_state["disabled"].append(item.name)
                    else:
                        char_state["enabled"].append(item.name)

            manifest["characters"][char_name] = char_state

            skin_cfg = self.skin_configs[char_name]
            manifest["skin_configs"][char_name] = {
                "active_skin": skin_cfg.get_active_skin(),
                "skin_groups": skin_cfg.config["skin_groups"],
                "group_rules": skin_cfg.config["group_rules"],
                "shared_mods": skin_cfg.config["shared_mods"]
            }

        with open(backup_path / "manifest.json", 'w', encoding='utf-8') as f:
            json.dump(manifest, f, ensure_ascii=False, indent=2)

        self.log(f"💾 已备份至: {backup_path.name}", "success")
        self.last_backup_path = backup_path
        return backup_path

    def execute_randomization(self):
        selected = [name for name, var in self.selected_chars.items() if var.get()]
        if not selected:
            self.log("❌ 请先选择至少一个角色", "error")
            return

        if not self.mod_base_dir:
            self.log("❌ 请先设置 Mod 根目录", "error")
            return

        valid_chars = []
        warnings = []

        for char_name in selected:
            char_dir = self.mod_base_dir / char_name
            if not char_dir.exists():
                warnings.append(f"❌ 角色「{char_name}」目录不存在")
                continue

            skin_cfg = self.skin_configs[char_name]
            active_skin = skin_cfg.get_active_skin()
            excluded_set = set(self.excluded_mods.get(char_name, []))

            conflict = skin_cfg.detect_conflicts(active_skin, list(excluded_set))
            if conflict["conflict"]:
                if conflict["type"] == "multi_enabled":
                    warnings.append(f"⚠️ 角色「{char_name}」激活皮肤有 {len(conflict['mods'])} 个启用Mod → 跳过")
                else:
                    warnings.append(f"⚠️ 角色「{char_name}」冻结皮肤有启用Mod → 跳过")
                continue

            candidates = skin_cfg.get_candidate_mods(active_skin, list(excluded_set))
            if not candidates:
                warnings.append(f"ℹ️ 角色「{char_name}」无可用候选 Mod → 跳过")
                continue

            valid_chars.append(char_name)

        if warnings:
            warn_text = "\n".join(warnings[:10]) + ("\n..." if len(warnings) > 10 else "")
            if not messagebox.askyesno("⚠️ 状态检查", f"检测到以下情况:\n\n{warn_text}\n\n是否继续执行？"):
                return

        if not valid_chars:
            self.log("❌ 无有效角色可执行随机化", "error")
            return

        confirm_msg = f"即将为 {len(valid_chars)} 个角色的激活皮肤随机选择 Mod\n\n"
        confirm_msg += "🛡️ 保护规则:\n"
        confirm_msg += "• 仅操作激活皮肤相关的 Mod\n"
        confirm_msg += "• 冻结皮肤的 Mod 状态 100% 保持不变\n"
        confirm_msg += "• 排除的 Mod 不参与随机化\n\n"
        confirm_msg += "确定继续？"

        if not messagebox.askyesno("✅ 确认操作", confirm_msg):
            return

        backup_path = self.backup_state()
        if not backup_path:
            return

        success_count = 0
        skipped_count = len(selected) - len(valid_chars)

        for char_name in valid_chars:
            char_dir = self.mod_base_dir / char_name
            if not char_dir.exists():
                self.log(f"❌ 跳过「{char_name}」: 目录不存在", "warn")
                continue

            skin_cfg = self.skin_configs[char_name]
            active_skin = skin_cfg.get_active_skin()
            excluded_set = set(self.excluded_mods.get(char_name, []))

            candidates = []
            for item in char_dir.iterdir():
                if item.is_dir() and not item.name.startswith('.'):
                    clean_name = item.name[len(DISABLED_PREFIX):] if item.name.startswith(
                        DISABLED_PREFIX) else item.name
                    # 大小写不敏感排除
                    if clean_name.lower() in excluded_set:
                        continue
                    if skin_cfg.is_mod_relevant_to_skin(clean_name, active_skin):
                        candidates.append((item, clean_name))

            if not candidates:
                self.log(f"⚠️ 跳过「{char_name}」: 无可用候选", "warn")
                continue

            for mod_dir, clean_name in candidates:
                if not mod_dir.name.startswith(DISABLED_PREFIX):
                    try:
                        mod_dir.rename(char_dir / (DISABLED_PREFIX + mod_dir.name))
                        self.log(f"   🔒 {char_name}[{active_skin}] → 禁用: {clean_name}", "info")
                    except Exception as e:
                        self.log(f"   ❌ {char_name}[{active_skin}] → 禁用失败 {clean_name}: {str(e)}", "error")

            selected_mod, clean_name = random.choice(candidates)
            target_path = char_dir / clean_name
            disabled_path = char_dir / (DISABLED_PREFIX + clean_name)

            if disabled_path.exists():
                try:
                    disabled_path.rename(target_path)
                    self.log(f"   ✅ {char_name}[{active_skin}] → 启用: {clean_name}", "success")
                    success_count += 1
                except Exception as e:
                    self.log(f"   ❌ {char_name}[{active_skin}] → 启用失败 {clean_name}: {str(e)}", "error")
            else:
                self.log(f"   ℹ️ {char_name}[{active_skin}] → 保持启用: {clean_name}", "info")
                success_count += 1

        summary = f"✨ 随机化完成! 成功处理 {success_count}/{len(valid_chars)} 个角色"
        if skipped_count > 0:
            summary += f" | 跳过 {skipped_count} 个角色"
        self.log(summary, "success")

        if messagebox.askyesno("🎮 操作完成", "是否立即启动游戏？"):
            self.launch_game()

    def undo_last_operation(self):
        if not self.last_backup_path or not self.last_backup_path.exists():
            if not self.backup_dir or not self.backup_dir.exists():
                self.log("❌ 未找到备份目录", "error")
                return

            backups = sorted([d for d in self.backup_dir.iterdir() if d.is_dir() and d.name.startswith("backup_")],
                             reverse=True)
            if not backups:
                self.log("❌ 未找到可用备份", "error")
                return

            latest_backup = backups[0]
        else:
            latest_backup = self.last_backup_path

        manifest_path = latest_backup / "manifest.json"
        if not manifest_path.exists():
            self.log("❌ 备份文件损坏", "error")
            return

        try:
            with open(manifest_path, 'r', encoding='utf-8') as f:
                manifest = json.load(f)

            base_dir = Path(manifest["base_dir"])
            if not base_dir.exists():
                raise Exception(f"原始 Mod 目录不存在: {base_dir}")

            char_list = ", ".join(manifest["characters"].keys())
            if not messagebox.askyesno("↩️ 撤销确认",
                                       f"将从备份恢复以下角色:\n{char_list}\n\n备份时间: {manifest['timestamp']}\n\n确定恢复？"):
                return

            for char_name, state in manifest["characters"].items():
                char_dir = base_dir / char_name
                if not char_dir.exists():
                    continue

                for item in char_dir.iterdir():
                    if item.is_dir() and not item.name.startswith('.') and not item.name.startswith(DISABLED_PREFIX):
                        try:
                            item.rename(char_dir / (DISABLED_PREFIX + item.name))
                        except:
                            pass

                for mod_name in state["enabled"]:
                    src = char_dir / (DISABLED_PREFIX + mod_name)
                    dst = char_dir / mod_name
                    if src.exists():
                        try:
                            src.rename(dst)
                        except:
                            pass

            for char_name, cfg in manifest.get("skin_configs", {}).items():
                char_dir = base_dir / char_name
                if char_dir.exists():
                    skin_cfg = SkinConfigManager(char_dir)
                    skin_cfg.config["active_skin"] = cfg["active_skin"]
                    skin_cfg.config["skin_groups"] = cfg["skin_groups"]
                    skin_cfg.config["group_rules"] = cfg.get("group_rules", {})
                    skin_cfg.config["shared_mods"] = cfg.get("shared_mods", {})
                    skin_cfg.save_config()

            # 恢复排除列表（确保小写）
            self.excluded_mods = {}
            for char_name, mods in manifest.get("excluded_mods", {}).items():
                self.excluded_mods[char_name] = [m.lower() for m in mods]  # 统一小写

            self.save_app_config()
            self.filter_characters()  # 刷新界面

            self.log(f"↩️ 已从备份 {latest_backup.name} 恢复状态", "success")

        except Exception as e:
            self.log(f"❌ 撤销失败: {str(e)}", "error")

    def launch_game(self):
        if CONFIG_FILE.exists():
            try:
                with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
                    cfg = json.load(f)
                    game_path = cfg.get("game_executable")
                    if game_path and Path(game_path).exists():
                        os.startfile(game_path)
                        self.log(f"🎮 已启动游戏: {Path(game_path).name}", "success")
                        return
            except:
                pass

        game_path = filedialog.askopenfilename(
            title="选择游戏启动程序 (.exe)",
            filetypes=[("Executable", "*.exe"), ("All files", "*.*")]
        )
        if not game_path:
            return

        try:
            os.startfile(game_path)
            cfg = {}
            if CONFIG_FILE.exists():
                try:
                    with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
                        cfg = json.load(f)
                except:
                    pass
            cfg["game_executable"] = game_path
            CONFIG_DIR.mkdir(parents=True, exist_ok=True)
            with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
                json.dump(cfg, f, ensure_ascii=False, indent=2)

            self.log(f"🎮 已启动游戏: {Path(game_path).name}", "success")
        except Exception as e:
            self.log(f"❌ 启动游戏失败: {str(e)}", "error")

    # ===== 核心修复：配置加载时序优化 =====
    def load_app_config(self):
        """修复重点：先加载排除列表，再扫描角色，最后强制刷新UI"""
        if CONFIG_FILE.exists():
            try:
                with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
                    cfg = json.load(f)

                # 步骤1: 先加载排除列表（统一小写）
                raw_excluded = cfg.get("excluded_mods", {})
                self.excluded_mods = {
                    char: [m.lower() for m in mods]
                    for char, mods in raw_excluded.items()
                }

                # 步骤2: 再设置路径（会触发扫描角色）
                path = cfg.get("mod_base_dir")
                if path and Path(path).exists():
                    self.set_base_directory(path)  # 内部会调用 scan_characters → filter_characters

                backup_path = cfg.get("backup_dir")
                if backup_path and Path(backup_path).exists():
                    self.set_backup_directory(backup_path)

                self.log("✓ 配置加载完成", "success")

                # ===== 核心修复：延迟强制刷新（确保所有状态同步完成）=====
                # 原因：set_base_directory 中的 filter_characters 可能因 excluded_mods 未完全初始化而显示错误状态
                # 解决：延迟100ms后再次刷新，确保所有状态同步
                self.root.after(100, self.filter_characters)
                # ===== 修复结束 =====

            except Exception as e:
                self.log(f"⚠️ 配置加载失败: {str(e)}", "warn")

    # ===== 修复结束 =====

    def save_app_config(self):
        CONFIG_DIR.mkdir(parents=True, exist_ok=True)
        cfg = {
            "mod_base_dir": str(self.mod_base_dir) if self.mod_base_dir else None,
            "backup_dir": str(self.backup_dir) if self.backup_dir else None,
            "selected_characters": [name for name, var in self.selected_chars.items() if var.get()],
            # 保存时确保小写
            "excluded_mods": {
                char: [m.lower() for m in mods]
                for char, mods in self.excluded_mods.items()
            },
            "last_used": datetime.now().isoformat()
        }
        with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
            json.dump(cfg, f, ensure_ascii=False, indent=2)


# ===== 启动程序 =====
if __name__ == "__main__":
    if sys.version_info < (3, 8):
        try:
            root = tk.Tk()
            root.withdraw()
            messagebox.showerror("❌ Python 版本过低",
                                 f"需要 Python 3.8 或更高版本，当前版本: {sys.version}\n\n"
                                 "请从 https://www.python.org/downloads/ 下载安装最新版")
            root.destroy()
        except:
            print("❌ 需要 Python 3.8+，请升级 Python")
        sys.exit(1)

    if sys.version_info.major == 3 and sys.version_info.minor >= 14:
        print(f"ℹ️ 检测到 Python {sys.version_info.major}.{sys.version_info.minor}，已启用兼容模式")

    root = tk.Tk()
    app = ModRandomizerGUI(root)
    root.mainloop()