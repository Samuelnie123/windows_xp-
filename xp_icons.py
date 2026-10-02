# -*- coding: utf-8 -*-
"""XP icon drawing system - replaces emoji with vector-drawn icons.

注册键使用 \\U / \\u 转义，避免源码写入时 emoji 被损坏。
FontWrapper 拦截 font.render / font.size，自动把文本中的 emoji
（含变体选择符 U+FE0F、零宽连接符 U+200D）替换为矢量绘制的图标，
支持 "emoji + 文字" 混合渲染（如 "⬅️ 后退"、"⏱ 012"）。
"""
import pygame, math

_ICON_CACHE = {}
_DRAWERS = {}

def _reg(name):
    def deco(fn):
        _DRAWERS[name] = fn
        return fn
    return deco

def _s(sz):
    return pygame.Surface((sz, sz), pygame.SRCALPHA)

def _r(s, x, y, w, h, c, r=0):
    if r: pygame.draw.rect(s, c, (x, y, w, h), border_radius=r)
    else: pygame.draw.rect(s, c, (x, y, w, h))

# ===================== 简单图标 =====================
@_reg('\u2b05')   # ⬅
def _back(s, sz):
    m = sz * 0.15
    pygame.draw.polygon(s, (50,100,200), [(m,sz/2),(sz*0.5,m),(sz*0.5,sz*0.35),(sz-m,sz*0.35),(sz-m,sz*0.65),(sz*0.5,sz*0.65),(sz*0.5,sz-m)])

@_reg('\u2190')   # ←  (计算器退格)
def _back2(s, sz):
    _back(s, sz)

@_reg('\u27a1')   # ➡
def _fwd(s, sz):
    m = sz * 0.15
    pygame.draw.polygon(s, (50,100,200), [(sz-m,sz/2),(sz*0.5,m),(sz*0.5,sz*0.35),(m,sz*0.35),(m,sz*0.65),(sz*0.5,sz*0.65),(sz*0.5,sz-m)])

@_reg('\u2b06')   # ⬆
def _up(s, sz):
    m = sz * 0.15
    pygame.draw.polygon(s, (50,100,200), [(sz/2,m),(m,sz*0.5),(sz*0.35,sz*0.5),(sz*0.35,sz-m),(sz*0.65,sz-m),(sz*0.65,sz*0.5),(sz-m,sz*0.5)])

@_reg('\u2795')   # ➕
def _plus(s, sz):
    c=(80,140,80); t=sz*0.12
    pygame.draw.rect(s,c,(sz*0.2,sz*0.5-t/2,sz*0.6,t))
    pygame.draw.rect(s,c,(sz*0.5-t/2,sz*0.2,t,sz*0.6))

@_reg('\u2b1c')   # ⬜
def _sq(s, sz):
    pygame.draw.rect(s,(100,100,100),(sz*0.15,sz*0.15,sz*0.7,sz*0.7),2)

@_reg('\u274c')   # ✖
def _x(s, sz):
    c=(200,30,30); m=sz*0.2; t=max(2,sz*0.08)
    pygame.draw.line(s,c,(m,m),(sz-m,sz-m),int(t))
    pygame.draw.line(s,c,(sz-m,m),(m,sz-m),int(t))

@_reg('\u25b6')   # ▶
def _play(s, sz):
    pygame.draw.polygon(s,(50,130,50),[(sz*0.25,sz*0.2),(sz*0.25,sz*0.8),(sz*0.8,sz*0.5)])

@_reg('\u23f9')   # ⏹
def _stop(s, sz):
    pygame.draw.rect(s,(200,50,50),(sz*0.2,sz*0.2,sz*0.6,sz*0.6))

@_reg('\u2728')   # ✨
def _sparkle(s, sz):
    cx,cy=sz/2,sz/2
    for i in range(4):
        a=i*math.pi/2
        pts=[(cx,cy-sz*0.35),(cx+sz*0.08,cy-sz*0.08),(cx+sz*0.35,cy),(cx+sz*0.08,cy+sz*0.08)]
        rot=[(cx+(p[0]-cx)*math.cos(a)-(p[1]-cy)*math.sin(a),cy+(p[0]-cx)*math.sin(a)+(p[1]-cy)*math.cos(a)) for p in pts]
        pygame.draw.polygon(s,(255,200,0),rot)

@_reg('\u21a9')   # ↩
def _restore(s, sz):
    c=(50,100,200)
    pygame.draw.arc(s,c,(sz*0.2,sz*0.2,sz*0.6,sz*0.5),math.pi*0.3,math.pi*1.7,max(2,int(sz*0.06)))
    pygame.draw.polygon(s,c,[(sz*0.2,sz*0.45),(sz*0.1,sz*0.45),(sz*0.15,sz*0.3)])

@_reg('\u21aa')   # ↪
def _frestore(s, sz):
    c=(50,100,200)
    pygame.draw.arc(s,c,(sz*0.2,sz*0.2,sz*0.6,sz*0.5),math.pi*0.3,math.pi*1.7,max(2,int(sz*0.06)))
    pygame.draw.polygon(s,c,[(sz*0.8,sz*0.45),(sz*0.9,sz*0.45),(sz*0.85,sz*0.3)])

@_reg('\U0001F50D')  # 🔍
def _search(s, sz):
    c=(80,80,80); cx,cy=sz*0.42,sz*0.42; r=sz*0.28
    pygame.draw.circle(s,c,(int(cx),int(cy)),int(r),max(2,int(sz*0.05)))
    pygame.draw.line(s,c,(cx+r*0.7,cy+r*0.7),(sz*0.85,sz*0.85),max(2,int(sz*0.07)))

@_reg('\u2753')   # ❓
def _q(s, sz):
    pygame.draw.circle(s,(50,100,200),(int(sz/2),int(sz/2)),int(sz*0.4))
    f=pygame.font.Font(None,int(sz*0.6)); f.set_bold(True)
    t=f.render('?',True,(255,255,255))
    s.blit(t,(sz/2-t.get_width()/2,sz/2-t.get_height()/2-1))

@_reg('\u26a0')   # ⚠
def _warn(s, sz):
    pts=[(sz/2,sz*0.1),(sz*0.9,sz*0.85),(sz*0.1,sz*0.85)]
    pygame.draw.polygon(s,(255,180,0),pts)
    pygame.draw.polygon(s,(180,120,0),pts,max(2,int(sz*0.03)))
    f=pygame.font.Font(None,int(sz*0.45)); f.set_bold(True)
    t=f.render('!',True,(0,0,0))
    s.blit(t,(sz/2-t.get_width()/2,sz*0.4))

@_reg('\u2139')   # ℹ
def _info(s, sz):
    pygame.draw.circle(s,(50,100,200),(int(sz/2),int(sz/2)),int(sz*0.4))
    f=pygame.font.Font(None,int(sz*0.55)); f.set_bold(True)
    t=f.render('i',True,(255,255,255))
    s.blit(t,(sz/2-t.get_width()/2+1,sz/2-t.get_height()/2))

@_reg('\U0001F512')  # 🔒
def _lock(s, sz):
    _r(s,sz*0.25,sz*0.45,sz*0.5,sz*0.4,(200,160,30),2)
    pygame.draw.arc(s,(120,120,120),(sz*0.32,sz*0.2,sz*0.36,sz*0.35),0,math.pi,max(2,int(sz*0.05)))
    _r(s,sz*0.45,sz*0.55,sz*0.1,sz*0.15,(80,60,0))

@_reg('\u23fb')   # ⏻
def _power(s, sz):
    c=(200,50,50); cx,cy=sz/2,sz/2
    pygame.draw.arc(s,c,(sz*0.2,sz*0.2,sz*0.6,sz*0.6),math.pi*0.25,math.pi*1.75,max(3,int(sz*0.07)))
    pygame.draw.line(s,c,(cx,sz*0.2),(cx,sz*0.5),max(3,int(sz*0.07)))

@_reg('\u23f1')   # ⏱
def _clock(s, sz):
    cx,cy=sz/2,sz/2; r=sz*0.38
    pygame.draw.circle(s,(255,255,255),(int(cx),int(cy)),int(r))
    pygame.draw.circle(s,(80,80,80),(int(cx),int(cy)),int(r),max(2,int(sz*0.04)))
    pygame.draw.line(s,(0,0,0),(cx,cy),(cx,cy-r*0.7),max(2,int(sz*0.04)))
    pygame.draw.line(s,(0,0,0),(cx,cy),(cx+r*0.6,cy),max(2,int(sz*0.04)))

@_reg('\U0001F6A9')  # 🚩
def _flag(s, sz):
    pygame.draw.line(s,(80,80,80),(sz*0.25,sz*0.1),(sz*0.25,sz*0.9),max(2,int(sz*0.05)))
    pygame.draw.polygon(s,(220,30,30),[(sz*0.25,sz*0.15),(sz*0.8,sz*0.3),(sz*0.25,sz*0.45)])

@_reg('\u270f')   # ✏
def _pencil(s, sz):
    pts=[(sz*0.15,sz*0.85),(sz*0.25,sz*0.75),(sz*0.7,sz*0.3),(sz*0.8,sz*0.4),(sz*0.35,sz*0.85),(sz*0.25,sz*0.95)]
    pygame.draw.polygon(s,(220,180,80),pts)
    pygame.draw.polygon(s,(160,120,40),pts,1)
    pygame.draw.polygon(s,(40,40,40),[(sz*0.7,sz*0.3),(sz*0.8,sz*0.4),(sz*0.85,sz*0.35),(sz*0.75,sz*0.25)])

@_reg('\U0001F4CF')  # 📏
def _ruler(s, sz):
    _r(s,sz*0.1,sz*0.35,sz*0.8,sz*0.3,(255,220,100),2)
    for i in range(5):
        x=sz*0.15+i*sz*0.15
        pygame.draw.line(s,(160,120,40),(x,sz*0.35),(x,sz*0.5),1)

@_reg('\U0001F9FD')  # 🧽
def _sponge(s, sz):
    _r(s,sz*0.15,sz*0.2,sz*0.7,sz*0.6,(240,140,130),3)
    for i in range(4):
        for j in range(3):
            pygame.draw.circle(s,(200,100,90),(int(sz*0.25+j*sz*0.2),int(sz*0.35+i*sz*0.13)),2)

@_reg('\U0001FAA3')  # 🪣
def _bucket(s, sz):
    pts=[(sz*0.2,sz*0.3),(sz*0.8,sz*0.3),(sz*0.7,sz*0.85),(sz*0.3,sz*0.85)]
    pygame.draw.polygon(s,(180,140,80),pts)
    pygame.draw.polygon(s,(120,90,40),pts,1)
    pygame.draw.ellipse(s,(200,160,100),(sz*0.2,sz*0.25,sz*0.6,sz*0.12))

@_reg('\U0001F504')  # 🔄
def _refresh(s, sz):
    c=(50,130,200)
    pygame.draw.arc(s,c,(sz*0.2,sz*0.2,sz*0.6,sz*0.6),math.pi*0.2,math.pi*1.5,max(2,int(sz*0.06)))
    pygame.draw.polygon(s,c,[(sz*0.8,sz*0.3),(sz*0.7,sz*0.15),(sz*0.6,sz*0.35)])

@_reg('\U0001F3E0')  # 🏠
def _home(s, sz):
    pts=[(sz*0.5,sz*0.1),(sz*0.1,sz*0.5),(sz*0.25,sz*0.5),(sz*0.25,sz*0.9),(sz*0.75,sz*0.9),(sz*0.75,sz*0.5),(sz*0.9,sz*0.5)]
    pygame.draw.polygon(s,(180,120,80),pts)
    pygame.draw.polygon(s,(120,80,40),pts,1)
    _r(s,sz*0.4,sz*0.6,sz*0.2,sz*0.3,(120,80,40))

@_reg('\U0001F319')  # 🌙
def _moon(s, sz):
    pygame.draw.circle(s,(255,230,120),(int(sz*0.5),int(sz*0.5)),int(sz*0.35))
    cut=pygame.Surface((sz,sz),pygame.SRCALPHA)
    pygame.draw.circle(cut,(255,255,255,255),(int(sz*0.65),int(sz*0.4)),int(sz*0.3))
    s.blit(cut,(0,0),special_flags=pygame.BLEND_RGBA_SUB)

@_reg('\U0001F524')  # 🔤
def _abc(s, sz):
    f=pygame.font.Font(None,int(sz*0.4)); f.set_bold(True)
    t=f.render('Abc',True,(50,100,200))
    s.blit(t,(sz/2-t.get_width()/2,sz/2-t.get_height()/2))

@_reg('\u26a1')   # ⚡
def _bolt(s, sz):
    pts=[(sz*0.55,sz*0.1),(sz*0.3,sz*0.5),(sz*0.5,sz*0.5),(sz*0.4,sz*0.9),(sz*0.7,sz*0.4),(sz*0.5,sz*0.4)]
    pygame.draw.polygon(s,(255,200,0),pts)
    pygame.draw.polygon(s,(180,140,0),pts,1)

@_reg('\U0001F550')  # 🕐
def _clock2(s, sz):
    _clock(s, sz)

# ===================== 复杂图标 =====================
@_reg('\U0001F5A5')  # 🖥  我的电脑
def _computer(s, sz):
    _r(s,sz*0.1,sz*0.1,sz*0.8,sz*0.6,(200,200,215),3)
    _r(s,sz*0.14,sz*0.14,sz*0.72,sz*0.52,(100,150,220))
    _r(s,sz*0.35,sz*0.7,sz*0.3,sz*0.08,(160,160,175))
    _r(s,sz*0.25,sz*0.78,sz*0.5,sz*0.06,(130,130,145))

@_reg('\U0001F5D1')  # 🗑  回收站
def _recycle(s, sz):
    pts=[(sz*0.25,sz*0.3),(sz*0.75,sz*0.3),(sz*0.68,sz*0.9),(sz*0.32,sz*0.9)]
    pygame.draw.polygon(s,(180,190,200),pts)
    pygame.draw.polygon(s,(120,130,140),pts,1)
    _r(s,sz*0.2,sz*0.2,sz*0.6,sz*0.12,(200,210,220),2)
    cx,cy=sz/2,sz*0.6
    for i in range(3):
        a=i*math.pi*2/3-math.pi/2
        pygame.draw.line(s,(60,140,60),(cx+math.cos(a)*sz*0.1,cy+math.sin(a)*sz*0.1),(cx+math.cos(a)*sz*0.18,cy+math.sin(a)*sz*0.18),2)

@_reg('\U0001F310')  # 🌐  网上邻居
def _globe(s, sz):
    cx,cy=sz/2,sz/2; r=sz*0.38
    pygame.draw.circle(s,(100,160,230),(int(cx),int(cy)),int(r))
    pygame.draw.circle(s,(60,120,190),(int(cx),int(cy)),int(r),1)
    for i in range(-2,3):
        y=cy+i*r*0.3; dy=abs(i)*r*0.3; w=math.sqrt(max(0,r*r-dy*dy))
        if w>0: pygame.draw.ellipse(s,(60,120,190),(cx-w,y-r*0.05,w*2,r*0.1),1)
    pygame.draw.line(s,(60,120,190),(cx,cy-r),(cx,cy+r),1)
    pygame.draw.ellipse(s,(60,120,190),(cx-r*0.5,cy-r,r,r*2),1)

@_reg('\U0001F4C1')  # 📁
def _folder(s, sz):
    pts=[(sz*0.1,sz*0.3),(sz*0.1,sz*0.8),(sz*0.9,sz*0.8),(sz*0.9,sz*0.4),(sz*0.45,sz*0.4),(sz*0.35,sz*0.3)]
    pygame.draw.polygon(s,(255,200,60),pts)
    pygame.draw.polygon(s,(200,150,30),pts,1)

@_reg('\U0001F4C2')  # 📂
def _folder_open(s, sz):
    pts=[(sz*0.1,sz*0.25),(sz*0.4,sz*0.25),(sz*0.5,sz*0.35),(sz*0.9,sz*0.35),(sz*0.8,sz*0.8),(sz*0.15,sz*0.8)]
    pygame.draw.polygon(s,(255,210,80),pts)
    pygame.draw.polygon(s,(200,150,30),pts,1)

@_reg('\U0001F4DD')  # 📝  记事本
def _notepad(s, sz):
    _r(s,sz*0.2,sz*0.1,sz*0.6,sz*0.8,(255,255,240),1)
    pygame.draw.rect(s,(180,180,160),(sz*0.2,sz*0.1,sz*0.6,sz*0.8),1)
    for i in range(5):
        pygame.draw.line(s,(100,140,220),(sz*0.28,sz*0.25+i*sz*0.13),(sz*0.72,sz*0.25+i*sz*0.13),1)

@_reg('\U0001F3A8')  # 🎨  画图
def _palette(s, sz):
    pygame.draw.ellipse(s,(240,230,200),(sz*0.1,sz*0.15,sz*0.8,sz*0.7))
    pygame.draw.ellipse(s,(180,170,140),(sz*0.1,sz*0.15,sz*0.8,sz*0.7),1)
    for i,c in enumerate([(220,50,50),(50,150,50),(50,80,220),(255,200,0),(150,50,200)]):
        cx=sz*0.25+(i%3)*sz*0.2; cy=sz*0.3+(i//3)*sz*0.2
        pygame.draw.circle(s,c,(int(cx),int(cy)),int(sz*0.06))
    pygame.draw.circle(s,(240,230,200),(int(sz*0.7),int(sz*0.6)),int(sz*0.08))

@_reg('\U0001F9EE')  # 🧮  计算器
def _calc(s, sz):
    _r(s,sz*0.15,sz*0.1,sz*0.7,sz*0.8,(180,180,190),3)
    _r(s,sz*0.2,sz*0.15,sz*0.6,sz*0.2,(120,160,100),1)
    for r in range(3):
        for c in range(3):
            _r(s,sz*0.22+c*sz*0.2,sz*0.4+r*sz*0.16,sz*0.15,sz*0.12,(220,220,230),1)

@_reg('\U0001F4A3')  # 💣  扫雷
def _bomb(s, sz):
    cx,cy=sz*0.45,sz*0.55; r=sz*0.32
    pygame.draw.circle(s,(50,50,50),(int(cx),int(cy)),int(r))
    pygame.draw.circle(s,(100,100,100),(int(cx-r*0.3),int(cy-r*0.3)),int(r*0.15))
    pygame.draw.line(s,(120,80,40),(cx+r*0.6,cy-r*0.6),(sz*0.8,sz*0.15),max(2,int(sz*0.04)))
    pygame.draw.circle(s,(255,180,0),(int(sz*0.82),int(sz*0.13)),int(sz*0.06))
    pygame.draw.circle(s,(255,100,0),(int(sz*0.82),int(sz*0.13)),int(sz*0.04))

@_reg('\u2699')   # ⚙  控制面板
def _gear(s, sz):
    cx,cy=sz/2,sz/2; r_out=sz*0.4; r_in=sz*0.25
    pts=[]
    for i in range(16):
        a=i*math.pi/8; r=r_out if i%2==0 else r_out*0.8
        pts.append((cx+math.cos(a)*r,cy+math.sin(a)*r))
    pygame.draw.polygon(s,(160,160,170),pts)
    pygame.draw.circle(s,(200,200,210),(int(cx),int(cy)),int(r_in))
    pygame.draw.circle(s,(120,120,130),(int(cx),int(cy)),int(r_in),1)

@_reg('\U0001F4CA')  # 📊  任务管理器
def _chart(s, sz):
    _r(s,sz*0.1,sz*0.15,sz*0.05,sz*0.7,(100,100,100))
    _r(s,sz*0.1,sz*0.8,sz*0.8,sz*0.05,(100,100,100))
    for x,h,c in [(0.2,0.4,(220,80,80)),(0.38,0.55,(80,160,80)),(0.56,0.3,(80,100,220)),(0.74,0.5,(255,180,0))]:
        _r(s,sz*x,sz*(0.8-h),sz*0.12,sz*h,c,1)

@_reg('\U0001F4BF')  # 💿
def _cd(s, sz):
    cx,cy=sz/2,sz/2; r=sz*0.4
    pygame.draw.circle(s,(220,220,230),(int(cx),int(cy)),int(r))
    pygame.draw.circle(s,(180,180,200),(int(cx),int(cy)),int(r),1)
    pygame.draw.circle(s,(240,240,250),(int(cx-r*0.3),int(cy-r*0.3)),int(r*0.15))
    pygame.draw.circle(s,(200,200,220),(int(cx),int(cy)),int(r*0.25),1)
    pygame.draw.circle(s,(240,240,250),(int(cx),int(cy)),int(r*0.1))

@_reg('\U0001F4BD')  # 💽
def _disk(s, sz):
    _r(s,sz*0.1,sz*0.25,sz*0.8,sz*0.5,(180,180,195),3)
    _r(s,sz*0.15,sz*0.3,sz*0.7,sz*0.15,(100,140,200),1)
    pygame.draw.circle(s,(220,220,230),(int(sz*0.75),int(sz*0.6)),int(sz*0.08))
    pygame.draw.circle(s,(160,160,175),(int(sz*0.75),int(sz*0.6)),int(sz*0.08),1)

@_reg('\U0001F5BC')  # 🖼  图片收藏
def _picture(s, sz):
    _r(s,sz*0.1,sz*0.1,sz*0.8,sz*0.8,(240,240,220),2)
    pygame.draw.rect(s,(180,180,160),(sz*0.1,sz*0.1,sz*0.8,sz*0.8),1)
    pygame.draw.polygon(s,(80,160,80),[(sz*0.2,sz*0.75),(sz*0.35,sz*0.55),(sz*0.5,sz*0.7),(sz*0.65,sz*0.5),(sz*0.8,sz*0.75)])
    pygame.draw.circle(s,(255,200,0),(int(sz*0.7),int(sz*0.3)),int(sz*0.06))

@_reg('\U0001F3B5')  # 🎵
def _music(s, sz):
    pygame.draw.circle(s,(50,50,50),(int(sz*0.3),int(sz*0.75)),int(sz*0.12))
    pygame.draw.circle(s,(50,50,50),(int(sz*0.65),int(sz*0.7)),int(sz*0.1))
    pygame.draw.line(s,(50,50,50),(sz*0.4,sz*0.75),(sz*0.4,sz*0.2),max(2,int(sz*0.04)))
    pygame.draw.line(s,(50,50,50),(sz*0.73,sz*0.7),(sz*0.73,sz*0.25),max(2,int(sz*0.04)))
    pygame.draw.line(s,(50,50,50),(sz*0.4,sz*0.2),(sz*0.73,sz*0.25),max(2,int(sz*0.04)))

@_reg('\U0001F3AE')  # 🎮
def _game(s, sz):
    _r(s,sz*0.1,sz*0.35,sz*0.8,sz*0.35,(120,120,130),8)
    pygame.draw.circle(s,(200,50,50),(int(sz*0.7),int(sz*0.45)),int(sz*0.05))
    pygame.draw.circle(s,(200,200,50),(int(sz*0.78),int(sz*0.55)),int(sz*0.05))
    _r(s,sz*0.2,sz*0.47,sz*0.08,sz*0.08,(60,60,60))
    _r(s,sz*0.16,sz*0.51,sz*0.16,sz*0.04,(60,60,60))

@_reg('\U0001F5A8')  # 🖨  打印机
def _printer(s, sz):
    _r(s,sz*0.15,sz*0.4,sz*0.7,sz*0.3,(180,180,190),3)
    _r(s,sz*0.25,sz*0.15,sz*0.5,sz*0.3,(240,240,240),1)
    _r(s,sz*0.25,sz*0.65,sz*0.5,sz*0.25,(240,240,240),1)
    for i in range(3):
        pygame.draw.line(s,(180,180,180),(sz*0.3,sz*0.72+i*sz*0.06),(sz*0.7,sz*0.72+i*sz*0.06),1)
    pygame.draw.circle(s,(80,160,80),(int(sz*0.75),int(sz*0.5)),int(sz*0.03))

@_reg('\U0001F50A')  # 🔊
def _speaker(s, sz):
    pygame.draw.polygon(s,(80,80,80),[(sz*0.2,sz*0.4),(sz*0.35,sz*0.4),(sz*0.5,sz*0.2),(sz*0.5,sz*0.8),(sz*0.35,sz*0.6),(sz*0.2,sz*0.6)])
    for i in range(2):
        pygame.draw.arc(s,(80,80,80),(sz*0.5,sz*0.3,sz*0.2+i*sz*0.12,sz*0.4),-math.pi/3,math.pi/3,max(2,int(sz*0.03)))

@_reg('\U0001F4F6')  # 📶
def _wifi(s, sz):
    cx=sz/2; cy=sz*0.75
    for i in range(3):
        r=sz*(0.15+i*0.15)
        pygame.draw.arc(s,(255,255,255),(cx-r,cy-r,r*2,r*2),math.pi*1.2,math.pi*1.8,max(2,int(sz*0.04)))
    pygame.draw.circle(s,(255,255,255),(int(cx),int(cy)),int(sz*0.04))

@_reg('\U0001F6E1')  # 🛡
def _shield(s, sz):
    pts=[(sz*0.5,sz*0.1),(sz*0.85,sz*0.25),(sz*0.85,sz*0.5),(sz*0.5,sz*0.9),(sz*0.15,sz*0.5),(sz*0.15,sz*0.25)]
    pygame.draw.polygon(s,(80,130,200),pts)
    pygame.draw.polygon(s,(50,90,150),pts,1)
    pygame.draw.line(s,(255,255,255),(sz*0.35,sz*0.5),(sz*0.45,sz*0.62),3)
    pygame.draw.line(s,(255,255,255),(sz*0.45,sz*0.62),(sz*0.65,sz*0.38),3)

@_reg('\U0001F464')  # 👤
def _user(s, sz):
    pygame.draw.circle(s,(255,210,150),(int(sz*0.5),int(sz*0.35)),int(sz*0.18))
    pygame.draw.ellipse(s,(80,130,200),(sz*0.25,sz*0.5,sz*0.5,sz*0.4))

@_reg('\U0001F4CB')  # 📋
def _clip(s, sz):
    _r(s,sz*0.15,sz*0.1,sz*0.7,sz*0.8,(240,240,230),2)
    pygame.draw.rect(s,(180,180,160),(sz*0.15,sz*0.1,sz*0.7,sz*0.8),1)
    _r(s,sz*0.35,sz*0.05,sz*0.3,sz*0.12,(180,180,190),2)
    for i in range(4):
        pygame.draw.line(s,(100,120,160),(sz*0.25,sz*0.3+i*sz*0.13),(sz*0.75,sz*0.3+i*sz*0.13),1)

@_reg('\U0001F4C4')  # 📄
def _doc(s, sz):
    pts=[(sz*0.2,sz*0.1),(sz*0.65,sz*0.1),(sz*0.8,sz*0.25),(sz*0.8,sz*0.9),(sz*0.2,sz*0.9)]
    pygame.draw.polygon(s,(255,255,245),pts)
    pygame.draw.polygon(s,(180,180,160),pts,1)
    pygame.draw.polygon(s,(220,220,200),[(sz*0.65,sz*0.1),(sz*0.8,sz*0.25),(sz*0.65,sz*0.25)])
    for i in range(5):
        pygame.draw.line(s,(150,150,130),(sz*0.28,sz*0.35+i*sz*0.1),(sz*0.72,sz*0.35+i*sz*0.1),1)

@_reg('\U0001F4E7')  # 📧
def _envelope(s, sz):
    _r(s,sz*0.1,sz*0.25,sz*0.8,sz*0.5,(255,255,250),2)
    pygame.draw.rect(s,(180,180,160),(sz*0.1,sz*0.25,sz*0.8,sz*0.5),1)
    pygame.draw.polygon(s,(200,80,60),[(sz*0.1,sz*0.25),(sz*0.5,sz*0.55),(sz*0.9,sz*0.25)])
    pygame.draw.line(s,(180,180,160),(sz*0.1,sz*0.75),(sz*0.5,sz*0.45),1)
    pygame.draw.line(s,(180,180,160),(sz*0.9,sz*0.75),(sz*0.5,sz*0.45),1)

@_reg('\U0001F5B1')  # 🖱  鼠标
def _mouse(s, sz):
    pygame.draw.ellipse(s,(220,220,230),(sz*0.3,sz*0.15,sz*0.4,sz*0.7))
    pygame.draw.ellipse(s,(160,160,175),(sz*0.3,sz*0.15,sz*0.4,sz*0.7),1)
    pygame.draw.line(s,(160,160,175),(sz*0.5,sz*0.15),(sz*0.5,sz*0.4),1)

@_reg('\u2328')    # ⌨  键盘
def _keyboard(s, sz):
    _r(s,sz*0.08,sz*0.3,sz*0.84,sz*0.5,(200,202,210),3)
    pygame.draw.rect(s,(150,152,165),(sz*0.08,sz*0.3,sz*0.84,sz*0.5),1)
    for r in range(3):
        for c in range(8):
            _r(s,sz*0.13+c*sz*0.09,sz*0.36+r*sz*0.13,sz*0.07,sz*0.08,(250,250,252),1)
    _r(s,sz*0.28,sz*0.72,sz*0.44,sz*0.05,(150,152,165),1)

@_reg('\U0001F4BB')  # 💻  笔记本
def _laptop(s, sz):
    _r(s,sz*0.15,sz*0.15,sz*0.7,sz*0.5,(180,180,195),2)
    _r(s,sz*0.19,sz*0.19,sz*0.62,sz*0.42,(100,150,220))
    pygame.draw.polygon(s,(120,120,135),[(sz*0.1,sz*0.72),(sz*0.9,sz*0.72),(sz*0.85,sz*0.85),(sz*0.15,sz*0.85)])

# ===================== 表情图标 =====================
@_reg('\U0001F642')  # 🙂
def _smile(s, sz):
    cx,cy=sz/2,sz/2; r=sz*0.4
    pygame.draw.circle(s,(255,220,0),(int(cx),int(cy)),int(r))
    pygame.draw.circle(s,(180,140,0),(int(cx),int(cy)),int(r),1)
    pygame.draw.circle(s,(50,50,50),(int(cx-r*0.35),int(cy-r*0.2)),int(r*0.1))
    pygame.draw.circle(s,(50,50,50),(int(cx+r*0.35),int(cy-r*0.2)),int(r*0.1))
    pygame.draw.arc(s,(50,50,50),(cx-r*0.4,cy-r*0.1,r*0.8,r*0.6),math.pi*1.1,math.pi*1.9,max(2,int(sz*0.04)))

@_reg('\U0001F60E')  # 😎
def _cool(s, sz):
    cx,cy=sz/2,sz/2; r=sz*0.4
    pygame.draw.circle(s,(255,220,0),(int(cx),int(cy)),int(r))
    pygame.draw.circle(s,(180,140,0),(int(cx),int(cy)),int(r),1)
    pygame.draw.circle(s,(50,50,50),(int(cx-r*0.35),int(cy-r*0.2)),int(r*0.15))
    pygame.draw.circle(s,(50,50,50),(int(cx+r*0.35),int(cy-r*0.2)),int(r*0.15))
    pygame.draw.arc(s,(50,50,50),(cx-r*0.4,cy-r*0.1,r*0.8,r*0.6),math.pi*1.1,math.pi*1.9,max(2,int(sz*0.04)))

@_reg('\U0001F62E')  # 😮
def _surprised(s, sz):
    cx,cy=sz/2,sz/2; r=sz*0.4
    pygame.draw.circle(s,(255,220,0),(int(cx),int(cy)),int(r))
    pygame.draw.circle(s,(180,140,0),(int(cx),int(cy)),int(r),1)
    pygame.draw.circle(s,(50,50,50),(int(cx-r*0.35),int(cy-r*0.2)),int(r*0.1))
    pygame.draw.circle(s,(50,50,50),(int(cx+r*0.35),int(cy-r*0.2)),int(r*0.1))
    pygame.draw.circle(s,(50,50,50),(int(cx),int(cy+r*0.25)),int(r*0.12))

@_reg('\U0001F635')  # 😵
def _dead(s, sz):
    cx,cy=sz/2,sz/2; r=sz*0.4
    pygame.draw.circle(s,(255,220,0),(int(cx),int(cy)),int(r))
    pygame.draw.circle(s,(180,140,0),(int(cx),int(cy)),int(r),1)
    ex,ey=cx-r*0.35,cy-r*0.2
    pygame.draw.line(s,(50,50,50),(ex-r*0.1,ey-r*0.1),(ex+r*0.1,ey+r*0.1),2)
    pygame.draw.line(s,(50,50,50),(ex+r*0.1,ey-r*0.1),(ex-r*0.1,ey+r*0.1),2)
    ex2=cx+r*0.35
    pygame.draw.line(s,(50,50,50),(ex2-r*0.1,ey-r*0.1),(ex2+r*0.1,ey+r*0.1),2)
    pygame.draw.line(s,(50,50,50),(ex2+r*0.1,ey-r*0.1),(ex2-r*0.1,ey+r*0.1),2)
    pygame.draw.arc(s,(50,50,50),(cx-r*0.3,cy+r*0.15,r*0.6,r*0.4),math.pi*0.1,math.pi*0.9,max(2,int(sz*0.04)))

# ===================== 图标缓存 / 查询 =====================
_VS = chr(0xfe0f)   # 变体选择符
_ZWJ = chr(0x200d)  # 零宽连接符
_SKIP = (_VS, _ZWJ)

def get_icon(emoji, sz):
    """根据 base emoji 字符与尺寸返回缓存好的图标 Surface。"""
    sz = int(sz)
    if sz < 4: sz = 4
    key = (emoji, sz)
    cached = _ICON_CACHE.get(key)
    if cached is not None:
        return cached
    fn = _DRAWERS.get(emoji)
    if not fn:
        return None
    surf = _s(sz)
    try:
        fn(surf, sz)
    except Exception:
        pass
    _ICON_CACHE[key] = surf
    return surf

def _tokenize(text):
    """把文本拆成 [('icon', base_char) | ('text', str), ...]，跳过 VS/ZWJ。"""
    runs = []
    i = 0
    n = len(text)
    while i < n:
        ch = text[i]
        if ch in _SKIP:
            i += 1
            continue
        if ch in _DRAWERS:
            j = i + 1
            while j < n and text[j] in _SKIP:
                j += 1
            runs.append(('icon', ch))
            i = j
        else:
            buf = []
            j = i
            while j < n:
                c2 = text[j]
                if c2 in _SKIP:
                    j += 1
                    continue
                if c2 in _DRAWERS:
                    break
                buf.append(c2)
                j += 1
            if buf:
                runs.append(('text', ''.join(buf)))
            i = j
    return runs

class FontWrapper:
    """包装 pygame.font.Font，拦截 render/size，把 emoji 替换为矢量图标。
    其余属性访问透传给真实字体对象。"""

    def __init__(self, real_font):
        object.__setattr__(self, '_f', real_font)

    def render(self, text, aa, color, bg=None):
        runs = _tokenize(text)
        if not runs:
            return self._f.render(text, aa, color, bg)
        # 单段纯文本：直接走原字体（保留 bg 等行为）
        if len(runs) == 1 and runs[0][0] == 'text':
            return self._f.render(runs[0][1], aa, color, bg)

        h_font = self._f.get_height()
        surfs = []
        for kind, content in runs:
            if kind == 'icon':
                ic = get_icon(content, h_font)
                surfs.append(ic if ic is not None else self._f.render(content, aa, color, bg))
            else:
                surfs.append(self._f.render(content, aa, color, None))

        max_h = max(s.get_height() for s in surfs)
        total_w = sum(s.get_width() for s in surfs)
        if bg is not None:
            result = pygame.Surface((total_w, max_h))
            result.fill(bg)
        else:
            result = pygame.Surface((total_w, max_h), pygame.SRCALPHA)
        x = 0
        for s in surfs:
            result.blit(s, (x, (max_h - s.get_height()) // 2))
            x += s.get_width()
        return result

    def size(self, text):
        runs = _tokenize(text)
        if not runs:
            return self._f.size(text)
        if len(runs) == 1 and runs[0][0] == 'text':
            return self._f.size(runs[0][1])
        h_font = self._f.get_height()
        total_w = 0
        max_h = h_font
        for kind, content in runs:
            if kind == 'icon':
                ic = get_icon(content, h_font)
                if ic is not None:
                    total_w += ic.get_width()
                    if ic.get_height() > max_h:
                        max_h = ic.get_height()
                else:
                    w, h = self._f.size(content)
                    total_w += w
                    if h > max_h:
                        max_h = h
            else:
                w, h = self._f.size(content)
                total_w += w
                if h > max_h:
                    max_h = h
        return (total_w, max_h)

    def __getattr__(self, name):
        return getattr(self._f, name)

    def __setattr__(self, name, value):
        if name == '_f':
            object.__setattr__(self, name, value)
        else:
            setattr(self._f, name, value)

def wrap(real_font):
    """包装一个真实字体对象，返回 FontWrapper。"""
    return FontWrapper(real_font)

def is_icon(text):
    """整段文本是否就是一个图标。返回 (bool, base_char_or_text)。"""
    t = text.replace(_VS, '').replace(_ZWJ, '').strip()
    return (t in _DRAWERS), t
