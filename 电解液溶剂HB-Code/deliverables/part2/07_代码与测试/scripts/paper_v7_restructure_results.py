# -*- coding: utf-8 -*-
"""【一次性溯源脚本】把 v6 的 build_paper_docx.py 结果章节从 3.1-3.17 重排为六节固定顺序。

它已经执行过一次；对 v7 源码重复执行会再次改写，因此只作改动溯源保留，不参与管线。
"""
import io, re, sys

PATH = r"E:\Claude Code\电解液溶剂-HB\论文\build_paper_docx.py"

SECTIONS = [
    (1, "模型层级与外部参考边界", [1, 15],
     "本节回答两个前置问题：研究对象是什么，以及目标有多可信。它对应工作包 WP1 与 WP7，"
     "主要图件为主图 1（三层研究框架 P/C/reference）与主图 2（外部锚点与方法 / 不确定度审计）。"
     "后面五节的所有判决都建立在这一边界之上：内部可复现不等于对实验有效。"),
    (2, "电子结构与介质物理如何改变排序", [2, 3, 4, 7, 8, 16],
     "本节回答“哪些物理改变排序”，对应 WP2（主图 3）。它按台阶逐级报告电子结构层（P0→P1、G1→G2）、"
     "连续介质层（P1→P2、介电极限）与自洽场求解所引入的位移与决策量，并给出逐家族口径。"),
    (3, "Li+ 配位条件态与还原态身份", [5, 9, 10, 17],
     "本节回答“为什么发生变化”，对应 WP3（主图 5）：Li+ 配位条件态如何改写排序、还原态身份如何分层、"
     "配位是否饱和，以及配位位移与分子内描述符标签的关系。"),
    (4, "不确定度感知的材料筛选", [6],
     "本节回答“哪些变化影响选择”，对应 WP4（主图 4）：把位移离散度变成一个可判定的不确定度预算与"
     "稳健翻转判据，并给出分辨率（unresolved）、Top-k 清单与 selection regret 的决策口径。"),
    (5, "模型位移与配位修正的可预测性", [13],
     "本节回答“能否廉价预测修正”，对应 WP5（主图 6）：在留一家族出（LOFO）外推下比较直接学习与位移学习，"
     "并同时报告预测误差与实际筛选决策指标。"),
    (6, "最小昂贵信息预算", [11, 12, 14],
     "本节回答“最少需要多少昂贵信息”，对应 WP6（主图 7）：最小计算层预算、broad pool 的实际演示"
     "与四策略主动学习重放。"),
]

REMAP = {1: "3.1.1", 15: "3.1.2",
         2: "3.2.1", 3: "3.2.2", 4: "3.2.3", 7: "3.2.4", 8: "3.2.5", 16: "3.2.6",
         5: "3.3.1", 9: "3.3.2", 10: "3.3.3", 17: "3.3.4",
         6: "3.4.1", 13: "3.5.1",
         11: "3.6.1", 12: "3.6.2", 14: "3.6.3"}

H2 = re.compile(r'^    h2\(doc, "3\.(\d+)\s+(.*)"\)\s*$')


def main():
    raw = io.open(PATH, encoding="utf-8").read()
    lines = raw.split("\n")

    i_a = next(i for i, l in enumerate(lines) if l.startswith("def write_results_a(doc):"))
    i_c = next(i for i, l in enumerate(lines) if l.startswith("def write_conclusion(doc):"))
    region = lines[i_a:i_c]

    head, blocks, order, cur = [], {}, [], None
    for l in region:
        if l.startswith("def write_results"):
            continue
        m = H2.match(l)
        if m:
            cur = int(m.group(1))
            blocks[cur] = [l]
            order.append(cur)
            continue
        if cur is None:
            head.append(l)
        else:
            blocks[cur].append(l)

    assert order == list(range(1, 18)), order
    assert len(head) == 1 and head[0].startswith('    h1(doc, "3'), head

    # 逐块去掉尾部空行
    for k in blocks:
        b = blocks[k]
        while len(b) > 1 and not b[-1].strip():
            b.pop()

    out = list(lines[:i_a])

    # 生成本节一个函数
    for k in order:
        body = list(blocks[k])
        m = H2.match(body[0])
        title = m.group(2).strip()
        body[0] = '    h3(doc, "%s  %s")' % (REMAP[k], title)
        out.append("def _r_%02d(doc):" % k)
        out.extend(body)
        out.append("")
        out.append("")

    # 六节聚合函数
    out.append("def write_results(doc):")
    out.append('    h1(doc, "3  结果与讨论")')
    for si, title, ids, bridge in SECTIONS:
        out.append('    h2(doc, "3.%d  %s")' % (si, title))
        out.append("    body(doc, %r)" % bridge)
        for k in ids:
            out.append("    _r_%02d(doc)" % k)
        out.append("")
    while out[-1] == "":
        out.pop()
    out.append("")
    out.append("")

    out.extend(lines[i_c:])
    text = "\n".join(out)

    # 交叉引用：把「3.N 节」里的旧编号换成新编号
    run = re.compile(r"3\.\d{1,2}(?:\s*[\u3001,\uff0c]\s*3\.\d{1,2})*\s*\u5c0f?\u8282")

    def fix(m):
        span = m.group(0)
        return re.sub(r"3\.(\d{1,2})",
                      lambda mm: REMAP.get(int(mm.group(1)), "3." + mm.group(1)),
                      span)

    text, n = run.subn(fix, text)

    # main() 调用聚合函数
    old_calls = "    write_results_a(doc)\n    write_results_b(doc)\n    write_results_c(doc)\n"
    assert old_calls in text
    text = text.replace(old_calls, "    write_results(doc)\n")

    io.open(PATH, "w", encoding="utf-8", newline="\n").write(text)
    print("remapped reference runs:", n)
    print("result blocks:", len(order))
    print("written bytes:", len(text.encode("utf-8")))


main()
