# Renders a contact sheet of every device screen using the
# SAME coordinates/colors as src/main.cpp, to visually check
# the UI before flashing. Python 3 + Pillow only.

from PIL import Image, ImageDraw, ImageFont
import math
import os

W, H = 160, 128
SCALE = 2

def col8(r, g, b):
    # approximate the RGB565 quantization used on the TFT
    r = (r & 0xF8) | (r >> 5)
    g = (g & 0xFC) | (g >> 6)
    b = (b & 0xF8) | (b >> 5)
    return (r, g, b)

BG        = col8(10, 10, 20)
PANEL     = col8(16, 24, 48)
PANEL_LT  = col8(22, 50, 74)
HEADER    = col8(21, 101, 216)
BLUE      = col8(33, 150, 243)
CYAN      = col8(79, 195, 247)
GREEN     = col8(34, 197, 94)
RED       = col8(229, 57, 53)
GOLD      = col8(245, 197, 24)
YELLOW    = col8(255, 215, 0)
GRAY      = col8(154, 160, 166)
DIM       = col8(100, 108, 130)
TRACK     = col8(42, 47, 58)
PINK      = col8(240, 98, 146)
WHITE     = (255, 255, 255)
BLACK     = (0, 0, 0)

def font(size):
    try:
        return ImageFont.load_default(size)
    except TypeError:
        return ImageFont.load_default()

class Screen:
    def __init__(self):
        self.img = Image.new("RGB", (W, H), BG)
        self.d = ImageDraw.Draw(self.img)

    # ---- primitives mirroring Adafruit_GFX ----

    def text(self, x, y, s, color, size=1):
        # classic 5x7 font: 6x8 px per char at size 1
        f = font(8 * size - 2)
        self.d.text((x, y), s, fill=color, font=f)

    def text_centered(self, s, y, color, size=1):
        w = len(s) * 6 * size
        x = max(0, (W - w) // 2)
        self.text(x, y, s, color, size)

    def title_auto(self, s, y, color):
        size = 2 if len(s) * 12 <= 152 else 1
        self.text_centered(s, y, color, size)

    def wrapped(self, s, x, y, max_y, chars, color):
        remaining = s
        while remaining and y < max_y:
            n = min(chars, len(remaining))
            if n < len(remaining):
                # match Arduino lastIndexOf(' ', n): end index included
                sp = remaining.rfind(' ', 0, n + 1)
                if sp > 0:
                    n = sp
            line = remaining[:n].strip()
            self.text(x, y, line, color)
            remaining = remaining[n:].strip()
            y += 10

    def wrapped_centered(self, s, y, chars, color, max_lines=3):
        remaining = s
        lines = 0
        while remaining and lines < max_lines:
            n = min(chars, len(remaining))
            if n < len(remaining):
                sp = remaining.rfind(' ', 0, n + 1)
                if sp > 0:
                    n = sp
            line = remaining[:n].strip()
            self.text_centered(line, y, color)
            remaining = remaining[n:].strip()
            y += 11
            lines += 1

    def rrect(self, box, r, fill=None, outline=None):
        self.d.rounded_rectangle(box, radius=r, fill=fill, outline=outline)

    def circle(self, cx, cy, r, fill=None, outline=None):
        b = [cx - r, cy - r, cx + r, cy + r]
        self.d.ellipse(b, fill=fill, outline=outline)

    def line(self, x1, y1, x2, y2, color):
        self.d.line([x1, y1, x2, y2], fill=color)

    def tri(self, pts, fill=None, outline=None):
        self.d.polygon(pts, fill=fill, outline=outline)

    # ---- icons ----

    def arcs(self, cx, cy, r, color):
        for side in (-1, 1):
            pts = []
            for a in range(-50, 51, 5):
                rad = math.radians(a)
                pts.append((cx + side * r * math.cos(rad),
                            cy - r * math.sin(rad)))
            self.d.line(pts, fill=color)

    def ring_arc(self, cx, cy, r, start, span, color):
        pts = []
        for a in range(start, start + span + 5, 5):
            rad = math.radians(a)
            pts.append((cx + r * math.cos(rad), cy + r * math.sin(rad)))
        self.d.line(pts, fill=color)

    def spinner(self, cx, cy, r, angle):
        self.circle(cx, cy, r, outline=TRACK)
        self.circle(cx, cy, r - 1, outline=TRACK)
        self.ring_arc(cx, cy, r, angle, 90, BLUE)
        self.ring_arc(cx, cy, r - 1, angle, 90, BLUE)

    def check_circle(self, cx, cy, r, color):
        self.circle(cx, cy, r, fill=color)
        for i in range(3):
            self.line(cx - r//2 - 1 + i, cy + 1, cx - 3 + i, cy + r//2, WHITE)
            self.line(cx - 3 + i, cy + r//2, cx + r//2 + 1 + i, cy - r//2, WHITE)

    def exclaim(self, cx, cy, r, color):
        self.circle(cx, cy, r, fill=color)
        self.d.rectangle([cx-2, cy-r+4, cx+1, cy-2], fill=WHITE)
        self.d.rectangle([cx-2, cy+3, cx+1, cy+6], fill=WHITE)

    def clock_small(self, cx, cy, color):
        self.circle(cx, cy, 4, outline=color)
        self.line(cx, cy, cx, cy-3, color)
        self.line(cx, cy, cx+2, cy+1, color)

    def clock_big(self, cx, cy, r, color):
        self.circle(cx, cy, r, outline=color)
        self.circle(cx, cy, r-1, outline=color)
        self.line(cx, cy, cx, cy-r+4, color)
        self.line(cx, cy, cx, cy-r+5, color)
        self.line(cx, cy, cx+r-5, cy+2, color)
        self.line(cx, cy, cx+r-6, cy+2, color)

    def wifi_lost(self, cx, cy):
        self.circle(cx, cy+4, 3, fill=RED)
        for r in (7, 8, 12, 13):
            self.arcs(cx, cy+4, r, RED)
        self.line(cx-16, cy-16, cx+16, cy+10, RED)
        self.line(cx-16, cy-15, cx+16, cy+11, RED)

    def hourglass(self, cx, cy):
        self.tri([(cx-11, cy-13), (cx+11, cy-13), (cx, cy-1)], outline=BLUE)
        self.tri([(cx-11, cy+13), (cx+11, cy+13), (cx, cy+1)], outline=BLUE)
        self.tri([(cx-4, cy-11), (cx+4, cy-11), (cx, cy-4)], fill=GOLD)
        self.tri([(cx-6, cy+11), (cx+6, cy+11), (cx, cy+5)], fill=GOLD)

    def paper_plane(self, cx, cy):
        self.circle(cx, cy, 16, fill=PANEL)
        self.tri([(cx-8, cy+8), (cx+9, cy-9), (cx+9, cy-3)], fill=WHITE)
        self.tri([(cx-8, cy+8), (cx+9, cy-3), (cx-1, cy+1)], fill=CYAN)

    def trophy(self, cx, cy):
        self.circle(cx, cy, 17, fill=GOLD)
        self.rrect([cx-8, cy-11, cx+7, cy-2], 2, fill=BG)
        self.circle(cx-11, cy-6, 3, outline=BG)
        self.circle(cx+11, cy-6, 3, outline=BG)
        self.d.rectangle([cx-1, cy-1, cx+1, cy+4], fill=BG)
        self.d.rectangle([cx-6, cy+5, cx+6, cy+7], fill=BG)
        for dx, dy, c in [(-26,-14,CYAN), (24,-10,PINK), (-30,8,GREEN),
                          (28,10,YELLOW), (-20,16,RED), (20,-18,CYAN),
                          (0,-22,PINK), (-14,-20,YELLOW)]:
            self.circle(cx+dx, cy+dy, 1, fill=c)

    def teacher(self, cx, cy):
        self.rrect([cx-24, cy-14, cx+23, cy+17], 4, outline=GOLD)
        self.rrect([cx-23, cy-13, cx+22, cy+16], 3, outline=GOLD)
        self.circle(cx, cy-3, 5, fill=WHITE)
        self.rrect([cx-9, cy+4, cx+8, cy+14], 4, fill=WHITE)

    def doc_icon(self, x, y, color):
        self.d.rectangle([x, y, x+9, y+11], outline=color)
        for i in range(3):
            self.line(x+2, y+3+i*3, x+7, y+3+i*3, color)

    def mini_clock(self, x, y, color):
        self.circle(x+5, y+5, 5, outline=color)
        self.line(x+5, y+5, x+5, y+1, color)
        self.line(x+5, y+5, x+8, y+6, color)

    def people_icon(self, x, y, color):
        self.circle(x+3, y+3, 3, fill=color)
        self.circle(x+11, y+4, 2, fill=DIM)
        self.rrect([x-1, y+7, x+7, y+12], 3, fill=color)
        self.rrect([x+8, y+7, x+14, y+12], 3, fill=DIM)

    # ---- chrome ----

    def app_header(self, title="PulseNet", connected=True):
        self.d.rectangle([0, 0, W-1, 15], fill=HEADER)
        self.line(0, 16, W-1, 16, CYAN)
        self.text(5, 4, title, WHITE)
        ic = WHITE if connected else DIM
        self.circle(147, 11, 2, fill=ic)
        self.arcs(147, 11, 4, ic)
        self.arcs(147, 11, 7, ic)

    def question_header(self):
        self.d.rectangle([0, 0, W-1, 15], fill=PANEL)
        self.line(0, 16, W-1, 16, CYAN)
        self.text(5, 4, "Q 3/10", WHITE)

    def button(self, x, y, w, h, color, label):
        self.rrect([x, y, x+w-1, y+h-1], 5, fill=PANEL, outline=color)
        self.rrect([x+1, y+1, x+w-2, y+h-2], 4, outline=color)
        self.text_centered(label, y + (h-8)//2, color)

# ---- screens ----

def scr_splash():
    s = Screen()
    # placeholder for the full-screen HCMUTE logo bitmap
    s.d.rectangle([0, 0, W-1, H-1], fill=WHITE)
    s.circle(80, 44, 26, outline=(122, 76, 141))
    s.circle(80, 44, 25, outline=(122, 76, 141))
    s.circle(80, 44, 24, outline=(122, 76, 141))
    s.text_centered("HCMUTE", 72, (122, 76, 141), 1)
    s.d.rectangle([0, 96, W-1, H-1], fill=WHITE)
    s.rrect([30, 104, 129, 111], 4, fill=TRACK)
    s.rrect([32, 106, 127, 109], 2, fill=HEADER)
    s.text_centered("Waiting for teacher...", 118, BLACK)
    return s

def scr_idle():
    s = Screen()
    s.app_header(connected=False)
    s.teacher(80, 40)
    s.title_auto("Waiting for teacher...", 68, WHITE)
    s.wrapped_centered("The quiz has not been started yet.", 88, 26, GRAY, 2)
    return s

def scr_lobby():
    s = Screen()
    s.app_header("Enter Student ID")
    s.rrect([10, 24, 149, 53], 5, fill=BG, outline=YELLOW)
    s.rrect([12, 26, 147, 51], 4, fill=PANEL)
    s.text(44, 31, "2310456_", YELLOW, 2)
    s.rrect([10, 62, 149, 107], 5, fill=PANEL)
    for i, (k, a) in enumerate([("0-9", "Input number"), ("*", "Clear"), ("#", "Confirm")]):
        y = 70 + i * 12
        s.text(24, y, k, CYAN)
        s.text(54, y, a, WHITE)
    return s

def scr_connecting():
    s = Screen()
    s.app_header()
    s.spinner(80, 46, 14, 40)
    s.title_auto("Joining...", 70, WHITE)
    s.wrapped_centered("Sending your information to the server.", 94, 24, GRAY, 2)
    return s

def scr_joined():
    s = Screen()
    s.app_header()
    s.check_circle(80, 34, 16, GREEN)
    s.text_centered("JOINED!", 58, GREEN, 2)
    s.text_centered("ID: 23104567", 80, WHITE)
    s.rrect([15, 94, 144, 119], 5, fill=PANEL)
    s.text_centered("Ready for quiz", 99, WHITE)
    s.text_centered("Please wait...", 109, GRAY)
    return s

def scr_quizinfo():
    s = Screen()
    s.app_header()
    s.text_centered("Quiz Information", 22, GOLD)
    s.wrapped_centered("IoT Final Review", 34, 26, CYAN, 2)
    s.rrect([12, 54, 147, 95], 5, fill=PANEL)
    y = 60
    s.doc_icon(24, y, CYAN); s.text(42, y+2, "10 questions", WHITE); y += 12
    s.mini_clock(24, y, CYAN); s.text(42, y+2, "15 minutes", WHITE); y += 12
    s.people_icon(24, y, CYAN); s.text(42, y+2, "Please get ready!", WHITE)
    s.button(25, 102, 110, 18, CYAN, "Waiting to start...")
    return s

def scr_countdown():
    s = Screen()
    s.app_header()
    s.text_centered("Quiz will start in", 22, WHITE)
    s.circle(80, 62, 22, outline=TRACK)
    s.circle(80, 62, 21, outline=TRACK)
    s.ring_arc(80, 62, 22, -90, 3*72, GOLD)
    s.ring_arc(80, 62, 21, -90, 3*72, GOLD)
    s.text_centered("3", 52, WHITE, 3)
    s.text_centered("Get ready!", 98, GOLD)
    return s

def scr_question():
    s = Screen()
    s.question_header()
    # clock in header
    s.d.rectangle([116, 0, 159, 15], fill=PANEL)
    s.clock_small(122, 8, GRAY)
    s.text(128, 4, "00:54", YELLOW)
    s.wrapped("Which protocol does PulseNet use for the device link?", 5, 21, 49, 26, WHITE)
    opts = ["Bluetooth Low Energy", "Wi-Fi Direct", "Zigbee Mesh", "LoRa WAN"]
    for i, o in enumerate(opts):
        y = 51 + i * 19
        if i == 0:
            s.rrect([3, y, 156, y+16], 4, fill=PANEL_LT, outline=CYAN)
            s.rrect([4, y+1, 155, y+15], 3, outline=CYAN)
            s.rrect([7, y+2, 19, y+14], 3, fill=CYAN)
            s.text(10, y+4, "A", BG)
        else:
            s.rrect([3, y, 156, y+16], 4, fill=PANEL)
            s.rrect([7, y+2, 19, y+14], 3, fill=HEADER)
            s.text(10, y+4, chr(65+i), WHITE)
        t = o if len(o) <= 22 else o[:19] + "..."
        s.text(24, y+5, t, WHITE)
    return s

def scr_sending():
    s = Screen()
    s.app_header()
    s.paper_plane(80, 44)
    s.spinner(80, 44, 21, 120)
    s.text_centered("Sending answer...", 76, CYAN)
    s.text_centered("Please wait...", 94, GRAY)
    return s

def scr_confirmed():
    s = Screen()
    s.app_header()
    s.check_circle(80, 30, 13, GREEN)
    s.text_centered("Answer sent!", 50, GREEN, 2)
    s.rrect([20, 70, 139, 97], 5, fill=PANEL)
    s.text(32, 76, "Q: 3/10", WHITE)
    s.text(32, 87, "Your answer: ", WHITE)
    s.d.text((32 + 13*6, 87), "A", fill=YELLOW, font=font(6))
    s.wrapped_centered("Waiting for next question...", 104, 26, GRAY, 2)
    return s

def scr_next():
    s = Screen()
    s.app_header()
    s.hourglass(80, 40)
    s.title_auto("Next question...", 72, WHITE)
    s.text_centered("Please wait...", 92, GRAY)
    return s

def scr_done():
    s = Screen()
    s.app_header()
    s.check_circle(80, 32, 14, GREEN)
    s.text_centered("All done!", 54, GREEN, 2)
    s.wrapped_centered("All questions answered.", 80, 26, WHITE, 1)
    s.wrapped_centered("Waiting for the quiz to end...", 100, 26, GRAY, 2)
    return s

def scr_result():
    s = Screen()
    s.app_header()
    s.trophy(80, 36)
    s.text_centered("Quiz Finished!", 58, WHITE)
    s.rrect([18, 68, 141, 105], 5, fill=PANEL)
    s.text(28, 74, "Correct: ", WHITE)
    s.d.text((28 + 9*6, 74), "8", fill=GREEN, font=font(6))
    s.d.text((28 + 10*6, 74), " / 10", fill=WHITE, font=font(6))
    s.text(28, 88, "Score:", WHITE)
    s.text(66, 86, "8.0/10", YELLOW, 2)
    s.text_centered("Thank you!", 112, GRAY)
    return s

def scr_lost():
    s = Screen()
    s.app_header(connected=False)
    s.wifi_lost(80, 38)
    s.title_auto("Connection Lost", 64, RED)
    s.wrapped_centered("Please stay in range of the classroom.", 86, 26, GRAY, 2)
    return s

def scr_invalid():
    s = Screen()
    s.app_header()
    s.exclaim(80, 36, 16, RED)
    s.title_auto("Invalid ID", 58, RED)
    s.wrapped_centered("This student ID is not registered or not allowed.", 82, 24, WHITE, 3)
    return s

def scr_timeup():
    s = Screen()
    s.app_header()
    s.clock_big(80, 38, 14, RED)
    s.title_auto("Time's up!", 60, RED)
    s.text_centered("No answer was sent.", 82, CYAN)
    s.button(25, 96, 110, 20, CYAN, "Next question...")
    return s

SCREENS = [
    ("1 Splash", scr_splash),
    ("15 Idle", scr_idle),
    ("2 Enter ID", scr_lobby),
    ("3 Connecting", scr_connecting),
    ("4 Joined", scr_joined),
    ("5 Quiz Info", scr_quizinfo),
    ("6 Countdown", scr_countdown),
    ("7 Question", scr_question),
    ("8 Sending", scr_sending),
    ("9 Confirmed", scr_confirmed),
    ("10 Next", scr_next),
    ("Done", scr_done),
    ("11 Finished", scr_result),
    ("12 Lost", scr_lost),
    ("13 Invalid", scr_invalid),
    ("14 Time up", scr_timeup),
]

def main():
    cols = 4
    rows = math.ceil(len(SCREENS) / cols)
    cw, ch = W * SCALE + 12, H * SCALE + 30
    sheet = Image.new("RGB", (cols * cw, rows * ch), (40, 44, 52))
    d = ImageDraw.Draw(sheet)
    f = font(11)
    for i, (label, fn) in enumerate(SCREENS):
        img = fn().img.resize((W * SCALE, H * SCALE), Image.NEAREST)
        cx, cy = (i % cols) * cw, (i // cols) * ch
        sheet.paste(img, (cx + 6, cy + 24))
        d.text((cx + 6, cy + 5), label, fill=WHITE, font=f)
    out = os.path.join(os.path.dirname(__file__), "ui_preview.png")
    sheet.save(out)
    print("saved:", out)

if __name__ == "__main__":
    main()
