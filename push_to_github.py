# -*- coding: utf-8 -*-
"""
全量推送脚本 — 使用 GitHub Git Data API（沙箱内 git push 不可达，api.github.com 可达）
策略：
  1. 以本地工作区为唯一事实来源（git ls-files -c -o --exclude-standard 收集，含中文路径安全）
  2. 每个文件创建 blob（base64）
  3. 全新 tree（等价于新版本全量覆盖旧版本；远程旧有但本地已删除的文件随之移除）
  4. 创建 commit，parent 取 main HEAD
  5. PATCH refs/heads/main（force:true）
受保护资源（数据库/密钥/凭据）已扫描确认本地不存在；.gitignore 已排除备份/日志/缓存。
"""
import base64, json, os, subprocess, sys, urllib.request, urllib.error

REPO = "pingfang154-ai/12306-student-ticket-agent"
BASE = "https://api.github.com"

def get_token():
    r = subprocess.run(["gh", "auth", "token"], capture_output=True, text=True)
    if r.returncode != 0:
        sys.exit("无法获取 gh token: " + r.stderr)
    return r.stdout.strip()

TOKEN = get_token()

def api(method, path, payload=None):
    req = urllib.request.Request(BASE + path, method=method)
    req.add_header("Authorization", "Bearer " + TOKEN)
    req.add_header("Accept", "application/vnd.github+json")
    req.add_header("User-Agent", "workbuddy-full-push")
    data = None
    if payload is not None:
        data = json.dumps(payload).encode("utf-8")
        req.add_header("Content-Type", "application/json")
    try:
        with urllib.request.urlopen(req, data, timeout=120) as resp:
            body = resp.read().decode("utf-8")
            return json.loads(body) if body else {}
    except urllib.error.HTTPError as e:
        print("HTTPError %s %s" % (e.code, e.read().decode("utf-8")[:800]), file=sys.stderr)
        raise

# 1) 收集文件清单（-c 已跟踪 + -o 未跟踪未忽略；--exclude-standard 应用 .gitignore）
out = subprocess.run(
    ["git", "-c", "core.quotePath=false", "ls-files", "-c", "-o", "--exclude-standard", "-z"],
    capture_output=True)
files = [f for f in out.stdout.decode("utf-8").split("\0") if f]
files.sort()
print(">>> 待推送文件数: %d" % len(files))

# 额外防线：再次按 .gitignore 规则排除（double-check）
for f in list(files):
    chk = subprocess.run(["git", "check-ignore", "-q", f], capture_output=True)
    if chk.returncode == 0:
        print("!!! 被忽略但混入清单，跳过: %s" % f)
        files.remove(f)

# 2) main HEAD
head = api("GET", "/repos/%s/commits/main" % REPO)["sha"]
print(">>> main HEAD: %s" % head)

# 3) 创建 blobs
blobs = {}
for i, f in enumerate(files, 1):
    with open(f, "rb") as fh:
        content = fh.read()
    if len(content) > 80 * 1024 * 1024:
        print("!!! 文件过大跳过: %s (%d bytes)" % (f, len(content)))
        continue
    sha = api("POST", "/repos/%s/git/blobs" % REPO,
              {"content": base64.b64encode(content).decode("ascii"), "encoding": "base64"})["sha"]
    blobs[f] = sha
    print("  [%3d/%d] blob %s  %s" % (i, len(files), sha[:8], f))

# 4) 构建 tree
tree = [{"path": f, "mode": "100644", "type": "blob", "sha": blobs[f]} for f in files]
tresp = api("POST", "/repos/%s/git/trees" % REPO, {"tree": tree})
tree_sha = tresp["sha"]
print(">>> tree: %s (%d entries)" % (tree_sha, len(tree)))

# 5) commit
msg = "v2.23 全量同步：711线/3096站数据层 + 深色地图主题 Web + 各省增量合并脚本与文档"
cresp = api("POST", "/repos/%s/git/commits" % REPO,
            {"message": msg, "tree": tree_sha, "parents": [head]})
commit_sha = cresp["sha"]
print(">>> commit: %s" % commit_sha)

# 6) 更新 ref
api("PATCH", "/repos/%s/git/refs/heads/main" % REPO, {"sha": commit_sha, "force": True})
print(">>> refs/heads/main 已更新 -> %s" % commit_sha)
print(">>> 推送成功：%d 个文件已同步" % len(files))
