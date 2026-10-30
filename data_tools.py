"""Data tools used by the analysis-path agent. Synthetic data only."""
import csv
import math
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent


def load_data():
    with (ROOT / "data" / "energy.csv").open(encoding="utf-8-sig", newline="") as f:
        rows = list(csv.DictReader(f))
    for r in rows:
        r["consumption"] = float(r["consumption"])
        r["output"] = float(r["output"])
    return rows


def aggregate(rows, key):
    totals = defaultdict(float)
    for row in rows:
        totals[row[key]] += row["consumption"]
    return [{"label": k, "value": round(v, 2)} for k, v in sorted(totals.items())]


def run_tool(tool, rows):
    if tool == "trend":
        series = aggregate(rows, "month")
        peak = max(series, key=lambda p: p["value"])
        return {"type": "line", "title": "月度能源消耗趋势", "series": series,
                "insight": f"样本中月度总消耗最高为 {peak['label']}，合计 {peak['value']:,.2f} 吨标准煤。"}
    if tool == "structure":
        series = aggregate(rows, "source")
        total = sum(p["value"] for p in series)
        peak = max(series, key=lambda p: p["value"])
        return {"type": "donut", "title": "能源结构占比", "series": series,
                "insight": f"{peak['label']}占样本总消耗的 {peak['value']/total:.1%}，是占比最高的能源类型。"}
    if tool == "regions":
        series = aggregate(rows, "region")
        peak = max(series, key=lambda p: p["value"])
        return {"type": "bar", "title": "地区能源消耗对比", "series": series,
                "insight": f"{peak['label']}累计消耗最高，为 {peak['value']:,.2f} 吨标准煤；规模差异不能直接解释为效率差异。"}
    if tool == "correlation":
        grouped = {}
        for r in rows:
            key = (r["month"], r["region"])
            if key not in grouped:
                grouped[key] = {"x": r["output"], "y": 0, "label": " / ".join(key)}
            grouped[key]["y"] += r["consumption"]
        points = list(grouped.values())
        mx = sum(p["x"] for p in points) / len(points)
        my = sum(p["y"] for p in points) / len(points)
        numerator = sum((p["x"]-mx)*(p["y"]-my) for p in points)
        denominator = math.sqrt(sum((p["x"]-mx)**2 for p in points) * sum((p["y"]-my)**2 for p in points))
        r = numerator / denominator if denominator else 0
        return {"type": "scatter", "title": "工业产出与能源消耗关联", "points": points,
                "r": round(r, 4), "insight": f"按月份×地区汇总，Pearson r = {r:.4f}。相关关系不表示因果关系；数据为教学合成样本。"}
    raise ValueError("不支持的分析工具")


