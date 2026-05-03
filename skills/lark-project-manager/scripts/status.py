#!/usr/bin/env python3
import argparse, json, subprocess, sys
from datetime import datetime

def run(cmd):
    r = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=30)
    if r.returncode != 0: return None
    try: return json.loads(r.stdout)
    except: return None

def main():
    p = argparse.ArgumentParser(); p.add_argument("--config", required=True)
    p.add_argument("--format", choices=["text","json"], default="text"); args = p.parse_args()
    with open(args.config) as f: cfg = json.load(f)
    at = cfg.get("base_app_token",""); tid = cfg.get("base_table_id","")
    name = cfg.get("name","Project")
    if not at or not tid:
        print("[status] Missing base config in %s" % args.config, file=sys.stderr); sys.exit(1)
    r = run("lark-cli base records list --app-token %s --table-id %s --as user --format json --page-all" % (at,tid))
    items = (r.get("data",{}).get("items",[]) or []) if r and r.get("ok") else []
    smap = {}; overdue = []
    for it in items:
        fd = it.get("fields",{})
        s = str(fd.get("status","")); smap[s] = smap.get(s,0)+1
        due = fd.get("due_date","") or fd.get("截止日期","")
        if due and s not in ("done","已完成"):
            try:
                if datetime.strptime(str(due)[:10],"%Y-%m-%d") < datetime.now():
                    overdue.append(fd.get("task_name",fd.get("任务名称","?")))
            except: pass
    total=len(items); done=smap.get("done",0)+smap.get("已完成",0)+smap.get("Done",0)
    rate=int(done/max(total,1)*100)
    if args.format=="json":
        print(json.dumps({"project":name,"total":total,"completed":done,"rate":rate,"breakdown":smap,"overdue":overdue},indent=2))
    else:
        bar="#"*(rate//5)+"-"*(20-rate//5)
        print("\n[%s] %d%% (%d/%d)"%(bar,rate,done,total))
        print("Status: %s"%json.dumps(smap,ensure_ascii=False))
        if overdue: print("OVERDUE: %s"%overdue)

if __name__=="__main__": main()
