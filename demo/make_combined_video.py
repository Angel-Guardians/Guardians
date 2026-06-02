# Guardian - 60s SIDE-BY-SIDE: the watch (left) and the agent system (right),
# animating in sync. Watch senses->fall->"Are you OK?"->voice, while the right
# panel shows risk climbing, the pipeline lighting (Signal>Risk>Router>Safety>Tools),
# and the live event log filling. Frames piped straight to ffmpeg.
import os, math, subprocess
from PIL import Image, ImageDraw, ImageFont

W, H, FPS, DUR = 1600, 900, 24, 60
FDIR = r"C:\Windows\Fonts"
OUT = r"C:\Projects\Guardians\demo\guardian-combined-demo.mp4"

def F(n,s): return ImageFont.truetype(os.path.join(FDIR,n),s)
f_h=F("segoeuib.ttf",28); f_lt=F("segoeuil.ttf",34); f_md=F("segoeui.ttf",26)
f_mdb=F("segoeuib.ttf",26); f_sm=F("segoeui.ttf",22); f_smb=F("segoeuib.ttf",22)
f_xs=F("segoeui.ttf",18); f_xss=F("segoeui.ttf",15); f_mono=F("consola.ttf",18)
f_monb=F("consolab.ttf",19); f_kick=F("segoeuib.ttf",16); f_hr=F("segoeuib.ttf",52)
f_big=F("segoeuib.ttf",40); f_cnt=F("segoeuib.ttf",40); f_ok=F("segoeuib.ttf",28)

BG=(13,17,24); CARD=(22,28,39); CARD2=(26,33,46); CHIP=(17,23,33)
BORD=(46,57,75); BORDS=(36,45,60)
TX=(233,239,246); DIM=(150,162,181); FAINT=(105,117,137)
TEAL=(45,212,191); GREEN=(74,222,128); SLATE=(150,165,186)
RED=(248,93,93); AMBER=(251,191,36); ORANGE=(251,146,60); VIOLET=(167,139,250); WHITE=(247,250,253)

def ease(p): p=max(0.0,min(1.0,p)); return 1-(1-p)*(1-p)
def a(c,al): return (c[0],c[1],c[2],int(max(0,min(255,al))))

def card(d,x0,y0,x1,y1,fill=CARD,outline=BORD,r=14,w=1):
    d.rounded_rectangle([x0,y0,x1,y1],r,fill=fill,outline=outline,width=w)
def kick(d,x,y,t,c=TEAL): d.text((x,y),t,font=f_kick,fill=c)

def header(d,blink):
    d.rounded_rectangle([40,30,92,82],12,fill=(20,30,38),outline=TEAL,width=2)
    cx=66; d.line([(cx-13,60),(cx-5,60),(cx-1,50),(cx+3,72),(cx+8,60),(cx+14,60)],fill=TEAL,width=3,joint="curve")
    d.text((108,32),"Guardian",font=f_h,fill=WHITE)
    d.text((108,64),"watch + multi-agent system, in sync",font=f_xs,fill=DIM)
    d.rounded_rectangle([W-176,38,W-40,74],15,fill=(34,18,20),outline=RED,width=1)
    d.ellipse([W-160,49,W-148,61],fill=a(RED,120+135*blink)); d.text((W-138,44),"LIVE",font=f_smb,fill=RED)
    d.line([(40,98),(W-40,98)],fill=BORDS,width=1)

def watch_body(d,cx,cy,R,accent):
    bw=int(R*0.76)
    d.rounded_rectangle([cx-bw,cy-R-int(R*0.8),cx+bw,cy-R+int(R*0.22)],int(R*0.3),fill=(52,58,70))
    d.rounded_rectangle([cx-bw,cy+R-int(R*0.22),cx+bw,cy+R+int(R*0.8)],int(R*0.3),fill=(52,58,70))
    d.rounded_rectangle([cx+R+4,cy-14,cx+R+16,cy+14],5,fill=(74,82,96))
    d.ellipse([cx-R-14,cy-R-14,cx+R+14,cy+R+14],fill=(40,47,60))
    d.ellipse([cx-R,cy-R,cx+R,cy+R],fill=(9,12,18),outline=accent,width=4)

def ecg(d,cx,cy,w,t,col,speed=0.6,spike=1.0):
    pts=[]; x0=cx-w/2
    for i in range(0,int(w)+1,3):
        u=(i/w+t*speed)%1.0; y=0
        if 0.45<u<0.5: y=-24*spike*math.sin((u-0.45)/0.05*math.pi)
        elif 0.5<=u<0.56: y=28*spike*math.sin((u-0.5)/0.06*math.pi)
        pts.append((x0+i,cy+y))
    d.line(pts,fill=col,width=3,joint="curve")

def waveform(d,cx,cy,w,n,t,col,amp=18):
    step=w/(n-1); x0=cx-w/2
    for i in range(n):
        h=2+amp*abs(math.sin(i*0.7+t*9))*(0.5+0.5*math.sin(i*1.3+t*5))
        x=x0+i*step; d.line([(x,cy-h),(x,cy+h)],fill=col,width=4)

def gval(u):
    if u<0.33: return 1.0+0.03*math.sin(u*70)
    if u<0.46: return 1.0-0.5*((u-0.33)/0.13)
    if u<0.55: return 0.5+1.8*((u-0.46)/0.09)
    if u<0.70:
        dd=(u-0.55)/0.15; return 2.3-1.3*dd+0.18*math.sin(dd*25)*(1-dd)
    return 1.0+0.02*math.sin(u*55)

def arrow(d,x0,y0,x1,y1,col,w=3):
    d.line([(x0,y0),(x1,y1)],fill=col,width=w); ang=math.atan2(y1-y0,x1-x0)
    d.polygon([(x1,y1),(x1-13*math.cos(ang)+6*math.sin(ang),y1-13*math.sin(ang)-6*math.cos(ang)),
               (x1-13*math.cos(ang)-6*math.sin(ang),y1-13*math.sin(ang)+6*math.cos(ang))],fill=col)
def packets(d,x0,y0,x1,y1,t,col,n=4,spd=1.0):
    for i in range(n):
        u=((t*spd)+i/n)%1.0; x=x0+(x1-x0)*u; y=y0+(y1-y0)*u
        d.ellipse([x-5,y-5,x+5,y+5],fill=a(col,255*math.sin(u*math.pi)))

def risk_at(t):
    if t<12: return 8
    if t<20: return 8+37*ease((t-12)/8)
    if t<29: return 45+27*ease((t-20)/9)
    if t<39: return 72
    if t<43: return 72+28*ease((t-39)/4)
    return 100
def tier(v):
    if v>=85: return "CRITICAL",RED
    if v>=60: return "HIGH",ORANGE
    if v>=30: return "MODERATE",AMBER
    return "LOW",GREEN

EVENTS=[(5,"vital_sample","HR 57 - sinus rhythm",GREEN),
        (15,"vital_sample","HR 142 - irregular rhythm",AMBER),
        (24,"fall_suspected","impact 2.3 g (free-fall - impact - still)",RED),
        (33,"safety","\"Are you okay? Say I'm OK.\"",SLATE),
        (40,"fall_confirmed","no response - confirmed",RED),
        (44,"routing_decision","router -> safety",SLATE),
        (46,"tool call_911","Emergency services +1 343 989 5045  OK",RED),
        (48,"tool notify_caregiver","son Merazin +1 416 837-9751  OK",AMBER),
        (51,"agent_reply","safety: help is on the way",GREEN)]

CAPTION=[(0,"Baseline - the watch streams vitals; the system sits quiet at LOW risk."),
         (12,"Rhythm flares - heart rate jumps to 142 and turns irregular. Risk moves up."),
         (20,"A fall - free-fall, an impact spike, then stillness. The watch catches it."),
         (29,"Safety speaks first: \"Are you okay?\" - an 8-second window to cancel."),
         (39,"No response -> CRITICAL. Router -> Safety -> call 911 + alert family."),
         (49,"Two-way voice - Guardian talks back to the wrist; the mic streams up."),
         (57,"Help is on the way.")]

def watch_panel(d,t):
    x0,y0,x1,y1=40,118,520,772
    card(d,x0,y0,x1,y1,fill=CARD)
    kick(d,x0+28,y0+18,"ON THE WRIST  ·  WEAR OS")
    cx,cy,R=280,400,140
    dx=int(7*math.sin(t*70)) if 21<=t<25 else 0
    if t<12: bez=GREEN
    elif t<20: bez=AMBER
    elif t<49: bez=RED
    elif t<57: bez=(TEAL if (t%1.0)<0.5 else VIOLET)
    else: bez=GREEN
    watch_body(d,cx+dx,cy,R,bez)
    cx+=dx
    if t<12:
        d.text((cx,cy-92),"HEART RATE",font=f_xs,fill=DIM,anchor="ma")
        d.text((cx,cy-68),"57",font=f_hr,fill=GREEN,anchor="ma"); d.text((cx,cy-6),"bpm",font=f_xs,fill=DIM,anchor="ma")
        ecg(d,cx,cy+40,200,t,GREEN)
    elif t<20:
        hr=57+int(85*ease((t-12)/8))
        d.text((cx,cy-92),"HEART RATE",font=f_xs,fill=DIM,anchor="ma")
        d.text((cx,cy-68),str(hr),font=f_hr,fill=AMBER,anchor="ma"); d.text((cx,cy-6),"irregular",font=f_xs,fill=AMBER,anchor="ma")
        ecg(d,cx,cy+40,200,t,AMBER,speed=1.4,spike=1.3)
    elif t<29:
        u=min(1.0,(t-20)/7.0)
        pts=[]; gx0,gy0,gw=cx-110,cy+10,220
        for i in range(0,221,4):
            uu=i/220
            if uu>u: break
            pts.append((gx0+i,gy0-(gval(uu)-1.0)*55))
        if len(pts)>=2: d.line(pts,fill=RED,width=3,joint="curve")
        if t>24: d.text((cx,cy-78),"FALL",font=f_ok,fill=RED,anchor="ma")
        else: d.text((cx,cy-78),"impact!",font=f_smb,fill=RED,anchor="ma")
        d.text((cx,cy+80),"accelerometer",font=f_xss,fill=FAINT,anchor="ma")
    elif t<39:
        secs=max(0,int(12*(1-(t-29)/10))); sweep=360*max(0.0,(1-(t-29)/10))
        d.arc([cx-R+22,cy-R+22,cx+R-22,cy+R-22],-90,270,fill=(60,40,44),width=8)
        if sweep>2: d.arc([cx-R+22,cy-R+22,cx+R-22,cy+R-22],-90,-90+sweep,fill=RED,width=8)
        d.text((cx,cy-78),"Are you OK?",font=f_ok,fill=WHITE,anchor="ma")
        d.text((cx,cy-26),str(secs),font=f_cnt,fill=RED,anchor="ma")
        card(d,cx-118,cy+44,cx-10,cy+86,fill=(20,40,30),outline=GREEN,r=10); d.text((cx-64,cy+54),"I'M OK",font=f_xs,fill=GREEN,anchor="ma")
        card(d,cx+10,cy+44,cx+118,cy+86,fill=(40,22,24),outline=RED,r=10); d.text((cx+64,cy+54),"GET HELP",font=f_xs,fill=RED,anchor="ma")
    elif t<49:
        d.text((cx,cy-50),"Fall confirmed",font=f_mdb,fill=RED,anchor="ma")
        d.text((cx,cy+4),"getting help",font=f_sm,fill=(250,180,180),anchor="ma")
        d.ellipse([cx-60,cy+44,cx+60,cy+96],outline=RED,width=2)
        d.text((cx,cy+52),"!",font=f_hr,fill=RED,anchor="ma")
    elif t<57:
        spk=(t%1.0)<0.5
        d.text((cx,cy-84),("Guardian" if spk else "listening"),font=f_xs,fill=(TEAL if spk else VIOLET),anchor="ma")
        waveform(d,cx,cy-6,180,15,t,(TEAL if spk else VIOLET),26 if spk else 18)
        d.text((cx,cy+70),("speaker" if spk else "mic"),font=f_xss,fill=DIM,anchor="ma")
    else:
        d.text((cx,cy-40),"Help is",font=f_mdb,fill=GREEN,anchor="ma")
        d.text((cx,cy+0),"on the way",font=f_mdb,fill=GREEN,anchor="ma")
        d.text((cx,cy+56),"stay still",font=f_sm,fill=DIM,anchor="ma")
    # watch sub-status
    d.line([(x0+28,y0+560),(x1-28,y0+560)],fill=BORDS,width=1)
    st=("standalone Wear OS app  ·  no phone relay" if t<20 else
        ("3-phase accelerometer: free-fall -> impact -> stillness" if t<29 else
         ("full-screen prompt  ·  ~8s to cancel a false alarm" if t<39 else
          ("buffered offline-first  ·  POST /vitals/ingest" if t<49 else
           ("bidirectional voice WebSocket" if t<57 else "Kokoro TTS on the wrist")))))
    d.text(((x0+x1)//2,y0+576),st,font=f_xss,fill=FAINT,anchor="ma")

def pnode(d,x0,y0,x1,y1,label,on,col):
    fill=(col[0]//5+16,col[1]//5+18,col[2]//5+22) if on else CHIP
    card(d,x0,y0,x1,y1,fill=fill,outline=(col if on else BORD),r=10,w=2 if on else 1)
    d.text(((x0+x1)//2,(y0+y1)//2-11),label,font=f_smb if on else f_sm,fill=(WHITE if on else DIM),anchor="ma")
    if on: d.ellipse([x1-18,y0+8,x1-8,y0+18],fill=col)

def agent_panel(d,t):
    px0,px1=560,1560
    # risk strip
    v=risk_at(t); lab,c=tier(v)
    card(d,px0,118,px1,206,fill=CARD,outline=c,w=2)
    kick(d,px0+24,134,"RISK MONITOR",c)
    d.text((px0+24,158),str(int(v)),font=f_big,fill=c); d.text((px0+96,172),"/ 100",font=f_sm,fill=DIM)
    bx0,bx1,by=px0+200,px1-150,166
    d.rounded_rectangle([bx0,by,bx1,by+22],11,fill=CHIP,outline=BORDS,width=1)
    fw=int((bx1-bx0)*v/100)
    if fw>6: d.rounded_rectangle([bx0,by,bx0+fw,by+22],11,fill=c)
    d.text((px1-24,152),lab,font=f_smb,fill=c,anchor="ra")
    # pipeline
    kick(d,px0+24,224,"AGENT PIPELINE")
    nodes=[("Signal",t>2,TEAL),("Risk",t>=12,(c if t>=12 else SLATE)),
           ("Router",t>=43,SLATE),("Safety",t>=44,RED),("Tools",t>=46,RED)]
    nx0=px0+20; nw=176; gap=20; ny0=250; ny1=322
    cxs=[]
    for i,(nm,on,col) in enumerate(nodes):
        x0=nx0+i*(nw+gap); pnode(d,x0,ny0,x0+nw,ny1,nm,on,col); cxs.append((x0,x0+nw))
    for i in range(len(nodes)-1):
        on=nodes[i+1][1]; arrow(d,cxs[i][1]+2,ny0+36,cxs[i+1][0]-2,ny0+36,(SLATE if on else BORDS),3 if on else 1)
    # six specialist chips
    ag=[("Safety",RED),("Health",TEAL),("Companion",VIOLET),("Reminder",AMBER),("Behavior",GREEN),("Caregiver",SLATE)]
    cw=150; cg=14; cx0=px0+22; cyy=346
    for i,(nm,col) in enumerate(ag):
        x0=cx0+i*(cw+cg); on=(nm=="Safety" and t>=44)
        card(d,x0,cyy,x0+cw,cyy+40,fill=CHIP,outline=(RED if on else BORDS),r=9,w=2 if on else 1)
        d.ellipse([x0+12,cyy+15,x0+22,cyy+25],fill=(col if on else (70,80,95)))
        d.text((x0+32,cyy+10),nm,font=f_xs,fill=(WHITE if on else DIM))
    # event log
    ely0=410
    card(d,px0,ely0,px1,772,fill=CARD)
    d.text((px0+24,ely0+16),"Live event stream  ·  Server-Sent Events",font=f_smb,fill=TX)
    appeared=[e for e in EVENTS if t>=e[0]]; vis=appeared[-6:]
    ry=ely0+58
    for (tt,k,s,col) in vis:
        ap=ease((t-tt)/0.6)
        card(d,px0+22,ry,px1-22,ry+42,fill=CHIP,outline=a(col,150*ap),r=9)
        d.ellipse([px0+40,ry+15,px0+56,ry+31],fill=a(col,255*ap))
        d.text((px0+76,ry+6),k,font=f_monb,fill=a(col,255*ap))
        d.text((px0+340,ry+8),s,font=f_sm,fill=a(TX,255*ap))
        ry+=48
    # calling pulse
    if 40<=t<53:
        d.ellipse([px1-150,ely0+14,px1-134,ely0+30],fill=a(RED,120+135*(0.5+0.5*math.sin(t*10))))
        d.text((px1-126,ely0+14),"CALLING",font=f_smb,fill=RED)

def middle(d,t):
    lx,rx=520,560; ym=380
    if t<20: arrow(d,lx,ym,rx,ym,a(GREEN,170)); packets(d,lx,ym,rx,ym,t,GREEN,3,0.8); d.text(((lx+rx)//2,ym-26),"vitals",font=f_xss,fill=FAINT,anchor="ma")
    elif t<49: arrow(d,lx,ym,rx,ym,a(RED,200)); packets(d,lx,ym,rx,ym,t,RED,4,1.1); d.text(((lx+rx)//2,ym-26),"fall data",font=f_xss,fill=FAINT,anchor="ma")
    elif t<57:
        arrow(d,rx,ym-26,lx,ym-26,TEAL); packets(d,rx,ym-26,lx,ym-26,-t,TEAL,3,0.9)
        arrow(d,lx,ym+26,rx,ym+26,VIOLET); packets(d,lx,ym+26,rx,ym+26,t,VIOLET,3,0.9)
        d.text(((lx+rx)//2,ym-52),"TTS",font=f_xss,fill=TEAL,anchor="ma"); d.text(((lx+rx)//2,ym+34),"mic",font=f_xss,fill=VIOLET,anchor="ma")

def caption(d,t):
    cur=CAPTION[0][1]
    for ct,txt in CAPTION:
        if t>=ct: cur=txt
    d.line([(40,792),(W-40,792)],fill=BORDS,width=1)
    d.text((W//2,806),cur,font=f_md,fill=TX,anchor="ma")
    # timeline
    tlx0,tlx1,tly=300,W-300,866
    d.line([(tlx0,tly),(tlx1,tly)],fill=BORDS,width=3)
    mx=tlx0+(tlx1-tlx0)*(t/DUR)
    d.line([(tlx0,tly),(mx,tly)],fill=TEAL,width=3)
    d.ellipse([mx-7,tly-7,mx+7,tly+7],fill=TEAL)
    d.text((40,856),"github.com/Angel-Guardians/Guardians",font=f_xss,fill=FAINT)
    d.text((W-40,856),f"{int(t):02d}s / {DUR}s",font=f_mono,fill=FAINT,anchor="ra")

def render(t):
    img=Image.new("RGB",(W,H),BG); d=ImageDraw.Draw(img,"RGBA")
    header(d,0.5+0.5*math.sin(t*6))
    watch_panel(d,t); agent_panel(d,t); middle(d,t); caption(d,t)
    return img

def main():
    p=subprocess.Popen(["ffmpeg","-y","-hide_banner","-loglevel","error","-f","rawvideo",
        "-pixel_format","rgb24","-video_size",f"{W}x{H}","-framerate",str(FPS),"-i","-",
        "-c:v","libx264","-pix_fmt","yuv420p","-movflags","+faststart",OUT],stdin=subprocess.PIPE)
    N=DUR*FPS
    for i in range(N):
        t=i/FPS; fr=render(t)
        f=min(1.0,i/8.0,(N-1-i)/8.0+0.0001)
        if f<1.0: fr=Image.blend(Image.new("RGB",(W,H),(0,0,0)),fr,max(0.0,min(1.0,0.12+0.88*f)))
        p.stdin.write(fr.tobytes())
    p.stdin.close(); p.wait()
    print("saved",OUT,"frames",N)

if __name__=="__main__":
    main()
