# -*- coding: utf-8 -*-
"""
合并山东省、青海省客运铁路线路站点到铁路数据层 (railway_data.py)。
策略：增量、仅追加（绝不删除已有边/车站），保持现有拓扑零回归。

输入：
  - 山东省客运铁路线路站点表.xlsx
  - 青海省客运铁路线路站点表.xlsx  (D:/AI专用/.../)

输出：
  - src/railway_data.py  (重新生成，保留原 helper 函数)
  - data/lines_order.json, data/graph_adjacency.json,
    data/station_info.json, data/city_to_stations.json  (同步)

处理要点：
  1. 车站顺序按 Excel 内 序号 升序（同一线路内）。
  2. 青海站名缺“站”后缀，统一补“站”以契合拓扑命名。
  3. 4 条与现有拓扑重叠的线路做精确拼接：
       济郑高速铁路 : 山东段(济南西…莘县) 前置到 濮阳东 之前
       兰新高速铁路 : 青海段(民和南…浩门) 插入到 民乐 之前
       兰青铁路     : 青海段(西宁…民和) 前置到 兰州站 之前
       格库铁路     : 青海段(格尔木…茫崖镇) 插入到 若羌 之后
  4. 全新线路整条追加；京沪高速铁路山东段已存在则跳过。
  5. GRAPH 仅“追加”新边 = 合并后 LINE_ORDER 邻边 - 原 LINE_ORDER 邻边，
     原 GRAPH 其它边完全保留。
"""
import os, sys, json
from collections import defaultdict

HERE = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.join(HERE, "src")
sys.path.insert(0, SRC)
import railway_data as R
import openpyxl

PROV_PREFIX = {"山东": "山东省", "青海": "青海省"}  # 所属省市 中的省前缀
CITY_SUFFIXES = ["维吾尔自治区", "壮族自治区", "回族自治区", "自治区",
                "白族自治州", "彝族自治州", "土家族苗族自治州",
                "苗族土家族自治县", "地区", "自治州", "自治县", "市", "州", "区", "县", "盟"]


def parse_excel(path):
    """返回 {line: [ {st, prov, city, line} ... 按序 ]}"""
    wb = openpyxl.load_workbook(path, read_only=True, data_only=True)
    ws = wb.active
    rows = list(ws.iter_rows(values_only=True))
    hi = next(i for i, r in enumerate(rows) if r and "线路名称" in r)
    hdr = rows[hi]
    idx = {c: i for i, c in enumerate(hdr)}
    recs = []
    for r in rows[hi + 1:]:
        if not r or not r[idx["车站名称"]]:
            continue
        seq = r[idx["序号"]]
        seq = seq if isinstance(seq, (int, float)) else 0
        prov = str(r[idx["省份"]]).strip()
        city_raw = str(r[idx["所属省市"]]).strip()
        city = city_raw
        for p in PROV_PREFIX.values():           # 剥掉省前缀 -> 城市名
            if city.startswith(p):
                city = city[len(p):]
                break
        st = str(r[idx["车站名称"]]).strip()
        if not st.endswith("站"):                # 青海站名补“站”
            st += "站"
        recs.append({"seq": seq, "prov": prov, "city": city,
                     "st": st, "line": str(r[idx["线路名称"]]).strip()})
    recs.sort(key=lambda x: (x["line"], x["seq"]))
    lines = defaultdict(list)
    for d in recs:
        lines[d["line"]].append(d)
    wb.close()
    return dict(lines)


def norm_city_alias(city):
    short = city
    for suf in CITY_SUFFIXES:
        if short.endswith(suf):
            short = short[: -len(suf)]
            break
    return short


# ---- 4 条重叠线路的精确拼接 ----
def splice(line, exist, new_seg):
    exist = list(exist)
    if line == "济郑高速铁路":
        anchor = "濮阳东站"
        if anchor in exist:
            i = exist.index(anchor)
            return new_seg + exist[i:]
        return new_seg + exist
    if line == "兰新高速铁路":
        anchor = "民乐站"
        if anchor in exist:
            i = exist.index(anchor)
            return exist[:i] + new_seg + exist[i:]
        return exist + new_seg
    if line == "兰青铁路":
        anchor = "兰州站"
        if anchor in exist:
            i = exist.index(anchor)
            return new_seg + exist[i:]
        return new_seg + exist
    if line == "格库铁路":
        anchor = "若羌站"
        if anchor in exist:
            i = exist.index(anchor)
            return exist[: i + 1] + new_seg + exist[i + 1:]
        return exist + new_seg
    # 默认：把 new_seg 中不存在于 exist 的站按序追加到末尾
    s = list(exist)
    seen = set(exist)
    for st in new_seg:
        if st not in seen:
            s.append(st)
            seen.add(st)
    return s


def edges_of(line_order):
    e = set()
    for sts in line_order.values():
        for a, b in zip(sts, sts[1:]):
            if a != b:
                e.add((a, b))
                e.add((b, a))
    return e


def main():
    sd = parse_excel(os.path.join(HERE, "..", "..", "山东省客运铁路线路站点表.xlsx"))
    qh = parse_excel(r"D:/AI专用/workbuddy专用/2026-07-18-12-09-49/青海省客运铁路线路站点表.xlsx")

    # 收集新线路/新车站
    new_lines = {}
    station_meta = {}
    for src_lines in (sd, qh):
        for line, recs in src_lines.items():
            names = [d["st"] for d in recs]
            new_lines.setdefault(line, names)
            for d in recs:
                m = station_meta.setdefault(d["st"], {"prov": d["prov"], "city": d["city"], "lines": set()})
                m["lines"].add(line)

    # ---- 合并 LINE_ORDER ----
    merged_line_order = {k: list(v) for k, v in R.LINE_ORDER.items()}
    skipped, merged_log = [], []
    for line, names in new_lines.items():
        if line in merged_line_order:
            exist = merged_line_order[line]
            if set(names) <= set(exist):          # 完全包含（如京沪高速山东段）-> 跳过
                skipped.append(line)
                continue
            merged_line_order[line] = splice(line, exist, names)
            merged_log.append(f"  [合并] {line}: +{len(names)}站 -> 现{len(merged_line_order[line])}站")
        else:
            merged_line_order[line] = names
            merged_log.append(f"  [新增] {line}: {len(names)}站")

    # ---- 合并 STATION_INFO / CITY / PROVINCE / ALIAS ----
    st_info = {k: dict(v) for k, v in R.STATION_INFO.items()}
    city_to = {k: list(v) for k, v in R.CITY_TO_STATIONS.items()}
    prov_to = {k: list(v) for k, v in R.PROVINCE_TO_STATIONS.items()}
    city_alias = dict(R.CITY_ALIAS)

    new_stations, new_cities = [], []
    for st, m in station_meta.items():
        if st not in st_info:
            st_info[st] = {"province": m["prov"], "city": m["city"], "lines": sorted(m["lines"])}
            new_stations.append(st)
        else:
            old = set(st_info[st].get("lines", []))
            old |= m["lines"]
            st_info[st]["lines"] = sorted(old)
        c = m["city"]
        if c not in city_to:
            city_to[c] = []
            new_cities.append(c)
            short = norm_city_alias(c)
            if short and short not in city_alias and short != c:
                city_alias[short] = c
        if st not in city_to[c]:
            city_to[c].append(st)
        p = m["prov"]
        prov_to.setdefault(p, [])
        if st not in prov_to[p]:
            prov_to[p].append(st)

    # ---- 合成线路：把必要的同城联络边以“线路”形式并入 LINE_ORDER ----
    # 济南站(胶济客专) ↔ 济南西站(京沪高速)：连通山东沿海与全国网。
    # 必须以线路形式存在，否则 _dijkstra（只走线路边）会忽略它。
    SYNTHETIC_LINES = {
        "济南市联络线": ["济南站", "济南西站"],
        "青岛市联络线": ["青岛站", "青岛北站", "青岛西站"],
        "曲阜市联络线": ["曲阜东站", "曲阜南站"],
    }
    for ln, sts in SYNTHETIC_LINES.items():
        if ln not in merged_line_order and all(s in st_info for s in sts):
            merged_line_order[ln] = list(sts)
            merged_log.append(f"  [合成] {ln}: {len(sts)}站")

    # ---- 仅追加新边到 GRAPH ----
    old_edges = edges_of(R.LINE_ORDER)
    new_edges = edges_of(merged_line_order)
    to_add = new_edges - old_edges
    gset = {k: set(v) for k, v in R.GRAPH.items()}
    for a, b in to_add:
        gset.setdefault(a, set()).add(b)
        gset.setdefault(b, set()).add(a)
    graph = {k: sorted(v) for k, v in gset.items()}

    # ---- 读取原文件 helper 块（LINE_NAME_ALIAS 起）以保留 ----
    with open(os.path.join(SRC, "railway_data.py"), "r", encoding="utf-8") as f:
        orig_all = f.readlines()
    tail = "".join(orig_all[13:])   # 第14行起 = LINE_NAME_ALIAS + helpers
    # 注入 resolver 增强：城市式带“站”后缀的查询（如“烟台站”→“烟台市”）
    _old = ('    if q in CITY_TO_STATIONS:\n'
            '        return set(CITY_TO_STATIONS[q])\n'
            '    if q in CITY_ALIAS:\n'
            '        return set(CITY_TO_STATIONS[CITY_ALIAS[q]])')
    _new = (_old + '\n'
            '    # 城市式带“站”后缀的查询（如“烟台站”→“烟台市”）：去掉后缀后按城市匹配\n'
            '    if q.endswith("站"):\n'
            '        q2 = q[:-1]\n'
            '        if q2 in CITY_TO_STATIONS:\n'
            '            return set(CITY_TO_STATIONS[q2])\n'
            '        if q2 in CITY_ALIAS:\n'
            '            return set(CITY_TO_STATIONS[CITY_ALIAS[q2]])')
    if _old in tail:
        tail = tail.replace(_old, _new)

    meta = {
        "version": "2.1",
        "sources": R.META.get("sources", []) + ["山东省客运铁路线路站点表.xlsx", "青海省客运铁路线路站点表.xlsx"],
        "generated_at": "2026-07-24",
        "line_count": len(merged_line_order),
        "station_count": len(st_info),
        "note": "v2.1 追加山东/青海两省；增量合并，未删除任何原有边",
    }

    out_py = os.path.join(SRC, "railway_data.py")
    with open(out_py, "w", encoding="utf-8") as f:
        f.write("# -*- coding: utf-8 -*-\n")
        f.write("# 整理后的全国铁路数据层 v2.1（含山东/青海两省补全，自动生成，请勿手动编辑）\n")
        f.write(f"# 生成时间：{meta['generated_at']}\n")
        f.write("# 数据来源：" + " + ".join(meta["sources"]) + "\n")
        f.write(f"# 线路数：{meta['line_count']}  车站数：{len(st_info)}\n\n")
        f.write("META = " + json.dumps(meta, ensure_ascii=False) + "\n\n")
        f.write("LINE_ORDER = " + json.dumps(merged_line_order, ensure_ascii=False) + "\n\n")
        f.write("STATION_INFO = " + json.dumps(st_info, ensure_ascii=False) + "\n\n")
        f.write("CITY_TO_STATIONS = " + json.dumps(city_to, ensure_ascii=False) + "\n\n")
        f.write("PROVINCE_TO_STATIONS = " + json.dumps(prov_to, ensure_ascii=False) + "\n\n")
        f.write("CITY_ALIAS = " + json.dumps(city_alias, ensure_ascii=False) + "\n\n")
        f.write("GRAPH = " + json.dumps(graph, ensure_ascii=False) + "\n\n")
        f.write(tail)

    # ---- 同步 data/*.json ----
    data_dir = os.path.join(HERE, "data")
    json.dump(merged_line_order, open(os.path.join(data_dir, "lines_order.json"), "w", encoding="utf-8"), ensure_ascii=False)
    json.dump(graph, open(os.path.join(data_dir, "graph_adjacency.json"), "w", encoding="utf-8"), ensure_ascii=False)
    json.dump(st_info, open(os.path.join(data_dir, "station_info.json"), "w", encoding="utf-8"), ensure_ascii=False)
    json.dump(city_to, open(os.path.join(data_dir, "city_to_stations.json"), "w", encoding="utf-8"), ensure_ascii=False)

    # ---- 报告 ----
    print("合并完成 ✅")
    print(f"线路总数: {len(merged_line_order)} (原 {len(R.LINE_ORDER)}) +{len(merged_line_order)-len(R.LINE_ORDER)}")
    print(f"车站总数: {len(st_info)} (原 {len(R.STATION_INFO)}) +{len(new_stations)} 新增")
    print(f"城市总数: {len(city_to)} (原 {len(R.CITY_TO_STATIONS)}) +{len(new_cities)} 新增城市: {new_cities}")
    print(f"GRAPH 新增边: {len(to_add)} 条（原 GRAPH 边完全保留）")
    print("跳过(已完全包含):", skipped)
    print("线路合并日志:")
    for l in merged_log:
        print(l)


if __name__ == "__main__":
    main()
