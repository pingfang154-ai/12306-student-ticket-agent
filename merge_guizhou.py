# -*- coding: utf-8 -*-
# 贵州省补充站点总表 合并脚本 v2.5 -> v2.6
import importlib.util, json, shutil, re, os

SRC = "src/railway_data.py"
BAK = "src/railway_data_v2.5.bak"
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
    """加入新站；若已存在则并集 lines。"""
    if name in STATION_INFO:
        cur = set(STATION_INFO[name].get("lines", []))
        cur.update(lines)
        STATION_INFO[name]["lines"] = sorted(cur)
    else:
        STATION_INFO[name] = {"province": prov, "city": city, "lines": sorted(lines)}
    # CITY_TO_STATIONS
    CITY_TO_STATIONS.setdefault(city, [])
    if name not in CITY_TO_STATIONS[city]:
        CITY_TO_STATIONS[city].append(name)
    # PROVINCE_TO_STATIONS
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

def derive_alias(city):
    s = city
    for suf in ["布依族苗族自治州","土家族苗族自治州","彝族自治州","白族自治州","维吾尔自治区","壮族自治区","回族自治区","自治区","自治县","自治州","地区","市","州","区","县","盟"]:
        if s.endswith(suf):
            s = s[:-len(suf)]; break
    return s

PROV = "贵州"

# ---------- 1. 水红铁路（整段重建，六盘水→红果） ----------
shuihong = ["六盘水站","玉舍站","白鸡坡站","都格站","发耳站","营街站","茅草坪站","三家寨站","雨格站","松河站","柏果站","月亮田站","盘关站","花家庄站","沙沱站","红果站"]
LINE_ORDER["水红铁路"] = shuihong
for s in shuihong:
    if s in STATION_INFO:
        union_line(s, "水红铁路")
    else:
        add_station(s, PROV, "六盘水市", ["水红铁路"])
# 六盘水市 alias
ensure_alias("六盘水市", "六盘水")

# ---------- 2. 威红铁路（整段重建，红果→威舍） ----------
weihong = ["红果站","上西铺站","鲁番站","威箐站","小雨谷站","瓦窑田站","新坪田站","威舍站"]
LINE_ORDER["威红铁路"] = weihong
for s in weihong:
    if s in STATION_INFO:
        union_line(s, "威红铁路")
    else:
        add_station(s, PROV, "黔西南布依族苗族自治州", ["威红铁路"])
ensure_alias("黔西南布依族苗族自治州", "黔西南")

# ---------- 3. 盘西铁路（红果→平关）+ 合成 富源-平关 ----------
pandi = ["红果站","平关站"]
LINE_ORDER["盘西铁路"] = pandi
union_line("红果站", "盘西铁路")
if "平关站" in STATION_INFO:
    union_line("平关站", "盘西铁路")
    union_line("平关站", "盘西铁路__SYN__富源__平关")
    union_line("富源站", "盘西铁路__SYN__富源__平关")
else:
    add_station("平关站", PROV, "六盘水市", ["盘西铁路","盘西铁路__SYN__富源__平关"])
    union_line("富源站", "盘西铁路__SYN__富源__平关")
LINE_ORDER["盘西铁路__SYN__富源__平关"] = ["富源站","平关站"]

# ---------- 4. 沪昆铁路（贵昆线）：葡萄菁-梅花山 合成 ----------
if "葡萄菁站" in STATION_INFO:
    union_line("葡萄菁站", "沪昆铁路（贵昆线）__SYN__葡萄菁__梅花山")
    union_line("梅花山站", "沪昆铁路（贵昆线）__SYN__葡萄菁__梅花山")
else:
    add_station("葡萄菁站", PROV, "毕节市", ["沪昆铁路（贵昆线）__SYN__葡萄菁__梅花山"])
    union_line("梅花山站", "沪昆铁路（贵昆线）__SYN__葡萄菁__梅花山")
LINE_ORDER["沪昆铁路（贵昆线）__SYN__葡萄菁__梅花山"] = ["葡萄菁站","梅花山站"]
ensure_alias("毕节市", "毕节")

# ---------- 5. 贵阳环线铁路（市域快铁）：插入 孟关/花溪南/花溪大学城 ----------
ring = LINE_ORDER["贵阳环线铁路（市域快铁）"]
# 当前: [双龙南, 党武, 天河潭, 湖潮东, 金华镇, 金阳南, 白云西]
i = ring.index("双龙南站") if "双龙南站" in ring else 0
insert = ["孟关站","花溪南站","花溪大学城站"]
ring[i+1:i+1] = insert
LINE_ORDER["贵阳环线铁路（市域快铁）"] = ring
for s in insert:
    if s in STATION_INFO:
        union_line(s, "贵阳环线铁路（市域快铁）")
    else:
        add_station(s, PROV, "贵阳市", ["贵阳环线铁路（市域快铁）"])
ensure_alias("贵阳市", "贵阳")
# 花溪大学城 贵安新区 -> 贵阳市 (已归贵阳市)；确保 贵安站同城市名一致性
# 龙洞堡 东北环 合成 龙洞堡-贵阳东
if "龙洞堡站" in STATION_INFO:
    union_line("龙洞堡站", "贵阳环线铁路（东北环）__SYN__龙洞堡__贵阳东")
    union_line("贵阳东站", "贵阳环线铁路（东北环）__SYN__龙洞堡__贵阳东")
else:
    add_station("龙洞堡站", PROV, "贵阳市", ["贵阳环线铁路（东北环）__SYN__龙洞堡__贵阳东"])
    union_line("贵阳东站", "贵阳环线铁路（东北环）__SYN__龙洞堡__贵阳东")
LINE_ORDER["贵阳环线铁路（东北环）__SYN__龙洞堡__贵阳东"] = ["龙洞堡站","贵阳东站"]

# ---------- 6. 南昆铁路（贵州段）：册亨-安龙-革居-岔江-威舍 合成 ----------
nanning_guizhou = ["册亨站","安龙站","革居站","岔江站","威舍站"]
LINE_ORDER["南昆铁路（贵州段）"] = nanning_guizhou
for s in ["册亨站","安龙站","革居站","岔江站"]:
    if s in STATION_INFO:
        union_line(s, "南昆铁路（贵州段）")
    else:
        add_station(s, PROV, "黔西南布依族苗族自治州", ["南昆铁路（贵州段）"])
union_line("威舍站", "南昆铁路（贵州段）")

# ---------- 7. 织毕/黄织/织纳 集群（经 织金 接 毕节） ----------
# 织金（接轨站）
add_station("织金站", PROV, "毕节市", ["织毕铁路__SYN__大方南__织金","黄织铁路__SYN__普定__织金","织纳铁路__SYN__织金__纳雍"])
add_station("大方南站", PROV, "毕节市", ["织毕铁路__SYN__大方南__织金"])
add_station("普定站", PROV, "安顺市", ["黄织铁路__SYN__普定__织金"])
add_station("纳雍站", PROV, "毕节市", ["织纳铁路__SYN__织金__纳雍"])
ensure_alias("安顺市", "安顺")
# 合成联络线
LINE_ORDER["织毕铁路__SYN__大方南__织金"] = ["大方南站","织金站"]
LINE_ORDER["黄织铁路__SYN__普定__织金"] = ["普定站","织金站"]
LINE_ORDER["织纳铁路__SYN__织金__纳雍"] = ["织金站","纳雍站"]
LINE_ORDER["织毕铁路__SYN__织金__毕节"] = ["织金站","毕节站"]
union_line("毕节站", "织毕铁路__SYN__织金__毕节")
union_line("普定站", "黄织铁路__SYN__普定__织金")
union_line("纳雍站", "织纳铁路__SYN__织金__纳雍")
union_line("大方南站", "织毕铁路__SYN__大方南__织金")

# ---------- 8. 成贵高速铁路：插入 清镇西（黔西<->白云北） ----------
cg = LINE_ORDER["成贵高速铁路"]
i = cg.index("黔西站")
# 黔西站 后插入 清镇西站
cg.insert(i+1, "清镇西站")
LINE_ORDER["成贵高速铁路"] = cg
if "清镇西站" in STATION_INFO:
    union_line("清镇西站", "成贵高速铁路")
else:
    add_station("清镇西站", PROV, "贵阳市", ["成贵高速铁路"])
union_line("黔西站", "成贵高速铁路")
union_line("白云北站", "成贵高速铁路")

# ---------- 9. 渝贵铁路：插入 修文县（息烽<->贵阳北） ----------
yg = LINE_ORDER["渝贵铁路"]
i = yg.index("息烽站")
yg.insert(i+1, "修文县站")
LINE_ORDER["渝贵铁路"] = yg
if "修文县站" in STATION_INFO:
    union_line("修文县站", "渝贵铁路")
else:
    add_station("修文县站", PROV, "贵阳市", ["渝贵铁路"])
union_line("息烽站", "渝贵铁路")
union_line("贵阳北站", "渝贵铁路")

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
gset = {k: set(v) for k, v in R.GRAPH.items()}
for fr in to_add:
    a, b = tuple(fr)
    gset.setdefault(a, set()).add(b)
    gset.setdefault(b, set()).add(a)
# 确保所有新站入图
for s in STATION_INFO:
    gset.setdefault(s, set())
GRAPH = {k: sorted(v) for k, v in gset.items()}

# ---------- 生成 META ----------
new_line_count = len(LINE_ORDER)
new_station_count = len(STATION_INFO)
META = {
    "version": "2.6",
    "sources": R.META.get("sources", []) + ["贵州省补充站点总表.xlsx"],
    "generated_at": "2026-07-26",
    "line_count": new_line_count,
    "station_count": new_station_count,
    "note": "v2.6 合并贵州省补充站点（35站/12线）：整段重建水红铁路、威红铁路；贵阳环线/成贵/渝贵插入；8条合成联络线连接孤立站（平关、葡萄菁、龙洞堡、南昆贵州段、织毕/黄织/织纳集群）；增量合并，未删除任何原有边"
}

# ---------- 重写 railway_data.py ----------
with open(SRC, "r", encoding="utf-8") as f:
    lines = f.read().split("\n")

# 更新注释头
lines[1] = "# 整理后的全国铁路数据层 v2.6（追加贵州省补充站点，自动生成，请勿手动编辑）"
lines[2] = "# 生成时间：2026-07-26"
lines[3] = "# 数据来源：既有 v2.5 数据源 + 贵州省补充站点总表.xlsx"

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
json.dump(LINE_ORDER, open(os.path.join(DATA,"lines_order.json"),"w",encoding="utf-8"), ensure_ascii=False, indent=1)
json.dump(GRAPH, open(os.path.join(DATA,"graph_adjacency.json"),"w",encoding="utf-8"), ensure_ascii=False, indent=1)
json.dump(STATION_INFO, open(os.path.join(DATA,"station_info.json"),"w",encoding="utf-8"), ensure_ascii=False, indent=1)
json.dump(CITY_TO_STATIONS, open(os.path.join(DATA,"city_to_stations.json"),"w",encoding="utf-8"), ensure_ascii=False, indent=1)
print("4 JSON synced.")
