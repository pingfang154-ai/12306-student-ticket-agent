# -*- coding: utf-8 -*-
import urllib.parse, urllib.request

BASE = "http://127.0.0.1:8091"

cases = [
    ("新疆案例", {"school": "新疆乌鲁木齐市", "home": "新疆巴州", "dep": "乌鲁木齐站", "arr": "库尔勒站"}),
    ("青藏案例(v2.19更正)", {"school": "拉萨市", "home": "林芝市", "dep": "拉萨站", "arr": "林芝站"}),
    ("首页", None),
]

for name, params in cases:
    if params is None:
        url = BASE + "/"
    else:
        url = BASE + "/check?" + urllib.parse.urlencode(params)
    try:
        req = urllib.request.Request(url)
        with urllib.request.urlopen(req, timeout=15) as r:
            body = r.read().decode("utf-8", "replace")
            code = r.getcode()
    except Exception as e:
        print(f"[{name}] ERROR {e}")
        continue
    # 抽取关键判定词
    kw = []
    for k in ("合规", "不符合", "无法解析", "山南市", "林芝市", "库尔勒", "岗嘎站", "乌鲁木齐"):
        if k in body:
            kw.append(k)
    print(f"[{name}] HTTP {code} | len={len(body)} | 命中关键词: {kw}")
    # 打印含有判定结论的一行（粗略）
    for line in body.splitlines():
        if "合规" in line or "不符合" in line or "无法解析" in line:
            print("    结论片段:", line.strip()[:160])
            break
