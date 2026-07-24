# 学生票 Agent — 项目上下文摘要

> 生成日期：2026-07-23
> 用途：供接收方（其他编程智能体或开发者）快速恢复项目认知

---

## 一、项目概述

学生票合规检查 Agent，用于判断用户输入的购票区间是否在其学生优惠区间（学校↔家庭所在地）的合理径路上，并提供反向购票识别、修改建议等功能。核心能力包括：

- **数据层**：覆盖全国 253 条铁路线路（含山东/青海两省 +3 条合成联络线、冀黑湘苏津五省市 +5 条合成联络线）、1530 个车站、330 个城市、31 个省/自治区/直辖市的铁路拓扑网络（v2.2，2026-07-24 追加山东/青海/冀黑湘苏津）
- **算法层**：带换乘惩罚的 Dijkstra 单路径搜索 + 简化版 Yen's KSP 多路径搜索（K=10）
- **规则层**：从 13 份 12306 官方规则文档中提取的学生票规则（结构化 JSON）
- **交互层**：FastAPI Web 界面（ECharts 路径可视化、多途经点、家庭修改）

---

## 二、已完成工作

### 数据整合（已完成）
- 基础数据：全国铁路站点字典 + 全国客运站点汇总
- 补充区域：安徽省（28线/99站）、东北三省（16线/69站）、宁夏（7线/35站）、京津冀（15线/105站）、江浙沪皖（17线/194站）、武昌→成都东段（3线桥梁）
- 后处理：襄渝/达成/遂成/汉丹铁路站序修复

### 算法引擎（已完成）
- 带换乘惩罚的 Dijkstra（TRANSFER_PENALTY=2.0）
- 简化版 Yen's KSP（K=10，支持边禁）
- `check_compliance()` / `suggest()` / `check_route_segments()` 核心函数
- 家庭所在地修改支持（`new_home_city` 参数）

### 规则层（已完成）
- 13 份规则文档提取 → `student_rules.json`
- 案例库 10 个（case1–case10）
- 额外城市别名 16 个

### Web 界面（已完成）
- FastAPI + Jinja2 服务端渲染
- ECharts 路径可视化
- 智能自动补全（自定义下拉框）
- 多途经点动态输入
- 家庭修改折叠面板
- 分段进度条
- 移动端适配

### 测试（已完成）
- 18 个测试用例全部通过（运行 `python test_cases.py`）

### 数据质量
- 游离站：0
- 未知城市：0
- 断头端点：4（均为物理终端）
- 车站-信息匹配率：95.8%

---

## 三、关键数据统计

| 指标 | 数值 |
|------|------|
| 铁路线路数 | 233 |
| 车站总数 | 1433 |
| 城市数 | 311 |
| 省份数 | 31 |
| GRAPH 节点数 | 1432 |
| 城市别名数 | 309 |
| 案例数 | 10 |
| 测试用例 | 18 ✅ |

---

## 四、核心代码位置

| 文件 | 功能 |
|------|------|
| `src/railway_data.py` | LINE_ORDER/GRAPH/STATION_INFO/CITY_TO_STATIONS/CITY_ALIAS + resolve_location() |
| `src/student_ticket_checker.py` | _dijkstra / find_multiple_paths_between_cities / check_compliance / suggest / check_route_segments |
| `src/web_app.py` | FastAPI 入口 + Jinja2 模板渲染 + JSON API |
| `src/test_cases.py` | 18 个自动化测试用例 |
| `src/build_v2.py` | 从 xlsx 源文件构建 railway_data.py 的流水线脚本 |
| `data/student_rules.json` | 规则层 + 10 案例 + 别名 |
| `data/lines_order.json` | 线路车站顺序（核心拓扑，JSON 格式） |
| `data/city_to_stations.json` | 同城车站映射 |
| `data/graph_adjacency.json` | 图邻接表（1432 节点） |
| `data/city_aliases.json` | 城市别名（309 条目） |
| `data/station_aliases.json` | 站名别名 |
| `web/templates/index.html` | 主页面（ECharts 可视化） |
| `web/templates/cases.html` | 案例库页面 |
| `web/static/style.css` | 样式文件 |

---

## 五、算法要点

### Dijkstra 状态
- 状态 = `(station, incoming_line)`，跨线换乘加 TRANSFER_PENALTY=2.0
- `blocked_edges` 参数用于 KSP

### KSP (Yen's Simplified)
- 迭代移除每条已发现路径的一条边，重新运行 Dijkstra
- K=10，择优保留路径
- 局限：当两个廊道完全分岔时，边缘除策略无法"跳"到另一廊道（如 武汉→大理 经重庆+成都）

### 区间合规判断
```
学校城市 ↔ 家庭城市 建立路径集(K=10)
如果 出发站 ∈ 学校城市 AND 到达站 ∈ 家庭城市 → 合规
如果 出发站 ∈ 家庭城市 AND 到达站 ∈ 学校城市 → 反向合规
如果 出发站/到达站 都在同一路径上且顺序包含 → 同路径合规
否则 → 不合规
```

---

## 六、待办事项

### P0 — 必须解决
1. ~~**KSP 跨廊道限制**：武汉→大理经重庆+成都的路径不在 K=10 范围内。~~ **【已修复 2026-07-24】** 已实现廊道探测算法 `find_path_via_hubs(start, end, via_stations, hub_list, max_depth=3)`，在 `check_compliance` 中以"用户显式途经站"为优先（优先于 Yen），并施加 2.6× 绕行守卫；同时保留 auto 廊道回退（1.4× 守卫）以保证无显式途经站时的零回归。验证：武汉→大理经重庆+成都+广通北、南京→西安（改家贵阳）经凯里南+荔波+安顺 均判合规；南昌→株洲绕行福建被守卫拦截。测试用例 27/27 通过。

### P1 — 重要
2. **Docker 部署**：创建 Dockerfile，支持一键容器化部署
3. **data_quality_report.md 更新**：`docs/data_quality_report_v2.md` 可以生成更多维度的报告

### P2 — 一般
4. **G3/G4 规则确认**：KU2（有未出行学生票时能否修改区间）和 KU3（修改冷却期）部分已确认但需用户补充
5. **路网扩张**：补充剩余断头线的连接段数据（包银、京港昌赣、济郑、贵开等）
6. **匹配率提升**：当前 95.8%，部分车站缺少省份/城市信息，可从其他来源补充

### P3 — 低优先级
7. **测试覆盖率**：从 18 个扩展到更多边缘场景
8. **��能优化**：GRAPH 加载时预计算更多缓存
9. **Docker Compose**：支持多服务编排

---

## 七、已知限制

1. ~~**路径搜索**：KSP 基于单边阻塞，无法发现需要同时阻塞多条边的替代路径（跨廊道场景）~~ **【已修复】** 跨廊道/多枢纽绕行现由 `find_path_via_hubs` 廊道探测覆盖（优先于 Yen，需用户显式给出途经站）。KSP 仍作为主路径搜索用于常规区间。
2. ~~**城市映射**：部分小站（如线路所、乘降所）可能未收录，对应城市信息可能缺失。~~ **【已修复 2026-07-24】** 原缺失的山东省、青海省（见 `merge_shandong_qinghai.py`）与冀黑湘苏津五省市（见 `merge_remaining_8_cities.py`）铁路线路与车站已全部并入数据层：山东/青海补 14 城、89 站、12 新线 +3 合成联络线；冀黑湘苏津补 5 城、8 站、5 合成联络线（山海关↔秦皇岛、塘沽↔天津、大庆↔大庆西、绥化↔哈尔滨北、鹤岗↔佳木斯），并对 5 条截断干线（哈齐/衡柳/湘桂/青盐/陇海）做精确插入。原 B 组 15 城（山海关、大庆、大庆西、绥化、鹤岗、永州、连云港、塘沽 + 山东/青海 7 城）至此**全部接入全国路网**，192 个枢纽站 100% 可解析，原 38 个失效枢纽清零。另：`resolve_location` 已支持"烟台站"式带"站"后缀城市名查询。
3. **规则完整性**：学生票规则基于"相对近径路或合理径路"的模糊标准，引擎的路径判定可能比 12306 实际系统更严格或更宽松
4. **数据时效**：铁路数据截止至 2026 年 7 月，新建线路需手动补充

---

## 八、运行测试

```bash
# 方法一（推荐）：从项目根目录
cd student_ticket_agent_handover
python -m src.test_cases

# 方法二：从 src/ 目录
cd src
python -u test_cases.py

# 方法三：通过 checker 引擎
python -m src.student_ticket_checker --test
```

## 九、快速自查命令

```bash
# 检查数据完整性
python -c "import sys; sys.path.insert(0,'src'); import railway_data as R; print(f'线路:{len(R.LINE_ORDER)} 车站:{len(R.STATION_INFO)} 城市:{len(R.CITY_TO_STATIONS)}')"

# 测试一个具体案例
python -c "import sys; sys.path.insert(0,'src'); from student_ticket_checker import check_student_ticket; r=check_student_ticket('武汉','大理','武汉','大理'); print('合规' if r['result']['ok'] else '不合规'); print(r['result']['reason'])"
```
