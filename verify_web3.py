# -*- coding: utf-8 -*-
import urllib.parse, urllib.request, re

BASE = "http://127.0.0.1:8091"
cases = [
    ("新疆案例", {"school": "新疆乌鲁木齐市", "home": "新疆巴州", "dep": "乌鲁木齐站", "arr": "库尔勒站"}),
    ("青藏案例(v2.19更正)", {"school": "拉萨市", "home": "林芝市", "dep": "拉萨站", "arr": "林芝站"}),
    ("反向/同城正向(北京)", {"school": "北京市", "home": "成都市", "dep": "北京西", "arr": "成都东"}),
]
for name, params in cases:
    url = BASE + "/check?" + urllib.parse.urlencode(params)
    with urllib.request.urlopen(url, timeout=15) as r:
        body = r.read().decode("utf-8", "replace")
    text = re.sub(r"<[^>]+>", " ", body)
    text = re.sub(r"\s+", " ", text).strip()
    m = re.search(r"(符合优惠区间|不符合优惠区间|无法解析|未找到)", text)
    verdict = m.group(0) if m else "(未定位)"
    idx = text.find(verdict) if m else -1
    snippet = text[max(0, idx-30): idx+150] if idx >= 0 else text[:200]
    print(f"=== {name} ===")
    print("判定:", verdict)
    print("上下文:", snippet)
    print()
