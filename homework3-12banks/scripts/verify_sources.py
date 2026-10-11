"""Verify discovered official attachments against the exact supplied files, without overwriting."""
import sys,hashlib,urllib.request,concurrent.futures,re,urllib.parse,json
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
from common import ROOT,read_json,write_json
manifest=read_json(ROOT/'data/manifest.json'); candidates=read_json(ROOT/'data/download_candidates.json')
def check(item):
    try:
        req=urllib.request.Request(item['source_url'],headers={'User-Agent':'Mozilla/5.0'})
        with urllib.request.urlopen(req,timeout=60) as r: content=r.read()
        return item,{**item,'sha256':hashlib.sha256(content).hexdigest(),'is_pdf':content.startswith(b'%PDF')}
    except Exception as e:return item,{**item,'error_type':type(e).__name__}
receipts=[]
with concurrent.futures.ThreadPoolExecutor(max_workers=3) as pool:
    for item,receipt in pool.map(check,candidates):
        m=next(x for x in manifest if x['company']==item['company']); receipt['matches_input']=receipt.get('sha256')==m['sha256'];receipts.append(receipt)
        if receipt['matches_input']:m.update({'source_url':item['source_url'],'source_status':'巨潮官方附件下载SHA256与输入一致：已核验'})
        else:m.update({'candidate_source_url':item['source_url'],'source_status':'用户声明巨潮来源；候选附件与输入不一致/未下载成功，未认作本文件来源'})
        print(item['company'],receipt['matches_input'],flush=True)
write_json(ROOT/'data/source_verification.json',receipts);write_json(ROOT/'data/manifest.json',manifest)
