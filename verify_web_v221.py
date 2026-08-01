# -*- coding: utf-8 -*-
"""验证 v2.21 Web /check 代表案例"""
import urllib.request, urllib.parse, re

BASE = "http://127.0.0.1:8092/check"
cases = [
    ("沈阳市", "大连市", "沈阳站", "大连站"),        # 哈大高铁
    ("沈阳市", "大连市", "苏家屯站", "普兰店站"),    # 沈大铁路（本批新线）
    ("北京市", "哈尔滨市", "北京站", "哈尔滨站"),    # 京哈高铁重构后
    ("北京市", "沈阳市", "北京朝阳站", "沈阳站"),    # 京沈高铁
    ("沈阳市", "丹东市", "本溪站", "通远堡站"),      # 沈丹铁路跨城
    ("承德市", "锦州市", "平泉站", "锦州站"),        # 锦承铁路义县贯通
    ("北京市", "大连市", "北京站", "大连站"),        # 京哈普速+秦沈+哈大
    ("沈阳市", "铁岭市", "沈阳站", "昌图站"),        # 京哈普速沈哈段
]
for school, home, dep, arr in cases:
    q = urllib.parse.urlencode({"school": school, "home": home, "dep": dep, "arr": arr})
    url = f"{BASE}?{q}"
    try:
        html = urllib.request.urlopen(url, timeout=10).read().decode("utf-8", "ignore")
        # 结论渲染字段：符合优惠区间 / 不符合优惠区间 / 无法解析
        if "符合优惠区间" in html and "不符合优惠区间" not in html:
            verdict = "✅ 符合优惠区间"
        elif "不符合优惠区间" in html:
            verdict = "❌ 不符合优惠区间"
        elif "无法解析" in html:
            verdict = "⚠️ 无法解析"
        else:
            verdict = "❓ 未找到结论（页面结构检查）"
        # 提取路径（如有）
        m = re.findall(r"([\u4e00-\u9fff]+站)", html)
        print(f"{school}→{home} | {dep}→{arr}: {verdict}  [{url[:80]}...]")
    except Exception as e:
        print(f"{school}→{home} | {dep}→{arr}: EXC {e}")
