# -*- coding: utf-8 -*-
"""增量合并「沪渝蓉沿江高铁（武宜段）」到第三版 railway_data.py + 4 个 JSON。
原则：只加不删。新连接必须作为 LINE_ORDER 中的线存在（含合成联络线），不能只加裸 GRAPH 边。
"""
import importlib.util, json, os, shutil, datetime

BASE = r"C:\Users\cjp15\Desktop\全国客运站点\交接文件夹第三版（含一、二合并）"
SRC = os.path.join(BASE, "src", "railway_data.py")
DATA = os.path.join(BASE, "data")

# ---------- 1. 备份 ----------
bak = os.path.join(BASE, "src", "railway_data_v2.2.bak")
if not os.path.exists(bak):
    shutil.copy2(SRC, bak)
    print("备份 ->", bak)
else:
    print("备份已存在，跳过:", bak)

# ---------- 2. import 现有模块（深拷贝，避免污染） ----------
spec = importlib.util.spec_from_file_location("rd", SRC)
R = importlib.util.module_from_spec(spec); spec.loader.exec_module(R)

LINE_ORDER = dict(R.LINE_ORDER)
STATION_INFO = {k: {"province": v["province"], "city": v["city"], "lines": list(v["lines"])}
                for k, v in R.STATION_INFO.items()}
CITY_TO_STATIONS = {k: list(v) for k, v in R.CITY_TO_STATIONS.items()}
PROVINCE_TO_STATIONS = {k: list(v) for k, v in R.PROVINCE_TO_STATIONS.items()}
CITY_ALIAS = dict(R.CITY_ALIAS)
GRAPH = {k: list(v) for k, v in R.GRAPH.items()}

# ---------- 3. 新数据：武宜段主线 + 宜昌北-宜昌东合成联络线 ----------
NEW_LINE = "沪渝蓉沿江高铁（武宜段）"
SEQ = ["汉口站", "汉川北站", "天门站", "京山南站", "钟祥南站", "荆门西站", "当阳西站", "宜昌北站"]
assert LINE_ORDER.get(NEW_LINE) is None, "武宜段线已存在？"
LINE_ORDER[NEW_LINE] = SEQ

SYN_LINE = "武宜段-宜昌北宜昌东联络线"
assert LINE_ORDER.get(SYN_LINE) is None
LINE_ORDER[SYN_LINE] = ["宜昌北站", "宜昌东站"]

# 新站 STATION_INFO（province=湖北）
new_stations = {
    "汉川北站": ("湖北", "孝感市"),
    "京山南站": ("湖北", "荆门市"),
    "钟祥南站": ("湖北", "荆门市"),
    "荆门西站": ("湖北", "荆门市"),
    "当阳西站": ("湖北", "宜昌市"),
    "宜昌北站": ("湖北", "宜昌市"),
}
added = []
for st, (prov, city) in new_stations.items():
    if st not in STATION_INFO:
        STATION_INFO[st] = {"province": prov, "city": city, "lines": [NEW_LINE]}
        added.append(st)
    elif NEW_LINE not in STATION_INFO[st]["lines"]:
        STATION_INFO[st]["lines"].append(NEW_LINE)

# 既有站补 lines（天门站/汉口站属于武宜段；宜昌东站属于联络线）
for st in ["汉口站", "天门站"]:
    if NEW_LINE not in STATION_INFO[st]["lines"]:
        STATION_INFO[st]["lines"].append(NEW_LINE)
if SYN_LINE not in STATION_INFO["宜昌东站"]["lines"]:
    STATION_INFO["宜昌东站"]["lines"].append(SYN_LINE)
if SYN_LINE not in STATION_INFO["宜昌北站"]["lines"]:
    STATION_INFO["宜昌北站"]["lines"].append(SYN_LINE)

# 同城映射 CITY_TO_STATIONS（全城市名 key）
cts_add = {
    "孝感市": ["汉川北站"],
    "荆门市": ["京山南站", "钟祥南站", "荆门西站"],
    "宜昌市": ["当阳西站", "宜昌北站"],
}
for city, sts in cts_add.items():
    for st in sts:
        if st not in CITY_TO_STATIONS.get(city, []):
            CITY_TO_STATIONS.setdefault(city, []).append(st)

# PROVINCE_TO_STATIONS["湖北"] 是站名扁平列表，加入 6 个新站
hb = PROVINCE_TO_STATIONS["湖北"]
for st in added:
    if st not in hb:
        hb.append(st)

# GRAPH 增量加边（Dijkstra 只认 LINE_ORDER 派生边，故新连接必须进 LINE_ORDER）
def edges_of(lo):
    e = set()
    for seq in lo.values():
        for a, b in zip(seq, seq[1:]):
            e.add(tuple(sorted((a, b))))
    return e

to_add = edges_of(LINE_ORDER) - edges_of(R.LINE_ORDER)
gset = {k: set(v) for k, v in GRAPH.items()}
for a, b in to_add:
    gset.setdefault(a, set()).add(b)
    gset.setdefault(b, set()).add(a)
GRAPH = {k: sorted(v) for k, v in gset.items()}

print(f"新增线路: {len(LINE_ORDER) - len(R.LINE_ORDER)} 条 -> {len(LINE_ORDER)}")
print(f"新增车站: {len(added)} 个 -> {added}")
print(f"新增边(对): {len(to_add)}")

# ---------- 4. 再生 railway_data.py（按标记截取 helper 尾部） ----------
orig = open(SRC, encoding="utf-8").read().splitlines()
hi = next(i for i, l in enumerate(orig) if l.strip().startswith("LINE_NAME_ALIAS"))
today = datetime.date.today().isoformat()
header = [
    "# -*- coding: utf-8 -*-",
    "# 整理后的全国铁路数据层 v2.3（追加沪渝蓉沿江高铁武宜段，自动生成，请勿手动编辑）",
    f"# 生成时间：{today}",
    "# 数据来源：既有 v2.2 数据源 + 沪渝蓉沿江高铁武宜段铁路站点表.xlsx",
    f"# 线路数：{len(LINE_ORDER)}  车站数：{len(STATION_INFO)}",
    "",
]
META = {
    "version": "2.3",
    "sources": R.META["sources"] + ["沪渝蓉沿江高铁武宜段铁路站点表.xlsx"],
    "generated_at": today,
    "line_count": len(LINE_ORDER),
    "station_count": len(STATION_INFO),
    "note": "v2.3 追加沪渝蓉沿江高铁（武宜段）8站及宜昌北-宜昌东合成联络线；增量合并，未删除任何原有边",
}
dict_lines = [
    "META = " + json.dumps(META, ensure_ascii=False),
    "LINE_ORDER = " + json.dumps(LINE_ORDER, ensure_ascii=False),
    "STATION_INFO = " + json.dumps(STATION_INFO, ensure_ascii=False),
    "CITY_TO_STATIONS = " + json.dumps(CITY_TO_STATIONS, ensure_ascii=False),
    "PROVINCE_TO_STATIONS = " + json.dumps(PROVINCE_TO_STATIONS, ensure_ascii=False),
    "CITY_ALIAS = " + json.dumps(CITY_ALIAS, ensure_ascii=False),
    "GRAPH = " + json.dumps(GRAPH, ensure_ascii=False),
]
tail = orig[hi:]  # 从 LINE_NAME_ALIAS 行起（含 helper 函数）
new_lines = header + dict_lines + [""] + tail
open(SRC, "w", encoding="utf-8").write("\n".join(new_lines) + "\n")
print("railway_data.py 已再生")

# ---------- 5. 同步 4 个 JSON ----------
json_map = {
    "lines_order.json": LINE_ORDER,
    "station_info.json": STATION_INFO,
    "city_to_stations.json": CITY_TO_STATIONS,
    "graph_adjacency.json": GRAPH,
}
for fn, d in json_map.items():
    json.dump(d, open(os.path.join(DATA, fn), "w", encoding="utf-8"), ensure_ascii=False, indent=2)
print("4 个 JSON 已同步")
