from typing import Optional
import pygame
from collections import deque
import random
import socket, os, select


pygame.init()
screen_size = (600, 600)
display_screen = pygame.display.set_mode(size=screen_size)
time_clock = pygame.time.Clock()
def _add(x, y): return x[0]+y[0], x[1]+y[1]
def _sub(x, y): return x[0]-y[0], x[1]-y[1]
def _ldiv(x, d): return x[0]//d, x[1]//d
def _mul(x, d): return x[0]*d, x[1]*d
def _transpose(x): return x[1], x[0]
def _toint(x): return int(x[0]), int(x[1])
def _simtoint(x): return int(x[0]+.5), int(x[1]+.5)
def _dproduct(x, y): return x[0]*y[0], x[1]*y[1]
'''font_names = ['Calibri', 'Microsoft YaHei', 'Arial']
def find_font():
    for name in font_names:
        if pygame.font.match_font(name):
            return name
    return None'''
default_font_size = 36
font_in = {x:pygame.font.Font('Arial.ttf', x) for x in range(120)}
def get_text_size(text, font_size, color=(0, 0, 0)):
    font = font_in[font_size]
    font_surface = font.render(text, True, color)
    return font_surface.get_size()

anips = 12
class ItemBox:
    def __init__(self, topleft=(0, 0), size=(0, 0), bgcolor=(255, 255, 255), color=(0, 0, 0),
                 text='', font_size=default_font_size, padding=0, radius=0):
        self.topleft = topleft
        self.dynamic = False
        self.static = False
        self.size = size
        self.padding = padding
        self.centered = 'l'
        self.text = text
        self.start = (0, 0)
        self.end = (0, 0)
        self.startsize = (0, 0)
        self.endsize = (0, 0)
        self.endstate = 0
        self.state = self.endstate # auto animation
        self.bgcolor = bgcolor
        self.color = color
        self.radius = radius
        self.zaxis = 0
        self.alpha = 1.0
        self.dalpha = 0.0
        self.display = None
        self.fontsize = font_size
        self.text_pos = None
        self.text_surface = None
        self.text_rect = None
        self.updating = False
        self.changed = False
        self.realphaed = False
        self.hide = False
        self.resized = False
        # self._vel = (0, 0)
    def _getcolor(self, color):
        # print(self.alpha, self.)
        if len(color)==3:
            return color+(int(255*self.alpha+0.5),)
        #print(color[:3]+(int(color[3]*self.alpha+0.5),))
        return color[:3]+(int(color[3]*self.alpha+0.5),)
    def renewdisplay(self):
        self.display = pygame.Surface(self.size, pygame.SRCALPHA)
        if self.hide: return
        pygame.draw.rect(self.display, self._getcolor(self.bgcolor), (0, 0, *self.size), border_radius=self.radius)
        font = font_in[self.fontsize]
        color = self._getcolor(self.color)
        self.text_surface = font.render(self.text, True, color[:3])
        self.text_surface.set_alpha(color[3])
        if self.centered == 'l':
            self.text_rect = self.text_surface.get_rect(topleft=(self.padding, self.padding))
        elif self.centered == 'r':
            self.text_rect = self.text_surface.get_rect(topright=(self.size[0]-self.padding, self.padding))
        elif self.centered == 'cx':
            self.text_rect = self.text_surface.get_rect(center=_toint(_dproduct(self.size, self.text_pos)))
        else: #self.centered == 'c'
            self.text_rect = self.text_surface.get_rect(center=_ldiv(self.size, 2))
        self.display.blit(self.text_surface, self.text_rect)
    def getdisplay(self):
        if self.display is None: self.renewdisplay()
        return self.display
    def nextstate(self):
        if self.static: return
        if not self.dynamic: return
        if self.state == self.endstate:
            if self.realphaed: self.alpha = 0.0; self.changed = True
            self.resized, self.realphaed = False, False
            return
        self.state += 1
        vec = _ldiv(_mul(_sub(self.end, self.start), self.state), self.endstate)
        self.topleft = _add(self.start, vec)
        if self.resized:
            vec2 = _ldiv(_mul(_sub(self.endsize, self.startsize), self.state), self.endstate)
            self.size = _add(self.startsize, vec2)
        if self.realphaed:
            self.alpha += self.dalpha
            if self.alpha < 0: self.alpha = 0
        self.updating = True; self.changed = True
    def setr(self, **kwargs):
        for key, value in  kwargs.items():
            setattr(self, key, value)
        return self
# pygame.font.SysFont().render()
def static_itembox(topleft, size, bgcolor, radius, color=(0,0,0), text='', font_size=0, padding=0, centered='l'):
    itembox = ItemBox(topleft, size, bgcolor, color, text, font_size, padding, radius)
    itembox.static = True; itembox.dynamic = False; itembox.zaxis = -1
    itembox.centered = centered
    return itembox
def dynamic_itembox(sf, topleft, size, bgcolor, radius, color=(0,0,0), text='', font_size=0, padding=0, centered='l'):
    if sf is None: itembox = ItemBox()
    else: itembox = sf
    itembox.setr(topleft=topleft, size=size, bgcolor=bgcolor,
                 color=color, text=text, fontsize=font_size,
                 padding=padding, radius=radius)
    itembox.static = False; itembox.dynamic = True; itembox.zaxis = -1
    itembox.centered = centered; itembox.state = itembox.endstate = 0
    itembox.updating = True; itembox.changed = True
    return itembox
class ItemBoxList:
    def __init__(self, ls):
        self.ls = list(ls)
        self.offset = (0, 0)
        self.hide = False
    def nextstate(self, screen):
        #dirty_rect
        for x in self.ls:
            x.nextstate()
            if x.changed:
                x.renewdisplay()
                x.changed = False
            if x.updating:
                pass
                #dirty rects
        if not self.hide:
            self.blit_to(screen)
    def add(self, x):
        self.ls.append(x)
    def delx(self, x): #!
        self.ls.pop(self.ls.index(x))
    def blit_to(self, screen):
        for x in self.ls:
            screen.blit(x.getdisplay(), _add(x.topleft, self.offset))
    def renewls(self, ls):
        self.ls = ls
    def sethide(self, hide):
        self.hide = hide

clr = {
    'txt0': (119, 110, 101), 'txt1': (255, 255, 255),
    'bg': (250, 248, 239), 'grid': (187, 173, 160), 'line': (224, 212, 208),
    '0': (205, 193, 180), '2': (238, 228, 216), '4': (237, 224, 200), '8': (242, 177, 121),
    '16': (245, 149, 99), '32': (246, 124, 95), '64': (246, 94, 59), '128': (237, 207, 114),
    '256': (237, 204, 97), '512': (237, 200, 80), '1024': (237, 197, 63), '2048': (237, 194, 46),
    '4096': (139, 0, 139), '8192': (75, 0, 130), '16384': (232, 54, 99), '32768': (168, 15, 53),
    '#': (0, 0, 0, 0), '×2': (4, 30, 83), '×4': (89, 194, 225), '×0': (192, 32, 24),
    'fog': (255, 255, 255, 128),
    'in1': (244, 238, 232),
    'null': (0, 0, 0, 0),
    'default': (32, 32, 32)
}
txt0 = {
    '2', '4', '#'
}


default_choice = (4, 4)

game_size = (410, 520)
game_offset = _ldiv(_sub(screen_size, game_size), 2)
grid_offset = (10, 120)
grid_size = (390, 390)

g_n: int; g_m: int; g_addfactor: int
g_k: str
class Layout:
    def __init__(self, n, m, k):
        self.n, self.m = n, m
        self.grid_lattice = ((390 - 30 * min(m, 4) // 4) // m, (390 - 30 * min(n, 4) // 4) // n)

        self.grid_mean_gap = _dproduct(_sub(grid_size, _dproduct(self.grid_lattice, (m, n))), (1/(m+1), 1/(n+1)))
        self.grid_radius = 1 + 16 // max(n, m)
        self.bg_itembox_list = ItemBoxList([
            static_itembox((0, 0), game_size, clr['bg'], 10),
            static_itembox((10, 10), (390, 70), clr['bg'], 5, clr['txt0'],
                           '2048_game', 50, 5),
            static_itembox((10, 80), (190, 30), clr['4'], 5, clr['txt0'],
                           'current: ', 20, 5),
            static_itembox((210, 80), (190, 30), clr['4'], 5, clr['txt0'],
                           'best: ', 20, 5),
            static_itembox((10, 120), (390, 390), clr['grid'], min(self.grid_radius, 5) * 2),
            *[static_itembox(_add((1 + 10, 1 + 120), self.getpos((i, j))),
                             (self.grid_lattice[0] - 2, self.grid_lattice[1] - 2), clr['0'], self.grid_radius,
                             centered='c') for i in range(n) for j in range(m)]
        ])
        self.bg_itembox_list.offset = game_offset

        self.grid_itembox_list = ItemBoxList([])
        self.grid_itembox_list.offset = _add(game_offset, grid_offset)

        self.over_itembox_list = ItemBoxList([
            static_itembox((0, 0), grid_size, clr['fog'], min(self.grid_radius, 5) * 2, clr['txt0'],
                           'Game Over!', 60, 10, centered='cx').setr(text_pos=(1 / 2, 1 / 3)),
            btn3_box := static_itembox((125, 195), (140, 40), clr['8'], 5, clr['txt1'],
                                       'menu', 30, 5, centered='c'),
            btn4_box := static_itembox((125, 245), (140, 40), clr['32'], 5, clr['txt1'],
                                       'restart', 30, 5, centered='c'),

        ])
        self.over_itembox_list.offset = _add(_ldiv(_sub(screen_size, game_size), 2), grid_offset)
        self.over_itembox_list.hide = True

        self.pause_itembox_list = ItemBoxList([
            static_itembox((0, 0), grid_size, clr['fog'], min(self.grid_radius, 5) * 2, clr['txt0'],
                           'Pause..', 60, 10, centered='cx').setr(text_pos=(1 / 2, 1 / 3)),
            static_itembox((125, 195), (140, 40), clr['8'], 5, clr['txt1'],
                                       'menu', 30, 5, centered='c'),
            static_itembox((125, 245), (140, 40), clr['32'], 5, clr['txt1'],
                                       'restart', 30, 5, centered='c'),

        ])
        self.pause_itembox_list.offset = _add(_ldiv(_sub(screen_size, game_size), 2), grid_offset)
        self.pause_itembox_list.hide = True

        self.lnum_topleft, self.rnum_topleft, self.lrnum_size = (10, 80), (205, 80), (185, 30)
        self.lradd_movex, self.lradd_alpha, self.lradd_dalpha, self.lradd_anilen = (0, -30), 0.7, -0.01, 24

        self.changing_itembox_list = ItemBoxList([
            static_itembox(self.lnum_topleft, self.lrnum_size, clr['null'], 5, clr['txt0'],
                           '', 20, 5, centered='r'),
            static_itembox(self.rnum_topleft, self.lrnum_size, clr['null'], 5, clr['txt0'],
                           '', 20, 5, centered='r'),
            dynamic_itembox(None, self.lnum_topleft, self.lrnum_size, clr['null'], 5, clr['txt0'],
                            '', 20, 5, centered='r'),
            dynamic_itembox(None, self.rnum_topleft, self.lrnum_size, clr['null'], 5, clr['txt0'],
                            '', 20, 5, centered='r'),
            btn1_box := static_itembox((295, 20), (105, 25), clr['8'], 5, clr['txt1'],
                                       'menu', 20, 5, centered='c'),
            btn2_box := static_itembox((295, 50), (105, 25), clr['32'], 5, clr['txt1'],
                                       'restart', 20, 5, centered='c'),
        ])
        self.lnum_itembox, self.rnum_itembox, self.ladd_itembox, self.radd_itembox = self.changing_itembox_list.ls[:4]
        self.changing_itembox_list.offset = _ldiv(_sub(screen_size, game_size), 2)

        self.button_list = ButtonList([
            Button(btn1_box, self.bg_itembox_list, menu_init),
            Button(btn2_box, self.bg_itembox_list, g2048_init, (n, m, k)),
            Button(btn3_box, self.over_itembox_list, menu_init),
            Button(btn4_box, self.over_itembox_list, g2048_init, (n, m, k)),
        ])

    def getpos(self, pos):
        pos = _transpose(pos)
        return _add(_dproduct(pos, self.grid_lattice),
                    _toint(_dproduct(_add(pos, (1, 1)), self.grid_mean_gap)))

all_mode = ['Regular', 'Featured', '???']
class Menu:
    def addn(self, x):
        if self.set_n+x in range(1, 256):
            self.set_n += x
            self.change_label1()
    def addm(self, x):
        if self.set_m+x in range(1, 256):
            self.set_m += x
            self.change_label2()
    def addk(self, x):
        if self.set_k-x in range(0, len(all_mode)):
            self.set_k -= x
            self.change_label3()
    @staticmethod
    def _tonum(x, l):
        ret = f'{x}'
        if len(ret)>l:
            ret=f'{float(x):.{l-3}e}'
        return ret
    def setmns(self):
        self.set_n = g_n
        self.set_m = g_m
        self.set_k = all_mode.index(g_k) if g_k in all_mode else 0
        self.score_display.setr(text=self._tonum(g2048_best_score, 12), changed=1)
        self.change_label1()
        self.change_label2()
        self.change_label3()
    def change_label1(self):
        self.label_1.setr(text=str(self.set_n), changed=1)
    def change_label2(self):
        self.label_2.setr(text=str(self.set_m), changed=1)
    def change_label3(self):
        self.label_3.setr(text=all_mode[self.set_k], changed=1)
    def change_setting(self, setting=1):
        b = bool(setting)
        self.button_changing[0].setr(hide=b)
        self.button_changing[1].setr(hide=not b)
        self.button_changing[2].setr(hide=not b)

    def __init__(self):
        n_text_size = get_text_size('n=', 28)
        m_text_size = get_text_size('m=', 28)
        self.set_n = g_n
        self.set_m = g_m
        self.set_k = all_mode.index(g_k) if g_k in all_mode else 0
        self.bg_itembox_list = ItemBoxList([
            static_itembox((0, 0), game_size, clr['bg'], 10),
            static_itembox((10, 10), (390, 70), clr['null'], 5, clr['txt0'],
                           '2048_menu', 50, 5),
            # static_itembox((10, 75), (390, 2), clr['line'], 1),

            static_itembox((20, line0:=80), (370, 45), clr['4'], 5, clr['txt0'],
                           'Best Score: ', 26, 8),

            static_itembox((10, (line1:=130)+2), (390, 41), clr['null'], 0),
            static_itembox((10, line1+2), (4, 41), clr['32'], 0),
            static_itembox((20, line1), (390, 45), clr['null'], 5, clr['txt0'],
                           'Size', 30, 5),

            static_itembox((20, line2:=185), (165, 50), clr['in1'], 5),
            static_itembox((225, line2), (165, 50), clr['in1'], 5),

            static_itembox((40, line2), (12 + n_text_size[0] - 20, 50), clr['4'], 0),
            static_itembox((20, line2), (12 + n_text_size[0], 50), clr['4'], 5, clr['txt0'],
                           'n=', 28, 6),

            static_itembox((245, line2), (12 + m_text_size[0] - 20, 50), clr['4'], 0),
            static_itembox((225, line2), (12 + m_text_size[0], 50), clr['4'], 5, clr['txt0'],
                           'm=', 28, 6),

            static_itembox((10, (line3:=255)+2), (390, 41), clr['null'], 0),
            static_itembox((10, line3+2), (4, 41), clr['32'], 0),
            static_itembox((20, line3), (390, 45), clr['null'], 5, clr['txt0'],
                           'Mode', 30, 5),

            static_itembox((20, line4:=310), (370, 50), clr['in1'], 5),
        ])

        self.bg_itembox_list.offset = game_offset
        btn_offhover, btn_onhover = clr['8'], None
        self.changing_itembox_list = ItemBoxList([
            sc_1:=static_itembox((160, line0), (230, 45), clr['null'], 5, clr['txt0'],
                           '0', 26, 8, centered='r'),

            # bn_0:=static_itembox((20, line2), (165, 50), clr['null'], 5),
            lb_1:=static_itembox((20+40, line2), (90, 50), clr['null'], 0, clr['txt0'],
                                 '0', 28, 6, centered='r'),
            bn_u1:=static_itembox((20+135, line2+10), (30, 14), btn_offhover, 0),
            bn_u0:=static_itembox((20+135, line2), (30, 24), btn_offhover, 5, clr['txt1'],
                           '▲',16, centered='c'),
            bn_d1:=static_itembox((20+135, line2+26), (30, 14), btn_offhover, 0),
            bn_d0:=static_itembox((20+135, line2+26), (30, 24), btn_offhover, 5, clr['txt1'],
                           '▼',16, centered='c'),

            # bm_0:=static_itembox((225, line2), (165, 50), clr['null'], 5),
            lb_2:=static_itembox((225+40, line2), (90, 50), clr['null'], 0, clr['txt0'],
                                   '0', 28, 6, centered='r'),
            bm_u1:=static_itembox((225+135, line2+10), (30, 14), btn_offhover, 0),
            bm_u0:=static_itembox((225+135, line2), (30, 24), btn_offhover, 5, clr['txt1'],
                           '▲',16, centered='c'),
            bm_d1:=static_itembox((225+135, line2+26), (30, 14), btn_offhover, 0),
            bm_d0:=static_itembox((225+135, line2+26), (30, 24), btn_offhover, 5, clr['txt1'],
                           '▼',16, centered='c'),

            lb_3:=static_itembox((20, line4), (370, 50), clr['null'], 0, clr['txt0'],
                                 '', 28, centered='c'),
            bk_u1:=static_itembox((360, line4+10), (30, 14), btn_offhover, 0),
            bk_u0:=static_itembox((360, line4), (30, 24), btn_offhover, 5, clr['txt1'],
                                    '▲', 16, centered='c'),
            bk_d1:=static_itembox((360, line4+26), (30, 14), btn_offhover, 0),
            bk_d0:=static_itembox((360, line4+26), (30, 24), btn_offhover, 5, clr['txt1'],
                                    '▼', 16, centered='c'),

            b_start:=static_itembox((20, 440), (370, 60), clr['32'], 10, clr['txt1'],
                                    'Start', 38, centered='c'),
            b_continue:=static_itembox((20, 440), (175, 60), clr['8'], 10, clr['txt1'],
                                    'Continue', 32, centered='c').setr(hide=True),
            b_restart:=static_itembox((215, 440), (175, 60), clr['32'], 10, clr['txt1'],
                                    'Restart', 32, centered='c').setr(hide=True)

        ])
        self.changing_itembox_list.offset = game_offset

        self.score_display = sc_1
        self.label_1 = lb_1
        self.label_2 = lb_2
        self.label_3 = lb_3
        self.button_changing = [b_start, b_continue, b_restart]
        self.button_list = ButtonList([
            Button(bn_u0, self.changing_itembox_list, show=[bn_u0, bn_u1],
                   color=[btn_offhover, btn_onhover], fn=self.addn, attr=(1,)),
            Button(bn_d0, self.changing_itembox_list, show=[bn_d0, bn_d1],
                   color=[btn_offhover, btn_onhover], fn=self.addn, attr=(-1,)),
            Button(bm_u0, self.changing_itembox_list, show=[bm_u0, bm_u1],
                   color=[btn_offhover, btn_onhover], fn=self.addm, attr=(1,)),
            Button(bm_d0, self.changing_itembox_list, show=[bm_d0, bm_d1],
                   color=[btn_offhover, btn_onhover], fn=self.addm, attr=(-1,)),
            Button(bk_u0, self.changing_itembox_list, show=[bk_u0, bk_u1],
                   color=[btn_offhover, btn_onhover], fn=self.addk, attr=(1,)),
            Button(bk_d0, self.changing_itembox_list, show=[bk_d0, bk_d1],
                   color=[btn_offhover, btn_onhover], fn=self.addk, attr=(-1,)),
            Button(b_start, self.changing_itembox_list,
                   fn=lambda x: g2048_init(x.set_n, x.set_m, x.set_k), attr=(self,)),
            Button(b_restart, self.changing_itembox_list,
                   fn=lambda x: g2048_init(x.set_n, x.set_m, x.set_k), attr=(self,)),
            Button(b_continue, self.changing_itembox_list, fn=g2048_resume)
        ])
menu_layout: Menu

g2048_layout: Layout

def getlayout(n, m, k):
    global g_n, g_m, g_k, g2048_layout, g_addfactor
    g_n, g_m, g_k = n, m, all_mode[k]
    g_addfactor = 16
    g2048_layout = Layout(n, m, k)

def getmenu():
    global menu_layout, menubgscreen
    menu_layout = Menu()


g2048_current_score = 0
g2048_best_score = 0
class NumBoard:
    def __init__(self, layout):
        self.lnum_bind = layout.lnum_itembox
        self.rnum_bind = layout.rnum_itembox
        self.ladd_bind = layout.ladd_itembox
        self.radd_bind = layout.radd_itembox
        self.layout = layout
        self.refresh(0, 0, g2048_current_score, g2048_best_score)

    @staticmethod
    def _tonum(x, add=True):
        ret = f'{x:+}' if add else f'{x}'
        if len(ret) > 9:
            ret = f'{float(x):+.4e}' if add else f'{float(x):.4e}'
        return ret

    def refresh(self, ladd, radd, current_score, best_score):
        self.lnum_bind.text = self._tonum(current_score, False)
        self.lnum_bind.changed = True
        if ladd:
            self.ladd_bind = dynamic_itembox(self.ladd_bind, self.layout.lnum_topleft, self.layout.lrnum_size, clr['null'], 5, clr['txt0'],
                                             self._tonum(ladd), 20, 5, centered='r')
            self.ladd_bind.setr(alpha=self.layout.lradd_alpha, dalpha=self.layout.lradd_dalpha, realphaed=True,
                                start=self.layout.lnum_topleft, end=_add(self.layout.lradd_movex, self.layout.lnum_topleft),
                                state=0, endstate=self.layout.lradd_anilen)
        self.rnum_bind.text = self._tonum(best_score, False)
        self.rnum_bind.changed = True
        if radd:
            self.radd_bind = dynamic_itembox(self.radd_bind, self.layout.rnum_topleft, self.layout.lrnum_size, clr['null'], 5, clr['txt0'],
                                             self._tonum(radd), 20, 5, centered='r')
            self.radd_bind.setr(alpha=self.layout.lradd_alpha, dalpha=self.layout.lradd_dalpha, realphaed=True,
                                start=self.layout.rnum_topleft, end=_add(self.layout.lradd_movex, self.layout.rnum_topleft),
                                state=0, endstate=self.layout.lradd_anilen)

    def add(self, x, current_score, best_score):
        current_score += x
        ladd, radd = x, 0
        if current_score > best_score:
            radd = current_score - best_score
            best_score = current_score
        self.refresh(ladd, radd, current_score, best_score)
        return current_score, best_score
numboard: NumBoard

# g_n, g_m, g_addfactor, grid_offset, grid_size, grid_lattice, grid_mean_gap, grid_radius = getlayout(4, 4)


bgscreen = pygame.Surface(screen_size, pygame.SRCALPHA)
menubgscreen = pygame.Surface(screen_size, pygame.SRCALPHA)
# aniscreen = pygame.Surface(screen_size, pygame.SRCALPHA)
def init_screen():
    display_screen.fill(clr['2'])
    display_screen.blit(bgscreen, (0, 0))



def to_str(x):
    if x < 0:
        if x == -1: return '#'
        if x == -3: return '×0'
        return '×'+str(-x)
    return str(x)

class GridBox:
    def grid_palette(self, s):
        if s in clr: return clr[s], clr['txt0' if s in txt0 else 'txt1']
        return clr['default'], clr['txt1']
    def grid_font(self, s):
        n, m = self.layout.n, self.layout.m
        lx, ly = self.layout.grid_lattice
        maxx, maxy = lx * 1.7 / max(len(s)+0.2, 3.6), ly * (0.4+0.02*min(n, 10))
        bdx, bdy = 20, 20
        return int(min(maxx, maxy, (3*maxx+bdx)/4, (3*maxy+bdy)/4, 100))

    def set_to(self, pos, x):
        self.x = x
        s = to_str(x)
        c1, c2 = self.grid_palette(s)
        fnt = self.grid_font(s)
        gridpos = self.layout.getpos(pos)
        self.bind = dynamic_itembox(self.bind, gridpos, self.layout.grid_lattice, c1, self.layout.grid_radius, c2, s, fnt, 0, 'c')
    def __init__(self, pos, x, layout): # plan + lazy deleting
        # self.pos = None
        self.x = None
        self.bind = None
        self.layout = layout
        self.set_to(pos, x)
    def setani_move(self, start, end):
        self.bind.state, self.bind.endstate = 0, anips
        spos = self.layout.getpos(start)
        epos = self.layout.getpos(end)
        self.bind.topleft = spos
        self.bind.start = spos
        self.bind.end = epos
    def setani_resize(self, pos, start = 0.0, end = 1.0):
        self.bind.state, self.bind.endstate = 0, anips
        ssiz = _toint(_mul(self.layout.grid_lattice, start))
        esiz = _toint(_mul(self.layout.grid_lattice, end))
        cpos = _add(self.layout.getpos(pos), _ldiv(self.layout.grid_lattice, 2))
        spos = _sub(cpos, _ldiv(ssiz, 2))
        epos = _sub(cpos, _ldiv(esiz, 2))
        self.bind.topleft = spos
        self.bind.start = spos
        self.bind.end = epos
        self.bind.size = ssiz
        self.bind.startsize = ssiz
        self.bind.endsize = esiz
        self.bind.resized = True

class Grid:
    def __init__(self, n, m):
        self.n = n
        self.m = m
        self.grid = [[0]*m for _ in range(n)]
        self.bind = [[None]*m for _ in range(n)]
        self.di_range = [range(m), range(n)[::-1], range(m)[::-1], range(n)]
        self.di_t = [0, 1, 0, 1]
    def __getitem__(self, item):
        if len(item)==3 and item[2]: return self.grid[item[1]][item[0]]
        else: return self.grid[item[0]][item[1]]
    def __setitem__(self, key, value):
        if len(key)==3 and key[2]: self.grid[key[1]][key[0]] = value
        else: self.grid[key[0]][key[1]] = value
    def __call__(self, x, y, z):
        if z: return y, x
        else: return x, y
    def get(self, item) -> Optional[GridBox]:
        return self.bind[item[0]][item[1]]
    def setbind(self, item, gridbox):
        self.bind[item[0]][item[1]] = gridbox
    def newbind(self, item, gridbox, itembox_list):
        self.bind[item[0]][item[1]] = gridbox
        ## itembox_list.add(gridbox.bind)
        # print(type(gridbox.bind))
    def movebind(self, start, end, itembox_list):
        ## ed = self.get(end)
        ## if ed is not None: itembox_list.delx(ed.bind)
        self.setbind(end, self.get(start))
        self.setbind(start, None)
    def send_to_list(self, itembox_list):
        ## print([x.bind.text for ln in self.bind for x in ln if x is not None])
        itembox_list.renewls([x.bind for ln in self.bind for x in ln if x is not None])
    def con_output(self, showbind=False, show=False):
        if not show: return
        print(' '+'='*20+(' '*8+'='*20 if showbind else ''))
        for i in range(self.n):
            for x in self.grid[i]:
                print(f'{x:5}', end='')
            print(' '*8, end='')
            if showbind:
                for x in self.bind[i]:
                    print(f'{x.x if x else 0:5}', end='')
            print('')
        print(' '+'='*20+(' '*8+'='*20 if showbind else ''))
        print()

def craft(x, y):
    if x==-3 or y==-3: return -1
    if x==y: return x*2
    elif (x>0) ^ (y>0): return -x*y
    else: return None
def mergescore(x, y):
    if x==-3 or y==-3: return -(x*y)*4
    if x==y:
        if x>0: return x*2
        else: return 2**((-x+2)*4)
    else: return 0

def g2048_move(direction, show=0):
    # n, m = grid.n, grid.m
    rj = grid.di_range[direction]; ri = grid.di_range[(direction+1)%4]
    t = grid.di_t[direction]
    q = []
    q2 = []
    b = 0
    sc = 0
    if show: print(f'di={direction}')
    for i in ri:
        it = iter(rj); y = 0; yb = 0; k = -1
        for j in rj:
            if x:=grid[i, j, t]:
                # print(i, j, k, x)
                if y and (cr:=craft(x, y)) is not None and (not yb):
                    q.append(('mov', grid(i, j, t), grid(i, k, t)))
                    q2.append(('$mov', grid(i, j, t), grid(i, k, t)))
                    b = 1
                    sc += mergescore(x, y)
                    y = cr; yb = 1; grid[i, k, t] = y
                    q2.append(('double', grid(i, k, t), y))
                else:
                    k = next(it)
                    if k != j:
                        q.append(('mov', grid(i, j, t), grid(i, k, t)))
                        q2.append(('$mov', grid(i, j, t), grid(i, k, t)))
                        b = 1
                    y = x; yb = 0; grid[i, k, t] = y
        while (k := next(it, None)) is not None:
            grid[i, k, t] = 0
    if sc: q2.append(('score', sc))
    grid.con_output()
    return b, q, q2

# customed
basicfactor = 2
def getrandomblock(p=0):
    # p = -100
    if g_k == 'Regular': p = -100
    if p == -100:
        r = random.randint(0, 99)
        return (2 if (r < 10) else 1) * basicfactor
    elif p == 0:
        r = random.randint(0, 99)
        if g_k == '???' and r == 0 and basicfactor<0 and random.randint(0, 10)==0:
            return 1
        if r < 94:
            return (2 if (r<10) else 1)*basicfactor
        else:
            if r<97: return -1
            else:
                r = random.randint(0, 9)
                return -4 if r==0 else -3 if r<4 else -2
    elif p == 1:
        r = random.randint(0, 15)
        return -3 if r==0 else -4 if r<6 else -2
    elif p == -1:
        r = random.randint(0, 15)
        return basicfactor if r==0 else 2*basicfactor if r<8 else -3
    elif p == 2:
        r = random.randint(0, 15)
        return 4 if r==0 else -3 if r==1 else -1 if r==2 else 2
    elif p == 4:
        r = random.randint(0, 15)
        return 2 if r<4 else -3 if r==4 else -1 if r==5 else 4
    return 0
    # return 2**8
def g2048_addnew(q2):
    n, m = grid.n, grid.m
    s = sum(not grid[i, j] for i in range(n) for j in range(m))
    r = random.sample(range(1, s+1), 1+s//g_addfactor)
    r.sort(reverse=True)
    for i in range(len(r)-1): r[i] -= r[i+1]

    for i in range(n):
        for j in range(m):
            if not grid[i, j]:
                if not r: break
                r[-1] -= 1
                if r[-1] == 0:
                    lx = [grid[i+di, j+dj] for di,dj in ((1,0), (-1,0), (0,-1), (0,1))
                          if i+di in range(n) and j+dj in range(m)]
                    r2 = random.randint(0, 5)
                    p1, p2, p3, p4 = 0, 0, 0, 0
                    for y in lx:
                        if y >= 256: p1 += 1
                        elif 16 <= y <= 64: p2 += 1
                        elif y == 4: p3 += 1
                        elif y == 2: p4 += 1
                    if r2 == 0:
                        if p1:
                            x = getrandomblock(1)
                        elif p2:
                            x = getrandomblock(-1)
                        elif p3:
                            x = getrandomblock(4)
                        elif p4:
                            x = getrandomblock(2)
                        else:
                            x = getrandomblock()
                    else: x = getrandomblock()
                    grid[i, j] = x
                    q2.append(('new', (i, j), x))
                    r.pop()
    if s > 1: return 1
    if any(craft(grid[i, j], grid[i+1, j]) is not None for i in range(n-1) for j in range(m)): return 1
    if any(craft(grid[i, j], grid[i, j+1]) is not None for i in range(n) for j in range(m-1)): return 1
    return 0

di_map = {'a': 0, 's': 1, 'd': 2, 'w': 3}
alive = 1
SchedEnd = -1

def g2048_input(key): #!
    global alive, sched_cnt
    if not alive: return -1
    di = di_map[key]
    b, q, q2 = g2048_move(di)
    if not b: return 0
    alive = g2048_addnew(q2)
    if not alive:
        q2.append(('over',))
    if q:
        sched_queue.extend([q]+[None]*(anips-3))
    if q2:
        sched_queue.extend([q2]+[None]*(anips-3))
    sched_queue.extend([None]*2+[SchedEnd])
    sched_cnt += 1
    return 1

sched_queue: deque
sched_cnt: int
def g2048_handle(events, show=0):
    global sched_cnt, g2048_current_score, g2048_best_score
    if events is None: return
    if events is SchedEnd: sched_cnt -= 1; return
    showtmp = {}
    for event in events:
        name = event[0]
        if show == 2: print(*event)
        elif show == 1:
            if name in showtmp: showtmp[name] += 1
            else: showtmp[name] = 1
        if name == 'mov':
            start, end = event[1:] #!
            # print(grid.bind)
            grid.get(start).setani_move(start, end)
        elif name == '$mov':
            start, end = event[1:] #!
            grid.movebind(start, end, g2048_layout.grid_itembox_list)#?
        elif name == 'double':
            pos, x = event[1:] #!
            grid.get(pos).set_to(pos, x)
        elif name == 'new':
            pos, x = event[1:] #!
            # print(pos, x)
            grid.newbind(pos, GridBox(pos, x, g2048_layout), g2048_layout.grid_itembox_list)
            grid.get(pos).setani_resize(pos, 0.5)
            # print(*map(type, grid_itembox_list.ls))
        elif name == 'score':
            x, = event[1:]
            g2048_current_score, g2048_best_score = numboard.add(x, g2048_current_score, g2048_best_score)
            #!
        elif name == 'over':
            # g2048_over = 1
            g2048_layout.over_itembox_list.sethide(False)
    if show==1: print(' '.join(f"{x}*{y}" for x, y in showtmp.items()))

def g2048_process():
    while sched_cnt > 1 and sched_queue:
        g2048_handle(sched_queue.popleft())
    if sched_queue:
        g2048_handle(sched_queue.popleft())
    # print(grid.bind)

    display_screen.blit(bgscreen, (0, 0))
    grid.send_to_list(g2048_layout.grid_itembox_list) #!
    # grid.con_output(show=True)
    g2048_layout.grid_itembox_list.nextstate(display_screen)
    g2048_layout.changing_itembox_list.nextstate(display_screen)
    g2048_layout.over_itembox_list.nextstate(display_screen)

def reset_anips(x):
    global anips
    while sched_queue:
        g2048_handle(sched_queue.popleft())
    anips = x


def menu_init():
    global isgaming
    isgaming = False
    menu_layout.setmns()
    menu_layout.change_setting(1)
    menu_layout.bg_itembox_list.blit_to(menubgscreen)
    menu_layout.changing_itembox_list.nextstate(display_screen)

def menu_process():
    display_screen.blit(menubgscreen, (0, 0))
    menu_layout.changing_itembox_list.nextstate(display_screen)

grid: Grid
anips_default = 12
def g2048_init(n, m, k):
    global grid, numboard
    global sched_queue, sched_cnt
    global anips
    global alive
    global g2048_current_score
    global basicfactor
    global isgaming
    global anips_default
    sched_queue = deque()
    sched_cnt = 0
    getlayout(n, m, k)
    grid = Grid(g_n, g_m)
    g2048_current_score = 0
    numboard = NumBoard(g2048_layout)
    anips = 12
    if g_n*g_m > 400: anips = 8
    if g_n*g_m > 1000: anips = 4
    anips_default = anips
    if g_k == '???':
        if random.randint(0, 2)==0:
            basicfactor = -1
        else:
            basicfactor = 2**random.randint(random.randint(1, 3),
                                            random.randint(4, random.randint(6, 14)))
    else: basicfactor = 2
    isgaming = True
    g2048_layout.bg_itembox_list.blit_to(bgscreen)
    q2 = []
    alive = g2048_addnew(q2)
    if not alive:
        q2.append(('over',))
    if q2:
        sched_queue.extend([q2])
    g2048_process()
def g2048_resume():
    global isgaming
    isgaming = True
    g2048_process()


g2048_key_map = {pygame.K_a: (1, 'a'), pygame.K_s: (1, 's'), pygame.K_d: (1, 'd'), pygame.K_w: (1, 'w'),
                 pygame.K_LEFT: (1, 'a'), pygame.K_DOWN: (1, 's'), pygame.K_RIGHT: (1, 'd'), pygame.K_UP: (1, 'w'),
                 pygame.K_ESCAPE: (2, 'esc')}

class Button:
    def __init__(self, itembox, itemboxlist, fn=None, attr=(), show=None, color=None):
        self.topleft = _add(itembox.topleft, itemboxlist.offset)
        self.size = itembox.size
        self.fn = fn
        self.attr = attr
        self.itembox = itembox
        self.itemboxlist = itemboxlist
        self.show = [itembox] if show is None else show
        self.hovered = 0
        self.hovercolor = [itembox.bgcolor,
                           None] if color is None else color
        if self.hovercolor[1] is None:
            self.hovercolor[1] = self._darkcolor(itembox.bgcolor)
    @staticmethod
    def _darkcolor(x):
        return tuple(max(c*33//32-18, 0) for c in x)
    def onclick(self):
        if self.fn is not None: self.fn(*self.attr)
    def inuse(self):
        return (not self.itemboxlist.hide) and (not self.itembox.hide)
    def onhover(self, b):
        if b != self.hovered:
            self.hovered = b
            cl = self.hovercolor[b]
            if cl is not None:
                for x in self.show:
                    x.setr(bgcolor=cl, changed=True)
    def __contains__(self, pos):
        return (self.topleft[0] <= pos[0] < self.topleft[0]+self.size[0]
                and self.topleft[1] <= pos[1] < self.topleft[1]+self.size[1])

class ButtonList:
    def __init__(self, ls):
        self.ls = ls
    def click(self, pos):
        for btn in self.ls:
            if pos in btn and btn.inuse():
                btn.onclick()
    def hover(self, pos):
        for btn in self.ls:
            if pos in btn and btn.inuse():
                btn.onhover(1)
            else:
                btn.onhover(0)

button_list: ButtonList
isgaming = False

def to_msg(grid: Grid|None):
    if grid is None:
        return 'still\n'
    buf = ['move', f'{grid.n} {grid.m}']
    for i in range(grid.n):
        buf.append(' '.join(str(grid[i, j]) for j in range(grid.m)))
    buf.append('')
    return '\n'.join(buf)

SOCK_PATH = '/tmp/2048game.sock'
class SockServer:
    def __init__(self):
        if os.path.exists(SOCK_PATH):
            os.unlink(SOCK_PATH)
        self.server = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        self.server.bind(SOCK_PATH)
        self.server.listen(1)
        self.client = None
    def write(self, msg):
        try:
            self.client.send(msg.encode())
        except BrokenPipeError:
            self.pipe_error()
    def pipe_error(self):
        self.disconnect()
    def disconnect(self):
        self.client.close()
        self.client = None
    def connect(self, accept=True):
        if accept:
            self.client, _ = self.server.accept()
        else:
            pass
    def get(self):
        rlist, _, _ = select.select([self.server] + ([self.client] if self.client else []),
                                    [], [], 0)
        data = None
        connected, disconnected = 0, 0
        for sock in rlist:
            if sock is self.server:
                if not self.client:
                    self.connect()
                    connected = 1
                else:
                    self.connect(False)
                    connected = 2
            else:
                try:
                    data = self.client.recv(4096)
                except BrokenPipeError:
                    self.pipe_error()
                if not data:
                    data = None
                    self.disconnect()
                    disconnected = 1
                else:
                    data = data.decode()
        return data, connected, disconnected
    def __del__(self):
        self.server.close()
        os.unlink(SOCK_PATH)
sockserver: SockServer


def UIloop():
    running = True
    init_screen()
    g2048_init(4, 4, 0)
    getmenu()
    sockserver = SockServer()
    while running:
        mouse_pos = pygame.mouse.get_pos()
        for event in pygame.event.get():
            if event.type == pygame.QUIT: running = False
            elif event.type == pygame.KEYDOWN:
                if event.key in g2048_key_map:
                    if isgaming:
                        fn, ch = g2048_key_map[event.key]
                        if fn == 1:
                            g2048_input(ch)
                        elif fn == 2:
                            # g2048_init(g_n+1, g_m+1, g_k)
                            if anips != 2:
                                reset_anips(2)
                            else:
                                reset_anips(anips_default)
                    else:
                        pass
            elif event.type == pygame.MOUSEBUTTONDOWN:
                if isgaming:
                    g2048_layout.button_list.click(mouse_pos)
                else:
                    menu_layout.button_list.click(mouse_pos)
        if isgaming:
            '''aa = (aa+1)%4
            g2048_input('wasd'[aa])'''
            # plan: lazy updating
            g2048_layout.button_list.hover(mouse_pos)
            data, connect, _ = sockserver.get()
            if connect == 1:
                sockserver.write(to_msg(grid))
                print("Connected")
            if data:
                # print(data)
                if g2048_input(data) == 1:
                    sockserver.write(to_msg(grid))
                else:
                    sockserver.write(to_msg(None))

            g2048_process()

            pygame.display.flip()
        else:
            menu_layout.button_list.hover(mouse_pos)
            menu_process()
            pygame.display.flip()
        time_clock.tick(128)

UIloop()
pygame.quit()