#!/usr/bin/env python3
import base64, html, json, re, shutil
from datetime import datetime, timedelta
from pathlib import Path
from urllib.parse import urlparse
from playwright.sync_api import sync_playwright

W,H=1080,1350
INPUT=Path('data/selected_story.json'); ROOT=Path('output/posts'); RETENTION_DAYS=7
CREAM='#F2EBDD'; INK='#0B0D0C'; FOREST='#12382E'; RED='#B70C07'; GOLD='#C8A45A'; BLUE='#426A78'; LIME='#B7E32B'
LEAK=re.compile(r'(callout graphic|visual concept|visual direction|visual strategy|design direction|layout instruction|highlight that|data graphic showing|contrast visual between|illustrate that|graphic showing|render this|create a|clean typography layout|diagram comparing|official diagram schematic|featured quote block|data metric visualization|summary graphics card)',re.I)

def clean(v):
    if isinstance(v,list): v=' '.join(map(str,v))
    if isinstance(v,dict): return ''
    return re.sub(r'\s+',' ',str(v or '')).strip()
def esc(v): return html.escape(clean(v),quote=True)
def first(*vs):
    for v in vs:
        v=clean(v)
        if v:return v
    return ''
def words(v): return re.findall(r"\b[\w’'-]+\b",clean(v))
def punch(v,max_words=8,max_chars=68):
    v=clean(v)
    if not v:return 'GETBYTERUSH'
    if len(words(v))<=max_words and len(v)<=max_chars:return v.rstrip(' .')
    s=re.split(r'(?<=[.!?])\s+',v)[0]
    if len(words(s))<=max_words and len(s)<=max_chars:return s.rstrip(' .')
    out=' '.join(words(v)[:max_words])
    if len(out)>max_chars: out=out[:max_chars].rsplit(' ',1)[0]
    return out.rstrip(' ,.;:')+'…'
def support(v,max_chars=115):
    v=clean(v)
    if not v or LEAK.search(v):return ''
    if len(v)<=max_chars:return v
    return v[:max_chars].rsplit(' ',1)[0].rstrip(' ,.;:')+'…'
def source(story,slide):
    src=story.get('source_story') if isinstance(story.get('source_story'),dict) else {}
    return first(slide.get('source_label'),src.get('source'),story.get('source'),'Source')[:90], first(slide.get('asset_url'),slide.get('source_url'),src.get('url'),story.get('source_url'))
def role(slide,i,total):
    x=first(slide.get('role'),slide.get('scene_role')).lower().replace(' ','_')
    if x:return x
    vt=first(slide.get('visual_type'),slide.get('layout')).lower()
    if i==1:return 'interrupt'
    if vt in {'evidence','screenshot','receipt'}:return 'proof'
    if vt in {'metric','number','stat'}:return 'metrics'
    if vt in {'quote','statement','typography'}:return 'statement'
    if i==total:return 'payoff'
    if vt in {'diagram','flow','process','architecture'}:return 'diagram'
    return 'editorial'
def content(slide):
    return punch(first(slide.get('headline'),slide.get('title'),slide.get('hook'),slide.get('text')),8,68), support(first(slide.get('body'),slide.get('supporting_text'),slide.get('copy'),slide.get('description')),115)
def numbers(text):
    return re.findall(r'(?<![A-Za-z])[+−-]?\d+(?:\.\d+)?\s*(?:x|%|ms|GB|TB|PB|M|B|K)(?![A-Za-z])',clean(text),re.I)
def metric_points(slide,head,body):
    raw=slide.get('data_points') or slide.get('stats') or slide.get('metrics') or []
    out=[]
    if isinstance(raw,list):
        for z in raw:
            if isinstance(z,dict):
                v=first(z.get('value'),z.get('number'),z.get('stat')); lab=first(z.get('label'),z.get('title'),z.get('name')); d=support(first(z.get('description'),z.get('body')),65)
                if v and lab:out.append((v,lab,d))
    if out:return out[:3]
    full=head+' '+body; low=full.lower(); seen=set()
    for n in numbers(full):
        key=n.replace(' ','').replace('−','-')
        if key in seen:continue
        seen.add(key); pos=low.find(n.lower().replace('−','-')); w=low[max(0,pos-90):pos+130]
        lab='BANDWIDTH' if 'bandwidth' in w else 'POWER' if 'power' in w else 'COMPUTE SPACE' if 'space' in w or 'die' in w else 'THROUGHPUT' if 'throughput' in w else 'TOKEN COST' if 'token cost' in w else 'KEY RESULT'
        out.append((n,lab,''))
    return out[:3]
def capture(url,dest):
    if not url or not urlparse(url).scheme:return None
    dest=Path(dest).resolve(); dest.parent.mkdir(parents=True,exist_ok=True)
    try:
        with sync_playwright() as pw:
            b=pw.chromium.launch(headless=True,args=['--no-sandbox','--disable-dev-shm-usage'])
            pg=b.new_page(viewport={'width':1440,'height':1000},device_scale_factor=1)
            pg.goto(url,wait_until='domcontentloaded',timeout=30000); pg.wait_for_timeout(1200)
            pg.add_style_tag(content='''#onetrust-banner-sdk,#onetrust-consent-sdk,[aria-label*="cookie" i],[class*="cookie" i],[id*="cookie" i]{display:none!important}''')
            pg.evaluate('window.scrollTo(0,0)'); pg.wait_for_timeout(250); pg.screenshot(path=str(dest),full_page=False); b.close()
        return dest if dest.exists() else None
    except Exception as e:
        print('WARNING evidence capture failed:',e); return None
def data_uri(path):
    if not path or not Path(path).exists():return ''
    return 'data:image/png;base64,'+base64.b64encode(Path(path).read_bytes()).decode()
def css():
    return '''@page{size:1080px 1350px;margin:0}*{box-sizing:border-box}html,body{margin:0;padding:0;width:1080px;height:1350px;overflow:hidden}body{font-family:Inter,Arial,Helvetica,sans-serif}.s{position:relative;width:1080px;height:1350px;overflow:hidden;background:#F2EBDD;color:#0B0D0C}.meta{position:absolute;top:30px;left:52px;right:52px;display:flex;justify-content:space-between;align-items:center;font:900 10px/1 ui-monospace,monospace;letter-spacing:1.4px;text-transform:uppercase;z-index:20}.page{border:1px solid currentColor;padding:7px 9px}.foot{position:absolute;left:52px;right:52px;bottom:27px;display:flex;justify-content:space-between;font:800 9px/1 ui-monospace,monospace;letter-spacing:1.2px;text-transform:uppercase;opacity:.55;z-index:20}.k{font:900 10px/1 ui-monospace,monospace;letter-spacing:1.7px;text-transform:uppercase;color:#B70C07}.h{font-weight:950;letter-spacing:-4.5px;line-height:.84;text-transform:uppercase}.fine{font:800 10px/1.2 ui-monospace,monospace;letter-spacing:1px;text-transform:uppercase;opacity:.68}.hero{position:absolute;left:52px;right:52px;top:112px}.hero h1{margin:15px 0 0;max-width:940px;font-size:82px}.hero p{max-width:690px;margin:20px 0 0;font-size:18px;line-height:1.2;opacity:.72}.gridbg{background-image:linear-gradient(rgba(11,13,12,.07) 1px,transparent 1px),linear-gradient(90deg,rgba(11,13,12,.07) 1px,transparent 1px);background-size:28px 28px}.hook{position:absolute;left:52px;right:52px;top:360px;bottom:82px;display:grid;grid-template-columns:1.48fr .78fr;gap:14px}.redpanel{background:#B70C07;color:#F2EBDD;padding:28px;position:relative;overflow:hidden}.redpanel:after{content:"";position:absolute;left:28px;right:28px;bottom:24px;height:1px;background:rgba(242,235,221,.5)}.redpanel .num{font:900 11px/1 ui-monospace,monospace;letter-spacing:1.5px}.redpanel .big{margin-top:52px;font-size:76px;line-height:.8;letter-spacing:-4px;font-weight:950;text-transform:uppercase}.blackpanel{background:#0B0D0C;color:#F2EBDD;padding:28px;position:relative;overflow:hidden}.blackpanel .shape{position:absolute;right:-30px;bottom:-20px;font:950 190px/.7 Arial;color:#B70C07;transform:rotate(-12deg)}.blackpanel .copy{position:absolute;left:28px;right:28px;bottom:32px;font-size:20px;line-height:1.03;font-weight:900;text-transform:uppercase}.blocks{position:absolute;left:52px;right:52px;top:430px;bottom:82px;display:grid;grid-template-columns:1fr 1fr;gap:14px}.blk{padding:27px;position:relative;overflow:hidden}.blk.light{background:#F2EBDD;border:2px solid #0B0D0C}.blk.dark{background:#0B0D0C;color:#F2EBDD}.blk.forest{background:#12382E;color:#F2EBDD}.blk.red{background:#B70C07;color:#F2EBDD}.blk .index{position:absolute;right:17px;top:14px;font:950 72px/.7 ui-monospace,monospace;opacity:.13}.blk .label{font:900 10px/1 ui-monospace,monospace;letter-spacing:1.3px;text-transform:uppercase;opacity:.7}.blk strong{display:block;margin-top:50px;max-width:420px;font-size:49px;line-height:.86;letter-spacing:-2.5px;font-weight:950;text-transform:uppercase}.blk p{max-width:390px;margin-top:20px;font-size:15px;line-height:1.2;opacity:.72}.arrow{position:absolute;right:18px;bottom:17px;font:950 74px/.7 Arial;color:#B70C07}.evidence{position:absolute;left:52px;right:52px;top:400px;bottom:78px}.evidence-frame{height:610px;background:#fff;border:2px solid #0B0D0C;padding:12px;position:relative;box-shadow:18px 18px 0 #B70C07;overflow:hidden}.evidence-frame img{width:100%;height:100%;object-fit:contain;display:block;background:#fff}.evidence-tag{position:absolute;left:18px;top:18px;background:#0B0D0C;color:#F2EBDD;padding:9px 11px;font:900 10px/1 ui-monospace,monospace;letter-spacing:1.2px;z-index:2}.evidence-line{margin-top:18px;display:flex;justify-content:space-between;font:800 9px/1.2 ui-monospace,monospace;letter-spacing:1.1px;text-transform:uppercase;opacity:.6}.metrics{position:absolute;left:52px;right:52px;top:455px;bottom:80px;display:grid;grid-template-columns:1fr 1fr 1fr;gap:14px}.metric{padding:24px 20px;border-top:7px solid #0B0D0C;position:relative;overflow:hidden}.metric:nth-child(2){background:#12382E;color:#F2EBDD;border-top-color:#12382E;transform:translateY(20px);box-shadow:14px 14px 0 #B70C07}.metric .v{font:950 92px/.78 ui-monospace,monospace;letter-spacing:-8px;color:#B70C07}.metric:nth-child(2) .v{color:#F2EBDD}.metric .l{margin-top:38px;font-size:21px;line-height:.9;font-weight:950;text-transform:uppercase;letter-spacing:-.7px}.metric .d{margin-top:14px;font-size:13px;line-height:1.18;opacity:.68}.redstatement{position:absolute;inset:400px 0 0;background:#B70C07;color:#F2EBDD;padding:64px 52px;overflow:hidden}.redstatement:after{content:"× × ×";position:absolute;right:38px;bottom:30px;font:900 42px/1 ui-monospace,monospace;letter-spacing:10px;opacity:.28}.redstatement .bar{height:5px;width:145px;background:#F2EBDD;margin-bottom:28px}.redstatement strong{display:block;max-width:890px;font-size:84px;line-height:.8;letter-spacing:-5px;font-weight:950;text-transform:uppercase}.redstatement p{max-width:670px;margin-top:24px;font-size:18px;line-height:1.18;opacity:.78}.flow{position:absolute;left:52px;right:52px;top:465px;bottom:85px;display:grid;grid-template-columns:1fr 62px 1fr 62px 1fr;align-items:center}.node{height:190px;padding:23px;border:2px solid #0B0D0C;background:#F2EBDD;position:relative}.node.green{background:#12382E;color:#F2EBDD;border-color:#12382E}.node.red{background:#B70C07;color:#F2EBDD;border-color:#B70C07}.node .t{font:900 9px/1 ui-monospace,monospace;letter-spacing:1.2px;text-transform:uppercase;opacity:.7}.node strong{display:block;margin-top:30px;font-size:30px;line-height:.9;letter-spacing:-1.5px;font-weight:950;text-transform:uppercase}.flowarrow{font-size:52px;font-weight:900;text-align:center;color:#B70C07}.pay{position:absolute;left:52px;right:52px;top:400px;bottom:82px;background:#0B0D0C;color:#F2EBDD;padding:58px 50px;overflow:hidden}.pay:before{content:"07";position:absolute;right:-15px;top:-45px;font:950 250px/.7 ui-monospace,monospace;color:#F2EBDD;opacity:.035}.pay:after{content:"↗";position:absolute;right:-8px;bottom:-75px;font:950 280px/.7 Arial;color:#B70C07;opacity:.9}.pay .bar{height:5px;width:145px;background:#B7E32B;margin-bottom:30px}.pay strong{display:block;max-width:820px;font-size:82px;line-height:.8;letter-spacing:-5px;font-weight:950;text-transform:uppercase}.pay p{max-width:650px;margin-top:25px;font-size:18px;line-height:1.18;opacity:.7}.sig{position:absolute;left:50px;bottom:28px;color:#C8A45A;font:900 9px/1 ui-monospace,monospace;letter-spacing:1.4px;text-transform:uppercase}'''

def body(slide,story,evidence,i,total):
    h,b=content(slide); r=role(slide,i,total); lab=first(slide.get('kicker'),r.replace('_',' '),'GETBYTERUSH'); src,_=source(story,slide)
    if r=='interrupt': return f'''<div class="hook"><div class="redpanel gridbg"><div class="num">01 / {esc(lab)}</div><div class="big">{esc(punch(h,7,50))}</div></div><div class="blackpanel"><div class="fine">GETBYTERUSH / TECH • AI • INTERNET</div><div class="shape">↗</div><div class="copy">{esc(support(b,75))}</div></div></div>'''
    if r in {'proof','evidence'} and evidence: return f'''<div class="hero"><div class="k">{esc(lab)}</div><h1 class="h" style="font-size:61px;max-width:910px">{esc(h)}</h1></div><div class="evidence"><div class="evidence-frame"><span class="evidence-tag">REAL-WORLD EVIDENCE</span><img src="{evidence}" alt="Source evidence"></div><div class="evidence-line"><span>{esc(src)}</span><span>{i:02d} / {total:02d}</span></div></div>'''
    if r=='metrics':
        pts=metric_points(slide,h,b)
        if pts:
            cards=''.join(f'<div class="metric"><div class="v">{esc(v)}</div><div class="l">{esc(l)}</div><div class="d">{esc(d)}</div></div>' for v,l,d in pts)
            return f'''<div class="hero"><div class="k">{esc(lab)}</div><h1 class="h" style="font-size:58px;max-width:900px">{esc(h)}</h1></div><div class="metrics">{cards}</div>'''
        return f'''<div class="hero"><div class="k">{esc(lab)}</div><h1 class="h" style="font-size:60px">{esc(h)}</h1></div><div class="redstatement"><div class="bar"></div><strong>{esc(punch(b,10,92))}</strong></div>'''
    if r=='statement': return f'''<div class="hero"><div class="k">{esc(lab)}</div><h1 class="h" style="font-size:62px;max-width:920px">{esc(h)}</h1></div><div class="redstatement"><div class="bar"></div><strong>{esc(punch(b or h,9,92))}</strong><p>{esc(src)}</p></div>'''
    if r=='diagram':
        a=first(slide.get('diagram_left'),slide.get('left_label'),'CONTEXT'); c=first(slide.get('diagram_right'),slide.get('right_label'),'REASONING'); mid=first(slide.get('diagram_middle'),slide.get('middle_label'),'KV CACHE')
        return f'''<div class="hero"><div class="k">{esc(lab)}</div><h1 class="h" style="font-size:60px;max-width:920px">{esc(h)}</h1><p>{esc(b)}</p></div><div class="flow"><div class="node"><div class="t">01 / INPUT</div><strong>{esc(punch(a,4,24))}</strong></div><div class="flowarrow">→</div><div class="node green"><div class="t">02 / SYSTEM</div><strong>{esc(punch(mid,4,24))}</strong></div><div class="flowarrow">→</div><div class="node red"><div class="t">03 / OUTPUT</div><strong>{esc(punch(c,4,24))}</strong></div></div>'''
    if r=='payoff': return f'''<div class="hero"><div class="k">{esc(lab)}</div><h1 class="h" style="font-size:63px;max-width:910px">{esc(h)}</h1></div><div class="pay"><div class="bar"></div><strong>{esc(punch(h,8,86))}</strong><p>{esc(support(b,100))}</p><div class="sig">GETBYTERUSH / TESTED • EXPLAINED • REAL</div></div>'''
    return f'''<div class="hero"><div class="k">{esc(lab)}</div><h1 class="h" style="font-size:62px;max-width:920px">{esc(h)}</h1></div><div class="blocks"><div class="blk dark"><div class="label">{esc(lab)}</div><div class="index">{i:02d}</div><strong>{esc(punch(h,7,45))}</strong><p>{esc(support(b,75))}</p></div><div class="blk red"><div class="label">THE TAKEAWAY</div><strong>{esc(punch(b or h,7,45))}</strong><p>{esc(src)}</p><div class="arrow">↗</div></div></div>'''
def render(story,out):
    slides=story.get('slides') or []; out.mkdir(parents=True,exist_ok=True); ev=None
    for s in slides:
        if role(s,int(s.get('number',0) or 0),len(slides)) in {'proof','evidence'}:
            _,u=source(story,s)
            if u:ev=capture(u,out/'evidence'/'source.png')
            break
    hd=out/'html'; pd=out/'slides'; hd.mkdir(exist_ok=True); pd.mkdir(exist_ok=True); evu=data_uri(ev); styles=css(); total=len(slides)
    with sync_playwright() as pw:
        b=pw.chromium.launch(headless=True,args=['--no-sandbox','--disable-dev-shm-usage']); pg=b.new_page(viewport={'width':W,'height':H},device_scale_factor=1)
        for i,s in enumerate(slides,1):
            src,_=source(story,s); inner=body(s,story,evu,i,total)
            doc=f'<!doctype html><html><head><meta charset="utf-8"><style>{styles}</style></head><body><main class="s"><div class="meta"><span>GETBYTERUSH</span><span>TECH • AI • INTERNET</span><span class="page">{i:02d} / {total:02d}</span></div>{inner}<div class="foot"><span>{esc(src)}</span><span>TESTED • EXPLAINED • REAL</span></div></main></body></html>'
            (hd/f'{i:02d}.html').write_text(doc,encoding='utf-8'); pg.set_content(doc,wait_until='load'); pg.screenshot(path=str(pd/f'{i:02d}.png'),full_page=False); print(f'✓ slide-{i:02d}.png')
        b.close()
    (out/'post.json').write_text(json.dumps(story,indent=2,ensure_ascii=False)+'\n',encoding='utf-8')
    title=clean(story.get('story_title','GetByteRush')); why=clean(story.get('why_this_story',''))
    (out/'caption.txt').write_text(f'{title}\n\n{why}\n\n#GetByteRush #AI #Technology #Internet\n',encoding='utf-8')
    (out/'hashtags.txt').write_text('#GetByteRush #AI #Technology #Internet #TechNews #ArtificialIntelligence\n',encoding='utf-8')
    (out/'alt-text.txt').write_text(f'GetByteRush editorial carousel about {title}.',encoding='utf-8'); (out/'pinned-comment.txt').write_text(first(story.get('pinned_comment'),'What changes next?'),encoding='utf-8')
def cleanup():
    cutoff=datetime.now()-timedelta(days=RETENTION_DAYS)
    if not ROOT.exists():return
    for d in list(ROOT.iterdir()):
        if not d.is_dir():continue
        for p in list(d.iterdir()):
            if not p.is_dir():continue
            try:t=datetime.strptime(p.name[:6],'%H%M%S'); pt=datetime.combine(datetime.strptime(d.name,'%Y-%m-%d').date(),t.time())
            except Exception:continue
            if pt<cutoff:shutil.rmtree(p,ignore_errors=True)
        try:
            if not any(d.iterdir()):d.rmdir()
        except OSError:pass
def main():
    if not INPUT.exists():raise SystemExit('Missing data/selected_story.json')
    story=json.loads(INPUT.read_text(encoding='utf-8'))
    if not story.get('selected') or not isinstance(story.get('slides'),list) or not story['slides']:raise SystemExit('Invalid selected editorial package')
    now=datetime.now(); slug=re.sub(r'[^a-z0-9]+','-',clean(story.get('story_title','getbyterush-post')).lower()).strip('-')[:90]; out=ROOT/now.strftime('%Y-%m-%d')/f'{now.strftime("%H%M%S")}-{slug}'; cleanup(); print('GETBYTERUSH PINTEREST-INSPIRED EDITORIAL RENDERER V5'); print(f'Slides: {len(story["slides"])} | Gemini: 0'); render(story,out); print(f'✓ Output: {out}')
if __name__=='__main__':main()
