import json, os, re
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
_CONVERTER = None
def write_json(path, obj):
    path=Path(path); path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, ensure_ascii=False, indent=2), encoding='utf-8')
def read_json(path): return json.loads(Path(path).read_text(encoding='utf-8'))
def load_env():
    # Never log values. The project .env takes priority over the workspace .env.
    for p in (ROOT/'.env', ROOT.parent/'.env'):
        if p.exists():
            for line in p.read_text(encoding='utf-8-sig').splitlines():
                if '=' in line and not line.lstrip().startswith('#'):
                    k,v=line.split('=',1); os.environ.setdefault(k.strip(),v.strip().strip('"').strip("'"))
            break
def configured():
    load_env(); k=os.getenv('DEEPSEEK_API_KEY','')
    return bool(k) and not any(s in k for s in ('替换','这里','your_key'))
def normalize(text):
    global _CONVERTER
    from opencc import OpenCC
    if _CONVERTER is None: _CONVERTER=OpenCC('t2s')
    return re.sub(r'\s+', ' ', _CONVERTER.convert(text)).strip()
