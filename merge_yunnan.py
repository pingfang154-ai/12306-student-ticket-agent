# -*- coding: utf-8 -*-
"""云南省补充站点增量合并到 railway_data.py (v2.3 -> v2.4)
原则：增量、只加不删；Dijkstra 只走 LINE_ORDER 派生边，新连接必须以线路形式存在。
"""
import importlib.util, json, os, shutil, copy, datetime

SRC = r"C:\Users\cjp15\Desktop\全国客运站点\交接文件夹第三版（含一、二合并）\src\railway_data.py"
DATA = r"C:\Users\cjp15\Desktop\全国客运站点\交接文件夹第三版（含一、二合并）\data"
BAK = SRC[:-3] + "_v2.3.bak"

# 1) 备份
if not os.path.exists(BAK):
    shutil.copy(SRC, BAK)
    print("backup ->", BAK)

# 2) 载入当前模块
spec = importlib.util.spec_from_file_location("rd", SRC)
R = importlib.util.module_from_spec(spec); spec.loader.exec_module(R)

LINE_ORDER = {k: list(v) for k, v in R.LINE_ORDER.items()}
STATION_INFO = copy.deepcopy(R.STATION_INFO)
CITY_TO_STATIONS = copy.deepcopy(R.CITY_TO_STATIONS)
PROVINCE_TO_STATIONS = copy.deepcopy(R.PROVINCE_TO_STATIONS)
CITY_ALIAS = copy.deepcopy(R.CITY_ALIAS)
GRAPH = {k: set(v) for k, v in R.GRAPH.items()}

changes = []   # 变更日志
def log(msg): changes.append(msg)

log("=== 云南省补充站点合并 (v2.3 -> v2.4) ===")
log("合并时间: " + datetime.date.today().isoformat())
log("冲突优先级策略: ① 仅增量、只加不删，绝不移除既有边/站/城市；")
log("  ② 补充站若已在库(同名)则并集其线路归属并保留既有城市，否则新增；")
log("  ③ 前/后一站引用的相邻站若不在补充表中、且为保持线路拓扑连续所必需，")
log("     作为'连通中转节点'补入(均属真实车站)；否则以最近的已入库锚点做合成联络线。")

# 3) 新增站点 (27 站，来自补充表)
NEW_STATIONS = {
    "小中甸站":   ("云南", "香格里拉市", "丽香铁路（滇藏铁路丽香段）", "丽香铁路；办理客货运"),
    "香格里拉站": ("云南", "香格里拉市", "丽香铁路（滇藏铁路丽香段）", "丽香铁路终点站；办理客运"),
    "曲江站":     ("云南", "红河哈尼族彝族自治州", "昆玉河铁路", "玉蒙段；办理旅客乘降及整车货物到发"),
    "小湾东站":   ("云南", "大理白族自治州", "大临铁路", "大临铁路；办理客运业务"),
    "班猫箐站":   ("云南", "昆明市", "南昆铁路（普速）", "乘降所(慢火车旅客乘降)"),
    "施家嘴站":   ("云南", "昆明市", "南昆铁路（普速）", "乘降所(慢火车旅客乘降)"),
    "西街口站":   ("云南", "昆明市", "南昆铁路（普速）", "乘降所"),
    "昆阳站":     ("云南", "昆明市", "昆玉铁路", "昆玉铁路终点；2026-02-20 恢复客运"),
    "小新街站":   ("云南", "昆明市", "沪昆铁路（普速）", "贵昆线；5651/5652 慢火车停靠(电子客票)"),
    "杨林站":     ("云南", "昆明市", "沪昆铁路（普速）", "贵昆线；客货运站"),
    "宜良北站":   ("云南", "昆明市", "南昆铁路（普速）", "办理旅客乘降、行包托运及货运"),
    "小哨站":     ("云南", "昆明市", "沪昆铁路（普速）", "贵昆线；5651/5652 慢火车停靠"),
    "七甸站":     ("云南", "昆明市", "南昆铁路（普速）", "乘降所"),
    "宜耐站":     ("云南", "昆明市", "南昆铁路（普速）", "五等站；办理旅客乘降"),
    "广卫南站":   ("云南", "昆明市", "南昆铁路（普速）", "即广南卫站(车站代码 48797)；五等站"),
    "永丰营站":   ("云南", "昆明市", "南昆铁路（普速）", "五等站；办理旅客乘降"),
    "乐善村站":   ("云南", "昆明市", "南昆铁路（普速）", "办理旅客乘降"),
    "茂舍祖站":   ("云南", "昆明市", "南昆铁路（普速）", "办理旅客乘降"),
    "阿南庄站":   ("云南", "楚雄彝族自治州", "成昆铁路（含复线）", "元昆段；五等站"),
    "龙骨甸站":   ("云南", "楚雄彝族自治州", "成昆铁路（含复线）", "元昆段；乘降所"),
    "龙塘坝站":   ("云南", "楚雄彝族自治州", "成昆铁路（含复线）", "元昆段；乘降所"),
    "小村站":     ("云南", "楚雄彝族自治州", "成昆铁路（含复线）", "元昆段；乘降所"),
    "小月旧站":   ("云南", "楚雄彝族自治州", "成昆铁路（含复线）", "元昆段；乘降所"),
    "尹地站":     ("云南", "楚雄彝族自治州", "成昆铁路（含复线）", "元昆段；乘降所"),
    "羊臼河站":   ("云南", "楚雄彝族自治州", "成昆铁路（含复线）", "元昆段；乘降所"),
    "甸心站":     ("云南", "楚雄彝族自治州", "成昆铁路（含复线）", "元昆段；五等站"),
    "蒲缥站":     ("云南", "保山市", "大瑞铁路（大保段）", "大瑞铁路；客货运站(2026-04-15 开客)"),
}

# 连通中转节点 (不在补充表，但为保持线路相邻连续所必需的真实车站)
CONNECTORS = {
    "拉市海站":   ("云南", "丽江市", "丽香铁路（滇藏铁路丽香段）"),
    "王家营西站": ("云南", "昆明市", "南昆铁路（普速）"),
    "石林南站":   ("云南", "昆明市", "南昆铁路（普速）"),
    "晋宁东站":   ("云南", "昆明市", "昆玉铁路"),
}

# 4) 写入 STATION_INFO
def add_station(name, province, city, line, code=None):
    if name in STATION_INFO:
        if line not in STATION_INFO[name]["lines"]:
            STATION_INFO[name]["lines"].append(line)
        log(f"  [更新] {name}: lines += {line} (既有站补归属)")
    else:
        info = {"province": province, "city": city, "lines": [line]}
        if code:
            info["code"] = code
        STATION_INFO[name] = info
        log(f"  [新增] {name}: province={province}, city={city}, lines=[{line}]" + (f", code={code}" if code else ""))

for nm, (prov, city, line, note) in NEW_STATIONS.items():
    code = "48797" if nm == "广卫南站" else None
    add_station(nm, prov, city, line, code)

for nm, (prov, city, line) in CONNECTORS.items():
    add_station(nm, prov, city, line)
    log(f"  [连通节点] {nm}: 补充表未单列，但为线路相邻连续所必需的真实车站")

# 5) 既有锚点站补线路归属
def add_line_to(name, line):
    if name in STATION_INFO:
        if line not in STATION_INFO[name]["lines"]:
            STATION_INFO[name]["lines"].append(line)
            log(f"  [锚点补线] {name}: lines += {line}")

add_line_to("丽江站", "丽香铁路（滇藏铁路丽香段）")
add_line_to("昆明站", "昆玉铁路")

# 6) CITY_TO_STATIONS
def add_city_station(city, name):
    lst = CITY_TO_STATIONS.setdefault(city, [])
    if name not in lst:
        lst.append(name)
        log(f"  [同城映射] {city} += {name}")

for nm, (prov, city, line, note) in NEW_STATIONS.items():
    add_city_station(city, nm)
for nm, (prov, city, line) in CONNECTORS.items():
    add_city_station(city, nm)
# 新城市键
if "香格里拉市" not in CITY_TO_STATIONS:
    log("  [新同城键] 香格里拉市 (迪庆藏族自治州下属，补充表中无既有键)")
# 别名
if "香格里拉" not in CITY_ALIAS:
    CITY_ALIAS["香格里拉"] = "香格里拉市"
    log("  [别名] 香格里拉 -> 香格里拉市")

# 7) PROVINCE_TO_STATIONS['云南']
yn = PROVINCE_TO_STATIONS.setdefault("云南", [])
before = len(yn)
for nm in list(NEW_STATIONS.keys()) + list(CONNECTORS.keys()):
    if nm not in yn:
        yn.append(nm)
log(f"  [省份列表] 云南: {before} -> {len(yn)} 站 (+{len(yn)-before})")

# 8) LINE_ORDER 合并
def splice_after(seq, anchor, block):
    """在 seq 中 anchor 之后插入 block(列表)。anchor 必须存在。"""
    i = seq.index(anchor)
    seq[i+1:i+1] = block

def splice_before(seq, anchor, block):
    i = seq.index(anchor)
    seq[i:i] = block

# A) 丽香铁路（滇藏铁路丽香段）—— 全新线
LINE_ORDER["丽香铁路（滇藏铁路丽香段）"] = ["丽江站", "拉市海站", "小中甸站", "香格里拉站"]
log("  [新线] 丽香铁路（滇藏铁路丽香段） = 丽江-拉市海-小中甸-香格里拉")

# B) 昆玉铁路 —— 全新线 (昆明-晋宁东-昆阳)
LINE_ORDER["昆玉铁路"] = ["昆明站", "晋宁东站", "昆阳站"]
log("  [新线] 昆玉铁路 = 昆明-晋宁东-昆阳")

# C) 昆玉河铁路 —— 曲江 插在 建水 与 个旧 之间
lo = LINE_ORDER["昆玉河铁路"]
splice_after(lo, "建水站", ["曲江站"])
log("  [拼接] 昆玉河铁路: 建水 -> 曲江 -> 个旧 (柿花树/李浩寨为补充表外小站，跳过，以建水为锚点合成连通)")

# D) 大临铁路 —— 小湾东 插在 巍山 与 南涧 之间 (真实顺序: 巍山-小湾东-南涧)
lo = LINE_ORDER["大临铁路"]
splice_after(lo, "巍山站", ["小湾东站"])
log("  [拼接] 大临铁路: 巍山 -> 小湾东 -> 南涧 -> 云县 (小湾东前=巍山 与补充表一致)")

# E) 大瑞铁路（大保段） —— 蒲缥 接在 保山 之后
lo = LINE_ORDER["大瑞铁路（大保段）"]
lo.append("蒲缥站")
log("  [拼接] 大瑞铁路（大保段）: 保山 -> 蒲缥 (蒲缥前=保山，瑞丽方向未开通)")

# F) 南昆铁路（普速） —— 大段插入
lo = LINE_ORDER["南昆铁路（普速）"]
# 昆明侧簇: 王家营西-广卫南-七甸-施家嘴-永丰营-乐善村-宜良北-班猫箐-石林南，再接 石林
splice_after(lo, "昆明站", ["王家营西站", "广卫南站", "七甸站", "施家嘴站", "永丰营站", "乐善村站", "宜良北站", "班猫箐站", "石林南站"])
# 石林-陆良 之间: 茂舍祖-西街口-宜耐
splice_after(lo, "石林站", ["茂舍祖站", "西街口站", "宜耐站"])
log("  [拼接] 南昆铁路（普速）: 昆明-王家营西-广卫南-七甸-施家嘴-永丰营-乐善村-宜良北-班猫箐-石林南-石林-茂舍祖-西街口-宜耐-陆良")
log("         (王家营西/石林南为补充表外相邻真实站，作为连通节点补入)")

# G) 沪昆铁路（普速） —— 小哨-杨林-小新街 插在 昆明 与 曲靖 之间
lo = LINE_ORDER["沪昆铁路（普速）"]
splice_after(lo, "昆明站", ["小哨站", "杨林站", "小新街站"])
log("  [拼接] 沪昆铁路（普速）: 昆明-小哨-杨林-小新街-曲靖 (照福铺为补充表外小站，跳过，以曲靖为锚点合成连通)")

# H) 成昆铁路（含复线） —— 两处拼接
lo = LINE_ORDER["成昆铁路（含复线）"]
# 元谋西 与 黑井 之间: 尹地-小月旧-羊臼河-小村-阿南庄-龙骨甸 (昆山方向: 元谋西->...->黑井)
splice_before(lo, "黑井站", ["尹地站", "小月旧站", "羊臼河站", "小村站", "阿南庄站", "龙骨甸站"])
# 黑井 与 禄丰 之间: 甸心-龙塘坝
splice_after(lo, "黑井站", ["甸心站", "龙塘坝站"])
log("  [拼接] 成昆铁路（含复线）: ...元谋西-尹地-小月旧-羊臼河-小村-阿南庄-龙骨甸-黑井-甸心-龙塘坝-禄丰...")
log("         (甸尾为补充表外小站，龙塘坝前一站跳过，以禄丰为锚点合成连通)")

# 9) GRAPH 增量重建 (保留既有的非线路节点，如 兴义)
def edges_of_lineorder(lod):
    e = set()
    for seq in lod.values():
        for a, b in zip(seq, seq[1:]):
            e.add((a, b)); e.add((b, a))
    return e

edges_lo = edges_of_lineorder(LINE_ORDER)
edges_g = set()
for a, nb in R.GRAPH.items():
    for b in nb:
        edges_g.add((a, b)); edges_g.add((b, a))
to_add = edges_lo - edges_g
for a, b in to_add:
    GRAPH.setdefault(a, set()).add(b)
    GRAPH.setdefault(b, set()).add(a)
log(f"  [GRAPH] 新增边 {len(to_add)} 条；总节点 {len(GRAPH)}")

# 10) 再生 railway_data.py (head + 7 个紧凑字典 + helper 尾部)
with open(SRC, encoding="utf-8") as f:
    all_lines = f.readlines()
idx_first = next(i for i, l in enumerate(all_lines) if l.strip().startswith("META") or l.strip().startswith("LINE_ORDER"))
idx_tail = next(i for i, l in enumerate(all_lines) if l.strip().startswith("LINE_NAME_ALIAS") or "def resolve_location" in l)
head_lines = all_lines[:idx_first]
tail_lines = all_lines[idx_tail:]

def dump(d):
    return json.dumps(d, ensure_ascii=False)

out = []
out.extend(head_lines)
out.append("META = " + dump(R.META) + "\n")
out.append("\n")
out.append("LINE_ORDER = " + dump(LINE_ORDER) + "\n")
out.append("\n")
out.append("STATION_INFO = " + dump(STATION_INFO) + "\n")
out.append("\n")
out.append("CITY_TO_STATIONS = " + dump(CITY_TO_STATIONS) + "\n")
out.append("\n")
out.append("PROVINCE_TO_STATIONS = " + dump(PROVINCE_TO_STATIONS) + "\n")
out.append("\n")
out.append("CITY_ALIAS = " + dump(CITY_ALIAS) + "\n")
out.append("\n")
out.append("GRAPH = " + dump({k: sorted(v) for k, v in GRAPH.items()}) + "\n")
out.append("\n")
out.extend(tail_lines)
if not out[-1].endswith("\n"):
    out[-1] += "\n"

with open(SRC, "w", encoding="utf-8") as f:
    f.write("".join(out))
log("  [文件] railway_data.py 已再生 (head + 7 字典 + helper 尾部)")

# 11) 同步 4 个 JSON
json.dump(LINE_ORDER, open(os.path.join(DATA, "lines_order.json"), "w", encoding="utf-8"), ensure_ascii=False)
json.dump({k: sorted(v) for k, v in GRAPH.items()}, open(os.path.join(DATA, "graph_adjacency.json"), "w", encoding="utf-8"), ensure_ascii=False)
json.dump(STATION_INFO, open(os.path.join(DATA, "station_info.json"), "w", encoding="utf-8"), ensure_ascii=False)
json.dump(CITY_TO_STATIONS, open(os.path.join(DATA, "city_to_stations.json"), "w", encoding="utf-8"), ensure_ascii=False)
log("  [JSON] lines_order / graph_adjacency / station_info / city_to_stations 已同步")

# 12) 写变更日志
with open(r"C:\Users\cjp15\Desktop\全国客运站点\交接文件夹第三版（含一、二合并）\yunnan_merge_changelog.md", "w", encoding="utf-8") as f:
    f.write("\n".join(changes) + "\n")
print("\n".join(changes))
print("\nDONE. 变更日志 -> yunnan_merge_changelog.md")
