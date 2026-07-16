# scripts/10_04_auth_passthrough_demo.py
"""10.04 BFF 配置与鉴权透传演示。

【本课要感受的四件事】
1. 无用户 Token → BFF 401
2. 伪造 tenantId 查询参 → 仍用鉴权结果里的租户
3. 非法 modelId → 403
4. 盖好的内部头到达 ai-service（echo + SSE done）

工作目录：必须在 ai-bff/ 下；会临时子进程拉起 ../ai-service。
"""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.lessons.m10_04_auth_passthrough import demo_suite  # noqa: E402

NOTE_PATH = ROOT / "notes" / "auth_passthrough_result.md"


def main() -> None:
    print("=" * 52, "CONFIG")
    print("BFF 验用户；下游只收内部头")
    print("ROOT =", ROOT)

    suite = demo_suite()
    note: list[str] = ["# 10.04 鉴权透传 · 实跑记录\n", ""]

    print("\n" + "=" * 52, "STEP 0 · 演示账号")
    for row in suite["cheat_sheet"]:
        print(f"  {row['authorization']} → tenant={row['tenant_id']} models={row['models']}")
    note.append("## 演示账号\n")
    for row in suite["cheat_sheet"]:
        note.append(
            f"- `{row['authorization']}` → tenant=`{row['tenant_id']}` models=`{row['models']}`"
        )
    note.append("")

    print("\n" + "=" * 52, "STEP 1 · 无用户 Token")
    n = suite["no_token"]
    print(f"  status={n['status_code']} body={n['body']}")
    assert n["status_code"] == 401
    print("ASSERT: BFF 401 → PASS")
    note.append("## STEP 1\n")
    note.append(f"- 无 Token → `{n['status_code']}`\n")

    print("\n" + "=" * 52, "STEP 2 · 伪造租户查询参")
    f = suite["forged"]
    print(
        f"  JWT租户={f['principal_tenant']} 伪造={f['forged_query']} "
        f"下游头={f['downstream_tenant']}"
    )
    assert f["ignored"]
    print("ASSERT: 仍用 JWT 租户 → PASS")
    note.append("## STEP 2\n")
    note.append(
        f"- 伪造 `{f['forged_query']}` 被忽略，下游=`{f['downstream_tenant']}`\n"
    )

    print("\n" + "=" * 52, "STEP 3 · 模型白名单")
    b = suite["bad_model"]
    print(f"  status={b['status_code']} body={b['body']}")
    assert b["status_code"] == 403
    print("ASSERT: 403 model not allowed → PASS")
    note.append("## STEP 3\n")
    note.append(f"- 非法 modelId → `{b['status_code']}`\n")

    print("\n" + "=" * 52, "STEP 4 · 上下文到达 ai-service")
    e = suite["e2e"]
    print(f"  echo={e['echo']}")
    print(f"  done={e['done']}")
    assert e["echo"].get("tenant_id") == "tenant-a"
    assert e["done"].get("request_id") == "req-e2e-004"
    print("ASSERT: tenant + request_id 到达 → PASS")
    note.append("## STEP 4\n")
    note.append(f"- echo: `{e['echo']}`")
    note.append(f"- done: `{e['done']}`\n")

    print("\n" + "=" * 52, "STEP 5 · curl 提示")
    print("  # A: ai-service :8001  B: ai-bff :8088")
    print(
        "  curl -N -X POST 'http://127.0.0.1:8088/api/chat/stream?tenantId=tenant-b' \\"
    )
    print("    -H 'Authorization: Bearer tok-alice' -H 'Content-Type: application/json' \\")
    print('    -d \'{"message":"hello","modelId":"default"}\'')
    print("  # 期望：流式 token…；响应头 X-Resolved-Tenant: tenant-a（不是 b）")
    note.append("## STEP 5 · curl\n")
    note.append(
        "```bash\n"
        "curl -N -X POST 'http://127.0.0.1:8088/api/chat/stream?tenantId=tenant-b' \\\n"
        "  -H 'Authorization: Bearer tok-alice' -H 'Content-Type: application/json' \\\n"
        "  -d '{\"message\":\"hello\",\"modelId\":\"default\"}'\n"
        "```\n"
    )

    assert suite["ok"]
    NOTE_PATH.parent.mkdir(parents=True, exist_ok=True)
    NOTE_PATH.write_text("\n".join(note), encoding="utf-8")
    print("\n笔记已写入:", NOTE_PATH)
    print("SUMMARY: auth_passthrough 验收通过")


if __name__ == "__main__":
    main()
