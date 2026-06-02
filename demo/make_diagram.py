# Guardian - System Architecture diagram (Calm Instrument philosophy)
# Hand-rendered with Pillow at 2x supersampling for crisp output.
import os, math
from PIL import Image, ImageDraw, ImageFont, ImageFilter
import numpy as np

SS = 2
W, H = 2400, 1500
CW, CH = W * SS, H * SS
OUT = r"C:\Projects\Guardians\demo\guardian-architecture.png"
FDIR = r"C:\Windows\Fonts"


def font(name, size):
    return ImageFont.truetype(os.path.join(FDIR, name), int(round(size * SS)))


# ---- type ----
f_brand   = font("segoeuib.ttf", 64)
f_arch    = font("segoeuil.ttf", 38)
f_sub     = font("segoeui.ttf", 23)
f_kicker  = font("segoeuib.ttf", 15)
f_ctitle  = font("segoeuib.ttf", 29)
f_csub    = font("segoeui.ttf", 20)
f_body    = font("segoeui.ttf", 21)
f_bodysb  = font("segoeuib.ttf", 21)
f_small   = font("segoeui.ttf", 17)
f_tiny    = font("segoeui.ttf", 15)
f_chip    = font("segoeuib.ttf", 22)
f_chips   = font("segoeui.ttf", 15)
f_mono    = font("consola.ttf", 18)
f_leg     = font("segoeui.ttf", 18)
f_arrow   = font("segoeuib.ttf", 18)

# ---- color ----
BG_TOP=(16,21,32); BG_BOT=(9,12,19)
CARD=(22,28,39); CARDHUB=(25,33,47); CHIP=(16,22,32)
BORDER=(48,60,80); BORDER_SOFT=(35,44,59)
TEXT=(231,238,245); DIM=(151,164,183); FAINT=(101,113,133)
TEAL=(45,212,191); GREEN=(74,222,128); SLATE=(150,165,186)
RED=(248,113,113); AMBER=(251,191,36); VIOLET=(167,139,250)
WHITE=(246,249,252)


# ---- base: vertical gradient + soft teal glow behind the hub ----
col = (np.linspace(0,1,CH)[:,None] * (np.array(BG_BOT)-np.array(BG_TOP)) + np.array(BG_TOP)).astype(np.uint8)
img = Image.fromarray(np.repeat(col[:,None,:], CW, axis=1), "RGB").convert("RGBA")

glow = Image.new("RGBA",(CW,CH),(0,0,0,0))
gd = ImageDraw.Draw(glow)
gx, gy = int(1140*SS), int(640*SS)
gd.ellipse([gx-540*SS, gy-380*SS, gx+540*SS, gy+380*SS], fill=(45,212,191,30))
glow = glow.filter(ImageFilter.GaussianBlur(150*SS))
img = Image.alpha_composite(img, glow)
draw = ImageDraw.Draw(img)


def q(v): return int(round(v*SS))

def rrect(x0,y0,x1,y1,r,fill=None,outline=None,width=1):
    draw.rounded_rectangle([q(x0),q(y0),q(x1),q(y1)], radius=q(r),
                           fill=fill, outline=outline, width=max(1,q(width)))

def text(x,y,s,fnt,fill=TEXT,anchor="la"):
    draw.text((q(x),q(y)), s, font=fnt, fill=fill, anchor=anchor)

def tw(s,fnt):
    b=draw.textbbox((0,0),s,font=fnt); return (b[2]-b[0])/SS, (b[3]-b[1])/SS

def segs(x,y,parts,gap=0):
    cx=x
    for t,f,c in parts:
        draw.text((q(cx),q(y)), t, font=f, fill=c, anchor="la")
        cx += tw(t,f)[0] + gap
    return cx

def dot(x,y,r,color):
    draw.ellipse([q(x-r),q(y-r),q(x+r),q(y+r)], fill=color)

def hline(x0,x1,y,color=BORDER_SOFT,w=1):
    draw.line([(q(x0),q(y)),(q(x1),q(y))], fill=color, width=max(1,q(w)))

def bullet(x,y,label,c=TEAL,sub=None):
    dot(x+4,y+10,3.2,c)
    cx = segs(x+16, y, [(label, f_body, TEXT)])
    if sub: segs(cx+8, y+2, [(sub, f_small, FAINT)])


# ---- card rects ----
WX0,WY0,WX1,WY1 = 64,360,470,1018          # watch
BX0,BY0,BX1,BY1 = 720,250,1560,1044        # backend hub
EWX0,EWY0,EWX1,EWY1 = 1812,300,2336,724    # web
EFX0,EFY0,EFX1,EFY1 = 1812,772,2336,1196   # flutter
TWX0,TWY0,TWX1,TWY1 = 720,1092,1016,1244   # twilio
NNX0,NNY0,NNX1,NNY1 = 1196,1092,1560,1244  # llm / dgx
EMX0,EMY0,EMX1,EMY1 = 1044,1128,1176,1208  # 911 pill

cards = [(WX0,WY0,WX1,WY1,16),(BX0,BY0,BX1,BY1,20),(EWX0,EWY0,EWX1,EWY1,16),
         (EFX0,EFY0,EFX1,EFY1,16),(TWX0,TWY0,TWX1,TWY1,14),(NNX0,NNY0,NNX1,NNY1,14)]

# ---- soft shadows under cards ----
sh = Image.new("RGBA",(CW,CH),(0,0,0,0))
sd = ImageDraw.Draw(sh)
for x0,y0,x1,y1,r in cards:
    sd.rounded_rectangle([q(x0+4),q(y0+12),q(x1+4),q(y1+14)], radius=q(r), fill=(0,0,0,120))
sh = sh.filter(ImageFilter.GaussianBlur(16*SS))
img.alpha_composite(sh)
draw = ImageDraw.Draw(img)


# ============================ HEADER ============================
# shield mark
sxc, stop, sw, shh = 95, 60, 56, 70
spts=[(sxc-sw/2,stop),(sxc+sw/2,stop),(sxc+sw/2,stop+shh*0.46),(sxc,stop+shh),(sxc-sw/2,stop+shh*0.46)]
draw.polygon([(q(px),q(py)) for px,py in spts], fill=(20,30,38), outline=TEAL, width=q(2.4))
# heartbeat inside the shield
hb=[(sxc-17,stop+38),(sxc-7,stop+38),(sxc-2,stop+24),(sxc+4,stop+50),(sxc+9,stop+38),(sxc+17,stop+38)]
draw.line([(q(px),q(py)) for px,py in hb], fill=TEAL, width=q(2.4), joint="curve")

text(140, 56, "Guardian", f_brand, WHITE)
bx = 140 + tw("Guardian", f_brand)[0]
text(bx+16, 92, "/", f_arch, (96,110,130))
text(bx+40, 84, "System Architecture", f_arch, TEAL)
text(146, 150, "Multi-agent home-emergency AI companion  ·  one backend, four clients, one coordinated pipeline", f_sub, DIM)

text(2336, 64, "HACKATHON BUILD", f_kicker, FAINT, anchor="ra")
text(2336, 92, "watch  ·  backend  ·  web  ·  mobile", f_sub, DIM, anchor="ra")
hline(64, 2336, 212, BORDER_SOFT, 1)


# ============================ WATCH ============================
rrect(WX0,WY0,WX1,WY1,16, fill=CARD, outline=BORDER, width=1.5)
text(WX0+28, WY0+24, "EDGE  ·  SENSOR", f_kicker, TEAL)
text(WX0+28, WY0+48, "Samsung Galaxy Watch", f_ctitle, TEXT)
text(WX0+28, WY0+90, "Wear OS  ·  Kotlin", f_csub, DIM)
hline(WX0+28, WX1-28, WY0+128, BORDER_SOFT, 1)
wy = WY0+152
for lab, sub in [("Heart rate · SpO₂ · HRV", None),
                 ("Steps · calories", "passive"),
                 ("3-phase fall detection", None),
                 ("free-fall → impact → stillness", "*")]:
    if sub=="*":
        segs(WX0+44, wy, [("free-fall → impact → stillness", f_small, FAINT)]); wy+=40
    else:
        bullet(WX0+28, wy, lab, TEAL, sub); wy+=46
bullet(WX0+28, wy, "On-device voice loop", TEAL, "VAD"); wy+=46
bullet(WX0+28, wy, "GPS location", TEAL)
# little watch glyph
gx0,gy0 = WX0+150, WY1-118
draw.rounded_rectangle([q(gx0-46),q(gy0-46),q(gx0+46),q(gy0+46)], radius=q(20), outline=BORDER, width=q(2))
draw.rounded_rectangle([q(gx0-30),q(gy0-58),q(gx0+30),q(gy0-46)], radius=q(5), fill=BORDER_SOFT)
draw.rounded_rectangle([q(gx0-30),q(gy0+46),q(gx0+30),q(gy0+58)], radius=q(5), fill=BORDER_SOFT)
hb2=[(gx0-30,gy0),(gx0-12,gy0),(gx0-4,gy0-18),(gx0+5,gy0+20),(gx0+13,gy0),(gx0+30,gy0)]
draw.line([(q(px),q(py)) for px,py in hb2], fill=TEAL, width=q(2.6), joint="curve")


# ============================ BACKEND HUB ============================
rrect(BX0,BY0,BX1,BY1,20, fill=CARDHUB, outline=TEAL, width=2)
ix0, ix1 = BX0+30, BX1-30
text(ix0, BY0+24, "THE BRAIN", f_kicker, TEAL)
text(ix0, BY0+46, "Backend", f_ctitle, WHITE)
text(ix1, BY0+54, "FastAPI  ·  LangGraph", f_csub, DIM, anchor="ra")
hline(ix0, ix1, BY0+96, BORDER_SOFT, 1)

cy = BY0+112
# router
rrect(ix0, cy, ix1, cy+56, 11, fill=CHIP, outline=BORDER, width=1.3)
dot(ix0+22, cy+28, 4, TEAL)
segs(ix0+40, cy+16, [("Hybrid Router", f_bodysb, TEXT),
                     ("   keyword emergency fast-path", f_body, DIM),
                     ("  →  LLM routing", f_body, DIM)])
cy += 56+30

text(ix0, cy, "SIX SPECIALIST AGENTS", f_kicker, DIM); cy += 26
agents = [("Safety","falls · chest pain · 911", RED),
          ("Health","vitals · symptoms", TEAL),
          ("Companion","reassurance", VIOLET),
          ("Reminder","meds · schedule", AMBER),
          ("Behavior","mood · patterns", GREEN),
          ("Caregiver Liaison","family alerts", SLATE)]
gap=16; cols=3; cwk=(ix1-ix0-gap*(cols-1))/cols; chh=80
for i,(nm,ds,c) in enumerate(agents):
    r=i//cols; cc=i%cols
    ax0=ix0+cc*(cwk+gap); ay0=cy+r*(chh+gap)
    hot = nm=="Safety"
    rrect(ax0, ay0, ax0+cwk, ay0+chh, 11, fill=CHIP,
          outline=(RED if hot else BORDER), width=1.6 if hot else 1.3)
    dot(ax0+22, ay0+28, 5, c)
    text(ax0+38, ay0+17, nm, f_chip, TEXT)
    text(ax0+20, ay0+48, ds, f_chips, DIM)
cy += 2*chh+gap+34

def fullpill(label, parts, tag=None, tagcolor=RED):
    global cy
    rrect(ix0, cy, ix1, cy+56, 11, fill=CHIP, outline=BORDER, width=1.3)
    dot(ix0+22, cy+28, 4, parts[0][2] if parts else TEAL)
    x = segs(ix0+40, cy+16, [(label, f_bodysb, TEXT), ("   ", f_body, DIM)] + parts)
    if tag:
        tw_ = tw(tag, f_chips)[0]
        rrect(ix1-tw_-24, cy+13, ix1-10, cy+43, 8, fill=(38,20,22), outline=tagcolor, width=1.3)
        text(ix1-tw_-17, cy+19, tag, f_chips, tagcolor)
    cy += 56+30

fullpill("Risk Monitor", [("HR · SpO₂ · BP · freshness  →  CTAS tiers", f_body, DIM)],
         tag="fall → CRITICAL", tagcolor=RED)
# tools (color call_911 red)
rrect(ix0, cy, ix1, cy+56, 11, fill=CHIP, outline=BORDER, width=1.3); dot(ix0+22, cy+28, 4, AMBER)
xx = segs(ix0+40, cy+16, [("Tools", f_bodysb, TEXT), ("   ", f_body, DIM)])
xx = segs(xx, cy+16, [("call_911", f_mono, RED), ("  ·  caregiver SMS  ·  schedule  ·  vitals  ·  memory", f_body, DIM)])
cy += 56+30
# voice
rrect(ix0, cy, ix1, cy+56, 11, fill=CHIP, outline=BORDER, width=1.3); dot(ix0+22, cy+28, 4, TEAL)
segs(ix0+40, cy+16, [("Voice pipeline", f_bodysb, TEXT), ("   ", f_body, DIM),
                     ("faster-whisper STT", f_body, SLATE), ("   +   ", f_body, DIM),
                     ("Kokoro TTS", f_body, TEAL)])
cy += 56+30
# db
rrect(ix0, cy, ix1, cy+56, 11, fill=CHIP, outline=BORDER, width=1.3)
dbx=ix0+22
draw.ellipse([q(dbx-9),q(cy+16),q(dbx+9),q(cy+24)], outline=GREEN, width=q(1.6))
draw.line([(q(dbx-9),q(cy+20)),(q(dbx-9),q(cy+38))], fill=GREEN, width=q(1.6))
draw.line([(q(dbx+9),q(cy+20)),(q(dbx+9),q(cy+38))], fill=GREEN, width=q(1.6))
draw.ellipse([q(dbx-9),q(cy+34),q(dbx+9),q(cy+42)], outline=GREEN, width=q(1.6))
segs(ix0+44, cy+16, [("SQLite / Postgres patient DB", f_bodysb, TEXT), ("   profile · vitals · events", f_body, DIM)])


# ============================ WEB + FLUTTER ============================
def client_card(x0,y0,x1,y1,kicker,title,sub,rows):
    rrect(x0,y0,x1,y1,16, fill=CARD, outline=BORDER, width=1.5)
    text(x0+28, y0+22, kicker, f_kicker, GREEN)
    text(x0+28, y0+46, title, f_ctitle, TEXT)
    text(x0+28, y0+88, sub, f_csub, DIM)
    hline(x0+28, x1-28, y0+126, BORDER_SOFT, 1)
    yy=y0+150
    for lab,c,hot in rows:
        if hot:
            dot(x0+32, yy+10, 3.2, RED)
            segs(x0+44, yy, [(lab, f_bodysb, (250,180,180))])
        else:
            bullet(x0+28, yy, lab, GREEN if c is None else c)
        yy+=46

client_card(EWX0,EWY0,EWX1,EWY1, "CLIENT  ·  OBSERVABILITY", "Next.js Web Dashboard",
            "Next.js 16  ·  Tailwind  ·  shadcn",
            [("Agent pipeline graph (live)",None,False),
             ("Event stream · transcripts",None,False),
             ("Risk monitor · vitals charts",None,False),
             ("Medical-history PDF upload",None,False),
             ("Live location map",None,False)])

client_card(EFX0,EFY0,EFX1,EFY1, "CLIENT  ·  MOBILE + ACTION", "Flutter Mobile App",
            "iOS  ·  Android",
            [("Mirrors the dashboard",None,False),
             ("Fall alerts · 1-tap med confirm",None,False),
             ("Lab-PDF upload",None,False),
             ("CallService dials 911 via SIM",None,True),
             ("+ speaks announcement aloud",None,True)])


# ============================ EXTERNAL ============================
rrect(TWX0,TWY0,TWX1,TWY1,14, fill=CARD, outline=BORDER, width=1.5)
text(TWX0+24, TWY0+22, "EXTERNAL", f_kicker, RED)
text(TWX0+24, TWY0+46, "Twilio", f_ctitle, TEXT)
text(TWX0+24, TWY0+92, "outbound voice + SMS", f_csub, DIM)

rrect(EMX0,EMY0,EMX1,EMY1,12, fill=(34,18,20), outline=RED, width=1.6)
text((EMX0+EMX1)/2, EMY0+18, "911", f_bodysb, RED, anchor="ma")
text((EMX0+EMX1)/2, EMY0+44, "Family", f_small, (250,180,180), anchor="ma")

rrect(NNX0,NNY0,NNX1,NNY1,14, fill=CARD, outline=BORDER, width=1.5)
text(NNX0+24, NNY0+22, "EXTERNAL  ·  PROVIDER-NEUTRAL", f_kicker, VIOLET)
text(NNX0+24, NNY0+46, "LLM Provider", f_ctitle, TEXT)
segs(NNX0+24, NNY0+92, [("OpenAI cloud", f_csub, DIM), ("   or   ", f_csub, FAINT), ("local Nemotron", f_csub, VIOLET)])
text(NNX0+24, NNY0+118, "NVIDIA DGX Spark  ·  switch via .env", f_small, FAINT)


# ============================ CONNECTORS ============================
def arrowhead(p, ang, color, size=13):
    x,y=p
    bx=x-size*math.cos(ang); by=y-size*math.sin(ang)
    ox=math.sin(ang)*size*0.6; oy=-math.cos(ang)*size*0.6
    draw.polygon([(q(x),q(y)),(q(bx+ox),q(by+oy)),(q(bx-ox),q(by-oy))], fill=color)

def connect(p0,p1,color,width=3.0,double=False,dashed=False,head=13):
    x0,y0=p0; x1,y1=p1; ang=math.atan2(y1-y0,x1-x0)
    sx0,sy0 = x0+math.cos(ang)*(head if double else 0), y0+math.sin(ang)*(head if double else 0)
    sx1,sy1 = x1-math.cos(ang)*head, y1-math.sin(ang)*head
    if dashed:
        tot=math.hypot(sx1-sx0,sy1-sy0); n=max(1,int(tot/16))
        for i in range(n):
            a=i/n; b=(i+0.55)/n
            draw.line([(q(sx0+(sx1-sx0)*a),q(sy0+(sy1-sy0)*a)),
                       (q(sx0+(sx1-sx0)*b),q(sy0+(sy1-sy0)*b))], fill=color, width=max(1,q(width)))
    else:
        draw.line([(q(sx0),q(sy0)),(q(sx1),q(sy1))], fill=color, width=max(1,q(width)), joint="curve")
    arrowhead(p1, ang, color, head)
    if double: arrowhead(p0, ang+math.pi, color, head)

def label(cx, cy, lines):
    pad=8; ws=[]; hs=[]
    for t,f,c in lines:
        w,h=tw(t,f); ws.append(w); hs.append(h+7)
    bw=max(ws)+pad*2; bh=sum(hs)+pad*2-7
    x0=cx-bw/2; y0=cy-bh/2
    draw.rounded_rectangle([q(x0),q(y0),q(x0+bw),q(y0+bh)], radius=q(8), fill=(11,15,23,232), outline=(48,60,80,255), width=q(1))
    yy=y0+pad
    for (t,f,c),h in zip(lines,hs):
        text(cx, yy, t, f, c, anchor="ma"); yy+=h

# Watch <-> Backend : voice WebSocket (teal, two-way)
connect((WX1+6, WY0+150),(BX0-6, BY0+170), TEAL, 3.2, double=True)
label(595, 452, [("Voice WebSocket", f_arrow, TEAL), ("Kokoro TTS ↓  ·  mic + STT ↑", f_small, DIM)])
# Watch -> Backend : vitals + fall events (amber)
connect((WX1+6, WY1-150),(BX0-6, BY1-150), AMBER, 3.0)
label(595, 838, [("vitals + fall events", f_arrow, AMBER), ("POST /vitals/ingest", f_mono, DIM)])

# Backend -> Web : SSE (green) ; Web -> Backend : HTTP (slate)
connect((BX1+6, BY0+150),(EWX0-6, EWY0+150), GREEN, 3.0)
connect((EWX0-6, EWY0+250),(BX1+6, BY0+250), SLATE, 2.2)
label(1686, 372, [("SSE live events", f_arrow, GREEN)])
label(1686, 470, [("HTTP requests", f_small, SLATE)])

# Backend -> Flutter : SSE + call_request (green/red) ; Flutter -> Backend : HTTP
connect((BX1+6, BY1-170),(EFX0-6, EFY0+150), GREEN, 3.0)
connect((EFX0-6, EFY0+250),(BX1+6, BY1-70), SLATE, 2.2)
label(1686, 902, [("SSE events", f_arrow, GREEN), ("call_request → dials 911", f_small, RED)])
label(1686, 1012, [("HTTP  /turn · profile · PDF", f_small, SLATE)])

# Backend -> Twilio (red) ; Twilio -> 911 (red) ; Backend <-> LLM (violet)
connect((TWX0+150, BY1+6),(TWX0+150, TWY0-6), RED, 3.0)
label(TWX0+150, (BY1+TWY0)/2, [("outbound calls", f_small, RED)])
connect((TWX1+6, (EMY0+EMY1)/2),(EMX0-6,(EMY0+EMY1)/2), RED, 2.6)
connect((NNX0+182, BY1+6),(NNX0+182, NNY0-6), VIOLET, 3.0, double=True)
label(NNX0+182, (BY1+NNY0)/2, [("LLM chat", f_small, VIOLET)])


# ============================ LEGEND ============================
ly = 1300
leg = [(TEAL,"Voice WebSocket (two-way)"),(GREEN,"SSE live events"),
       (SLATE,"HTTP requests"),(RED,"Emergency / calls"),(VIOLET,"LLM (provider-neutral)")]
widths=[34+14+tw(t,f_leg)[0]+46 for _,t in leg]
total=sum(widths); lx=(W-total)/2
for (c,t),wd in zip(leg,widths):
    draw.line([(q(lx),q(ly+11)),(q(lx+34),q(ly+11))], fill=c, width=q(3))
    arrowhead((lx+34,ly+11),0,c,11)
    text(lx+34+14, ly, t, f_leg, DIM); lx+=wd

# ============================ FOOTER ============================
hline(64, 2336, 1372, BORDER_SOFT, 1)
stack="Python  ·  FastAPI  ·  LangGraph  ·  SQLModel  ·  Kokoro TTS  ·  faster-whisper  ·  Wear OS / Kotlin  ·  Next.js 16  ·  Flutter  ·  Twilio  ·  Docker  ·  NVIDIA DGX Spark"
text(W/2, 1398, stack, f_small, FAINT, anchor="ma")
text(64, 1438, "Guardian  ·  home-emergency AI companion", f_small, FAINT)
text(2336, 1438, "github.com/Angel-Guardians/Guardians", f_small, TEAL, anchor="ra")


# ---- downscale & save ----
img.convert("RGB").resize((W,H), Image.LANCZOS).save(OUT)
print("saved", OUT)
