# -*- coding: utf-8 -*-
"""
学生票判断引擎测试用例。
运行：python student_ticket_checker.py --test
"""
import student_ticket_checker as C
import railway_data as R

CASES = [
    # (name, school, home, dep, arr, seat, fresh_grad, 期望ok, 期望is_reverse, 期望seat_invalid, via_stations, new_home_city)
    ("合规-同城端点(成都↔北京)", "成都", "北京", "成都东", "北京西", "二等座", False, True, False, False),
    ("中间站合规(成都↔上海,经南京南)", "成都", "上海", "成都东", "南京南", "二等座", False, True, False, False),
    ("反向购票(学校成都,家庭上海,买南京南→成都东)", "成都", "上海", "南京南", "成都东", "二等座", False, True, True, False),
    ("案例四已变合规(成都↔北京含广州南经新线)", "成都", "北京", "成都东", "广州南", "二等座", False, True, False, False),
    ("席别不符(商务座)", "成都", "北京", "成都东", "北京西", "商务座", False, True, False, True),
    ("同城兼容(出发站填城市名成都)", "成都", "北京", "成都", "北京西", None, False, True, False, False),
    ("新生场景(凭通知书1次)", "成都", "北京", "成都东", "北京西", "二等座", True, True, False, False),
    ("硬座合规(普速席别)", "成都", "北京", "成都东", "北京西", "硬座", False, True, False, False),
    ("同城端点-学校家庭同城应不符", "成都", "成都", "成都东", "成都南", None, False, False, False, False),
    ("案例五-广州↔合肥经长沙(段1)", "广州", "合肥", "广州", "长沙南", "二等座", False, True, False, False),
    ("案例五-广州↔合肥经长沙(段2)", "广州", "合肥", "长沙南", "合肥", "二等座", False, True, False, False),
    # ---- 4新案例(引擎确定性判断部分) ----
    ("案例一-合规段:武汉↔大理,广通北→大理", "武汉", "大理", "广通北", "大理", "二等座", False, True, False, False),
    ("案例一-多径路合规:武汉↔大理,武汉→成都东(多路径)", "武汉", "大理", "武汉", "成都东", "二等座", False, True, False, False),
    ("案例二:南京↔保定,黄山→保定(不在路径)", "南京", "保定", "黄山", "保定", "二等座", False, False, False, False),
    # ⚠ 引擎已知局限：改家到黄山的场景(南京↔黄山新区间 + 黄山→保定)现实中合规但引擎当前无法建模(需多区间支持)
    ("案例二:南京↔黄山区间,南京→黄山(合规)", "南京", "黄山", "南京", "黄山", "二等座", False, True, False, False),
    ("案例三-段1:桂林↔南宁,桂林→南宁(合规,反向)", "南宁", "桂林", "桂林", "南宁", "二等座", False, True, True, False),
    ("案例四:南京↔西安,南京→贵阳(不在路径)", "南京", "西安", "南京", "贵阳", "二等座", False, False, False, False),
    ("案例四:南京↔西安,贵阳→西安(不在路径)", "南京", "西安", "贵阳", "西安", "二等座", False, False, False, False),
    # ---- 廊道探测修复（跨廊道 / 多枢纽绕行，explicit via 优先）----
    ("廊道修复:武汉↔大理,武汉→重庆(经重庆枢纽)", "武汉", "大理", "武汉", "重庆", "二等座", False, True, False, False, ["重庆"]),
    ("廊道修复:武汉↔大理,重庆→大理(经重庆枢纽)", "武汉", "大理", "重庆", "大理", "二等座", False, True, False, False, ["重庆"]),
    ("廊道修复:武汉↔大理,武汉→成都东(仍合规,回归)", "武汉", "大理", "武汉", "成都东", "二等座", False, True, False, False),
    # 守卫验证：南京↔西安 买南京→贵阳 仍应不合规（离谱绕行被拦截）
    ("廊道守卫:南京↔西安,南京→贵阳(仍不合规)", "南京", "西安", "南京", "贵阳", "二等座", False, False, False, False),
    # ---- 新增：显式途经站廊道探测（优先级最高）----
    # 案例六：武汉→大理 经 重庆+成都+广通北（跨廊道多枢纽，KSP 单边阻塞无法发现）
    ("案例六-廊道优先:武汉↔大理,武汉→大理 经[重庆,成都,广通北]",
     "武汉", "大理", "武汉", "大理", "二等座", False, True, False, False,
     ["重庆", "成都", "广通北"]),
    # 案例九方案B：南京→西安（改家贵阳）经 凯里南+荔波+安顺（贵阳作枢纽连接两区间）
    ("案例九B-廊道优先:南京↔西安(改家贵阳),南京→西安 经[凯里南,荔波,安顺]",
     "南京", "西安", "南京", "西安", "二等座", False, True, False, False,
     ["凯里南", "荔波", "安顺"], "贵阳"),
    # 负例：南昌→株洲 绕行福建（株洲 不在 南昌↔上海 优惠路径上，且离谱绕行被守卫拦截 → 不合规）
    ("负例-廊道守卫:南昌↔上海,南昌→株洲 经[福州,厦门](绕行福建仍不合规)",
     "南昌", "上海", "南昌", "株洲", "二等座", False, False, False, False,
     ["福州", "厦门"]),
]

def run_all():
    passed = 0
    failed = 0
    for i, case in enumerate(CASES, 1):
        name = case[0]
        school, home, dep, arr = case[1:5]
        seat, fg = case[5], case[6]
        exp_ok, exp_rev, exp_seat = case[7:10]
        via = case[10] if len(case) > 10 else None
        new_home = case[11] if len(case) > 11 else None
        rep = C.check_student_ticket(school, home, dep, arr, seat, fg, new_home, via)
        r = rep["result"]
        ok_match = (r["ok"] == exp_ok)
        rev_match = (r.get("is_reverse", False) == exp_rev) if exp_ok else True
        seat_match = (r.get("seat_invalid", False) == exp_seat)
        all_match = ok_match and rev_match and seat_match
        flag = "PASS" if all_match else "FAIL"
        if all_match:
            passed += 1
        else:
            failed += 1
        print(f"[{flag}] 用例{i}: {name}")
        print(f"        输入: {school}↔{home}{('(改家→'+new_home+')') if new_home else ''}, "
              f"{dep}→{arr}, 席别={seat}, 新生={fg}"
              f"{(' via='+str(via)) if via else ''}")
        print(f"        结果: ok={r['ok']}(期望{exp_ok}) "
              f"is_reverse={r.get('is_reverse',False)}(期望{exp_rev}) "
              f"seat_invalid={r.get('seat_invalid',False)}(期望{exp_seat})")
        print(f"        结论: {r['reason']}")
        if not all_match:
            print(f"        ⚠ 期望不符，请核查")
    print("\n" + "-" * 56)
    print("补充验证1：find_path_via_hubs（廊道探测核心函数，新签名 (bool, path)）")
    # 直接验证廊道探测能产出 武汉→重庆→成都→大理（经广通北）的完整径路。
    # 注意：径路使用具体站名（如汉口站代表武汉、云南驿站代表大理），故按"城市站集"判断。
    sch_wh = R.resolve_location("武汉")
    home_dl = R.resolve_location("大理")
    chongqing = R.resolve_location("重庆")
    chengdu = R.resolve_location("成都")
    found, p = C.find_path_via_hubs("武汉", "大理", ["重庆", "成都", "广通北"], C.HUB_STATIONS)
    ok_path = (
        found and p
        and any(s in sch_wh for s in p)        # 起点落在武汉城市
        and any(s in chongqing for s in p)      # 途经重庆
        and any(s in chengdu for s in p)        # 途经成都
        and any(s in R.resolve_location("广通北") for s in p)  # 途经广通北（同城站，如广通北站/南华站等）
        and any(s in home_dl for s in p)        # 终点落在大理城市
    )
    if ok_path:
        passed += 1
        print(f"[PASS] find_path_via_hubs 返回 武汉→(重庆,成都,广通北)→大理 廊道径路：")
        print(f"        {' → '.join(p[:18])}{' ...' if len(p) > 18 else ''}")
    else:
        failed += 1
        print(f"[FAIL] find_path_via_hubs 未返回预期廊道径路：found={found}, path={p}")

    print("\n" + "-" * 56)
    print("补充验证2：多区间联合判断（改家场景，扣2次）")
    # 南京(学校)↔保定(原家)，改家到黄山：南京→黄山(新区间) + 黄山→保定(衍生区间)
    seg = C.check_route_segments("南京", "保定", ["南京", "黄山", "保定"],
                                  new_home_city="黄山")
    seg_ok = all(s["ok"] for s in seg["segments"])
    if seg_ok:
        passed += 1
        print(f"[PASS] 改家黄山后 南京→黄山→保定 全程可购学生票（{seg['overall_summary']}）")
        for s in seg["segments"]:
            print(f"        {s['dep']}→{s['arr']}: {'✅学生票' if s['ok'] else '❌成人票'} | {s['reason']}")
    else:
        failed += 1
        print(f"[FAIL] 改家黄山后 南京→黄山→保定 未全程合规：{seg['overall_summary']}")
        for s in seg["segments"]:
            print(f"        {s['dep']}→{s['arr']}: {'✅学生票' if s['ok'] else '❌成人票'} | {s['reason']}")
    total = passed + failed
    print("\n" + "=" * 56)
    print(f"测试结果：通过 {passed}/{total}，失败 {failed}")
    print("=" * 56)
    return failed == 0

if __name__ == "__main__":
    import sys
    sys.exit(0 if run_all() else 1)
