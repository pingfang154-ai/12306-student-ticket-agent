# -*- coding: utf-8 -*-
"""v2.22 端到端复验"""
import sys
sys.path.insert(0, r"C:\Users\cjp15\Desktop\全国客运站点\交接文件夹第三版（含一、二合并）\src")
from student_ticket_checker import check_compliance

cases = [
    ("哈尔滨市", "漠河市", "哈尔滨站", "古莲站", "硬座"),
    ("哈尔滨市", "漠河市", "哈尔滨站", "漠河站", "硬座"),
    ("长春市", "珲春市", "长春站", "珲春站", "二等座"),
    ("长春市", "图们市", "长春站", "图们站", "硬座"),
    ("哈尔滨市", "绥芬河市", "哈尔滨站", "绥芬河站", "二等座"),
    ("哈尔滨市", "牡丹江市", "哈尔滨站", "牡丹江站", "二等座"),
    ("沈阳市", "吉林市", "沈阳站", "吉林站", "硬座"),
    ("北京市", "哈尔滨市", "北京站", "哈尔滨站", "二等座"),
    ("上海市", "哈尔滨市", "上海虹桥站", "哈尔滨站", "二等座"),
    ("广州市", "哈尔滨市", "广州站", "哈尔滨站", "二等座"),
    ("哈尔滨市", "大连市", "哈尔滨站", "大连站", "二等座"),
    ("长春市", "白山市", "长春站", "临江站", "硬座"),
    ("哈尔滨市", "鸡西市", "哈尔滨站", "东方红站", "硬座"),
    ("哈尔滨市", "抚远市", "哈尔滨站", "抚远站", "硬座"),
    ("哈尔滨市", "鹤岗市", "哈尔滨站", "鹤北站", "硬座"),
    ("哈尔滨市", "伊春市", "哈尔滨站", "乌伊岭站", "硬座"),
]
pass_n = 0
for school, home, dep, arr, seat in cases:
    try:
        r = check_compliance(school_city=school, home_city=home, dep_station=dep,
                             arr_station=arr, seat=seat)
        ok = r.get("ok") if isinstance(r, dict) else False
        reason = (r.get("reason") or "")[:50] if isinstance(r, dict) else ""
        print(f"  {'PASS' if ok else 'FAIL'} {school}→{home} | {dep}→{arr}: {reason}")
        pass_n += 1 if ok else 0
    except Exception as e:
        print(f"  EXC {school}→{home} | {dep}→{arr}: {type(e).__name__}: {e}")
print("PASS:", pass_n, "/", len(cases))
