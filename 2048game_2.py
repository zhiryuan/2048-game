from typing import Optional
import pygame
from collections import deque
import random

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
default_font_size = 36
default_font = 'Arial'

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
        self.endstate = anips
        self.state = self.endstate # 0:8, 20ms # auto animation
        self.bgcolor = bgcolor
        self.color = color
        self.radius = radius
        self.zaxis = 0
        self.alpha = 1.0
        self.dalpha = 0.0
        self.display = None
        self.fontsize = font_size
        self.font = default_font
        self.text_surface = None
        self.text_rect = None
        self.updating = False
        self.changed = False
        self.realphaed = False
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
        pygame.draw.rect(self.display, self._getcolor(self.bgcolor), (0, 0, *self.size), border_radius=self.radius)
        font = pygame.font.SysFont(self.font, self.fontsize)
        color = self._getcolor(self.color)
        self.text_surface = font.render(self.text, True, color[:3])
        self.text_surface.set_alpha(color[3])
        if self.centered == 'c':
            self.text_rect = self.text_surface.get_rect(center=_ldiv(self.size, 2))
        elif self.centered == 'l':
            self.text_rect = self.text_surface.get_rect(topleft=(self.padding, self.padding))
        else:
            self.text_rect = self.text_surface.get_rect(topright=(self.size[0]-self.padding, self.padding))
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
        vec = _ldiv(_mul(_sub(self.end, self.start), self.state), anips)
        self.topleft = _add(self.start, vec)
        if self.resized:
            vec2 = _ldiv(_mul(_sub(self.endsize, self.startsize), self.state), anips)
            self.size = _add(self.startsize, vec2)
        if self.realphaed:
            self.alpha += self.dalpha
            if self.alpha < 0: self.alpha = 0
        self.updating = True; self.changed = True
# pygame.font.SysFont().render()
def static_itembox(topleft, size, bgcolor, radius, color=(0,0,0), text='', font_size=0, padding=0, centered='l'):
    itembox = ItemBox(topleft, size, bgcolor, color, text, font_size, padding, radius)
    itembox.static = True; itembox.dynamic = False; itembox.zaxis = -1
    itembox.centered = centered
    return itembox
def dynamic_itembox(sf, topleft, size, bgcolor, radius, color=(0,0,0), text='', font_size=0, padding=0, centered='l'):
    if sf is None: itembox = ItemBox()
    else: itembox = sf
    (
        itembox.topleft, itembox.size, itembox.bgcolor, itembox.color,
        itembox.text, itembox.fontsize, itembox.padding, itembox.radius
    ) = topleft, size, bgcolor, color, text, font_size, padding, radius
    itembox.static = False; itembox.dynamic = True; itembox.zaxis = -1
    itembox.centered = centered; itembox.state = itembox.endstate
    itembox.updating = True; itembox.changed = True
    return itembox
class ItemBoxList:
    def __init__(self, ls):
        self.ls = list(ls)
        self.offset = (0, 0)
    def nextstate(self, screen):
        #dirty_
        for x in self.ls:
            x.nextstate()
            if x.changed:
                x.renewdisplay()
                x.changed = False
            if x.updating:
                pass
                #dirty rects
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

clr = {
    'txt0': (119, 110, 101), 'txt1': (255, 255, 255),
    'bg': (250, 248, 239), 'grid': (187, 173, 160),
    '0': (205, 193, 180), '2': (238, 228, 218), '4': (237, 224, 200), '8': (242, 177, 121),
    '16': (245, 149, 99), '32': (246, 124, 95), '64': (246, 94, 59), '128': (237, 207, 114),
    '256': (237, 204, 97), '512': (237, 200, 80), '1024': (237, 197, 63), '2048': (237, 194, 46),
    '4096': (139, 0, 139), '8192': (75, 0, 130), '16384': (232, 54, 99), '32768': (168, 15, 53),
    '#': (0, 0, 0, 0), '×2': (0, 28, 83), '×4': (89, 194, 225), '×0': (45, 215, 112),
    'null': (0, 0, 0, 0),
    'default': (0, 0, 0)
}
txt0 = {
    '2', '4', '#'
}

g_n, g_m = 4, 4

game_size = (400, 510)
grid_offset = (10, 120)
grid_size = (380, 380)
grid_gap = 8
grid_lattice = 85
grid_radius = 5
static_itembox_list = ItemBoxList([
    static_itembox((0, 0), game_size, clr['bg'], 10, clr['txt0'],
                   '', 36, 10),
    static_itembox((10, 10), (380, 70), clr['bg'], 5, clr['txt0'],
                    '2048_game', 50, 5),
    static_itembox((10, 80), (185, 30), clr['4'], 5, clr['txt0'],
                    'current: ', 20, 5),
    static_itembox((205, 80), (185, 30), clr['4'], 5, clr['txt0'],
                    'best: ', 20, 5),
    static_itembox((10, 120), (380, 380), clr['grid'], 10),
    *[static_itembox((1 + 10 + (j+1)*grid_gap + j*grid_lattice, 1 + 120 + (i+1)*grid_gap + i*grid_lattice),
                     (grid_lattice - 2, grid_lattice - 2), clr['0'], 5,
                     centered='c') for i in range(g_n) for j in range(g_m)]
])
static_itembox_list.offset = _ldiv(_sub(screen_size, game_size), 2)
grid_itembox_list = ItemBoxList([])
grid_itembox_list.offset = _add(static_itembox_list.offset, grid_offset)

lnum_topleft, rnum_topleft, lrnum_size = (10, 80), (205, 80), (185, 30)
lradd_movex, lradd_alpha, lradd_dalpha, lradd_anilen = (0, -20), 0.6, -0.01, 20

num_itembox_list = ItemBoxList([
    static_itembox(lnum_topleft, lrnum_size, clr['null'], 5, clr['txt0'],
                   '0', 20, 5, centered='r'),
    static_itembox(rnum_topleft, lrnum_size, clr['null'], 5, clr['txt0'],
                   '0', 20, 5, centered='r'),
    dynamic_itembox(None, lnum_topleft, lrnum_size, clr['null'], 5, clr['txt0'],
                   '', 20, 5, centered='r'),
    dynamic_itembox(None, rnum_topleft, lrnum_size, clr['null'], 5, clr['txt0'],
                   '', 20, 5, centered='r'),
])
lnum_itembox, rnum_itembox, ladd_itembox, radd_itembox = num_itembox_list.ls
num_itembox_list.offset = _ldiv(_sub(screen_size, game_size), 2)

bgscreen = pygame.Surface(screen_size, pygame.SRCALPHA)
aniscreen = pygame.Surface(screen_size, pygame.SRCALPHA)
def init_screen():
    display_screen.fill(clr['2'])
    static_itembox_list.blit_to(bgscreen)
    display_screen.blit(bgscreen, (0, 0))

class NumBoard:
    def __init__(self):
        self.lnum_bind = lnum_itembox
        self.lnum = 0
        self.rnum_bind = rnum_itembox
        self.rnum = 0
        self.ladd_bind = ladd_itembox
        self.radd_bind = radd_itembox
    def add(self, x):
        self.lnum += x
        ladd = x
        self.lnum_bind.text = str(self.lnum)
        self.lnum_bind.changed = True
        self.ladd_bind = dynamic_itembox(self.ladd_bind, lnum_topleft, lrnum_size, clr['null'], 5, clr['txt0'],
                       f'{ladd:+}', 20, 5, centered='r')
        self.ladd_bind.alpha, self.ladd_bind.dalpha, self.ladd_bind.realphaed = lradd_alpha, lradd_dalpha, True
        self.ladd_bind.start, self.ladd_bind.end = lnum_topleft, _add(lradd_movex, lnum_topleft)
        self.ladd_bind.state, self.ladd_bind.endstate = 0, lradd_anilen
        if self.lnum > self.rnum:
            radd = self.lnum - self.rnum
            self.rnum = self.lnum
            self.rnum_bind.text = str(self.rnum)
            self.rnum_bind.changed = True
            self.radd_bind = dynamic_itembox(self.radd_bind, rnum_topleft, lrnum_size, clr['null'], 5, clr['txt0'],
                           f'{radd:+}', 20, 5, centered='r')
            self.radd_bind.alpha, self.radd_bind.dalpha, self.radd_bind.realphaed = lradd_alpha, lradd_dalpha, True
            self.radd_bind.start, self.radd_bind.end = rnum_topleft, _add(lradd_movex, rnum_topleft)
            self.radd_bind.state, self.radd_bind.endstate = 0, lradd_anilen
numboard = NumBoard()

def to_str(x):
    if x < 0:
        if x == -1: return '#'
        if x == -3: return '×0'
        return '×'+str(-x)
    return str(x)
def grid_palette(s):
    if s in clr: return clr[s], clr['txt0' if s in txt0 else 'txt1']
    return clr['default'], clr['txt1']
def grid_font(s):
    return (36 if len(s)<4 else 128//len(s)), 5

class GridBox:
    def set_to(self, pos, x):
        self.x = x
        s = to_str(x)
        c1, c2 = grid_palette(s)
        fnt, pd = grid_font(s)
        pos = _transpose(pos)
        gridpos = _add(_mul(pos, grid_gap + grid_lattice), (grid_gap, grid_gap))
        self.bind = dynamic_itembox(self.bind, gridpos, (grid_lattice, grid_lattice), c1, grid_radius, c2, s, fnt, pd, 'c')
    def __init__(self, pos, x): # plan + lazy deleting
        # self.pos = None
        self.x = None
        self.bind = None
        self.set_to(pos, x)
    def setani_move(self, start, end):
        self.bind.state = 0
        spos = _add(_mul(_transpose(start), grid_gap + grid_lattice), (grid_gap, grid_gap))
        epos = _add(_mul(_transpose(end), grid_gap + grid_lattice), (grid_gap, grid_gap))
        self.bind.topleft = spos
        self.bind.start = spos
        self.bind.end = epos
    def setani_resize(self, pos, start = 0.0, end = 1.0):
        self.bind.state = 0
        ssiz = _toint(_mul((grid_lattice, grid_lattice), start))
        esiz = _toint(_mul((grid_lattice, grid_lattice), end))
        cpos = _add(_mul(_transpose(pos), grid_gap + grid_lattice), (grid_gap + grid_lattice//2, grid_gap + grid_lattice//2))
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
    def con_output(self, showbind=False):
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
    if x==-3 or y==-3: return -(x*y)*2
    if x==y:
        if x>0: return x*2
        else: return 2**((-x)*8)
    else: return 0

def g2048_move(direction):
    # n, m = grid.n, grid.m
    rj = grid.di_range[direction]; ri = grid.di_range[(direction+1)%4]
    t = grid.di_t[direction]
    q = []
    q2 = []
    b = 0
    sc = 0
    print(f'di={direction}')
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
    q2.append(('score', sc))
    grid.con_output()
    return b, q, q2

# customed
basicfactor = 1
def getrandomblock():
    r = random.randint(0, 99)
    if r < 94:
        return (4 if (r<10) else 2)*basicfactor
    else:
        if r<97: return -1
        else:
            r = random.randint(0, 9)
            return -4 if r==0 else -3 if r<4 else -2
    # return 2**8
def g2048_addnew(q2):
    n, m = grid.n, grid.m
    s = sum(not grid[i, j] for i in range(n) for j in range(m))
    r = random.randint(1, s)
    x = getrandomblock()
    for i in range(n):
        for j in range(m):
            if not grid[i, j]:
                r -= 1
                if r == 0:
                    grid[i, j] = x
                    q2.append(('new', (i, j), x))
    if s > 1: return 1
    if any(craft(grid[i, j], grid[i+1, j]) is not None for i in range(n-1) for j in range(m)): return 1
    if any(craft(grid[i, j], grid[i, j+1]) is not None for i in range(n) for j in range(m-1)): return 1
    return 0

di_map = {'a': 0, 's': 1, 'd': 2, 'w': 3}
alive = 1
SchedEnd = -1

def g2048_input(key): #!
    global alive, sched_cnt
    if not alive: return
    di = di_map[key]
    b, q, q2 = g2048_move(di)
    if not b: return
    alive = g2048_addnew(q2)
    if not alive:
        q2.append(('over',))
    if q:
        sched_queue.extend([q]+[None]*(anips-3))
    if q2:
        sched_queue.extend([q2]+[None]*(anips-3))
    sched_queue.extend([None]*2+[SchedEnd])
    sched_cnt += 1

sched_queue = deque()
sched_cnt = 0
def g2048_handle(events):
    global sched_cnt
    if events is None: return
    if events is SchedEnd: sched_cnt -= 1; return
    for event in events:
        name = event[0]
        print(*event)
        if name == 'mov':
            start, end = event[1:] #!
            # print(grid.bind)
            grid.get(start).setani_move(start, end)
        elif name == '$mov':
            start, end = event[1:] #!
            grid.movebind(start, end, grid_itembox_list)#?
        elif name == 'double':
            pos, x = event[1:] #!
            grid.get(pos).set_to(pos, x)
        elif name == 'new':
            pos, x = event[1:] #!
            # print(pos, x)
            grid.newbind(pos, GridBox(pos, x), grid_itembox_list)
            grid.get(pos).setani_resize(pos, 0.5)
            # print(*map(type, grid_itembox_list.ls))
        elif name == 'score':
            x, = event[1:]
            numboard.add(x)
            #!
        elif name == 'over':
            pass #!

def g2048_process():
    while sched_cnt > 1 and sched_queue:
        g2048_handle(sched_queue.popleft())
    if sched_queue:
        g2048_handle(sched_queue.popleft())
    # print(grid.bind)
    grid.send_to_list(grid_itembox_list) #!
    # grid.con_output()
    grid_itembox_list.nextstate(display_screen)
    num_itembox_list.nextstate(display_screen)

def g2048_init():
    global alive
    q2 = []
    alive = g2048_addnew(q2)
    if not alive:
        q2.append(('over',))
    if q2:
        sched_queue.extend([q2])
    g2048_process()

grid = Grid(4, 4)
key_map = {pygame.K_a: (1, 'a'), pygame.K_s: (1, 's'), pygame.K_d: (1, 'd'), pygame.K_w: (1, 'w')}

def UIloop():
    running = True
    refresh = 0
    init_screen()
    g2048_init()
    while running:
        for event in pygame.event.get():
            if event.type == pygame.QUIT: running = False
            elif event.type == pygame.KEYDOWN:
                if event.key in key_map:
                    fn, ch = key_map[event.key]
                    if fn == 1:
                        g2048_input(ch)
            elif event.type == pygame.MOUSEBUTTONDOWN:
                pass
        if refresh == 0: # plan: lazy updating
            display_screen.blit(bgscreen, (0, 0))
            g2048_process()
            pygame.display.flip()
        time_clock.tick(128)

UIloop()
pygame.quit()