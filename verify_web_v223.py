# -*- coding: utf-8 -*-
"""验证 v2.23 Web /check 代表案例"""
import urllib.request, urllib.parse

BASE = "http://127.0.0.1:8094/check"
cases = [
    ("北京市", "呼和浩特市", "北京站", "呼和浩特站"),      # 京包铁路贯通
    ("北京市", "包头市", "北京站", "包头东站"),           # 京包终点
    ("北京市", "通辽市", "北京站", "通辽站"),             # 京通铁路贯通
    ("北京市", "赤峰市", "北京站", "赤峰站"),             # 京通+喀赤
    ("通辽市", "霍林郭勒市", "通辽站", "霍林河站"),        # 通霍铁路
    ("白城市", "阿尔山市", "白城站", "阿尔山站"),          # 白阿铁路全线
    ("长春市", "乌兰浩特市", "长春站", "乌兰浩特站"),      # 长白乌
    ("呼和浩特市", "锡林浩特市", "呼和浩特站", "锡林浩特站"), # 京包+集通+锡多
    ("哈尔滨市", "满洲里市", "哈尔滨站", "满洲里站"),      # 滨洲全线
    ("哈尔滨市", "根河市", "哈尔滨站", "满归站"),          # 滨洲+牙林
    ("北京市", "额济纳旗", "北京站", "额济纳站"),          # 包兰+临哈
    ("银川市", "包头市", "银川站", "包头站"),             # 包兰
    ("呼和浩特市", "鄂尔多斯市", "呼和浩特站", "鄂尔多斯站"), # 呼准鄂+包西
    ("呼和浩特市", "苏尼特右旗", "呼和浩特站", "赛汗塔拉站"), # 京包+集二
]
for school, home, dep, arr in cases:
    q = urllib.parse.urlencode({"school": school, "home": home, "dep": dep, "arr": arr})
    url = f"{BASE}?{q}"
    try:
        html = urllib.request.urlopen(url, timeout=10).read().decode("utf-8", "ignore")
        if "符合优惠区间" in html and "不符合优惠区间" not in html:
            verdict = "OK  符合优惠区间"
        elif "不符合优惠区间" in html:
            verdict = "FAIL 不符合优惠区间"
        elif "无法解析" in html:
            verdict = "FAIL 无法解析"
        else:
            verdict = "???? 无结论"
        print(f"{verdict}  {school}→{home} | {dep}→{arr}")
    except Exception as e:
        print(f"EXC {school}→{home} | {dep}→{arr}: {e}")
