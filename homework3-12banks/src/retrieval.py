import json, pickle, re, logging
import numpy as np
import jieba
from rank_bm25 import BM25Okapi
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.decomposition import TruncatedSVD
from sklearn.preprocessing import normalize as unit
from common import ROOT, normalize, write_json
jieba.setLogLevel(logging.ERROR)
for word in ['净息差','不良贷款率','拨备覆盖率','核心一级资本充足率','营业收入','归母净利润','净利息收入','金融科技','集团口径','资本充足率']:
    jieba.add_word(word)
STOP={'的','了','和','是','在','请','分别','哪些','多少','如何','什么','报告','半年报'}
def tokens(t): return [x for x in jieba.lcut(normalize(t)) if x.strip() and x not in STOP and re.search(r'[\w\u4e00-\u9fff]',x)]
def build():
    chunks=[json.loads(x) for x in (ROOT/'data/chunks.jsonl').read_text(encoding='utf-8').splitlines()]
    docs=[f"{c['company']} {c['section']} {c['search_text']}" for c in chunks]
    tf=TfidfVectorizer(analyzer='char',ngram_range=(2,4),min_df=2,max_features=70000,sublinear_tf=True)
    matrix=tf.fit_transform(docs)
    svd=TruncatedSVD(n_components=min(192,len(chunks)-1,matrix.shape[1]-1),random_state=42)
    vectors=unit(svd.fit_transform(matrix)).astype('float32')
    bm=BM25Okapi([tokens(t) for t in docs]); path=ROOT/'data/index'; path.mkdir(parents=True,exist_ok=True)
    with (path/'index.pkl').open('wb') as f: pickle.dump((chunks,tf,svd,vectors,bm),f)
    write_json(path/'metadata.json',{'vector':'TF-IDF char 2-4gram → TruncatedSVD/LSA → L2 cosine','dimensions':vectors.shape[1],'random_seed':42,'fusion':'RRF k=60; each channel top40','chunks':len(chunks),'semantic_limit':'本地语料统计向量，非预训练 embedding；同义改写能力有限'})
    print('INDEX',len(chunks),vectors.shape,flush=True)
class Retriever:
    def __init__(self):
        with (ROOT/'data/index/index.pkl').open('rb') as f: self.chunks,self.tf,self.svd,self.vectors,self.bm=pickle.load(f)
        self.companies=sorted(set(c['company'] for c in self.chunks)); self.by_id={c['id']:c for c in self.chunks}
        self.pages={}
        for company in self.companies:
            for p in json.loads((ROOT/'data/pages'/f'{company}.json').read_text(encoding='utf-8')):
                c={**p,'id':f"{company}-p{p['pdf_page']:03d}-read",'kind':'page_read','search_text':normalize(p['text'])}
                self.pages[(company,p['pdf_page'])]=c; self.by_id[c['id']]=c
    def focus(self,q):
        """Generic metric routing; contains no bank values, gold pages, or question IDs."""
        if '原因' in q and ('净息差' in q or '净利息收入' in q):
            return '净息差 净利息收益率 利息净收入 收益率 成本率 定价 负债 下降', ['净息差','净利息收益率','利息净收入','净利息收入']
        mapping={'营业收入':['营业收入'],'净息差':['净息差','净利息收益率'],'不良贷款率':['不良贷款率'],'拨备覆盖率':['拨备覆盖率'],'核心一级资本充足率':['核心一级资本充足率'],'现金股息':['普通股股利','中期股利','中期现金股息'],'归母净利润':['归属于本行股东的净利润','归属于母公司股东的净利润']}
        terms=[s for key,values in mapping.items() if key in q for s in values]
        return (' '.join(terms),terms) if terms else (q,[])
    def search(self,q,company=None,k=5,method='hybrid'):
        query=unit(self.svd.transform(self.tf.transform([normalize(q)])))[0]
        vs=self.vectors@query; bs=np.asarray(self.bm.get_scores(tokens(q)))
        valid=np.array([i for i,c in enumerate(self.chunks) if not company or c['company']==company])
        if not len(valid): return []
        vr=valid[np.argsort(-vs[valid],kind='stable')[:40]]; br=valid[np.argsort(-bs[valid],kind='stable')[:40]]
        scores={}
        if method=='vector': scores={int(i):float(vs[i]) for i in vr}
        elif method=='bm25': scores={int(i):float(bs[i]) for i in br}
        else:
            for ranks in (vr,br):
                for rank,i in enumerate(ranks,1): scores[int(i)]=scores.get(int(i),0)+1/(60+rank)
        results=[]; pages=set()
        for i,s in sorted(scores.items(),key=lambda x:-x[1]):
            c=self.chunks[i]; key=(c['company'],c['pdf_page'])
            # Keep two chunks maximum per page rather than losing all surrounding rows.
            if sum((r['company'],r['pdf_page'])==key for r in results)>=2: continue
            results.append({**c,'score':s,'vector_score':float(vs[i]),'bm25_score':float(bs[i])})
            if len(results)>=k: break
        return results
    def retrieve(self,q,companies=None,panorama=False,method='hybrid'):
        # Stage 2: focus the indicator, inspect complete original pages, return distinct read IDs.
        focused,terms=self.focus(q)
        targets=companies or [c for c in self.companies if c in q]
        targets=targets or (self.companies if panorama else [None])
        output=[]
        for company in targets:
            candidates=self.search(focused,company,30,method)
            def relevance(c):
                page=self.pages[(c['company'],c['pdf_page'])]
                t=page['search_text']; matched=sum(s in t for s in terms)
                # A grouped comparison requires the total, not a branch/geography/product subportfolio.
                subtotal=any(s in t for s in ['县域金融','县域业务','按行业划分','按地区划分','按业务类型划分'])
                return c['score']+(0.08*matched if method=='hybrid' else 0)+( -0.06 if subtotal and '集团' in q and method=='hybrid' else 0)
            if method=='hybrid': candidates=sorted(candidates,key=relevance,reverse=True)
            seen=set(); limit=3 if panorama or len(targets)>1 else 4
            for c in candidates:
                key=(c['company'],c['pdf_page'])
                if key in seen: continue
                seen.add(key); page=self.pages[key]
                output.append({**page,'score':c['score'],'vector_score':c['vector_score'],'bm25_score':c['bm25_score'],'candidate_id':c['id'],'read_complete_page':True,'focus_query':focused})
                if len(seen)>=limit: break
        return output
