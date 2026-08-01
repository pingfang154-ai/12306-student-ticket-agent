# -*- coding: utf-8 -*-
"""v2.23 端到端终验（修正用例）"""
import sys
sys.path.insert(0, r"C:\Users\cjp15\Desktop\全国客运站点\交接文件夹第三版（含一、二合并）\src")
from student_ticket_checker import check_compliance

cases = [
    ("北京市", "呼和浩特市", "北京站", "呼和浩特站", "硬座"),
    ("北京市", "包头市", "北京站", "包头东站", "硬座"),
    ("北京市", "呼和浩特市", "北京北站", "呼和浩特东站", "二等座"),
    ("呼和浩特市", "鄂尔多斯市", "呼和浩特站", "鄂尔多斯站", "硬座"),
    ("北京市", "通辽市", "北京站", "通辽站", "硬座"),
    ("北京市", "赤峰市", "北京站", "赤峰站", "硬座"),
    ("通辽市", "霍林郭勒市", "通辽站", "霍林河站", "硬座"),   # 同城代管县级市→退化，预期 FAIL 属正常
    ("白城市", "阿尔山市", "白城站", "阿尔山站", "硬座"),
    ("长春市", "乌兰浩特市", "长春站", "乌兰浩特站", "二等座"),
    ("呼和浩特市", "锡林浩特市", "呼和浩特站", "锡林浩特站", "硬座"),
    ("哈尔滨市", "满洲里市", "哈尔滨站", "满洲里站", "硬座"),
    ("哈尔滨市", "根河市", "哈尔滨站", "满归站", "硬座"),
    ("哈尔滨市", "额尔古纳市", "哈尔滨站", "莫尔道嘎站", "硬座"),
    ("北京市", "额济纳旗", "北京站", "额济纳站", "硬座"),
    ("银川市", "包头市", "银川站", "包头站", "硬座"),
    ("呼和浩特市", "苏尼特右旗", "呼和浩特站", "赛汗塔拉站", "硬座"),
    ("哈尔滨市", "海拉尔市", "哈尔滨站", "海拉尔站", "硬座"),
    ("哈尔滨市", "漠河市", "哈尔滨站", "古莲站", "硬座"),   # 跨批联动
]
pass_n = 0
for school, home, dep, arr, seat in cases:
    try:
        r = check_compliance(school_city=school, home_city=home, dep_station=dep,
                             arr_station=arr, seat=seat)
        ok = r.get("ok") if isinstance(r, dict) else False
        reason = (r.get("reason") or "")[:50] if isinstance(r, dict) else ""
        print(f"  {'PASS' if ok else '-- '} {school}→{home} | {dep}→{arr}: {reason}")
        pass_n += 1 if ok else 0
    except Exception as e:
        print(f"  EXC {school}→{home} | {dep}→{arr}: {type(e).__name__}: {e}")
print("PASS:", pass_n, "/", len(cases))
