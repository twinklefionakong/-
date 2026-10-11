"""Local-only HTTP UI. No key or environment value is returned to the browser."""
import sys,json,os,threading,urllib.parse
from pathlib import Path
from http.server import ThreadingHTTPServer,BaseHTTPRequestHandler
sys.path.insert(0,str(Path(__file__).resolve().parent/'src'))
from common import ROOT,read_json,configured,write_json
from retrieval import Retriever
from qa import answer
retriever=None
class Handler(BaseHTTPRequestHandler):
    def log_message(self,*args): pass
    def send(self,obj,status=200):
        b=json.dumps(obj,ensure_ascii=False).encode(); self.send_response(status); self.send_header('Content-Type','application/json; charset=utf-8'); self.send_header('Content-Length',str(len(b))); self.end_headers(); self.wfile.write(b)
    def do_GET(self):
        path=urllib.parse.urlparse(self.path).path
        if path=='/api/status':
            summary=read_json(ROOT/'evaluation/summary.json') if (ROOT/'evaluation/summary.json').exists() else None
            return self.send({'companies':retriever.companies,'chunks':len(retriever.chunks),'configured':configured(),'summary':summary})
        if path=='/api/evaluations':
            return self.send(read_json(ROOT/'evaluation/results.json') if (ROOT/'evaluation/results.json').exists() else [])
        if path.startswith('/api/chunk/'):
            c=retriever.by_id.get(urllib.parse.unquote(path.rsplit('/',1)[1])); return self.send(c or {},200 if c else 404)
        if path.startswith('/report/'):
            name=urllib.parse.unquote(path.rsplit('/',1)[1]); folder=Path(os.getenv('REPORTS_DIR',str(ROOT/'reports' if (ROOT/'reports').exists() else ROOT.parent/'银行2026半年报'))); source=folder/name
            if Path(name).name!=name or not source.is_file(): return self.send({'error':'报告不可用'},404)
            b=source.read_bytes(); self.send_response(200); self.send_header('Content-Type','application/pdf'); self.send_header('Content-Length',str(len(b))); self.end_headers(); return self.wfile.write(b)
        target=ROOT/'web'/('index.html' if path=='/' else path.lstrip('/'))
        if not target.resolve().is_relative_to((ROOT/'web').resolve()) or not target.is_file(): return self.send({'error':'not found'},404)
        b=target.read_bytes(); self.send_response(200); self.send_header('Content-Type','text/html; charset=utf-8' if target.suffix=='.html' else 'text/plain'); self.send_header('Content-Length',str(len(b))); self.end_headers(); self.wfile.write(b)
    def do_POST(self):
        if self.path!='/api/ask': return self.send({'error':'not found'},404)
        try:
            length=int(self.headers.get('Content-Length',0))
            if length>20000: return self.send({'error':'问题过长'},400)
            body=json.loads(self.rfile.read(length)); q=body['question'].strip()
            if not q or len(q)>1500: return self.send({'error':'请输入不超过1500字的问题'},400)
            method=body.get('method','hybrid'); panorama=bool(body.get('panorama')) or any(t in q for t in ['12家','十二家','所有银行','各家银行','全景'])
            evidence=retriever.retrieve(q,panorama=panorama,method=method); result=answer(q,evidence)
            result.update({'question':q,'method':method,'panorama':panorama,'evidence':evidence,'candidate_company_count':len(set(c['company'] for c in evidence)),'target_company_count':len(retriever.companies) if panorama else len(set(c['company'] for c in evidence))})
            return self.send(result)
        except Exception as e:
            # Never expose request headers, credentials, or API response bodies.
            return self.send({'error':'问答请求失败：'+type(e).__name__+'。请检查 API 余额、网络或模型配置。'},502)
if __name__=='__main__':
    retriever=Retriever(); print('http://127.0.0.1:8765',flush=True)
    ThreadingHTTPServer(('127.0.0.1',8765),Handler).serve_forever()
