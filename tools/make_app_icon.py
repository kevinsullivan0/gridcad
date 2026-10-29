"""Generate GridCAD's original MIT-licensed vector mark and Windows icon sizes.

No vendor artwork or third-party font. Pillow is an existing build dependency.
"""
from pathlib import Path
from PIL import Image, ImageDraw
ROOT=Path(__file__).resolve().parents[1]

def main():
    folder=ROOT/'resources';folder.mkdir(exist_ok=True)
    tiles=[(x,y,'#35b6ce' if (x,y) in [(48,48),(104,104),(160,160)] else '#dae8ef') for y in (48,104,160) for x in (48,104,160)]
    svg='<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 256 256" role="img" aria-label="GridCAD rectangular grid mark">\n<rect width="256" height="256" rx="36" fill="#182a3c"/>\n'
    for x,y,color in tiles:svg+=f'<rect x="{x}" y="{y}" width="48" height="48" rx="6" fill="{color}"/>\n'
    svg+='</svg>\n';(folder/'gridcad.svg').write_text(svg,encoding='utf-8')
    scale=4;im=Image.new('RGBA',(256*scale,256*scale));d=ImageDraw.Draw(im)
    d.rounded_rectangle((0,0,256*scale-1,256*scale-1),radius=36*scale,fill='#182a3c')
    for x,y,color in tiles:d.rounded_rectangle((x*scale,y*scale,(x+48)*scale-1,(y+48)*scale-1),radius=6*scale,fill=color)
    im=im.resize((256,256),Image.Resampling.LANCZOS)
    im.save(folder/'gridcad.png');im.save(folder/'gridcad.ico',sizes=[(n,n) for n in (16,24,32,48,64,128,256)])
if __name__=='__main__':main()
