# -*- coding: utf-8 -*-
"""v2.21 终验：真实跨城案例 + lines-MISS 复查 + 自测 3 轮"""
import importlib.util, os, sys

BASE = r"C:\Users\cjp15\Desktop\全国客运站点\交接文件夹第三版（含一、二合并）\src"
sys.path.insert(0, BASE)
spec = importlib.util.spec_from_file_location("rd", os.path.join(BASE, "railway_data.py"))
R = importlib.util.module_from_spec(spec)
spec.loader.exec_module(R)
from student_ticket_checker import check_compliance

print("===== 真实跨城端到端 =====")
cases = [
    ("沈阳市", "大连市", "沈阳站", "大连站", "二等座"),          # 哈大高铁
    ("沈阳市", "大连市", "苏家屯站", "普兰店站", "硬座"),        # 沈大铁路
    ("沈阳市", "丹东市", "沈阳站", "丹东站", "二等座"),          # 沈丹客专
    ("沈阳市", "丹东市", "本溪站", "通远堡站", "硬座"),          # 沈丹铁路跨城
    ("沈阳市", "丹东市", "陈相屯站", "凤凰城站", "硬座"),        # 沈丹铁路北段
    ("北京市", "大连市", "北京站", "大连站", "二等座"),          # 京哈普速+秦沈+哈大
    ("北京市", "哈尔滨市", "北京站", "哈尔滨站", "二等座"),      # 京哈高铁重构后
    ("北京市", "沈阳市", "北京朝阳站", "沈阳站", "二等座"),      # 京沈高铁
    ("沈阳市", "葫芦岛市", "沈阳站", "葫芦岛站", "硬座"),        # 京哈普速沈山段
    ("承德市", "锦州市", "平泉站", "锦州站", "硬座"),            # 锦承铁路（义县贯通）
    ("沈阳市", "抚顺市", "沈阳站", "清原站", "硬座"),            # 沈吉铁路
    ("北京市", "赤峰市", "北京站", "赤峰站", "二等座"),          # 京哈高铁+喀赤（注意 key 格式）
    ("沈阳市", "盘锦市", "沈阳站", "盘锦站", "二等座"),          # 秦沈+盘营
    ("北京市", "通辽市", "北京站", "通辽站", "二等座"),          # 京哈高铁+新通
    ("沈阳市", "铁岭市", "沈阳站", "昌图站", "硬座"),            # 京哈普速沈哈段
]
for school, home, dep, arr, seat in cases:
    try:
        r = check_compliance(school_city=school, home_city=home, dep_station=dep,
                             arr_station=arr, seat=seat)
        if isinstance(r, dict):
            ok = r.get("ok")
            reason = (r.get("reason") or "").replace("\n", " ")
            print(f"  {'PASS' if ok else 'FAIL'} {school}→{home} | {dep}→{arr}: {reason[:70]}")
        else:
            print(f"  ??? {school}→{home} | {dep}→{arr}: {r}")
    except Exception as e:
        print(f"  EXC {school}→{home} | {dep}→{arr}: {type(e).__name__}: {e}")

print("\n===== lines-MISS 复查（全库）=====")
from importlib.machinery import SourceFileLoader
RB = SourceFileLoader("rb", os.path.join(BASE, "railway_data_v2.20.bak")).load_module()
miss_new = []
for line, seq in R.LINE_ORDER.items():
    if line in RB.LINE_ORDER and RB.LINE_ORDER[line] == seq:
        continue
    for s in seq:
        lines = R.STATION_INFO.get(s, {}).get("lines", [])
        if line not in lines:
            miss_new.append((line, s))
print(f"本批新增/变更线路中的 lines-MISS: {miss_new if miss_new else '0'}")
# 全库既有 MISS 基线（与 v2.20 对比，只多不判断）
miss_all = [(l, s) for l, seq in R.LINE_ORDER.items() for s in seq
            if l not in R.STATION_INFO.get(s, {}).get("lines", [])]
miss_base = [(l, s) for l, seq in RB.LINE_ORDER.items() for s in seq
             if l not in RB.STATION_INFO.get(s, {}).get("lines", [])]
print(f"全库 MISS: v2.21={len(miss_all)}  v2.20基线={len(miss_base)}  增量={len(set(miss_all)-set(miss_base))}")
