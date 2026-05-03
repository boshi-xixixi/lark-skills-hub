#!/usr/bin/env python3
import argparse, json, subprocess, sys

def run(cmd):
    r = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=30)
    if r.returncode != 0:
        print("[error] %s" % r.stderr.strip(), file=sys.stderr)
        return None
    try: return json.loads(r.stdout)
    except: return {"raw": r.stdout}

def main():
    p = argparse.ArgumentParser(); p.add_argument("--name", required=True)
    p.add_argument("--desc", default=""); args = p.parse_args()
    print("[init] Creating project [%s]..." % args.name, file=sys.stderr)
    results = {}
    print("[init] Step 1/3: Folder...", file=sys.stderr)
    r = run('lark-cli drive folder create --name "%s" --as user --format json' % args.name)
    if r and r.get("ok"):
        results["folder_url"] = r.get("data",{}).get("url","")
        print("[init] OK: %s" % results["folder_url"], file=sys.stderr)
    print("[init] Step 2/3: Document...", file=sys.stderr)
    md = "# %s\n\n## Overview\n%s" % (args.name, args.desc or "No description")
    esc = md.replace("'", "'\\''")
    r = run('lark-cli docs +create --title "PROJECT-%s" --markdown \'%s\' --as user --format json' % (args.name, esc))
    if r and r.get("ok"):
        results["doc_url"] = r.get("data",{}).get("url","")
        print("[init] OK: %s" % results["doc_url"], file=sys.stderr)
    cfg = ".project_%s.json" % args.name.replace(" ","_")
    with open(cfg,"w") as f:
        json.dump({"name":args.name,"desc":args.desc,**results}, f, indent=2)
    print("[init] DONE! Config: %s" % cfg, file=sys.stderr)
    print(json.dumps(results, indent=2))

if __name__=="__main__": main()
