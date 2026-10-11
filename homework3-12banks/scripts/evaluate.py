"""Record frozen retrieval, answer, channel ablation. Gold is NEVER supplied to the model."""
import sys,json,time,datetime
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
from common import ROOT,read_json,write_json,configured
from retrieval import Retriever
from qa import answer,SYSTEM
if not configured(): raise SystemExit('请先配置 .env；不把检索摘录计入答案评测。')
r=Retriever(); questions=read_json(ROOT/'evaluation/questions.json'); results=[]
old={x['id']:x for x in read_json(ROOT/'evaluation/results.json')} if (ROOT/'evaluation/results.json').exists() else {}
for q in questions:
    if q['id'] in old and old[q['id']].get('mode')=='deepseek': results.append(old[q['id']]); continue
    evidence=r.retrieve(q['question'],q.get('companies'),q.get('panorama',False))
    item={**q,'evidence':evidence,'method':'hybrid','candidate_company_count':len(set(c['company'] for c in evidence)),'target_company_count':len(q.get('companies') or r.companies) if q.get('panorama') else len(q.get('companies',[])),'timestamp':datetime.datetime.now(datetime.timezone.utc).isoformat(),'ablations':{m:[{'id':c['id'],'company':c['company'],'pdf_page':c['pdf_page'],'score':c['score']} for c in r.retrieve(q['question'],q.get('companies'),q.get('panorama',False),m)] for m in ['vector','bm25']}}
    try: item.update(answer(q['question'],evidence))
    except Exception as e: item.update({'mode':'api_error','answer':'API 请求失败','error_type':type(e).__name__})
    results.append(item); write_json(ROOT/'evaluation/results.json',results); print(q['id'],item['mode'],flush=True)
write_json(ROOT/'evaluation/run_config.json',{'prompt':SYSTEM,'temperature':0,'top_k_local_pages':4,'top_k_per_company_pages':3,'vector':'local LSA 192d','bm25':'jieba + BM25Okapi','fusion':'RRF(k=60), channel candidates=40','routing':'指标别名聚焦、指标命中加权、子组合降权、完整原页读取','gold_exposed_to_model':False,'source':'full source PDFs, extraction before question definition','note':'首轮失败后在同10题复测，属于开发集修复对照，不是独立测试集；gold数值/页号不进入路由；实际 token usage 和模型名逐题保存'})
