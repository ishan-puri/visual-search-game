import pygame, sys, random, math, json, time, os
from dataclasses import dataclass
from typing import List, Tuple

WIDTH, HEIGHT = 960, 720
FPS = 60
MARGIN = 60

PALETTE = {
    "bg": (18, 18, 22),
    "panel": (28, 28, 36),
    "accent": (120, 190, 255),
    "ok": (80, 220, 100),
    "bad": (240, 90, 90),
    "warn": (255, 195, 0),
    "white": (240, 240, 245),
    "muted": (170, 170, 180),
    "blue": (0, 114, 178),
    "orange": (230, 159, 0),
    "sky": (86, 180, 233),
    "green": (0, 158, 115),
    "yellow": (240, 228, 66),
    "red": (213, 94, 0),
    "purple": (204, 121, 167),
}

SHAPES = ["circle", "square", "triangle"]
COLOR_NAMES = ["blue", "orange", "sky", "green", "yellow", "red", "purple"]

HIGHSCORE_FILE = "focusforge_highscores.json"

class Button:
    def __init__(self, rect, text, font, on_click, fg=PALETTE["white"], bg=PALETTE["panel"]):
        self.rect = pygame.Rect(rect)
        self.text = text
        self.font = font
        self.on_click = on_click
        self.fg = fg
        self.bg = bg
        self.hover = False
    def draw(self, surf):
        color = tuple(min(255, c + (18 if self.hover else 0)) for c in self.bg)
        pygame.draw.rect(surf, color, self.rect, border_radius=14)
        label = self.font.render(self.text, True, self.fg)
        surf.blit(label, label.get_rect(center=self.rect.center))
    def handle(self, event):
        if event.type == pygame.MOUSEMOTION:
            self.hover = self.rect.collidepoint(event.pos)
        elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            if self.rect.collidepoint(event.pos):
                self.on_click()

class Toggle:
    def __init__(self, pos, text, font, initial=False, on_change=None):
        self.pos = pos
        self.text = text
        self.font = font
        self.value = initial
        self.on_change = on_change
        self.rect = pygame.Rect(pos[0], pos[1], 46, 26)
    def draw(self, surf):
        label = self.font.render(self.text, True, PALETTE["white"])
        surf.blit(label, (self.pos[0] + 60, self.pos[1]-2))
        bg = PALETTE["panel"]
        pygame.draw.rect(surf, bg, self.rect, border_radius=13)
        knob_x = self.rect.x + (26 if self.value else 4)
        knob_color = PALETTE["ok"] if self.value else PALETTE["muted"]
        pygame.draw.circle(surf, knob_color, (knob_x+9, self.rect.y+13), 11)
    def handle(self, event):
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            if self.rect.collidepoint(event.pos):
                self.value = not self.value
                if self.on_change: self.on_change(self.value)

class Particle:
    def __init__(self, pos, vel, life, size):
        self.x, self.y = pos
        self.vx, self.vy = vel
        self.life = life
        self.size = size
        self.t = 0
    def update(self, dt):
        self.t += dt
        self.x += self.vx * dt
        self.y += self.vy * dt
        self.vy += 200 * dt
        return self.t < self.life
    def draw(self, surf):
        alpha = max(0, 255 * (1 - self.t / self.life))
        color = (*PALETTE["ok"], int(alpha))
        s = pygame.Surface((self.size*2, self.size*2), pygame.SRCALPHA)
        pygame.draw.circle(s, color, (self.size, self.size), self.size)
        surf.blit(s, (self.x - self.size, self.y - self.size))

class Highscores:
    def __init__(self, path):
        self.path = path
        self.data = {"classic": [], "conjunction": [], "mixed": []}
        self.load()
    def load(self):
        try:
            if os.path.exists(self.path):
                with open(self.path, "r") as f:
                    self.data = json.load(f)
        except Exception:
            self.data = {"classic": [], "conjunction": [], "mixed": []}
    def save(self):
        try:
            with open(self.path, "w") as f:
                json.dump(self.data, f, indent=2)
        except Exception as e:
            print("Could not save highscores:", e)
    def add(self, mode, score, details):
        arr = self.data.get(mode, [])
        arr.append({"score": score, "ts": int(time.time()), "details": details})
        arr.sort(key=lambda x: -x["score"])
        self.data[mode] = arr[:10]
        self.save()

@dataclass
class Item:
    x: int
    y: int
    size: int
    shape: str
    color_name: str
    is_target: bool = False
    angle: float = 0.0
    def rect(self) -> pygame.Rect:
        return pygame.Rect(self.x - self.size, self.y - self.size, self.size*2, self.size*2)
    def draw(self, surf):
        color = PALETTE[self.color_name]
        cx, cy, r = self.x, self.y, self.size
        if self.shape == "circle":
            pygame.draw.circle(surf, color, (cx, cy), r)
        elif self.shape == "square":
            pygame.draw.rect(surf, color, (cx - r, cy - r, 2*r, 2*r))
        elif self.shape == "triangle":
            pts = [
                (cx + r*math.cos(self.angle), cy + r*math.sin(self.angle)),
                (cx + r*math.cos(self.angle+2.094), cy + r*math.sin(self.angle+2.094)),
                (cx + r*math.cos(self.angle+4.188), cy + r*math.sin(self.angle+4.188)),
            ]
            pygame.draw.polygon(surf, color, pts)

def generate_positions(n: int, pad: int, rng: random.Random):
    positions = []
    attempts = 0
    while len(positions) < n and attempts < n*200:
        attempts += 1
        x = rng.randint(MARGIN+pad, WIDTH-MARGIN-pad)
        y = rng.randint(MARGIN+pad+40, HEIGHT-MARGIN-pad)
        ok = True
        for px, py in positions:
            if (px-x)**2 + (py-y)**2 < (pad*2.5)**2:
                ok = False
                break
        if ok:
            positions.append((x, y))
    if len(positions) < n:
        cols = int(math.sqrt(n))
        rows = math.ceil(n / cols)
        gx = (WIDTH - 2*MARGIN) / (cols+1)
        gy = (HEIGHT - 2*MARGIN - 80) / (rows+1)
        positions = []
        for r in range(rows):
            for c in range(cols):
                if len(positions) >= n: break
                positions.append((int(MARGIN+(c+1)*gx), int(MARGIN+80+(r+1)*gy)))
    return positions

def make_items(mode: str, level: int, rng: random.Random) -> Tuple[List[Item], dict]:
    set_size = min(8 + level*2, 60)
    size = max(12, 26 - level//2)
    heterogeneity = min(1.0, 0.3 + level*0.05)
    rotation = min(1.0, 0.2 + level*0.03)
    crowding = min(1.0, level*0.06)
    positions = generate_positions(set_size, size+6, rng)
    if mode == "classic":
        target_shape = rng.choice(SHAPES)
        distract_shape = target_shape
        if rng.random() < 0.5:
            while distract_shape == target_shape:
                distract_shape = rng.choice(SHAPES)
            target_color = rng.choice(COLOR_NAMES)
            distract_color = target_color
        else:
            target_color = rng.choice(COLOR_NAMES)
            distract_color = target_color
            while distract_color == target_color:
                distract_color = rng.choice(COLOR_NAMES)
    elif mode == "conjunction":
        target_shape = rng.choice(SHAPES)
        target_color = rng.choice(COLOR_NAMES)
        d1_shape = target_shape; d1_color = rng.choice([c for c in COLOR_NAMES if c != target_color])
        d2_shape = rng.choice([s for s in SHAPES if s != target_shape]); d2_color = target_color
        distract_pairs = [(d1_shape, d1_color), (d2_shape, d2_color)]
    else:
        if rng.random() < 0.65:
            return make_items("classic", level, rng)
        elif rng.random() < 0.95:
            return make_items("conjunction", level, rng)
        else:
            target_shape = rng.choice(SHAPES)
            target_color = rng.choice(COLOR_NAMES)
            distract_shape = target_shape
            distract_color = target_color
    items: List[Item] = []
    target_index = rng.randrange(set_size)
    for i, (x, y) in enumerate(positions):
        if i == target_index:
            angle = rng.random()*math.tau if rng.random() < rotation else 0.0
            tsize = size if mode != "mixed" else int(size*1.4)
            items.append(Item(x, y, tsize, target_shape, target_color, True, angle))
        else:
            if mode == "conjunction":
                shape, color = rng.choice(distract_pairs)
            else:
                shape = distract_shape
                color = distract_color
            if rng.random() < heterogeneity*0.35:
                if rng.random() < 0.5:
                    shape = rng.choice(SHAPES)
                else:
                    color = rng.choice(COLOR_NAMES)
            angle = rng.random()*math.tau if rng.random() < rotation else 0.0
            items.append(Item(x, y, size, shape, color, False, angle))
    if crowding > 0 and len(items) >= 5:
        tx, ty = items[target_index].x, items[target_index].y
        crowd_n = int(2 + crowding*4)
        for _ in range(crowd_n):
            dx = int(rng.uniform(-size*2.5, size*2.5))
            dy = int(rng.uniform(-size*2.5, size*2.5))
            if dx*dx + dy*dy < (size*1.2)**2:
                dy += int(size*1.5)
            shape = rng.choice(SHAPES)
            color = rng.choice(COLOR_NAMES)
            angle = rng.random()*math.tau if rng.random() < rotation else 0.0
            items.append(Item(tx+dx, ty+dy, max(8, size-2), shape, color, False, angle))
    rule = {"mode": mode, "desc": ""}
    if mode == "classic":
        if distract_shape != target_shape:
            rule["desc"] = f"Find the only {target_shape} among {distract_shape}s"
        else:
            rule["desc"] = f"Find the only {target_color} item"
    elif mode == "conjunction":
        rule["desc"] = f"Find the only {target_color} {target_shape} (others share its color or shape)"
    else:
        rule["desc"] = "Find the unique oddball (size/feature)"
    return items, rule

class Game:
    def __init__(self):
        pygame.init()
        pygame.display.set_caption("FocusForge: Visual Search & Attention")
        self.screen = pygame.display.set_mode((WIDTH, HEIGHT))
        self.clock = pygame.time.Clock()
        self.font = pygame.font.SysFont("futura", 24)
        self.big = pygame.font.SysFont("futura", 48, bold=True)
        self.small = pygame.font.SysFont("futura", 18)
        self.state = "menu"
        self.mode = "mixed"
        self.level = 1
        self.score = 0
        self.round_time = 12.0
        self.time_left = self.round_time
        self.combo = 0
        self.misses = 0
        self.items: List[Item] = []
        self.rule = {}
        self.particles: List[Particle] = []
        self.rng = random.Random()
        self.rng.seed()
        self.highscores = Highscores(HIGHSCORE_FILE)
        self.buttons: List[Button] = []
        self.toggles: List[Toggle] = []
        self.sound = None
        self.load_sound()
        self.build_menu()
    def load_sound(self):
        try:
            pygame.mixer.init()
            self.sound = pygame.mixer.Sound(buffer=self._make_beep())
        except Exception:
            self.sound = None
    def _make_beep(self, freq=880, ms=80):
        import array
        sample_rate = 44100
        n_samples = int(sample_rate * ms / 1000)
        arr = array.array('h')
        for i in range(n_samples):
            t = i / sample_rate
            val = int(3000 * math.sin(2*math.pi*freq*t))
            arr.append(val)
        return arr.tobytes()
    def build_menu(self):
        self.buttons.clear()
        gap = 70
        start_y = 260
        def start_mode(m):
            return lambda: self.start_game(m)
        self.buttons.append(Button((WIDTH//2-140, start_y, 280, 56), "Start: MIXED", self.font, start_mode("mixed"), bg=PALETTE["accent"]))
        self.buttons.append(Button((WIDTH//2-140, start_y+gap, 280, 56), "Start: CLASSIC", self.font, start_mode("classic")))
        self.buttons.append(Button((WIDTH//2-140, start_y+2*gap, 280, 56), "Start: CONJUNCTION", self.font, start_mode("conjunction")))
        self.buttons.append(Button((WIDTH//2-140, start_y+3*gap, 280, 56), "View High Scores", self.font, self.view_scores))
        self.toggles = [
            Toggle((WIDTH//2-220, start_y-60), "Hardcore (shorter timer, harsher penalties)", self.small, False),
            Toggle((WIDTH//2+80, start_y-60), "Zen mode (no timer, practice)", self.small, False),
        ]
    def start_game(self, mode):
        self.mode = mode
        self.level = 1
        self.score = 0
        self.combo = 0
        self.misses = 0
        self.state = "play"
        hardcore = self.toggles[0].value
        zen = self.toggles[1].value
        self.round_time = 10.0 if hardcore else 12.0
        if zen:
            self.round_time = 9999.0
        self.new_round()
    def view_scores(self):
        self.state = "scores"
    def new_round(self):
        self.items, self.rule = make_items(self.mode, self.level, self.rng)
        self.time_left = self.round_time
        self.particles.clear()
    def update_particles(self, dt):
        self.particles = [p for p in self.particles if p.update(dt)]
    def add_burst(self, pos):
        for _ in range(24):
            ang = random.random()*math.tau
            spd = random.uniform(120, 260)
            vel = (math.cos(ang)*spd, math.sin(ang)*spd)
            self.particles.append(Particle(pos, vel, life=random.uniform(0.3, 0.7), size=random.randint(2,4)))
    def handle_click(self, pos):
        hit_target = False
        for it in sorted(self.items, key=lambda i: i.is_target, reverse=True):
            if it.rect().collidepoint(pos):
                if it.is_target:
                    hit_target = True
                    self.combo += 1
                    base = 100
                    time_bonus = int(max(0, self.time_left) * 8)
                    streak_bonus = min(150, self.combo*15)
                    gain = base + time_bonus + streak_bonus
                    self.score += gain
                    self.add_burst((it.x, it.y))
                    if self.sound: self.sound.play()
                    self.level += 1
                    self.new_round()
                else:
                    self.combo = 0
                    self.misses += 1
                    self.time_left -= 1.2
                break
        if not hit_target and self.state == "play":
            self.time_left -= 0.25
    def run(self):
        while True:
            dt = self.clock.tick(FPS)/1000.0
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    pygame.quit(); sys.exit(0)
                if self.state == "menu":
                    for b in self.buttons: b.handle(event)
                    for t in self.toggles: t.handle(event)
                elif self.state == "play":
                    if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
                        self.state = "menu"
                    if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                        self.handle_click(event.pos)
                elif self.state == "scores":
                    if event.type == pygame.KEYDOWN or (event.type==pygame.MOUSEBUTTONDOWN and event.button==1):
                        self.state = "menu"
            if self.state == "play":
                if self.time_left < 9999:
                    self.time_left -= dt
                self.update_particles(dt)
                if self.time_left <= 0:
                    self.highscores.add(self.mode, self.score, {"level": self.level, "misses": self.misses, "combo": self.combo})
                    self.state = "gameover"
                    self.go_ts = time.time()
            self.draw()
    def draw_hud(self):
        pygame.draw.rect(self.screen, PALETTE["panel"], (0,0, WIDTH, 64))
        title = self.font.render(f"Mode: {self.mode.upper()}   Level: {self.level}", True, PALETTE["white"])
        self.screen.blit(title, (16, 18))
        if self.round_time < 9999:
            frac = max(0.0, min(1.0, self.time_left / self.round_time))
            bw = int(frac * 220)
            pygame.draw.rect(self.screen, PALETTE["muted"], (WIDTH-260, 20, 220, 16), border_radius=8)
            pygame.draw.rect(self.screen, PALETTE["ok"] if frac>0.35 else PALETTE["bad"], (WIDTH-260, 20, bw, 16), border_radius=8)
            t = self.small.render(f"{self.time_left:0.1f}s", True, PALETTE["white"])
            self.screen.blit(t, (WIDTH-260, 40))
        else:
            t = self.small.render("Zen mode (no timer)", True, PALETTE["white"])
            self.screen.blit(t, (WIDTH-260, 28))
        score = self.font.render(f"Score: {self.score}", True, PALETTE["accent"])
        self.screen.blit(score, (WIDTH//2 - score.get_width()//2, 18))
        rule = self.small.render(self.rule.get("desc",""), True, PALETTE["yellow"])
        self.screen.blit(rule, (16, 42))
    def draw(self):
        self.screen.fill(PALETTE["bg"])
        if self.state == "menu":
            head = self.big.render("FocusForge", True, PALETTE["accent"])
            sub = self.small.render("A Visual Search & Attention Game", True, PALETTE["muted"])
            self.screen.blit(head, head.get_rect(center=(WIDTH//2, 120)))
            self.screen.blit(sub, sub.get_rect(center=(WIDTH//2, 160)))
            for b in self.buttons: b.draw(self.screen)
            for t in self.toggles: t.draw(self.screen)
            legend = [
                "CLASSIC: Find a pop-out by single feature (color OR shape).",
                "CONJUNCTION: Find the unique color+shape combo.",
                "MIXED: Learns your pace; throws surprises.",
                "Scoring: Speed + streaks; misses cut time.",
            ]
            for i, line in enumerate(legend):
                lab = self.small.render(line, True, PALETTE["muted"])
                self.screen.blit(lab, (WIDTH//2 - 300, 520 + i*22))
            ft = self.small.render("Tip: Click ESC in-game to return here.", True, PALETTE["muted"])
            self.screen.blit(ft, (16, HEIGHT-28))
        elif self.state == "play":
            self.draw_hud()
            for it in self.items:
                it.draw(self.screen)
            for p in self.particles:
                p.draw(self.screen)
        elif self.state == "scores":
            head = self.big.render("High Scores", True, PALETTE["accent"])
            self.screen.blit(head, head.get_rect(center=(WIDTH//2, 100)))
            x = WIDTH//2 - 360
            y = 180
            for mode in ["mixed", "classic", "conjunction"]:
                title = self.font.render(mode.upper(), True, PALETTE["white"])
                self.screen.blit(title, (x, y-40))
                arr = self.highscores.data.get(mode, [])
                if not arr:
                    none = self.small.render("No scores yet. Play a round!", True, PALETTE["muted"])
                    self.screen.blit(none, (x, y))
                for i, row in enumerate(arr[:10]):
                    line = f"{i+1:>2}. {row['score']:>6}   L:{row['details'].get('level',0):<3}  Miss:{row['details'].get('misses',0):<2}  Best x{row['details'].get('combo',0)}"
                    lab = self.small.render(line, True, PALETTE["muted"])
                    self.screen.blit(lab, (x, y + i*24))
                x += 260
            sub = self.small.render("Press any key or click to return.", True, PALETTE["muted"])
            self.screen.blit(sub, sub.get_rect(center=(WIDTH//2, HEIGHT-60)))
        elif self.state == "gameover":
            head = self.big.render("Time!", True, PALETTE["accent"])
            self.screen.blit(head, head.get_rect(center=(WIDTH//2, 170)))
            sc = self.font.render(f"Final Score: {self.score}", True, PALETTE["white"])
            self.screen.blit(sc, sc.get_rect(center=(WIDTH//2, 230)))
            st = self.small.render(f"Level reached: {self.level}   Misses: {self.misses}   Best streak: x{self.combo}", True, PALETTE["muted"])
            self.screen.blit(st, st.get_rect(center=(WIDTH//2, 270)))
            prompt = self.small.render("Click to play again, or press ESC for menu.", True, PALETTE["muted"])
            self.screen.blit(prompt, prompt.get_rect(center=(WIDTH//2, 320)))
            for event in pygame.event.get(pump=True):
                pass
            pressed = pygame.mouse.get_pressed()[0] or any(pygame.key.get_pressed())
            if time.time() - getattr(self, "go_ts", time.time()) > 0.6 and pressed:
                self.state = "menu"
        pygame.display.flip()

def main():
    Game().run()

if __name__ == "__main__":
    main()
