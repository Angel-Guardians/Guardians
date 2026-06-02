# Guardian - live emergency demo video, rendered from the REAL run's data.
# Real run (Eleanor, patient_id=1) on the running app:
#   message  : "I fell and I can't get up, my chest feels tight"
#   route    : safety  (deterministic keyword fast-path)
#   tools     : call_911 -> Emergency services +1 343 989 5045 (real Twilio call_sid)
#               notify_caregiver -> son Merazin +1 416 837-9751
#   reply    : "Emergency services are on their way, and I've informed your son,
#               Merazin. Stay still - I'm right here with you."
#   risk     : 100 / CRITICAL
import os, math, shutil, subprocess
from PIL import Image, ImageDraw, ImageFont

W, H, FPS = 1600, 900, 24
FDIR = r"C:\Windows\Fonts"
OUTDIR = r"C:\Projects\Guardians\demo\_vframes"
OUT = r"C:\Projects\Guardians\demo\guardian-live-demo.mp4"

def F(name, size): return ImageFont.truetype(os.path.join(FDIR, name), size)
f_h   = F("segoeuib.ttf", 30)
f_big = F("segoeuib.ttf", 64)
f_lt  = F("segoeuil.ttf", 40)
f_md  = F("segoeui.ttf", 30)
f_mdb = F("segoeuib.ttf", 30)
f_sm  = F("segoeui.ttf", 24)
f_smb = F("segoeuib.ttf", 24)
f_xs  = F("segoeui.ttf", 20)
f_mono= F("consola.ttf", 24)
f_monb= F("consolab.ttf", 24)
f_kick= F("segoeuib.ttf", 18)

BG=(13,17,24); CARD=(22,28,39); CARD2=(26,33,46); CHIP=(17,23,33)
BORD=(46,57,75); BORDS=(36,45,60)
TX=(233,239,246); DIM=(150,162,181); FAINT=(105,117,137)
TEAL=(45,212,191); GREEN=(74,222,128); SLATE=(150,165,186)
RED=(248,93,93); AMBER=(251,191,36); WHITE=(247,250,253)

def ease(p): p=max(0,min(1,p)); return 1-(1-p)*(1-p)

def base(blink):
    img=Image.new("RGB",(W,H),BG); d=ImageDraw.Draw(img,"RGBA")
    # header
    d.rounded_rectangle([40,38,40+58,38+58],14,fill=(20,30,38),outline=TEAL,width=2)
    cx=69; d.line([(cx-15,72),(cx-6,72),(cx-1,60),(cx+4,84),(cx+9,72),(cx+16,72)],fill=TEAL,width=3,joint="curve")
    d.text((116,40),"Guardian",font=f_h,fill=WHITE)
    d.text((116,74),"Home Emergency Companion  ·  live",font=f_xs,fill=DIM)
    # LIVE pill (blinking dot)
    a=int(120+135*blink)
    d.rounded_rectangle([W-188,46,W-40,84],16,fill=(34,18,20),outline=RED,width=1)
    d.ellipse([W-172,57,W-160,69],fill=(RED[0],RED[1],RED[2],a))
    d.text((W-150,52),"LIVE",font=f_smb,fill=RED)
    d.line([(40,112),(W-40,112)],fill=BORDS,width=1)
    # footer
    d.line([(40,H-58),(W-40,H-58)],fill=BORDS,width=1)
    d.text((40,H-44),"NVIDIA Spark Hack · Toronto",font=f_xs,fill=FAINT)
    d.text((W-40,H-44),"github.com/Angel-Guardians/Guardians",font=f_xs,fill=TEAL,anchor="ra")
    return img,d

def card(d,x0,y0,x1,y1,fill=CARD,outline=BORD,r=16,w=1):
    d.rounded_rectangle([x0,y0,x1,y1],r,fill=fill,outline=outline,width=w)

def kicker(d,x,y,t,c=TEAL): d.text((x,y),t,font=f_kick,fill=c)

# ---------------- scenes ----------------
def scene_title(p):
    img,d=base(0.5+0.5*math.sin(p*6))
    d.text((W/2,330),"Live emergency, end to end",font=f_big,fill=WHITE,anchor="ma")
    al=int(255*ease(p*2))
    d.text((W/2,420),"A real run on the running app — watch · backend · 6 agents · 911",
           font=f_lt,fill=(DIM[0],DIM[1],DIM[2],al),anchor="ma")
    # flow chips
    if p>0.35:
        items=["Watch / message","Guardian router","Safety agent","call 911 + caregiver"]
        n=len(items); gap=28; ws=[]
        for t in items: ws.append(d.textbbox((0,0),t,font=f_smb)[2]+44)
        tot=sum(ws)+gap*(n-1); x=(W-tot)/2; cols=[TEAL,SLATE,RED,RED]
        for i,(t,wd) in enumerate(zip(items,ws)):
            ap=ease((p-0.35-i*0.12)/0.4)
            if ap<=0: x+=wd+gap; continue
            cc=cols[i]
            card(d,x,560,x+wd,610,fill=CHIP,outline=(cc[0],cc[1],cc[2],int(180*ap)))
            d.text((x+22,572),t,font=f_smb,fill=(TX[0],TX[1],TX[2],int(255*ap)))
            if i<n-1: d.text((x+wd+6,574),"→",font=f_smb,fill=(FAINT[0],FAINT[1],FAINT[2],int(220*ap)))
            x+=wd+gap
    return img

def scene_message(p):
    img,d=base(0.5+0.5*math.sin(p*6))
    kicker(d,80,150,"PATIENT")
    d.text((80,176),"Eleanor, 70  ·  42 Maple Street, Toronto  ·  cardiac history, lives alone",font=f_sm,fill=DIM)
    card(d,80,250,W-80,420,fill=CARD2,outline=BORD)
    d.ellipse([110,290,170,350],fill=(30,58,74)); d.text((140,305),"E",font=f_mdb,fill=TEAL,anchor="ma")
    full="I fell and I can't get up, my chest feels tight"
    n=max(0,min(len(full),int(len(full)*ease(p*1.6))))
    d.text((200,300),full[:n],font=f_md,fill=TX)
    if int(p*FPS)%16<9 and n<len(full)+2:
        wdt=d.textbbox((200,300),full[:n],font=f_md)[2]
        d.line([(wdt+3,302),(wdt+3,334)],fill=TEAL,width=2)
    d.text((200,360),"sent to Guardian  ·  POST /turn",font=f_mono,fill=FAINT)
    if p>0.7:
        ap=ease((p-0.7)/0.3)
        d.text((W/2,520),"Guardian is listening…",font=f_lt,fill=(TEAL[0],TEAL[1],TEAL[2],int(255*ap)),anchor="ma")
    return img

def node(d,x,y,w,h,label,col,on,sub=None):
    fill=CHIP if not on else (col[0]//5+18,col[1]//5+20,col[2]//5+24)
    out=BORD if not on else col
    card(d,x,y,x+w,y+h,fill=fill,outline=out,w=2 if on else 1)
    d.text((x+w/2,y+(20 if sub else h/2-12)),label,font=f_smb if on else f_sm,
           fill=(WHITE if on else DIM),anchor="ma")
    if sub: d.text((x+w/2,y+46),sub,font=f_xs,fill=(col if on else FAINT),anchor="ma")
    if on:
        d.ellipse([x+w-22,y+12,x+w-10,y+24],fill=col)

def scene_route(p):
    img,d=base(0.5+0.5*math.sin(p*6))
    kicker(d,80,150,"AGENT PIPELINE")
    d.text((80,176),"input  →  router  →  specialist  →  tools",font=f_sm,fill=DIM)
    y=300
    node(d,90,y,260,90,"Patient input",SLATE,p>0.05,"\"I fell … chest tight\"")
    node(d,430,y,250,90,"Guardian router",SLATE,p>0.2,"keyword fast-path")
    # agents column (only safety lights)
    ag=[("Safety",RED),("Health",TEAL),("Companion",(167,139,250)),("Reminder",AMBER)]
    ax=770
    for i,(nm,c) in enumerate(ag):
        on = (nm=="Safety" and p>0.42)
        node(d,ax,150+i*150,230,84,nm,c,on,("falls · chest pain · 911" if nm=="Safety" else None))
    # connectors
    def arrow(x0,y0,x1,y1,c,on):
        col=c if on else BORDS
        d.line([(x0,y0),(x1,y1)],fill=col,width=3 if on else 1)
        ang=math.atan2(y1-y0,x1-x0)
        d.polygon([(x1,y1),(x1-12*math.cos(ang)+6*math.sin(ang),y1-12*math.sin(ang)-6*math.cos(ang)),
                   (x1-12*math.cos(ang)-6*math.sin(ang),y1-12*math.sin(ang)+6*math.cos(ang))],fill=col)
    arrow(350,y+45,428,y+45,SLATE,p>0.2)
    arrow(680,y+45,768,192,RED,p>0.42)
    if p>0.55:
        ap=ease((p-0.55)/0.3)
        d.text((W/2,640),"Routed to Safety before the model even runs — the only agent that can call 911.",
               font=f_md,fill=(TX[0],TX[1],TX[2],int(255*ap)),anchor="ma")
    return img

EVENTS=[("routing_decision","router → safety",SLATE),
        ("tool · call_911","Emergency services  +1 343 989 5045   ✓ dispatched",RED),
        ("tool · notify_caregiver","son Merazin  +1 416 837-9751   ✓ called",AMBER),
        ("agent_reply","safety is speaking…",GREEN)]

def scene_events(p):
    img,d=base(0.5+0.5*math.sin(p*6))
    kicker(d,80,150,"LIVE EVENT STREAM  ·  Server-Sent Events")
    # red calling pulse
    pulse=0.5+0.5*math.sin(p*10)
    d.ellipse([80,182,96,198],fill=(RED[0],RED[1],RED[2],int(120+135*pulse)))
    d.text((108,176),"CALLING — outbound via Twilio",font=f_smb,fill=RED)
    card(d,80,230,W-80,690,fill=CARD,outline=BORD)
    d.text((110,250),"Event log",font=f_smb,fill=TX)
    d.text((110,250),"",font=f_smb,fill=TX)
    yy=308
    for i,(k,s,c) in enumerate(EVENTS):
        ap=ease((p - (0.12+i*0.2))/0.25)
        if ap<=0: continue
        rowy=yy+i*92
        card(d,110,rowy,W-110,rowy+76,fill=(CHIP[0],CHIP[1],CHIP[2]),outline=(c[0],c[1],c[2],int(150*ap)))
        d.ellipse([132,rowy+30,150,rowy+48],fill=(c[0],c[1],c[2],int(255*ap)))
        d.text((176,rowy+12),k,font=f_monb,fill=(c[0],c[1],c[2],int(255*ap)))
        d.text((176,rowy+42),s,font=f_sm,fill=(TX[0],TX[1],TX[2],int(255*ap)))
    return img

REPLY=("Emergency services are on their way, and I've informed your son, Merazin. "
       "Stay still — I'm right here with you.")
def wrap(d,text,font,maxw):
    words=text.split(); lines=[]; cur=""
    for w in words:
        t=(cur+" "+w).strip()
        if d.textbbox((0,0),t,font=font)[2]<=maxw: cur=t
        else: lines.append(cur); cur=w
    if cur: lines.append(cur)
    return lines

def scene_reply(p):
    img,d=base(0.5+0.5*math.sin(p*6))
    kicker(d,80,150,"GUARDIAN · SAFETY AGENT")
    card(d,80,210,W-560,470,fill=CARD2,outline=(TEAL[0],TEAL[1],TEAL[2],170))
    d.ellipse([110,238,162,290],fill=(20,30,38)); d.text((136,250),"G",font=f_mdb,fill=TEAL,anchor="ma")
    lines=wrap(d,REPLY,f_md,W-560-220)
    chars=int(len(REPLY)*ease(p*1.5)); seen=0
    ly=250
    for ln in lines:
        show=ln
        if seen+len(ln)>chars: show=ln[:max(0,chars-seen)]
        d.text((200,ly),show,font=f_md,fill=TX); ly+=44; seen+=len(ln)+1
    d.text((200,430),"spoken aloud · Kokoro TTS",font=f_mono,fill=FAINT)
    # risk gauge
    gx0=W-500; card(d,gx0,210,W-80,470,fill=CARD,outline=RED,w=2)
    d.text((gx0+30,238),"RISK MONITOR",font=f_kick,fill=RED)
    val=int(100*ease(p*1.3))
    d.text((gx0+30,275),str(val),font=f_big,fill=RED)
    d.text((gx0+150,322),"/ 100",font=f_md,fill=DIM)
    bx0=gx0+30; bx1=W-110; by=400
    d.rounded_rectangle([bx0,by,bx1,by+26],13,fill=CHIP,outline=BORDS,width=1)
    fillw=int((bx1-bx0)*val/100)
    if fillw>6: d.rounded_rectangle([bx0,by,bx0+fillw,by+26],13,fill=RED)
    lab="CRITICAL" if val>=85 else ("HIGH" if val>=60 else "…")
    d.text((bx1,360),lab,font=f_smb,fill=RED,anchor="ra")
    d.text((gx0+30,300),"",font=f_sm,fill=DIM)
    if p>0.6:
        ap=ease((p-0.6)/0.35)
        d.text((W/2,560),"A recent fall forces CRITICAL instantly — no waiting for the model.",
               font=f_md,fill=(DIM[0],DIM[1],DIM[2],int(255*ap)),anchor="ma")
        d.text((W/2,610),"Then the Companion agent keeps Eleanor calm until help arrives.",
               font=f_md,fill=(DIM[0],DIM[1],DIM[2],int(255*ap)),anchor="ma")
    return img

def scene_close(p):
    img,d=base(0.5+0.5*math.sin(p*6))
    d.text((W/2,300),"Routed. Reasoned. Acted. Live.",font=f_big,fill=WHITE,anchor="ma")
    al=int(255*ease(p*1.6))
    d.text((W/2,400),"watch senses  →  6 specialist agents reason & act  →  the phone calls 911",
           font=f_md,fill=(DIM[0],DIM[1],DIM[2],al),anchor="ma")
    d.text((W/2,470),"FastAPI · LangGraph · SQLite/Postgres · Kokoro · faster-whisper · Twilio · Nemotron on NVIDIA DGX Spark",
           font=f_sm,fill=(FAINT[0],FAINT[1],FAINT[2],al),anchor="ma")
    if p>0.4:
        ap=ease((p-0.4)/0.4)
        d.text((W/2,580),"github.com/Angel-Guardians/Guardians",font=f_mdb,
               fill=(TEAL[0],TEAL[1],TEAL[2],int(255*ap)),anchor="ma")
    return img

TIMELINE=[(scene_title,2.6),(scene_message,3.2),(scene_route,3.4),
          (scene_events,4.6),(scene_reply,4.8),(scene_close,2.8)]

def main():
    if os.path.isdir(OUTDIR): shutil.rmtree(OUTDIR)
    os.makedirs(OUTDIR)
    idx=0
    for fn,secs in TIMELINE:
        nf=int(secs*FPS)
        for k in range(nf):
            p=k/max(1,nf-1)
            frame=fn(p)
            # gentle fade in/out between scenes
            fade=min(1.0, k/6.0, (nf-1-k)/6.0+0.0001)
            if fade<1.0:
                black=Image.new("RGB",(W,H),(0,0,0))
                frame=Image.blend(black,frame,max(0.0,min(1.0,0.15+0.85*fade)))
            frame.save(os.path.join(OUTDIR,f"f_{idx:05d}.png")); idx+=1
    print("frames:",idx)
    cmd=["ffmpeg","-y","-hide_banner","-loglevel","error","-framerate",str(FPS),
         "-i",os.path.join(OUTDIR,"f_%05d.png"),"-c:v","libx264","-pix_fmt","yuv420p",
         "-movflags","+faststart",OUT]
    subprocess.run(cmd,check=True)
    print("saved",OUT)

if __name__=="__main__":
    main()
