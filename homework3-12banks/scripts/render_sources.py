"""Private visual review sheets for independently checked source pages."""
import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
from common import ROOT
import pypdfium2 as pdf
from PIL import Image,ImageDraw,ImageFont
specs={'中国银行':[7,13,66],'交通银行':[10,30],'光大银行':[10,19,55],'兴业银行':[13,17,18],'农业银行':[11,16],'北京银行':[6,15,35],'华夏银行':[6,50],'厦门银行':[2,7,22],'工商银行':[13,15,19,21],'建设银行':[8,9,14],'招商银行':[9,38],'郑州银行':[8,9,17]}
out=ROOT/'tmp/source_review';out.mkdir(parents=True,exist_ok=True)
font=ImageFont.truetype('C:/Windows/Fonts/msyh.ttc',22)
images=[]
for company,numbers in specs.items():
    source=next((ROOT.parent/'银行2026半年报').glob(company+'：*.pdf')); d=pdf.PdfDocument(source)
    for n in numbers:
        im=d[n-1].render(scale=1.5).to_pil().convert('RGB'); im.save(out/f'{company}-p{n}.png')
        im.thumbnail((600,860)); tile=Image.new('RGB',(620,915),'#e8edf1'); tile.paste(im,((620-im.width)//2,48)); ImageDraw.Draw(tile).text((10,10),f'{company} PDF {n}',font=font,fill='#172c3c');images.append(tile)
    d.close()
for batch in range(0,len(images),6):
    sheet=Image.new('RGB',(1860,1830),'white')
    for i,im in enumerate(images[batch:batch+6]):sheet.paste(im,((i%3)*620,(i//3)*915))
    sheet.save(out/f'sheet-{batch//6+1}.jpg')
print(out)
