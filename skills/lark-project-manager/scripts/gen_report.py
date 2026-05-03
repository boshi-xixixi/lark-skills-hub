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
    p=argparse.ArgumentParser()
    p.add_argument("--config",required=True)
    p.add_argument("--mode",choices=["daily","weekly"],default="weekly")
    p.add_argument("--output",default=None)
    args=p.parse_args()
    with open(args.config) as f: cfg=json.load(f)
    name=cfg.get("name","Project"); at=cfg.get("base_app_token",""); tid=cfg.get("base_table_id","")
    if not at or not tid:
        print("[report] No base config",file=sys.stderr); sys.exit(1)
    r=run("lark-cli base records list --app-token %s --table-id %s --as user --format json --page-all"%(at,tid))
    items=(r.get("data",{}).get("items",[])or[])if r and r.get("ok")else[]
    groups={}
    for it in items:
        fd=it.get("fields",{}); s=str(fd.get("status","unknown"))
        groups.setdefault(s,[]).append(fd.get("task_name",fd.get("任务名称","-")))
    total=len(items)
    done=len(groups.get("done",[]))+len(groups.get("已完成",[]))+len(groups.get("Done",[]))
    rate=int(done/max(total,1)*100)
    lbl="Weekly" if args.mode=="weekly" else "Daily"
    rpt="""# Report [%s] - %s

> Generated: %s

## Overview
| Metric | Value |
|--------|-------|
| Total | %d |
| Done | %d (%d%%) |
| Active | %d |

## Completed (%d)
%s

## In Progress
%s
"""%(lbl,name,datetime.now().strftime("%Y-%m-%d %H:%M"),total,done,rate,total-done,done,
"\n".join("- %s"%t for t in groups.get("done",[])[:10]),
"\n".join("- %s"%t for t in groups.get("doing",groups.get("进行中",[]))[:10]))
    out=args.output or "report_%s_%s.md"%(name.replace(" ","_"),args.mode)
    with open(out,"w") as f: f.write(rpt)
    print("[report] Saved: %s"%out,file=sys.stderr)

if __name__=="__main__": main()
