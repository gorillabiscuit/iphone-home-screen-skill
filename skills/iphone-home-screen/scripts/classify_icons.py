#!/usr/bin/env python3
"""Offline border/glyph OKLab classifier. Requires already-installed Pillow/numpy."""
import argparse
import hashlib
import io
import json
from pathlib import Path
import numpy as np
from PIL import Image, ImageCms, ImageDraw, ImageFilter, ImageFont

def oklab(rgb):
    v=np.where(rgb<=.04045,rgb/12.92,((rgb+.055)/1.055)**2.4)
    lms=v@np.array([[.4122214708,.2119034982,.0883024619],
                    [.5363325363,.6806995451,.2817188376],
                    [.0514459929,.1073969566,.6299787005]])
    return np.cbrt(lms)@np.array([[.2104542553,1.9779984951,.0259040371],
                                 [.793617785,-2.428592205,.7827717662],
                                 [-.0040720468,.4505937099,-.808675766]])

def lch(v):
    return [float(v[0]),float(np.hypot(v[1],v[2])),float(np.degrees(np.arctan2(v[2],v[1]))%360)]

def bucket(v):
    L,C,H=lch(v)
    if C<.035:return 'white' if L>.9 else 'black' if L<.25 else 'grey'
    if H<30 or H>=350:return 'red'
    if H<75:return 'orange'
    if H<110:return 'yellow'
    if H<175:return 'green'
    if H<230:return 'cyan'
    if H<270:return 'blue'
    if H<325:return 'purple'
    return 'pink'

def cluster(pixels):
    if not len(pixels):return []
    rng=np.random.default_rng(17)
    pixels=pixels[rng.choice(len(pixels),min(3000,len(pixels)),replace=False)]
    best=None
    for _ in range(5):
        centres=pixels[rng.choice(len(pixels),min(4,len(pixels)),replace=False)].copy()
        for step in range(20):
            d=((pixels[:,None,:]-centres[None,:,:])**2).sum(2)
            labels=d.argmin(1)
            fresh=np.array([pixels[labels==i].mean(0) if np.any(labels==i) else centres[i] for i in range(len(centres))])
            if np.max(np.abs(fresh-centres))<.0001:
                centres=fresh;break
            centres=fresh
        d=((pixels[:,None,:]-centres[None,:,:])**2).sum(2)
        labels=d.argmin(1);cost=d.min(1).sum()
        if best is None or cost<best[0]:best=(cost,centres.copy(),labels.copy())
    _,centres,labels=best
    return sorted([(c,float(np.mean(labels==i))) for i,c in enumerate(centres) if np.any(labels==i)],key=lambda x:-x[1])

def classify(path):
    raw=Path(path).read_bytes();im=Image.open(io.BytesIO(raw))
    warnings=[]
    if im.info.get('icc_profile'):
        try:
            profile=ImageCms.ImageCmsProfile(io.BytesIO(im.info['icc_profile']))
            alpha=im.convert('RGBA').getchannel('A')
            im=ImageCms.profileToProfile(im.convert('RGB'),profile,ImageCms.createProfile('sRGB'),outputMode='RGB')
            im.putalpha(alpha)
        except Exception as exc:warnings.append('ICC conversion failed: '+type(exc).__name__)
    im=im.convert('RGBA').resize((128,128),Image.Resampling.LANCZOS)
    a=np.asarray(im)
    shape=Image.new('L',(128,128));ImageDraw.Draw(shape).rounded_rectangle((0,0,127,127),radius=28,fill=255)
    mask=Image.fromarray(np.where((a[:,:,3]>=250)&(np.asarray(shape)>0),255,0).astype('uint8'))
    inner=np.asarray(mask.filter(ImageFilter.MinFilter(9)))>0
    # Edge erosion needs an exterior zero border; PIL repeats boundary pixels.
    pad=Image.new('L',(154,154));pad.paste(mask,(13,13))
    near=np.asarray(pad.filter(ImageFilter.MinFilter(11)).crop((13,13,141,141)))>0
    far=np.asarray(pad.filter(ImageFilter.MinFilter(27)).crop((13,13,141,141)))>0
    ring=near&~far
    lab=oklab(a[:,:,:3]/255.)
    if inner.sum()<50 or ring.sum()<20:raise ValueError('Too few opaque pixels for classification')
    bg=np.median(lab[ring],axis=0)
    uniformity=float(np.mean(np.linalg.norm(lab[ring]-bg,axis=1)<.05))
    glyph=inner&(np.linalg.norm(lab-bg,axis=2)>.08)
    whole=cluster(lab[inner])
    palette=cluster(lab[glyph]) if uniformity>=.7 and glyph.sum()>10 else whole
    base=bg if uniformity>=.7 else whole[0][0]
    chromatic=[(c,s) for c,s in palette if lch(c)[1]>=.035]
    accent=max(chromatic,key=lambda v:v[1]*lch(v[0])[1])[0] if chromatic else None
    significant=[lch(c)[2] for c,s in palette if s>=.15 and lch(c)[1]>=.035]
    distinct=[]
    for h in significant:
        if all(min(abs(h-j),360-abs(h-j))>60 for j in distinct):distinct.append(h)
    result={'sha256':hashlib.sha256(raw).hexdigest(),'base_oklch':lch(base),
            'accent_oklch':lch(accent) if accent is not None else None,
            'background_bucket':bucket(base),'accent_bucket':bucket(accent) if accent is not None else None,
            'neutral':lch(base)[1]<.035,'multicolour':len(distinct)>=3,
            'glyph_share':float(glyph.sum()/inner.sum()) if uniformity>=.7 else None,
            'uniformity':uniformity,'confidence':'heuristic; visually review',
            'warnings':warnings}
    result['review_reasons']=[]
    if uniformity<.7:result['review_reasons'].append('Photo or gradient: background/glyph separation uncertain')
    if result['multicolour']:result['review_reasons'].append('Multicoloured symbol: do not sort solely by one accent')
    result['bucket']=result['background_bucket']
    if result['neutral'] and uniformity>=.7 and result['glyph_share']>=.08 and accent is not None and lch(accent)[1]>=.08:
        result['alternative_bucket']=bucket(accent)
    return result

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--manifest',required=True,help='JSON list of path,label,identity,source')
    p.add_argument('--out',required=True)
    args=p.parse_args();out=Path(args.out);out.mkdir(parents=True,exist_ok=False)
    results=[]
    for record in json.loads(Path(args.manifest).read_text()):
        try:results.append({**record,**classify(record['path'])})
        except Exception as exc:results.append({**record,'error':str(exc)})
    (out/'colours.json').write_text(json.dumps(results,indent=2))
    good=sorted([r for r in results if 'error' not in r],key=lambda r:(r['bucket'],r['base_oklch'][0]))
    font_path=Path('/System/Library/Fonts/Supplemental/Arial Unicode.ttf')
    font=ImageFont.truetype(str(font_path),14) if font_path.exists() else ImageFont.load_default(size=14)
    for offset in range(0,len(good),48):
        items=good[offset:offset+48];sheet=Image.new('RGB',(1200,((len(items)+7)//8)*170+35),'#eeeef0')
        draw=ImageDraw.Draw(sheet);draw.text((12,8),'Heuristic colour groups - review visually; source appearance may differ',font=font,fill='black')
        for n,r in enumerate(items):
            x=(n%8)*150+15;y=(n//8)*170+40
            icon=Image.open(r['path']).convert('RGBA');icon.thumbnail((95,95))
            sheet.paste(icon,(x+12,y),icon)
            draw.text((x,y+100),r.get('label',r['identity'])[:19],font=font,fill='black')
            b=r['bucket']+(' / '+r['alternative_bucket'] if r.get('alternative_bucket') else '')
            draw.text((x,y+120),b,font=font,fill='#333333')
        sheet.save(out/f'contact-{offset//48+1:02}.png')
    print(json.dumps({'classified':len(good),'failed':len(results)-len(good),'output':str(out)}))

if __name__=='__main__':main()
