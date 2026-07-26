# -*- coding: utf-8 -*-
# 湖北省补充站点总表 合并脚本 v2.6 -> v2.7
import importlib.util, json, shutil, re, os

SRC = "src/railway_data.py"
BAK = "src/railway_data_v2.6.bak"
shutil.copyfile(SRC, BAK)
print("backup ->", BAK)

spec = importlib.util.spec_from_file_location("rd", SRC)
R = importlib.util.module_from_spec(spec); spec.loader.exec_module(R)

LINE_ORDER = {k: list(v) for k, v in R.LINE_ORDER.items()}
STATION_INFO = {k: dict(v) for k, v in R.STATION_INFO.items()}
CITY_TO_STATIONS = {k: list(v) for k, v in R.CITY_TO_STATIONS.items()}
PROVINCE_TO_STATIONS = {k: list(v) for k, v in R.PROVINCE_TO_STATIONS.items()}
CITY_ALIAS = dict(R.CITY_ALIAS)

def add_station(name, prov, city, lines):
    if name in STATION_INFO:
        cur = set(STATION_INFO[name].get("lines", []))
        cur.update(lines)
        STATION_INFO[name]["lines"] = sorted(cur)
        # 城市可能变更（如新站），保持 city 同步
        STATION_INFO[name]["city"] = city
        STATION_INFO[name]["province"] = prov
    else:
        STATION_INFO[name] = {"province": prov, "city": city, "lines": sorted(lines)}
    CITY_TO_STATIONS.setdefault(city, [])
    if name not in CITY_TO_STATIONS[city]:
        CITY_TO_STATIONS[city].append(name)
    PROVINCE_TO_STATIONS.setdefault(prov, [])
    if city not in PROVINCE_TO_STATIONS[prov]:
        PROVINCE_TO_STATIONS[prov].append(city)

def union_line(station, line):
    if station in STATION_INFO:
        cur = set(STATION_INFO[station].get("lines", []))
        cur.add(line)
        STATION_INFO[station]["lines"] = sorted(cur)

def ensure_alias(full, short):
    if full == short: return
    if short not in CITY_ALIAS and short not in CITY_TO_STATIONS:
        CITY_ALIAS[short] = full

PROV = "湖北"

ADDED = []  # 记录新增站

def new_station(name, prov, city, lines):
    add_station(name, prov, city, lines)
    ADDED.append(name)

# =================== A. 既有线精确插入 / 整段重建 ===================

# 1. 宜万铁路：野三关站 插在 巴东站 <-> 高坪站 之间（地理正确；
#    Excel 标注"前一站=长阳站"，但真实走向为 长阳→巴东→野三关→高坪，故依地理置于巴东之后）
yw = LINE_ORDER["宜万铁路"]
i_bd = yw.index("巴东站")
yw.insert(i_bd + 1, "野三关站")
LINE_ORDER["宜万铁路"] = yw
new_station("野三关站", PROV, "恩施土家族苗族自治州", ["宜万铁路"])
union_line("巴东站", "宜万铁路")
union_line("高坪站", "宜万铁路")
ensure_alias("恩施土家族苗族自治州", "恩施")

# 2. 西十高速铁路：重建为 [西安东, 蓝田, 商洛西, 山阳, 漫川关, 郧西站, 十堰东站]
xishi = ["西安东站","蓝田站","商洛西站","山阳站","漫川关站","郧西站","十堰东站"]
LINE_ORDER["西十高速铁路"] = xishi
for s in xishi:
    if s in STATION_INFO:
        union_line(s, "西十高速铁路")
    else:
        new_station(s, PROV, "十堰市", ["西十高速铁路"])
ensure_alias("十堰市", "十堰")

# 3. 汉丹铁路：襄州站 插在 襄阳站 <-> 汉口站 之间（襄阳之后）
hd = LINE_ORDER["汉丹铁路"]
i_xy = hd.index("襄阳站")
hd.insert(i_xy + 1, "襄州站")
LINE_ORDER["汉丹铁路"] = hd
new_station("襄州站", PROV, "襄阳市", ["汉丹铁路"])
union_line("襄阳站", "汉丹铁路")
union_line("汉口站", "汉丹铁路")
ensure_alias("襄阳市", "襄阳")

# 4. 长荆铁路：整段重建为 [天门站, 应城站, 京山站, 钟祥站, 荆门站]
cj = ["天门站","应城站","京山站","钟祥站","荆门站"]
LINE_ORDER["长荆铁路"] = cj
# 应城属孝感市，京山/钟祥属荆门市
new_station("应城站", PROV, "孝感市", ["长荆铁路"])
new_station("京山站", PROV, "荆门市", ["长荆铁路"])
new_station("钟祥站", PROV, "荆门市", ["长荆铁路"])
union_line("天门站", "长荆铁路")
union_line("荆门站", "长荆铁路")
ensure_alias("孝感市", "孝感")
ensure_alias("荆门市", "荆门")

# 5. 京九铁路：浠水站 插在 黄州站 <-> 蕲春站 之间（横车站缺，直接相接）
jj = LINE_ORDER["京九铁路"]
i_hz = jj.index("黄州站")
jj.insert(i_hz + 1, "浠水站")
LINE_ORDER["京九铁路"] = jj
new_station("浠水站", PROV, "黄冈市", ["京九铁路"])
union_line("黄州站", "京九铁路")
union_line("蕲春站", "京九铁路")
ensure_alias("黄冈市", "黄冈")

# 6. 合九铁路：黄梅站 插在 宿松站 之后
hj = LINE_ORDER["合九铁路"]
i_ss = hj.index("宿松站")
hj.insert(i_ss + 1, "黄梅站")
LINE_ORDER["合九铁路"] = hj
new_station("黄梅站", PROV, "黄冈市", ["合九铁路"])
union_line("宿松站", "合九铁路")

# 7. 黔常铁路：整段重建为 [黔江站, 咸丰站, 来凤站, 张家界西站]（龙山北缺，来凤直连张家界西）
qc = ["黔江站","咸丰站","来凤站","张家界西站"]
LINE_ORDER["黔常铁路"] = qc
for s in ["咸丰站","来凤站"]:
    new_station(s, PROV, "恩施土家族苗族自治州", ["黔常铁路"])
union_line("黔江站", "黔常铁路")
union_line("张家界西站", "黔常铁路")

# =================== B. 合成 2 站联络线（孤立站接已有锚点） ===================

# 8. 焦柳铁路：宜城南站 接 襄阳站
LINE_ORDER["__SYN__焦柳铁路__襄阳站__宜城南站"] = ["襄阳站","宜城南站"]
new_station("宜城南站", PROV, "襄阳市", ["焦柳铁路","__SYN__焦柳铁路__襄阳站__宜城南站"])
union_line("襄阳站", "焦柳铁路")
union_line("襄阳站", "__SYN__焦柳铁路__襄阳站__宜城南站")
# 焦柳铁路 主线也补 宜城南 归属
union_line("宜城南站", "焦柳铁路")

# 9. 焦柳铁路：当阳站 接 荆门站
LINE_ORDER["__SYN__焦柳铁路__荆门站__当阳站"] = ["荆门站","当阳站"]
new_station("当阳站", PROV, "宜昌市", ["焦柳铁路","__SYN__焦柳铁路__荆门站__当阳站"])
union_line("荆门站", "焦柳铁路")
union_line("荆门站", "__SYN__焦柳铁路__荆门站__当阳站")
union_line("当阳站", "焦柳铁路")
ensure_alias("宜昌市", "宜昌")

# 10. 襄渝铁路：谷城站 接 十堰站
LINE_ORDER["__SYN__襄渝铁路__十堰站__谷城站"] = ["十堰站","谷城站"]
new_station("谷城站", PROV, "襄阳市", ["襄渝铁路","__SYN__襄渝铁路__十堰站__谷城站"])
union_line("十堰站", "襄渝铁路")
union_line("十堰站", "__SYN__襄渝铁路__十堰站__谷城站")
union_line("谷城站", "襄渝铁路")

# 11. 京广铁路：花园站 接 孝感站
LINE_ORDER["__SYN__京广铁路__孝感站__花园站"] = ["孝感站","花园站"]
new_station("花园站", PROV, "孝感市", ["京广铁路","__SYN__京广铁路__孝感站__花园站"])
union_line("孝感站", "京广铁路")
union_line("孝感站", "__SYN__京广铁路__孝感站__花园站")
union_line("花园站", "京广铁路")

# =================== C. 全新线路（端点已在库或同步新增） ===================

# 12. 荆荆高速铁路：[荆州站, 沙洋西站, 荆门西站]
LINE_ORDER["荆荆高速铁路"] = ["荆州站","沙洋西站","荆门西站"]
new_station("沙洋西站", PROV, "荆门市", ["荆荆高速铁路"])
union_line("荆州站", "荆荆高速铁路")
union_line("荆门西站", "荆荆高速铁路")

# 13. 黄黄高速铁路：[黄冈东站, 浠水南站, 武穴北站, 黄梅东站, 宿松东站]（蕲春南缺，浠水南直连武穴北）
LINE_ORDER["黄黄高速铁路"] = ["黄冈东站","浠水南站","武穴北站","黄梅东站","宿松东站"]
for s in ["浠水南站","武穴北站","黄梅东站"]:
    new_station(s, PROV, "黄冈市", ["黄黄高速铁路"])
union_line("黄冈东站", "黄黄高速铁路")
union_line("宿松东站", "黄黄高速铁路")

# 14. 武仙城际铁路：[天门南站, 仙桃站]（大福站不办客，经天门南接入汉宜网）
LINE_ORDER["武仙城际铁路"] = ["天门南站","仙桃站"]
new_station("仙桃站", PROV, "仙桃市", ["武仙城际铁路"])
union_line("天门南站", "武仙城际铁路")
ensure_alias("仙桃市", "仙桃")

# 15. 麻武铁路（武麻联络线）：[红安站, 麻城站]（横店站缺，红安直连麻城）
LINE_ORDER["麻武铁路（武麻联络线）"] = ["红安站","麻城站"]
new_station("红安站", PROV, "黄冈市", ["麻武铁路（武麻联络线）"])
union_line("麻城站", "麻武铁路（武麻联络线）")

# =================== 重建 GRAPH（增量加边） ===================
def edges_of(order):
    e = set()
    for seq in order.values():
        for a, b in zip(seq, seq[1:]):
            e.add(frozenset((a, b)))
    return e

old_edges = edges_of(R.LINE_ORDER)
new_edges = edges_of(LINE_ORDER)
to_add = new_edges - old_edges
gset = {k: set(v) for k, v in R.GRAPH.items()}
for fr in to_add:
    a, b = tuple(fr)
    gset.setdefault(a, set()).add(b)
    gset.setdefault(b, set()).add(a)
for s in STATION_INFO:
    gset.setdefault(s, set())
GRAPH = {k: sorted(v) for k, v in gset.items()}

# =================== 生成 META ===================
new_line_count = len(LINE_ORDER)
new_station_count = len(STATION_INFO)
META = {
    "version": "2.7",
    "sources": R.META.get("sources", []) + ["湖北省补充站点总表.xlsx"],
    "generated_at": "2026-07-26",
    "line_count": new_line_count,
    "station_count": new_station_count,
    "note": "v2.7 合并湖北省补充站点总表（20新站/15线操作：7条既有线精确插入+重建、4条合成2站联络线、4条全新线路）；武宜段8站已在v2.3并入，不重复；枝江北/蕲春为既有库存，跳过；增量合并，未删除任何原有边"
}

# =================== 重写 railway_data.py（就地替换 7 个单行 dict + 注释头） ===================
with open(SRC, "r", encoding="utf-8") as f:
    lines = f.read().split("\n")

lines[1] = "# 整理后的全国铁路数据层 v2.7（追加湖北省补充站点，自动生成，请勿手动编辑）"
lines[2] = "# 生成时间：2026-07-26"
lines[3] = "# 数据来源：既有 v2.6 数据源 + 湖北省补充站点总表.xlsx"

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
print("新增站数:", len(ADDED))
print("新增站:", ADDED)

# =================== 同步 4 个 JSON ===================
DATA = "data"
os.makedirs(DATA, exist_ok=True)
json.dump(LINE_ORDER, open(os.path.join(DATA,"lines_order.json"),"w",encoding="utf-8"), ensure_ascii=False, indent=1)
json.dump(GRAPH, open(os.path.join(DATA,"graph_adjacency.json"),"w",encoding="utf-8"), ensure_ascii=False, indent=1)
json.dump(STATION_INFO, open(os.path.join(DATA,"station_info.json"),"w",encoding="utf-8"), ensure_ascii=False, indent=1)
json.dump(CITY_TO_STATIONS, open(os.path.join(DATA,"city_to_stations.json"),"w",encoding="utf-8"), ensure_ascii=False, indent=1)
print("4 JSON synced.")
