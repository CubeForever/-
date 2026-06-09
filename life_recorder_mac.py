#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
生命记录仪 — 桌面挂件版 · macOS 适配版
实时年龄、生命倒计时，常驻桌面角落。
"""

import tkinter as tk
from tkinter import ttk, messagebox
from datetime import datetime, timedelta
import platform

# ======================== 常量 ========================
SEC_PER_YEAR = 31556952
SEC_PER_DAY  = 86400
BPM          = 70
MEALS        = 3

W = 380
H = 500

# macOS 字体
FONT_CN = 'PingFang SC'      # macOS 中文字体
FONT_MONO = 'Menlo'          # macOS 等宽字体

# macOS 窗口整体透明度（0.0=全透明 1.0=不透明）
WINDOW_ALPHA = 0.88

# ======================== 主题色板（4套）======================
THEMES = {
    '极光': {
        'page': '#0E1230', 'card': '#141A3A', 'border': '#448AFF',
        'text': '#FFFFFF', 'text_sec': '#9DA3C9', 'text_dim': '#5A6090',
        'entry_bg': '#0D1328', 'entry_border': '#303F9F',
        'age': '#00E5FF', 'pct': '#00E676',
        'age_cycle': True, 'dark': True,
        'btn': '#238636', 'btn_hover': '#2EA043',
        'stat_colors': ['#00E676', '#FF9100', '#FF1744', '#D500F9'],
    },
    '霓虹': {
        'page': '#110025', 'card': '#1A0033', 'border': '#E040FB',
        'text': '#FFFFFF', 'text_sec': '#CE93D8', 'text_dim': '#7B1FA2',
        'entry_bg': '#0D001A', 'entry_border': '#7C4DFF',
        'age': '#FF00E5', 'pct': '#00E5FF',
        'age_cycle': True, 'dark': True,
        'btn': '#D500F9', 'btn_hover': '#E040FB',
        'stat_colors': ['#00E5FF', '#FFEA00', '#FF4081', '#76FF03'],
    },
    '樱花': {
        'page': '#FFF5F8', 'card': '#FFFFFF', 'border': '#F48FB1',
        'text': '#4A1A2C', 'text_sec': '#AD1457', 'text_dim': '#E91E63',
        'entry_bg': '#FCE4EC', 'entry_border': '#F48FB1',
        'age': '#E91E63', 'pct': '#C62828',
        'age_cycle': False, 'dark': False,
        'btn': '#EC407A', 'btn_hover': '#F06292',
        'stat_colors': ['#E91E63', '#FF8A65', '#AB47BC', '#26A69A'],
    },
    '海洋': {
        'page': '#0C1A2E', 'card': '#122039', 'border': '#4FC3F7',
        'text': '#E0F7FA', 'text_sec': '#80DEEA', 'text_dim': '#4DD0E1',
        'entry_bg': '#0A1628', 'entry_border': '#1565C0',
        'age': '#4FC3F7', 'pct': '#4FC3F7',
        'age_cycle': False, 'dark': True,
        'btn': '#00897B', 'btn_hover': '#009688',
        'stat_colors': ['#4FC3F7', '#FF8A65', '#FFD54F', '#CE93D8'],
    },
}
DEFAULT_THEME = '极光'


def _get_page_bg(theme_name):
    """获取主题的页面背景色"""
    return THEMES.get(theme_name, THEMES[DEFAULT_THEME])['page']


# ======================== 主类 ========================
class LifeRecorder:
    """生命记录仪 — macOS 桌面挂件（多主题）"""

    def __init__(self, root):
        self.root = root
        self.root.title("生命记录仪")

        # 窗口属性
        self.root.overrideredirect(True)
        self.root.attributes('-topmost', True)
        self.root.configure(bg=_get_page_bg(DEFAULT_THEME))

        # === macOS 半透明引擎 ===
        try:
            self.root.attributes('-alpha', WINDOW_ALPHA)
        except Exception:
            pass

        self.root.update_idletasks()
        sw = self.root.winfo_screenwidth()
        self.root.geometry(f"{W}x{H}+{sw - W - 20}+50")

        # 状态
        self._update_id = None
        self._age_cycle = 0
        self._drag_x = 0
        self._drag_y = 0
        self._stat_labels = {}
        self._birth_dt = None
        self._life_exp = 80
        self._death_dt = None
        self._total_love = 5
        self._done_love = 0

        # 输入变量
        self.birth_year   = tk.StringVar(value="1990")
        self.birth_month  = tk.StringVar(value="1")
        self.birth_day    = tk.StringVar(value="1")
        self.birth_hour   = tk.StringVar(value="0")
        self.birth_min    = tk.StringVar(value="0")
        self.birth_sec    = tk.StringVar(value="0")
        var = self.life_exp_var = tk.StringVar(value="80")
        self.exp_love_var = tk.StringVar(value="5")
        self.done_love_var = tk.StringVar(value="0")

        # ---------- 主题系统 ----------
        self._current_theme = DEFAULT_THEME
        # role -> [widget1, widget2, ...]
        self._tw = {}
        def tw_setdefault(role):
            if role not in self._tw:
                self._tw[role] = []
        self._tw_setdefault = tw_setdefault

        # 鼠标事件
        self.root.bind('<Button-1>', self._start_drag)
        self.root.bind('<B1-Motion>', self._do_drag)
        self.root.bind('<Button-3>', self._show_menu)
        self.root.bind('<Button-2>', self._show_menu)  # macOS 备选右键

        # 构建 UI
        self._style = ttk.Style()
        self._style.theme_use('clam')
        pg = _get_page_bg(DEFAULT_THEME)
        self._style.configure('TLabel', background=pg, foreground='white')
        self._style.configure('TFrame', background=pg)
        self._build_input()
        self._build_display()

        # 右键菜单（需在 UI 构建完毕后再建，因为依赖 _apply_theme）
        self._menu = tk.Menu(root, tearoff=0, font=(FONT_CN, 10))
        theme_menu = tk.Menu(self._menu, tearoff=0,
                             font=(FONT_CN, 10))
        for tn in THEMES:
            theme_menu.add_command(
                label=f"{'✓ ' if tn == self._current_theme else '  '}{tn}",
                command=lambda n=tn: self._set_theme(n))
        self._menu.add_cascade(label="🎨 切换主题", menu=theme_menu)
        self._menu.add_separator()
        self._menu.add_command(label="⟳ 重新设置", command=self._reset)
        self._menu.add_separator()
        self._menu.add_command(label="✕ 退出", command=self._on_close)

        # 应用默认主题
        self._apply_theme(DEFAULT_THEME)
        self.input_frame.pack(fill=tk.BOTH, expand=True)

    # ==================== 主题引擎 ====================

    def _tag(self, role, w):
        """为换肤记录 widget 引用"""
        self._tw_setdefault(role)
        self._tw[role].append(w)

    def _tag_card(self, body, gf):
        """标记卡片 body 与 grid 子容器"""
        self._tag('card_bg', body)
        self._tag('card_bg', gf)

    def _apply_theme(self, name):
        """应用主题——更新所有 widget 颜色"""
        T = THEMES.get(name, THEMES[DEFAULT_THEME])
        self._current_theme = name
        page_bg = T['page']

        # ---- 页面背景 ----
        self.root.configure(bg=page_bg)
        for w in self._tw.get('page_bg', []):
            if w.winfo_exists():
                w.configure(bg=page_bg)

        # ---- 标题 / 副标题（浮于页面背景） ----
        for w in self._tw.get('title', []):
            if w.winfo_exists():
                w.configure(bg=page_bg, fg=T['age'])
        for w in self._tw.get('subtitle', []):
            if w.winfo_exists():
                w.configure(bg=page_bg, fg=T['text_dim'])

        # ---- 卡片背景 + 边框 ----
        for w in self._tw.get('card_bg', []):
            if w.winfo_exists():
                w.configure(bg=T['card'],
                           highlightbackground=T['border'])

        # ---- 卡片标题/正文标签 ----
        for w in self._tw.get('card_label', []):
            if w.winfo_exists():
                w.configure(bg=T['card'], fg=T['text_sec'])
        for w in self._tw.get('card_title', []):
            if w.winfo_exists():
                w.configure(bg=T['card'], fg=T['text_dim'])

        # ---- 静默文字 ----
        for w in self._tw.get('muted', []):
            if w.winfo_exists():
                w.configure(bg=T['card'], fg=T['text_dim'])

        # ---- 年龄 ----
        for w in self._tw.get('age', []):
            if w.winfo_exists():
                w.configure(bg=T['card'], fg=T['age'])

        # ---- 进度文字 ----
        for w in self._tw.get('pct', []):
            if w.winfo_exists():
                w.configure(bg=T['card'], fg=T['pct'])

        # ---- 统计行标签（stat_name、stat_unit、stat_val）----
        names = ['周末', '饭量', '心跳', '恋爱']
        keys = ['weekend', 'meal', 'heart', 'love']
        for idx, key in enumerate(keys):
            # 统计名标签
            for w in self._tw.get(f'stat_n_{key}', []):
                if w.winfo_exists():
                    w.configure(bg=T['card'], fg=T['stat_colors'][idx])
            # 统计值标签
            for w in self._tw.get(f'stat_v_{key}', []):
                if w.winfo_exists():
                    w.configure(bg=T['card'], fg=T['text'])
            # 单位标签
            for w in self._tw.get(f'stat_u_{key}', []):
                if w.winfo_exists():
                    w.configure(bg=T['card'], fg=T['text_dim'])
            # emoji 背景
            for w in self._tw.get(f'stat_e_{key}', []):
                if w.winfo_exists():
                    w.configure(bg=T['card'])

        # ---- 输入框 ----
        for w in self._tw.get('entry', []):
            if w.winfo_exists():
                w.configure(bg=T['entry_bg'],
                           highlightbackground=T['entry_border'])

        # ---- 开始按钮 ----
        for w in self._tw.get('start_btn', []):
            if w.winfo_exists():
                w.configure(bg=T['btn'], fg='white',
                           activebackground=T['btn_hover'])

        # ---- 更新右键菜单勾选 ----
        self._menu.delete(0, 'end')
        theme_menu = tk.Menu(self._menu, tearoff=0,
                             font=(FONT_CN, 10))
        for tn in THEMES:
            theme_menu.add_command(
                label=f"{'✓ ' if tn == name else '  '}{tn}",
                command=lambda n=tn: self._set_theme(n))
        self._menu.add_cascade(label="🎨 切换主题", menu=theme_menu)
        self._menu.add_separator()
        self._menu.add_command(label="⟳ 重新设置", command=self._reset)
        self._menu.add_separator()
        self._menu.add_command(label="✕ 退出", command=self._on_close)

    def _set_theme(self, name):
        """切换主题（保留当前界面状态）"""
        if name == self._current_theme:
            return
        is_display = (hasattr(self, 'display_frame') and
                      self.display_frame.winfo_ismapped())
        # 保存 tick 状态
        was_ticking = self._update_id is not None
        if was_ticking and self._update_id:
            self.root.after_cancel(self._update_id)
            self._update_id = None

        self._apply_theme(name)

        # 恢复显示
        if is_display:
            self.display_frame.pack(fill=tk.BOTH, expand=True)
            if was_ticking:
                self._tick()
        else:
            self.input_frame.pack(fill=tk.BOTH, expand=True)

    # ==================== 窗口交互 ====================

    def _start_drag(self, event):
        self._drag_x = event.x
        self._drag_y = event.y

    def _do_drag(self, event):
        x = self.root.winfo_x() + event.x - self._drag_x
        y = self.root.winfo_y() + event.y - self._drag_y
        self.root.geometry(f"+{x}+{y}")

    def _show_menu(self, event):
        self._menu.post(event.x_root, event.y_root)

    # ==================== 输入界面 ====================

    def _card(self, parent, title, icon=''):
        """带边框的卡片，返回 grid 子容器"""
        T = THEMES[self._current_theme]
        outer = tk.Frame(parent, bg=T['page'])
        outer.pack(fill=tk.X, pady=(0, 8))
        self._tag('page_bg', outer)
        body = tk.Frame(outer, bg=T['card'],
                        highlightbackground=T['border'],
                        highlightthickness=1, padx=10, pady=8)
        body.pack(fill=tk.X)
        self._tag('card_bg', body)
        lbl = tk.Label(body, text=f"{icon} {title}" if icon else title,
                       font=(FONT_CN, 10, 'bold'),
                       bg=T['card'], fg=T['text_dim'])
        lbl.pack(anchor=tk.W, pady=(0, 6))
        self._tag('card_title', lbl)
        gf = tk.Frame(body, bg=T['card'])
        gf.pack(fill=tk.X)
        self._tag('card_bg', gf)
        return gf

    def _mk_entry(self, parent, label, var, width, **gk):
        """一行 label + 暗色 Entry"""
        T = THEMES[self._current_theme]
        lbl = tk.Label(parent, text=label,
                       font=(FONT_CN, 10),
                       bg=T['card'], fg=T['text_sec'])
        lbl.grid(**gk, sticky=tk.W)
        self._tag('card_label', lbl)
        ent = tk.Entry(parent, textvariable=var, width=width,
                       font=(FONT_CN, 10),
                       bg=T['entry_bg'], fg='white',
                       relief=tk.FLAT,
                       highlightbackground=T['entry_border'],
                       highlightthickness=1, bd=0)
        ent.grid(row=gk['row'], column=gk['column'] + 1,
                 padx=(4, 0), pady=2, sticky=tk.W)
        self._tag('entry', ent)

    def _build_input(self):
        T = THEMES[self._current_theme]
        page_bg = T['page']
        f = self.input_frame = tk.Frame(self.root, bg=page_bg,
                                        padx=10, pady=10)
        self._tag('page_bg', f)

        # 标题
        lbl1 = tk.Label(f, text="🧬 生命记录仪",
                        font=(FONT_CN, 16, 'bold'),
                        bg=page_bg, fg=T['age'])
        lbl1.pack(pady=(0, 2))
        self._tag('page_bg', lbl1)
        self._tag('title', lbl1)

        lbl2 = tk.Label(f, text="桌面挂件 · macOS 适配版",
                        font=(FONT_CN, 9),
                        bg=page_bg, fg=T['text_dim'])
        lbl2.pack(pady=(0, 10))
        self._tag('page_bg', lbl2)
        self._tag('subtitle', lbl2)

        # 出生时刻
        bf = self._card(f, "出生时刻", '⏱')
        self._mk_entry(bf, '年', self.birth_year, 6,
                       row=0, column=0)
        self._mk_entry(bf, '月', self.birth_month, 4,
                       row=0, column=2, padx=(8, 0))
        self._mk_entry(bf, '日', self.birth_day, 4,
                       row=0, column=4, padx=(8, 0))
        self._mk_entry(bf, '时', self.birth_hour, 4,
                       row=1, column=0)
        self._mk_entry(bf, '分', self.birth_min, 4,
                       row=1, column=2, padx=(8, 0))
        self._mk_entry(bf, '秒', self.birth_sec, 4,
                       row=1, column=4, padx=(8, 0))

        # 人生参数
        sf = self._card(f, "人生参数", '⚡')
        rows = [('预期寿命（岁）', self.life_exp_var),
                ('期望恋爱总次数', self.exp_love_var),
                ('已恋爱次数', self.done_love_var)]
        for i, (lb, vr) in enumerate(rows):
            lbl = tk.Label(sf, text=lb,
                           font=(FONT_CN, 10),
                           bg=T['card'], fg=T['text_sec'])
            lbl.grid(row=i, column=0, sticky=tk.W, pady=3)
            self._tag('card_label', lbl)
            ent = tk.Entry(sf, textvariable=vr, width=6,
                           font=(FONT_CN, 10),
                           bg=T['entry_bg'], fg='white',
                           relief=tk.FLAT,
                           highlightbackground=T['entry_border'],
                           highlightthickness=1, bd=0)
            ent.grid(row=i, column=1, sticky=tk.W, padx=(6, 0), pady=3)
            self._tag('entry', ent)

        # 开始按钮
        bf2 = tk.Frame(f, bg=page_bg)
        bf2.pack(pady=(8, 0))
        self._tag('page_bg', bf2)
        self.start_btn = tk.Button(
            bf2, text="✦ 开始我的生命记录 ✦",
            command=self._start,
            font=(FONT_CN, 11, 'bold'),
            bg=T['btn'], fg='white',
            activebackground=T['btn_hover'], activeforeground='white',
            relief=tk.FLAT, padx=20, pady=6,
            border=0, highlightthickness=0)
        self.start_btn.pack()
        self._tag('start_btn', self.start_btn)

    # ==================== 实时显示界面 ====================

    def _build_display(self):
        T = THEMES[self._current_theme]
        page_bg = T['page']
        f = self.display_frame = tk.Frame(self.root, bg=page_bg,
                                          padx=10, pady=10)
        self._tag('page_bg', f)

        # ---- 年龄卡片 ----
        ac = tk.Frame(f, bg=T['card'],
                      highlightbackground=T['border'],
                      highlightthickness=1, padx=10, pady=8)
        ac.pack(pady=(0, 6), fill=tk.X)
        self._tag('card_bg', ac)
        ml = tk.Label(ac, text="— 当前年龄 —",
                      font=(FONT_CN, 9),
                      bg=T['card'], fg=T['text_dim'])
        ml.pack()
        self._tag('muted', ml)
        self.age_label = tk.Label(ac, text="-- 岁",
                                  font=(FONT_CN, 24, 'bold'),
                                  bg=T['card'], fg=T['age'])
        self.age_label.pack(pady=(2, 0))
        self._tag('age', self.age_label)

        # ---- 进度条 ----
        pc = tk.Frame(f, bg=T['card'],
                      highlightbackground=T['border'],
                      highlightthickness=1, padx=10, pady=6)
        pc.pack(pady=(0, 6), fill=tk.X)
        self._tag('card_bg', pc)
        self.progress = ttk.Progressbar(pc, length=330, mode='determinate')
        self.progress.pack(pady=(2, 3))
        self.progress_label = tk.Label(pc, text="生命进度  0.00%",
                                       font=(FONT_CN, 9),
                                       bg=T['card'], fg=T['pct'])
        self.progress_label.pack()
        self._tag('pct', self.progress_label)

        # ---- 剩余统计 ----
        sc = tk.Frame(f, bg=T['card'],
                      highlightbackground=T['border'],
                      highlightthickness=1, padx=10, pady=6)
        sc.pack(pady=(0, 6), fill=tk.X)
        self._tag('card_bg', sc)
        sh = tk.Label(sc, text="📊 剩余统计",
                      font=(FONT_CN, 10, 'bold'),
                      bg=T['card'], fg=T['text_dim'])
        sh.pack(anchor=tk.W, pady=(0, 4))
        self._tag('card_title', sh)

        # 4 行统计
        stat_info = [
            ('weekend', '🏖', '周末', '天', '#00E676'),
            ('meal',    '🍚', '饭量', '顿', '#FF9100'),
            ('heart',   '💓', '心跳', '次', '#FF1744'),
            ('love',    '💕', '恋爱', '次', '#D500F9'),
        ]
        for idx, (key, emoji, name, unit, color) in enumerate(stat_info):
            row = tk.Frame(sc, bg=T['card'])
            row.pack(fill=tk.X, pady=1)
            self._tag('card_bg', row)
            el = tk.Label(row, text=emoji, font=(FONT_CN, 11),
                          bg=T['card'])
            el.pack(side=tk.LEFT)
            self._tag(f'stat_e_{key}', el)
            nl = tk.Label(row, text=name,
                          font=(FONT_CN, 10),
                          bg=T['card'], fg=T['stat_colors'][idx])
            nl.pack(side=tk.LEFT, padx=(4, 0))
            self._tag(f'stat_n_{key}', nl)
            vf = tk.Frame(row, bg=T['card'])
            vf.pack(side=tk.RIGHT)
            self._tag('card_bg', vf)
            vl = tk.Label(vf, text="--",
                          font=(FONT_MONO, 11, 'bold'),
                          bg=T['card'], fg='white')
            vl.pack(side=tk.LEFT)
            self._tag(f'stat_v_{key}', vl)
            ul = tk.Label(vf, text=unit,
                          font=(FONT_CN, 9),
                          bg=T['card'], fg=T['text_dim'])
            ul.pack(side=tk.LEFT, padx=(2, 0))
            self._tag(f'stat_u_{key}', ul)
            self._stat_labels[key] = vl

    # ==================== 核心逻辑 ====================

    def _get_birth(self):
        return datetime(int(self.birth_year.get()),
                        int(self.birth_month.get()),
                        int(self.birth_day.get()),
                        int(self.birth_hour.get()),
                        int(self.birth_min.get()),
                        int(self.birth_sec.get()))

    def _validate(self):
        try:
            b = self._get_birth()
            if b > datetime.now():
                return '出生日期不能晚于当前时间'
            le = float(self.life_exp_var.get())
            if not (0 < le <= 150):
                return '预期寿命应在 1～150 之间'
            if int(self.exp_love_var.get()) < 0:
                return '期望恋爱次数不能为负数'
            if int(self.done_love_var.get()) < 0:
                return '已恋爱次数不能为负数'
            return None
        except ValueError:
            return '请检查所有输入是否为有效数字'

    def _start(self):
        err = self._validate()
        if err:
            messagebox.showerror('输入有误', err)
            return
        self._birth_dt = self._get_birth()
        self._life_exp = float(self.life_exp_var.get())
        self._death_dt = self._birth_dt + timedelta(
            seconds=self._life_exp * SEC_PER_YEAR)
        self._total_love = int(self.exp_love_var.get())
        self._done_love = int(self.done_love_var.get())
        self.input_frame.pack_forget()
        self.display_frame.pack(fill=tk.BOTH, expand=True)
        self._tick()

    def _tick(self):
        now = datetime.now()

        # 年龄
        age_sec = (now - self._birth_dt).total_seconds()
        age_yr = age_sec / SEC_PER_YEAR
        self.age_label.config(text=f'{age_yr:.11f} 岁')

        # 主题色轮（仅极光/霓虹启用）
        T = THEMES[self._current_theme]
        if T.get('age_cycle'):
            if self._age_cycle % 3 == 0:
                palette = THEMES[self._current_theme]['stat_colors']
                ci = (self._age_cycle // 3) % len(palette)
                self.age_label.config(fg=palette[ci])
            self._age_cycle += 1

        # 剩余
        remain_sec = max(0, (self._death_dt - now).total_seconds())
        remain_days = remain_sec / SEC_PER_DAY

        # 进度
        total = self._life_exp * SEC_PER_YEAR
        pct = min(100, age_sec / total * 100) if total else 0
        self.progress['value'] = pct
        self.progress_label.config(text=f'生命进度  {pct:.2f}%')

        # 统计
        wk = self._count_weekends(now, self._death_dt) if remain_sec > 0 else 0
        self._stat_labels['weekend'].config(text=f'{wk:,}')
        self._stat_labels['meal'].config(
            text=f'{int(remain_days * MEALS):,}')
        self._stat_labels['heart'].config(
            text=f'{int(remain_sec / 60 * BPM):,}')
        love = max(0, self._total_love - self._done_love)
        self._stat_labels['love'].config(text=str(love))

        self._update_id = self.root.after(1000, self._tick)

    @staticmethod
    def _count_weekends(start, end):
        """O(1) 统计周六+周日总数"""
        days = (end.date() - start.date()).days
        if days <= 0:
            return 0
        full = days // 7
        rem = days % 7
        cnt = full * 2
        wd = start.weekday()
        for i in range(rem):
            if (wd + i) % 7 >= 5:
                cnt += 1
        return cnt

    def _reset(self):
        if self._update_id:
            self.root.after_cancel(self._update_id)
            self._update_id = None
        self._age_cycle = 0
        # 恢复年龄颜色为主题色
        T = THEMES[self._current_theme]
        for w in self._tw.get('age', []):
            if w.winfo_exists():
                w.configure(fg=T['age'])
        self.age_label.config(text='-- 岁')
        self.progress['value'] = 0
        self.progress_label.config(text='生命进度  0.00%')
        for k in self._stat_labels:
            self._stat_labels[k].config(text='--')
        self.display_frame.pack_forget()
        self.input_frame.pack(fill=tk.BOTH, expand=True)

    def _on_close(self):
        if self._update_id:
            self.root.after_cancel(self._update_id)
        self.root.destroy()


if __name__ == '__main__':
    root = tk.Tk()
    app = LifeRecorder(root)
    root.mainloop()
