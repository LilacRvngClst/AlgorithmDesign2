"""Visualization agent: plan a dependent analysis path, execute tools with memory."""
from collections import defaultdict
from data_tools import load_data, run_tool
from planner import solve, greedy
from scenarios import configuration


def yearly_changes(rows, key):
    totals = defaultdict(lambda: {"2025": 0.0, "2026": 0.0})
    for row in rows:
        year = row["month"][:4]
        if year in ("2025", "2026"):
            totals[row[key]][year] += row["consumption"]
    return [{"label": label, "value": round(v["2026"]-v["2025"], 2),
             "previous": round(v["2025"], 2), "current": round(v["2026"], 2)}
            for label, v in sorted(totals.items())]


def perform(action, rows, memory):
    tool = action["tool"]
    if tool == "regions":
        series = yearly_changes(rows, "region")
        focus = max(series, key=lambda p: p["value"])
        memory["region"] = focus["label"]
        memory["region_delta"] = focus["value"]
        return {"chart": {"type": "bar", "title": "各地区2026年相对2025年的能源增量", "series": series},
                "finding": f"{focus['label']}增量最大，为{focus['value']:,.2f}吨标准煤；将其作为下一步细分对象。",
                "evidence": {"focus_region": focus["label"], "delta": focus["value"]}}
    if tool == "drilldown":
        if "region" not in memory:
            raise ValueError("缺少重点地区，不能直接执行能源细分")
        subset = [r for r in rows if r["region"] == memory["region"]]
        series = yearly_changes(subset, "source")
        focus = max(series, key=lambda p: p["value"])
        memory["source"] = focus["label"]
        memory["source_delta"] = focus["value"]
        return {"chart": {"type": "bar", "title": f"{memory['region']}各能源类型的消耗增量", "series": series},
                "finding": f"在{memory['region']}，{focus['label']}的消耗增量最大，为{focus['value']:,.2f}吨标准煤。",
                "evidence": {"focus_region": memory["region"], "focus_source": focus["label"], "delta": focus["value"]}}
    if tool.startswith("explain_"):
        if tool == "explain_source":
            if not {"region", "source"} <= memory.keys():
                raise ValueError("缺少地区与能源细分证据")
            finding = f"2026年相对2025年，{memory['region']}的能源消耗增量为{memory['region_delta']:,.2f}吨标准煤；其中{memory['source']}增量最高，为{memory['source_delta']:,.2f}吨标准煤。以上是增量定位与分解，不构成因果解释。"
        elif tool == "explain_relation":
            if "r" not in memory:
                raise ValueError("缺少关联分析证据")
            finding = f"样本工业产出与能耗的Pearson相关系数为{memory['r']:.4f}。这是总体关联，尚未完成地区与能源增量定位，不能据此回答增长原因。"
        elif tool == "explain_region":
            finding = f"重点地区是{memory['region']}，消耗增量为{memory['region_delta']:,.2f}吨标准煤，尚未进一步细分能源类型。"
        else:
            finding = "已经检查总体趋势，但尚未定位增长集中在哪个地区、哪种能源。"
        return {"chart": None, "finding": finding, "evidence": dict(memory)}
    chart = run_tool(tool, rows)
    if tool == "correlation":
        memory["r"] = chart["r"]
    return {"chart": chart, "finding": chart["insight"], "evidence": {"tool": tool}}


def execute(payload):
    if set(payload) - {"budget", "edges"}:
        raise ValueError("本接口仅接受预算与工作流操作评分，不再接受独立任务集合")
    config = configuration()
    # The research question and permitted state transitions are fixed, not invented by an LLM.
    edges = config["edges"]
    if "edges" in payload:
        supplied = payload["edges"]
        if not isinstance(supplied, list) or len(supplied) != len(edges):
            raise ValueError("请完整提供工作流的操作成本与收益")
        by_id = {}
        for e in supplied:
            if not isinstance(e, dict) or e.get("id") in by_id:
                raise ValueError("操作配置无效或重复")
            by_id[e.get("id")] = e
        if set(by_id) != {e["id"] for e in edges}:
            raise ValueError("不能增删固定工作流中的操作")
        for e in edges:
            e["cost"], e["reward"] = by_id[e["id"]].get("cost"), by_id[e["id"]].get("reward")
    budget = payload.get("budget", 6)
    result = solve(config["states"], edges, config["start"], budget)
    baseline = greedy(config["states"], edges, config["start"], budget)
    rows, memory, steps = load_data(), {}, []
    names = {s["id"]: s["name"] for s in config["states"]}
    for number, action in enumerate(result["path"], 1):
        before = dict(memory)
        output = perform(action, rows, memory)
        steps.append({"number": number, "action": action["id"], "name": action["name"],
                      "from": names[action["from"]], "to": names[action["to"]],
                      "cost": action["cost"], "reward": action["reward"],
                      "budget_before": action["before"], "budget_after": action["after"],
                      "memory_before": before, "memory_after": dict(memory), **output})
    conclusion = steps[-1]["finding"] if steps else "预算不足，智能体没有执行分析操作。"
    if result["end"] != "done" and steps:
        conclusion = "当前预算只完成部分分析，未到达解释状态。最近发现：" + conclusion
    return {"goal": config["goal"], "states": config["states"], "edges": edges,
            "start": config["start"], "budget": budget, "result": result,
            "greedy": baseline, "steps": steps, "conclusion": conclusion,
            "completed": result["end"] == "done", "data_rows": len(rows)}
