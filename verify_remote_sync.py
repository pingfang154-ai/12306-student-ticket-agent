# -*- coding: utf-8 -*-
"""全量校验：本地文件 vs 远程 main tree，逐文件字节级比对"""
import json, subprocess, hashlib

r = subprocess.run(
    ["gh", "api", "repos/pingfang154-ai/12306-student-ticket-agent/git/trees/main?recursive=1",
     "--jq", '.tree[]|select(.type=="blob")|{path,sha}'],
    capture_output=True, text=True)
remote = {}
for line in r.stdout.strip().splitlines():
    d = json.loads(line)
    remote[d["path"]] = d["sha"]

out = subprocess.run(
    ["git", "-c", "core.quotePath=false", "ls-files", "-c", "-o", "--exclude-standard", "-z"],
    capture_output=True)
files = [f for f in out.stdout.decode("utf-8").split("\0") if f]

mismatch, missing_remote = [], []
for f in files:
    if f not in remote:
        missing_remote.append(f)
        continue
    data = open(f, "rb").read()
    lsha = hashlib.sha1(b"blob %d\x00" % len(data) + data).hexdigest()
    if lsha != remote[f]:
        mismatch.append((f, remote[f][:8], lsha[:8]))

extra_remote = [p for p in remote if p not in files]

print("本地文件数:", len(files))
print("远程 blob 数:", len(remote))
print("内容一致:", len(files) - len(mismatch) - len(missing_remote), "个")
print("内容不一致:", mismatch if mismatch else "无")
print("本地存在但远程缺失:", missing_remote if missing_remote else "无")
print("远程独有(新版本已移除):", extra_remote if extra_remote else "无")
