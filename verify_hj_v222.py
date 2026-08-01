# -*- coding: utf-8 -*-
"""v2.22 黑吉批连通性 + 端到端核查"""
import importlib.util, os, sys

BASE = r"C:\Users\cjp15\Desktop\全国客运站点\交接文件夹第三版（含一、二合并）\src"
sys.path.insert(0, BASE)
spec = importlib.util.spec_from_file_location("rd", os.path.join(BASE, "railway_data.py"))
R = importlib.util.module_from_spec(spec)
spec.loader.exec_module(R)
from student_ticket_checker import _dijkstra, check_compliance

print("===== 1) 新站 BFS 连通性（→ 北京/上海虹桥/广州/哈尔滨/沈阳）=====")
hubs = ["北京站", "上海虹桥站", "广州站", "哈尔滨站", "沈阳站"]
samples = ["绥芬河站", "黑河站", "古莲站", "抚远站", "东方红站", "乌伊岭站", "黑河站", "图们站",
           "珲春站", "集安站", "临江站", "松原站", "孙吴站", "加格达奇站", "五常站", "密山站",
           "七台河站", "双鸭山站", "齐齐哈尔站", "延吉站", "敦化站", "梅河口站", "辽源站"]
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

print("\n===== 2) 端到端 check_compliance =====")
cases = [
    ("哈尔滨市", "绥芬河市", "哈尔滨站", "绥芬河站", "二等座"),      # 滨绥铁路
    ("哈尔滨市", "齐齐哈尔市", "哈尔滨站", "齐齐哈尔站", "二等座"),  # 哈齐高铁
    ("哈尔滨市", "佳木斯市", "哈尔滨站", "佳木斯站", "二等座"),      # 哈佳铁路
    ("哈尔滨市", "牡丹江市", "哈尔滨站", "牡丹江站", "二等座"),      # 哈牡高铁
    ("哈尔滨市", "黑河市", "哈尔滨站", "黑河站", "硬座"),           # 滨北+北黑
    ("哈尔滨市", "漠河市", "哈尔滨站", "古莲站", "硬座"),           # 滨北+齐北?+富嫩+嫩林
    ("长春市", "珲春市", "长春站", "珲春站", "二等座"),             # 长珲城际
    ("长春市", "图们市", "长春站", "图们站", "硬座"),               # 长图铁路
    ("长春市", "白城市", "长春站", "白城站", "二等座"),             # 长白铁路
    ("长春市", "通化市", "长春站", "通化站", "硬座"),               # 长图?+沈吉+通灌
    ("四平市", "齐齐哈尔市", "四平站", "齐齐哈尔站", "硬座"),        # 平齐铁路
    ("沈阳市", "吉林市", "沈阳站", "吉林站", "硬座"),               # 沈吉铁路
    ("沈阳市", "梅河口市", "沈阳站", "梅河口站", "硬座"),            # 沈吉
    ("北京市", "哈尔滨市", "北京站", "哈尔滨站", "二等座"),          # 京哈普速(补全后)
    ("哈尔滨市", "三亚市", "哈尔滨站", "三亚站", "二等座"),          # 长途跨线
    ("大连市", "哈尔滨市", "大连站", "哈尔滨站", "二等座"),          # 哈大高铁
    ("通化市", "丹东市", "通化站", "丹东站", "硬座"),               # 通灌+沈丹
]
for school, home, dep, arr, seat in cases:
    try:
        r = check_compliance(school_city=school, home_city=home, dep_station=dep,
                             arr_station=arr, seat=seat)
        if isinstance(r, dict):
            ok = r.get("ok")
            reason = (r.get("reason") or "").replace("\n", " ")
            print(f"  {'PASS' if ok else 'FAIL'} {school}→{home} | {dep}→{arr}: {reason[:60]}")
        else:
            print(f"  ??? {school}→{home} | {dep}→{arr}: {r}")
    except Exception as e:
        print(f"  EXC {school}→{home} | {dep}→{arr}: {type(e).__name__}: {e}")

print("\n===== 3) lines-MISS 差分（本批新增=0）=====")
from importlib.machinery import SourceFileLoader
RB = SourceFileLoader("rb", os.path.join(BASE, "railway_data_v2.21.bak")).load_module()
miss_new = []
for line, seq in R.LINE_ORDER.items():
    if line in RB.LINE_ORDER and RB.LINE_ORDER[line] == seq:
        continue
    for s in seq:
        lines = R.STATION_INFO.get(s, {}).get("lines", [])
        if line not in lines:
            miss_new.append((line, s))
print(f"本批新增/变更线路 MISS: {miss_new if miss_new else '0'}")

print("\n===== 4) 关键线路线序 =====")
for k in ["平齐铁路", "京哈铁路（普速）", "滨洲铁路", "长白铁路", "哈齐高速铁路", "哈牡高速铁路",
          "哈佳铁路", "长珲城际铁路", "滨绥铁路", "图佳铁路", "绥佳铁路", "嫩林铁路", "京哈高速铁路"]:
    if k in R.LINE_ORDER:
        seq = R.LINE_ORDER[k]
        print(f"  {k} ({len(seq)}站): {seq}")
