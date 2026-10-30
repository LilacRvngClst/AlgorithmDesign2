"""Bounded analysis workflow for a visualization tool agent."""
from copy import deepcopy

STATES = [
    {"id": "start", "name": "读取用户问题", "stage": 0},
    {"id": "overview", "name": "已掌握总体趋势", "stage": 1},
    {"id": "structure", "name": "已掌握能源结构", "stage": 1},
    {"id": "region", "name": "已定位重点地区", "stage": 2},
    {"id": "relation", "name": "已检查产出关联", "stage": 2},
    {"id": "source", "name": "已细分重点能源", "stage": 3},
    {"id": "done", "name": "已生成分析解释", "stage": 4},
]
EDGES = [
    {"id": "a", "from": "start", "to": "overview", "name": "观察总体趋势", "tool": "trend", "cost": 2, "reward": 2},
    {"id": "b", "from": "start", "to": "structure", "name": "先看能源占比", "tool": "structure", "cost": 2, "reward": 5},
    {"id": "c", "from": "overview", "to": "region", "name": "按地区定位增量", "tool": "regions", "cost": 1, "reward": 3},
    {"id": "d", "from": "start", "to": "region", "name": "直接按地区筛查", "tool": "regions", "cost": 3, "reward": 4},
    {"id": "e", "from": "region", "to": "source", "name": "细分重点地区能源", "tool": "drilldown", "cost": 2, "reward": 7},
    {"id": "f", "from": "structure", "to": "relation", "name": "检查产出能耗关联", "tool": "correlation", "cost": 3, "reward": 3},
    {"id": "g", "from": "source", "to": "done", "name": "解释地区与能源增量", "tool": "explain_source", "cost": 1, "reward": 2},
    {"id": "h", "from": "relation", "to": "done", "name": "解释产出关联", "tool": "explain_relation", "cost": 1, "reward": 1},
    {"id": "i", "from": "region", "to": "done", "name": "输出地区简要解释", "tool": "explain_region", "cost": 1, "reward": 1},
    {"id": "j", "from": "overview", "to": "done", "name": "输出趋势简要解释", "tool": "explain_overview", "cost": 1, "reward": 1},
]


def configuration():
    return deepcopy({"states": STATES, "edges": EDGES, "start": "start", "budget": 6,
                     "goal": "分析2026年相比2025年能源消耗的增长，定位重点地区和能源类型"})
