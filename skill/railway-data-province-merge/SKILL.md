---
name: railway-data-province-merge
description: 把某省份/地区的"客运铁路线路站点"Excel 增量合并进学生票 Agent 的铁路数据层 railway_data.py（LINE_ORDER / STATION_INFO / CITY_TO_STATIONS / GRAPH + 4 个 JSON）。适用于用户分批补全国客运站点数据、修复缺省省份拓扑的场景。触发词：合并省份 Excel、补铁路站点、merge province railway、修补数据库、接入新城市、B 组/缺省省份。
---

# 省份铁路 Excel → railway_data.py 增量合并

学生票合规 Agent（`交接文件夹/student_ticket_agent_handover/`）的数据层是单文件
`src/railway_data.py`，由 `LINE_ORDER`(线→有序站列表)、`STATION_INFO`、`CITY_TO_STATIONS`、
`PROVINCE_TO_STATIONS`、`CITY_ALIAS`、`GRAPH`(邻接表) 及文件尾部的 helper 函数（含 `resolve_location`）组成。
另有 4 个 JSON（`data/lines_order.json` 等）需在修改后同步。

## 通用原则
- **增量、只加不删**：绝不删除已有边/站/城市，避免回归。先备份 `src/railway_data_vX.bak`。
- 全程用管理版 venv：`C:/Users/cjp15/.workbuddy/binaries/python/envs/default/Scripts/python.exe`，
  其中已装 `openpyxl`（若缺失：`.../python.exe -m venv .../envs/default` 后 `pip install openpyxl`）。

## Excel 两种格式（决定合并策略）
1. **整段式**（如山东/青海批）：每条线在该省内有多个连续车站，且与现有 `LINE_ORDER` 在某一端重叠
   → 用"重叠段精确拼接"（找共有锚点站，把新段前插/后插/中插）。
2. **单点式**（如冀黑湘苏津批）：每条线仅列该省自己的一个站，无顺序上下文
   → 用"精确插入 + 合成联络线"：把该站插到既有截断序列的地理正确位置，断网的城市用合成联络线接到已存在的锚点站。

## 关键算法坑（必读，否则白做）
- **Dijkstra 只走"属于某条线"的边**：`student_ticket_checker._dijkstra` 依赖 `_EDGE_LINES`
  （由 `LINE_ORDER` 派生），裸 `GRAPH` 边对它不可见。所以任何新连接**必须以"线路"形式存在**
  （在 `LINE_ORDER` 里加一条线，哪怕是 2 站的合成联络线），不能只往 `GRAPH` 加裸边。
- **再生 railway_data.py 时，helper 尾部必须按"内容标记"截取，绝不能用行号**：
  用 `next(i for i,l in enumerate(lines) if l.strip().startswith("LINE_NAME_ALIAS") or "def resolve_location" in l)`
  取 `lines[hi:]`。曾因用 `orig_all[13:]`（行号）把中段的数据字典（CITY_ALIAS/PROVINCE_TO_STATIONS/GRAPH）
  当 tail 拷入，导致文件出现**重复 `GRAPH =`**，Python 加载时**尾部陈旧 GRAPH 覆盖正文新 GRAPH**，
  表现为"LINE_ORDER 里有新站、JSON 也有，但模块 GRAPH 没有 → 连通性 FAIL"。修复后须确认
  `GRAPH =`/`CITY_ALIAS =`/`PROVINCE_TO_STATIONS =` 在文件中各恰好 1 次。
- **GRAPH 重建须从 `R.GRAPH`（当前图，含非线路边如兴义站等）增量加边**，不要从 `LINE_ORDER` 全量重算
  （会丢失那 41 个仅存于 GRAPH 的节点）：
  `to_add = edges_of(merged) - edges_of(R.LINE_ORDER)`；`gset = {k:set(v) for k,v in R.GRAPH.items()}`；
  把 `to_add` 加进 `gset` 即得新 `GRAPH`。

## 标准步骤
1. 备份：`cp src/railway_data.py src/railway_data_vX.bak`（X 取当前次号，如 v2.1→v2.2）。
2. 读 Excel：`openpyxl` 定位含"线路名称"的表头行；取 序号/省份/所属省市/线路名称/车站名称。
   城市名 = 剥掉省前缀（"河北省秦皇岛市"→"秦皇岛市"；"天津市"无"省"直接保留）。
   站名统一补"站"后缀。收集 `{line: [stations按序], station: {prov,city,lines}}`。
3. 合并 `LINE_ORDER`：
   - 整段式：用 splice（重叠锚点）拼接/跳过已含整线/新增整线。
   - 单点式：对每条既有截断线做 `apply_insert(seq, mode, anchor, stations)`
     （mode∈after/before/append，anchor 必须是该线现有站、且地理正确）。
     断网城市加 `SYNTHETIC_LINES`（真实相邻站对，如 `["山海关站","秦皇岛站"]`），
     条件：两端站都已在 `STATION_INFO`（或本次 Excel 中）。
4. 合并 `STATION_INFO`/`CITY_TO_STATIONS`/`PROVINCE_TO_STATIONS`/`CITY_ALIAS`：
   新站加 `{"province":..,"city":<全城市名带市>,"lines":[..]}`；新城市加短名别名（剥"市"等后缀）。
   把"插入到既有线的既有站"（如徐州站）也补上该线归属。
5. 重建 `GRAPH`（见上，增量加边）。
6. 再生 `railway_data.py`：header 注释 + `META/LINE_ORDER/STATION_INFO/CITY_TO_STATIONS/
   PROVINCE_TO_STATIONS/CITY_ALIAS/GRAPH`(json.dumps) + **按标记截取的 helper 尾部**。
7. 同步 4 个 JSON：`lines_order.json`、`graph_adjacency.json`、`station_info.json`、`city_to_stations.json`
   （`json.dump(d, open(path,"w",encoding="utf-8"), ensure_ascii=False)`）。
8. 验证：
   - `cd src && python -u student_ticket_checker.py --test` 须 27/27（零回归）。
   - 新站 `resolve_location('X站')` 非空；枢纽解析 `192/192`（若用默认 hub 清单）。
   - 连通性：`from student_ticket_checker import _dijkstra; _dijkstra(resolve_location(a), resolve_location(b))`
     对新城市→北京/上海/广州 均返回 path 非 None。
   - 端到端：`check_compliance(school_city=.., home_city=.., dep_station=.., arr_station=.., seat=..)` 返回 ok。
   - 确认文件中 `GRAPH =`/`CITY_ALIAS =`/`PROVINCE_TO_STATIONS =` 各 1 次。

## 参考实现
- 整段式：`merge_shandong_qinghai.py`（山东/青海批，splice 4 条重叠线 + 3 合成联络线）。
- 单点式：`merge_remaining_8_cities.py`（冀黑湘苏津批，5 条精确插入 + 5 合成联络线）。
两个脚本均可作为模板，按新批次的线/站改 `LINE_INSERTS` 与 `SYNTHETIC_LINES` 即可。
