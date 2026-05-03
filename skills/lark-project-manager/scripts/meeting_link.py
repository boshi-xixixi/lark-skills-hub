#!/usr/bin/env python3
import argparse, json, os, subprocess, sys
from datetime import datetime
try:
    from dotenv import load_dotenv
    _sd=os.path.dirname(os.path.abspath(__file__))
    _env=os.path.join(os.path.dirname(_sd),".env")
    if os.path.exists(_env): load_dotenv(_env)
except: pass

def run(cmd):
    r=subprocess.run(cmd,shell=True,capture_output=True,text=True,timeout=30)
    if r.returncode!=0: return None
    try: return json.loads(r.stdout)
    except: return None

def main():
    p=argparse.ArgumentParser(description="Link meeting to project")
    p.add_argument("--project-doc",required=True)
    p.add_argument("--minute-token",default=None)
    p.add_argument("--dry-run",action="store_true")
    args=p.parse_args()
    content=""; title="Meeting"
    if args.minute_token:
        r=run("lark-cli lark-minutes get --token %s --as user --format json"%args.minute_token)
        if r and r.get("ok"):
            d=r.get("data",{}); title=d.get("title",title)
            content=d.get("summary","") or d.get("object_content","") or ""
    if not content:
        print("[meeting-link] No content",file=sys.stderr); return
    append="\n\n---\n## Meeting: %s\n> Linked: %s\n\n%s"%(title,datetime.now().strftime("%Y-%m-%d %H:%M"),content[:2000])
    if args.dry_run:
        print("[DRY RUN]\n%s"%append[:300])
    else:
        esc=append.replace("'","'\\''").replace('"','\\"')
        r=run('lark-cli docs +update --doc %s --markdown \'%s\' --mode append --as user'%(args.project_doc,esc))
        if r and r.get("ok"): print("[meeting-link] OK",file=sys.stderr)
        else: print("[meeting-link] FAILED",file=sys.stderr)

if __name__=="__main__": main()
