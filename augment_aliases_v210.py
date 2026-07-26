# -*- coding: utf-8 -*-
# 增强：为 CITY_TO_STATIONS 所有城市键补充「双格式」别名，使 resolve_location 同时接受
#   * 广西前缀格式：广西南宁市 <-> 南宁市
#   * 省份+ Prefecture 格式：长沙市 <-> 湖南长沙市
# 仅修改 CITY_ALIAS（不触及其它字典、不删边），CITY_ALIAS 不在 4 个 JSON 同步范围内，仅写 railway_data.py。
import importlib.util, json, re
SRC = "src/railway_data.py"
spec = importlib.util.spec_from_file_location("rd", SRC)
R = importlib.util.module_from_spec(spec); spec.loader.exec_module(R)

LINE_ORDER = R.LINE_ORDER
STATION_INFO = R.STATION_INFO
CITY_TO_STATIONS = R.CITY_TO_STATIONS
PROVINCE_TO_STATIONS = R.PROVINCE_TO_STATIONS
CITY_ALIAS = dict(R.CITY_ALIAS)
GRAPH = R.GRAPH
META = R.META

added = []
for K in list(CITY_TO_STATIONS.keys()):
    if K.startswith('广西') or K.startswith('广东省') or K.startswith('湖南省') or K.startswith('香港特别行政区'):
        # 广西前缀 -> 裸 Prefecture 别名
        bare = K[2:] if K.startswith('广西') else (K[3:] if K.startswith('广东省') else (K[3:] if K.startswith('湖南省') else None))
        if bare and bare not in CITY_ALIAS and bare not in CITY_TO_STATIONS:
            CITY_ALIAS[bare] = K; added.append((bare, K))
        # 同时补 省份+Prefecture（广东/湖南）
        if K.startswith('广东') or K.startswith('湖南'):
            prov = '广东' if K.startswith('广东') else '湖南'
            alias2 = prov + K
            if alias2 not in CITY_ALIAS:
                CITY_ALIAS[alias2] = K; added.append((alias2, K))
    else:
        # 裸 Prefecture（如 长沙市/广州市/武汉市…）-> 省份+Prefecture 别名
        # 取该城市任一车站的 province
        prov = None
        for st in CITY_TO_STATIONS[K]:
            if st in STATION_INFO and STATION_INFO[st].get('province'):
                prov = STATION_INFO[st]['province']; break
        if prov:
            alias2 = prov + K
            if alias2 not in CITY_ALIAS:
                CITY_ALIAS[alias2] = K; added.append((alias2, K))
        # 裸 Prefecture 去"市"短名（如 长沙）已多由既有别名覆盖，setdefault 补充
        short = K[:-1] if K.endswith('市') else K
        if short not in CITY_ALIAS and short != K:
            CITY_ALIAS[short] = K; added.append((short, K))

print("added aliases:", len(added))
for a in added[:30]:
    print("  ", a[0], "->", a[1])

with open(SRC, "r", encoding="utf-8") as f:
    lines = f.read().split("\n")
def replace_line(name, value):
    for idx, ln in enumerate(lines):
        if re.match(r"^" + re.escape(name) + r"\s*=\s*", ln):
            lines[idx] = name + " = " + value
            return idx
    raise RuntimeError("未找到 " + name)
replace_line("CITY_ALIAS", json.dumps(CITY_ALIAS, ensure_ascii=False))
with open(SRC, "w", encoding="utf-8") as f:
    f.write("\n".join(lines) + "\n")
print("CITY_ALIAS updated in railway_data.py")
