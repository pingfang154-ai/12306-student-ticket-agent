# -*- coding: utf-8 -*-
"""v2.21 辽宁批连通性核查"""
import importlib.util, os, sys, collections

BASE = r"C:\Users\cjp15\Desktop\全国客运站点\交接文件夹第三版（含一、二合并）\src"
sys.path.insert(0, BASE)
spec = importlib.util.spec_from_file_location("rd", os.path.join(BASE, "railway_data.py"))
R = importlib.util.module_from_spec(spec)
spec.loader.exec_module(R)

from student_ticket_checker import _dijkstra, check_compliance

print("===== 1) 新站 resolve_location =====")
new71 = ["普兰店站","熊岳城站","盖州站","大石桥站","海城站","鞍山站","灯塔站","林盛堡站","苏家屯站",
    "绥中站","兴城站","葫芦岛站","锦州站","沟帮子站","大虎山站","新民站","马三家站","铁岭站","开原站",
    "昌图站","营口站","东戴河站","绥中北站","葫芦岛北站","锦州南站","台安站","辽中站","黑山北站",
    "新民北站","牛河梁站","喀左站","北票站","建平站","铁岭西站","开原西站","昌图西站","西柳站",
    "陈相屯站","石桥子站","南芬站","下马塘站","连山关站","祁家堡站","草河口站","通远堡站","刘家河站",
    "凤凰城站","一面山站","汤山城站","五龙背站","本溪新城站","南芬北站","通远堡西站","凤城东站",
    "五龙背东站","小市站","铁刹山站","大阳站","八里甸子站","五女山站","灌水站","宽甸站","花博山站",
    "义县站","新立屯站","西丰站","八面城站","三江口站","南杂木站","南口前站","清原站"]
bad = [s for s in new71 if not R.resolve_location(s)]
print(f"resolve_location 空: {bad if bad else '无'}")
print(f"已入库: {sum(1 for s in new71 if s in R.STATION_INFO)}/{len(new71)}")

print("\n===== 2) BFS 连通性（新站 → 沈阳站 / 北京站 / 上海虹桥站 / 广州站）=====")
hubs = ["沈阳站", "北京站", "上海虹桥站", "广州站"]
samples = ["普兰店站","苏家屯站","锦州站","铁岭西站","新民北站","喀左站","建平站","五女山站",
           "花博山站","宽甸站","营口站","西柳站","新立屯站","西丰站","三江口站","清原站","义县站"]
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
    print(f"  {s}: " + " ".join(f"{h}={'OK' if v else 'FAIL'}" for h, v in reach.items()))

print("\n===== 3) 端到端 check_compliance =====")
cases = [
    # (school_city, home_city, dep, arr, seat)
    ("沈阳市", "大连市", "沈阳站", "大连站", "二等座"),          # 哈大高铁 直达
    ("沈阳市", "大连市", "苏家屯站", "普兰店站", "硬座"),        # 沈大铁路 直达
    ("沈阳市", "丹东市", "沈阳站", "丹东站", "二等座"),          # 沈丹客专
    ("沈阳市", "丹东市", "凤凰城站", "五龙背站", "硬座"),        # 沈丹铁路
    ("北京市", "大连市", "北京站", "大连站", "二等座"),          # 京哈普速+秦沈+哈大 多线
    ("沈阳市", "葫芦岛市", "沈阳站", "葫芦岛站", "硬座"),        # 京哈普速沈山段
    ("北京市", "哈尔滨市", "北京站", "哈尔滨站", "二等座"),      # 京哈高铁重构后
    ("沈阳市", "锦州市", "锦州站", "义县站", "硬座"),            # 锦承铁路义县
    ("沈阳市", "抚顺市", "沈阳站", "清原站", "硬座"),            # 沈吉铁路
    ("北京市", "赤峰市", "北京站", "赤峰站", "二等座"),          # 京哈高铁+喀赤
    ("沈阳市", "通辽市", "沈阳站", "通辽站", "二等座"),          # 京哈高铁+新通/大郑
    ("沈阳市", "盘锦市", "沈阳站", "盘锦站", "二等座"),          # 秦沈+盘营
]
for school, home, dep, arr, seat in cases:
    try:
        r = check_compliance(school_city=school, home_city=home, dep_station=dep,
                             arr_station=arr, seat=seat)
        if isinstance(r, dict):
            ok = r.get("ok")
            reason = r.get("reason", "")
            rev = "反向" if r.get("is_reverse") else ""
            print(f"  {school}→{home} | {dep}→{arr}: ok={ok} {rev} reason={reason[:60]}")
        else:
            print(f"  {school}→{home} | {dep}→{arr}: {r}")
    except Exception as e:
        print(f"  {school}→{home} | {dep}→{arr}: EXC {type(e).__name__}: {e}")

print("\n===== 4) lines-MISS 差分扫描（本批新增 MISS=0）=====")
# 基线 v2.20 的 LINE_ORDER 中既有 MISS 不算；只看本批新增行的 MISS
from importlib.machinery import SourceFileLoader
RB = SourceFileLoader("rb", os.path.join(BASE, "railway_data_v2.20.bak")).load_module()

miss_new = []
for line, seq in R.LINE_ORDER.items():
    if line in RB.LINE_ORDER and RB.LINE_ORDER[line] == seq:
        continue  # 未变动的既有线
    for s in seq:
        lines = R.STATION_INFO.get(s, {}).get("lines", [])
        if line not in lines:
            miss_new.append((line, s))
print(f"本批新增/变更线路中的 lines-MISS: {miss_new if miss_new else '0'}")

print("\n===== 5) 关键线路最终线序 =====")
for k in ["京哈高速铁路", "京哈铁路（普速）", "秦沈客运专线", "沈大铁路", "沈丹铁路",
          "沈丹客运专线", "溪田铁路（田桓铁路）", "锦承铁路", "喀赤高速铁路", "大郑铁路",
          "平齐铁路", "沈吉铁路", "沟海铁路", "营口支线", "凤上铁路", "辽开铁路", "溪博铁路（田桓铁路）"]:
    if k in R.LINE_ORDER:
        seq = R.LINE_ORDER[k]
        print(f"  {k} ({len(seq)}站): {seq}")
    else:
        print(f"  {k}: 不存在!")
