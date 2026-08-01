# -*- coding: utf-8 -*-
"""v2.23 内蒙古批连通性 + 端到端核查"""
import importlib.util, os, sys

BASE = r"C:\Users\cjp15\Desktop\全国客运站点\交接文件夹第三版（含一、二合并）\src"
sys.path.insert(0, BASE)
spec = importlib.util.spec_from_file_location("rd", os.path.join(BASE, "railway_data.py"))
R = importlib.util.module_from_spec(spec)
spec.loader.exec_module(R)
from student_ticket_checker import _dijkstra, check_compliance

print("===== 1) 新站 BFS（→北京/上海/广州/哈尔滨/呼和浩特/沈阳）=====")
hubs = ["北京站", "上海虹桥站", "广州站", "哈尔滨站", "呼和浩特站", "沈阳站"]
samples = ["赛汗塔拉站", "满归站", "莫尔道嘎站", "阿里河站", "伊敏站", "塔尔气站", "白云鄂博站",
           "额济纳站", "乌审旗站", "霍林河站", "阿尔山站", "阿尔山北站", "库伦站", "开鲁站",
           "苏尼特左旗站", "锡林浩特站", "奈曼站", "天义站", "大板站", "呼和浩特站", "包头东站",
           "乌海西站", "乌拉山西站", "集宁南站", "东来站", "乌丹站", "根河站", "满归站"]
for s in samples:
    sa = R.resolve_location(s)
    if not sa:
        print(f"  {s}: 解析空!"); continue
    start = min(sa)
    reach = {}
    for h in hubs:
        hb = R.resolve_location(h)
        if hb:
            reach[h] = _dijkstra(start, min(hb)) is not None
    bad = [h for h, v in reach.items() if not v]
    print(f"  {s}: {'OK' if not bad else 'FAIL ' + str(bad)}")

print("\n===== 2) 端到端 =====")
cases = [
    ("北京市", "呼和浩特市", "北京站", "呼和浩特站", "硬座"),      # 京包铁路
    ("北京市", "包头市", "北京站", "包头东站", "硬座"),           # 京包
    ("北京市", "呼和浩特市", "北京北站", "呼和浩特东站", "二等座"), # 京张+京包客专
    ("呼和浩特市", "鄂尔多斯市", "呼和浩特站", "鄂尔多斯站", "硬座"), # 呼准鄂+包西
    ("呼和浩特市", "集宁市", "呼和浩特站", "集宁南站", "硬座"),    # 京包
    ("北京市", "通辽市", "北京站", "通辽站", "硬座"),             # 京通铁路
    ("北京市", "赤峰市", "北京站", "赤峰站", "硬座"),             # 京通+喀赤
    ("通辽市", "霍林郭勒市", "通辽站", "霍林河站", "硬座"),        # 通霍铁路
    ("通辽市", "乌兰浩特市", "通辽站", "乌兰浩特站", "硬座"),      # 通霍+白阿/锡乌
    ("白城市", "阿尔山市", "白城站", "阿尔山站", "硬座"),          # 白阿铁路
    ("长春市", "乌兰浩特市", "长春站", "乌兰浩特站", "二等座"),    # 长白铁路
    ("呼和浩特市", "锡林浩特市", "呼和浩特站", "锡林浩特站", "硬座"), # 京包+集通+锡多
    ("北京市", "满归市", "北京站", "满归站", "硬座"),             # 滨洲+牙林
    ("哈尔滨市", "满洲里市", "哈尔滨站", "满洲里站", "硬座"),      # 滨洲全线
    ("哈尔滨市", "莫尔道嘎市", "哈尔滨站", "莫尔道嘎站", "硬座"),   # 滨洲+朝乌
    ("北京市", "额济纳旗", "北京站", "额济纳站", "硬座"),          # 包兰+临哈
    ("银川市", "包头市", "银川站", "包头站", "硬座"),             # 包兰
    ("乌兰察布市", "二连浩特市", "乌兰察布站", "赛汗塔拉站", "硬座"), # 京包+集二
]
pass_n = 0
for school, home, dep, arr, seat in cases:
    try:
        r = check_compliance(school_city=school, home_city=home, dep_station=dep,
                             arr_station=arr, seat=seat)
        ok = r.get("ok") if isinstance(r, dict) else False
        reason = (r.get("reason") or "")[:52] if isinstance(r, dict) else ""
        print(f"  {'PASS' if ok else 'FAIL'} {school}→{home} | {dep}→{arr}: {reason}")
        pass_n += 1 if ok else 0
    except Exception as e:
        print(f"  EXC {school}→{home} | {dep}→{arr}: {type(e).__name__}: {e}")
print("PASS:", pass_n, "/", len(cases))

print("\n===== 3) lines-MISS 差分 =====")
from importlib.machinery import SourceFileLoader
RB = SourceFileLoader("rb", os.path.join(BASE, "railway_data_v2.22.bak")).load_module()
miss_new = []
for line, seq in R.LINE_ORDER.items():
    if line in RB.LINE_ORDER and RB.LINE_ORDER[line] == seq:
        continue
    for s in seq:
        lines = R.STATION_INFO.get(s, {}).get("lines", [])
        if line not in lines:
            miss_new.append((line, s))
print(f"本批新增/变更线路 MISS: {miss_new if miss_new else '0'}")
