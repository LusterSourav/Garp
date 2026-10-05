"""Exact nyum UI (doersino/nyum, MIT): same templates, same style.css,
same search.js, same fonts/icons served from vendored assets/.
Only additions: upload section on index, /recipe/<slug> URLs instead of
*.html, /search.json + /category/* routes. Class names kept 1:1 so the
vendored CSS applies untouched."""
import html
import json
import os
import re

try:
    from . import iconboil
except ImportError:  # bookview imported outside the package
    import iconboil

TITLE = "Garp"
DESC = "Turn your grandpa's voice memos into a family recipe book."
V = "34"  # bump to bust asset caches (assets served immutable)

FLAGS = (("vegan", "leaf", "Vegan"), ("spicy", "pepper", "Spicy"),
         ("sweet", "candy", "Sweet"), ("salty", "salt", "Salty"),
         ("sour", "lemon", "Sour"), ("bitter", "coffee", "Bitter"),
         ("umami", "mushroom", "Umami"))


def parse_recipe(path: str) -> dict:
    """nyum-format md -> {meta, steps, slug}."""
    with open(path) as f:
        raw = f.read()
    meta, body = {}, raw
    if raw.startswith("---"):
        _, front, body = raw.split("---", 2)
        for line in front.strip().splitlines():
            if ":" in line:
                k, v = line.split(":", 1)
                meta[k.strip()] = v.strip()
    steps = []
    for chunk in body.split("---"):
        ings, texts = [], []
        for line in chunk.strip().splitlines():
            line = line.strip()
            if line.startswith("* "):
                m = re.match(r"\*\s+`([^`]*)`\s*(.*)", line)
                ings.append((m.group(1), m.group(2)) if m
                            else ("", line[2:]))
            elif line.startswith("> "):
                texts.append(line[2:])
        if ings or texts:
            steps.append({"ings": ings, "text": " ".join(texts)})
    meta["slug"] = os.path.splitext(os.path.basename(path))[0]
    return {"meta": meta, "steps": steps}


def list_recipes(book_dir: str) -> list:
    out = []
    if os.path.isdir(book_dir):
        for fn in sorted(os.listdir(book_dir)):
            if fn.endswith(".md"):
                try:
                    out.append(parse_recipe(os.path.join(book_dir, fn)))
                except Exception:
                    pass  # one bad file never breaks the index
    return out


def _head(title: str) -> str:
    return ("<!DOCTYPE html>\n<html lang=\"en\">\n<head>\n"
            "<meta charset=\"UTF-8\">\n"
            "<meta name=\"viewport\" content=\"width=device-width, initial-scale=1\">\n"
            "<meta name=\"garp-v\" content=\"" + V + "\">\n"
            "<link rel=\"icon\" type=\"image/svg+xml\" href=\"/assets/favicon.svg?v=" + V + "\">\n"
            "<link rel=\"apple-touch-icon\" href=\"/assets/favicon.svg?v=" + V + "\">\n"
            "<link rel=\"stylesheet\" href=\"/assets/fonts/barlow/webfont.css\">\n"
            "<link rel=\"stylesheet\" href=\"/assets/fonts/lora/webfont.css\">\n"
            "<link rel=\"stylesheet\" href=\"/assets/style.css?v=" + V + "\">\n"
            "<style>body.stage{background-color:#0d0309;color:#f3e6ea}"
            ".stage a{color:#f2a9c0}"
            ".stage header nav{color:#c99}"
            ".stage{--foreground:#f5e9ec;--nav:#d8b;--link:#f2a9c0;--footer:#a08090}"
            ".stage .search .results h3{color:#16161d}"
            "@media print{body.stage{background-color:#fff;color:#16161d}.stage a{color:#239}}</style>\n"
            "<script>(function(){if(location.search.indexOf('sakura=debug')<0)"
            "return;var d=document.createElement('div');"
            "d.style.cssText='position:fixed;left:8px;bottom:8px;z-index:99;"
            "background:#000;color:#0f0;font:12px monospace;padding:6px 8px;"
            "border-radius:4px;white-space:pre';d.textContent='sakura…';"
            "document.addEventListener('DOMContentLoaded',function(){"
            "document.body.appendChild(d);setInterval(function(){var s="
            "window.__sakura;d.textContent=s?('petals '+s.count+' | '+s.mode+"
            "' | '+s.fps+' fps | webgl '+(s.webgl?'ok':'FAIL')):"
            "'sakura.js not running';},500);});})();</script>\n"
            + SAKURA_CSS +
            f"<title>{html.escape(title)}</title>\n</head>\n<body class=\"stage\">")


def _close() -> str:
    return "</main></body></html>"


def _icon(name: str, alt: str) -> str:
    """Boil-ready icon: boil.js draws it sketchy on canvas, <img> is fallback."""
    try:
        d = iconboil.icon_paths(name)
    except Exception:
        d = None
    if not d:
        return (f"<img src=\"/assets/tabler-icons/tabler-icon-{name}.svg\" "
                f"alt=\"{html.escape(alt)}\">")
    return (f"<span class=\"boil\" data-paths=\""
            f"{html.escape(json.dumps(d['paths']), quote=True)}\" "
            f"data-color=\"{html.escape(d['color'])}\">"
            f"<img src=\"/assets/tabler-icons/tabler-icon-{name}.svg\" "
            f"alt=\"{html.escape(alt)}\"></span>")


def _icon_js() -> str:
    return ("<script src=\"/assets/rough.js?v=" + V + "\"></script>"
            "<script src=\"/assets/boil.js?v=" + V + "\"></script>"
            "<script defer src=\"/assets/tab-anim.js?v=" + V + "\"></script>")


def _icons(m: dict) -> str:
    h = ["<i class=\"icons\">"]
    if m.get("favorite"):
        h.append(_icon("star", "Favorite"))
    if m.get("memo"):
        h.append(_icon("microphone", "Voice memo"))
    if not m.get("veggie") and not m.get("vegan") and not m.get("memo"):
        h.append(_icon("meat", "Meat"))
    for key, icon, label in FLAGS:
        if m.get(key):
            h.append(_icon(icon, label))
    return "".join(h) + "</i>"


BOOK_CSS = ("<style>"
 ".book-viewport{width:min(760px,96vw);margin:0 auto;position:relative;"
 "perspective:1400px;padding:clamp(8px,2vw,20px) 0;min-height:420px}"
 ".book-viewport .scene{position:absolute;left:50%;top:0;width:780px;height:580px;"
 "margin-left:-390px;transform-origin:center top;transform-style:preserve-3d}"
 ".book-viewport #book{width:248px;height:350px;position:absolute;left:46%;top:30%;"
 "transform:translate3d(0,0,-10px) rotateX(60deg) rotateZ(29deg);"
 "transform-style:preserve-3d;transform-origin:0 0 0}"
 ".book-viewport #flip{width:253px;height:350px;position:absolute;left:46%;top:30%;"
 "transform:translateZ(-10px) rotateX(60deg) rotateZ(29deg) rotateY(0deg);"
 "transform-style:preserve-3d;transform-origin:0 0 0;"
 "transition:transform 1.6s ease-in-out;cursor:pointer}"
 ".book-viewport .book3d.flipped #flip{transform:translateZ(-10px) rotateX(60deg)"
 " rotateZ(29deg) rotateY(-180deg)}"
 ".book-viewport .book3d.peek #flip{transform:translateZ(-10px) rotateX(60deg)"
 " rotateZ(29deg) rotateY(-12deg)}"
 ".book-viewport #flip div{height:350px;width:24px;position:absolute;left:calc(100% - 1px);"
 "transform-origin:0 100%;transform-style:preserve-3d;background-size:253px 350px;"
 "transition:transform 1.6s ease-in-out}"
 ".book-viewport #flip #front,.book-viewport #flip #front div{"
 "background-image:url(/assets/pika.jpeg);"
 "box-shadow:inset rgba(255,255,255,.3) 0 -1px 0 0,rgba(0,0,0,.35) 0 1px 0 0}"
 ".book-viewport #flip #front>div>div>div>div>div>div>div>div>div>div{"
 "box-shadow:inset rgba(255,255,255,.3) -1px -1px 0 0,rgba(0,0,0,.35) 1px 1px 0 0}"
 ".book-viewport #flip #back{transform:rotateY(.4deg);transform-origin:-100% 0}"
 ".book-viewport #flip #back,.book-viewport #flip #back div{"
 "background-image:url(/assets/pika.jpeg);"
 "box-shadow:inset rgba(255,255,255,.3) 0 -1px 0 0,rgba(0,0,0,.35) 0 1px 0 0}"
 ".book-viewport #flip>div{left:0;background-position-x:0}"
 ".book-viewport #flip div>div{background-position-x:-23px}"
 ".book-viewport #flip div>div>div{background-position-x:-46px}"
 ".book-viewport #flip div>div>div>div{background-position-x:-69px}"
 ".book-viewport #flip div>div>div>div>div{background-position-x:-92px}"
 ".book-viewport #flip div>div>div>div>div>div{background-position-x:-115px}"
 ".book-viewport #flip div>div>div>div>div>div>div{background-position-x:-138px}"
 ".book-viewport #flip div>div>div>div>div>div>div>div{background-position-x:-161px}"
 ".book-viewport #flip div>div>div>div>div>div>div>div>div{background-position-x:-184px}"
 ".book-viewport #flip div>div>div>div>div>div>div>div>div>div{background-position-x:-207px}"
 ".book-viewport #flip div>div>div>div>div>div>div>div>div>div>div{background-position-x:-229px}"
 ".book-viewport .book3d.flipping #flip div>div{transform:rotateY(-8deg)}"
 ".book-viewport .book3d.flipping #flip div>div>div{transform:rotateY(-4deg)}"
 ".book-viewport .book3d.flipping #flip div>div>div>div>div{transform:rotateY(5deg)}"
 ".book-viewport .book3d.flipping #flip div>div>div>div>div>div>div{transform:rotateY(11deg)}"
 ".book-viewport #book #top{background:linear-gradient(105deg,#f2ecdb 88%,#d9cfb6 100%);"
 "height:350px;width:248px;position:absolute;left:0;top:0;overflow:hidden;"
 "box-shadow:inset rgba(0,0,0,.12) 30px 0 60px -30px}"
 ".book-viewport #top-text{position:absolute;inset:0;display:flex;flex-direction:column;"
 "justify-content:center;gap:8px;padding:26px 24px;color:#2b2118}"
 ".book-viewport #top-text h3{font:700 21px/1.25 Barlow,Helvetica,sans-serif;margin:0}"
 ".book-viewport #top-text ol{margin:0;padding-left:18px;font:400 13px/1.55 Barlow,Helvetica,sans-serif}"
 ".book-viewport #top-text .quote{font:italic 13px/1.5 Lora,Georgia,serif;margin:0}"
 ".book-viewport #top-text .from{text-align:right;font:400 11px Barlow,Helvetica,sans-serif;"
 "opacity:.7;margin:0}"
 ".book-viewport #top-text ol{margin:0;padding-left:16px}"
 ".book-viewport #top-text .sub{margin:0;opacity:.75}"
 ".book-viewport #book #bottom{background:#E7DED1;"
 "box-shadow:rgba(83,53,13,.2) 4px 2px 1px,#35582C 1px 1px 0 0;"
 "height:350px;width:253px;position:absolute;transform:translateZ(-40px);left:0;top:0}"
 ".book-viewport #book #front{background:repeating-linear-gradient(to bottom,"
 "#FCF6EA 0,#FCF6EA 1px,#D8D1C3 1px,#D8D1C3 2px);"
 "box-shadow:inset #C2BBA2 3px 0 0,#35582C -2px 1px 0 0;"
 "height:40px;width:251px;left:-3px;position:absolute;bottom:-40px;"
 "transform:rotateX(-90deg);transform-origin:50% 0;"
 "border-top-left-radius:5px;border-bottom-left-radius:5px}"
 ".book-viewport #book #right{background:repeating-linear-gradient(to right,"
 "#DDD2BB 0,#DDD2BB 1px,#BDB3A0 1px,#BDB3A0 2px);"
 "height:100%;width:40px;position:absolute;right:-40px;top:0;"
 "transform:rotateY(90deg);transform-origin:0 50%}"
 ".book-viewport #bookmark{position:absolute;transform:translate3d(20px,350px,-16px);"
 "transform-style:preserve-3d}"
 ".book-viewport #bookmark div{background:#975858;box-shadow:#854d4d 1px 0;"
 "height:10px;width:20px;position:absolute;top:9px;"
 "transform:rotateX(-14deg);transform-origin:50% 0;transform-style:preserve-3d}"
 ".book-viewport #bookmark>div>div{"
 "background:linear-gradient(to bottom,#975858,#bd7b7b,#975858)}"
 ".book-viewport #bookmark>div>div>div{"
 "background:linear-gradient(to bottom,#975858,#854d4d)}"
 ".book-viewport #bookmark>div>div>div>div{background:none;border-top:0 solid transparent;"
 "border-right:10px solid #854d4d;border-bottom:10px solid transparent;"
 "border-left:10px solid #854d4d;height:0;width:0}"
 ".book-viewport .noanim #flip,.book-viewport .noanim #flip div{transition:none!important}"
 ".book-viewport #bookmark-shadow{background:linear-gradient(to bottom,"
 "rgba(83,53,13,.25),rgba(83,53,13,.11));height:15px;width:20px;position:absolute;"
 "transform:translate3d(12px,350px,-25px) rotateX(-90deg) skewX(20deg);transform-origin:0 0}"
 ".book-viewport .zone{position:absolute;top:0;bottom:0;width:50%;z-index:30;min-height:44px}"
 ".book-viewport .zone-left{left:0;cursor:w-resize}"
 ".book-viewport .zone-right{right:0;cursor:e-resize}"
 "@media (prefers-reduced-motion:reduce){"
 ".book-viewport #flip,.book-viewport #flip div{transition:none}}"
  ".book-viewport #top-text .rhead{font:700 11px/1.4 Barlow,Helvetica,sans-serif;letter-spacing:.12em;text-transform:uppercase;color:#8a6b52;margin:8px 0 2px}"
  ".book-viewport #top-text .ing{font:400 14px/1.65 Barlow,Helvetica,sans-serif;margin:0;overflow-wrap:anywhere}"
  ".book-viewport #top-text .step{font:400 14px/1.65 Barlow,Helvetica,sans-serif;margin:0 0 4px;overflow-wrap:anywhere}"
  ".book-viewport #top-text .step .sn{font-weight:700}"
  ".book-viewport #top-text .tips{font:italic 13px/1.55 Lora,Georgia,serif;margin:6px 0 0}"
  ".book-viewport #top-text.paged{justify-content:flex-start;padding:20px 18px 8px}"
  ".book-viewport .pturn{position:absolute;top:0;bottom:0;width:50%;z-index:60;cursor:pointer}"
  ".book-viewport .pturn-left{left:0;cursor:w-resize}"
  ".book-viewport .pturn-right{right:0;cursor:e-resize}"
  ".book-viewport .pages{position:relative;flex:1;min-height:0;margin-top:4px;perspective:900px}"
  ".book-viewport .page{position:absolute;inset:0;overflow:hidden;background:linear-gradient(105deg,#f2ecdb 88%,#e7dcc2 100%);"
  "box-shadow:inset rgba(0,0,0,.10) 18px 0 30px -18px;transform-origin:left center;transform-style:preserve-3d;"
  "backface-visibility:hidden;transition:transform .8s cubic-bezier(.4,0,.2,1),filter .8s ease}"
  ".book-viewport .page.turned{transform:rotateY(-155deg);filter:brightness(.93)}"
  ".book-viewport .instant .page{transition:none}"
  "@media (prefers-reduced-motion:reduce){"
  ".book-viewport #flip,.book-viewport #flip div,.book-viewport .page{transition:none}}"
  "@media print{.book-viewport .zone,.book-viewport .pturn{display:none}"
  ".book-viewport .pages{position:static}.book-viewport .page{position:static;transform:none;margin-bottom:12px}}</style>")

BOOK_JS = ("<script>(function(){var b=document.getElementById('book3d');"
 "if(!b)return;var reduce=matchMedia('(prefers-reduced-motion: reduce)').matches;"
 "var vp=b.parentElement;"
 "function uni(rs){var l=1e9,t=1e9,r=-1e9,bo=-1e9;"
 "rs.forEach(function(x){l=Math.min(l,x.left);t=Math.min(t,x.top);"
 "r=Math.max(r,x.right);bo=Math.max(bo,x.bottom);});"
 "return{l:l,t:t,w:r-l,h:bo-t};}"
  "function fit(){var was=b.classList.contains('flipped');"
 "b.classList.add('noanim');b.classList.remove('peek');b.style.scale=1;"
 "var bs=b.getBoundingClientRect();"
 "var closed=uni([b.querySelector('#book').getBoundingClientRect(),"
 "b.querySelector('#flip').getBoundingClientRect()]);"
 "b.classList.add('flipped');void b.offsetWidth;"
 "var opened=uni([b.querySelector('#book').getBoundingClientRect(),"
 "b.querySelector('#flip').getBoundingClientRect()]);"
 "if(!was){b.classList.remove('flipped');}"
 "b.classList.remove('noanim');"
 "var l=Math.min(closed.l,opened.l)-bs.left,t=Math.min(closed.t,opened.t)-bs.top;"
 "var r=Math.max(closed.l+closed.w,opened.l+opened.w)-bs.left;"
 "var bo=Math.max(closed.t+closed.h,opened.t+opened.h)-bs.top;"
 "var uw=r-l,uh=bo-t;if(uw<1||uh<1){return;}"
 "var cap=Math.min(620,Math.max(280,(window.innerHeight||800)-300));"
 "var s=Math.min(1,(vp.clientWidth-24)/uw,cap/uh);"
 "var rest=(closed.l-bs.left)+closed.w/2;"
 "b.style.scale=s;b.style.marginLeft=(-390-(rest-390)*s)+'px';"
 "vp.style.height=(uh*s+16)+'px';"
 "if(window.console){console.info('garp book fit',Math.round(s*100)+'%');}}"
 "if(window.ResizeObserver){new ResizeObserver(fit).observe(vp);}fit();"
  "var flap=null;"
  "function open(){b.classList.add('flipped');b.classList.add('flipping');"
 "clearTimeout(flap);flap=setTimeout(function(){b.classList.remove('flipping')},1700);}"
 "function shut(){b.classList.remove('flipped');b.classList.add('flipping');"
 "clearTimeout(flap);flap=setTimeout(function(){b.classList.remove('flipping')},1700);}"
 "function toggle(){b.classList.contains('flipped')?shut():open();}"
 "var zl=b.querySelector('.zone-left'),zr=b.querySelector('.zone-right');"
 "var f=b.querySelector('#flip');"
 "if(zr){zr.addEventListener('mouseenter',function(){if(!b.classList.contains('flipped'))b.classList.add('peek');});"
 "zr.addEventListener('mouseleave',function(){b.classList.remove('peek');});"
  "zr.addEventListener('click',function(){b.classList.remove('peek');open();});}"
  "if(zl){zl.addEventListener('click',function(){shut();});}"
  "if(f){f.addEventListener('click',function(){toggle();});"
  "f.addEventListener('keydown',function(e){if(e.key==='Enter')toggle();});}"
  "document.addEventListener('keydown',function(e){if(e.key==='ArrowRight')open();"
  "if(e.key==='ArrowLeft')shut();});"
  "var x0=null;b.addEventListener('touchstart',function(e){x0=e.touches[0].clientX;},{passive:true});"
  "b.addEventListener('touchend',function(e){if(x0===null)return;"
  "var dx=e.changedTouches[0].clientX-x0;x0=null;"
  "if(dx<-30)open();else if(dx>30)shut();},{passive:true});"
 "if(!reduce){var seen=false;"
 "['click','keydown','touchstart'].forEach(function(t){document.addEventListener(t,function(){seen=true},{once:true});});"
 "setTimeout(function(){if(!seen)open();},700);"
 "setTimeout(function(){if(!seen)shut();},2800);}})();</script>")

INTAKE_CSS = ("<style>"
 ".book-viewport #top-text .memo-line{margin:0;font:italic 15px/1.5 Lora,Georgia,serif;color:#5a4a3a}"
 ".book-viewport #top-text .book-actions{display:flex;gap:10px;flex-wrap:wrap;margin-top:8px}"
 ".book-viewport #top-text .book-actions button{font:700 13px/1 Barlow,Helvetica,sans-serif;color:#f7eddc;background:#35582c;border:0;border-radius:6px;padding:10px 14px;cursor:pointer}"
 ".book-viewport #top-text .book-actions button:disabled{opacity:.6;cursor:wait}"
 ".book-viewport #top-text .intake-status{min-height:1.2em;margin:6px 0 0;font:400 12px/1.4 Barlow,Helvetica,sans-serif;color:#6b5a48}"
 ".book-viewport #top-text summary{cursor:pointer;font:700 14px/1.5 Barlow,Helvetica,sans-serif;color:#2b2118}"
 ".book-viewport #top-text .live-timer{margin:0;font:400 12px/1.4 Barlow,Helvetica,sans-serif;color:#8a6b52}"
 "@media print{.book-viewport .book-actions{display:none}}</style>")

INTAKE_JS = ("<script>(function(){var f=document.getElementById('voice_intake'),v=document.getElementById('voice_btn'),l=document.getElementById('live_btn'),t=document.getElementById('live_timer'),s=document.getElementById('intake_status'),fi=document.getElementById('memo_file');"
 "function st(m){s.textContent=m;}function send(fd){st('Processing voice memo...');return fetch('/extract',{method:'POST',body:fd,headers:{'Accept':'application/json'}}).then(function(r){return r.json().then(function(j){return {ok:r.ok,j:j};});}).then(function(r){if(r.j.error){st('Not added: '+r.j.error);return;}st('Added: '+(r.j.title||'recipe')+'.');location.href='/recipe/'+(r.j.slug||'');}).catch(function(){st('Could not process that memo.');});}"
 "f.addEventListener('submit',function(e){e.preventDefault();var fd=new FormData(f);fd.set('language','auto');send(fd);});"
 "v.addEventListener('click',function(){fi.click();});fi.addEventListener('change',function(){if(!fi.files[0])return;var fd=new FormData(f);fd.set('language','auto');send(fd);});"
 "var rec,st2,stream,chunks,ts,tick,actx,an,src,sil=0,last=0;"
 "function stopRec(reason){if(rec&&rec.state!=='inactive')rec.stop();l.textContent='Live';l.disabled=false;st2=false;if(tick)clearInterval(tick);if(stream)stream.getTracks().forEach(function(x){x.stop();});if(src)try{src.disconnect();}catch(e){}if(actx)try{actx.close();}catch(e){}t.textContent='';st(reason?reason:'');}"
 "l.addEventListener('click',function(){if(st2){stopRec('Processing voice memo...');return;}if(!navigator.mediaDevices||!window.MediaRecorder){st('Live recording is not supported here. Use Voice to upload a memo.');return;}navigator.mediaDevices.getUserMedia({audio:true}).then(function(s2){stream=s2;chunks=[];st2=true;l.textContent='Stop';st('Recording... speak, then pause about 5 seconds to auto-stop.');var mime=MediaRecorder.isTypeSupported('audio/mp4')?'audio/mp4':(MediaRecorder.isTypeSupported('audio/webm;codecs=opus')?'audio/webm;codecs=opus':'');try{rec=new MediaRecorder(stream,mime?{mimeType:mime}:undefined);}catch(e){rec=new MediaRecorder(stream);mime=rec.mimeType;}var ext=(rec.mimeType||mime).indexOf('mp4')>=0?'m4a':((rec.mimeType||mime).indexOf('ogg')>=0?'ogg':'webm'); rec.ondataavailable=function(e){if(e.data.size)chunks.push(e.data);};rec.onstop=function(){var blob=new Blob(chunks,{type:rec.mimeType||mime}); if(!blob.size){st('No audio captured.');return;}var fd=new FormData(f);fd.set('memo',blob,'memo.'+ext);fd.set('language','auto');send(fd);}; rec.start(1000); var A=window.AudioContext||window.webkitAudioContext; if(A){actx=new A();src=actx.createMediaStreamSource(stream);an=actx.createAnalyser();an.fftSize=512;src.connect(an);var gz=actx.createGain();gz.gain.value=0;an.connect(gz);gz.connect(actx.destination);var data=new Uint8Array(an.fftSize);tick=setInterval(function(){var x=Math.floor((Date.now()-ts)/1000);t.textContent=Math.floor(x/60)+':'+String(x%60).padStart(2,'0');if(x>=300){stopRec('Auto-stopped: 5 minute limit reached. Processing...');return;} if(actx.state==='suspended')actx.resume();an.getByteTimeDomainData(data);var sum=0;for(var i=0;i<data.length;i++){var y=(data[i]-128)/128;sum+=y*y;}var rms=Math.sqrt(sum/data.length); if(rms>.015){sil=0;}else{sil++;}if(sil>=10)stopRec('Auto-stopped: long pause. Processing...');},500);}else{ts=Date.now();tick=setInterval(function(){var x=Math.floor((Date.now()-ts)/1000);t.textContent=Math.floor(x/60)+':'+String(x%60).padStart(2,'0');if(x>=300)stopRec('Auto-stopped: 5 minute limit reached. Processing...');},500);}}).catch(function(){st('Microphone blocked or unavailable.');});});})();</script>")

PAGER_JS = ("<script>(function(){var holder=document.getElementById('recipe_pages');"
 "if(!holder)return;var blocks=Array.prototype.slice.call(holder.children);"
 "var zl=document.getElementById('pturn_left'),zr=document.getElementById('pturn_right');"
 "holder.innerHTML='';"
 "function mkPage(){var d=document.createElement('div');d.className='page';holder.appendChild(d);return d;}"
 "function fits(p){return p.scrollHeight<=p.clientHeight+2;}"
 "var cur=mkPage(),held=null;"
 "function flushHeld(){if(held){cur.appendChild(held);held=null;}}"
 "function fillWords(node,words){var el=node.cloneNode(false);cur.appendChild(el);var i=0;"
 "while(i<words.length){el.appendChild(document.createTextNode(words[i]+' '));"
 "if(!fits(cur)){el.removeChild(el.lastChild);"
 "if(!el.textContent){el.appendChild(document.createTextNode(words[i]+' '));i++;}"
 "else{cur=mkPage();el=node.cloneNode(false);"
 "var tag=document.createElement('span');tag.className='cont';tag.textContent='\\u2026continued ';el.appendChild(tag);cur.appendChild(el);}}"
 "else{i++;}}}"
 "function splitNode(node){var words=node.textContent.split(/\\s+/).filter(Boolean);"
 "fillWords(node,words);}"
 "blocks.forEach(function(node){"
 "if(node.classList.contains('rhead')){held=node;return;}"
 "flushHeld();cur.appendChild(node);"
 "if(!fits(cur)){cur.removeChild(node);"
 "var kids=cur.children,last=kids[kids.length-1];"
 "if(last&&last.classList&&last.classList.contains('rhead')){cur.removeChild(last);held=last;}"
 "cur=mkPage();flushHeld();"
 "if(node.classList.contains('step')||node.classList.contains('ing')||node.classList.contains('tips'))splitNode(node);"
 "else cur.appendChild(node);}});"
 "flushHeld();"
 "var all=Array.prototype.slice.call(holder.children);"
 "if(matchMedia('(prefers-reduced-motion: reduce)').matches)holder.parentElement.classList.add('instant');"
 "var turned=0;"
 "function render(){all.forEach(function(p,i){var t=i<turned;p.classList.toggle('turned',t);"
 "p.style.zIndex=t?(i+1):(all.length-i);});}"
 "function go(n){turned=Math.max(0,Math.min(all.length-1,n));render();}"
 "function onTap(el,fn){if(!el)return;el.addEventListener('click',fn);"
 "el.addEventListener('keydown',function(e){if(e.key==='Enter'||e.key===' '){e.preventDefault();fn();}});}"
 "onTap(zl,function(){go(turned-1);});"
 "onTap(zr,function(){go(turned+1);});"
 "var x0=null;holder.addEventListener('touchstart',function(e){x0=e.touches[0].clientX;},{passive:true});"
 "holder.addEventListener('touchend',function(e){if(x0===null)return;var dx=e.changedTouches[0].clientX-x0;x0=null;"
 "if(dx<-30)go(turned+1);else if(dx>30)go(turned-1);},{passive:true});"
 "document.addEventListener('keydown',function(e){if(all.length<2)return;"
 "var b=document.getElementById('book3d');if(!b||!b.classList.contains('flipped'))return;"
 "if(e.key==='ArrowRight'){e.stopPropagation();go(turned+1);}"
 "else if(e.key==='ArrowLeft'){e.stopPropagation();go(turned-1);}},true);"
 "render();})();</script>")

SAKURA_CSS = ("<style>#sakura{position:fixed;inset:0;width:100%;height:100%;"
 "z-index:-1;pointer-events:none}"
 "main{position:relative;z-index:0}"
 "@media print{#sakura{display:none}}</style>")

SAKURA_DIV = ("<canvas id=\"sakura\"></canvas>"
 "<script src=\"/assets/sakura.js?v=" + V + "\"></script>")



HOME_CSS = ("<style>"
 ".home{font-size:16px}"
 ".home header{margin-bottom:.4em;padding:.7em 1em .4em}"
 ".home h1{font-size:1.5rem;margin:.15rem 0}"
 ".home .topline{display:flex;align-items:center;gap:1.4em;flex-wrap:wrap}"
 ".home .tag{margin:0;font-size:.95em;flex:1 1 12em}"
 ".home .search{margin:1.4em auto;max-width:40em}"
  ".home .search input{font-size:1.2em;padding:.6em 1.1rem}"
  ".home .deck{display:flex;justify-content:center;align-items:center;"
 "max-width:56rem;margin:0 auto;padding:clamp(12px,3vw,32px) 1em clamp(16px,3vw,40px)}"
 ".home footer{margin:1em 0 .6em}"
  "@media(min-width:1100px) and (min-height:700px){"
 ".home{display:flex;flex-direction:column}"
 ".home .deck{flex:1;min-height:0}}"
 "@media(max-width:700px){"
 ".home .topline{gap:.7em}"
 ".home .search{max-width:none;flex:1 1 100%}}"
  "</style>")



def _book(title="Grandpa's voice memos, kept as recipes", subtitle="",
          body=None,
          quote="Don't rush the onions, they'll punish you.",
          frm="from Thatha's voice memo", intake=False, pager=False) -> str:
    """3D book hero; inside page is generated from the calling context."""
    nest = "<div>" * 10 + "</div>" * 10  # 10-deep slices = bending cover
    if body is None:
        body = ("<ol><li>Add a voice memo</li>"
                "<li>We extract the recipe</li>"
                "<li>It lands in the family book</li></ol>")
    sub = (f"<p class=\"sub\">{html.escape(subtitle)}</p>"
           if subtitle.strip() else "")
    content = (f"<h3>{html.escape(title)}</h3>" + sub + body
               + (f"<p class=\"quote\">{html.escape(quote)}</p>" if quote else "")
               + (f"<p class=\"from\">&mdash; {html.escape(frm)}</p>" if frm else ""))
    if pager:
        content = ("<div class=\"pages\" id=\"recipe_pages\">" + content + "</div>"
                   "<div class=\"pturn pturn-left\" id=\"pturn_left\" role=\"button\" "
                   "aria-label=\"Previous page\" tabindex=\"0\"></div>"
                   "<div class=\"pturn pturn-right\" id=\"pturn_right\" role=\"button\" "
                   "aria-label=\"Next page\" tabindex=\"0\"></div>")
    return (BOOK_CSS + "<div class=\"book-viewport\" role=\"group\" "
            + "aria-label=\"Family recipe book\">"
            + "<div class=\"scene book3d" + (" intake" if intake else "") + "\" id=\"book3d\">"
            + "<div id=\"book\">"
            + "<div id=\"top\"><div id=\"top-text\"" + (" class=\"paged\"" if pager else "") + ">"
            + content
            + "</div></div>"
            + "<div id=\"bottom\"></div>"
            + "<div id=\"front\"></div>"
            + "<div id=\"right\"></div>"
            + "<div id=\"bookmark\"><div><div><div><div></div></div></div></div></div>"
            + "<div id=\"bookmark-shadow\"></div>"
            + "</div>"
            + "<div id=\"flip\" tabindex=\"0\" role=\"button\" aria-label=\"Recipe book cover\"><div id=\"front\">" + nest + "</div>"
            + "<div id=\"back\">" + nest + "</div></div>"
            + ("" if (intake or pager) else "<div class=\"zone zone-left\"></div>"
               "<div class=\"zone zone-right\"></div>")
            + "</div>"
            + "</div>" + BOOK_JS)


def index(recs: list, langs: dict) -> str:
    _ = recs  # list lives on search + /category pages, not the home page
    h = [_head(f"{TITLE}"),
         SAKURA_DIV,
         HOME_CSS,
         "<main class=\"index home\"><header><div class=\"topline\">"
         "<div class=\"name\">"
         "<nav><a href=\"/\"><img class=\"logo\" src=\"/assets/logo.svg\"></a> "
         "<i>\u27e9</i></nav>",
          f"<h1 style=\"position:absolute;width:1px;height:1px;overflow:hidden;clip:rect(0 0 0 0);white-space:nowrap\">{html.escape(TITLE)}</h1></div>"
          f"<p class=\"tag\">{html.escape(DESC)}</p>",
          "<aside class=\"search\"><input type=\"text\" placeholder=\"Search...\" "
          "id=\"search_input\" disabled><div class=\"results\" id=\"search_output\">"
          "</div><script src=\"/assets/search.js?v=" + V + "\"></script></aside>"
          "</div></header>",
          INTAKE_CSS,
          "<div class=\"deck\">",
          _book(body=("<ol><li><details id=\"memo_details\">"
                      "<summary>Add a voice or live memo</summary>"
                      "<form id=\"voice_intake\" action=\"/extract\" method=\"post\" "
                      "enctype=\"multipart/form-data\">"
                      "<div class=\"book-actions\">"
                      "<button type=\"button\" id=\"voice_btn\">Voice</button>"
                      "<button type=\"button\" id=\"live_btn\">Live</button>"
                      "</div>"
                      "<input type=\"file\" id=\"memo_file\" name=\"memo\" hidden>"
                      "<input type=\"hidden\" name=\"language\" value=\"auto\">"
                      "<p class=\"live-timer\" id=\"live_timer\"></p>"
                      "<p class=\"intake-status\" id=\"intake_status\" role=\"status\"></p>"
                      "</form>"
                      "</details></li>"
                      "<li>We extract the recipe</li>"
                      "<li>It lands in the family book</li></ol>"),
                intake=True), "</div>",
          INTAKE_JS]
    return "".join(h) + _icon_js() + _close()


def category_page(cat: str, recs: list) -> str:
    """Category: slim header + centered 3D book only (no list section)."""
    h = [_head(f"{cat}"),
         SAKURA_DIV,
         "<main class=\"index\"><header><div class=\"name\">",
         "<nav><a href=\"/\"><img class=\"logo\" src=\"/assets/logo.svg\"></a> "
         "<i>\u27e9</i></nav>",
          f"<h1>{html.escape(cat)}</h1></div></header>",
          _book(title=cat,
                body="<ol>" + "".join(
                    f"<li>{html.escape(t)}</li>" for t in
                    [t for t in (r["meta"].get("title", "")[:40]
                                 for r in recs[:3]) if t]) + "</ol>",
                quote=f"{len(recs)} recipe"
                      f"{'s' if len(recs) != 1 else ''} and counting",
                frm="the family book")]
    return "".join(h) + _icon_js() + _close()


def recipe_page(r: dict) -> str:
    """Recipe detail: slim header (nav + meta); the full recipe lives in the book."""
    m = r["meta"]
    h = [_head(f"{m.get('title', '')}"),
         SAKURA_DIV,
         "<main class=\"recipe\"><header><div class=\"name\">",
         "<nav><a href=\"/\"><img class=\"logo\" src=\"/assets/logo.svg\"></a> "
         f"<i>\u27e9</i> {html.escape(m.get('category', ''))} <i>\u27e9</i></nav>",
         "</div><ul class=\"meta\">"]
    if m.get("favorite"):
        h.append("<li>{} Favorite</li>".format(_icon('star', 'Favorite')))
    if m.get("size"):
        h.append(f"<li>{_icon('tools-kitchen-2', 'Size')} {html.escape(m['size'])}</li>")
    if m.get("time"):
        h.append(f"<li>{_icon('clock', 'Time')} {html.escape(m['time'])}</li>")
    if m.get("author"):
        h.append(f"<li>{_icon('user', 'Author')} {html.escape(m['author'])}</li>")
    if not m.get("veggie") and not m.get("vegan") and not m.get("memo"):
        h.append(f"<li>{_icon('meat', 'Meat')} Meat</li>")
    if m.get("memo"):
        h.append(f"<li>{_icon('microphone', 'Voice memo')} Voice memo</li>")
    for key, icon, label in FLAGS:
        if m.get(key):
            h.append(f"<li>{_icon(icon, label)} {html.escape(label)}</li>")
    h.append("</ul>")
    h.append("</header>")
    ings = [(q, n) for s in r["steps"] for q, n in s["ings"]]
    texts = [s["text"] for s in r["steps"] if s["text"]]
    body = ""
    if ings:
        body += "<h4 class=\"rhead\">Ingredients</h4>" + "".join(
            f"<p class=\"ing\">{html.escape(q + ' \u2014 ' + n) if (q and n) else html.escape(q or n)}</p>"
            for q, n in ings)
    if texts:
        body += "<h4 class=\"rhead\">Steps</h4>" + "".join(
            f"<p class=\"step\"><span class=\"sn\">{i}.</span> {html.escape(t)}</p>"
            for i, t in enumerate(texts, 1))
    h.append(_book(title=m.get("title", ""),
                   subtitle=m.get("original_title", ""),
                   body=body,
                   quote=m.get("description") or (texts[0] if texts else ""),
                   frm=m.get("author") or m.get("category", "")
                   or "the family book",
                   pager=True))
    if m.get("image"):
        h.append(f"<div class=\"servingsuggestion\"><img src=\"{html.escape(m['image'])}\"></div>")
    return "".join(h) + _icon_js() + PAGER_JS + _close()


def search_index(recs: list) -> list:
    out = []
    for r in recs:
        m = r["meta"]
        out.append({"title": m.get("title", ""), "original_title": m.get("original_title", ""),
                    "category": m.get("category", ""), "author": m.get("author", ""),
                    "description": m.get("description", ""),
                    "htmlfile": f"/recipe/{m['slug']}",
                    "favorite": bool(m.get("favorite")),
                    "veggie": bool(m.get("veggie")), "vegan": bool(m.get("vegan")),
                    "spicy": bool(m.get("spicy")), "sweet": bool(m.get("sweet")),
                    "salty": bool(m.get("salty")), "sour": bool(m.get("sour")),
                    "bitter": bool(m.get("bitter")), "umami": bool(m.get("umami"))})
    return out
