"""Discover cninfo half-year full reports and download only explicitly matching titles.
Do not silently substitute a different year or a summary. Website access may change.
"""
import argparse,json,re,sys,time,urllib.request,urllib.parse,hashlib
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
from common import ROOT,write_json,read_json
CODES={'工商银行':'601398','建设银行':'601939','农业银行':'601288','中国银行':'601988','交通银行':'601328','招商银行':'600036','兴业银行':'601166','光大银行':'601818','华夏银行':'600015','北京银行':'601169','厦门银行':'601187','郑州银行':'002936'}
def discover(company,code,year):
    query={'pageNum':1,'pageSize':100,'column':'szse' if code.startswith('0') else 'sse','tabName':'fulltext','stock':'','searchkey':company,'secid':'','plate':'','category':'','trade':'','seDate':f'{year}-07-01~{year}-10-11','sortName':'time','sortType':'desc','isHLtitle':'true'}
    request=urllib.request.Request('https://www.cninfo.com.cn/new/hisAnnouncement/query',data=urllib.parse.urlencode(query).encode(),headers={'User-Agent':'Mozilla/5.0','Referer':'https://www.cninfo.com.cn/','Content-Type':'application/x-www-form-urlencoded'})
    with urllib.request.urlopen(request,timeout=40) as response: data=json.load(response)
    candidates=[]
    for row in data.get('announcements') or []:
        title=re.sub('<[^>]+>','',row['announcementTitle'])
        if row.get('secCode')!=code or str(year) not in title or any(s in title for s in ['摘要','英文','H股','第三支柱']): continue
        if not any(term in title for term in ['半年度报告','半年度報告','中期报告']):continue
        candidates.append({'company':company,'code':code,'title':title,'announcement_id':row['announcementId'],'source_url':'https://static.cninfo.com.cn/'+row['adjunctUrl'].lstrip('/')})
    return candidates
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--year',type=int,default=2026);p.add_argument('--download',action='store_true');p.add_argument('--urls',help='人工核对后的JSON数组：company/source_url/title');p.add_argument('--output',default=str(ROOT/'reports'));a=p.parse_args()
    if a.urls: items=read_json(a.urls)
    else:
        items=[]
        for company,code in CODES.items():
            try:
                rows=discover(company,code,a.year)
                if len(rows)==1:items+=rows
                else:print(company,f'候选{len(rows)}份；请在巨潮核对，不自动选择',flush=True)
            except Exception as e:print(company,'查询失败',type(e).__name__,flush=True)
            time.sleep(0.3)
        write_json(ROOT/'data/download_candidates.json',items)
    if a.download:
        folder=Path(a.output);folder.mkdir(parents=True,exist_ok=True)
        for item in items:
            url=item['source_url']; parsed=urllib.parse.urlparse(url)
            if parsed.scheme!='https' or parsed.hostname!='static.cninfo.com.cn':raise ValueError('只下载巨潮官方HTTPS附件')
            target=folder/f"{item['company']}：{a.year}年半年度报告.pdf"
            if target.exists():print(item['company'],'已存在，跳过');continue
            with urllib.request.urlopen(urllib.request.Request(url,headers={'User-Agent':'Mozilla/5.0'}),timeout=90) as response:content=response.read()
            if not content.startswith(b'%PDF'):raise ValueError('返回内容不是PDF')
            target.write_bytes(content);item['download_sha256']=hashlib.sha256(content).hexdigest();print(item['company'],'已下载',flush=True)
        write_json(ROOT/'data/download_receipts.json',items)
