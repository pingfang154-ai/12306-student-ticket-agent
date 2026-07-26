# -*- coding: utf-8 -*-
# 修复：武汉→成都 经重庆 路径不可用
# 背景：宁蓉铁路(沪汉蓉)是武汉-重庆-成都的真实客运走廊，但数据库把它拆成
#       汉宜+宜万+渝利+成遂渝 多段，且每段均匀计权，导致 Dijkstra/Yen-KSP
#       返回最短边数的"达州(襄渝+达成)"绕行路线，永远不途经重庆；
#       同时 CITY_TO_STATIONS 没有"重庆"城市键，重庆北/重庆西被锁在市辖区，
#       引擎无法把"经重庆北"识别为"途经重庆"。
# 修复：
#   1) 网络层：补入 宁蓉铁路(沪汉蓉) 干线走廊（武汉→重庆→成都 主要大站序列），
#      使"经重庆"路线成为引擎可达的最短合理径路，KSP 自然将其列为首选。
#   2) 数据层：将 重庆站/重庆北站/重庆西站/沙坪坝站 统一归入城市"重庆"，
#      并加 CITY_ALIAS["重庆市"]="重庆"，使"途经重庆"被引擎正确识别。
# 铁律：仅增量、只加不删；新线写入 LINE_ORDER（Dijkstra 才可见）。
import importlib.util, json, shutil, re, os

SRC = "src/railway_data.py"
BAK = "src/railway_data_v2.7.bak"
shutil.copyfile(SRC, BAK)
print("backup ->", BAK)

spec = importlib.util.spec_from_file_location("rd", SRC)
R = importlib.util.module_from_spec(spec); spec.loader.exec_module(R)

LINE_ORDER = {k: list(v) for k, v in R.LINE_ORDER.items()}
STATION_INFO = {k: dict(v) for k, v in R.STATION_INFO.items()}
CITY_TO_STATIONS = {k: list(v) for k, v in R.CITY_TO_STATIONS.items()}
PROVINCE_TO_STATIONS = {k: list(v) for k, v in R.PROVINCE_TO_STATIONS.items()}
CITY_ALIAS = dict(R.CITY_ALIAS)

def union_line(station, line):
    if station in STATION_INFO:
        cur = set(STATION_INFO[station].get("lines", []))
        cur.add(line)
        STATION_INFO[station]["lines"] = sorted(cur)

# ---------- 1. 宁蓉铁路（沪汉蓉）武汉→重庆→成都 干线走廊 ----------
# 真实主要大站顺序（经联网核验：汉口-仙桃西-荆州-宜昌东-恩施-利川-丰都-重庆北-遂宁-成都东）
# 其中 宜昌东↔恩施 / 利川↔丰都 / 丰都↔重庆北 / 重庆北↔遂宁 为新增"干线直连"边，
# 使本走廊总跳数(9)短于既有"达州绕行"(12~17)，从而成为引擎首选合理径路。
NINGRONG = ["汉口站", "仙桃西站", "荆州站", "宜昌东站", "恩施站",
            "利川站", "丰都站", "重庆北站", "遂宁站", "成都东站"]
LINE_ORDER["宁蓉铁路"] = NINGRONG
for s in NINGRONG:
    if s in STATION_INFO:
        union_line(s, "宁蓉铁路")
    else:
        raise SystemExit("宁蓉干线站缺失: " + s)

# ---------- 2. 统一“重庆”城市（重庆站/重庆北/重庆西/沙坪坝） ----------
cq_city = [s for s in STATION_INFO
           if s.startswith("重庆")
           or (STATION_INFO[s].get("city") in ("渝中区", "渝北区", "沙坪坝区"))]
cq_city = sorted(set(cq_city))
print("重庆统一城市集:", cq_city)
CITY_TO_STATIONS["重庆"] = cq_city
# 别名：重庆市 -> 重庆（既有记忆：home 须用"重庆"；现"重庆市"亦可）
CITY_ALIAS["重庆市"] = "重庆"
# PROVINCE_TO_STATIONS 一致性（引擎未使用，仅保持数据整洁）
PROVINCE_TO_STATIONS.setdefault("重庆", [])
if "重庆" not in PROVINCE_TO_STATIONS["重庆"]:
    PROVINCE_TO_STATIONS["重庆"].append("重庆")

# ---------- 重建 GRAPH（增量加边） ----------
def edges_of(order):
    e = set()
    for seq in order.values():
        for a, b in zip(seq, seq[1:]):
            e.add(frozenset((a, b)))
    return e

old_edges = edges_of(R.LINE_ORDER)
new_edges = edges_of(LINE_ORDER)
to_add = new_edges - old_edges
print("新增边:", [tuple(e) for e in sorted(to_add, key=lambda x: (tuple(x)[0], tuple(x)[1]))])
gset = {k: set(v) for k, v in R.GRAPH.items()}
for fr in to_add:
    a, b = tuple(fr)
    gset.setdefault(a, set()).add(b)
    gset.setdefault(b, set()).add(a)
for s in STATION_INFO:
    gset.setdefault(s, set())
GRAPH = {k: sorted(v) for k, v in gset.items()}

# ---------- 生成 META ----------
new_line_count = len(LINE_ORDER)
new_station_count = len(STATION_INFO)
META = {
    "version": "2.8",
    "sources": R.META.get("sources", []) + ["宁蓉铁路(沪汉蓉)干线走廊修复"],
    "generated_at": "2026-07-26",
    "line_count": new_line_count,
    "station_count": new_station_count,
    "note": "v2.8 修复武汉→成都经重庆路径：补入宁蓉铁路(沪汉蓉)干线走廊(汉口-仙桃西-荆州-宜昌东-恩施-利川-丰都-重庆北-遂宁-成都东)，使经重庆成为引擎首选合理径路；将重庆站/重庆北/重庆西/沙坪坝统一归入城市'重庆'并加CITY_ALIAS['重庆市']。增量合并，未删除任何原有边"
}

# ---------- 重写 railway_data.py ----------
with open(SRC, "r", encoding="utf-8") as f:
    lines = f.read().split("\n")

lines[1] = "# 整理后的全国铁路数据层 v2.8（修复武汉→成都经重庆路径，自动生成，请勿手动编辑）"
lines[2] = "# 生成时间：2026-07-26"
lines[3] = "# 数据来源：既有 v2.7 数据源 + 宁蓉铁路(沪汉蓉)干线走廊修复"

def replace_line(name, value):
    for idx, ln in enumerate(lines):
        if re.match(r"^" + re.escape(name) + r"\s*=\s*", ln):
            lines[idx] = name + " = " + value
            return idx
    raise RuntimeError("未找到 " + name)

replace_line("META", json.dumps(META, ensure_ascii=False))
replace_line("LINE_ORDER", json.dumps(LINE_ORDER, ensure_ascii=False))
replace_line("STATION_INFO", json.dumps(STATION_INFO, ensure_ascii=False))
replace_line("CITY_TO_STATIONS", json.dumps(CITY_TO_STATIONS, ensure_ascii=False))
replace_line("PROVINCE_TO_STATIONS", json.dumps(PROVINCE_TO_STATIONS, ensure_ascii=False))
replace_line("CITY_ALIAS", json.dumps(CITY_ALIAS, ensure_ascii=False))
replace_line("GRAPH", json.dumps(GRAPH, ensure_ascii=False))

with open(SRC, "w", encoding="utf-8") as f:
    f.write("\n".join(lines) + "\n")

print("LINE_ORDER lines:", new_line_count)
print("STATION_INFO stations:", new_station_count)
print("GRAPH nodes:", len(GRAPH))
print("新增合成线数:", len([k for k in LINE_ORDER if '__SYN__' in k]))

# ---------- 同步 4 个 JSON ----------
DATA = "data"
os.makedirs(DATA, exist_ok=True)
json.dump(LINE_ORDER, open(os.path.join(DATA, "lines_order.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
json.dump(GRAPH, open(os.path.join(DATA, "graph_adjacency.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
json.dump(STATION_INFO, open(os.path.join(DATA, "station_info.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
json.dump(CITY_TO_STATIONS, open(os.path.join(DATA, "city_to_stations.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
print("4 JSON synced.")
