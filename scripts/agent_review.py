import json, time, urllib.request
from pathlib import Path

PENDING = "/ai-agent/training/dataset/pending_review.jsonl"
REVIEWED = "/ai-agent/training/dataset/agent_reviewed.jsonl"
LOG = "/ai-agent/logs/agent_review.log"
URL = "http://192.168.0.198:11434/api/generate"
MODEL = "qwen3.5:9b-q4_K_M"

def ask(prompt):
    try:
        data = json.dumps({"model":MODEL,"prompt":prompt,"stream":False,"options":{"temperature":0,"num_predict":2000}}).encode()
        req = urllib.request.Request(URL, data=data, headers={"Content-Type":"application/json"})
        with urllib.request.urlopen(req, timeout=120) as r:
            return json.loads(r.read()).get("response","").strip()
    except Exception as e:
        print(f"  err: {e}")
        return None

lines = open(PENDING, encoding="utf-8").read().strip().split("\n")
print(f"开始审核 {len(lines)} 条")
ok=bad=fail=n=0
for line in lines:
    n+=1
    s = json.loads(line)
    inst = s["instruction"][:150].replace("\n"," ")
    outp = s["output"][:150].replace("\n"," ")
    score = s["score"]
    r = ask(f"回答[通过]或[拒绝]：此对话是否有技术价值、非闲聊？指令:{inst} 输出:{outp} 评分:{score}")
    if not r:
        fail+=1; print(f"[{n}/{len(lines)}] x"); continue
    approved = "通过" in r
    s["agent_decision"]="approved" if approved else "rejected"
    s["agent_reason"]=r[:50].replace("\n"," ")
    s["agent_review_time"]=time.strftime("%Y-%m-%dT%H:%M:%SZ",time.gmtime())
    open(REVIEWED,"a",encoding="utf-8").write(json.dumps(s,ensure_ascii=False)+"\n")
    if approved: ok+=1
    else: bad+=1
    reason = s["agent_reason"][:25]
    symbol = "ok" if approved else "x"
    print(f"[{n}/{len(lines)}] {symbol} | {reason}")
    if n%10==0:
        Path(LOG).parent.mkdir(parents=True,exist_ok=True)
        ts = time.strftime("%Y-%m-%dT%H:%M:%SZ",time.gmtime())
        open(LOG,"a").write(f"[{ts}] {n}/{len(lines)} ok={ok} bad={bad} fail={fail}\n")
        print(f"  进度: {n/len(lines)*100:.1f}%")
    time.sleep(1)
print(f"完成: 通过{ok} 拒绝{bad} 失败{fail}")