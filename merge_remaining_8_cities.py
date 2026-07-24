# -*- coding: utf-8 -*-
"""
合并《冀黑湘苏津客运铁路线路站点表.xlsx》到铁路数据层 (railway_data.py)。

背景：本文件覆盖此前仍缺失的 8 座城市（山海关、大庆、大庆西、绥化、鹤岗、永州、
连云港、塘沽），分属 河北/黑龙江/湖南/江苏/天津 五省市。本批数据每线仅列本省车站
（单点），与山东/青海批（整段）不同，无法用“重叠段拼接”自动处理；改用语义化
“精确插入 + 合成联络线”方案，确保地理正确且对全国路网零回归。

策略：增量、仅追加（绝不删除已有边/车站），保持现有拓扑零回归。
输出：src/railway_data.py（重新生成，保留原 helper）+ 同步 4 个 JSON。
"""
import os, sys, json
from collections import defaultdict

HERE = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.join(HERE, "src")
sys.path.insert(0, SRC)
import railway_data as R
import openpyxl

XLSX = os.path.join(HERE, "..", "..", "冀黑湘苏津客运铁路线路站点表.xlsx")


def parse_excel(path):
    """返回 {line: [ {st, prov, city, line, seq} ... 按序 ]}，并整理出 station_meta。"""
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
        # 剥省前缀 -> 城市全名(带“市”)
        prefix = prov + "省"
        if city_raw.startswith(prefix):
            city = city_raw[len(prefix):]            # 河北省秦皇岛市 -> 秦皇岛市
        else:
            city = city_raw                          # 天津市
        st = str(r[idx["车站名称"]]).strip()
        if not st.endswith("站"):
            st += "站"
        recs.append({"seq": seq, "prov": prov, "city": city,
                     "st": st, "line": str(r[idx["线路名称"]]).strip()})
    recs.sort(key=lambda x: (x["line"], x["seq"]))
    lines = defaultdict(list)
    for d in recs:
        lines[d["line"]].append(d)
    wb.close()
    return dict(lines), recs


# ---- 5 条既有截断线路的精确插入（地理正确位置）----
# mode: 'after' 锚点之后 | 'before' 锚点之前 | 'append' 末尾
LINE_INSERTS = {
    "哈齐高速铁路": ("after", "哈尔滨北站", ["大庆西站"]),
    "衡柳铁路":     ("before", "衡阳东站", ["永州站"]),
    "湘桂铁路":     ("before", "桂林北站", ["永州站"]),
    "青盐铁路":     ("after", "岚山西站", ["连云港站"]),
    "陇海铁路":     ("after", "黄口站", ["徐州站", "连云港站"]),
}

# ---- 5 条合成联络线（真实相邻站对，以“线路”形式并入使 Dijkstra 可见）----
SYNTHETIC_LINES = {
    "山海关站联络线": ["山海关站", "秦皇岛站"],
    "塘沽站联络线":   ["塘沽站", "天津站"],
    "大庆站联络线":   ["大庆站", "大庆西站"],
    "绥化站联络线":   ["绥化站", "哈尔滨北站"],
    "鹤岗站联络线":   ["鹤岗站", "佳木斯站"],
}


def norm_city_alias(city):
    for suf in ["维吾尔自治区", "壮族自治区", "回族自治区", "自治区",
               "白族自治州", "彝族自治州", "土家族苗族自治州",
               "苗族土家族自治县", "地区", "自治州", "自治县", "市", "州", "区", "县", "盟"]:
        if city.endswith(suf):
            return city[: -len(suf)]
    return city


def apply_insert(seq, mode, anchor, stations):
    s = list(seq)
    if mode == "append":
        seen = set(s)
        for st in stations:
            if st not in seen:
                s.append(st); seen.add(st)
        return s
    if anchor not in s:
        # 锚点缺失则退化为末尾追加（不应发生，已校验）
        return apply_insert(seq, "append", None, stations)
    i = s.index(anchor)
    if mode == "after":
        s[i + 1:i + 1] = stations
    elif mode == "before":
        s[i:i] = stations
    return s


def edges_of(line_order):
    e = set()
    for sts in line_order.values():
        for a, b in zip(sts, sts[1:]):
            if a != b:
                e.add((a, b)); e.add((b, a))
    return e


def main():
    src_lines, recs = parse_excel(XLSX)

    # 收集车站元数据（来自 Excel）
    station_meta = {}
    for d in recs:
        m = station_meta.setdefault(d["st"], {"prov": d["prov"], "city": d["city"], "lines": set()})
        m["lines"].add(d["line"])

    # ---- 合并 LINE_ORDER ----
    merged_line_order = {k: list(v) for k, v in R.LINE_ORDER.items()}
    logs = []

    # 1) 真实线路精确插入
    for line, (mode, anchor, stations) in LINE_INSERTS.items():
        assert line in merged_line_order, f"线路 {line} 不在现有 LINE_ORDER 中！"
        assert anchor in merged_line_order[line], f"锚点 {anchor} 不在 {line} 中！"
        merged_line_order[line] = apply_insert(merged_line_order[line], mode, anchor, stations)
        logs.append(f"  [插入] {line}: 于 {anchor} {mode} {stations} -> 现 {len(merged_line_order[line])} 站")
        # 把插入的既有站补上该线路归属（元数据）
        for st in stations:
            if st in R.STATION_INFO and line not in R.STATION_INFO[st].get("lines", []):
                pass  # 下面统一处理

    # 2) 合成联络线
    for ln, sts in SYNTHETIC_LINES.items():
        if ln not in merged_line_order and all(s in R.STATION_INFO or s in station_meta for s in sts):
            merged_line_order[ln] = list(sts)
            logs.append(f"  [合成] {ln}: {sts}")

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
            old = set(st_info[st].get("lines", [])) | m["lines"]
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

    # 把“插入到既有线路中的既有站”（如 徐州站）补上该线路归属
    for line, (mode, anchor, stations) in LINE_INSERTS.items():
        for st in stations:
            if st in st_info and line not in st_info[st].get("lines", []):
                st_info[st]["lines"] = sorted(set(st_info[st]["lines"]) | {line})

    # ---- 仅追加新边到 GRAPH（保留既有非线路边，如 兴义站 等）----
    old_edges = edges_of(R.LINE_ORDER)
    new_edges = edges_of(merged_line_order)
    to_add = new_edges - old_edges
    gset = {k: set(v) for k, v in R.GRAPH.items()}
    for a, b in to_add:
        gset.setdefault(a, set()).add(b)
        gset.setdefault(b, set()).add(a)
    graph = {k: sorted(v) for k, v in gset.items()}

    # ---- 读取原文件 helper 块（按内容定位，避免行号错位导致重复数据）----
    with open(os.path.join(SRC, "railway_data.py"), "r", encoding="utf-8") as f:
        orig_all = f.readlines()
    hi = next(i for i, l in enumerate(orig_all)
              if l.strip().startswith("LINE_NAME_ALIAS") or "def resolve_location" in l)
    tail = "".join(orig_all[hi:])   # 仅取 helper 函数（不含任何数据字典）

    meta = {
        "version": "2.2",
        "sources": R.META.get("sources", []) + ["冀黑湘苏津客运铁路线路站点表.xlsx"],
        "generated_at": "2026-07-24",
        "line_count": len(merged_line_order),
        "station_count": len(st_info),
        "note": "v2.2 追加冀黑湘苏津五省市(剩余8城)；增量合并，未删除任何原有边",
    }

    out_py = os.path.join(SRC, "railway_data.py")
    with open(out_py, "w", encoding="utf-8") as f:
        f.write("# -*- coding: utf-8 -*-\n")
        f.write("# 整理后的全国铁路数据层 v2.2（含冀黑湘苏津五省市补全，自动生成，请勿手动编辑）\n")
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
    print("合并完成 ✅ (v2.2)")
    print(f"线路总数: {len(merged_line_order)} (原 {len(R.LINE_ORDER)}) +{len(merged_line_order)-len(R.LINE_ORDER)}")
    print(f"车站总数: {len(st_info)} (原 {len(R.STATION_INFO)}) +{len(new_stations)} 新增: {new_stations}")
    print(f"城市总数: {len(city_to)} (原 {len(R.CITY_TO_STATIONS)}) +{len(new_cities)} 新增城市: {new_cities}")
    print(f"GRAPH 新增边: {len(to_add)} 条（原 GRAPH 边完全保留）")
    print("线路变更日志:")
    for l in logs:
        print(l)


if __name__ == "__main__":
    main()
