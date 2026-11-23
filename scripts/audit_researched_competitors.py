"""Compare SAVED real POST results with manually reviewed external sources.

No network, Gemini calls, or fake POST responses. The catalog does not
modify live API responses; never mistake research coverage for model accuracy.

Usage: python -m scripts.audit_researched_competitors --output research/audit
"""
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from urllib.parse import urlsplit

ROOT = Path(__file__).resolve().parent.parent
CATALOG = ROOT / 'research' / 'VERIFIED_COMPETITORS_2026-11-23.json'
BAD_NAME = re.compile(r'\b(?:placeholder|competitor\s*\d+|candidate\s*\d+|tbd)\b', re.I)


def norm(text: str) -> str:
    return ''.join(re.findall(r'[a-z0-9]+', text.casefold()))


def load_catalog(path: Path = CATALOG) -> dict:
    data = json.loads(path.read_text(encoding='utf-8'))
    keys: set[str] = set()
    for case in data['cases']:
        if case['key'] in keys:
            raise ValueError(f"Duplicate researched company: {case['key']}")
        keys.add(case['key'])
        names: set[str] = set()
        if len(case['competitors']) < 3:
            raise ValueError(f"Research case missing three credible peers: {case['key']}")
        for entry in case['competitors']:
            key = norm(entry['name'])
            if key in names:
                raise ValueError(f"Duplicate researched competitor: {entry['name']}")
            names.add(key)
            for field in ('official_product_source','comparative_editorial_source'):
                target = urlsplit(entry[field])
                if target.scheme != 'https' or not target.hostname or target.username:
                    raise ValueError(f"Source must be a public HTTPS URL: {entry['name']} {field}")
            if not entry['source_verified_capability'] or not entry['evaluation_tradeoff_not_measured']:
                raise ValueError(f"Empty research description: {entry['name']}")
    return data


def find_researched_peer(value: str, case: dict) -> dict | None:
    if BAD_NAME.search(value):
        return None
    n = norm(value)
    for peer in case['competitors']:
        if n in {norm(peer['name']), *(norm(a) for a in peer['aliases'])}:
            return peer
    return None


def audit_case(case: dict, root: Path = ROOT) -> dict:
    file = root / case['saved_real_post']
    response = json.loads(file.read_text(encoding='utf-8'))
    if response.get('success') is not True or response.get('status') != 'analysis_complete':
        raise ValueError(f"Not a saved success response: {file}")
    host = urlsplit(response['website']).hostname or ''
    expected_host = urlsplit(case['website']).hostname or ''
    if host.removeprefix('www.') != expected_host.removeprefix('www.'):
        raise ValueError(f"Saved website hostname differs from case: {case['key']}")
    observed = response['analysis']['competitor_analysis']['competitors']
    matched, rejected, outside = [], [], []
    for item in observed:
        name = item.get('name','')
        if BAD_NAME.search(name):
            rejected.append(name)
            continue
        peer = find_researched_peer(name,case)
        if peer is None:
            outside.append(name)
        elif peer['name'] not in matched:
            matched.append(peer['name'])
    return {
        'case':case['key'],
        'company':case['brand'],
        'saved_real_post':case['saved_real_post'],
        'saved_post_status':response.get('status'),
        'historical_post_not_v1_3':True,
        'recorded_model':response.get('model_info',{}).get('model'),
        'saved_observed_competitors':[x.get('name') for x in observed],
        'matched_to_external_research':matched,
        'bad_placeholder_names':rejected,
        'other_observed_candidates_not_in_selected_research':outside,
        'source_backed_competitors':[{'name':p['name'], 'official_product_source':p['official_product_source'], 'comparative_editorial_source':p['comparative_editorial_source']} for p in case['competitors']],
        'matched_observed_count':len(matched),
        'researched_competitor_count':len(case['competitors']),
        'semantic_caveat':'Research corroborates vendor identity and advertised product category, not all model-authored strengths, weaknesses, or numerical claims.'
    }


def render_markdown(catalog: dict, audits: list[dict]) -> str:
    out=['# Competitor evidence review — 23 November 2026','',
         '**Scope:** 3 real saved POST outputs (older versions) cross-checked against 10 manually researched alternatives. This is **not** new Gemini execution and not proof of generic live competitor search.','',
         '**Evidence rule:** Official product documentation supports product identity and stated capabilities; 2026 editorial comparison pages provide category-overlap context. Neither proves superiority, conversion uplift, pricing advantage or market share.','']
    lookup={a['case']:a for a in audits}
    for case in catalog['cases']:
        audit=lookup[case['key']]
        out += [f"## {case['brand']} — {case['sector']}", '',
                f"Recorded real POST: `{audit['saved_real_post']}`; original version (not v1.3).",
                f"Model's observed names: {', '.join(audit['saved_observed_competitors'])}.",
                f"**Research match:** {audit['matched_observed_count']} existing names matched against {audit['researched_competitor_count']} researched candidates.",'',
                '| Real competitor | Officially documented capability | Official source | Independent/editorial context |',
                '|---|---|---|---|']
        for p in case['competitors']:
            out.append(f"| {p['name']} | {p['source_verified_capability']} | [Product reference]({p['official_product_source']}) | [Comparison context]({p['comparative_editorial_source']}) |")
        out += ['', 'Scope distinctions (review questions, **not** tested weaknesses):','']
        for p in case['competitors']:
            out.append(f"- **{p['name']}:** {p['evaluation_tradeoff_not_measured']}")
        if audit['bad_placeholder_names']:
            out+=['', '**Rejected LLM draft name (not a researched company):** '+', '.join(audit['bad_placeholder_names'])+'.']
        if audit['other_observed_candidates_not_in_selected_research']:
            out+=['', '**Other historical model candidates:** '+', '.join(audit['other_observed_candidates_not_in_selected_research'])+'. Not automatically fake; simply outside this narrow comparison set.']
        if case['key']=='shopify':
            out+=['', '**Important:** BigCommerce is a fourth independently researched alternative, not a name present in the saved Shopify JSON. The real API output was NOT edited.']
        out+=['']
    out+=['## Honest limits','',
          '- All saved POSTs are real recorded requests from earlier releases. `v1.3` Render **Live** and `/health` **1.3.0** were separately evidenced; a fresh v1.3 POST is NOT claimed. Do not repeat earlier POSTs merely to inflate the evidence count.',
          '- The researched catalog is manually curated and versioned; the deployed generic endpoint does not automatically use these sources or perform external search. This is research evidence for the practical-test competitor section, not a claim of automatic factual grounding.',
          '- Product capabilities may vary by plan. Do not convert source documentation into fabricated negative competitor weaknesses.',
          '- If the evaluator requires current external research for every arbitrary submitted domain, that is a separate integration requiring a search provider and runtime validation; it is not silently solved here.',
          '', '## Reproducible audit (offline, no quota)', '',
          '```powershell', '.\\.venv\\Scripts\\python.exe -m scripts.audit_researched_competitors --output research/audit', '```',
          '', 'Output: one `audit-summary.json` and this Markdown report. Both preserve source version provenance.', '']
    return '\n'.join(out)


def main() -> None:
    parser=argparse.ArgumentParser()
    parser.add_argument('--output',default='research/audit')
    args=parser.parse_args()
    catalog=load_catalog()
    audits=[audit_case(c) for c in catalog['cases']]
    output=Path(args.output)
    if not output.is_absolute():
        output=ROOT/output
    output.mkdir(parents=True,exist_ok=True)
    (output/'audit-summary.json').write_text(json.dumps(audits,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    (output/'COMPETITOR_EVIDENCE_REVIEW.md').write_text(render_markdown(catalog,audits),encoding='utf-8')
    for a in audits:
        print(f"{a['company']}: saved POST analysis_complete, externally sourced {a['researched_competitor_count']} peers, matched observed {a['matched_observed_count']}, broken placeholders {len(a['bad_placeholder_names'])}")
    print('Research report and JSON audit written to',output)


if __name__=='__main__':
    main()
