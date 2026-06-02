# Guardian - WATCH demo video: vitals up, 3-phase fall detection, "Are you OK?",
# data to backend, and the bidirectional voice loop (Kokoro TTS down / mic+STT up).
# Same aesthetic as guardian-live-demo.mp4. Grounded in the real watch app:
#   fall heuristic: free-fall <0.72g -> impact spike >1.7g -> post-fall stillness
#   full-screen "Are you OK?" 30s countdown; no response -> confirmed -> POST /vitals/ingest
#   risk monitor -> CRITICAL; voice WebSocket: Kokoro TTS to speaker, mic+STT up.
import os, math, shutil, subprocess
from PIL import Image, ImageDraw, ImageFont

W, H, FPS = 1600, 900, 24
FDIR = r"C:\Windows\Fonts"
OUTDIR = r"C:\Projects\Guardians\demo\_wframes"
OUT = r"C:\Projects\Guardians\demo\guardian-watch-demo.mp4"

def F(n,s): return ImageFont.truetype(os.path.join(FDIR,n),s)
f_h=F("segoeuib.ttf",30); f_big=F("segoeuib.ttf",62); f_lt=F("segoeuil.ttf",40)
f_md=F("segoeui.ttf",30); f_mdb=F("segoeuib.ttf",30); f_sm=F("segoeui.ttf",24)
f_smb=F("segoeuib.ttf",24); f_xs=F("segoeui.ttf",20); f_mono=F("consola.ttf",24)
f_kick=F("segoeuib.ttf",18); f_hr=F("segoeuib.ttf",56); f_wsm=F("segoeuib.ttf",22)
f_ok=F("segoeuib.ttf",34); f_cnt=F("segoeuib.ttf",46)

BG=(13,17,24); CARD=(22,28,39); CARD2=(26,33,46); CHIP=(17,23,33)
BORD=(46,57,75); BORDS=(36,45,60)
TX=(233,239,246); DIM=(150,162,181); FAINT=(105,117,137)
TEAL=(45,212,191); GREEN=(74,222,128); SLATE=(150,165,186)
RED=(248,93,93); AMBER=(251,191,36); VIOLET=(167,139,250); WHITE=(247,250,253)

def ease(p): p=max(0.0,min(1.0,p)); return 1-(1-p)*(1-p)

def base(blink):
    img=Image.new("RGB",(W,H),BG); d=ImageDraw.Draw(img,"RGBA")
    d.rounded_rectangle([40,38,98,96],14,fill=(20,30,38),outline=TEAL,width=2)
    cx=69; d.line([(cx-15,72),(cx-6,72),(cx-1,60),(cx+4,84),(cx+9,72),(cx+16,72)],fill=TEAL,width=3,joint="curve")
    d.text((116,40),"Guardian",font=f_h,fill=WHITE)
    d.text((116,74),"Wear OS watch  ·  the frontline sensor",font=f_xs,fill=DIM)
    a=int(120+135*blink)
    d.rounded_rectangle([W-208,46,W-40,84],16,fill=(20,34,32),outline=TEAL,width=1)
    d.ellipse([W-192,57,W-180,69],fill=(TEAL[0],TEAL[1],TEAL[2],a))
    d.text((W-170,52),"ON WRIST",font=f_smb,fill=TEAL)
    d.line([(40,112),(W-40,112)],fill=BORDS,width=1)
    d.line([(40,H-58),(W-40,H-58)],fill=BORDS,width=1)
    d.text((40,H-44),"NVIDIA Spark Hack · Toronto",font=f_xs,fill=FAINT)
    d.text((W-40,H-44),"github.com/Angel-Guardians/Guardians",font=f_xs,fill=TEAL,anchor="ra")
    return img,d

def card(d,x0,y0,x1,y1,fill=CARD,outline=BORD,r=16,w=1):
    d.rounded_rectangle([x0,y0,x1,y1],r,fill=fill,outline=outline,width=w)
def kick(d,x,y,t,c=TEAL): d.text((x,y),t,font=f_kick,fill=c)

def watch_body(d,cx,cy,R,accent=BORD):
    bw=int(R*0.78)
    d.rounded_rectangle([cx-bw,cy-R-int(R*0.85),cx+bw,cy-R+int(R*0.25)],int(R*0.32),fill=(52,58,70))
    d.rounded_rectangle([cx-bw,cy+R-int(R*0.25),cx+bw,cy+R+int(R*0.85)],int(R*0.32),fill=(52,58,70))
    d.rounded_rectangle([cx+R+4,cy-16,cx+R+18,cy+16],5,fill=(74,82,96))
    d.ellipse([cx-R-16,cy-R-16,cx+R+16,cy+R+16],fill=(40,47,60))
    d.ellipse([cx-R,cy-R,cx+R,cy+R],fill=(9,12,18),outline=accent,width=4)

def waveform(d,cx,cy,w,n,t,col,amp=18,base_h=2):
    step=w/(n-1); x0=cx-w/2
    for i in range(n):
        h=base_h+amp*abs(math.sin(i*0.7+t*8))*(0.5+0.5*math.sin(i*1.3+t*5))
        x=x0+i*step
        d.line([(x,cy-h),(x,cy+h)],fill=col,width=4)

def ecg(d,cx,cy,w,t,col):
    pts=[]; x0=cx-w/2
    for i in range(0,int(w)+1,4):
        u=(i/w + t*0.6)%1.0; y=0
        if 0.45<u<0.5: y=-26*math.sin((u-0.45)/0.05*math.pi)
        elif 0.5<=u<0.56: y=30*math.sin((u-0.5)/0.06*math.pi)
        pts.append((x0+i,cy+y))
    d.line(pts,fill=col,width=3,joint="curve")

def gval(u):
    if u<0.33: return 1.0+0.03*math.sin(u*70)
    if u<0.46: return 1.0-(1.0-0.5)*((u-0.33)/0.13)
    if u<0.55: return 0.5+(2.3-0.5)*((u-0.46)/0.09)
    if u<0.70:
        dd=(u-0.55)/0.15; return 2.3-(2.3-1.0)*dd+0.18*math.sin(dd*25)*(1-dd)
    return 1.0+0.02*math.sin(u*55)

def packets(d,x0,y0,x1,y1,t,col,n=4,speed=1.0):
    for i in range(n):
        u=((t*speed)+i/n)%1.0
        x=x0+(x1-x0)*u; y=y0+(y1-y0)*u
        a=int(255*math.sin(u*math.pi))
        d.ellipse([x-6,y-6,x+6,y+6],fill=(col[0],col[1],col[2],max(0,a)))

def arrow(d,x0,y0,x1,y1,col,w=3):
    d.line([(x0,y0),(x1,y1)],fill=col,width=w)
    ang=math.atan2(y1-y0,x1-x0)
    d.polygon([(x1,y1),(x1-14*math.cos(ang)+7*math.sin(ang),y1-14*math.sin(ang)-7*math.cos(ang)),
               (x1-14*math.cos(ang)-7*math.sin(ang),y1-14*math.sin(ang)+7*math.cos(ang))],fill=col)

# ---------------- scenes ----------------
def s_title(p):
    img,d=base(0.5+0.5*math.sin(p*6))
    cx=300; cy=470; R=120
    watch_body(d,cx,cy,R,TEAL)
    d.text((cx,cy-54),"57",font=f_hr,fill=GREEN,anchor="ma")
    d.text((cx,cy+18),"bpm",font=f_xs,fill=DIM,anchor="ma")
    ecg(d,cx,cy+58,150,p,GREEN)
    d.text((660,300),"The watch that",font=f_big,fill=WHITE)
    d.text((660,372),"calls for help",font=f_big,fill=WHITE)
    al=int(255*ease(p*2))
    d.text((660,470),"It senses, detects a fall, and talks back —",font=f_md,fill=(DIM[0],DIM[1],DIM[2],al))
    d.text((660,512),"all on the wrist, no phone relay.",font=f_md,fill=(DIM[0],DIM[1],DIM[2],al))
    return img

def s_vitals(p):
    img,d=base(0.5+0.5*math.sin(p*6))
    kick(d,80,150,"STEP 1 · CONTINUOUS MONITORING")
    cx=380; cy=470; R=150
    watch_body(d,cx,cy,R,GREEN)
    d.text((cx,cy-118),"HEART RATE",font=f_xs,fill=DIM,anchor="ma")
    hr=57+int(2*math.sin(p*12))
    d.text((cx,cy-92),str(hr),font=f_hr,fill=GREEN,anchor="ma")
    d.text((cx,cy-26),"bpm",font=f_xs,fill=DIM,anchor="ma")
    ecg(d,cx,cy+18,210,p,GREEN)
    d.text((cx,cy+70),"SpO₂ 97%   ·   12,480 steps",font=f_sm,fill=DIM,anchor="ma")
    # backend card + stream
    card(d,820,300,W-80,640,fill=CARD,outline=BORD)
    kick(d,852,330,"BACKEND",TEAL); d.text((852,356),"FastAPI · risk monitor",font=f_sm,fill=DIM)
    d.text((852,420),"All quiet — HR 57, sinus",font=f_md,fill=GREEN)
    d.text((852,470),"Risk:  LOW",font=f_mdb,fill=GREEN)
    arrow(d,560,470,810,470,(GREEN[0],GREEN[1],GREEN[2],160))
    packets(d,565,470,805,470,p,GREEN,4,0.7)
    d.text((685,430),"vitals",font=f_xs,fill=FAINT,anchor="ma")
    d.text((685,490),"POST /vitals/ingest  ·  every ~60s",font=f_mono,fill=FAINT,anchor="ma")
    return img

def s_fall(p):
    img,d=base(0.5+0.5*math.sin(p*6))
    kick(d,80,150,"STEP 2 · FALL DETECTION  (3-phase accelerometer)")
    # watch shakes around impact (u~0.52)
    shake=0
    if 0.40<p<0.62: shake=int(8*math.sin(p*80))
    cx=330+shake; cy=480; R=140
    accent = RED if p>0.55 else AMBER
    watch_body(d,cx,cy,R,accent)
    if p>0.62:
        d.text((cx,cy-30),"FALL",font=f_ok,fill=RED,anchor="ma")
        d.text((cx,cy+18),"detected",font=f_sm,fill=(250,180,180),anchor="ma")
    else:
        d.text((cx,cy-44),str(57+int(p*180)),font=f_hr,fill=AMBER,anchor="ma")
        d.text((cx,cy+22),"bpm",font=f_xs,fill=DIM,anchor="ma")
    # accel graph panel
    gx0,gy0,gx1,gy1=620,250,W-80,700
    card(d,gx0,gy0,gx1,gy1,fill=CARD,outline=BORD)
    d.text((gx0+30,gy0+22),"Accelerometer · g-force",font=f_smb,fill=TX)
    px0,py0,px1,py1=gx0+60,gy0+90,gx1-40,gy1-60
    def gy(g): return py1-(g/2.6)*(py1-py0)
    # threshold guides
    for gthr,lab,c in [(0.72,"free-fall < 0.72 g",TEAL),(1.7,"impact > 1.7 g",RED)]:
        yy=gy(gthr)
        for xx in range(int(px0),int(px1),16): d.line([(xx,yy),(xx+8,yy)],fill=(c[0],c[1],c[2],120),width=1)
        d.text((px1,yy-22),lab,font=f_xs,fill=c,anchor="ra")
    # line revealed up to progress
    prog=min(1.0,p*1.15); pts=[]
    steps=120
    for i in range(steps+1):
        u=i/steps
        if u>prog: break
        x=px0+(px1-px0)*u; pts.append((x,gy(gval(u))))
    if len(pts)>=2: d.line(pts,fill=AMBER if prog<0.6 else RED,width=4,joint="curve")
    # phase labels
    for u0,lab in [(0.40,"free-fall"),(0.53,"impact"),(0.80,"stillness")]:
        if prog>u0:
            x=px0+(px1-px0)*u0
            d.text((x,py1+12),lab,font=f_xs,fill=DIM,anchor="ma")
    return img

def s_areyouok(p):
    img,d=base(0.5+0.5*math.sin(p*6))
    cx=W//2; cy=460; R=210
    watch_body(d,cx,cy,R,RED)
    # countdown ring
    sweep=360*(1-min(1.0,p*1.05))
    d.arc([cx-R+18,cy-R+18,cx+R-18,cy+R-18],-90,-90+360,fill=(60,40,44),width=10)
    if sweep>2: d.arc([cx-R+18,cy-R+18,cx+R-18,cy+R-18],-90,-90+sweep,fill=RED,width=10)
    secs=max(0,int(30*(1-min(1.0,p*1.05))))
    d.text((cx,cy-128),"Possible fall",font=f_sm,fill=(250,180,180),anchor="ma")
    d.text((cx,cy-90),"Are you OK?",font=f_ok,fill=WHITE,anchor="ma")
    d.text((cx,cy-30),str(secs),font=f_cnt,fill=RED,anchor="ma")
    d.text((cx,cy+26),"seconds",font=f_xs,fill=DIM,anchor="ma")
    card(d,cx-150,cy+60,cx-12,cy+108,fill=(20,40,30),outline=GREEN,r=12); d.text((cx-81,cy+72),"I'M OK",font=f_wsm,fill=GREEN,anchor="ma")
    card(d,cx+12,cy+60,cx+150,cy+108,fill=(40,22,24),outline=RED,r=12); d.text((cx+81,cy+72),"GET HELP",font=f_wsm,fill=RED,anchor="ma")
    if p>0.72:
        ap=ease((p-0.72)/0.28)
        d.text((W/2,750),"No response → fall confirmed, sent to the backend instantly.",
               font=f_md,fill=(TX[0],TX[1],TX[2],int(255*ap)),anchor="ma")
    return img

def s_backend(p):
    img,d=base(0.5+0.5*math.sin(p*6))
    kick(d,80,150,"STEP 3 · THE WATCH HANDS OFF")
    cx=300; cy=470; R=120
    watch_body(d,cx,cy,R,RED)
    d.text((cx,cy-20),"sent",font=f_sm,fill=(250,180,180),anchor="ma")
    d.ellipse([cx-16,cy+20,cx+16,cy+52],outline=RED,width=3); d.text((cx,cy+26),"✓",font=f_smb,fill=RED,anchor="ma")
    arrow(d,440,470,720,470,RED)
    packets(d,445,470,715,470,p,RED,5,1.1)
    d.text((580,418),"fall_confirmed",font=f_mono,fill=(250,180,180),anchor="ma")
    d.text((580,496),"HR 135 · SpO₂ 91 · POST /vitals/ingest",font=f_mono,fill=FAINT,anchor="ma")
    card(d,740,290,W-80,650,fill=CARD,outline=RED,w=2)
    kick(d,772,318,"BACKEND",RED); d.text((772,344),"FastAPI · LangGraph",font=f_sm,fill=DIM)
    rows=[("Risk monitor","a fall forces CRITICAL",RED,0.2),
          ("Router","→ Safety agent",SLATE,0.45),
          ("Safety","call 911 + alert son",RED,0.65)]
    for nm,s,c,t0 in rows:
        ap=ease((p-t0)/0.25)
        if ap<=0: continue
        i=rows.index((nm,s,c,t0)); ry=400+i*72
        d.ellipse([772,ry,790,ry+18],fill=(c[0],c[1],c[2],int(255*ap)))
        d.text((808,ry-6),nm,font=f_smb,fill=(TX[0],TX[1],TX[2],int(255*ap)))
        d.text((808+d.textbbox((0,0),nm,font=f_smb)[2]+14,ry-6),s,font=f_sm,fill=(DIM[0],DIM[1],DIM[2],int(255*ap)))
    return img

def s_voice(p):
    img,d=base(0.5+0.5*math.sin(p*6))
    kick(d,80,150,"STEP 4 · TWO-WAY VOICE  (the watch talks back)")
    cx=300; cy=470; R=140
    speaking = (p%1.0)<0.5
    watch_body(d,cx,cy,R,TEAL if speaking else VIOLET)
    if speaking:
        d.text((cx,cy-86),"Guardian",font=f_xs,fill=TEAL,anchor="ma")
        waveform(d,cx,cy-4,170,15,p,TEAL,26)
        d.text((cx,cy+74),"speaker",font=f_xs,fill=DIM,anchor="ma")
    else:
        d.text((cx,cy-86),"listening",font=f_xs,fill=VIOLET,anchor="ma")
        waveform(d,cx,cy-4,170,15,p,VIOLET,20)
        d.text((cx,cy+74),"mic",font=f_xs,fill=DIM,anchor="ma")
    # two channels to backend
    bx=920
    card(d,bx,300,W-80,640,fill=CARD,outline=BORD)
    kick(d,bx+32,330,"BACKEND · VOICE WEBSOCKET",TEAL)
    arrow(d,bx-6,400,470,400,TEAL); packets(d,bx-12,400,476,400,-p,TEAL,4,0.9)
    d.text((bx-235,360),"Kokoro TTS  ↓  spoken reply",font=f_mono,fill=TEAL,anchor="ma")
    arrow(d,470,540,bx-6,540,VIOLET); packets(d,476,540,bx-12,540,p,VIOLET,4,0.9)
    d.text((bx-235,556),"mic + STT (faster-whisper)  ↑",font=f_mono,fill=VIOLET,anchor="ma")
    d.text((bx+32,470),"\"I detected a fall and your",font=f_sm,fill=TX)
    d.text((bx+32,502),"heart looks off. Are you okay?\"",font=f_sm,fill=TX)
    return img

def s_outcome(p):
    img,d=base(0.5+0.5*math.sin(p*6))
    cx=300; cy=470; R=130
    watch_body(d,cx,cy,R,GREEN)
    d.text((cx,cy-58),"Help is",font=f_mdb,fill=GREEN,anchor="ma")
    d.text((cx,cy-18),"on the way",font=f_mdb,fill=GREEN,anchor="ma")
    d.text((cx,cy+40),"stay still",font=f_sm,fill=DIM,anchor="ma")
    d.text((660,290),"Sense → detect → speak → act.",font=f_big,fill=WHITE)
    al=int(255*ease(p*1.6))
    for i,(t,c) in enumerate([("911 called  ·  son notified",RED),
                              ("Companion keeps Eleanor calm",VIOLET),
                              ("All from the wrist — offline-first, no phone",TEAL)]):
        d.text((660,390+i*52),"•  "+t,font=f_md,fill=(c[0],c[1],c[2],al))
    if p>0.45:
        ap=ease((p-0.45)/0.4)
        d.text((660,600),"github.com/Angel-Guardians/Guardians",font=f_mdb,fill=(TEAL[0],TEAL[1],TEAL[2],int(255*ap)))
    return img

TIMELINE=[(s_title,2.8),(s_vitals,3.4),(s_fall,4.4),(s_areyouok,3.8),
          (s_backend,3.8),(s_voice,4.6),(s_outcome,3.0)]

def main():
    if os.path.isdir(OUTDIR): shutil.rmtree(OUTDIR)
    os.makedirs(OUTDIR); idx=0
    for fn,secs in TIMELINE:
        nf=int(secs*FPS)
        for k in range(nf):
            p=k/max(1,nf-1); fr=fn(p)
            fade=min(1.0,k/6.0,(nf-1-k)/6.0+0.0001)
            if fade<1.0:
                fr=Image.blend(Image.new("RGB",(W,H),(0,0,0)),fr,max(0.0,min(1.0,0.15+0.85*fade)))
            fr.save(os.path.join(OUTDIR,f"f_{idx:05d}.png")); idx+=1
    print("frames:",idx)
    subprocess.run(["ffmpeg","-y","-hide_banner","-loglevel","error","-framerate",str(FPS),
        "-i",os.path.join(OUTDIR,"f_%05d.png"),"-c:v","libx264","-pix_fmt","yuv420p",
        "-movflags","+faststart",OUT],check=True)
    print("saved",OUT)

if __name__=="__main__":
    main()
