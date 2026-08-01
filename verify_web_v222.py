# -*- coding: utf-8 -*-
"""验证 v2.22 Web /check 代表案例"""
import urllib.request, urllib.parse

BASE = "http://127.0.0.1:8093/check"
cases = [
    ("哈尔滨市", "漠河市", "哈尔滨站", "古莲站"),      # 滨北+齐北+富嫩+嫩林 至全国最北端
    ("长春市", "珲春市", "长春站", "珲春站"),          # 长珲城际
    ("哈尔滨市", "绥芬河市", "哈尔滨站", "绥芬河站"),  # 滨绥铁路
    ("哈尔滨市", "抚远市", "哈尔滨站", "抚远站"),      # 哈佳+绥佳+佳富+福前+前抚 至最东端
    ("北京市", "哈尔滨市", "北京站", "哈尔滨站"),      # 京哈普速贯通
    ("沈阳市", "吉林市", "沈阳站", "吉林站"),          # 沈吉铁路
    ("长春市", "图们市", "长春站", "图们站"),          # 长图铁路
    ("四平市", "齐齐哈尔市", "四平站", "齐齐哈尔站"),  # 平齐铁路
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
