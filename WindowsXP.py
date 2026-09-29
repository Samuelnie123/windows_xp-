# -*- coding: utf-8 -*-
"""
Windows XP 操作系统模拟器 (Pygame 实现)
功能：启动动画、登录、桌面、任务栏、开始菜单、窗口系统、
      我的电脑、回收站、控制面板、记事本、计算器、扫雷、画图、IE、
      任务管理器、无响应模拟、结束任务、右键菜单、鼠标状态、音效。
"""
import pygame, numpy as np, math, time, random, sys
from dataclasses import dataclass, field
from typing import Optional, Callable

import xp_icons  # 程序化图标绘制，替代 emoji 字体渲染（修复系统图片加载 bug）

# ===================== 常量 =====================
W, H = 1024, 768
FPS = 60
TASKBAR_H = 30

# XP 经典配色
C = {
    'desktop': (0, 78, 152),
    'win_bg': (236, 233, 216),
    'win_border': (8, 49, 217),
    'title_a': (0, 88, 230), 'title_b': (48, 128, 232), 'title_c': (14, 75, 191),
    'title_in_a': (122, 159, 224), 'title_in_b': (90, 127, 184),
    'btn_face': (245, 244, 234), 'btn_face2': (222, 219, 202),
    'btn_border': (127, 157, 185),
    'sel_blue': (49, 106, 197), 'sel_blue_l': (192, 212, 240),
    'menu_hi': (49, 106, 197),
    'text': (0, 0, 0), 'text_dis': (160, 160, 160),
    'sb_bg': (215, 211, 196), 'sb_border': (172, 168, 153),
    'green': (60, 142, 61), 'green_d': (42, 107, 43),
    'orange': (255, 154, 0),
    'start_l': (60, 142, 61), 'start_d': (30, 95, 31),
}

_FONT_CACHE = {}
_FONT_PATH = None
def _find_font():
    global _FONT_PATH
    if _FONT_PATH: return _FONT_PATH
    import os
    candidates = [
        r'C:\Windows\Fonts\msyh.ttc', r'C:\Windows\Fonts\msyh.ttf',
        r'C:\Windows\Fonts\simhei.ttf', r'C:\Windows\Fonts\simsun.ttc',
        r'C:\Windows\Fonts\Deng.ttf',
    ]
    for p in candidates:
        if os.path.isfile(p):
            _FONT_PATH = p; return p
    _FONT_PATH = None; return None

def font(size, bold=False):
    key = (size, bold)
    if key in _FONT_CACHE: return _FONT_CACHE[key]
    fp = _find_font()
    if fp:
        try:
            f = pygame.font.Font(fp, size)
            f.set_bold(bold)
        except Exception:
            f = pygame.font.Font(None, size)
    else:
        f = pygame.font.Font(None, size)
        f.set_bold(bold)
    wf = xp_icons.wrap(f)
    _FONT_CACHE[key] = wf
    return wf

def lerp(a, b, t): return a + (b - a) * t

def vgrad(w, h, c1, c2, c3=None):
    """生成竖直渐变 Surface"""
    s = pygame.Surface((w, h))
    for y in range(h):
        t = y / max(1, h - 1)
        if c3 and t > 0.5:
            tt = (t - 0.5) * 2
            col = tuple(int(lerp(c2[i], c3[i], tt)) for i in range(3))
        else:
            tt = t * 2 if c3 else t
            col = tuple(int(lerp(c1[i], c2[i], tt)) for i in range(3))
        pygame.draw.line(s, col, (0, y), (w, y))
    return s

def hgrad(w, h, stops):
    """stops: [(pos, color), ...] 水平渐变"""
    s = pygame.Surface((w, h))
    for x in range(w):
        t = x / max(1, w - 1)
        for i in range(len(stops) - 1):
            p0, c0 = stops[i]; p1, c1 = stops[i + 1]
            if p0 <= t <= p1:
                tt = (t - p0) / max(0.001, p1 - p0)
                col = tuple(int(lerp(c0[k], c1[k], tt)) for k in range(3))
                break
        else:
            col = stops[-1][1]
        pygame.draw.line(s, col, (x, 0), (x, h))
    return s

# ===================== 音效系统 =====================
class Sound:
    def __init__(self):
        self.ok = False; self.enabled = True
        try:
            pygame.mixer.pre_init(44100, -16, 2, 256)
            pygame.mixer.init()
            self.ok = True
        except Exception:
            self.ok = False
        self.sr = 44100
        self.cache = {}

    def _tone(self, freq, dur, vol=0.3, decay=6, wave='sine'):
        key = (freq, round(dur, 3), vol, decay, wave)
        if key in self.cache: return self.cache[key]
        n = int(self.sr * dur)
        t = np.arange(n) / self.sr
        env = np.exp(-t * decay)
        if wave == 'sine': w = np.sin(2 * np.pi * freq * t)
        elif wave == 'tri': w = 2 * np.abs(2 * (freq * t - np.floor(freq * t + 0.5))) - 1
        elif wave == 'sq': w = np.sign(np.sin(2 * np.pi * freq * t))
        else: w = np.sin(2 * np.pi * freq * t)
        sig = (vol * env * w * 32767).astype(np.int16)
        stereo = np.column_stack([sig, sig])
        snd = pygame.sndarray.make_sound(stereo)
        self.cache[key] = snd
        return snd

    def _noise(self, dur, vol=0.2, decay=8, hp=0):
        n = int(self.sr * dur); t = np.arange(n) / self.sr
        env = np.exp(-t * decay)
        w = np.random.uniform(-1, 1, n)
        if hp > 0:  # 简易高通：差分
            w = np.diff(w, prepend=0) * (1 + hp)
        sig = (vol * env * w * 32767).astype(np.int16)
        return pygame.sndarray.make_sound(np.column_stack([sig, sig]))

    def play(self, snd):
        if self.ok and self.enabled and snd:
            try: snd.play()
            except Exception: pass

    def click(self): self.play(self._tone(900, 0.04, 0.18, 30))
    def ding(self): self.play(self._tone(1200, 0.12, 0.22, 12, 'tri'))
    def err(self):
        self.play(self._tone(220, 0.18, 0.28, 8, 'sq'))
        pygame.time.delay(110)
        self.play(self._tone(160, 0.28, 0.28, 6, 'sq'))
    def startup(self):
        if not (self.ok and self.enabled): return
        for i, f in enumerate([523, 659, 784, 1047]):
            self.play(self._tone(f, 0.35, 0.22, 4))
            pygame.time.delay(120)
    def shutdown(self):
        if not (self.ok and self.enabled): return
        for f in [440, 370, 311, 247]:
            self.play(self._tone(f, 0.4, 0.25, 4))
            pygame.time.delay(150)
    def open(self): self.play(self._tone(700, 0.06, 0.16, 20))
    def max(self): self.play(self._tone(600, 0.05, 0.15, 24))
    def min(self): self.play(self._tone(400, 0.05, 0.15, 24))

SND = None

# ===================== 光标系统 =====================
class Cursor:
    """自定义鼠标指针，支持多种状态"""
    ARROW, BUSY, TEXT, HAND, HELP, SIZE = range(6)

    def __init__(self):
        self.state = self.ARROW
        self.spin = 0.0
        self.arrow = self._make_arrow()
        self.visible = True

    def _make_arrow(self):
        s = pygame.Surface((24, 24), pygame.SRCALPHA)
        # 白边 + 黑芯 箭头
        pts = [(2, 2), (2, 18), (6, 14), (9, 22), (12, 21), (9, 13), (15, 13)]
        pygame.draw.polygon(s, (255, 255, 255), [(p[0] + 1, p[1]) for p in pts] + [(p[0] - 1, p[1]) for p in pts])
        pygame.draw.polygon(s, (0, 0, 0), pts)
        pygame.draw.polygon(s, (255, 255, 255), pts, 1)
        return s

    def update(self, dt):
        self.spin += dt * 7.0

    def draw(self, surf, pos):
        if not self.visible: return
        x, y = pos
        if self.state == self.ARROW:
            surf.blit(self.arrow, (x, y))
        elif self.state == self.BUSY:
            # 旋转的沙漏圈
            cx, cy = x, y
            for i in range(12):
                a = self.spin + i * (math.pi * 2 / 12)
                alpha = int(255 * (i / 12))
                r1, r2 = 9, 13
                p1 = (cx + math.cos(a) * r1, cy + math.sin(a) * r1)
                p2 = (cx + math.cos(a) * r2, cy + math.sin(a) * r2)
                col = (60, 60, 60, alpha) if i > 6 else (200, 200, 200, alpha)
                pygame.draw.line(surf, col[:3], p1, p2, 3)
            pygame.draw.circle(surf, (0, 0, 0), (cx, cy), 14, 1)
        elif self.state == self.TEXT:
            # I-beam
            pygame.draw.rect(surf, (0, 0, 0), (x - 1, y - 8, 2, 16))
            pygame.draw.rect(surf, (0, 0, 0), (x - 4, y - 9, 8, 2))
            pygame.draw.rect(surf, (0, 0, 0), (x - 4, y + 7, 8, 2))
            pygame.draw.rect(surf, (255, 255, 255), (x, y - 8, 1, 16))
        elif self.state == self.HAND:
            # 手指
            pygame.draw.rect(surf, (0, 0, 0), (x - 1, y, 3, 10))
            pygame.draw.rect(surf, (255, 255, 255), (x, y + 1, 1, 8))
            pygame.draw.polygon(surf, (0, 0, 0), [(x - 4, y + 8), (x + 5, y + 8), (x + 5, y + 12), (x - 4, y + 12)])
            pygame.draw.polygon(surf, (255, 230, 180), [(x - 3, y + 9), (x + 4, y + 9), (x + 4, y + 11), (x - 3, y + 11)])
        elif self.state == self.HELP:
            surf.blit(self.arrow, (x, y))
            pygame.draw.circle(surf, (255, 255, 255), (x + 14, y + 14), 7)
            pygame.draw.circle(surf, (0, 0, 0), (x + 14, y + 14), 7, 1)
            t = font(11, bold=True).render('?', True, (0, 0, 0))
            surf.blit(t, (x + 11, y + 8))
        else:
            surf.blit(self.arrow, (x, y))

# ===================== UI 辅助 =====================
def draw_button(surf, rect, label, pressed=False, hover=False, enabled=True, fontobj=None):
    f = fontobj or font(11)
    r = pygame.Rect(rect)
    if not enabled:
        bg1, bg2, tc = (235, 233, 224), (215, 213, 196), C['text_dis']
    elif pressed:
        bg1, bg2, tc = (210, 208, 192), (245, 244, 234), C['text']
    elif hover:
        bg1, bg2, tc = (255, 255, 255), (228, 226, 210), C['text']
    else:
        bg1, bg2, tc = (245, 244, 234), (222, 219, 202), C['text']
    pygame.draw.rect(surf, bg1, r)
    pygame.draw.rect(surf, bg2, r, 0)
    # 渐变填充
    g = vgrad(r.w, r.h, bg1, bg2)
    surf.blit(g, r.topleft)
    if enabled:
        # 顶部高光
        pygame.draw.line(surf, (255, 255, 255), (r.left + 1, r.top + 1), (r.right - 2, r.top + 1))
        pygame.draw.rect(surf, C['btn_border'], r, 1)
    else:
        pygame.draw.rect(surf, (180, 178, 165), r, 1)
    t = f.render(label, True, tc)
    surf.blit(t, (r.centerx - t.get_width() // 2, r.centery - t.get_height() // 2))

def draw_title_bar(surf, rect, icon, title, active=True, fonts=None):
    r = pygame.Rect(rect)
    if active:
        g = hgrad(r.w, r.h, [(0, (0, 88, 230)), (0.08, (48, 128, 232)), (0.4, (26, 95, 192)),
                             (0.88, (22, 86, 208)), (1, (14, 75, 191))])
    else:
        g = vgrad(r.w, r.h, C['title_in_a'], C['title_in_b'])
    surf.blit(g, r.topleft)
    f = fonts or font(11, bold=True)
    if icon:
        surf.blit(font(13).render(icon, True, (255, 255, 255)), (r.left + 5, r.centery - 7))
    t = f.render(title, True, (255, 255, 255))
    # 文字阴影
    sh = f.render(title, True, (0, 0, 0))
    surf.blit(sh, (r.left + 24, r.top + 7))
    surf.blit(t, (r.left + 23, r.top + 6))

def draw_tb_button(surf, rect, kind, hover=False, pressed=False):
    """kind: 'min' 'max' 'close' 'restore'"""
    r = pygame.Rect(rect)
    if kind == 'close':
        c1, c2 = (232, 114, 103), (184, 52, 36)
    else:
        c1, c2 = (72, 139, 240), (30, 90, 192)
    if hover: c1, c2 = tuple(min(255, x + 18) for x in c1), tuple(min(255, x + 18) for x in c2)
    g = vgrad(r.w, r.h, c1, c2)
    surf.blit(g, r.topleft)
    pygame.draw.rect(surf, (255, 255, 255), r, 1)
    cx, cy = r.centerx, r.centery
    col = (255, 255, 255)
    if kind == 'min':
        pygame.draw.line(surf, col, (cx - 5, cy + 3), (cx + 5, cy + 3), 2)
    elif kind == 'max':
        pygame.draw.rect(surf, col, (cx - 5, cy - 4, 10, 8), 1)
    elif kind == 'restore':
        pygame.draw.rect(surf, col, (cx - 6, cy - 2, 8, 6), 1)
        pygame.draw.rect(surf, col, (cx - 2, cy - 5, 8, 6), 1)
    elif kind == 'close':
        pygame.draw.line(surf, col, (cx - 4, cy - 4), (cx + 4, cy + 4), 2)
        pygame.draw.line(surf, col, (cx + 4, cy - 4), (cx - 4, cy + 4), 2)

def point_in(p, rect):
    return rect.collidepoint(p)

# ===================== 窗口系统 =====================
class Window:
    def __init__(self, sys, title, icon, w, h, app=None):
        self.sys = sys
        self.title = title
        self.icon = icon
        self.app = app  # 应用对象，负责渲染内容区
        self.rect = pygame.Rect(0, 0, w, h)
        self.rect.center = (W // 2 + random.randint(-40, 40), H // 2 - 40 + random.randint(-30, 30))
        self.rect.clamp_ip(pygame.Rect(0, 0, W, H - TASKBAR_H))
        self.minimized = False
        self.maximized = False
        self.prev_rect = None
        self.z = 0
        self.responding = True
        self.freeze_timer = 0.0  # 无响应计时
        self.click_count = 0
        self.last_click_t = 0
        self.taskbar_btn_rect = None
        # 菜单栏
        self.menus = []  # [(name, [items])]  items: [(label, callback_or_None, enabled)]
        self.open_menu = -1
        self.menu_bar_h = 0
        # 状态栏
        self.status = ''
        # 拖动
        self._drag_off = None
        # dirty
        self.content_surf = pygame.Surface((w, h - 26), pygame.SRCALPHA)

    @property
    def title_bar_rect(self):
        return pygame.Rect(self.rect.x, self.rect.y, self.rect.w, 26)

    def menu_bar_rect(self):
        if self.menus:
            return pygame.Rect(self.rect.x, self.rect.bottom - (20 + (20 if self.status else 0)), self.rect.w, 20)
        return pygame.Rect(0, 0, 0, 0)

    def body_rect(self):
        top = self.rect.y + 26
        bottom = self.rect.bottom
        if self.status:
            bottom -= 20
        if self.menus:
            bottom -= 20
        return pygame.Rect(self.rect.x, top, self.rect.w, bottom - top)

    def status_bar_rect(self):
        if not self.status: return pygame.Rect(0, 0, 0, 0)
        return pygame.Rect(self.rect.x, self.rect.bottom - 20, self.rect.w, 20)

    def set_menus(self, menus):
        self.menus = menus

    def set_status(self, s):
        self.status = s

    def close(self):
        if self.app and hasattr(self.app, 'on_close'):
            if not self.app.on_close():
                return False
        return True

    def render(self, surf):
        if self.minimized: return
        r = self.rect
        # 阴影
        sh = pygame.Surface((r.w + 6, r.h + 6), pygame.SRCALPHA)
        pygame.draw.rect(sh, (0, 0, 0, 60), (3, 3, r.w, r.h), border_radius=8)
        surf.blit(sh, (r.x - 3, r.y - 3))
        # 窗体
        pygame.draw.rect(surf, C['win_border'], r, border_radius=8)
        body_inner = pygame.Rect(r.x + 1, r.y + 26, r.w - 2, r.h - 27)
        pygame.draw.rect(surf, C['win_bg'], body_inner)
        # 标题栏
        draw_title_bar(surf, self.title_bar_rect, self.icon, self.title, active=self.sys.active_win is self)
        # 标题按钮
        tb = self.title_bar_rect
        bx = tb.right - 6
        for kind in ['close', 'max', 'min']:
            bx -= 24
            hover = point_in(self.sys.mouse, pygame.Rect(bx, tb.y + 3, 22, 20))
            kind2 = 'restore' if kind == 'max' and self.maximized else kind
            draw_tb_button(surf, (bx, tb.y + 3, 22, 20), kind2, hover=hover)
        # 内容区
        body = self.body_rect()
        if self.app:
            self.content_surf = pygame.Surface((body.w, body.h), pygame.SRCALPHA)
            # 同 handle_event：渲染期间把鼠标平移到内容区局部坐标，使 app 内部
            # 的悬停高亮（hot/hover）能正确命中。
            saved_mouse = self.sys.mouse
            self.sys.mouse = (saved_mouse[0] - body.x, saved_mouse[1] - body.y)
            try:
                self.app.render(self.content_surf, self)
            except Exception as e:
                self.content_surf.fill((255, 255, 255))
                self.content_surf.blit(font(12).render(f"渲染错误: {e}", True, (200, 0, 0)), (8, 8))
            finally:
                self.sys.mouse = saved_mouse
            surf.blit(self.content_surf, body.topleft)
        # 菜单栏
        if self.menus:
            self._render_menu_bar(surf)
        # 状态栏
        if self.status:
            sb = self.status_bar_rect()
            pygame.draw.rect(surf, C['sb_bg'], sb)
            pygame.draw.line(surf, (255, 255, 255), (sb.x, sb.y), (sb.right, sb.y))
            pygame.draw.line(surf, C['sb_border'], (sb.x, sb.bottom - 1), (sb.right, sb.bottom - 1))
            surf.blit(font(11).render(self.status, True, C['text']), (sb.x + 8, sb.y + 4))
        # 无响应遮罩
        if not self.responding:
            ov = pygame.Surface((r.w, r.h), pygame.SRCALPHA)
            ov.fill((255, 255, 255, 180))
            surf.blit(ov, r.topleft)
            t = font(13).render('(没有响应)', True, (80, 80, 80))
            surf.blit(t, (r.centerx - t.get_width() // 2, r.centery - 8))

    def _render_menu_bar(self, surf):
        mb = self.menu_bar_rect()
        pygame.draw.rect(surf, C['win_bg'], mb)
        pygame.draw.line(surf, C['sb_border'], (mb.x, mb.y), (mb.right, mb.y))
        x = mb.x + 4
        f = font(11)
        for i, (name, _) in enumerate(self.menus):
            tw = f.size(name)[0] + 14
            item_rect = pygame.Rect(x, mb.y + 2, tw, 16)
            hot = self.open_menu == i or (point_in(self.sys.mouse, item_rect) and self.open_menu >= 0)
            if hot:
                pygame.draw.rect(surf, C['menu_hi'], item_rect)
                surf.blit(f.render(name, True, (255, 255, 255)), (x + 7, mb.y + 4))
            else:
                surf.blit(f.render(name, True, C['text']), (x + 7, mb.y + 4))
            x += tw
        # 下拉菜单
        if self.open_menu >= 0:
            self._render_dropdown(surf, self.open_menu, mb)

    def _menu_item_pos(self, i):
        mb = self.menu_bar_rect()
        x = mb.x + 4
        f = font(11)
        for j in range(i):
            x += f.size(self.menus[j][0])[0] + 14
        return x

    def _render_dropdown(self, surf, idx, mb):
        name, items = self.menus[idx]
        f = font(11)
        x = self._menu_item_pos(idx)
        ww = 160
        hh = 4
        meas = []
        for label, cb, en in items:
            if label == '-':
                meas.append(('sep', 0, True))
                hh += 5
            else:
                tw = f.size(label)[0]
                meas.append((label, tw, en))
                hh += 20
        y = mb.bottom
        box = pygame.Rect(x, y, ww, hh)
        # 阴影
        sh = pygame.Surface((ww + 4, hh + 4), pygame.SRCALPHA)
        pygame.draw.rect(sh, (0, 0, 0, 60), (2, 2, ww, hh))
        surf.blit(sh, (x - 2, y - 2))
        pygame.draw.rect(surf, C['win_bg'], box)
        pygame.draw.rect(surf, C['btn_border'], box, 1)
        cy = y + 2
        mp = self.sys.mouse
        for k, (lab, tw, en) in enumerate(meas):
            if lab == 'sep':
                pygame.draw.line(surf, C['sb_border'], (box.x + 4, cy + 2), (box.right - 4, cy + 2))
                cy += 5
            else:
                ir = pygame.Rect(box.x, cy, ww, 18)
                hov = point_in(mp, ir) and en
                if hov:
                    pygame.draw.rect(surf, C['menu_hi'], ir)
                    surf.blit(f.render(lab, True, (255, 255, 255) if en else (200, 200, 200)), (box.x + 18, cy + 2))
                else:
                    surf.blit(f.render(lab, True, C['text'] if en else C['text_dis']), (box.x + 18, cy + 2))
                cy += 20

    def handle_event(self, ev):
        """返回 True 表示事件被消费"""
        mp = self.sys.mouse
        # 无响应时只允许标题栏拖动尝试（实际冻结）
        if not self.responding:
            return False
        # 菜单下拉处理
        if self.menus and self.open_menu >= 0:
            if ev.type == pygame.MOUSEBUTTONDOWN and ev.button == 1:
                mb = self.menu_bar_rect()
                name, items = self.menus[self.open_menu]
                x = self._menu_item_pos(self.open_menu)
                ww = 160
                cy = mb.bottom + 2
                for lab, cb, en in items:
                    if lab == '-':
                        cy += 5
                    else:
                        ir = pygame.Rect(x, cy, ww, 18)
                        if ir.collidepoint(mp) and en and cb:
                            SND.click()
                            cb()
                            self.open_menu = -1
                            return True
                        cy += 20
                # 点击菜单标题切换
                if mb.collidepoint(mp):
                    tx = mb.x + 4
                    f = font(11)
                    for i in range(len(self.menus)):
                        tw = f.size(self.menus[i][0])[0] + 14
                        if pygame.Rect(tx, mb.y + 2, tw, 16).collidepoint(mp):
                            self.open_menu = i if i != self.open_menu else -1
                            return True
                        tx += tw
                self.open_menu = -1
                return True
            if ev.type == pygame.MOUSEMOTION:
                mb = self.menu_bar_rect()
                if mb.collidepoint(mp):
                    tx = mb.x + 4
                    f = font(11)
                    for i in range(len(self.menus)):
                        tw = f.size(self.menus[i][0])[0] + 14
                        if pygame.Rect(tx, mb.y + 2, tw, 16).collidepoint(mp):
                            if self.open_menu != i: self.open_menu = i
                            return True
                        tx += tw
            return False

        # 标题栏按钮
        if ev.type == pygame.MOUSEBUTTONDOWN and ev.button == 1:
            tb = self.title_bar_rect
            bx = tb.right - 6
            for kind in ['close', 'max', 'min']:
                bx -= 24
                if pygame.Rect(bx, tb.y + 3, 22, 20).collidepoint(mp):
                    if kind == 'close':
                        self.sys.close_window(self)
                    elif kind == 'max':
                        self.sys.toggle_max(self)
                    elif kind == 'min':
                        self.sys.minimize(self)
                    return True
            # 标题栏拖动 / 双击最大化
            if tb.collidepoint(mp):
                now = time.time()
                if now - self.last_click_t < 0.35:
                    self.sys.toggle_max(self)
                    self.last_click_t = 0
                    return True
                self.last_click_t = now
                if not self.maximized:
                    self._drag_off = (mp[0] - self.rect.x, mp[1] - self.rect.y)
                self.sys.click_window_title(self)
                return True
        if ev.type == pygame.MOUSEBUTTONUP:
            self._drag_off = None
        if ev.type == pygame.MOUSEMOTION and self._drag_off:
            self.rect.x = mp[0] - self._drag_off[0]
            self.rect.y = mp[1] - self._drag_off[1]
            self.rect.clamp_ip(pygame.Rect(-self.rect.w + 80, 0, W + self.rect.w - 80, H - TASKBAR_H))
            return True

        # 菜单栏点击打开
        if self.menus and ev.type == pygame.MOUSEBUTTONDOWN and ev.button == 1:
            mb = self.menu_bar_rect()
            if mb.collidepoint(mp):
                tx = mb.x + 4
                f = font(11)
                for i in range(len(self.menus)):
                    tw = f.size(self.menus[i][0])[0] + 14
                    if pygame.Rect(tx, mb.y + 2, tw, 16).collidepoint(mp):
                        self.open_menu = i
                        return True
                    tx += tw

        # 交给应用处理（将鼠标平移到内容区局部坐标，与 app.render 的局部几何对齐）
        # 注意：app.render 绘制到 content_surf（原点为 body 左上角），故 app 内部所有
        # 几何都是局部坐标；而 self.sys.mouse 是屏幕绝对坐标。窗口不在 (0,0) 时若不
        # 平移，点击位置会整体错位（如扫雷点 cell(2,2) 实际落到棋盘外）。
        if self.app and self.body_rect().collidepoint(mp):
            body = self.body_rect()
            saved_mouse = self.sys.mouse
            self.sys.mouse = (mp[0] - body.x, mp[1] - body.y)
            try:
                consumed = self.app.handle_event(ev, self)
            finally:
                self.sys.mouse = saved_mouse
            if consumed:
                return True
        return False

    def update(self, dt):
        if self.freeze_timer > 0:
            self.freeze_timer -= dt
            if self.freeze_timer <= 0:
                self.responding = True
        if self.app and self.responding:
            try: self.app.update(dt, self)
            except Exception: pass

# ===================== 应用基类 =====================
class App:
    name = "App"
    icon = "📄"
    def __init__(self, sys): self.sys = sys
    def render(self, surf, win): pass
    def handle_event(self, ev, win): return False
    def update(self, dt, win): pass
    def on_close(self): return True
    def cursor_state(self, mp, win): return None

# ===================== 记事本 =====================
class NotepadApp(App):
    name = "无标题 - 记事本"; icon = "📝"
    def __init__(self, sys):
        super().__init__(sys)
        self.text = ""
        self.cursor = 0
        self.sel = None
        self.scroll = 0
        self.dirty = False
        self.blink = 0
        self.word_wrap = False
        self.font_size = 13
        self.history = [""]   # 撤销历史
        self.hist_idx = 0

    def _push_history(self):
        # 截断未来记录，压入当前文本
        self.history = self.history[:self.hist_idx + 1]
        self.history.append(self.text)
        self.hist_idx = len(self.history) - 1
        # 限制历史长度
        if len(self.history) > 50:
            self.history = self.history[-50:]
            self.hist_idx = len(self.history) - 1

    def lines(self, maxw=None):
        if not self.word_wrap or not maxw:
            return self.text.split('\n')
        # 自动换行：按显示宽度拆分
        f = font(self.font_size)
        result = []
        for raw in self.text.split('\n'):
            if not raw:
                result.append('')
                continue
            line = ''
            for ch in raw:
                if f.size(line + ch)[0] > maxw and line:
                    result.append(line); line = ch
                else:
                    line += ch
            result.append(line)
        return result

    def render(self, surf, win):
        surf.fill((255, 255, 255))
        lines = self.lines(surf.get_width() - 8)
        f = font(self.font_size)
        lh = f.get_height() + 2
        clip = surf.get_rect()
        y = 2 - self.scroll
        for li, line in enumerate(lines):
            if y + lh > 0 and y < clip.h:
                surf.blit(f.render(line if line else ' ', True, C['text']), (4, y))
            y += lh
        # 光标
        self.blink = (self.blink + 1) % 60
        if self.blink < 30:
            cy = 0; cx = 0
            for li, line in enumerate(lines):
                ll = len(line)
                if self.cursor <= cy + ll + (1 if li < len(lines) - 1 else 0):
                    rel = self.cursor - cy
                    cx = max(0, min(rel, ll))
                    py = li * lh + 2 - self.scroll
                    tx = 4 + f.size(line[:cx])[0]
                    pygame.draw.line(surf, (0, 0, 0), (tx, py), (tx, py + lh - 2), 1)
                    break
                cy += ll + 1

    def handle_event(self, ev, win):
        if ev.type == pygame.KEYDOWN:
            self.dirty = True
            if ev.key == pygame.K_BACKSPACE:
                if self.cursor > 0:
                    self._push_history()
                    self.text = self.text[:self.cursor-1] + self.text[self.cursor:]
                    self.cursor -= 1
                return True
            if ev.key == pygame.K_DELETE:
                if self.cursor < len(self.text):
                    self._push_history()
                    self.text = self.text[:self.cursor] + self.text[self.cursor+1:]
                return True
            if ev.key == pygame.K_LEFT:
                self.cursor = max(0, self.cursor - 1); return True
            if ev.key == pygame.K_RIGHT:
                self.cursor = min(len(self.text), self.cursor + 1); return True
            if ev.key == pygame.K_HOME:
                # 行首
                i = self.cursor - 1
                while i >= 0 and self.text[i] != '\n': i -= 1
                self.cursor = i + 1; return True
            if ev.key == pygame.K_END:
                i = self.cursor
                while i < len(self.text) and self.text[i] != '\n': i += 1
                self.cursor = i; return True
            if ev.key == pygame.K_RETURN:
                self._push_history()
                self.text = self.text[:self.cursor] + '\n' + self.text[self.cursor:]
                self.cursor += 1; return True
            if ev.key == pygame.K_TAB:
                self._push_history()
                self.text = self.text[:self.cursor] + '    ' + self.text[self.cursor:]
                self.cursor += 4; return True
            if ev.key == pygame.K_z and (pygame.key.get_mods() & pygame.KMOD_CTRL):
                self.sys._np_undo(self); return True
        if ev.type == pygame.TEXTINPUT and ev.text:
            self._push_history()
            self.text = self.text[:self.cursor] + ev.text + self.text[self.cursor:]
            self.cursor += len(ev.text)
            return True
        return False

    def cursor_state(self, mp, win):
        return Cursor.TEXT

    def on_close(self):
        if self.dirty:
            return self.sys.confirm("记事本", "文件已修改，是否保存？\n（是=保存并关闭 否=不保存 取消=返回）")
        return True

# ===================== 计算器 =====================
class CalcApp(App):
    name = "计算器"; icon = "🧮"
    def __init__(self, sys):
        super().__init__(sys)
        self.display = "0"
        self.prev = None
        self.op = None
        self.new = True
        self.mem = 0

    def render(self, surf, win):
        surf.fill((236, 233, 216))
        # 显示屏
        dr = pygame.Rect(8, 8, surf.get_width() - 16, 36)
        pygame.draw.rect(surf, (255, 255, 255), dr)
        pygame.draw.rect(surf, C['btn_border'], dr, 1)
        t = font(20, bold=True).render(self.display, True, C['text'])
        surf.blit(t, (dr.right - t.get_width() - 6, dr.y + 8))
        # 按钮
        labels = [
            ('MC', 'MR', 'MS', 'M+', '←'),
            ('7', '8', '9', '/', '√'),
            ('4', '5', '6', '*', '%'),
            ('1', '2', '3', '-', '1/x'),
            ('0', '+/-', '.', '+', '='),
        ]
        x0, y0 = 8, 54
        bw = (surf.get_width() - 16 - 4 * 4) // 5
        bh = 32
        mp = self.sys.mouse
        for ri, row in enumerate(labels):
            for ci, lab in enumerate(row):
                bx = x0 + ci * (bw + 4)
                by = y0 + ri * (bh + 4)
                r = pygame.Rect(bx, by, bw, bh)
                hover = r.collidepoint(mp)
                col = C['text']
                if lab in '0123456789.':
                    bg1, bg2 = (255, 255, 255), (222, 219, 202)
                elif lab in '+-*/=':
                    bg1, bg2 = (90, 160, 240), (40, 100, 200)
                    col = (255, 255, 255)
                else:
                    bg1, bg2 = (245, 244, 234), (200, 198, 180)
                if hover:
                    bg1 = tuple(min(255, x + 20) for x in bg1)
                g = vgrad(r.w, r.h, bg1, bg2)
                surf.blit(g, r.topleft)
                pygame.draw.rect(surf, C['btn_border'], r, 1)
                f = font(12, bold=True)
                t = f.render(lab, True, col)
                surf.blit(t, (r.centerx - t.get_width() // 2, r.centery - t.get_height() // 2))

    def handle_event(self, ev, win):
        if ev.type == pygame.MOUSEBUTTONDOWN and ev.button == 1:
            mp = self.sys.mouse
            labels = [
                ('MC', 'MR', 'MS', 'M+', 'back'),
                ('7', '8', '9', '/', 'sqrt'),
                ('4', '5', '6', '*', '%'),
                ('1', '2', '3', '-', 'inv'),
                ('0', 'sign', '.', '+', '='),
            ]
            x0, y0 = 8, 54
            bw = (win.body_rect().w - 16 - 16) // 5
            bh = 32
            for ri, row in enumerate(labels):
                for ci, lab in enumerate(row):
                    bx = x0 + ci * (bw + 4)
                    by = y0 + ri * (bh + 4)
                    if pygame.Rect(bx, by, bw, bh).collidepoint(mp):
                        SND.click()
                        self._press(lab)
                        return True
        return False

    def _press(self, lab):
        try:
            if lab in '0123456789':
                if self.new or self.display == '0':
                    self.display = lab; self.new = False
                else:
                    self.display += lab
            elif lab == '.':
                if '.' not in self.display: self.display += '.'
                self.new = False
            elif lab == 'sign':
                self.display = str(-float(self.display))
            elif lab == 'back':
                self.display = self.display[:-1] or '0'
            elif lab in '+-*/':
                if self.op and not self.new:
                    self._calc()
                else:
                    self.prev = float(self.display)
                self.op = lab; self.new = True
            elif lab == '=':
                self._calc(); self.op = None; self.new = True
            elif lab == 'sqrt':
                self.display = str(math.sqrt(float(self.display))); self.new = True
            elif lab == 'inv':
                v = float(self.display)
                self.display = str(1 / v) if v else 'Error'; self.new = True
            elif lab == '%':
                if self.prev is not None:
                    self.display = str(self.prev * float(self.display) / 100)
            elif lab in ('MC', 'MR', 'MS', 'M+'):
                if lab == 'MC': self.mem = 0
                elif lab == 'MR': self.display = str(self.mem); self.new = True
                elif lab == 'MS': self.mem = float(self.display)
                elif lab == 'M+': self.mem += float(self.display)
            if len(self.display) > 16: self.display = self.display[:16]
        except Exception:
            self.display = 'Error'

    def _calc(self):
        if self.op and self.prev is not None:
            b = float(self.display)
            if self.op == '+': r = self.prev + b
            elif self.op == '-': r = self.prev - b
            elif self.op == '*': r = self.prev * b
            elif self.op == '/': r = self.prev / b if b else 0
            else: return
            if r == int(r): r = int(r)
            self.display = str(r)
            self.prev = r

# ===================== 扫雷 =====================
class MinesApp(App):
    name = "扫雷"; icon = "💣"
    def __init__(self, sys):
        super().__init__(sys)
        self.cols, self.rows, self.mines = 9, 9, 10
        self.reset()

    def reset(self):
        self.grid = [[0] * self.cols for _ in range(self.rows)]  # -1 雷, 0-8 数字
        self.revealed = [[False] * self.cols for _ in range(self.rows)]
        self.flagged = [[False] * self.cols for _ in range(self.rows)]
        self.state = 'ready'  # ready playing win lose
        self.first = True
        self.start_t = 0
        self.flags = 0

    def _place(self, sx, sy):
        positions = [(r, c) for r in range(self.rows) for c in range(self.cols)
                     if abs(r - sy) > 1 or abs(c - sx) > 1]
        random.shuffle(positions)
        for r, c in positions[:self.mines]:
            self.grid[r][c] = -1
        for r in range(self.rows):
            for c in range(self.cols):
                if self.grid[r][c] == -1: continue
                cnt = sum(1 for dr in (-1, 0, 1) for dc in (-1, 0, 1)
                          if 0 <= r + dr < self.rows and 0 <= c + dc < self.cols
                          and self.grid[r + dr][c + dc] == -1)
                self.grid[r][c] = cnt

    def cell_rect(self, c, r, ox, oy, cs):
        return pygame.Rect(ox + c * cs, oy + r * cs, cs, cs)

    def render(self, surf, win):
        surf.fill((192, 192, 192))
        cs = 24
        ox = (surf.get_width() - self.cols * cs) // 2
        oy = 36
        # 顶部信息
        top = pygame.Rect(ox, 4, self.cols * cs, 28)
        pygame.draw.rect(surf, (255, 255, 255), top)
        pygame.draw.rect(surf, (128, 128, 128), top, 1)
        mines_left = max(0, self.mines - self.flags)
        surf.blit(font(18, bold=True).render(f"💣 {mines_left:02d}", True, (255, 0, 0)), (ox + 6, 10))
        elapsed = int(time.time() - self.start_t) if self.state == 'playing' else 0
        if self.state == 'win' or self.state == 'lose': elapsed = int(time.time() - self.start_t)
        t = font(18, bold=True).render(f"⏱ {min(999, elapsed):03d}", True, (255, 0, 0))
        surf.blit(t, (top.right - t.get_width() - 6, 10))
        # 笑脸
        face_r = pygame.Rect(top.centerx - 12, 6, 24, 24)
        face = '🙂' if self.state != 'lose' else '😵'
        if self.state == 'win': face = '😎'
        if self.cell_rect(0, 0, ox, oy, cs).collidepoint(self.sys.mouse) and pygame.mouse.get_pressed()[0] and self.state == 'playing':
            face = '😮'
        surf.blit(font(20).render(face, True, (0, 0, 0)), (face_r.x, face_r.y))
        self._face_rect = face_r
        # 网格
        nums = {1: (0, 0, 255), 2: (0, 128, 0), 3: (255, 0, 0), 4: (0, 0, 128),
                5: (128, 0, 0), 6: (0, 128, 128), 7: (0, 0, 0), 8: (128, 128, 128)}
        for r in range(self.rows):
            for c in range(self.cols):
                cr = self.cell_rect(c, r, ox, oy, cs)
                if self.revealed[r][c]:
                    pygame.draw.rect(surf, (192, 192, 192), cr)
                    pygame.draw.line(surf, (128, 128, 128), (cr.x, cr.bottom - 1), (cr.right, cr.bottom - 1))
                    pygame.draw.line(surf, (128, 128, 128), (cr.right - 1, cr.y), (cr.right - 1, cr.bottom))
                    v = self.grid[r][c]
                    if v == -1:
                        surf.blit(font(16).render('💣', True, (0, 0, 0)), (cr.x + 4, cr.y + 2))
                    elif v > 0:
                        surf.blit(font(15, bold=True).render(str(v), True, nums.get(v, (0, 0, 0))), (cr.x + 7, cr.y + 3))
                else:
                    # 凸起按钮
                    pygame.draw.rect(surf, (255, 255, 255), cr)
                    pygame.draw.line(surf, (255, 255, 255), (cr.x, cr.y), (cr.right, cr.y))
                    pygame.draw.line(surf, (255, 255, 255), (cr.x, cr.y), (cr.x, cr.bottom))
                    pygame.draw.line(surf, (128, 128, 128), (cr.right - 1, cr.y), (cr.right - 1, cr.bottom))
                    pygame.draw.line(surf, (128, 128, 128), (cr.x, cr.bottom - 1), (cr.right, cr.bottom - 1))
                    if self.flagged[r][c]:
                        surf.blit(font(14).render('🚩', True, (0, 0, 0)), (cr.x + 4, cr.y + 3))
        if self.state == 'lose':
            # 显示所有雷
            for r in range(self.rows):
                for c in range(self.cols):
                    if self.grid[r][c] == -1 and not self.flagged[r][c]:
                        cr = self.cell_rect(c, r, ox, oy, cs)
                        pygame.draw.rect(surf, (255, 0, 0), cr)
                        surf.blit(font(16).render('💣', True, (0, 0, 0)), (cr.x + 4, cr.y + 2))
        self._grid_origin = (ox, oy, cs)

    def handle_event(self, ev, win):
        if ev.type == pygame.MOUSEBUTTONDOWN:
            mp = self.sys.mouse
            if hasattr(self, '_face_rect') and self._face_rect.collidepoint(mp):
                SND.click(); self.reset(); return True
            if self.state == 'lose' or self.state == 'win':
                return True
            ox, oy, cs = self._grid_origin
            c = (mp[0] - ox) // cs; r = (mp[1] - oy) // cs
            if 0 <= c < self.cols and 0 <= r < self.rows:
                if ev.button == 1:
                    if self.flagged[r][c]: return True
                    if self.first:
                        self._place(c, r); self.first = False
                        self.state = 'playing'; self.start_t = time.time()
                    self._reveal(r, c)
                    self._check_win()
                    SND.click()
                elif ev.button == 3:
                    if not self.revealed[r][c]:
                        self.flagged[r][c] = not self.flagged[r][c]
                        self.flags += 1 if self.flagged[r][c] else -1
                        SND.click()
                return True
        return False

    def _reveal(self, r, c):
        if r < 0 or r >= self.rows or c < 0 or c >= self.cols: return
        if self.revealed[r][c] or self.flagged[r][c]: return
        self.revealed[r][c] = True
        if self.grid[r][c] == -1:
            self.state = 'lose'; SND.err(); return
        if self.grid[r][c] == 0:
            for dr in (-1, 0, 1):
                for dc in (-1, 0, 1):
                    if dr or dc: self._reveal(r + dr, c + dc)

    def _check_win(self):
        for r in range(self.rows):
            for c in range(self.cols):
                if self.grid[r][c] != -1 and not self.revealed[r][c]: return
        self.state = 'win'; SND.ding()

# ===================== 画图 =====================
class PaintApp(App):
    name = "未命名 - 画图"; icon = "🎨"
    def __init__(self, sys):
        super().__init__(sys)
        self.canvas = None
        self.color = (0, 0, 0)
        self.tool = 'pencil'  # pencil, eraser, line, rect, fill
        self.size = 2
        self.drawing = False
        self.start_pt = None
        self.colors = [(0,0,0),(255,255,255),(255,0,0),(0,255,0),(0,0,255),
                       (255,255,0),(255,0,255),(0,255,255),(128,0,0),(0,128,0)]
        self.snapshots = []   # 撤销快照（最多 20 张）

    def _push_snapshot(self):
        if self.canvas is not None:
            snap = self.canvas.copy()
            self.snapshots.append(snap)
            if len(self.snapshots) > 20:
                self.snapshots.pop(0)

    def undo(self):
        if self.snapshots:
            snap = self.snapshots.pop()
            if self.canvas is not None and snap.get_size() == self.canvas.get_size():
                self.canvas.blit(snap, (0, 0))
            else:
                self.canvas = snap
            self.sys.message("画图", "已撤销上一步操作。", "🎨")

    def render(self, surf, win):
        surf.fill((192, 192, 192))
        bw = surf.get_width(); bh = surf.get_height()
        # 工具栏
        tools = [('✏️', 'pencil'), ('🧽', 'eraser'), ('📏', 'line'), ('⬜', 'rect'), ('🪣', 'fill')]
        tx = 4
        for emo, tid in tools:
            r = pygame.Rect(tx, 4, 24, 24)
            pygame.draw.rect(surf, (255,255,255) if self.tool != tid else (200,220,255), r)
            pygame.draw.rect(surf, (128,128,128), r, 1)
            surf.blit(font(14).render(emo, True, (0,0,0)), (tx+4, 6))
            tx += 26
        # 调色板
        cx = tx + 10
        for i, col in enumerate(self.colors):
            r = pygame.Rect(cx + i * 18, 6, 16, 16)
            pygame.draw.rect(surf, col, r)
            pygame.draw.rect(surf, (0,0,0), r, 1)
            if col == self.color:
                pygame.draw.rect(surf, (255,255,255), r.inflate(4,4), 2)
        # 画布
        cw, ch = bw - 12, bh - 40
        if self.canvas is None or self.canvas.get_size() != (cw, ch):
            old = self.canvas
            self.canvas = pygame.Surface((cw, ch))
            self.canvas.fill((255, 255, 255))
            if old:
                self.canvas.blit(old, (0, 0))
        surf.blit(self.canvas, (6, 34))
        pygame.draw.rect(surf, (128,128,128), (6, 34, cw, ch), 1)
        self._canvas_rect = pygame.Rect(6, 34, cw, ch)

    def handle_event(self, ev, win):
        mp = self.sys.mouse
        if ev.type == pygame.MOUSEBUTTONDOWN and ev.button == 1:
            # 工具选择
            tools = ['pencil', 'eraser', 'line', 'rect', 'fill']
            for i in range(5):
                if pygame.Rect(4 + i*26, 4, 24, 24).collidepoint(mp):
                    self.tool = tools[i]; SND.click(); return True
            # 颜色
            cx = 4 + 5*26 + 10
            for i in range(len(self.colors)):
                if pygame.Rect(cx + i*18, 6, 16, 16).collidepoint(mp):
                    self.color = self.colors[i]; SND.click(); return True
            # 画布
            if self._canvas_rect.collidepoint(mp):
                lp = (mp[0] - self._canvas_rect.x, mp[1] - self._canvas_rect.y)
                self._push_snapshot()   # 操作前留快照供撤销
                self.drawing = True
                self.start_pt = lp
                if self.tool == 'pencil':
                    pygame.draw.circle(self.canvas, self.color, lp, self.size)
                elif self.tool == 'eraser':
                    pygame.draw.circle(self.canvas, (255,255,255), lp, self.size + 4)
                elif self.tool == 'fill':
                    self._flood_fill(lp, self.color)
                return True
        if ev.type == pygame.MOUSEBUTTONUP:
            if self.drawing and self.tool in ('line', 'rect'):
                lp = (mp[0] - self._canvas_rect.x, mp[1] - self._canvas_rect.y)
                if self.tool == 'line':
                    pygame.draw.line(self.canvas, self.color, self.start_pt, lp, self.size)
                else:
                    r = pygame.Rect(min(self.start_pt[0], lp[0]), min(self.start_pt[1], lp[1]),
                                    abs(lp[0]-self.start_pt[0]), abs(lp[1]-self.start_pt[1]))
                    pygame.draw.rect(self.canvas, self.color, r, self.size)
            self.drawing = False
        if ev.type == pygame.MOUSEMOTION and self.drawing:
            if self._canvas_rect.collidepoint(mp):
                lp = (mp[0] - self._canvas_rect.x, mp[1] - self._canvas_rect.y)
                if self.tool == 'pencil':
                    pygame.draw.line(self.canvas, self.color, self.start_pt, lp, self.size)
                    self.start_pt = lp
                elif self.tool == 'eraser':
                    pygame.draw.line(self.canvas, (255,255,255), self.start_pt, lp, self.size + 4)
                    self.start_pt = lp
        return False

    def _flood_fill(self, pt, col):
        target = self.canvas.get_at(pt)
        if target[:3] == col: return
        stack = [pt]
        while stack:
            x, y = stack.pop()
            if x < 0 or y < 0 or x >= self.canvas.get_width() or y >= self.canvas.get_height(): continue
            if self.canvas.get_at((x, y))[:3] != target[:3]: continue
            self.canvas.set_at((x, y), col)
            stack.extend([(x+1,y),(x-1,y),(x,y+1),(x,y-1)])

# ===================== 我的电脑 =====================
class MyComputerApp(App):
    name = "我的电脑"; icon = "🖥️"
    def __init__(self, sys):
        super().__init__(sys)
        self.items = [
            ('💽', '本地磁盘 (C:)', '系统', 'my-documents'),
            ('💿', 'DVD 驱动器 (D:)', 'DVD RW', 'dvd'),
            ('📁', '我的文档', '文件夹', 'my-documents'),
            ('🖼️', '图片收藏', '文件夹', 'pictures'),
            ('🎵', '我的音乐', '文件夹', 'music'),
            ('⚙️', '控制面板', '系统文件夹', 'control-panel'),
            ('🗑️', '回收站', '系统文件夹', 'recycle'),
            ('🖨️', '打印机和传真', '控制面板', 'printers'),
            ('🌐', '网上邻居', '网络', 'network'),
            ('📝', '记事本', '快捷方式', 'notepad'),
            ('🧮', '计算器', '快捷方式', 'calc'),
            ('💣', '扫雷', '快捷方式', 'minesweeper'),
            ('🎨', '画图', '快捷方式', 'paint'),
            ('📧', 'Outlook Express', '快捷方式', 'outlook'),
            ('🎵', 'Media Player', '快捷方式', 'music'),
        ]
        self.selected = -1
        self.path = "我的电脑"

    def render(self, surf, win):
        surf.fill((255, 255, 255))
        bw = surf.get_width()
        # 工具栏
        tb_h = 30
        g = vgrad(bw, tb_h, (245,244,234), (222,219,202))
        surf.blit(g, (0, 0))
        pygame.draw.line(surf, C['sb_border'], (0, tb_h), (bw, tb_h))
        tools = ['⬅️ 后退', '➡️ 前进', '⬆️ 向上', '🔍 搜索', '📁 文件夹']
        tx = 6
        for tl in tools:
            t = font(10).render(tl, True, C['text'])
            r = pygame.Rect(tx, 4, t.get_width() + 12, 22)
            hot = r.collidepoint(self.sys.mouse)
            if hot: pygame.draw.rect(surf, (220,225,250), r); pygame.draw.rect(surf, (120,160,230), r, 1)
            surf.blit(t, (tx + 6, 9))
            tx += r.w + 4
        # 地址栏
        ay = tb_h + 4
        surf.blit(font(10).render("地址", True, C['text']), (6, ay + 3))
        ar = pygame.Rect(40, ay, bw - 90, 20)
        pygame.draw.rect(surf, (255,255,255), ar); pygame.draw.rect(surf, C['btn_border'], ar, 1)
        surf.blit(font(11).render(f"🖥️ {self.path}", True, C['text']), (ar.x + 4, ay + 3))
        # 文件区
        fy = ay + 26
        fh = surf.get_height() - fy
        # 侧边栏
        sw = 170
        side = pygame.Rect(0, fy, sw, fh)
        sg = vgrad(sw, fh, (124, 169, 229), (74, 124, 192))
        surf.blit(sg, side.topleft)
        self._draw_sidebar(surf, side)
        # 文件列表
        fl = pygame.Rect(sw, fy, bw - sw, fh)
        self._draw_files(surf, fl)

    def _draw_sidebar(self, surf, r):
        sections = [
            ("系统任务", [("⚙️ 查看系统信息", 'control-panel'), ("➕ 添加/删除程序", 'control-panel'), ("⚡ 更改设置", 'control-panel')]),
            ("其他位置", [("📁 我的文档", 'my-documents'), ("🗑️ 回收站", 'recycle'), ("🌐 网上邻居", None)]),
            ("详细信息", [("我的电脑", None)]),
        ]
        y = r.y + 6
        for title, items in sections:
            box = pygame.Rect(r.x + 4, y, r.w - 8, 18 + len(items) * 16 + 6)
            bg = vgrad(box.w, box.h, (221, 233, 250), (188, 212, 240))
            surf.blit(bg, box.topleft)
            surf.blit(font(11, bold=True).render(title, True, (0, 51, 153)), (box.x + 6, y + 3))
            iy = y + 20
            for lab, app in items:
                it = font(10).render(lab, True, (0, 51, 153))
                ir = pygame.Rect(box.x + 6, iy, box.w - 12, 14)
                hot = ir.collidepoint(self.sys.mouse) and app
                if hot: surf.blit(font(10, bold=True).render(lab, True, (0, 51, 153)), (box.x + 6, iy))
                else: surf.blit(it, (box.x + 6, iy))
                self.sys._register_link(ir, app)
                iy += 16
            y += box.h + 4

    def _draw_files(self, surf, r):
        pygame.draw.rect(surf, (255, 255, 255), r)
        ix = r.x + 10; iy = r.y + 8
        cw = 88
        mp = self.sys.mouse
        for i, (ic, name, det, app) in enumerate(self.items):
            col = (i % max(1, (r.w - 10) // cw))
            row = i // max(1, (r.w - 10) // cw)
            x = ix + col * cw; y = iy + row * 76
            box = pygame.Rect(x, y, cw, 72)
            sel = (self.selected == i)
            hot = box.collidepoint(mp)
            if sel:
                pygame.draw.rect(surf, C['sel_blue_l'], box)
                pygame.draw.rect(surf, C['sel_blue'], box, 1)
            elif hot:
                pygame.draw.rect(surf, (232, 240, 255), box)
            surf.blit(font(28).render(ic, True, (0, 0, 0)), (x + (cw - 28) // 2, y + 4))
            # 文件名换行
            f = font(10)
            words = name; ty = y + 36
            maxw = cw - 6
            line = ''
            for ch in words:
                if f.size(line + ch)[0] > maxw:
                    t = f.render(line, True, (255,255,255) if sel else C['text'])
                    surf.blit(t, (x + (cw - t.get_width()) // 2, ty)); ty += 12; line = ch
                else: line += ch
            if line:
                t = f.render(line, True, (255,255,255) if sel else C['text'])
                surf.blit(t, (x + (cw - t.get_width()) // 2, ty))

    def handle_event(self, ev, win):
        if ev.type == pygame.MOUSEBUTTONDOWN and ev.button == 1:
            mp = self.sys.mouse
            # 文件双击
            r = self._files_rect(win)
            if r.collidepoint(mp):
                cw = 88
                col = (mp[0] - r.x - 10) // cw
                row = (mp[1] - r.y - 8) // 76
                per_row = max(1, (r.w - 10) // cw)
                idx = int(row * per_row + col)
                if 0 <= idx < len(self.items):
                    self.selected = idx
                    now = time.time()
                    if not hasattr(self, '_last') or now - self._last > 0.4:
                        self._last = now; return True
                    # 双击
                    ic, name, det, app = self.items[idx]
                    if app:
                        self.sys.launch(app)
                    else:
                        self.sys.message("我的电脑", f"无法访问 {name}。", "📂")
                    self._last = now
                    return True
        return False

    def _files_rect(self, win):
        bw = win.body_rect().w
        tb_h = 30; ay = tb_h + 4 + 26
        return pygame.Rect(170, ay, bw - 170, win.body_rect().h - ay)

# ===================== 回收站 =====================
class RecycleApp(App):
    name = "回收站"; icon = "🗑️"
    def __init__(self, sys):
        super().__init__(sys)
        self.items = []  # (icon, name)

    def render(self, surf, win):
        surf.fill((255, 255, 255))
        bw = surf.get_width()
        tb_h = 30
        g = vgrad(bw, tb_h, (245,244,234), (222,219,202))
        surf.blit(g, (0, 0))
        pygame.draw.line(surf, C['sb_border'], (0, tb_h), (bw, tb_h))
        tools = ['↩️ 还原', '🗑️ 删除', '✨ 清空回收站']
        tx = 6
        for tl in tools:
            t = font(10).render(tl, True, C['text'])
            r = pygame.Rect(tx, 4, t.get_width() + 12, 22)
            hot = r.collidepoint(self.sys.mouse)
            if hot: pygame.draw.rect(surf, (220,225,250), r); pygame.draw.rect(surf, (120,160,230), r, 1)
            surf.blit(t, (tx + 6, 9))
            self._btn_rects = getattr(self, '_btn_rects', {})
            self._btn_rects[tl] = r
            tx += r.w + 4
        if not self.items:
            t = font(28).render('🗑️', True, (180,180,180))
            surf.blit(t, (bw // 2 - 24, surf.get_height() // 2 - 30))
            t2 = font(12).render('回收站是空的', True, (160,160,160))
            surf.blit(t2, (bw // 2 - t2.get_width() // 2, surf.get_height() // 2 + 20))
        else:
            ix = 12; iy = tb_h + 12; cw = 88
            for i, (ic, name) in enumerate(self.items):
                col = i % max(1, (bw - 12) // cw)
                row = i // max(1, (bw - 12) // cw)
                x = ix + col * cw; y = iy + row * 70
                surf.blit(font(26).render(ic, True, (0,0,0)), (x + (cw-26)//2, y))
                t = font(10).render(name, True, C['text'])
                surf.blit(t, (x + (cw - t.get_width()) // 2, y + 32))
        win.set_status(f"{len(self.items)} 个对象" if self.items else "0 个对象")

    def handle_event(self, ev, win):
        if ev.type == pygame.MOUSEBUTTONDOWN and ev.button == 1:
            mp = self.sys.mouse
            btns = getattr(self, '_btn_rects', {})
            for name, r in btns.items():
                if r.collidepoint(mp):
                    SND.click()
                    if '清空' in name:
                        if self.items and self.sys.confirm("回收站", "确定要永久删除所有项目吗？"):
                            self.items.clear(); SND.err()
                        elif not self.items:
                            self.sys.message("回收站", "回收站已经是空的。", "🗑️")
                    elif '还原' in name or '删除' in name:
                        if not self.items:
                            self.sys.message("回收站", "没有可操作的项目。", "🗑️")
                    return True
        return False

# ===================== 控制面板 =====================
class ControlPanelApp(App):
    name = "控制面板"; icon = "⚙️"
    def __init__(self, sys):
        super().__init__(sys)
        self.items = [
            ('🎨', '显示', '更改桌面背景、屏幕保护等', 'display'),
            ('🔊', '声音和音频设备', '调整音量、声音方案', 'sound'),
            ('🖱️', '鼠标', '更改鼠标指针设置', 'mouse'),
            ('⌨️', '键盘', '调整键盘响应速度', 'keyboard'),
            ('🕐', '日期和时间', '设置系统日期和时间', 'datetime'),
            ('🌐', 'Internet 选项', '配置 Internet 设置', 'internet'),
            ('⚡', '电源选项', '配置电源管理', 'power'),
            ('📋', '系统', '查看系统信息', 'system'),
            ('👤', '用户账户', '管理用户账户', 'user'),
            ('➕', '添加或删除程序', '安装或卸载程序', 'addremove'),
            ('🖨️', '打印机和传真', '管理打印机', 'printer'),
            ('🔤', '区域和语言选项', '配置区域设置', 'region'),
        ]

    def render(self, surf, win):
        surf.fill((255, 255, 255))
        # 左侧任务
        sw = 170
        side = pygame.Rect(0, 0, sw, surf.get_height())
        sg = vgrad(sw, surf.get_height(), (124, 169, 229), (74, 124, 192))
        surf.blit(sg, side.topleft)
        y = 8
        for title, links in [("请参阅", ["🌐 网络", "👤 用户账户"]), ("另请参阅", ["📂 我的电脑", "⚙️ 系统"])]:
            box = pygame.Rect(4, y, sw - 8, 18 + len(links) * 16 + 6)
            bg = vgrad(box.w, box.h, (221, 233, 250), (188, 212, 240))
            surf.blit(bg, box.topleft)
            surf.blit(font(11, bold=True).render(title, True, (0, 51, 153)), (box.x + 6, y + 3))
            iy = y + 20
            for lab in links:
                surf.blit(font(10).render(lab, True, (0, 51, 153)), (box.x + 6, iy)); iy += 16
            y += box.h + 4
        # 右侧网格
        rx = sw; rw = surf.get_width() - sw
        surf.blit(font(13, bold=True).render("选择一个类别", True, C['text']), (rx + 10, 8))
        cw = 150; ch = 70; ix = rx + 10; iy = 34
        per = max(1, (rw - 10) // cw)
        mp = self.sys.mouse
        for i, (ic, name, desc, act) in enumerate(self.items):
            col = i % per; row = i // per
            x = ix + col * cw; yy = iy + row * ch
            box = pygame.Rect(x, yy, cw - 6, ch - 6)
            hot = box.collidepoint(mp)
            if hot:
                pygame.draw.rect(surf, (232, 240, 255), box)
            surf.blit(font(26).render(ic, True, (0,0,0)), (x + 6, yy + 6))
            surf.blit(font(11, bold=True).render(name, True, (0, 51, 153) if hot else C['text']), (x + 42, yy + 8))
            t = font(9).render(desc, True, (120, 120, 120))
            # 简单换行
            if t.get_width() > cw - 48:
                surf.blit(font(9).render(desc[:14], True, (120,120,120)), (x + 42, yy + 24))
                surf.blit(font(9).render(desc[14:], True, (120,120,120)), (x + 42, yy + 36))
            else:
                surf.blit(t, (x + 42, yy + 26))

    def handle_event(self, ev, win):
        if ev.type == pygame.MOUSEBUTTONDOWN and ev.button == 1:
            mp = self.sys.mouse
            sw = 170; rw = win.body_rect().w - sw
            cw = 150; ch = 70; ix = sw + 10; iy = 34
            per = max(1, (rw - 10) // cw)
            for i, (ic, name, desc, act) in enumerate(self.items):
                col = i % per; row = i // per
                x = ix + col * cw; yy = iy + row * ch
                if pygame.Rect(x, yy, cw - 6, ch - 6).collidepoint(mp):
                    SND.click()
                    self.sys.settings_dialog(name, ic, self._groups_for(act))
                    return True
        return False

    def _groups_for(self, act):
        s = self.sys.settings
        now = time.strftime('%Y-%m-%d %H:%M:%S')
        wp_names = ['Bliss 蓝天白云', '绿色草地', '纯色深蓝']
        if act == 'display':
            return [
                ("桌面", [
                    {'kind': 'choice', 'label': '背景', 'key': 'wallpaper', 'choices': wp_names, 'values': [0, 1, 2]},
                    {'kind': 'choice', 'label': '分辨率', 'key': 'resolution', 'choices': ['800 × 600', '1024 × 768', '1280 × 1024']},
                    {'kind': 'choice', 'label': '刷新率', 'key': 'refresh', 'choices': [60, 70, 75, 85]},
                ]),
                ("效果", [
                    {'kind': 'info', 'label': '当前壁纸', 'value': lambda d: wp_names[d.get('wallpaper', 0)]},
                ]),
            ]
        if act == 'sound':
            return [
                ("音量", [
                    {'kind': 'check', 'label': '静音', 'key': 'mute'},
                    {'kind': 'choice', 'label': '音量', 'key': 'vol', 'choices': ['0', '1', '2', '3', '4', '5'], 'values': [0, 1, 2, 3, 4, 5]},
                ]),
                ("声音", [
                    {'kind': 'choice', 'label': '声音方案', 'key': 'sound_scheme', 'choices': ['Windows 默认', '无声', '经典'], 'values': [0, 1, 2]},
                ]),
            ]
        if act == 'mouse':
            return [
                ("按钮", [
                    {'kind': 'check', 'label': '切换主要和次要按钮', 'key': 'swap_buttons'},
                    {'kind': 'check', 'label': '单击锁定', 'key': 'clicklock'},
                ]),
                ("指针", [
                    {'kind': 'choice', 'label': '指针速度', 'key': 'pointer_speed', 'choices': ['慢', '较慢', '中', '较快', '快'], 'values': [0, 1, 2, 3, 4]},
                    {'kind': 'check', 'label': '显示指针轨迹', 'key': 'cursor_trail'},
                ]),
            ]
        if act == 'keyboard':
            return [
                ("字符重复", [
                    {'kind': 'choice', 'label': '重复延迟', 'key': 'repeat_delay', 'choices': ['长', '较长', '中', '较短', '短'], 'values': [0, 1, 2, 3, 4]},
                    {'kind': 'choice', 'label': '重复率', 'key': 'repeat_rate', 'choices': ['慢', '中', '快'], 'values': [0, 1, 2]},
                ]),
                ("测试", [
                    {'kind': 'info', 'label': '按住任意键测试重复', 'value': '在文本框中按住一个键...'},
                ]),
            ]
        if act == 'datetime':
            return [
                ("日期和时间", [
                    {'kind': 'info', 'label': '当前时间', 'value': now},
                    {'kind': 'info', 'label': '时区', 'value': '(UTC+08:00) 北京、重庆、香港'},
                    {'kind': 'choice', 'label': '日期格式', 'key': 'date_format', 'choices': ['yyyy-MM-dd', 'MM/dd/yyyy', 'dd-MM-yyyy'], 'values': [0, 1, 2]},
                ]),
            ]
        if act == 'internet':
            return [
                ("主页", [
                    {'kind': 'choice', 'label': '主页', 'key': 'homepage', 'choices': ['http://www.microsoft.com/windowsxp', 'http://www.microsoft.com', 'about:blank']},
                ]),
                ("历史记录", [
                    {'kind': 'info', 'label': '网页保存在历史记录中的天数', 'value': '20'},
                    {'kind': 'button', 'label': '清除历史记录', 'action': 'clearhistory'},
                ]),
            ]
        if act == 'power':
            return [
                ("电源使用方案", [
                    {'kind': 'choice', 'label': '关闭监视器', 'key': 'monitor_off', 'choices': ['从不', '5 分钟', '10 分钟', '30 分钟'], 'values': [0, 1, 2, 3]},
                    {'kind': 'choice', 'label': '系统待机', 'key': 'standby_after', 'choices': ['从不', '5 分钟', '10 分钟', '30 分钟'], 'values': [0, 1, 2, 3]},
                    {'kind': 'check', 'label': '启用休眠', 'key': 'hibernate'},
                ]),
            ]
        if act == 'system':
            return [
                ("常规", [
                    {'kind': 'info', 'label': '系统', 'value': 'Microsoft Windows XP'},
                    {'kind': 'info', 'label': '版本', 'value': 'Professional 2002 Service Pack 3'},
                    {'kind': 'info', 'label': '处理器', 'value': 'Intel Pentium 4 2.40 GHz'},
                    {'kind': 'info', 'label': '内存', 'value': '512 MB RAM'},
                ]),
            ]
        if act == 'user':
            return [
                ("账户", [
                    {'kind': 'info', 'label': '当前账户', 'value': s.get('account_name', 'Administrator')},
                    {'kind': 'info', 'label': '类型', 'value': '计算机管理员'},
                ]),
            ]
        if act == 'addremove':
            return [
                ("已安装程序", [
                    {'kind': 'info', 'label': '记事本', 'value': '1.0'},
                    {'kind': 'info', 'label': '计算器', 'value': '1.0'},
                    {'kind': 'info', 'label': '画图', 'value': '1.0'},
                    {'kind': 'info', 'label': '扫雷', 'value': '1.0'},
                    {'kind': 'info', 'label': 'Internet Explorer', 'value': '6.0'},
                ]),
            ]
        if act == 'printer':
            return [
                ("打印机和传真", [
                    {'kind': 'info', 'label': '默认打印机', 'value': 'HP LaserJet (未连接)'},
                    {'kind': 'info', 'label': '状态', 'value': '脱机'},
                ]),
            ]
        if act == 'region':
            return [
                ("区域选项", [
                    {'kind': 'choice', 'label': '位置', 'key': 'location', 'choices': ['中国', '美国', '日本', '英国'], 'values': [0, 1, 2, 3]},
                    {'kind': 'choice', 'label': '日期格式', 'key': 'date_format', 'choices': ['yyyy-MM-dd', 'MM/dd/yyyy', 'dd-MM-yyyy'], 'values': [0, 1, 2]},
                ]),
            ]
        return [("信息", [{'kind': 'info', 'label': '该项', 'value': '暂无设置'}])]

# ===================== IE 浏览器 =====================
class IEApp(App):
    name = "Internet Explorer"; icon = "🌐"
    def __init__(self, sys):
        super().__init__(sys)
        home = sys.settings.get('homepage', 'http://www.microsoft.com/windowsxp')
        self.history = [home]
        self.hist_idx = 0
        self.url_editing = False
        self.url_buf = ''
        self.loading = 0.0
        self.status = '完成'
        self._links = []        # [(rect, url)]
        self._tb = []           # [(rect, action)]
        self._addr_rect = None

    def _cur(self):
        return self.history[self.hist_idx]

    def navigate(self, url):
        url = (url or '').strip()
        if not url: return
        if url in ('home', '主页'): url = self.sys.settings.get('homepage', 'http://www.microsoft.com/windowsxp')
        if not url.startswith('http') and url != 'about:blank':
            url = 'http://' + url
        if url == self._cur():
            self.loading = 0.5; self.status = '正在加载...'; return
        self.history = self.history[:self.hist_idx + 1] + [url]
        self.hist_idx = len(self.history) - 1
        self.loading = 0.5; self.status = '正在加载...'
        self.url_editing = False

    def back(self):
        if self.hist_idx > 0:
            self.hist_idx -= 1; self.loading = 0.3; self.status = '正在加载...'

    def forward(self):
        if self.hist_idx < len(self.history) - 1:
            self.hist_idx += 1; self.loading = 0.3; self.status = '正在加载...'

    def home(self):
        self.navigate(self.sys.settings.get('homepage', 'http://www.microsoft.com/windowsxp'))

    def refresh(self):
        self.loading = 0.5; self.status = '正在加载...'

    def update(self, dt, win):
        if self.loading > 0:
            self.loading -= dt
            if self.loading <= 0:
                self.loading = 0; self.status = '完成'

    def _page(self, url):
        # 返回 (标题, [(kind, text), ...], [(文字, url), ...])
        if url == 'about:blank':
            return ('空白页', [], [])
        if url == 'http://www.microsoft.com':
            return ('Microsoft Corporation', [
                ('h', 'Microsoft Corporation'),
                ('s', 'Microsoft 主页'),
                ('p', '欢迎访问 Microsoft 官方网站。'),
                ('p', 'Microsoft 为个人和企业提供软件、服务和解决方案。'),
                ('p', ''),
            ], [('访问 Windows XP 主页', 'http://www.microsoft.com/windowsxp'),
                ('Microsoft 搜索', 'http://search.microsoft.com')])
        if url.endswith('/windowsxp/new'):
            return ('Windows XP 新功能', [
                ('h', 'Windows XP 新功能'),
                ('p', 'Windows XP 引入了大量改进：'),
                ('p', '• 全新的 Luna 视觉主题'),
                ('p', '• 快速用户切换'),
                ('p', '• 远程桌面'),
                ('p', '• Windows 防火墙'),
                ('p', '• 系统还原'),
                ('p', ''),
            ], [('返回主页', 'http://www.microsoft.com/windowsxp'),
                ('Microsoft 主页', 'http://www.microsoft.com')])
        if 'search' in url:
            return ('Microsoft 搜索', [
                ('h', '搜索结果'),
                ('p', '请选择一个结果：'),
                ('p', ''),
            ], [('Windows XP 主页', 'http://www.microsoft.com/windowsxp'),
                ('Windows XP 新功能', 'http://www.microsoft.com/windowsxp/new'),
                ('Microsoft 主页', 'http://www.microsoft.com')])
        # 默认 Windows XP 主页
        return ('Windows XP', [
            ('h', 'Windows XP'),
            ('s', 'Microsoft Corporation'),
            ('p', '欢迎使用 Windows XP Professional。'),
            ('p', 'Windows XP 提供了全新的视觉体验和更强大的功能。'),
            ('p', '• 全新的 Luna 用户界面'),
            ('p', '• 更快的启动和登录速度'),
            ('p', '• 改进的多媒体支持'),
            ('p', '• 增强的网络和安全性'),
            ('p', ''),
        ], [('了解 Windows XP 新功能', 'http://www.microsoft.com/windowsxp/new'),
            ('访问 Microsoft 主页', 'http://www.microsoft.com'),
            ('Microsoft 搜索', 'http://search.microsoft.com')])

    def render(self, surf, win):
        self._links = []; self._tb = []
        bw = surf.get_width(); bh = surf.get_height()
        surf.fill((255, 255, 255))
        tb_h = 30
        g = vgrad(bw, tb_h, (245, 244, 234), (222, 219, 202))
        surf.blit(g, (0, 0))
        pygame.draw.line(surf, C['sb_border'], (0, tb_h), (bw, tb_h))
        # 工具按钮
        can_back = self.hist_idx > 0
        can_fwd = self.hist_idx < len(self.history) - 1
        tools = [('⬅ 后退', 'back', can_back), ('➡ 前进', 'fwd', can_fwd),
                 ('⏹ 停止', 'stop', self.loading > 0), ('🔄 刷新', 'refresh', True),
                 ('🏠 主页', 'home', True)]
        tx = 6
        for tl, act, en in tools:
            t = font(10).render(tl, True, C['text'] if en else C['text_dis'])
            r = pygame.Rect(tx, 4, t.get_width() + 12, 22)
            hot = en and r.collidepoint(self.sys.mouse)
            if hot:
                pygame.draw.rect(surf, (220, 225, 250), r); pygame.draw.rect(surf, (120, 160, 230), r, 1)
            surf.blit(t, (tx + 6, 9))
            if en: self._tb.append((r, act))
            tx += r.w + 4
        # 地址栏
        ay = tb_h + 4
        surf.blit(font(10).render("地址", True, C['text']), (6, ay + 3))
        ar = pygame.Rect(40, ay, bw - 90, 20)
        self._addr_rect = ar
        pygame.draw.rect(surf, (255, 255, 255), ar)
        pygame.draw.rect(surf, (120, 160, 230) if self.url_editing else C['btn_border'], ar, 1)
        disp = self.url_buf if self.url_editing else self._cur()
        caret = '|' if self.url_editing and int(time.time() * 2) % 2 else ''
        surf.blit(font(11).render(disp + caret, True, C['text']), (ar.x + 4, ay + 3))
        # 转到按钮
        go = pygame.Rect(bw - 45, ay, 40, 20)
        draw_button(surf, go, "转到", hover=go.collidepoint(self.sys.mouse))
        self._tb.append((go, 'go'))
        # 网页内容
        py = ay + 26
        page_h = bh - py - 18
        pygame.draw.rect(surf, (255, 255, 255), (0, py, bw, page_h))
        if self.loading > 0:
            surf.blit(font(13).render("正在加载...", True, (120, 120, 120)), (20, py + 10))
        else:
            title, lines, links = self._page(self._cur())
            yy = py + 10
            for kind, text in lines:
                if kind == 'h':
                    surf.blit(font(22, bold=True).render(text, True, (0, 51, 153)), (20, yy)); yy += 30
                elif kind == 's':
                    surf.blit(font(13).render(text, True, (120, 120, 120)), (20, yy)); yy += 20
                else:
                    surf.blit(font(12).render(text, True, C['text']), (20, yy)); yy += 18
            yy += 8
            for ltext, lurl in links:
                t = font(12).render(ltext, True, (0, 0, 238))
                lr = pygame.Rect(20, yy, t.get_width(), 16)
                hot = lr.collidepoint(self.sys.mouse)
                if hot: pygame.draw.line(surf, (0, 0, 238), (20, yy + 15), (20 + t.get_width(), yy + 15), 1)
                surf.blit(t, (20, yy))
                self._links.append((lr, lurl))
                yy += 18
        # 状态栏
        sb = pygame.Rect(0, bh - 18, bw, 18)
        pygame.draw.rect(surf, (236, 233, 216), sb)
        pygame.draw.line(surf, C['sb_border'], (0, sb.y), (bw, sb.y))
        surf.blit(font(10).render(self.status, True, C['text']), (6, sb.y + 3))

    def handle_event(self, ev, win):
        if ev.type == pygame.MOUSEBUTTONDOWN and ev.button == 1:
            mp = self.sys.mouse
            if self._addr_rect and self._addr_rect.collidepoint(mp):
                self.url_editing = True; self.url_buf = self._cur(); SND.click(); return True
            for r, act in self._tb:
                if r.collidepoint(mp):
                    SND.click()
                    if self.url_editing and act != 'go': self.url_editing = False
                    if act == 'back': self.back()
                    elif act == 'fwd': self.forward()
                    elif act == 'stop': self.loading = 0; self.status = '已停止'
                    elif act == 'refresh': self.refresh()
                    elif act == 'home': self.home()
                    elif act == 'go': self.navigate(self.url_buf); self.url_editing = False
                    return True
            for r, url in self._links:
                if r.collidepoint(mp):
                    SND.click(); self.navigate(url); return True
            if self.url_editing: self.url_editing = False
            return False
        if ev.type == pygame.TEXTINPUT and self.url_editing:
            self.url_buf += ev.text; return True
        if ev.type == pygame.KEYDOWN and self.url_editing:
            if ev.key == pygame.K_BACKSPACE: self.url_buf = self.url_buf[:-1]; return True
            if ev.key == pygame.K_RETURN: self.navigate(self.url_buf); return True
            if ev.key == pygame.K_ESCAPE: self.url_editing = False; return True
        return False

# ===================== 任务管理器 =====================
class TaskMgrApp(App):
    name = "Windows 任务管理器"; icon = "📊"
    def __init__(self, sys):
        super().__init__(sys)
        self.tab = 'apps'
        self.selected = -1

    def render(self, surf, win):
        surf.fill((236, 233, 216))
        bw = surf.get_width()
        # 标签
        tabs = [('应用程序', 'apps'), ('进程', 'proc'), ('性能', 'perf')]
        tx = 4
        for name, tid in tabs:
            f = font(11, bold=(self.tab == tid))
            tw = f.size(name)[0] + 16
            r = pygame.Rect(tx, 4, tw, 20)
            if self.tab == tid:
                pygame.draw.rect(surf, (255,255,255), r)
                pygame.draw.rect(surf, C['btn_border'], r, 1)
            else:
                pygame.draw.rect(surf, (222,219,202), r)
                pygame.draw.rect(surf, (160,158,145), r, 1)
            surf.blit(f.render(name, True, C['text']), (tx + 8, 7))
            tx += tw + 2
        pygame.draw.line(surf, C['sb_border'], (0, 26), (bw, 26))
        if self.tab == 'apps':
            self._render_apps(surf, win)
        elif self.tab == 'proc':
            self._render_proc(surf, win)
        else:
            self._render_perf(surf, win)

    def _render_apps(self, surf, win):
        bw = surf.get_width(); bh = surf.get_height()
        # 列表
        lr = pygame.Rect(6, 32, bw - 12, bh - 70)
        pygame.draw.rect(surf, (255,255,255), lr)
        pygame.draw.rect(surf, C['btn_border'], lr, 1)
        # 表头
        pygame.draw.rect(surf, (245,244,234), (lr.x, lr.y, lr.w, 18))
        pygame.draw.line(surf, C['sb_border'], (lr.x, lr.y + 18), (lr.right, lr.y + 18))
        surf.blit(font(11, bold=True).render("任务", True, C['text']), (lr.x + 26, lr.y + 3))
        surf.blit(font(11, bold=True).render("状态", True, C['text']), (lr.x + 200, lr.y + 3))
        # 列表项
        y = lr.y + 22
        self._app_rows = []
        for i, w in enumerate(self.sys.windows):
            st = '正在运行' if w.responding else '没有响应'
            row = pygame.Rect(lr.x + 1, y, lr.w - 2, 16)
            if i == self.selected:
                pygame.draw.rect(surf, C['sel_blue'], row)
                tc = (255,255,255)
            else:
                tc = C['text']
            surf.blit(font(11).render(w.icon, True, tc), (lr.x + 6, y))
            surf.blit(font(11).render(w.title, True, tc), (lr.x + 26, y))
            surf.blit(font(11).render(st, True, tc if w.responding else (220,0,0)), (lr.x + 200, y))
            self._app_rows.append((row, w))
            y += 16
        # 按钮
        by = bh - 32
        draw_button(surf, (bw - 250, by, 75, 22), "结束任务", hover=pygame.Rect(bw-250, by, 75, 22).collidepoint(self.sys.mouse))
        draw_button(surf, (bw - 170, by, 75, 22), "切换至", hover=pygame.Rect(bw-170, by, 75, 22).collidepoint(self.sys.mouse))
        draw_button(surf, (bw - 90, by, 80, 22), "新任务...", hover=pygame.Rect(bw-90, by, 80, 22).collidepoint(self.sys.mouse))

    def _render_proc(self, surf, win):
        bw = surf.get_width(); bh = surf.get_height()
        lr = pygame.Rect(6, 32, bw - 12, bh - 70)
        pygame.draw.rect(surf, (255,255,255), lr)
        pygame.draw.rect(surf, C['btn_border'], lr, 1)
        pygame.draw.rect(surf, (245,244,234), (lr.x, lr.y, lr.w, 18))
        pygame.draw.line(surf, C['sb_border'], (lr.x, lr.y + 18), (lr.right, lr.y + 18))
        cols = [("映像名称", 6, 140), ("用户名", 150, 90), ("CPU", 245, 60), ("内存使用", 310, 80)]
        for name, x, ww in cols:
            surf.blit(font(11, bold=True).render(name, True, C['text']), (lr.x + x, lr.y + 3))
        procs = [("System Idle Process", "SYSTEM", 95, "20 K"), ("System", "SYSTEM", 2, "240 K"),
                 ("explorer.exe", "Administrator", 1, "8,420 K"), ("svchost.exe", "SYSTEM", 1, "4,200 K"),
                 ("winlogon.exe", "SYSTEM", 0, "1,200 K"), ("csrss.exe", "SYSTEM", 0, "3,800 K"),
                 ("lsass.exe", "SYSTEM", 0, "1,600 K"), ("services.exe", "SYSTEM", 0, "2,100 K")]
        y = lr.y + 22
        for i, (n, u, c, m) in enumerate(procs):
            if i == self.selected:
                pygame.draw.rect(surf, C['sel_blue'], (lr.x + 1, y, lr.w - 2, 16))
                tc = (255,255,255)
            else: tc = C['text']
            surf.blit(font(11).render(n, True, tc), (lr.x + 6, y))
            surf.blit(font(11).render(u, True, tc), (lr.x + 150, y))
            surf.blit(font(11).render(str(c), True, tc), (lr.x + 245, y))
            surf.blit(font(11).render(m, True, tc), (lr.x + 310, y))
            y += 16
        by = bh - 32
        draw_button(surf, (bw - 170, by, 75, 22), "结束进程", hover=pygame.Rect(bw-170, by, 75, 22).collidepoint(self.sys.mouse))

    def _render_perf(self, surf, win):
        bw = surf.get_width(); bh = surf.get_height()
        # CPU 历史
        cr = pygame.Rect(10, 36, 130, 80)
        pygame.draw.rect(surf, (0, 0, 0), cr)
        for i in range(40):
            v = 20 + 15 * math.sin(time.time() * 2 + i * 0.3) + random.randint(-3, 3)
            x = cr.x + i * 3
            pygame.draw.line(surf, (0, 255, 0), (x, cr.bottom), (x, cr.bottom - v), 2)
        surf.blit(font(11, bold=True).render("CPU 使用: 3%", True, C['text']), (cr.x, cr.bottom + 4))
        # 内存
        mr = pygame.Rect(150, 36, 130, 80)
        pygame.draw.rect(surf, (0, 0, 0), mr)
        for i in range(40):
            v = 45 + 5 * math.sin(time.time() + i * 0.2) + random.randint(-2, 2)
            x = mr.x + i * 3
            pygame.draw.line(surf, (255, 255, 0), (x, mr.bottom), (x, mr.bottom - v), 2)
        surf.blit(font(11, bold=True).render("PF 使用: 245 MB", True, C['text']), (mr.x, mr.bottom + 4))
        # 总数
        info = ["句柄数: 4,521", "线程数: 312", "进程数: " + str(len(self.sys.windows) + 8),
                "物理内存(K): 524288 总数 / 278921 可用",
                "认可用量(K): 612352 总数 / 251392 限制 / 245632 峰值"]
        y = 140
        for s in info:
            surf.blit(font(10).render(s, True, C['text']), (10, y)); y += 16

    def handle_event(self, ev, win):
        if ev.type == pygame.MOUSEBUTTONDOWN and ev.button == 1:
            mp = self.sys.mouse
            tabs = [('应用程序', 'apps'), ('进程', 'proc'), ('性能', 'perf')]
            tx = 4
            for name, tid in tabs:
                f = font(11, bold=(self.tab == tid))
                tw = f.size(name)[0] + 16
                if pygame.Rect(tx, 4, tw, 20).collidepoint(mp):
                    self.tab = tid; SND.click(); self.selected = -1; return True
                tx += tw + 2
            if self.tab == 'apps' and hasattr(self, '_app_rows'):
                for row, w in self._app_rows:
                    if row.collidepoint(mp):
                        self.selected = self.sys.windows.index(w); SND.click(); return True
                bw = win.body_rect().w; bh = win.body_rect().h
                by = bh - 32
                if pygame.Rect(bw - 250, by, 75, 22).collidepoint(mp):
                    if 0 <= self.selected < len(self.sys.windows):
                        w = self.sys.windows[self.selected]
                        if not w.responding:
                            self.sys.close_window(w); SND.ding()
                        else:
                            self.sys.close_window(w)
                    return True
                if pygame.Rect(bw - 170, by, 75, 22).collidepoint(mp):
                    if 0 <= self.selected < len(self.sys.windows):
                        self.sys.focus(self.sys.windows[self.selected])
                    return True
                if pygame.Rect(bw - 90, by, 80, 22).collidepoint(mp):
                    self.sys.launch('run'); return True
        return False

# ===================== 我的文档 =====================
class MyDocsApp(App):
    name = "我的文档"; icon = "📁"
    def __init__(self, sys):
        super().__init__(sys)
        self.items = [
            ('📝', '欢迎使用.txt', '文本文档', 'notepad'),
            ('📝', '项目笔记.txt', '文本文档', 'notepad'),
            ('🎨', '我的画图.bmp', 'BMP 图像', 'paint'),
            ('📄', '报告.doc', 'Word 文档', 'doc-file'),
            ('📊', '数据.xls', 'Excel 工作表', 'xls-file'),
            ('🎵', '音乐.mp3', 'MP3 文件', 'music'),
            ('📁', '工作', '文件夹', 'folder-empty'),
            ('📁', '照片', '文件夹', 'folder-empty'),
        ]
        self.selected = -1

    def render(self, surf, win):
        surf.fill((255, 255, 255))
        bw = surf.get_width()
        cw = 88; ix = 12; iy = 12
        mp = self.sys.mouse
        for i, (ic, name, det, app) in enumerate(self.items):
            col = i % max(1, (bw - 12) // cw); row = i // max(1, (bw - 12) // cw)
            x = ix + col * cw; y = iy + row * 74
            box = pygame.Rect(x, y, cw, 70)
            sel = self.selected == i; hot = box.collidepoint(mp)
            if sel: pygame.draw.rect(surf, C['sel_blue_l'], box); pygame.draw.rect(surf, C['sel_blue'], box, 1)
            elif hot: pygame.draw.rect(surf, (232,240,255), box)
            surf.blit(font(28).render(ic, True, (0,0,0)), (x + (cw-28)//2, y + 4))
            t = font(10).render(name, True, (255,255,255) if sel else C['text'])
            surf.blit(t, (x + (cw - t.get_width()) // 2, y + 38))
            t2 = font(8).render(det, True, (160,160,160) if not sel else (200,210,230))
            surf.blit(t2, (x + (cw - t2.get_width()) // 2, y + 52))

    def handle_event(self, ev, win):
        if ev.type == pygame.MOUSEBUTTONDOWN and ev.button == 1:
            mp = self.sys.mouse
            bw = win.body_rect().w; cw = 88
            col = (mp[0] - 12) // cw; row = (mp[1] - 12) // 74
            per = max(1, (bw - 12) // cw)
            idx = int(row * per + col)
            if 0 <= idx < len(self.items):
                self.selected = idx
                now = time.time()
                if not hasattr(self, '_last') or now - self._last > 0.4:
                    self._last = now; return True
                ic, name, det, app = self.items[idx]
                if app: self.sys.launch(app)
                else: self.sys.message("我的文档", f"无法打开 {name}。\n没有关联的程序。", ic)
                self._last = now; return True
        return False

# ===================== Outlook Express =====================
class OutlookExpressApp(App):
    name = "收件箱 - Outlook Express"; icon = "📧"
    def __init__(self, sys):
        super().__init__(sys)
        # 收件箱：(发件人, 主题, 日期, 正文, 已读)
        self.inbox = [
            ("Microsoft", "欢迎使用 Outlook Express", "2026-08-09 08:00",
             "感谢您使用 Outlook Express！\n\n本邮件客户端由 Windows XP 模拟器提供。\n您可以阅读邮件、撰写新邮件并发送。\n\n祝您使用愉快！", False),
            ("Windows 团队", "Windows XP 新功能介绍", "2026-08-08 14:30",
             "Windows XP 引入了 Luna 主题、快速用户切换和远程桌面等新功能。\n\n点击邮件中的链接可以了解更多信息。", False),
            ("Administrator", "测试邮件", "2026-08-07 10:15",
             "这是一封测试邮件。\n\n用于验证 Outlook Express 是否正常工作。", True),
            ("系统通知", "您的账户已创建", "2026-08-01 09:00",
             "您的 Administrator 账户已成功创建。\n\n如需修改账户信息，请前往控制面板。", True),
        ]
        self.sent = []
        self.folder = 'inbox'  # inbox / sent / read / compose
        self.selected = -1
        self.compose = {'to': '', 'subject': '', 'body': '', 'field': 'to'}
        self.read_idx = -1
        self.scroll = 0

    def _current_list(self):
        return self.inbox if self.folder == 'inbox' else self.sent

    def render(self, surf, win):
        surf.fill((255, 255, 255))
        bw = surf.get_width(); bh = surf.get_height()
        # 工具栏
        tb_h = 28
        g = vgrad(bw, tb_h, (245, 244, 234), (222, 219, 202))
        surf.blit(g, (0, 0))
        pygame.draw.line(surf, C['sb_border'], (0, tb_h), (bw, tb_h))
        tools = [('✉ 创建邮件', 'compose'), ('📥 收件箱', 'inbox'), ('📤 已发送', 'sent'), ('🔄 收发', 'refresh')]
        self._tb = []
        tx = 6
        for tl, act in tools:
            t = font(10).render(tl, True, C['text'])
            r = pygame.Rect(tx, 4, t.get_width() + 12, 20)
            hot = r.collidepoint(self.sys.mouse)
            active = (act == self.folder) or (act == 'compose' and self.folder == 'compose')
            if active:
                pygame.draw.rect(surf, (200, 220, 255), r); pygame.draw.rect(surf, (120, 160, 230), r, 1)
            elif hot:
                pygame.draw.rect(surf, (220, 225, 250), r); pygame.draw.rect(surf, (120, 160, 230), r, 1)
            surf.blit(t, (tx + 6, 8))
            self._tb.append((r, act))
            tx += r.w + 4
        # 文件夹列表区
        if self.folder in ('inbox', 'sent'):
            self._render_list(surf, bw, bh, tb_h)
        elif self.folder == 'read':
            self._render_read(surf, bw, bh, tb_h)
        elif self.folder == 'compose':
            self._render_compose(surf, bw, bh, tb_h)

    def _render_list(self, surf, bw, bh, tb_h):
        mails = self._current_list()
        # 列表区
        list_h = min(160, bh - tb_h - 80)
        list_rect = pygame.Rect(0, tb_h, bw, list_h)
        pygame.draw.rect(surf, (255, 255, 255), list_rect)
        pygame.draw.line(surf, C['sb_border'], (0, tb_h + list_h), (bw, tb_h + list_h))
        # 表头
        hdr_y = tb_h
        cols = [('发件人', 0, 160), ('主题', 160, bw - 280), ('日期', bw - 120, 120)]
        for name, x, w in cols:
            pygame.draw.rect(surf, (240, 240, 240), (x, hdr_y, w, 18))
            surf.blit(font(10, bold=True).render(name, True, C['text']), (x + 4, hdr_y + 3))
        pygame.draw.line(surf, C['sb_border'], (0, hdr_y + 18), (bw, hdr_y + 18))
        self._mail_rows = []
        ry = hdr_y + 18
        for i, m in enumerate(mails):
            row = pygame.Rect(0, ry, bw, 22)
            self._mail_rows.append((row, i))
            hot = row.collidepoint(self.sys.mouse)
            sel = (self.selected == i)
            if sel:
                pygame.draw.rect(surf, C['sel_blue_l'], row); pygame.draw.rect(surf, C['sel_blue'], row, 1)
            elif hot:
                pygame.draw.rect(surf, (232, 240, 255), row)
            sender, subject, date, body, read = m
            sc = C['text'] if read else (0, 0, 180)
            sf = font(10) if read else font(10, bold=True)
            surf.blit(sf.render(sender, True, sc), (4, ry + 4))
            surf.blit(sf.render(subject, True, sc), (164, ry + 4))
            surf.blit(font(9).render(date, True, (120, 120, 120)), (bw - 116, ry + 4))
            ry += 22
        # 预览区
        pv = pygame.Rect(0, tb_h + list_h, bw, bh - tb_h - list_h)
        pygame.draw.rect(surf, (252, 252, 248), pv)
        if 0 <= self.selected < len(mails):
            m = mails[self.selected]
            surf.blit(font(12, bold=True).render(f"主题: {m[1]}", True, C['text']), (pv.x + 10, pv.y + 8))
            surf.blit(font(10).render(f"发件人: {m[0]}    日期: {m[2]}", True, (90, 90, 90)), (pv.x + 10, pv.y + 28))
            pygame.draw.line(surf, C['sb_border'], (pv.x + 10, pv.y + 48), (pv.right - 10, pv.y + 48))
            yy = pv.y + 56
            for line in m[3].split('\n'):
                surf.blit(font(11).render(line, True, C['text']), (pv.x + 12, yy))
                yy += 16
        else:
            surf.blit(font(11).render("选择一封邮件以预览，双击可在新窗口阅读。", True, (160, 160, 160)), (pv.x + 12, pv.y + 12))
        # 状态栏
        sb = pygame.Rect(0, bh - 18, bw, 18)
        pygame.draw.rect(surf, C['sb_bg'], sb)
        unread = sum(1 for m in mails if not m[4]) if self.folder == 'inbox' else 0
        pygame.draw.line(surf, C['sb_border'], (sb.x, sb.y), (sb.right, sb.y))
        surf.blit(font(10).render(f"{self.folder_label()}，共 {len(mails)} 封邮件，{unread} 封未读", True, C['text']), (sb.x + 8, sb.y + 3))

    def folder_label(self):
        return {'inbox': '收件箱', 'sent': '已发送'}.get(self.folder, '')

    def _render_read(self, surf, bw, bh, tb_h):
        mails = self.inbox
        if not (0 <= self.read_idx < len(mails)):
            self.folder = 'inbox'; return
        m = mails[self.read_idx]
        surf.blit(font(16, bold=True).render(m[1], True, C['text']), (12, tb_h + 8))
        surf.blit(font(11).render(f"发件人: {m[0]}", True, (90, 90, 90)), (12, tb_h + 32))
        surf.blit(font(11).render(f"日期: {m[2]}", True, (90, 90, 90)), (12, tb_h + 50))
        pygame.draw.line(surf, C['sb_border'], (12, tb_h + 70), (bw - 12, tb_h + 70))
        yy = tb_h + 80
        for line in m[3].split('\n'):
            surf.blit(font(12).render(line, True, C['text']), (16, yy))
            yy += 18
        sb = pygame.Rect(0, bh - 18, bw, 18)
        pygame.draw.rect(surf, C['sb_bg'], sb)
        surf.blit(font(10).render("阅读邮件 — 点击“收件箱”返回列表", True, C['text']), (sb.x + 8, sb.y + 3))

    def _render_compose(self, surf, bw, bh, tb_h):
        c = self.compose
        # 收件人
        surf.blit(font(11).render("收件人:", True, C['text']), (12, tb_h + 10))
        tr = pygame.Rect(70, tb_h + 8, bw - 84, 22)
        self._field_to = tr
        pygame.draw.rect(surf, (255, 255, 255), tr)
        pygame.draw.rect(surf, (120, 160, 230) if c['field'] == 'to' else C['btn_border'], tr, 1)
        caret = '|' if c['field'] == 'to' and int(time.time() * 2) % 2 else ''
        surf.blit(font(11).render(c['to'] + caret, True, C['text']), (tr.x + 4, tr.y + 4))
        # 主题
        surf.blit(font(11).render("主题:", True, C['text']), (12, tb_h + 38))
        sr = pygame.Rect(70, tb_h + 36, bw - 84, 22)
        self._field_subj = sr
        pygame.draw.rect(surf, (255, 255, 255), sr)
        pygame.draw.rect(surf, (120, 160, 230) if c['field'] == 'subject' else C['btn_border'], sr, 1)
        surf.blit(font(11).render(c['subject'] + ('|' if c['field'] == 'subject' and int(time.time() * 2) % 2 else ''), True, C['text']), (sr.x + 4, sr.y + 4))
        # 正文
        br = pygame.Rect(12, tb_h + 68, bw - 24, bh - tb_h - 68 - 50)
        self._field_body = br
        pygame.draw.rect(surf, (255, 255, 255), br)
        pygame.draw.rect(surf, (120, 160, 230) if c['field'] == 'body' else C['btn_border'], br, 1)
        lines = c['body'].split('\n')
        yy = br.y + 4
        for i, line in enumerate(lines):
            surf.blit(font(11).render(line, True, C['text']), (br.x + 4, yy))
            yy += 16
            if yy > br.bottom - 8: break
        # 发送 / 取消 按钮
        send = pygame.Rect(bw - 180, bh - 38, 80, 24)
        cancel = pygame.Rect(bw - 90, bh - 38, 80, 24)
        self._send_btn = send; self._cancel_btn = cancel
        draw_button(surf, send, "发送", hover=send.collidepoint(self.sys.mouse))
        draw_button(surf, cancel, "取消", hover=cancel.collidepoint(self.sys.mouse))

    def handle_event(self, ev, win):
        mp = self.sys.mouse
        if ev.type == pygame.MOUSEBUTTONDOWN and ev.button == 1:
            # 工具栏
            for r, act in getattr(self, '_tb', []):
                if r.collidepoint(mp):
                    SND.click()
                    if act == 'compose':
                        self.folder = 'compose'
                        self.compose = {'to': '', 'subject': '', 'body': '', 'field': 'to'}
                    elif act == 'inbox':
                        self.folder = 'inbox'; self.selected = -1
                    elif act == 'sent':
                        self.folder = 'sent'; self.selected = -1
                    elif act == 'refresh':
                        self.sys.message("Outlook Express", "没有新邮件。\n\n上次检查时间: " + time.strftime("%H:%M"), "📧")
                    return True
            if self.folder == 'compose':
                # 字段切换
                if getattr(self, '_field_to', pygame.Rect(0,0,0,0)).collidepoint(mp):
                    self.compose['field'] = 'to'; return True
                if getattr(self, '_field_subj', pygame.Rect(0,0,0,0)).collidepoint(mp):
                    self.compose['field'] = 'subject'; return True
                if getattr(self, '_field_body', pygame.Rect(0,0,0,0)).collidepoint(mp):
                    self.compose['field'] = 'body'; return True
                if getattr(self, '_send_btn', pygame.Rect(0,0,0,0)).collidepoint(mp):
                    SND.click()
                    if not self.compose['to'].strip():
                        self.sys.message("Outlook Express", "请输入收件人地址。", "⚠️"); return True
                    self.sent.insert(0, (self.compose['to'], self.compose['subject'] or '(无主题)',
                                         time.strftime("%Y-%m-%d %H:%M"), self.compose['body'] or '(无内容)', True))
                    self.folder = 'sent'; self.selected = 0
                    self.sys.message("Outlook Express", "邮件已发送成功！", "✉️")
                    return True
                if getattr(self, '_cancel_btn', pygame.Rect(0,0,0,0)).collidepoint(mp):
                    SND.click(); self.folder = 'inbox'; return True
                return True
            # 列表点击
            for row, i in getattr(self, '_mail_rows', []):
                if row.collidepoint(mp):
                    SND.click()
                    now = time.time()
                    dbl = hasattr(self, '_last') and self._last_i == i and now - self._last < 0.4
                    self._last = now; self._last_i = i
                    self.selected = i
                    if self.folder == 'inbox':
                        m = self.inbox[i]
                        self.inbox[i] = (m[0], m[1], m[2], m[3], True)
                    if dbl:
                        self.read_idx = i; self.folder = 'read'
                    return True
            return True
        if ev.type == pygame.TEXTINPUT and self.folder == 'compose':
            f = self.compose['field']
            if f == 'to':
                self.compose['to'] += ev.text
            elif f == 'subject':
                self.compose['subject'] += ev.text
            else:
                self.compose['body'] += ev.text
            return True
        if ev.type == pygame.KEYDOWN and self.folder == 'compose':
            f = self.compose['field']
            if ev.key == pygame.K_BACKSPACE:
                if f == 'to': self.compose['to'] = self.compose['to'][:-1]
                elif f == 'subject': self.compose['subject'] = self.compose['subject'][:-1]
                else: self.compose['body'] = self.compose['body'][:-1]
                return True
            if ev.key == pygame.K_RETURN and f == 'body':
                self.compose['body'] += '\n'; return True
            if ev.key == pygame.K_TAB:
                self.compose['field'] = {'to': 'subject', 'subject': 'body', 'body': 'to'}[f]
                return True
        return False

# ===================== 音乐播放器 =====================
class MusicPlayerApp(App):
    name = "Windows Media Player"; icon = "🎵"
    def __init__(self, sys):
        super().__init__(sys)
        self.tracks = [
            ("Windows 启动音效.wav", "系统", 8),
            ("Bliss 山丘.mp3", "自然环境", 204),
            ("Luna 主题曲.mp3", "Bill Brown", 171),
            ("登录音效.wav", "系统", 4),
            ("经典.wav", "系统", 6),
        ]
        self.cur = 0
        self.playing = False
        self.pos = 0.0  # 秒

    def _fmt(self, secs):
        m = int(secs) // 60; s = int(secs) % 60
        return f"{m}:{s:02d}"

    def _track_duration(self, i):
        return float(self.tracks[i][2])

    def render(self, surf, win):
        surf.fill((40, 40, 55))
        bw = surf.get_width(); bh = surf.get_height()
        # 顶部标题栏区
        hg = vgrad(bw, 50, (60, 60, 90), (40, 40, 60))
        surf.blit(hg, (0, 0))
        pygame.draw.line(surf, (100, 100, 140), (0, 50), (bw, 50))
        surf.blit(font(15, bold=True).render("🎵 Windows Media Player", True, (255, 255, 255)), (12, 8))
        surf.blit(font(10).render("正在播放", True, (200, 200, 220)), (12, 30))
        # 可视化区
        viz = pygame.Rect(10, 60, bw - 20, 110)
        pygame.draw.rect(surf, (20, 20, 30), viz, border_radius=6)
        pygame.draw.rect(surf, (80, 80, 110), viz, 1, border_radius=6)
        # 频谱条（基于时间和当前轨道）
        import math as _m
        n = 24
        bw_bar = (viz.w - 20) // n
        def _clamp(v): return max(0, min(255, int(v)))
        for i in range(n):
            if self.playing:
                h = 8 + 70 * (0.5 + 0.5 * _m.sin(self.pos * 6 + i * 0.7)) * (0.6 + 0.4 * _m.sin(i * 0.5))
            else:
                h = 6
            col = (_clamp(80 + 100 * _m.sin(i * 0.4)), _clamp(120 + 80 * _m.sin(i * 0.7 + 1)), 220)
            br = pygame.Rect(viz.x + 10 + i * bw_bar, viz.bottom - 8 - h, bw_bar - 3, h)
            pygame.draw.rect(surf, col, br, border_radius=2)
        # 当前曲目信息
        info_y = viz.bottom + 12
        name, artist, dur = self.tracks[self.cur]
        surf.blit(font(13, bold=True).render(name, True, (255, 255, 255)), (12, info_y))
        surf.blit(font(10).render(f"艺术家: {artist}", True, (180, 180, 200)), (12, info_y + 22))
        # 进度条
        pr = pygame.Rect(12, info_y + 44, bw - 24, 8)
        self._prog_rect = pr
        pygame.draw.rect(surf, (70, 70, 90), pr, border_radius=4)
        d = self._track_duration(self.cur)
        p = min(1.0, self.pos / d) if d > 0 else 0
        if p > 0:
            fw = int(pr.w * p)
            pygame.draw.rect(surf, (100, 180, 255), (pr.x, pr.y, fw, pr.h), border_radius=4)
        surf.blit(font(9).render(self._fmt(self.pos), True, (200, 200, 220)), (pr.x, pr.bottom + 2))
        surf.blit(font(9).render(self._fmt(d), True, (200, 200, 220)), (pr.right - 24, pr.bottom + 2))
        # 控制按钮
        by = bh - 40
        self._btns = []
        defs = [('⏮', 'prev'), ('⏯', 'play'), ('⏭', 'next'), ('⏹', 'stop')]
        bx = bw // 2 - 80
        for lab, act in defs:
            r = pygame.Rect(bx, by, 40, 28)
            hot = r.collidepoint(self.sys.mouse)
            col = (90, 90, 130) if not hot else (120, 120, 170)
            pygame.draw.rect(surf, col, r, border_radius=4)
            pygame.draw.rect(surf, (140, 140, 180), r, 1, border_radius=4)
            surf.blit(font(14).render(lab, True, (255, 255, 255)), (r.x + 13, r.y + 6))
            self._btns.append((r, act))
            bx += 44
        # 播放列表
        pl = pygame.Rect(bw - 170, 60, 160, bh - 110)
        pygame.draw.rect(surf, (30, 30, 45), pl, border_radius=4)
        pygame.draw.rect(surf, (80, 80, 110), pl, 1, border_radius=4)
        surf.blit(font(10, bold=True).render("播放列表", True, (220, 220, 240)), (pl.x + 8, pl.y + 6))
        self._pl_rows = []
        yy = pl.y + 24
        for i, (n, a, d) in enumerate(self.tracks):
            row = pygame.Rect(pl.x + 4, yy, pl.w - 8, 22)
            self._pl_rows.append((row, i))
            hot = row.collidepoint(self.sys.mouse)
            cur = (i == self.cur)
            if cur:
                pygame.draw.rect(surf, (70, 110, 160), row, border_radius=3)
            elif hot:
                pygame.draw.rect(surf, (60, 60, 85), row, border_radius=3)
            nm = n if len(n) < 18 else n[:17] + '…'
            surf.blit(font(9).render(nm, True, (255, 255, 255) if cur else (200, 200, 220)), (row.x + 4, row.y + 2))
            surf.blit(font(8).render(self._fmt(d), True, (160, 160, 180)), (row.right - 28, row.y + 4))
            yy += 24
            if yy > pl.bottom - 6: break

    def handle_event(self, ev, win):
        mp = self.sys.mouse
        if ev.type == pygame.MOUSEBUTTONDOWN and ev.button == 1:
            for r, act in getattr(self, '_btns', []):
                if r.collidepoint(mp):
                    SND.click()
                    if act == 'play':
                        self.playing = not self.playing
                        if self.playing: SND.ding()
                    elif act == 'stop':
                        self.playing = False; self.pos = 0
                    elif act == 'prev':
                        self.cur = (self.cur - 1) % len(self.tracks)
                        self.pos = 0; self.playing = True
                    elif act == 'next':
                        self.cur = (self.cur + 1) % len(self.tracks)
                        self.pos = 0; self.playing = True
                    return True
            for row, i in getattr(self, '_pl_rows', []):
                if row.collidepoint(mp):
                    SND.click()
                    self.cur = i; self.pos = 0; self.playing = True
                    return True
            # 进度条拖动
            pr = getattr(self, '_prog_rect', None)
            if pr and pr.collidepoint(mp):
                d = self._track_duration(self.cur)
                self.pos = max(0, min(d, (mp[0] - pr.x) / pr.w * d))
                return True
        return False

    def update(self, dt, win):
        if self.playing:
            self.pos += dt
            d = self._track_duration(self.cur)
            if self.pos >= d:
                self.pos = 0
                self.cur = (self.cur + 1) % len(self.tracks)
                self.duration = self._track_duration(self.cur)

# ===================== 系统主类 =====================
class XPSystem:
    def __init__(self):
        pygame.init()
        self.screen = pygame.display.set_mode((W, H))
        pygame.display.set_caption("Windows XP 模拟器")
        self.clock = pygame.time.Clock()
        global SND
        SND = Sound()
        self.snd = SND
        self.cursor = Cursor()
        self.mouse = (0, 0)
        self.windows = []
        self.active_win = None
        self.z_counter = 10
        self.phase = 'boot'  # boot login desktop shutdown
        self.boot_t = 0
        self.boot_progress = 0
        self.login_t = 0
        self._login_msg = None  # (text, remaining_seconds)
        self.shut_t = 0
        # 桌面图标
        self.icons = [
            ('🖥️', '我的电脑', 'computer'),
            ('🗑️', '回收站', 'recycle'),
            ('🌐', 'Internet Explorer', 'ie'),
            ('📁', '我的文档', 'my-documents'),
            ('📝', '记事本', 'notepad'),
            ('🎨', '画图', 'paint'),
            ('🧮', '计算器', 'calc'),
            ('💣', '扫雷', 'minesweeper'),
        ]
        self.icon_selected = -1
        # 开始菜单
        self.start_open = False
        # 右键菜单
        self.ctx_menu = None  # {'items':[(label,cb,icon,enabled)], 'pos':(x,y)}
        # 对话框
        self.dialog = None
        # 链接注册（侧边栏）
        self._links = []
        # 桌面壁纸缓存
        self._wallpaper = self._make_wallpaper()
        self._boot_logo = self._make_boot_logo()
        self._last_click_t = 0
        self._last_click_target = None
        # 关机/待机
        self.shut_mode = 'off'   # 'off' 关机  'restart' 重启
        self.standby_t = 0
        self._standby_snap = None   # 进入待机前抓取的桌面快照（用于淡出动画）
        self._standby_waking = 0.0  # >0 表示正在从待机唤醒（淡入剩余时间）
        # 系统设置（持久化，控制面板各项修改这里）
        self.settings = {
            'mute': not self.snd.enabled,
            'vol': 3,                 # 0-5 音量
            'sound_scheme': 0,        # 0 默认 1 无声 2 经典
            'wallpaper': 0,           # 0 蓝天白云 1 草地 2 纯色
            'resolution': '1024 × 768',
            'refresh': 60,
            'swap_buttons': False,
            'pointer_speed': 2,       # 1-3
 'clicklock': False,
            'cursor_trail': False,
            'repeat_rate': 2,         # 0 慢 1 中 2 快
            'repeat_delay': 2,
            'date_format': 0,         # 0 yyyy-MM-dd 1 MM/dd/yyyy
            'location': 0,            # 区域索引
            'standby_after': 1,       # 0 从不 1 5分钟 2 10分钟 3 30分钟
            'monitor_off': 1,
            'hibernate': False,
            'account_name': 'Administrator',
            'homepage': 'http://www.microsoft.com/windowsxp',
        }

    def _make_wallpaper(self):
        variant = self.settings.get('wallpaper', 0) if hasattr(self, 'settings') else 0
        s = pygame.Surface((W, H))
        if variant == 2:
            # 纯色深蓝
            s.fill((0, 78, 152)); return s
        if variant == 1:
            # 草地：蓝天 + 大片绿草
            for y in range(H):
                t = y / H
                if t < 0.55:
                    r = int(lerp(120, 180, t / 0.55)); g = int(lerp(180, 220, t / 0.55)); b = int(lerp(230, 200, t / 0.55))
                else:
                    u = (t - 0.55) / 0.45
                    r = int(lerp(90, 50, u)); g = int(lerp(170, 95, u)); b = int(lerp(70, 35, u))
                pygame.draw.line(s, (r, g, b), (0, y), (W, y))
            # 朵朵白云
            for cx, cy, cr in [(180, 110, 26), (460, 80, 20), (760, 140, 30), (920, 90, 18)]:
                for dx, dy, rr in [(0, 0, cr), (cr * 0.8, 6, cr * 0.8), (-cr * 0.8, 6, cr * 0.8), (0, -cr * 0.4, cr * 0.7)]:
                    pygame.draw.circle(s, (255, 255, 255), (int(cx + dx), int(cy + dy)), int(rr))
            return s
        # 默认：蓝天白云（XP Bliss 风格）
        for y in range(H):
            t = y / H
            r = int(lerp(56, 26, t)); g = int(lerp(118, 48, t)); b = int(lerp(197, 96, t))
            pygame.draw.line(s, (r, g, b), (0, y), (W, y))
        for layer, (col, off) in enumerate([((80, 140, 70), 0), ((60, 110, 55), 40), ((45, 85, 45), 80)]):
            pts = [(0, H - TASKBAR_H)]
            for x in range(0, W + 10, 10):
                y = H - TASKBAR_H - 60 - off - 30 * math.sin(x * 0.01 + layer) - 20 * math.sin(x * 0.03)
                pts.append((x, y))
            pts.append((W, H - TASKBAR_H))
            pygame.draw.polygon(s, col, pts)
        pygame.draw.circle(s, (255, 240, 180), (W - 150, 120), 40)
        pygame.draw.circle(s, (255, 255, 220), (W - 150, 120), 30)
        return s

    def _make_boot_logo(self):
        s = pygame.Surface((340, 120), pygame.SRCALPHA)
        # Windows 旗帜
        flag_pts = [(0, 0), (18, -5), (18, 18), (0, 18)]
        colors = [(232, 67, 0), (255, 184, 0), (0, 160, 227), (60, 160, 71)]
        for i, col in enumerate(colors):
            x = 220 + (i % 2) * 22
            y = 10 + (i // 2) * 22
            quad = [(x, y), (x + 18, y - 4), (x + 18, y + 14), (x, y + 18)]
            pygame.draw.polygon(s, col, quad)
        # 文字
        f1 = font(22, bold=True)
        f2 = font(18)
        s.blit(f1.render("Windows", True, (255, 255, 255)), (0, 10))
        xp = font(28, bold=True).render("xp", True, (255, 154, 0))
        s.blit(xp, (f1.size("Windows")[0] + 4, 4))
        s.blit(f2.render("Professional", True, (255, 255, 255)), (0, 48))
        s.blit(font(11).render("Microsoft®", True, (200, 200, 200)), (0, 80))
        return s

    # ---------- 应用启动 ----------
    def launch(self, app_id):
        app_map = {
            'computer': (MyComputerApp, 720, 480, '我的电脑', '🖥️'),
            'my-computer': (MyComputerApp, 720, 480, '我的电脑', '🖥️'),
            'recycle': (RecycleApp, 600, 400, '回收站', '🗑️'),
            'recycle-bin': (RecycleApp, 600, 400, '回收站', '🗑️'),
            'ie': (IEApp, 640, 460, 'Internet Explorer', '🌐'),
            'internet-explorer': (IEApp, 640, 460, 'Internet Explorer', '🌐'),
            'my-documents': (MyDocsApp, 560, 400, '我的文档', '📁'),
            'notepad': (NotepadApp, 500, 380, '无标题 - 记事本', '📝'),
            'paint': (PaintApp, 560, 420, '未命名 - 画图', '🎨'),
            'calc': (CalcApp, 260, 280, '计算器', '🧮'),
            'calculator': (CalcApp, 260, 280, '计算器', '🧮'),
            'minesweeper': (MinesApp, 280, 360, '扫雷', '💣'),
            'control-panel': (ControlPanelApp, 640, 440, '控制面板', '⚙️'),
            'taskmanager': (TaskMgrApp, 480, 380, 'Windows 任务管理器', '📊'),
            'outlook': (OutlookExpressApp, 600, 420, '收件箱 - Outlook Express', '📧'),
            'outlook-express': (OutlookExpressApp, 600, 420, '收件箱 - Outlook Express', '📧'),
            'music': (MusicPlayerApp, 520, 380, 'Windows Media Player', '🎵'),
            'media-player': (MusicPlayerApp, 520, 380, 'Windows Media Player', '🎵'),
        }
        if app_id == 'run':
            self._open_run(); return
        if app_id == 'help':
            self.message("帮助和支持中心", "Windows XP 帮助和支持\n\n这是一个用 Pygame 实现的 Windows XP 模拟器。\n\n功能：\n• 双击桌面图标启动程序\n• 拖动窗口标题栏移动\n• 双击标题栏最大化\n• 右键桌面/图标弹出菜单\n• 连续点击窗口标题栏可触发无响应\n• Ctrl+Alt+Del 打开任务管理器\n• 点击开始菜单访问所有程序", "❓"); return
        if app_id == 'search':
            self._open_search(); return
        if app_id == 'pictures':
            self.launch('paint'); return
        if app_id == 'printers':
            self.launch('control-panel'); return
        if app_id == 'dvd':
            self.message("DVD 驱动器 (D:)", "请将磁盘插入驱动器 D:。\n\n当前驱动器中没有可读取的介质。", "💿"); return
        if app_id == 'network':
            self.message("网上邻居", "当前没有可用的网络连接。\n\n请检查网络设置或联系系统管理员。", "🌐"); return
        if app_id == 'folder-empty':
            self.message("文件夹", "此文件夹为空。", "📁"); return
        if app_id == 'doc-file':
            self._open_doc_file(); return
        if app_id == 'xls-file':
            self._open_xls_file(); return
        if app_id == 'shutdown':
            self._shutdown(); return
        if app_id == 'logoff':
            if self.confirm("注销 Windows", "确定要注销吗？\n当前所有程序将被关闭。"):
                SND.shutdown(); pygame.time.delay(500); self.phase = 'boot'; self.boot_t = 0; self.boot_progress = 0
                self.windows.clear()
            return
        info = app_map.get(app_id)
        if not info:
            self.message("Windows", f"找不到应用程序：{app_id}", "⚠️"); return
        AppCls, w, h, title, icon = info
        app = AppCls(self)
        win = Window(self, title, icon, w, h, app=app)
        # 记事本菜单
        if isinstance(app, NotepadApp):
            self._setup_notepad_menus(win, app)
        if isinstance(app, MyComputerApp):
            win.set_status(f"{len(app.items)} 个对象")
        if isinstance(app, RecycleApp):
            win.set_status("0 个对象")
        if isinstance(app, PaintApp):
            win.set_menus([
                ("文件", [("新建", lambda: self._paint_clear(app), True), ("退出", lambda: self.close_window(win), True)]),
                ("编辑", [("撤销", lambda: app.undo(), True), ("清除", lambda: self._paint_clear(app), True)]),
                ("帮助", [("关于画图", lambda: self.message("关于画图", "画图\nWindows XP 模拟器", "🎨"), True)]),
            ])
        self.windows.append(win)
        self.focus(win)
        SND.open()

    def _open_run(self):
        self.dialog = {'type': 'run', 'text': '', 'btn': 0}

    def _open_search(self):
        # 搜索对话框：在已安装程序与文件中匹配
        self.dialog = {'type': 'search', 'text': '', 'btn': 0, 'results': [], 'sel': -1}

    def _search_apps(self, query):
        q = query.lower().strip()
        if not q: return []
        apps = [
            ('🌐', 'Internet Explorer', 'ie'),
            ('📧', 'Outlook Express', 'outlook'),
            ('📝', '记事本', 'notepad'),
            ('🎨', '画图', 'paint'),
            ('🧮', '计算器', 'calc'),
            ('💣', '扫雷', 'minesweeper'),
            ('🖥️', '我的电脑', 'computer'),
            ('📁', '我的文档', 'my-documents'),
            ('🗑️', '回收站', 'recycle'),
            ('⚙️', '控制面板', 'control-panel'),
            ('📊', '任务管理器', 'taskmanager'),
            ('🎵', 'Windows Media Player', 'music'),
        ]
        res = []
        for ic, name, app in apps:
            if q in name.lower() or q in app.lower():
                res.append((ic, name, app))
        return res

    def _open_doc_file(self):
        # 用记事本打开“报告/数据”等文档（模拟打开文档内容）
        app = NotepadApp(self)
        app.text = "报告\n\n这是用记事本打开的示例文档。\n由于未安装 Microsoft Word，已用记事本显示纯文本内容。\n\n您可以直接编辑并保存。"
        app.cursor = 0; app.dirty = False
        win = Window(self, '报告.doc - 记事本', '📄', 500, 380, app=app)
        self._setup_notepad_menus(win, app)
        self.windows.append(win); self.focus(win); SND.open()

    def _open_xls_file(self):
        app = NotepadApp(self)
        app.text = "数据.xls\n（未安装 Microsoft Excel，已用记事本显示）\n\n项目\t数量\t单价\t合计\n笔\t12\t3.00\t36.00\n本\t5\t8.50\t42.50\n尺\t3\t2.00\t6.00\n\n合计：\t\t\t84.50"
        app.cursor = 0; app.dirty = False
        win = Window(self, '数据.xls - 记事本', '📊', 500, 380, app=app)
        self._setup_notepad_menus(win, app)
        self.windows.append(win); self.focus(win); SND.open()

    def _setup_notepad_menus(self, win, app):
        win.set_menus([
            ("文件", [("新建", lambda: self._np_new(app), True), ("保存", lambda: self._np_save(app), True),
                      ("-", None, True), ("退出", lambda: self.close_window(win), True)]),
            ("编辑", [("撤销", lambda: self._np_undo(app), True),
                      ("-", None, True),
                      ("全选", lambda: self._np_select_all(app), True),
                      ("日期/时间", lambda: self._np_datetime(app), True)]),
            ("格式", [("自动换行", lambda: self._np_toggle_wrap(app), True),
                      ("字体...", lambda: self._np_font(app), True)]),
            ("帮助", [("关于记事本", lambda: self.message("关于记事本", "记事本\nWindows XP 模拟器\nPygame 版本", "📝"), True)]),
        ])
        win.set_status(f"第 1 行，第 1 列")

    def _np_new(self, app):
        if app.dirty and not self.confirm("记事本", "是否保存当前内容？"):
            return
        app.text = ""; app.cursor = 0; app.dirty = False
        app.history = [app.text]; app.hist_idx = 0

    def _np_save(self, app):
        app.dirty = False
        self.message("记事本", "文件已保存。", "📝")

    def _np_undo(self, app):
        if app.hist_idx > 0:
            app.hist_idx -= 1
            app.text = app.history[app.hist_idx]
            app.cursor = min(app.cursor, len(app.text))

    def _np_toggle_wrap(self, app):
        app.word_wrap = not app.word_wrap
        self.message("记事本", f"自动换行已{'开启' if app.word_wrap else '关闭'}。", "📝")

    def _np_font(self, app):
        sizes = [11, 13, 15, 17]
        try: idx = sizes.index(app.font_size)
        except ValueError: idx = 1
        app.font_size = sizes[(idx + 1) % len(sizes)]
        self.message("字体", f"记事本字体大小已设置为 {app.font_size} pt。", "🔤")

    def _np_select_all(self, app):
        app.cursor = len(app.text)

    def _np_datetime(self, app):
        app._push_history()
        s = time.strftime("%H:%M %Y-%m-%d")
        app.text = app.text[:app.cursor] + s + app.text[app.cursor:]
        app.cursor += len(s)

    def _paint_clear(self, app):
        if app.canvas:
            app._push_snapshot()
            app.canvas.fill((255, 255, 255))

    # ---------- 窗口管理 ----------
    def focus(self, win):
        if win.minimized:
            win.minimized = False
        self.z_counter += 1
        win.z = self.z_counter
        self.active_win = win
        self.windows.sort(key=lambda w: w.z)

    def close_window(self, win):
        if not win.close(): return
        if win in self.windows:
            self.windows.remove(win)
        if self.active_win is win:
            self.active_win = self.windows[-1] if self.windows else None
            if self.active_win: self.focus(self.active_win)
        SND.min()

    def minimize(self, win):
        win.minimized = True
        if self.active_win is win:
            self.active_win = None
            for w in reversed(self.windows):
                if not w.minimized:
                    self.focus(w); break
        SND.min()

    def toggle_max(self, win):
        if win.maximized:
            win.rect = win.prev_rect
            win.maximized = False
        else:
            win.prev_rect = win.rect.copy()
            win.rect = pygame.Rect(0, 0, W, H - TASKBAR_H)
            win.maximized = True
        SND.max()

    def click_window_title(self, win):
        """连续点击同一标题栏触发无响应"""
        now = time.time()
        if self._last_click_target is win and now - self._last_click_t < 1.5:
            pass  # 同一窗口
        else:
            win.click_count = 0
        win.click_count += 1
        self._last_click_t = now
        self._last_click_target = win
        if win.click_count >= 5:
            win.responding = False
            win.freeze_timer = 999  # 持续冻结直到任务管理器结束
            win.click_count = 0
            SND.err()

    # ---------- 对话框 ----------
    def message(self, title, text, icon="ℹ️"):
        self.dialog = {'type': 'msg', 'title': title, 'text': text, 'icon': icon}
        SND.ding()

    def confirm(self, title, text):
        """同步风格确认框，返回 bool。简化为异步：用 dialog 队列"""
        self.dialog = {'type': 'confirm', 'title': title, 'text': text, 'icon': '❓', 'result': None}
        SND.ding()
        # 由于主循环驱动，我们返回 True（简化），实际由对话框处理
        return True

    def _shutdown(self):
        self.dialog = {'type': 'shutdown'}

    # ---------- 设置对话框（控制面板各项） ----------
    def settings_dialog(self, title, icon, groups):
        """groups: [(组标题, [option, ...]), ...]
        option:
          {'kind':'check', 'label':..., 'key':...}
          {'kind':'choice', 'label':..., 'key':..., 'choices':[...]}
          {'kind':'info', 'label':..., 'value':str或callable(data)->str}
          {'kind':'button', 'label':..., 'action':'reset'|'clearhistory'|...}
        """
        self.dialog = {'type': 'settings', 'title': title, 'icon': icon,
                       'groups': groups, 'data': dict(self.settings),
                       'btn': 0, 'scroll': 0, '_hits': []}
        SND.ding()

    def _apply_settings(self, data):
        old_wp = self.settings.get('wallpaper', 0)
        self.settings.update(data)
        # 真实生效的效果
        self.snd.enabled = not self.settings.get('mute', False)
        if self.settings.get('wallpaper', 0) != old_wp:
            self._wallpaper = self._make_wallpaper()

    # ---------- 右键菜单 ----------
    def show_context(self, pos, items):
        self.ctx_menu = {'items': items, 'pos': pos}

    # ---------- 链接注册 ----------
    def _register_link(self, rect, app_id):
        self._links.append((rect, app_id))

    # ---------- 主循环 ----------
    def run(self):
        running = True
        while running:
            dt = min(self.clock.tick(FPS) / 1000.0, 0.05)
            self.mouse = pygame.mouse.get_pos()
            self.cursor.update(dt)
            # 注意：_links 不在此处重置，保留上一帧注册的链接供事件处理使用，
            # 在 _render 之前重置以便重新注册。

            for ev in pygame.event.get():
                if ev.type == pygame.QUIT:
                    running = False
                elif ev.type == pygame.KEYDOWN:
                    if ev.key == pygame.K_LCTRL or ev.key == pygame.K_RCTRL:
                        pass
                    if (ev.key == pygame.K_DELETE and
                            (pygame.key.get_mods() & pygame.KMOD_CTRL) and
                            (pygame.key.get_mods() & pygame.KMOD_ALT)):
                        self.launch('taskmanager'); continue
                    if ev.key == pygame.K_ESCAPE:
                        if self.ctx_menu: self.ctx_menu = None; continue
                        if self.start_open: self.start_open = False; continue
                if self.phase == 'desktop':
                    self._handle_event(ev)
                elif self.phase == 'boot':
                    if ev.type == pygame.MOUSEBUTTONDOWN or ev.type == pygame.KEYDOWN:
                        pass  # 跳过启动
                elif self.phase == 'login':
                    self._handle_login(ev)
                elif self.phase == 'standby':
                    if ev.type in (pygame.MOUSEBUTTONDOWN, pygame.KEYDOWN, pygame.TEXTINPUT):
                        # 仅在已完全进入待机（黑屏）后才唤醒，避免误触
                        if self.standby_t > 1.0:
                            self._standby_waking = 0.6   # 唤醒淡入时长（秒）
                            self.phase = 'desktop'; SND.ding()
            self._update(dt)
            self._links = []   # 渲染前清空，由各应用 render 重新注册
            self._render()
            pygame.display.flip()
        pygame.quit()
        sys.exit()

    def _update(self, dt):
        if self.phase == 'boot':
            self.boot_t += dt
            self.boot_progress = min(100, self.boot_progress + dt * 28)
            if self.boot_progress >= 100 and self.boot_t > 3.5:
                self.phase = 'login'; self.login_t = 0; SND.startup()
        elif self.phase == 'login':
            self.login_t += dt
            # 不再自动进入桌面：必须由用户在登录界面点击用户名
            if self._login_msg and self._login_msg[1] > 0:
                self._login_msg = (self._login_msg[0], self._login_msg[1] - dt)
        elif self.phase == 'shutdown':
            self.shut_t += dt
            self.cursor.spin += dt * 6.0
            if self.shut_mode == 'restart' and self.shut_t > 2.8:
                # 重启：进入开机流程
                self.phase = 'boot'; self.boot_t = 0; self.boot_progress = 0
                self.shut_t = 0; self.windows.clear()
            elif self.shut_mode == 'off' and self.shut_t > 3.4:
                pygame.quit(); sys.exit()
        elif self.phase == 'standby':
            self.standby_t += dt
        # 唤醒淡入倒计时（desktop 阶段）
        if self._standby_waking > 0:
            self._standby_waking = max(0.0, self._standby_waking - dt)
        for w in self.windows:
            w.update(dt)

    def _handle_event(self, ev):
        # 对话框优先
        if self.dialog:
            self._handle_dialog(ev); return
        # 右键菜单
        if self.ctx_menu:
            self._handle_ctx(ev); return
        # 侧边栏链接（由各应用 render 注册，此处响应点击）
        if ev.type == pygame.MOUSEBUTTONDOWN and ev.button == 1 and self._links:
            for r, app_id in self._links:
                if app_id and r.collidepoint(self.mouse):
                    SND.click(); self.launch(app_id); return
        # 开始菜单打开时，点击其他地方关闭
        if self.start_open:
            # 先让开始菜单处理
            if self._handle_start(ev): return
        # 窗口事件（从顶层开始）
        if ev.type == pygame.MOUSEBUTTONDOWN:
            # 检查任务栏按钮
            if self._handle_taskbar(ev): return
            # 检查开始按钮
            if pygame.Rect(0, H - TASKBAR_H, 100, TASKBAR_H).collidepoint(self.mouse):
                if ev.button == 1:
                    self.start_open = not self.start_open; SND.click(); return
        # 窗口
        for w in reversed(self.windows):
            if w.minimized: continue
            if w.rect.collidepoint(self.mouse) or (w.menus and w.open_menu >= 0):
                if w.handle_event(ev):
                    self.focus(w)
                    return
        # 桌面
        if ev.type == pygame.MOUSEBUTTONDOWN:
            if ev.button == 1:
                self._handle_desktop_click(ev)
            elif ev.button == 3:
                self._handle_desktop_right(ev)
        elif ev.type == pygame.MOUSEMOTION:
            self.icon_selected = -1

    def _handle_desktop_click(self, ev):
        self.icon_selected = -1
        # 图标点击
        for i, (ic, name, app) in enumerate(self.icons):
            r = self._icon_rect(i)
            if r.collidepoint(self.mouse):
                self.icon_selected = i
                now = time.time()
                if hasattr(self, '_dlast') and self._dlast_i == i and now - self._dlast < 0.4:
                    self.launch(app); self._dlast = 0; return
                self._dlast = now; self._dlast_i = i
                SND.click(); return
        # 空白桌面
        self.start_open = False

    def _handle_desktop_right(self, ev):
        items = []
        for i, (ic, name, app) in enumerate(self.icons):
            r = self._icon_rect(i)
            if r.collidepoint(self.mouse):
                items = [
                    (f"打开", lambda a=app: self.launch(a), '📂', True),
                    ("-", None, '', True),
                    ("复制", lambda n=name, a=app: self._icon_copy(n, a), '📋', True),
                    ("删除", lambda idx=i, n=name: self._icon_delete(idx, n), '🗑️', True),
                    ("重命名", lambda idx=i, n=name: self._icon_rename(idx, n), '✏️', True),
                    ("-", None, '', True),
                    ("属性", lambda n=name, a=app, e=ic: self.message(n, f"类型：快捷方式\n目标：{a}\n位置：桌面", e), '⚙️', True),
                ]
                self.show_context(self.mouse, items); return
        # 桌面空白
        has_clip = hasattr(self, '_clipboard') and self._clipboard
        items = [
            ("排列图标", lambda: self._icons_arrange(), '🔄', True),
            ("刷新", lambda: SND.ding(), '🔄', True),
            ("-", None, '', True),
            ("粘贴", lambda: self._icon_paste(), '📋', has_clip),
            ("粘贴快捷方式", lambda: self._icon_paste(), '📋', has_clip),
            ("-", None, '', True),
            ("新建文本文档", lambda: self.launch('notepad'), '📝', True),
            ("新建位图图像", lambda: self.launch('paint'), '🎨', True),
            ("-", None, '', True),
            ("属性", lambda: self.launch('control-panel'), '⚙️', True),
        ]
        self.show_context(self.mouse, items)

    def _icon_paste(self):
        if not (hasattr(self, '_clipboard') and self._clipboard):
            self.message("桌面", "剪贴板为空。", "📋"); return
        _, name, app = self._clipboard
        # 若重名则加后缀
        existing = {n for _, n, _ in self.icons}
        new_name = name
        i = 2
        while new_name in existing:
            new_name = f"{name} ({i})"; i += 1
        # 复制图标（沿用同 emoji）
        emo = next((e for e, n, a in self.icons if n == name), '📄')
        self.icons.append((emo, new_name, app))
        self.message("桌面", f"已粘贴 “{new_name}”。", "📋")

    def _icon_copy(self, name, app):
        self._clipboard = ('icon', name, app)
        self.message("桌面", f"已复制 “{name}” 到剪贴板。\n（在桌面右键即可粘贴副本）", "📋")

    def _icon_delete(self, idx, name):
        if len(self.icons) <= 1:
            self.message("桌面", "至少需要保留一个图标。", "⚠️"); return
        del self.icons[idx]
        self.icon_selected = -1
        self.message("桌面", f"已将 “{name}” 移至回收站。", "🗑️")

    def _icon_rename(self, idx, name):
        self.dialog = {'type': 'rename', 'text': name, 'idx': idx, 'btn': 0}

    def _icons_arrange(self):
        # 按名称排序
        self.icons.sort(key=lambda x: x[1])
        self.message("桌面", "已按名称排列桌面图标。", "🔄")

    def _icon_apply_rename(self, idx, new_name):
        new_name = new_name.strip()
        if not new_name:
            self.message("桌面", "名称不能为空。", "⚠️"); return
        if not (0 <= idx < len(self.icons)):
            self.message("桌面", "找不到该图标。", "⚠️"); return
        ic, _, app = self.icons[idx]
        self.icons[idx] = (ic, new_name, app)
        SND.click()

    def _icon_rect(self, i):
        return pygame.Rect(10, 10 + i * 78, 80, 74)

    def _handle_taskbar(self, ev):
        if ev.type == pygame.MOUSEBUTTONDOWN and ev.button == 1:
            # 任务栏应用按钮
            apps_area = pygame.Rect(105, H - TASKBAR_H, W - 105 - 150, TASKBAR_H)
            if apps_area.collidepoint(self.mouse):
                bx = 108
                for w in self.windows:
                    br = pygame.Rect(bx, H - TASKBAR_H + 4, 140, 22)
                    w.taskbar_btn_rect = br
                    if br.collidepoint(self.mouse):
                        if w.minimized:
                            self.focus(w)
                        elif self.active_win is w:
                            self.minimize(w)
                        else:
                            self.focus(w)
                        SND.click(); return True
                    bx += 144
                return True
            # 系统托盘
            tray = pygame.Rect(W - 150, H - TASKBAR_H, 150, TASKBAR_H)
            if tray.collidepoint(self.mouse):
                # 音量图标
                if pygame.Rect(W - 140, H - 24, 16, 16).collidepoint(self.mouse):
                    self.snd.enabled = not self.snd.enabled
                    SND.click()
                    self.message("音量", f"音量已{'开启' if self.snd.enabled else '静音'}", "🔊")
                    return True
                # 时钟
                if pygame.Rect(W - 70, H - 24, 60, 16).collidepoint(self.mouse):
                    now = time.strftime("%Y年%m月%d日 %A %H:%M:%S")
                    self.message("日期和时间", now, "🕐"); return True
        return False

    def _handle_start(self, ev):
        sm = pygame.Rect(0, H - TASKBAR_H - 420, 380, 420)
        if ev.type == pygame.MOUSEBUTTONDOWN:
            if not sm.collidepoint(self.mouse) and not pygame.Rect(0, H - TASKBAR_H, 100, TASKBAR_H).collidepoint(self.mouse):
                self.start_open = False; return False
            if ev.button == 1 and sm.collidepoint(self.mouse):
                # 开始菜单项
                items = self._start_items()
                for r, lab, app, side in items:
                    if r.collidepoint(self.mouse):
                        SND.click(); self.start_open = False
                        if app: self.launch(app)
                        return True
                # 底部按钮
                self._start_footer_click()
                return True
        return False

    def _start_items(self):
        """返回 [(rect, label, app, side)]，rect 为屏幕绝对坐标"""
        res = []
        # 菜单左上角 (与 _render_start_menu 保持一致)
        my = H - TASKBAR_H - 420
        left = [
            ('🌐', 'Internet Explorer', 'ie'),
            ('📧', 'Outlook Express', 'outlook'),
            ('📝', '记事本', 'notepad'),
            ('🎨', '画图', 'paint'),
            ('🧮', '计算器', 'calc'),
            ('💣', '扫雷', 'minesweeper'),
            ('🎵', 'Windows Media Player', 'music'),
        ]
        right = [
            ('🖥️', '我的电脑', 'computer'),
            ('📁', '我的文档', 'my-documents'),
            ('🗑️', '回收站', 'recycle'),
            ('⚙️', '控制面板', 'control-panel'),
            ('🔍', '搜索', 'search'),
            ('❓', '帮助和支持', 'help'),
        ]
        x0 = 8; y0 = my + 64
        for ic, name, app in left:
            r = pygame.Rect(x0, y0, 180, 28)
            res.append((r, name, app, 'L')); y0 += 30
        # “运行...”按钮紧跟左侧项之后（与渲染位置一致）
        r = pygame.Rect(8, my + 64 + 7 * 30 + 6, 180, 28)
        res.append((r, '运行...', 'run', 'L'))
        x0 = 195; y0 = my + 64
        for ic, name, app in right:
            r = pygame.Rect(x0, y0, 175, 26)
            res.append((r, name, app, 'R')); y0 += 28
        return res

    def _start_footer_click(self):
        r1 = pygame.Rect(8, H - TASKBAR_H - 30, 100, 22)
        r2 = pygame.Rect(120, H - TASKBAR_H - 30, 130, 22)
        if r1.collidepoint(self.mouse):
            if self.confirm("注销 Windows", "确定要注销吗？"):
                SND.shutdown(); pygame.time.delay(400); self.phase = 'boot'; self.boot_t = 0; self.boot_progress = 0
                self.windows.clear()
        elif r2.collidepoint(self.mouse):
            self._shutdown()

    def _handle_ctx(self, ev):
        if ev.type == pygame.MOUSEBUTTONDOWN:
            mp = self.mouse
            items = self.ctx_menu['items']
            # 计算菜单大小
            ww = 160; hh = 4 + sum(5 if lab == '-' else 20 for lab, _, _, _ in items)
            pos = self.ctx_menu['pos']
            box = pygame.Rect(pos[0], pos[1], ww, hh)
            if box.collidepoint(mp):
                y = pos[1] + 2
                for lab, cb, ic, en in items:
                    if lab == '-': y += 5; continue
                    ir = pygame.Rect(pos[0], y, ww, 18)
                    if ir.collidepoint(mp) and en and cb:
                        self.ctx_menu = None; cb(); return
                    y += 20
            self.ctx_menu = None

    def _handle_dialog(self, ev):
        d = self.dialog
        if d['type'] == 'settings':
            data = d['data']
            if ev.type == pygame.MOUSEBUTTONDOWN and ev.button == 1:
                mp = self.mouse
                for rect, h in d.get('_hits', []):
                    if rect.collidepoint(mp):
                        SND.click()
                        kind = h[0]
                        if kind == 'check':
                            k = h[1]; data[k] = not data.get(k, False)
                        elif kind == 'prev':
                            k = h[1]; vals = h[2]; n = len(vals)
                            cur = data.get(k, vals[0] if vals else 0)
                            try: ci = vals.index(cur)
                            except ValueError: ci = 0
                            data[k] = vals[(ci - 1) % n]
                        elif kind == 'next':
                            k = h[1]; vals = h[2]; n = len(vals)
                            cur = data.get(k, vals[0] if vals else 0)
                            try: ci = vals.index(cur)
                            except ValueError: ci = 0
                            data[k] = vals[(ci + 1) % n]
                        elif kind == 'btn':
                            act = h[1]
                            if act == 'clearhistory':
                                self.message("Internet 选项", "已成功清除历史记录。", "🌐")
                        elif kind == 'ok':
                            self._apply_settings(data); self.dialog = None
                        elif kind == 'cancel':
                            self.dialog = None
                        elif kind == 'apply':
                            self._apply_settings(data)
                        return
            elif ev.type == pygame.MOUSEWHEEL:
                d['scroll'] = max(0, d.get('scroll', 0) - ev.y * 24)
            return
        if d['type'] == 'shutdown':
            if ev.type == pygame.MOUSEBUTTONDOWN and ev.button == 1:
                mp = self.mouse
                bw, bh = 360, 220
                bx, by = (W - bw) // 2, (H - bh) // 2
                # 按钮
                for i, lab in enumerate(['待机', '关闭', '重新启动']):
                    r = pygame.Rect(bx + 30 + i * 105, by + bh - 60, 90, 30)
                    if r.collidepoint(mp):
                        SND.click()
                        if lab == '关闭':
                            self.dialog = None; self.phase = 'shutdown'; self.shut_t = 0; self.shut_mode = 'off'; SND.shutdown()
                        elif lab == '重新启动':
                            self.dialog = None; self.phase = 'shutdown'; self.shut_t = 0; self.shut_mode = 'restart'; SND.shutdown(); self.windows.clear()
                        else:  # 待机
                            self.dialog = None; self.phase = 'standby'; self.standby_t = 0
                            self._standby_snap = self.screen.copy(); self._standby_waking = 0.0; SND.min()
                        return
                r = pygame.Rect(bx + bw - 30, by + 8, 22, 20)
                if r.collidepoint(mp):
                    self.dialog = None; SND.click()
            return
        if d['type'] == 'run':
            if ev.type == pygame.TEXTINPUT and ev.text:
                d['text'] += ev.text; return
            if ev.type == pygame.KEYDOWN:
                if ev.key == pygame.K_BACKSPACE: d['text'] = d['text'][:-1]; return
                if ev.key == pygame.K_RETURN:
                    t = d['text'].lower().strip()
                    self.dialog = None
                    if t in ('notepad', '记事本'): self.launch('notepad')
                    elif t in ('calc', '计算器'): self.launch('calc')
                    elif t in ('mspaint', '画图'): self.launch('paint')
                    elif t in ('explorer', '我的电脑'): self.launch('computer')
                    elif t in ('taskmgr', '任务管理器'): self.launch('taskmanager')
                    elif t in ('winmine', '扫雷'): self.launch('minesweeper')
                    elif t: self.message("运行", f"找不到 '{d['text']}'。请检查文件名后重试。", "⚠️")
                    return
                if ev.key == pygame.K_ESCAPE: self.dialog = None; return
            if ev.type == pygame.MOUSEBUTTONDOWN and ev.button == 1:
                mp = self.mouse
                bw, bh = 380, 160
                bx, by = (W - bw) // 2, (H - bh) // 2
                # OK / Cancel
                r1 = pygame.Rect(bx + bw - 170, by + bh - 38, 75, 24)
                r2 = pygame.Rect(bx + bw - 85, by + bh - 38, 75, 24)
                if r1.collidepoint(mp):
                    self.dialog = None
                    t = d['text'].lower().strip()
                    if t in ('notepad', '记事本'): self.launch('notepad')
                    elif t in ('calc', '计算器'): self.launch('calc')
                    elif t in ('mspaint', '画图'): self.launch('paint')
                    elif t in ('explorer', '我的电脑'): self.launch('computer')
                    elif t in ('taskmgr', '任务管理器'): self.launch('taskmanager')
                    elif t in ('winmine', '扫雷'): self.launch('minesweeper')
                    elif t: self.message("运行", f"找不到 '{d['text']}'。", "⚠️")
                    return
                if r2.collidepoint(mp): self.dialog = None; return
            return
        if d['type'] == 'search':
            if ev.type == pygame.TEXTINPUT and ev.text:
                d['text'] += ev.text
                d['results'] = self._search_apps(d['text']); d['sel'] = -1
                return
            if ev.type == pygame.KEYDOWN:
                if ev.key == pygame.K_BACKSPACE:
                    d['text'] = d['text'][:-1]
                    d['results'] = self._search_apps(d['text']); d['sel'] = -1
                    return
                if ev.key == pygame.K_RETURN:
                    if d['results']:
                        self.dialog = None
                        self.launch(d['results'][0][2])
                    return
                if ev.key == pygame.K_ESCAPE: self.dialog = None; return
            if ev.type == pygame.MOUSEBUTTONDOWN and ev.button == 1:
                mp = self.mouse
                for r, app in d.get('_res_hits', []):
                    if r.collidepoint(mp):
                        SND.click(); self.dialog = None; self.launch(app); return
                bw, bh = 420, 320
                bx, by = (W - bw) // 2, (H - bh) // 2
                r_cancel = pygame.Rect(bx + bw - 85, by + bh - 38, 75, 24)
                r_search = pygame.Rect(bx + bw - 170, by + bh - 38, 75, 24)
                if r_search.collidepoint(mp):
                    SND.click(); d['results'] = self._search_apps(d['text']); return
                if r_cancel.collidepoint(mp): self.dialog = None; return
            return
        if d['type'] == 'rename':
            if ev.type == pygame.TEXTINPUT and ev.text:
                d['text'] += ev.text; return
            if ev.type == pygame.KEYDOWN:
                if ev.key == pygame.K_BACKSPACE: d['text'] = d['text'][:-1]; return
                if ev.key == pygame.K_RETURN:
                    self._icon_apply_rename(d['idx'], d['text']); self.dialog = None; return
                if ev.key == pygame.K_ESCAPE: self.dialog = None; return
            if ev.type == pygame.MOUSEBUTTONDOWN and ev.button == 1:
                mp = self.mouse
                bw, bh = 360, 160
                bx, by = (W - bw) // 2, (H - bh) // 2
                r_ok = pygame.Rect(bx + bw - 170, by + bh - 38, 75, 24)
                r_cancel = pygame.Rect(bx + bw - 85, by + bh - 38, 75, 24)
                if r_ok.collidepoint(mp):
                    SND.click(); self._icon_apply_rename(d['idx'], d['text']); self.dialog = None; return
                if r_cancel.collidepoint(mp): self.dialog = None; return
            return
        # msg / confirm
        if ev.type == pygame.MOUSEBUTTONDOWN and ev.button == 1:
            mp = self.mouse
            bw, bh = 360, 180
            bx, by = (W - bw) // 2, (H - bh) // 2
            if d['type'] == 'msg':
                r = pygame.Rect(bx + bw // 2 - 40, by + bh - 50, 80, 26)
                if r.collidepoint(mp): self.dialog = None; SND.click()
            elif d['type'] == 'confirm':
                r1 = pygame.Rect(bx + bw // 2 - 90, by + bh - 50, 75, 26)
                r2 = pygame.Rect(bx + bw // 2 + 15, by + bh - 50, 75, 26)
                if r1.collidepoint(mp): self.dialog = None; SND.click()
                elif r2.collidepoint(mp): self.dialog = None; SND.click()

    # ---------- 渲染 ----------
    def _render(self):
        if self.phase == 'boot':
            self._render_boot()
        elif self.phase == 'login':
            self._render_login()
        elif self.phase == 'desktop':
            self._render_desktop()
            # 待机唤醒淡入：从黑屏渐显回桌面
            if self._standby_waking > 0:
                a = int(255 * (self._standby_waking / 0.6))
                ov = pygame.Surface((W, H)); ov.fill((0, 0, 0)); ov.set_alpha(a)
                self.screen.blit(ov, (0, 0))
        elif self.phase == 'shutdown':
            self._render_shutdown()
        elif self.phase == 'standby':
            self._render_standby()

    def _render_boot(self):
        self.screen.fill((0, 0, 0))
        self.screen.blit(self._boot_logo, ((W - 340) // 2, H // 2 - 80))
        # 进度条
        pr = pygame.Rect((W - 220) // 2, H // 2 + 50, 220, 16)
        pygame.draw.rect(self.screen, (30, 30, 30), pr)
        pygame.draw.rect(self.screen, (80, 80, 80), pr, 1)
        pw = int(pr.w * self.boot_progress / 100)
        if pw > 0:
            g = hgrad(pw, pr.h, [(0, (0, 51, 153)), (0.5, (0, 102, 204)), (1, (0, 51, 153))])
            self.screen.blit(g, pr.topleft)
            # 滑动高光
            sx = int((self.boot_t * 200) % (pw + 30)) - 30
            if 0 <= sx < pw:
                hl = pygame.Surface((30, pr.h), pygame.SRCALPHA)
                hl.fill((255, 255, 255, 80))
                self.screen.blit(hl, (pr.x + sx, pr.y))
        t = font(11).render("正在启动 Microsoft® Windows®", True, (200, 200, 200))
        self.screen.blit(t, ((W - t.get_width()) // 2, pr.bottom + 12))
        # 版权
        c = font(10).render("Copyright © 1985-2001 Microsoft Corporation", True, (110, 110, 110))
        self.screen.blit(c, (40, H - 60))
        # 旋转加载光标
        self.cursor.state = self.cursor.BUSY
        self.cursor.draw(self.screen, self.mouse)

    def _render_login(self):
        # 背景
        g = vgrad(W, H, (90, 126, 214), (58, 91, 176))
        self.screen.blit(g, (0, 0))
        # 顶部横幅
        banner = pygame.Rect(0, 0, W, 120)
        bg = vgrad(W, banner.h, (232, 232, 240), (160, 160, 184))
        self.screen.blit(bg, banner.topleft)
        self.screen.blit(self._boot_logo, (60, 20))
        t = font(20, bold=True).render("要开始，请单击您的用户名", True, (0, 51, 153))
        self.screen.blit(t, (420, 40))
        t2 = font(12).render("登录后，您可以添加或更改账户。", True, (80, 80, 100))
        self.screen.blit(t2, (420, 70))
        # 用户列表
        self._login_users = []
        uy = 180
        for i, (name, status, enabled) in enumerate([
            ("Administrator", "已登录", True),
            ("Guest", "来宾账户已关闭", False),
        ]):
            r = pygame.Rect(W // 2 - 130, uy + i * 90, 260, 70)
            self._login_users.append((r, name, enabled))
            hot = r.collidepoint(self.mouse) and enabled
            if i == 0:
                pygame.draw.rect(self.screen, (200, 215, 245), r, border_radius=4)
                pygame.draw.rect(self.screen, (0, 51, 153), r, 2, border_radius=4)
            if hot:
                s = pygame.Surface((r.w, r.h), pygame.SRCALPHA)
                s.fill((255, 255, 255, 40))
                self.screen.blit(s, r.topleft)
                pygame.draw.rect(self.screen, (255, 220, 120), r, 2, border_radius=4)
            # 头像
            ar = pygame.Rect(r.x + 10, r.y + 10, 50, 50)
            pygame.draw.rect(self.screen, (255, 255, 255), ar)
            pygame.draw.rect(self.screen, (100, 100, 100), ar, 2)
            self.screen.blit(font(30).render("👤", True, (0, 0, 0)), (ar.x + 8, ar.y + 6))
            name_col = (255, 255, 255) if enabled else (180, 180, 200)
            self.screen.blit(font(14, bold=True).render(name, True, name_col), (r.x + 70, r.y + 18))
            self.screen.blit(font(11).render(status, True, (200, 210, 230)), (r.x + 70, r.y + 40))
            if hot:
                tip = font(10).render("单击登录", True, (255, 240, 180))
                self.screen.blit(tip, (r.x + 70, r.y + 56))
        # 底部提示 + 关机按钮
        bt = font(10).render("登录后，您可以添加或更改账户。只需转到控制面板并单击用户账户。", True, (200, 200, 220))
        self.screen.blit(bt, (60, H - 80))
        # 关机按钮（左下角）
        pwr = pygame.Rect(60, H - 50, 130, 28)
        self._login_pwr_rect = pwr
        hot = pwr.collidepoint(self.mouse)
        col = (90, 90, 120) if not hot else (60, 60, 90)
        pygame.draw.rect(self.screen, col, pwr, border_radius=4)
        pygame.draw.rect(self.screen, (200, 200, 220), pwr, 1, border_radius=4)
        self.screen.blit(font(11).render("⏻ 关闭计算机", True, (255, 255, 255)), (pwr.x + 12, pwr.y + 8))
        # 临时提示消息（如 Guest 已禁用）
        msg = getattr(self, '_login_msg', None)
        if msg and msg[1] > 0:
            text = msg[0]
            t = font(11).render(text, True, (255, 220, 180))
            bw = t.get_width() + 24; bh = 24
            mr = pygame.Rect((W - bw) // 2, H - 100, bw, bh)
            pygame.draw.rect(self.screen, (120, 30, 30), mr, border_radius=4)
            pygame.draw.rect(self.screen, (255, 180, 180), mr, 1, border_radius=4)
            self.screen.blit(t, (mr.x + 12, mr.y + 5))
        self.cursor.state = self.cursor.ARROW
        self.cursor.draw(self.screen, self.mouse)

    def _handle_login(self, ev):
        if ev.type == pygame.MOUSEBUTTONDOWN and ev.button == 1:
            mp = self.mouse
            # 用户点击
            for r, name, enabled in getattr(self, '_login_users', []):
                if r.collidepoint(mp):
                    if not enabled:
                        SND.err()
                        self._login_msg = ("来宾账户已被禁用，请联系系统管理员。", 2.5)
                        return True
                    SND.click()
                    self.settings['account_name'] = name
                    self.phase = 'desktop'; SND.ding()
                    return True
            # 关机按钮
            pwr = getattr(self, '_login_pwr_rect', None)
            if pwr and pwr.collidepoint(mp):
                SND.click(); self.phase = 'shutdown'; self.shut_t = 0; self.shut_mode = 'off'; SND.shutdown()
                return True
        elif ev.type == pygame.KEYDOWN:
            # 回车/空格直接以 Administrator 登录；Esc 关机
            if ev.key in (pygame.K_RETURN, pygame.K_SPACE, pygame.K_KP_ENTER):
                SND.click(); self.phase = 'desktop'; SND.ding(); return True
            if ev.key == pygame.K_ESCAPE:
                SND.click(); self.phase = 'shutdown'; self.shut_t = 0; self.shut_mode = 'off'; SND.shutdown()
                return True
        return False

    def _render_desktop(self):
        self.screen.blit(self._wallpaper, (0, 0))
        # 桌面图标
        for i, (ic, name, app) in enumerate(self.icons):
            r = self._icon_rect(i)
            sel = (self.icon_selected == i)
            hot = r.collidepoint(self.mouse)
            if sel:
                pygame.draw.rect(self.screen, (49, 106, 197), r, border_radius=2)
                pygame.draw.rect(self.screen, (49, 106, 197), r, 1, border_radius=2)
            elif hot:
                s = pygame.Surface((r.w, r.h), pygame.SRCALPHA)
                s.fill((49, 106, 197, 60))
                self.screen.blit(s, r.topleft)
            self.screen.blit(font(28).render(ic, True, (255, 255, 255)), (r.x + (r.w - 28) // 2, r.y + 4))
            # 文字带阴影
            for line in self._wrap(name, r.w - 8):
                pass
            self._draw_icon_label(self.screen, name, r)
        # 窗口（按 z 序）
        for w in self.windows:
            w.render(self.screen)
        # 任务栏
        self._render_taskbar()
        # 开始菜单
        if self.start_open:
            self._render_start_menu()
        # 右键菜单
        if self.ctx_menu:
            self._render_context()
        # 对话框
        if self.dialog:
            self._render_dialog()
        # 光标状态
        self._update_cursor_state()
        self.cursor.draw(self.screen, self.mouse)

    def _draw_icon_label(self, surf, name, r):
        f = font(10)
        # 简单换行
        maxw = r.w - 4
        lines = []; line = ''
        for ch in name:
            if f.size(line + ch)[0] > maxw:
                lines.append(line); line = ch
            else: line += ch
        if line: lines.append(line)
        y = r.y + 38
        for ln in lines:
            t = f.render(ln, True, (255, 255, 255))
            sh = f.render(ln, True, (0, 0, 0))
            surf.blit(sh, (r.x + (r.w - t.get_width()) // 2 + 1, y + 1))
            surf.blit(t, (r.x + (r.w - t.get_width()) // 2, y))
            y += 12

    def _wrap(self, text, maxw):
        f = font(10); line = ''; lines = []
        for ch in text:
            if f.size(line + ch)[0] > maxw: lines.append(line); line = ch
            else: line += ch
        if line: lines.append(line)
        return lines

    def _render_taskbar(self):
        tb = pygame.Rect(0, H - TASKBAR_H, W, TASKBAR_H)
        g = vgrad(W, TASKBAR_H, (43, 87, 151), (30, 63, 122))
        self.screen.blit(g, tb.topleft)
        pygame.draw.line(self.screen, (10, 36, 106), (0, tb.y), (W, tb.y))
        # 开始按钮
        sb = pygame.Rect(0, tb.y, 100, TASKBAR_H)
        sgrad = vgrad(sb.w, sb.h, C['green'], C['green_d'])
        self.screen.blit(sgrad, sb.topleft)
        pygame.draw.line(self.screen, (120, 200, 120), (sb.right - 1, sb.y), (sb.right - 1, sb.bottom))
        # 旗帜
        for i, col in enumerate([(232, 67, 0), (255, 184, 0), (0, 160, 227), (60, 160, 71)]):
            x = 8 + (i % 2) * 10; y = 7 + (i // 2) * 10
            quad = [(x, y), (x + 9, y - 2), (x + 9, y + 8), (x, y + 9)]
            pygame.draw.polygon(self.screen, col, quad)
        self.screen.blit(font(14, bold=True).render("开始", True, (255, 255, 255)), (32, tb.y + 7))
        # 应用按钮
        bx = 108
        for w in self.windows:
            br = pygame.Rect(bx, tb.y + 4, 140, 22)
            w.taskbar_btn_rect = br
            active = (self.active_win is w and not w.minimized)
            hot = br.collidepoint(self.mouse)
            if active:
                g2 = vgrad(br.w, br.h, (60, 123, 212), (43, 90, 160))
            elif hot:
                g2 = vgrad(br.w, br.h, (76, 139, 228), (59, 106, 176))
            else:
                g2 = vgrad(br.w, br.h, (60, 123, 212), (43, 90, 160))
            self.screen.blit(g2, br.topleft)
            pygame.draw.rect(self.screen, (10, 36, 106), br, 1)
            self.screen.blit(font(11).render(w.icon, True, (255, 255, 255)), (br.x + 4, br.y + 4))
            label = w.title if len(w.title) < 14 else w.title[:13] + '…'
            if not w.responding: label = '(没有响应) ' + label
            self.screen.blit(font(10).render(label, True, (255, 255, 255)), (br.x + 22, br.y + 6))
            bx += 144
            if bx > W - 200: break
        # 系统托盘
        tray = pygame.Rect(W - 150, tb.y, 150, TASKBAR_H)
        tg = vgrad(tray.w, tray.h, (18, 144, 233), (16, 112, 192))
        self.screen.blit(tg, tray.topleft)
        pygame.draw.line(self.screen, (10, 36, 106), (tray.x, tray.y), (tray.x, tray.bottom))
        self.screen.blit(font(11).render("🔊", True, (255, 255, 255)), (tray.x + 8, tb.y + 7))
        self.screen.blit(font(11).render("📶", True, (255, 255, 255)), (tray.x + 30, tb.y + 7))
        self.screen.blit(font(11).render("🛡️", True, (255, 255, 255)), (tray.x + 52, tb.y + 7))
        now = time.strftime("%H:%M")
        t = font(11).render(now, True, (255, 255, 255))
        self.screen.blit(t, (tray.right - t.get_width() - 8, tb.y + 8))

    def _render_start_menu(self):
        mw, mh = 380, 420
        my = H - TASKBAR_H - mh
        # 阴影
        sh = pygame.Surface((mw + 6, mh + 6), pygame.SRCALPHA)
        pygame.draw.rect(sh, (0, 0, 0, 80), (3, 3, mw, mh))
        self.screen.blit(sh, (0 - 3, my - 3))
        # 主体
        body = pygame.Rect(0, my, mw, mh)
        pygame.draw.rect(self.screen, (255, 255, 255), body)
        pygame.draw.rect(self.screen, (8, 49, 217), body, 1)
        # 头部
        head = pygame.Rect(0, my, mw, 54)
        hg = vgrad(mw, 54, (21, 82, 176), (10, 61, 128))
        self.screen.blit(hg, head.topleft)
        pygame.draw.rect(self.screen, C['orange'], (0, my + 52, mw, 2))
        # 头像
        ar = pygame.Rect(12, my + 7, 40, 40)
        pygame.draw.rect(self.screen, (232, 232, 216), ar)
        pygame.draw.rect(self.screen, (255, 255, 255), ar, 2)
        self.screen.blit(font(24).render("👤", True, (0, 0, 0)), (ar.x + 6, ar.y + 6))
        self.screen.blit(font(13, bold=True).render("Administrator", True, (255, 255, 255)), (60, my + 18))
        # 左侧
        left = [
            ('🌐', 'Internet Explorer', 'ie'),
            ('📧', 'Outlook Express', 'outlook'),
            ('📝', '记事本', 'notepad'),
            ('🎨', '画图', 'paint'),
            ('🧮', '计算器', 'calc'),
            ('💣', '扫雷', 'minesweeper'),
            ('🎵', 'Windows Media Player', 'music'),
        ]
        x0 = 8; y0 = my + 64
        for ic, name, app in left:
            r = pygame.Rect(x0, y0, 180, 28)
            hot = r.collidepoint(self.mouse)
            if hot:
                g = hgrad(r.w, r.h, [(0, (47, 113, 205)), (1, (25, 86, 181))])
                self.screen.blit(g, r.topleft)
                tc = (255, 255, 255)
            else: tc = C['text']
            self.screen.blit(font(15).render(ic, True, (0, 0, 0) if not hot else (255, 255, 255)), (r.x + 6, r.y + 5))
            self.screen.blit(font(12, bold=True).render(name, True, tc), (r.x + 32, r.y + 8))
            y0 += 30
        # 分隔
        pygame.draw.line(self.screen, (181, 200, 232), (8, y0 + 2), (188, y0 + 2))
        # 运行
        r = pygame.Rect(x0, y0 + 6, 180, 28)
        hot = r.collidepoint(self.mouse)
        if hot:
            g = hgrad(r.w, r.h, [(0, (47, 113, 205)), (1, (25, 86, 181))])
            self.screen.blit(g, r.topleft); tc = (255, 255, 255)
        else: tc = C['text']
        self.screen.blit(font(14).render("▶️", True, tc), (r.x + 6, r.y + 6))
        self.screen.blit(font(12).render("运行...", True, tc), (r.x + 32, r.y + 8))
        # 右侧
        right_bg = pygame.Rect(190, my + 54, 190, mh - 54 - 30)
        rb = vgrad(right_bg.w, right_bg.h, (211, 229, 250), (180, 206, 240))
        self.screen.blit(rb, right_bg.topleft)
        pygame.draw.line(self.screen, (181, 200, 232), (right_bg.x, right_bg.y), (right_bg.x, right_bg.bottom))
        right = [
            ('🖥️', '我的电脑', 'computer'),
            ('📁', '我的文档', 'my-documents'),
            ('🗑️', '回收站', 'recycle'),
            ('⚙️', '控制面板', 'control-panel'),
            ('🔍', '搜索', 'search'),
            ('❓', '帮助和支持', 'help'),
        ]
        x0 = 195; y0 = my + 64
        for ic, name, app in right:
            r = pygame.Rect(x0, y0, 175, 26)
            hot = r.collidepoint(self.mouse)
            if hot:
                g = hgrad(r.w, r.h, [(0, (47, 113, 205)), (1, (25, 86, 181))])
                self.screen.blit(g, r.topleft); tc = (255, 255, 255)
            else: tc = (0, 51, 153)
            self.screen.blit(font(13).render(ic, True, (0, 0, 0) if not hot else (255, 255, 255)), (r.x + 6, r.y + 5))
            self.screen.blit(font(11).render(name, True, tc), (r.x + 30, r.y + 7))
            y0 += 28
        # 底部
        foot = pygame.Rect(0, my + mh - 30, mw, 30)
        fg = vgrad(mw, 30, (21, 82, 176), (10, 61, 128))
        self.screen.blit(fg, foot.topleft)
        # 注销
        r1 = pygame.Rect(8, foot.y + 4, 100, 22)
        hot = r1.collidepoint(self.mouse)
        if hot: pygame.draw.rect(self.screen, (47, 113, 205), r1, border_radius=3)
        self.screen.blit(font(12).render("🔒 注销", True, (255, 255, 255)), (r1.x + 8, r1.y + 4))
        # 关闭
        r2 = pygame.Rect(120, foot.y + 4, 130, 22)
        hot = r2.collidepoint(self.mouse)
        if hot: pygame.draw.rect(self.screen, (200, 60, 50), r2, border_radius=3)
        self.screen.blit(font(12).render("⏻ 关闭计算机", True, (255, 255, 255)), (r2.x + 8, r2.y + 4))

    def _render_context(self):
        items = self.ctx_menu['items']
        f = font(11)
        ww = 170
        hh = 4
        meas = []
        for lab, cb, ic, en in items:
            if lab == '-': meas.append(('sep',)); hh += 5
            else: meas.append((lab,)); hh += 20
        pos = self.ctx_menu['pos']
        px = min(pos[0], W - ww - 4); py = min(pos[1], H - hh - TASKBAR_H - 4)
        # 阴影
        sh = pygame.Surface((ww + 6, hh + 6), pygame.SRCALPHA)
        pygame.draw.rect(sh, (0, 0, 0, 80), (3, 3, ww, hh))
        self.screen.blit(sh, (px - 3, py - 3))
        pygame.draw.rect(self.screen, C['win_bg'], (px, py, ww, hh))
        pygame.draw.rect(self.screen, C['btn_border'], (px, py, ww, hh), 1)
        y = py + 2
        mp = self.mouse
        for i, m in enumerate(meas):
            if m[0] == 'sep':
                pygame.draw.line(self.screen, C['sb_border'], (px + 4, y + 2), (px + ww - 4, y + 2))
                y += 5
            else:
                lab, cb, ic, en = items[i]
                ir = pygame.Rect(px, y, ww, 18)
                hot = ir.collidepoint(mp) and en
                if hot:
                    pygame.draw.rect(self.screen, C['menu_hi'], ir)
                    tc = (255, 255, 255)
                else:
                    tc = C['text'] if en else C['text_dis']
                if ic:
                    self.screen.blit(font(12).render(ic, True, tc), (px + 5, y + 2))
                self.screen.blit(f.render(lab, True, tc), (px + 28, y + 3))
                y += 20

    def _render_dialog(self):
        d = self.dialog
        # 半透明遮罩
        ov = pygame.Surface((W, H), pygame.SRCALPHA)
        ov.fill((0, 0, 0, 40))
        self.screen.blit(ov, (0, 0))
        if d['type'] == 'shutdown':
            self._render_shutdown_dialog(); return
        if d['type'] == 'run':
            self._render_run_dialog(); return
        if d['type'] == 'search':
            self._render_search_dialog(); return
        if d['type'] == 'rename':
            self._render_rename_dialog(); return
        if d['type'] == 'settings':
            self._render_settings_dialog(); return
        # msg / confirm
        bw, bh = 380, 180
        bx, by = (W - bw) // 2, (H - bh) // 2
        title = d.get('title', 'Windows')
        text = d.get('text', '')
        icon = d.get('icon', 'ℹ️')
        # 阴影
        sh = pygame.Surface((bw + 8, bh + 8), pygame.SRCALPHA)
        pygame.draw.rect(sh, (0, 0, 0, 90), (4, 4, bw, bh), border_radius=8)
        self.screen.blit(sh, (bx - 4, by - 4))
        pygame.draw.rect(self.screen, C['win_border'], (bx, by, bw, bh), border_radius=8)
        pygame.draw.rect(self.screen, C['win_bg'], (bx + 1, by + 1, bw - 2, bh - 2))
        # 标题栏
        tb = pygame.Rect(bx, by, bw, 26)
        draw_title_bar(self.screen, tb, icon, title)
        # 内容
        ix = bx + 20; iy = by + 40
        self.screen.blit(font(40).render(icon, True, (0, 0, 0)), (ix, iy))
        tx = ix + 56
        ty = iy
        for line in text.split('\n'):
            self.screen.blit(font(12).render(line, True, C['text']), (tx, ty))
            ty += 18
        # 按钮
        if d['type'] == 'msg':
            r = pygame.Rect(bx + bw // 2 - 40, by + bh - 42, 80, 24)
            hot = r.collidepoint(self.mouse)
            draw_button(self.screen, r, "确定", hover=hot)
        elif d['type'] == 'confirm':
            r1 = pygame.Rect(bx + bw // 2 - 90, by + bh - 42, 75, 24)
            r2 = pygame.Rect(bx + bw // 2 + 15, by + bh - 42, 75, 24)
            draw_button(self.screen, r1, "是", hover=r1.collidepoint(self.mouse))
            draw_button(self.screen, r2, "否", hover=r2.collidepoint(self.mouse))

    def _render_settings_dialog(self):
        d = self.dialog
        hits = []; d['_hits'] = hits
        bw, bh = 540, 420
        bx, by = (W - bw) // 2, (H - bh) // 2
        sh = pygame.Surface((bw + 8, bh + 8), pygame.SRCALPHA)
        pygame.draw.rect(sh, (0, 0, 0, 90), (4, 4, bw, bh), border_radius=8)
        self.screen.blit(sh, (bx - 4, by - 4))
        pygame.draw.rect(self.screen, C['win_border'], (bx, by, bw, bh), border_radius=8)
        pygame.draw.rect(self.screen, C['win_bg'], (bx + 1, by + 1, bw - 2, bh - 2))
        tb = pygame.Rect(bx, by, bw, 26)
        draw_title_bar(self.screen, tb, d.get('icon', '⚙️'), d.get('title', '设置'))
        # 内容区（裁剪 + 滚动）
        content = pygame.Rect(bx + 1, by + 27, bw - 2, bh - 27 - 34)
        self.screen.set_clip(content)
        data = d['data']
        scroll = d.get('scroll', 0)
        y = by + 36 - scroll
        for glabel, opts in d['groups']:
            # 组标题
            if y > by + 26 and y < content.bottom:
                self.screen.blit(font(11, bold=True).render(glabel, True, (0, 51, 153)), (bx + 16, y))
            y += 20
            for opt in opts:
                row = pygame.Rect(bx + 16, y, bw - 32, 22)
                kind = opt['kind']
                if kind == 'check':
                    k = opt['key']; on = bool(data.get(k, False))
                    cb = pygame.Rect(row.x, row.y + 3, 14, 14)
                    pygame.draw.rect(self.screen, (255, 255, 255), cb)
                    pygame.draw.rect(self.screen, (100, 120, 150), cb, 1)
                    if on:
                        pygame.draw.line(self.screen, (0, 0, 0), (cb.x + 3, cb.y + 7), (cb.x + 6, cb.y + 10), 2)
                        pygame.draw.line(self.screen, (0, 0, 0), (cb.x + 6, cb.y + 10), (cb.x + 11, cb.y + 4), 2)
                    if row.bottom > by + 26 and row.y < content.bottom:
                        self.screen.blit(font(11).render(opt['label'], True, C['text']), (cb.right + 6, row.y + 3))
                    hits.append((pygame.Rect(cb.x, max(cb.y, content.top), cb.w, min(cb.bottom, content.bottom) - max(cb.y, content.top)) if cb.bottom > content.top and cb.y < content.bottom else pygame.Rect(0,0,0,0), ('check', k)))
                elif kind == 'choice':
                    k = opt['key']; choices = opt['choices']
                    values = opt.get('values', choices); n = len(values)
                    cur = data.get(k, values[0] if values else 0)
                    try: idx = values.index(cur)
                    except ValueError: idx = 0
                    if row.bottom > by + 26 and row.y < content.bottom:
                        self.screen.blit(font(11).render(opt['label'], True, C['text']), (row.x, row.y + 3))
                    vr = pygame.Rect(row.right - 150, row.y + 1, 150, 20)
                    if row.bottom > by + 26 and row.y < content.bottom:
                        pygame.draw.rect(self.screen, (255, 255, 255), vr)
                        pygame.draw.rect(self.screen, C['btn_border'], vr, 1)
                        self.screen.blit(font(11).render(str(choices[idx]), True, C['text']), (vr.x + 6, vr.y + 3))
                    # 左右箭头按钮
                    lh = pygame.Rect(vr.x, vr.y, 18, vr.h)
                    rh = pygame.Rect(vr.right - 18, vr.y, 18, vr.h)
                    if row.bottom > by + 26 and row.y < content.bottom:
                        if lh.collidepoint(self.mouse): pygame.draw.rect(self.screen, (220, 225, 245), lh)
                        if rh.collidepoint(self.mouse): pygame.draw.rect(self.screen, (220, 225, 245), rh)
                        pygame.draw.line(self.screen, C['text'], (lh.centerx - 3, lh.centery), (lh.centerx + 3, lh.centery - 4), 2)
                        pygame.draw.line(self.screen, C['text'], (lh.centerx - 3, lh.centery), (lh.centerx + 3, lh.centery + 4), 2)
                        pygame.draw.line(self.screen, C['text'], (rh.centerx + 3, rh.centery), (rh.centerx - 3, rh.centery - 4), 2)
                        pygame.draw.line(self.screen, C['text'], (rh.centerx + 3, rh.centery), (rh.centerx - 3, rh.centery + 4), 2)
                        hits.append((lh, ('prev', k, values))); hits.append((rh, ('next', k, values)))
                elif kind == 'info':
                    val = opt.get('value', '')
                    if callable(val): val = val(data)
                    if row.bottom > by + 26 and row.y < content.bottom:
                        self.screen.blit(font(11).render(opt['label'], True, C['text']), (row.x, row.y + 3))
                        t = font(11).render(str(val), True, (90, 90, 90))
                        self.screen.blit(t, (row.right - 6 - t.get_width(), row.y + 3))
                elif kind == 'button':
                    br = pygame.Rect(row.x, row.y + 1, 120, 20)
                    if row.bottom > by + 26 and row.y < content.bottom:
                        draw_button(self.screen, br, opt['label'], hover=br.collidepoint(self.mouse))
                    hits.append((br, ('btn', opt.get('action', ''))))
                y += 24
            y += 8
        self.screen.set_clip(None)
        # 底部按钮
        by2 = by + bh - 34
        r_ok = pygame.Rect(bx + bw - 270, by2, 80, 24)
        r_cancel = pygame.Rect(bx + bw - 180, by2, 80, 24)
        r_apply = pygame.Rect(bx + bw - 90, by2, 80, 24)
        draw_button(self.screen, r_ok, "确定", hover=r_ok.collidepoint(self.mouse))
        draw_button(self.screen, r_cancel, "取消", hover=r_cancel.collidepoint(self.mouse))
        draw_button(self.screen, r_apply, "应用", hover=r_apply.collidepoint(self.mouse))
        hits.append((r_ok, ('ok',))); hits.append((r_cancel, ('cancel',))); hits.append((r_apply, ('apply',)))

    def _render_shutdown_dialog(self):
        bw, bh = 400, 240
        bx, by = (W - bw) // 2, (H - bh) // 2
        # 背景
        bg = vgrad(bw, bh, (90, 126, 214), (58, 91, 176))
        self.screen.blit(bg, (bx, by))
        pygame.draw.rect(self.screen, (255, 255, 255), (bx, by, bw, bh), 2)
        # 顶部
        self.screen.blit(font(28, bold=True).render("⏻", True, (255, 255, 255)), (bx + 20, by + 20))
        t = font(18, bold=True).render("关闭 Windows", True, (255, 255, 255))
        self.screen.blit(t, (bx + 70, by + 28))
        self.screen.blit(font(12).render("您希望计算机做什么？", True, (220, 230, 250)), (bx + 20, by + 70))
        for i, lab in enumerate(['待机', '关闭', '重新启动']):
            r = pygame.Rect(bx + 30 + i * 120, by + 100, 110, 50)
            hot = r.collidepoint(self.mouse)
            col = (255, 255, 255) if not hot else (180, 210, 255)
            pygame.draw.rect(self.screen, col, r, border_radius=6)
            pygame.draw.rect(self.screen, (255, 255, 255), r, 2, border_radius=6)
            ic = {'待机': '🌙', '关闭': '⏻', '重新启动': '🔄'}[lab]
            self.screen.blit(font(24).render(ic, True, (0, 51, 153)), (r.x + 8, r.y + 12))
            self.screen.blit(font(12, bold=True).render(lab, True, (0, 51, 153)), (r.x + 40, r.y + 18))

    def _render_run_dialog(self):
        d = self.dialog
        bw, bh = 380, 170
        bx, by = (W - bw) // 2, (H - bh) // 2
        sh = pygame.Surface((bw + 8, bh + 8), pygame.SRCALPHA)
        pygame.draw.rect(sh, (0, 0, 0, 90), (4, 4, bw, bh), border_radius=8)
        self.screen.blit(sh, (bx - 4, by - 4))
        pygame.draw.rect(self.screen, C['win_border'], (bx, by, bw, bh), border_radius=8)
        pygame.draw.rect(self.screen, C['win_bg'], (bx + 1, by + 1, bw - 2, bh - 2))
        tb = pygame.Rect(bx, by, bw, 26)
        draw_title_bar(self.screen, tb, '▶️', "运行")
        self.screen.blit(font(13).render("请输入程序名称:", True, C['text']), (bx + 20, by + 38))
        ar = pygame.Rect(bx + 20, by + 60, bw - 40, 22)
        pygame.draw.rect(self.screen, (255, 255, 255), ar)
        pygame.draw.rect(self.screen, C['btn_border'], ar, 1)
        self.screen.blit(font(12).render(d['text'] + ('|' if int(time.time() * 2) % 2 else ' '), True, C['text']), (ar.x + 4, ar.y + 4))
        self.screen.blit(font(9).render("例如: notepad, calc, mspaint, winmine, taskmgr", True, (130, 130, 130)), (bx + 20, by + 90))
        r1 = pygame.Rect(bx + bw - 170, by + bh - 36, 75, 24)
        r2 = pygame.Rect(bx + bw - 85, by + bh - 36, 75, 24)
        draw_button(self.screen, r1, "确定", hover=r1.collidepoint(self.mouse))
        draw_button(self.screen, r2, "取消", hover=r2.collidepoint(self.mouse))

    def _render_search_dialog(self):
        d = self.dialog
        bw, bh = 420, 320
        bx, by = (W - bw) // 2, (H - bh) // 2
        sh = pygame.Surface((bw + 8, bh + 8), pygame.SRCALPHA)
        pygame.draw.rect(sh, (0, 0, 0, 90), (4, 4, bw, bh), border_radius=8)
        self.screen.blit(sh, (bx - 4, by - 4))
        pygame.draw.rect(self.screen, C['win_border'], (bx, by, bw, bh), border_radius=8)
        pygame.draw.rect(self.screen, C['win_bg'], (bx + 1, by + 1, bw - 2, bh - 2))
        tb = pygame.Rect(bx, by, bw, 26)
        draw_title_bar(self.screen, tb, '🔍', "搜索结果")
        self.screen.blit(font(12).render("全部或部分文件名:", True, C['text']), (bx + 20, by + 36))
        ar = pygame.Rect(bx + 20, by + 56, bw - 40, 22)
        pygame.draw.rect(self.screen, (255, 255, 255), ar)
        pygame.draw.rect(self.screen, (120, 160, 230), ar, 1)
        self.screen.blit(font(12).render(d['text'] + ('|' if int(time.time() * 2) % 2 else ' '), True, C['text']), (ar.x + 4, ar.y + 4))
        # 结果列表
        rl = pygame.Rect(bx + 20, by + 88, bw - 40, bh - 88 - 44)
        pygame.draw.rect(self.screen, (255, 255, 255), rl)
        pygame.draw.rect(self.screen, C['btn_border'], rl, 1)
        results = d.get('results', [])
        d['_res_hits'] = []
        if not d['text'].strip():
            self.screen.blit(font(11).render("请输入要搜索的程序或文件名。", True, (160, 160, 160)), (rl.x + 8, rl.y + 8))
        elif not results:
            self.screen.blit(font(11).render(f"没有找到与 \"{d['text']}\" 匹配的结果。", True, (160, 100, 100)), (rl.x + 8, rl.y + 8))
        else:
            self.screen.blit(font(10, bold=True).render(f"找到 {len(results)} 个结果（点击打开）：", True, (0, 51, 153)), (rl.x + 8, rl.y + 6))
            yy = rl.y + 26
            for ic, name, app in results:
                row = pygame.Rect(rl.x + 4, yy, rl.w - 8, 22)
                hot = row.collidepoint(self.mouse)
                if hot:
                    pygame.draw.rect(self.screen, C['sel_blue_l'], row)
                    pygame.draw.rect(self.screen, C['sel_blue'], row, 1)
                self.screen.blit(font(13).render(ic, True, (0, 0, 0)), (row.x + 4, row.y + 3))
                self.screen.blit(font(11).render(name, True, C['text']), (row.x + 26, row.y + 4))
                d['_res_hits'].append((row, app))
                yy += 24
                if yy > rl.bottom - 4: break
        # 按钮
        r_search = pygame.Rect(bx + bw - 170, by + bh - 36, 75, 24)
        r_cancel = pygame.Rect(bx + bw - 85, by + bh - 36, 75, 24)
        draw_button(self.screen, r_search, "搜索", hover=r_search.collidepoint(self.mouse))
        draw_button(self.screen, r_cancel, "取消", hover=r_cancel.collidepoint(self.mouse))

    def _render_rename_dialog(self):
        d = self.dialog
        bw, bh = 360, 160
        bx, by = (W - bw) // 2, (H - bh) // 2
        sh = pygame.Surface((bw + 8, bh + 8), pygame.SRCALPHA)
        pygame.draw.rect(sh, (0, 0, 0, 90), (4, 4, bw, bh), border_radius=8)
        self.screen.blit(sh, (bx - 4, by - 4))
        pygame.draw.rect(self.screen, C['win_border'], (bx, by, bw, bh), border_radius=8)
        pygame.draw.rect(self.screen, C['win_bg'], (bx + 1, by + 1, bw - 2, bh - 2))
        tb = pygame.Rect(bx, by, bw, 26)
        draw_title_bar(self.screen, tb, '✏️', "重命名")
        self.screen.blit(font(12).render("请输入新的名称:", True, C['text']), (bx + 20, by + 38))
        ar = pygame.Rect(bx + 20, by + 60, bw - 40, 22)
        pygame.draw.rect(self.screen, (255, 255, 255), ar)
        pygame.draw.rect(self.screen, (120, 160, 230), ar, 1)
        self.screen.blit(font(12).render(d['text'] + ('|' if int(time.time() * 2) % 2 else ' '), True, C['text']), (ar.x + 4, ar.y + 4))
        r_ok = pygame.Rect(bx + bw - 170, by + bh - 36, 75, 24)
        r_cancel = pygame.Rect(bx + bw - 85, by + bh - 36, 75, 24)
        draw_button(self.screen, r_ok, "确定", hover=r_ok.collidepoint(self.mouse))
        draw_button(self.screen, r_cancel, "取消", hover=r_cancel.collidepoint(self.mouse))

    def _draw_spinner(self, cx, cy, t, r1=8, r2=14):
        for i in range(12):
            a = t + i * (math.pi * 2 / 12)
            p1 = (cx + math.cos(a) * r1, cy + math.sin(a) * r1)
            p2 = (cx + math.cos(a) * r2, cy + math.sin(a) * r2)
            col = (80, 80, 80) if i > 6 else (200, 200, 200)
            pygame.draw.line(self.screen, col, p1, p2, 3)

    def _render_shutdown(self):
        t = self.shut_t
        if t < 1.2:
            # 阶段1：保存您的设置（XP 经典蓝绿背景）
            g = vgrad(W, H, (78, 110, 161), (58, 91, 176))
            self.screen.blit(g, (0, 0))
            self.screen.blit(self._boot_logo, ((W - 340) // 2, H // 2 - 110))
            msg = font(18, bold=True).render("正在保存您的设置...", True, (255, 255, 255))
            self.screen.blit(msg, ((W - msg.get_width()) // 2, H // 2 + 20))
            self._draw_spinner(W // 2, H // 2 + 60, self.cursor.spin)
        elif t < 2.8:
            # 阶段2：关闭 Windows
            self.screen.fill((0, 0, 0))
            msg = font(20, bold=True).render("正在关闭 Windows...", True, (200, 200, 200))
            self.screen.blit(msg, ((W - msg.get_width()) // 2, H // 2 - 20))
            self._draw_spinner(W // 2, H // 2 + 30, self.cursor.spin)
        else:
            # 阶段3：可安全关机（仅关机模式会到达这里）
            self.screen.fill((0, 0, 0))
            msg = font(18, bold=True).render("现在可以安全地关闭计算机了", True, (255, 154, 0))
            self.screen.blit(msg, ((W - msg.get_width()) // 2, H // 2))

    def _render_standby(self):
        # 阶段1 (t<1.0)：从桌面快照淡出到黑屏，模拟显示器进入省电
        # 阶段2 (t>=1.0)：纯黑（显示器已关闭，无任何提示文字）
        t = self.standby_t
        if t < 1.0 and self._standby_snap is not None:
            # 先画桌面快照
            self.screen.blit(self._standby_snap, (0, 0))
            # 叠加逐渐变黑的半透明遮罩（alpha 随 t 从 0 升到 255）
            a = int(255 * (t / 1.0))
            ov = pygame.Surface((W, H)); ov.fill((0, 0, 0)); ov.set_alpha(a)
            self.screen.blit(ov, (0, 0))
        else:
            self.screen.fill((0, 0, 0))

    def _update_cursor_state(self):
        mp = self.mouse
        # 检查无响应窗口 → busy 光标
        for w in self.windows:
            if not w.responding and w.rect.collidepoint(mp) and not w.minimized:
                self.cursor.state = self.cursor.BUSY
                return
        # 检查当前活动窗口应用的光标
        if self.active_win and not self.active_win.minimized and self.active_win.responding:
            w = self.active_win
            if w.rect.collidepoint(mp):
                if w.app and hasattr(w.app, 'cursor_state'):
                    st = w.app.cursor_state(mp, w)
                    if st is not None:
                        self.cursor.state = st
                        return
        # 桌面图标 → hand
        for i, (ic, name, app) in enumerate(self.icons):
            if self._icon_rect(i).collidepoint(mp):
                self.cursor.state = self.cursor.ARROW
                return
        self.cursor.state = self.cursor.ARROW


# ===================== 入口 =====================
if __name__ == "__main__":
    XPSystem().run()