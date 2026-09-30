import html
import xml.etree.ElementTree as ET


def junit(results):
    root = ET.Element(
        "testsuite",
        name="AgentFixture",
        tests=str(len(results)),
        failures=str(sum(bool(r["failures"]) for r in results)),
        errors=str(sum(bool(r.get("error")) for r in results)),
    )
    for row in results:
        case = ET.SubElement(
            root, "testcase", name=row["name"], classname="agentfixture"
        )
        if row.get("error"):
            ET.SubElement(case, "error", message=row["error"])
        elif row["failures"]:
            ET.SubElement(case, "failure", message="; ".join(row["failures"]))
    return ET.tostring(root, encoding="unicode", xml_declaration=True)


def render(results):
    esc = html.escape
    rows = "".join(
        "<article><h2>"
        + esc(row["name"])
        + '</h2><p class="status">'
        + ("INVALID" if row.get("error") else "FAIL" if row["failures"] else "PASS")
        + "</p><ul>"
        + "".join(
            "<li>" + esc(f) + "</li>"
            for f in ([row["error"]] if row.get("error") else row["failures"])
        )
        + "</ul></article>"
        for row in results
    )
    passed = sum(not row["failures"] and not row.get("error") for row in results)
    return f'<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1"><title>AgentFixture report</title><style>body{{background:#09090c;color:#ececf1;font:16px system-ui;max-width:960px;margin:48px auto;padding:0 24px}}h1{{font-size:42px}}header p,.status{{color:#f2982d}}article{{border-top:1px solid #303039;padding:20px 0}}h2{{overflow-wrap:anywhere}}li{{line-height:1.8}}footer{{color:#aaa}}</style><header><p>MOHAPX-V-IT / AGENT TESTING</p><h1>AgentFixture</h1><p>{passed} / {len(results)} scenarios passed</p></header>{rows}<footer>Local trace assertions. No model or external tool executed.</footer></html>'
