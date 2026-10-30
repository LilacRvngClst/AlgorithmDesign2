"""Budget-constrained path DP over a directed acyclic analysis workflow."""


def validate(states, edges, start, budget):
    if type(budget) is not int or not 0 <= budget <= 200:
        raise ValueError("预算必须是0～200的整数")
    if not isinstance(states, list) or not 1 <= len(states) <= 20:
        raise ValueError("状态数量必须为1～20")
    if not isinstance(edges, list) or len(edges) > 40:
        raise ValueError("操作数量不能超过40")
    by_id = {}
    for s in states:
        if not isinstance(s, dict) or not isinstance(s.get("id"), str) or not s["id"] or s["id"] in by_id:
            raise ValueError("状态ID必须为不重复的字符串")
        if not isinstance(s.get("name"), str) or len(s["name"]) > 100:
            raise ValueError("状态名称无效")
        if type(s.get("stage")) is not int or not 0 <= s["stage"] <= 20:
            raise ValueError("阶段必须为0～20的整数")
        by_id[s["id"]] = s
    if start not in by_id:
        raise ValueError("初始状态不存在")
    seen, outgoing = set(), {s["id"]: [] for s in states}
    for e in edges:
        if not isinstance(e, dict) or not isinstance(e.get("id"), str) or not e["id"] or e["id"] in seen:
            raise ValueError("操作ID必须为不重复的字符串")
        seen.add(e["id"])
        if e.get("from") not in by_id or e.get("to") not in by_id:
            raise ValueError("操作的起止状态不存在")
        if by_id[e["from"]]["stage"] >= by_id[e["to"]]["stage"]:
            raise ValueError("操作必须指向更后面的阶段，工作流不能有环")
        if type(e.get("cost")) is not int or not 1 <= e["cost"] <= 200:
            raise ValueError("操作成本必须为1～200的整数")
        if type(e.get("reward")) is not int or not 0 <= e["reward"] <= 1000:
            raise ValueError("操作收益必须为0～1000的整数")
        outgoing[e["from"]].append(e)
    return by_id, outgoing


def solve(states, edges, start, budget):
    """V(s,b): best FUTURE reward from analysis state s with budget b."""
    by_id, outgoing = validate(states, edges, start, budget)
    order = sorted(states, key=lambda s: s["stage"], reverse=True)
    values = {s["id"]: [0] * (budget + 1) for s in states}
    choices = {s["id"]: [None] * (budget + 1) for s in states}
    trace = []
    for state in order:
        s = state["id"]
        for b in range(budget + 1):
            best, selected, candidates = 0, None, []  # Stopping now is allowed.
            for action in outgoing[s]:
                feasible = action["cost"] <= b
                future = values[action["to"]][b-action["cost"]] if feasible else None
                total = action["reward"] + future if feasible else None
                candidates.append({"action": action["id"], "feasible": feasible,
                                   "future": future, "total": total})
                if feasible and total > best:
                    best, selected = total, action["id"]
            values[s][b], choices[s][b] = best, selected
            trace.append({"state": s, "budget": b, "value": best,
                          "choice": selected, "candidates": candidates})
    edge_by_id = {e["id"]: e for e in edges}
    path, s, b = [], start, budget
    while choices[s][b] is not None:
        action = edge_by_id[choices[s][b]]
        path.append({**action, "before": b, "after": b-action["cost"],
                     "future": values[action["to"]][b-action["cost"]]})
        s, b = action["to"], b-action["cost"]
    return {"value": values[start][budget], "cost": budget-b, "remaining": b,
            "path": path, "end": s, "values": values, "choices": choices,
            "trace": trace, "state_count": len(states)*(budget+1)}


def greedy(states, edges, start, budget):
    """Choose highest immediate reward/cost among available outgoing actions."""
    _, outgoing = validate(states, edges, start, budget)
    s, b, value, path = start, budget, 0, []
    while True:
        feasible = [e for e in outgoing[s] if e["cost"] <= b and e["reward"] > 0]
        if not feasible:
            break
        action = sorted(feasible, key=lambda e: (-e["reward"]/e["cost"], e["id"]))[0]
        path.append(action["id"])
        b -= action["cost"]
        value += action["reward"]
        s = action["to"]
    return {"value": value, "cost": budget-b, "path": path, "end": s}


def exhaustive(states, edges, start, budget):
    """Independent path enumeration oracle for small instances, no DP caching."""
    validate(states, edges, start, budget)
    def visit(s, b):
        best = 0
        for edge in edges:
            if edge["from"] == s and edge["cost"] <= b:
                best = max(best, edge["reward"] + visit(edge["to"], b-edge["cost"]))
        return best
    return visit(start, budget)
