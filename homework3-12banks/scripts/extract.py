"""Full-report extraction. Source text is retained; normalized text is for search only."""
import sys, argparse, hashlib, re, concurrent.futures
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
from common import ROOT, write_json, normalize
import pdfplumber
from pypdf import PdfReader

def extract_one(path):
    path=Path(path); company=path.name.split('：')[0]; pages=[]; chunks=[]; tables=[]
    reader=PdfReader(path); section='封面及前言'; outlines={}
    def walk(items):
        for item in items:
            if isinstance(item,list): walk(item)
            else:
                try: outlines[reader.get_destination_page_number(item)]=normalize(item.title)
                except Exception: pass
    walk(reader.outline)
    with pdfplumber.open(path) as doc:
        for n, page in enumerate(doc.pages,1):
            # layout=True retains horizontal spacing. Table cells are serialized below.
            text=page.extract_text(layout=True) or ''
            lines=[l.rstrip() for l in text.splitlines() if l.strip()]
            raw='\n'.join(lines); plain=normalize(raw)
            if n-1 in outlines: section=outlines[n-1]
            else:
                for l in lines[:12]:
                    h=normalize(l)
                    if re.match(r'^(第[一二三四五六七八九十\d]+[章节]|管理层讨论|财务回顾|风险管理|资本管理|公司治理|重要事项|财务报告)',h) and len(h)<65:
                        section=h; break
            # A printed locator is an observation, never assumed to equal PDF index.
            printed=None
            for l in lines[:3]+lines[-3:]:
                h=normalize(l)
                m=re.match(r'^(\d{1,3})\s+.*(?:半年度报告|中国建设银行)',h) or re.search(r'(?:半年度报告)\s+(\d{1,3})$',h)
                if m: printed=m.group(1); break
                if re.fullmatch(r'\d{1,3}',h): printed=h
            base={'company':company,'report':path.name,'year':2026,'period':'2026H1','pdf_page':n,'printed_page':printed,'section':section}
            structured=[]
            # Ruling-line tables. No claim that all borderless tables are recovered.
            for ti,table in enumerate(page.find_tables()):
                rows=table.extract()
                if len(rows)<2 or max((len(r) for r in rows),default=0)<2: continue
                tid=f'{company}-p{n:03d}-t{ti+1}'
                cleaned=[[re.sub(r'\s+',' ',c or '').strip() for c in r] for r in rows]
                if sum(bool(c) for r in cleaned for c in r)<4: continue
                record={**base,'table_id':tid,'bbox':list(table.bbox),'rows':cleaned,'method':'pdfplumber-lines','reviewed':False}
                tables.append(record)
                # Repeat all header candidates in each row chunk; preserve full table separately.
                header=' | '.join(cleaned[0]); context='\n'.join(lines[:10])
                for ri,row in enumerate(cleaned[1:],2):
                    body=f'表格 {tid}，第 {ri} 行\n页首上下文：{context}\n首行：{header}\n当前行：'+ ' | '.join(row)
                    structured.append({**base,'id':f'{tid}-r{ri}','kind':'table_row','table_id':tid,'row':ri,'text':body,'search_text':normalize(body)})
            # Page-bounded chunks avoid assigning one page number to multiple pages.
            buf=[]; count=0; block=0
            def flush():
                nonlocal buf,count,block
                if buf:
                    block+=1; body='\n'.join(buf)
                    chunks.append({**base,'id':f'{company}-p{n:03d}-b{block}','kind':'layout_text','text':body,'search_text':normalize(body)})
                buf=[]; count=0
            for line in lines:
                if count+len(line)>1600: flush()
                buf.append(line); count+=len(line)
            flush(); chunks.extend(structured)
            pages.append({**base,'text':raw,'table_count':len(structured),'low_text':len(plain)<60})
            page.close()
    write_json(ROOT/'data/pages'/f'{company}.json',pages)
    write_json(ROOT/'data/tables'/f'{company}.json',tables)
    return {'company':company,'file':path.name,'sha256':hashlib.sha256(path.read_bytes()).hexdigest(),'pages':len(pages),'chunks':len(chunks),'tables':len(tables),'low_text_pages':[p['pdf_page'] for p in pages if p['low_text']],'source_url':None,'source_status':'用户提供；待确认原始下载链接','extraction_warning':'无边框表格仅保留等宽布局；乱码标题及复杂跨页表需回原页核对'}, chunks

if __name__=='__main__':
    a=argparse.ArgumentParser(); a.add_argument('--reports',default=str(ROOT.parent/'银行2026半年报')); a.add_argument('--workers',type=int,default=3); args=a.parse_args()
    files=sorted(Path(args.reports).glob('*.pdf')); (ROOT/'data').mkdir(exist_ok=True)
    manifest=[]; all_chunks=[]
    with concurrent.futures.ProcessPoolExecutor(max_workers=args.workers) as pool:
        for meta,chunks in pool.map(extract_one,files):
            manifest.append(meta); all_chunks.extend(chunks); print(meta['company'],meta['pages'],meta['chunks'],flush=True)
    write_json(ROOT/'data/manifest.json',manifest)
    with (ROOT/'data/chunks.jsonl').open('w',encoding='utf-8') as out:
        import json
        for c in all_chunks: out.write(json.dumps(c,ensure_ascii=False)+'\n')
    print('DONE',len(manifest),len(all_chunks),flush=True)
