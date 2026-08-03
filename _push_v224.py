# -*- coding: utf-8 -*-
"""
增量推送 v2.24 到 GitHub main — 使用 Git Data API（沙箱 git push 不可达）
方案：以本地工作区文件树 + 远程 main HEAD(parent) 创建新 commit，正常推进 main。
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
    req.add_header("User-Agent", "workbuddy-sync-v224")
    data = None
    if payload is not None:
        data = json.dumps(payload).encode("utf-8")
        req.add_header("Content-Type", "application/json")
    try:
        with urllib.request.urlopen(req, data, timeout=120) as resp:
            body = resp.read().decode("utf-8")
            return json.loads(body) if body else {}
    except urllib.error.HTTPError as e:
        err = e.read().decode("utf-8", "ignore")[:800]
        print("HTTPError %s %s" % (e.code, err), file=sys.stderr)
        raise

print(">>> 1) 收集文件清单（已跟踪 + 未忽略未跟踪）")
out = subprocess.run(
    ["git", "-c", "core.quotePath=false", "ls-files", "-c", "-o", "--exclude-standard", "-z"],
    capture_output=True)
files = [f for f in out.stdout.decode("utf-8").split("\0") if f]
files.sort()
# 二次防线：check-ignore
for f in list(files):
    chk = subprocess.run(["git", "check-ignore", "-q", f], capture_output=True)
    if chk.returncode == 0:
        files.remove(f)
print(">>> 待推送文件数: %d" % len(files))

print(">>> 2) 远程 main HEAD")
head = api("GET", "/repos/%s/commits/main" % REPO)["sha"]
print(">>> parent: %s" % head)

print(">>> 3) 创建 blobs")
blobs = {}
for i, f in enumerate(files, 1):
    with open(f, "rb") as fh:
        content = fh.read()
    if len(content) > 80 * 1024 * 1024:
        print("!!! 跳过超大文件: %s (%d bytes)" % (f, len(content)))
        continue
    sha = api("POST", "/repos/%s/git/blobs" % REPO,
              {"content": base64.b64encode(content).decode("ascii"), "encoding": "base64"})["sha"]
    blobs[f] = sha
    if i % 10 == 0 or i == len(files):
        print("  [%3d/%d]" % (i, len(files)))

print(">>> 4) 构建 tree")
tree = [{"path": f, "mode": "100644", "type": "blob", "sha": blobs[f]} for f in files]
tresp = api("POST", "/repos/%s/git/trees" % REPO, {"tree": tree})
tree_sha = tresp["sha"]
print(">>> tree: %s (%d entries)" % (tree_sha, len(tree)))

print(">>> 5) 创建 commit")
msg = "v2.24 功能增强：AI辅助判定+12306实时数据集成+中转三层优化\n\n核心变更：\n- AI 辅助判定修缮：API Key sessionStorage 持久化（刷新不断链）、判定强制联网、\n  合规/不合规分支（三选深度查询 / 自动改家追问并截取）\n- 接入 12306 skill：/api/train_info 查询真实车次/时刻/余票/公布票价，AI 深度查询基于官方数据\n- 直达/中转查询：/api/direct_route 三层逻辑（路径最短/时间最短/价格最优三类推荐\n  + 学生票合规审核 + 本地兜底），15 天日期选择\n- 前端：规则提示文案与样式微调、候选栏 z-index 修复、中转合规徽章与票价明细\n\n数据层：铁路数据增量（各省合并脚本与文档）\n备注：移除曾临时接入的数据看板功能，回归本地化学生票判断系统"
cresp = api("POST", "/repos/%s/git/commits" % REPO,
            {"message": msg, "tree": tree_sha, "parents": [head]})
commit_sha = cresp["sha"]
print(">>> commit: %s" % commit_sha)

print(">>> 6) 更新 refs/heads/main")
api("PATCH", "/repos/%s/git/refs/heads/main" % REPO, {"sha": commit_sha, "force": False})
print(">>> 推送成功：main -> %s （%d 个文件）" % (commit_sha, len(files)))
