"""Evidence integrity and submission checks, not a self-fulfilling accuracy test."""
import sys,json,re,hashlib
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
from common import ROOT,read_json
from retrieval import Retriever
r=Retriever(); results=read_json(ROOT/'evaluation/results.json'); assert len(results)==10
for row in results:
    assert row['mode']=='deepseek' and row['citation_valid']
    allowed={c['id'] for c in row['evidence']}
    assert set(row['cited_ids']).issubset(allowed)
    for c in row['evidence']:
        assert r.by_id[c['id']]['text']==c['text'],(row['id'],c['id'])
        assert c['company'] in r.companies and c['pdf_page']>=1
    if row.get('panorama'):assert {c['company'] for c in row['evidence']}==set(r.companies)
manifest=read_json(ROOT/'data/manifest.json');assert len(manifest)==12
for m in manifest:
    p=ROOT.parent/'银行2026半年报'/m['file']
    assert hashlib.sha256(p.read_bytes()).hexdigest()==m['sha256']
print('PASS: 10真实答案、引用白名单、原页证据一致性、全景候选12家、12份输入SHA256。')
print('以上不证明事实正确；独立判分见 evaluation/report.md 和 gold.json。')
