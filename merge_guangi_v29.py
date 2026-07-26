# -*- coding: utf-8 -*-
# 任务五：广西壮族自治区补充站点总表 增量合并 (v2.8 -> v2.9)
# 数据源：各省市细分站点/广西壮族自治区/广西壮族自治区补充站点总表.xlsx
# 共 17 座办理客运车站（分属 7 条线路），均为"单点式"补充（Excel 给前/后一站相邻参考）。
# 策略：
#   - 既有线精确插入（衡柳/焦柳/益湛/黎湛/湘桂）：把新站插到既有序列的地理正确位置；
#   - 南凭高速铁路（南崇段）整段延伸：补全崇凭段，重命名为 南凭高速铁路；
#   - 玉铁铁路为全新线（玉林-博白），建 2 站线保证 Dijkstra 可见；
#   - 富川站经既有 益湛铁路（永玉段）挂在 贺州站（相邻客站，钟山站货运化被跳过）前；
#   - 宁明站插入 湘桂铁路 崇左-凭祥 之间；凭祥站已在湘桂铁路，无需新线。
# 铁律：仅增量、只加不删；新线写入 LINE_ORDER（Dijkstra 才可见）。
import importlib.util, json, shutil, re, os

SRC = "src/railway_data.py"
BAK = "src/railway_data_v2.8.bak"
shutil.copyfile(SRC, BAK)
print("backup ->", BAK)

spec = importlib.util.spec_from_file_location("rd", SRC)
R = importlib.util.module_from_spec(spec); spec.loader.exec_module(R)

LINE_ORDER = {k: list(v) for k, v in R.LINE_ORDER.items()}
STATION_INFO = {k: dict(v) for k, v in R.STATION_INFO.items()}
CITY_TO_STATIONS = {k: list(v) for k, v in R.CITY_TO_STATIONS.items()}
PROVINCE_TO_STATIONS = {k: list(v) for k, v in R.PROVINCE_TO_STATIONS.items()}
CITY_ALIAS = dict(R.CITY_ALIAS)

PROV = "广西壮族自治区"

def union_line(station, line):
    if station in STATION_INFO:
        cur = set(STATION_INFO[station].get("lines", []))
        cur.add(line)
        STATION_INFO[station]["lines"] = sorted(cur)

def ensure_station(name, city, line):
    if name not in STATION_INFO:
        STATION_INFO[name] = {"province": PROV, "city": city, "lines": []}
    STATION_INFO[name]["province"] = PROV
    STATION_INFO[name]["city"] = city
    union_line(name, line)
    if city not in CITY_TO_STATIONS:
        CITY_TO_STATIONS[city] = []
    if name not in CITY_TO_STATIONS[city]:
        CITY_TO_STATIONS[city].append(name)
    PROVINCE_TO_STATIONS.setdefault(PROV, [])
    if name not in PROVINCE_TO_STATIONS[PROV]:
        PROVINCE_TO_STATIONS[PROV].append(name)

def insert_in_line(line_name, station, after=None, before=None):
    seq = LINE_ORDER[line_name]
    if station in seq:
        return
    if after is not None:
        seq.insert(seq.index(after) + 1, station)
    elif before is not None:
        seq.insert(seq.index(before), station)
    else:
        seq.append(station)

# ---------- A. 南凭高速铁路（南崇段）→ 南凭高速铁路（延伸崇凭段） ----------
oldkey = "南凭高速铁路（南崇段）"
seq = LINE_ORDER.pop(oldkey)
seq = seq + ["宁明东站", "龙州站", "凭祥东站"]
LINE_ORDER["南凭高速铁路"] = seq
for s in seq:
    if s in STATION_INFO and oldkey in STATION_INFO[s].get("lines", []):
        STATION_INFO[s]["lines"].remove(oldkey)
    union_line(s, "南凭高速铁路")
ensure_station("宁明东站", "广西崇左市", "南凭高速铁路")
ensure_station("龙州站", "广西崇左市", "南凭高速铁路")
ensure_station("凭祥东站", "广西凭祥市", "南凭高速铁路")
print("A 南凭高速铁路:", LINE_ORDER["南凭高速铁路"])

# ---------- B. 湘桂铁路：插入 宁明站（崇左-凭祥之间） ----------
insert_in_line("湘桂铁路", "宁明站", after="崇左站")
ensure_station("宁明站", "广西崇左市", "湘桂铁路")
print("B 湘桂铁路(尾):", LINE_ORDER["湘桂铁路"][-4:])

# ---------- C. 衡柳铁路：插入 全州南站、兴安北站（永州之后） ----------
insert_in_line("衡柳铁路", "全州南站", after="永州站")
insert_in_line("衡柳铁路", "兴安北站", after="全州南站")
ensure_station("全州南站", "广西桂林市", "衡柳铁路")
ensure_station("兴安北站", "广西桂林市", "衡柳铁路")
print("C 衡柳铁路(头):", LINE_ORDER["衡柳铁路"][:5])

# ---------- D. 焦柳铁路：插入 罗城站/融水站（柳州-融安之间）、三江县站（融安之后） ----------
insert_in_line("焦柳铁路", "罗城站", after="柳州站")
insert_in_line("焦柳铁路", "融水站", after="罗城站")
insert_in_line("焦柳铁路", "三江县站", after="融安站")
ensure_station("罗城站", "广西河池市", "焦柳铁路")
ensure_station("融水站", "广西柳州市", "焦柳铁路")
ensure_station("三江县站", "广西柳州市", "焦柳铁路")
print("D 焦柳铁路(尾):", LINE_ORDER["焦柳铁路"][-5:])

# ---------- E. 益湛铁路（永玉段）：富川站挂贺州前；容县/北流插岑溪-玉林之间 ----------
insert_in_line("益湛铁路（永玉段）", "富川站", before="贺州站")
insert_in_line("益湛铁路（永玉段）", "容县站", after="岑溪站")
insert_in_line("益湛铁路（永玉段）", "北流站", after="容县站")
ensure_station("富川站", "广西贺州市", "益湛铁路（永玉段）")
ensure_station("容县站", "广西玉林市", "益湛铁路（永玉段）")
ensure_station("北流站", "广西玉林市", "益湛铁路（永玉段）")
print("E 益湛铁路（永玉段）:", LINE_ORDER["益湛铁路（永玉段）"])

# ---------- F. 黎湛铁路：兴业站（贵港-玉林之间）、文地站（陆川之后） ----------
insert_in_line("黎湛铁路", "兴业站", after="贵港站")
insert_in_line("黎湛铁路", "文地站", after="陆川站")
ensure_station("兴业站", "广西玉林市", "黎湛铁路")
ensure_station("文地站", "广西玉林市", "黎湛铁路")
print("F 黎湛铁路:", LINE_ORDER["黎湛铁路"])

# ---------- G. 玉铁铁路：全新线（玉林-博白） ----------
LINE_ORDER["玉铁铁路"] = ["玉林站", "博白站"]
union_line("玉林站", "玉铁铁路")
ensure_station("博白站", "广西玉林市", "玉铁铁路")
print("G 玉铁铁路:", LINE_ORDER["玉铁铁路"])

# ---------- 重建 GRAPH（增量加边） ----------
def edges_of(order):
    e = set()
    for s in order.values():
        for a, b in zip(s, s[1:]):
            e.add(frozenset((a, b)))
    return e

old_edges = edges_of(R.LINE_ORDER)
new_edges = edges_of(LINE_ORDER)
to_add = new_edges - old_edges
print("新增边:", sorted([tuple(e) for e in to_add]))
gset = {k: set(v) for k, v in R.GRAPH.items()}
for fr in to_add:
    a, b = tuple(fr)
    gset.setdefault(a, set()).add(b)
    gset.setdefault(b, set()).add(a)
for s in STATION_INFO:
    gset.setdefault(s, set())
GRAPH = {k: sorted(v) for k, v in gset.items()}

# ---------- 生成 META ----------
META = {
    "version": "2.9",
    "sources": R.META.get("sources", []) + ["广西壮族自治区补充站点总表.xlsx"],
    "generated_at": "2026-07-26",
    "line_count": len(LINE_ORDER),
    "station_count": len(STATION_INFO),
    "note": "v2.9 广西补充站点合并：17站(南凭高铁崇凭段4/湘桂普速宁明/衡柳全州南·兴安北/焦柳三江·融水·罗城/益湛富川·容县·北流/黎湛兴业·文地/玉铁博白)增量插入既有线或新建玉铁铁路；南凭高速铁路（南崇段）延伸并重命名为南凭高速铁路。仅增量合并，未删除任何原有边"
}

# ---------- 重写 railway_data.py（原地 replace_line，避免重复 GRAPH） ----------
with open(SRC, "r", encoding="utf-8") as f:
    lines = f.read().split("\n")

lines[1] = "# 整理后的全国铁路数据层 v2.9（广西补充站点合并，自动生成，请勿手动编辑）"
lines[2] = "# 生成时间：2026-07-26"

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

print("LINE_ORDER lines:", len(LINE_ORDER))
print("STATION_INFO stations:", len(STATION_INFO))
print("GRAPH nodes:", len(GRAPH))

# ---------- 同步 4 个 JSON ----------
DATA = "data"
os.makedirs(DATA, exist_ok=True)
json.dump(LINE_ORDER, open(os.path.join(DATA, "lines_order.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
json.dump(GRAPH, open(os.path.join(DATA, "graph_adjacency.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
json.dump(STATION_INFO, open(os.path.join(DATA, "station_info.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
json.dump(CITY_TO_STATIONS, open(os.path.join(DATA, "city_to_stations.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
print("4 JSON synced.")
