# 12306 学生票合规判定 Agent — 项目总览与开发日志

> 本文档用于**快速调取项目关键信息**，避免反复读取大量上下文。最后更新：2026-07-25。

---

## 1. 项目定位

- **目标**：判断用户购买的学生票区间（出发站 → 到达站）是否符合其优惠区间（学校城市 ↔ 家庭城市）。
- **核心能力**：
  - 同城多站解析（如“北京” → 北京站/北京南/北京西/北京北/北京朝阳/北京丰台/大兴机场/北京通州等）。
  - 基于铁路拓扑图的最短路径搜索，支持跨线、跨城、经枢纽中转。
  - 支持“优惠区间反向乘车”判定。
  - 支持多段联程（改家场景）的跨区间联合判定。
- **GitHub 私有仓库**：`https://github.com/pingfang154-ai/12306-student-ticket-agent`

---

## 2. 数据层现状（v2.2）

| 指标 | 数值 | 备注 |
|------|------|------|
| 线路数 `LINE_ORDER` | 253 条 | 含 12 条合成联络线（济南/青岛/曲阜、山海关/塘沽/大庆/绥化/鹤岗 等） |
| 车站数 `STATION_INFO` | 1530 站 | 覆盖 32 省级行政区 |
| 城市数 `CITY_TO_STATIONS` | 330 城 | 含 `CITY_ALIAS` 简称映射 |
| 省份数 `PROVINCE_TO_STATIONS` | 32 省/直辖市/自治区 | 含港澳台之外全部省级 |
| 图节点 `GRAPH` | 1528 节点 | 由 `LINE_ORDER` 相邻站生成 |
| 枢纽站清单 | 192 个 | **全部可解析**（100%） |

### 数据来源（v2.2 合成）

`全国客运铁路线路站点字典_v2.py`、`全国客运站点汇总.xlsx`，以及以下分省 Excel：

- 安徽省客运铁路线路站点表
- 东北客运铁路线路及车站列表
- 宁夏客运铁路站点列表
- 山东省客运铁路线路站点表
- 青海省客运铁路线路站点表
- 冀黑湘苏津客运铁路线路站点表

---

## 3. 核心模块

| 文件 | 职责 | 关键入口 |
|------|------|----------|
| `src/railway_data.py` | 数据层：线路顺序、车站信息、城市映射、省份映射、图、别名 | `resolve_location(query)` |
| `src/student_ticket_checker.py` | 合规判定引擎：Dijkstra、枢纽路径、 corridor 检测、三段式判定 | `_dijkstra`, `find_path_via_hubs`, `check_compliance` |
| `src/test_cases.py` | 27 条回归测试用例 | `python -u src/student_ticket_checker.py --test` |
| `merge_shandong_qinghai.py` | 山东、青海两省增量合并脚本 | 直接运行 |
| `merge_remaining_8_cities.py` | 冀黑湘苏津剩余 8 城增量合并脚本 | 直接运行 |
| `web_app/` | 演示前端（FastAPI，当前未安装依赖） | — |
| `docs/` | 规则分析、部署指南、数据质量报告、断点审查 | — |
| `data/` | JSON 数据：lines_order、graph_adjacency、station_info、city_to_stations、hub_stations | — |

---

## 4. 关键算法与设计

### 4.1 路径搜索只走“有线路的边”

`student_ticket_checker._dijkstra` 遍历边时，只使用同时满足以下条件的边：

- 在 `railway_data.GRAPH` 邻接表中存在；
- 该边属于某条 `LINE_ORDER` 线路的相邻站对（由 `_EDGE_LINES` 索引维护）。

**这意味着**：直接手工往 `GRAPH` 里加边是无效的，必须把它包装成一条 `LINE_ORDER` 线路（通常是合成联络线）。这是多次踩坑后定下的铁律。

### 4.2 合成联络线（Synthetic Lines）

用于连接同城不同站，或把新省份子图挂到全国网上。当前共有：

| 联络线 | 作用 |
|--------|------|
| 济南市联络线 | 济南站 ↔ 济南西站 |
| 青岛市联络线 | 青岛站 ↔ 青岛北站 ↔ 青岛西站 |
| 曲阜市联络线 | 曲阜东站 ↔ 曲阜南站 |
| 山海关站联络线 | 山海关站 ↔ 秦皇岛站 |
| 塘沽站联络线 | 塘沽站 ↔ 天津站 |
| 大庆站联络线 | 大庆站 ↔ 大庆西站 |
| 绥化站联络线 | 绥化站 ↔ 哈尔滨北站 |
| 鹤岗站联络线 | 鹤岗站 ↔ 佳木斯站 |
| 连云港站联络线 | 连云港站 ↔ 东海县站 |
| 永州站联络线 | 永州站 ↔ 衡阳东站 |
| 连云港市联络线 | 东海县站 ↔ 连云港东站 |

（注：永州、连云港也使用了既有线路插入 + 联络线。）

### 4.3 Corridor 检测（跨走廊路径）

函数签名：

```python
find_path_via_hubs(start, end, via_stations, hub_list, max_depth=3) -> (bool, path)
```

- 优先使用 `via_stations`（精确经停站）拼接，允许 2.6 倍绕行系数。
- 其次使用 Yen KSP 生成 k 条最短路径，检查是否经过 hub。
- 兜底使用自动 corridor 中转，允许 1.4 倍绕行系数。

### 4.4 合规判定三段式

`check_compliance(school_city, home_city, dep_station, arr_station, ...)`：

1. 正向判定：学校 → 家庭路径上是否顺序包含 dep → arr。
2. 反向判定：家庭 → 学校路径上是否顺序包含 arr → dep（允许反向乘车）。
3. 多区间/改家判定：若用户修改家庭城市，检查新旧家庭区间是否联合覆盖购票区间。

---

## 5. 已知坑与修复记录

| 时间 | 问题 | 原因 | 修复 |
|------|------|------|------|
| 2026-07-24 | 青岛/潍坊 → 北京无路径 | 济南站—济南西手动加边但无对应线路，Dijkstra 跳过 | 改成“济南市联络线” |
| 2026-07-24 | 临沂 → 北京仍无路径 | 青岛/曲阜同城站未互联，山东沿海子图孤立 | 增加“青岛市联络线”“曲阜市联络线” |
| 2026-07-24 | 烟台站无法解析 | `resolve_location` 不支持城市名带“站”后缀 | 增加 `q.endswith('站')` 回退 |
| 2026-07-25 | 冀黑湘苏津合并后新站不可达 | 再生成 `railway_data.py` 时 tail 截取用了行号，导致 `GRAPH=` 重复，尾部旧图覆盖新图 | 改为按内容标记定位 helper 起点 |
| 2026-07-25 | `gh repo create` 报已存在 | 之前已创建同名仓库 `12306学生票判定` | 改用新仓库名 `12306-student-ticket-agent` |

---

## 6. 分省数据增量合并 SOP

新增省份/城市 Excel 时，按以下流程执行：

1. **格式勘察**：确认 Excel 是“整段连续站”（如山东/青海）还是“每线一个站”（如冀黑湘苏津）。
2. **重叠线识别**：与现有 `LINE_ORDER` 对比，找出需要拼接的线路。
3. **锚点验证**：新站必须能挂到已在全国网中的锚点站；否则需新增合成联络线。
4. **编写/复用 merge 脚本**：
   - 使用 `edges_of(LINE_ORDER)` 计算新边；
   - 只添加 `merged - original` 的边，绝不删除旧边；
   - 使用 `railway_data_v2.X.bak` 备份当前版本；
   - 生成 `railway_data.py` 时，按 `LINE_NAME_ALIAS` / `def resolve_location` 内容标记截取 helper tail，不要用行号。
5. **同步 4 个 JSON**：`lines_order.json`、`graph_adjacency.json`、`station_info.json`、`city_to_stations.json`。
6. **验证**：运行 `python -u src/student_ticket_checker.py --test`，并抽查新城到 北京/上海/广州 的可达性。
7. **提交**：`git add . && git commit -m "..." && git push origin main`。

可复用技能：`~/.workbuddy/skills/railway-data-province-merge/SKILL.md`

---

## 7. 测试与验证

- 回归测试：`python -u src/student_ticket_checker.py --test` → **27/27 通过**。
- 关键城市可达性抽查：
  - 山东：青岛、烟台、潍坊、淄博、临沂、菏泽、日照、威海 ↔ 北京/上海 可达。
  - 青海：西宁 ↔ 兰州 可达。
  - 冀黑湘苏津：山海关、大庆、绥化、鹤岗、永州、连云港、塘沽 ↔ 北京/上海/广州 可达。
- 端到端合规：`check_compliance(学校=北京, 家庭=大庆, 大庆站→北京站)` → `ok=True`。

---

## 8. 变更日志

### 2026-07-24
- 接入山东、青海两省数据，数据层从 v2.0 → v2.1。
- 新增 14 城、89 站、12 线（含 3 条合成联络线）。
- 枢纽解析从 154/192 → 184/192。
- 增加 `resolve_location` “站”后缀城市解析。

### 2026-07-25
- 接入冀黑湘苏津五省市数据，数据层从 v2.1 → v2.2。
- 新增 5 城、8 站、5 条合成联络线。
- 枢纽解析达到 **192/192（100%）**。
- 修复 `railway_data.py` 重复 `GRAPH=` 生成 bug。
- 项目首次提交到 GitHub 私有仓库 `12306-student-ticket-agent`。

---

## 9. 后续 TODO / 扩展方向

- [ ] 安装并跑通 `web_app`（当前缺少 FastAPI 等依赖）。
- [ ] 每年例行检查新开线路/车站，按 SOP 增量合并。
- [ ] 优化 `_dijkstra` 性能：当前全图规模 1528 节点，仍可接受；若未来扩展到 3000+ 站，考虑缓存或 A\*。
- [ ] 将 `LINE_NAME_ALIAS` 真正用起来，处理线路名括号/普速后缀标准化。
- [ ] 补充学生票规则文档（如“每学年 4 次”“新生/毕业生特殊规则”）到 `docs/`。

---

## 10. 快速命令备忘

```bash
# 运行测试
cd src
python -u student_ticket_checker.py --test

# 本地启动演示（需先安装依赖）
cd web_app
pip install fastapi uvicorn
uvicorn main:app --reload

# 推送到 GitHub
git add .
git commit -m "feat: ..."
git push origin main
```
