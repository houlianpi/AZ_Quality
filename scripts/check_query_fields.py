#!/usr/bin/env python3
"""检查 ADO Query 的字段配置情况"""
import json
import subprocess
import sys

REQUIRED_FIELDS = {
    "System.Id": "ID",
    "System.Title": "Title",
    "System.State": "State",
    "System.AssignedTo": "Assigned To",
    "Microsoft.VSTS.Scheduling.DueDate": "Due Date",
    "Microsoft.VSTS.Common.Priority": "Priority",
    "Microsoft.VSTS.Common.Severity": "Severity",
    "Microsoft.VSTS.Common.Blocking": "Blocking",
    "Microsoft.VSTS.Common.Release": "Release",
    "System.AreaPath": "Area Path",
    "System.CreatedDate": "Created Date",
    "System.Tags": "Tags",
    "OSG.SDLSeverity": "SDL Severity",
}

def check_query(query_id: str, query_name: str) -> None:
    """检查单个 Query 的字段配置"""
    cmd = ["az", "boards", "query", "--id", query_id, "--output", "json"]
    result = subprocess.run(cmd, capture_output=True, text=True)

    if result.returncode != 0:
        print(f"=== {query_name} ===")
        print(f"❌ 查询失败: {result.stderr[:100]}")
        return

    try:
        data = json.loads(result.stdout)
    except json.JSONDecodeError:
        print(f"=== {query_name} ===")
        print("⚠️ 空结果或无效 JSON")
        return

    if not data:
        print(f"=== {query_name} ===")
        print("⚠️ 空结果 (没有符合条件的 bugs)")
        return

    total = len(data)
    print(f"=== {query_name} ({total} bugs) ===")

    # 统计每个字段出现次数
    field_counts = {name: 0 for name in REQUIRED_FIELDS.values()}

    for bug in data:
        fields = bug.get("fields", {})
        # ID 在顶层
        if bug.get("id"):
            field_counts["ID"] += 1
        # 其他字段在 fields 中
        for ado_field, display_name in REQUIRED_FIELDS.items():
            if ado_field != "System.Id" and ado_field in fields:
                field_counts[display_name] += 1

    # 输出结果
    for name in ["ID", "Title", "State", "Assigned To", "Due Date", "Priority",
                 "Severity", "Blocking", "Release", "Area Path", "Created Date",
                 "Tags", "SDL Severity"]:
        count = field_counts[name]
        if count == 0:
            status = "❌ 未配置或全空"
        elif count == total:
            status = "✅ 已配置 (100%)"
        else:
            pct = count / total * 100
            status = f"⚠️ 已配置 ({count}/{total}={pct:.0f}%有值)"
        print(f"  {name:15} {status}")
    print()


def main():
    queries = {
        "Blocking": "794cee31-0a95-4490-a120-68e2a7d51578",
        "Security": "36ab0106-671a-4ce1-8bbd-f6a96291a4d1",
        "Need Triage": "c0f09030-b1e7-43f6-84d2-4b05de23d423",
        "P0P1": "64965d76-01cd-4951-b917-b491a055d207",
        "A11y": "3a9adaff-387a-4f34-9e69-9fb5288c0f60",
    }

    print("检查 edge-china-consumer 所有 Query 的字段配置")
    print("=" * 60)
    print()

    for name, query_id in queries.items():
        check_query(query_id, name)


if __name__ == "__main__":
    main()
