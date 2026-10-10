"""Build the 6x9 KDP layout: PDF proof + Affinity-importable IDML.

usage: python3 build.py <manuscript.docx> <out_dir>
"""
import json
import os
import sys

import idml
import model
import proof


def main(docx, out_dir):
    os.makedirs(out_dir, exist_ok=True)
    sections = model.build_sections(docx)
    pdf = os.path.join(out_dir, 'Marketing_by_the_Numbers_KDP_6x9_proof.pdf')
    book, pages, toc = proof.typeset(sections, pdf)
    labels = [book.label(i) for i in range(len(pages))]
    out = os.path.join(out_dir, 'Marketing_by_the_Numbers_KDP_6x9.idml')
    idml.write(sections, pages, labels, book.arabic_start, out)
    plan = [{'page': labels[i], 'section': sections[p['section']].get('title') or sections[p['section']]['kind'],
             'role': p['role']} for i, p in enumerate(pages)]
    with open(os.path.join(out_dir, 'page_plan.json'), 'w') as f:
        json.dump(plan, f, indent=1, ensure_ascii=False)
    print(len(pages), 'pages ->', out)


if __name__ == '__main__':
    main(sys.argv[1], sys.argv[2])
