#!/usr/bin/env python3
"""Citation verifier for the academic-paper skill.

Runs a four-tier cascade against every entry in a .bib file:

  Tier 1: CrossRef by DOI (if entry already has one)
  Tier 2: CrossRef title-search
  Tier 3: OpenAlex title-search with LaTeX-cleaned title (broad coverage, 250M works)
  Tier 4: arXiv title-search

Implements the cascade described in rules/citations.md. The OpenAlex tier is the
workhorse: it finds papers that CrossRef's title-search misses (recent preprints,
non-DOI conference papers, papers with messy LaTeX titles). The script cleans LaTeX
escapes from the title before each search, so entries with `{...}`, `\\cmd{}`, or
`$...$` in the title still match.

Usage:
    python3 tools/bibverify.py refs.bib
    python3 tools/bibverify.py refs.bib --json
    python3 tools/bibverify.py refs.bib --update-provenance  # write % verified: lines

Exit code 0 if every entry PASSes or already has provenance; 1 if any entry FAILs.
"""

import argparse
import datetime as dt
import json
import os
import re
import sys
import time
from urllib.parse import quote

try:
    import requests
except ImportError:
    print('FAIL: bibverify.py requires the "requests" library. '
          'Install with: pip install requests', file=sys.stderr)
    sys.exit(2)


HEADERS = {'User-Agent': 'bibverify.py academic-paper-skill'}
SLEEP = 0.15  # politeness between API calls
IMS_JOURNALS = {
    'statistical science', 'annals of statistics', 'annals of applied statistics',
    'electronic journal of statistics', 'annals of probability', 'bernoulli',
    'annals of applied probability',
}


# ============================================================================
# Bib parsing (with proper balanced-brace handling)
# ============================================================================

def _extract_balanced(text, start_idx):
    """Given text starting at an open brace, return (content, end_idx) for the matching close."""
    assert text[start_idx] == '{'
    depth, i = 1, start_idx + 1
    while i < len(text) and depth > 0:
        if text[i] == '{':
            depth += 1
        elif text[i] == '}':
            depth -= 1
            if depth == 0:
                return text[start_idx + 1:i], i + 1
        i += 1
    return None, i


def _parse_fields(raw):
    """Parse fields from an entry's raw text, handling nested braces in values."""
    fields = {}
    i = 0
    while i < len(raw):
        fm = re.search(r'(\w+)\s*=\s*([{"])', raw[i:])
        if not fm:
            break
        field_name = fm.group(1).lower()
        delim = fm.group(2)
        val_pos = i + fm.end() - 1
        if delim == '{':
            val, end = _extract_balanced(raw, val_pos)
            if val is None:
                break
            i = end
        else:
            end = raw.find('"', val_pos + 1)
            if end == -1:
                break
            val = raw[val_pos + 1:end]
            i = end + 1
        fields[field_name] = val.strip()
    return fields


def parse_bib(path):
    """Yield entry dicts with key, type, raw, fields, has_provenance, start, end.

    Provenance is detected by walking backward from the entry's start line and
    looking at the immediately preceding non-blank line. This avoids the trap
    where a `% verified:` line from the previous entry sits within an arbitrary
    fixed-size prefix window.
    """
    with open(path) as fh:
        text = fh.read()
    entries = []
    entry_re = re.compile(r'@(\w+)\s*\{\s*([^,\s]+)\s*,', re.MULTILINE)
    for m in entry_re.finditer(text):
        depth, i = 0, m.end()
        while i < len(text):
            if text[i] == '{':
                depth += 1
            elif text[i] == '}':
                if depth == 0:
                    break
                depth -= 1
            i += 1
        raw = text[m.start(): i + 1]
        fields = _parse_fields(raw)

        # Walk backward to find the immediately preceding non-blank line.
        # If it is a `% verified:` line, this entry has provenance.
        # If we hit any other content (closing brace of a prior entry, etc.)
        # before finding a `% verified:` line, this entry lacks provenance.
        pos = m.start() - 1
        prov_line = None
        while pos >= 0:
            # Find the line containing pos
            line_start = text.rfind('\n', 0, pos) + 1
            line = text[line_start: pos + 1]
            stripped = line.strip()
            if not stripped:
                pos = line_start - 1
                continue
            if stripped.startswith('% verified:'):
                prov_line = stripped
            break

        entries.append({
            'key': m.group(2).strip(),
            'type': m.group(1).lower(),
            'raw': raw,
            'fields': fields,
            'has_provenance': prov_line is not None,
            'provenance_line': prov_line,
            'start': m.start(),
            'end': i + 1,
        })
    return entries


def clean_title(t):
    """Strip LaTeX escapes and math from a title so it can be sent to a search API."""
    if not t:
        return ''
    t = re.sub(r'\$[^$]*\$', '', t)
    t = re.sub(r'\\[a-zA-Z]+\{([^}]*)\}', r'\1', t)
    t = re.sub(r'\\[a-zA-Z]+', '', t)
    t = t.replace('\\', '').replace('{', '').replace('}', '')
    t = re.sub(r'\s+', ' ', t).strip()
    return t


def norm(t):
    return re.sub(r'[^a-z0-9 ]+', '', (t or '').lower()).strip()


# ============================================================================
# API queries
# ============================================================================

def crossref_doi(doi):
    url = f'https://api.crossref.org/works/{quote(doi, safe="")}'
    try:
        r = requests.get(url, headers=HEADERS, timeout=15)
    except requests.RequestException as e:
        return None, f'network error: {e}'
    if r.status_code != 200:
        return None, f'HTTP {r.status_code}'
    msg = r.json().get('message', {})
    return {
        'title': (msg.get('title') or [''])[0],
        'authors': [a.get('family', '') for a in msg.get('author', [])],
        'year': (msg.get('issued', {}).get('date-parts') or [[None]])[0][0],
        'container': (msg.get('container-title') or [''])[0],
        'doi': msg.get('DOI'),
        'subtype': msg.get('subtype'),
    }, None


def crossref_search(title, author):
    params = []
    if title:
        params.append(f'query.bibliographic={quote(title)}')
    if author:
        params.append(f'query.author={quote(author)}')
    params.append('rows=3')
    url = 'https://api.crossref.org/works?' + '&'.join(params)
    try:
        r = requests.get(url, headers=HEADERS, timeout=15)
    except requests.RequestException as e:
        return None, f'network error: {e}'
    if r.status_code != 200:
        return None, f'HTTP {r.status_code}'
    items = r.json().get('message', {}).get('items', [])
    return [{
        'score': it.get('score', 0),
        'title': (it.get('title') or [''])[0],
        'authors': [a.get('family', '') for a in it.get('author', [])],
        'year': (it.get('issued', {}).get('date-parts') or [[None]])[0][0],
        'doi': it.get('DOI'),
    } for it in items], None


def openalex_search(title):
    """Title-only search; OpenAlex's author filter is too strict for accented names."""
    url = f'https://api.openalex.org/works?search={quote(title)}&per-page=5'
    try:
        r = requests.get(url, headers=HEADERS, timeout=15)
    except requests.RequestException as e:
        return None, f'network error: {e}'
    if r.status_code != 200:
        return None, f'HTTP {r.status_code}'
    return [{
        'title': w.get('title'),
        'year': w.get('publication_year'),
        'doi': (w.get('doi') or '').replace('https://doi.org/', '') if w.get('doi') else None,
        'openalex_id': (w.get('id') or '').replace('https://openalex.org/', ''),
        'authors': [a.get('author', {}).get('display_name', '') for a in w.get('authorships', [])],
    } for w in r.json().get('results', [])], None


def arxiv_search(title):
    """arXiv API title search with cleaned title."""
    words = [w for w in re.findall(r'\w+', title)[:6] if len(w) > 2]
    if not words:
        return [], None
    q = '+AND+'.join(f'ti:{quote(w)}' for w in words)
    url = f'http://export.arxiv.org/api/query?search_query={q}&max_results=3'
    try:
        r = requests.get(url, headers=HEADERS, timeout=15)
    except requests.RequestException as e:
        return None, f'network error: {e}'
    if r.status_code != 200:
        return None, f'HTTP {r.status_code}'
    results = []
    for entry in re.finditer(r'<entry>(.*?)</entry>', r.text, re.DOTALL):
        txt = entry.group(1)
        id_m = re.search(r'<id>http[^<]*?arxiv\.org/abs/([^<]+)</id>', txt)
        title_m = re.search(r'<title>([^<]+)</title>', txt, re.DOTALL)
        if id_m and title_m:
            results.append({'arxiv_id': id_m.group(1).strip(),
                            'title': title_m.group(1).strip()})
    return results, None


# ============================================================================
# Match scoring
# ============================================================================

def best_title_match(results, target_title, author=''):
    """Score candidates and return the best match (or None) for a title-search result."""
    target = norm(target_title)
    a_norm = norm(author)
    candidates = []
    for w in results:
        w_title = norm(w.get('title', ''))
        if not w_title:
            continue
        if w_title == target:
            candidates.append((w, 100))
            continue
        if len(target) > 30 and target in w_title:
            candidates.append((w, 90))
            continue
        if len(w_title) > 30 and w_title in target:
            candidates.append((w, 85))
            continue
        t_words = set(target.split())
        w_words = set(w_title.split())
        if len(t_words) >= 4:
            overlap = len(t_words & w_words) / len(t_words)
            if overlap >= 0.75:
                authors = [norm(a) for a in (w.get('authors') or [])]
                bonus = 10 if (a_norm and any(a_norm.split()[0] in a for a in authors)) else 0
                candidates.append((w, int(overlap * 70) + bonus))
    if not candidates:
        return None
    candidates.sort(key=lambda x: x[1], reverse=True)
    return candidates[0][0] if candidates[0][1] >= 70 else None


# ============================================================================
# Verification cascade
# ============================================================================

def verify(entry):
    """Return (status, source, message). Source is human-readable provenance."""
    fields = entry['fields']
    doi = fields.get('doi')
    raw_title = fields.get('title', '')
    title = clean_title(raw_title)
    author = fields.get('author', '').split(' and ')[0].split(',')[0].strip()
    year = fields.get('year', '')
    eprint = fields.get('eprint') or fields.get('arxiv')
    journal = fields.get('journal', '').lower()

    # Tier 1: CrossRef by DOI
    if doi:
        data, err = crossref_doi(doi)
        time.sleep(SLEEP)
        if data and not err:
            if data.get('subtype') == 'retraction':
                return ('FAIL', f'crossref:{doi}', 'cited paper is a retraction notice')
            problems = []
            if title and data.get('title') and norm(data['title']) != norm(title):
                problems.append(f"title mismatch (crossref='{data['title']}')")
            if author and data.get('authors') and author.lower() not in data['authors'][0].lower():
                problems.append(f"first-author mismatch (crossref='{data['authors'][0]}')")
            if year and data.get('year') and str(year) != str(data['year']):
                problems.append(f"year mismatch (crossref={data['year']})")
            if not problems:
                return ('PASS', f'crossref {doi}', 'DOI resolves, metadata matches')
            return ('WARN', f'crossref {doi}', '; '.join(problems))
        return ('FAIL', 'crossref', f'DOI {doi} did not resolve ({err})')

    # Tier 1b: CrossRef title+author search
    if title:
        cands, _ = crossref_search(title, author)
        time.sleep(SLEEP)
        if cands:
            best = max(cands, key=lambda c: c.get('score', 0))
            if best.get('score', 0) >= 3.0 and norm(best['title']) == norm(title):
                return ('WARN', f'crossref-search {best["doi"]}',
                        f'matched; add doi={best["doi"]} to .bib')

    # Tier 2: OpenAlex with cleaned title (the workhorse)
    if title:
        results, _ = openalex_search(title)
        time.sleep(SLEEP)
        if results:
            match = best_title_match(results, title, author)
            if match:
                oa_id = match['openalex_id']
                match_doi = match.get('doi') or ''
                # OpenAlex returns arXiv DOIs like 10.48550/arxiv.2407.12345
                arxiv_m = re.match(r'^10\.48550/arxiv\.(.+)$', match_doi, re.IGNORECASE)
                if arxiv_m:
                    return ('WARN', f'openalex {oa_id}',
                            f'arXiv match; add eprint={arxiv_m.group(1)} to .bib')
                if match_doi:
                    return ('WARN', f'openalex {oa_id}',
                            f'OpenAlex match; add doi={match_doi} to .bib')
                return ('PASS', f'openalex {oa_id}',
                        'OpenAlex match (no DOI; record as % verified: openalex)')

    # Tier 3: arXiv
    if eprint:
        return ('PASS', f'arxiv {eprint}', 'arXiv ID present')
    if title:
        ids, _ = arxiv_search(title)
        time.sleep(SLEEP)
        if ids:
            match = best_title_match(ids, title, author)
            if match:
                return ('WARN', f'arxiv {match["arxiv_id"]}',
                        f'arXiv match; add eprint={match["arxiv_id"]} to .bib')

    # Tier 4: IMS hint (manual Project Euclid verification)
    if any(j in journal for j in IMS_JOURNALS):
        return ('FAIL', 'project-euclid',
                'IMS journal; verify on projecteuclid.org and record % verified: euclid')

    return ('FAIL', 'none',
            'no verification source matched; entry needs DOI, OpenAlex ID, or arXiv ID')


# ============================================================================
# Bib update
# ============================================================================

def update_bib(path, entries, results, also_add_fields=True):
    """Insert % verified: lines (and optionally doi/eprint fields) into the .bib.

    PASS entries get % verified: <source> <date>.
    WARN entries that the script can resolve (DOI or eprint extracted from message)
    also get the corresponding field added if missing, then are stamped as well.
    """
    today = dt.date.today().isoformat()
    with open(path) as fh:
        text = fh.read()
    by_key = {e['key']: e for e in entries}
    updates = 0

    # Process in reverse offset order to preserve positions
    sorted_results = sorted(
        results,
        key=lambda r: by_key.get(r['key'], {}).get('start', -1),
        reverse=True,
    )

    for r in sorted_results:
        if r['key'] not in by_key:
            continue
        entry = by_key[r['key']]
        if entry['has_provenance']:
            continue

        status = r['status']
        source = r['source']
        msg = r['message']

        if status == 'PASS':
            value, kind = None, None
        elif status == 'WARN' and also_add_fields:
            doi_m = re.search(r'add doi=(\S+)', msg)
            eprint_m = re.search(r'add eprint=(\S+)', msg)
            if doi_m:
                value, kind = doi_m.group(1).rstrip(' .,'), 'doi'
            elif eprint_m:
                value, kind = eprint_m.group(1).rstrip(' .,'), 'eprint'
            else:
                value, kind = None, None
        else:
            continue

        # Add missing field
        if value and kind:
            entry_text = text[entry['start']:entry['end']]
            if not re.search(rf'\b{kind}\s*=', entry_text):
                new_entry = entry_text.rstrip().rstrip('}').rstrip()
                if not new_entry.endswith(','):
                    new_entry += ','
                new_entry += f'\n  {kind} = {{{value}}}\n}}'
                text = text[:entry['start']] + new_entry + text[entry['end']:]

        # Insert provenance line
        src_clean = source.split(' (')[0].replace('crossref-search', 'crossref')
        line = f'% verified: {src_clean} {today}\n'
        text = text[:entry['start']] + line + text[entry['start']:]
        updates += 1

    if updates:
        with open(path, 'w') as fh:
            fh.write(text)
    return updates


# ============================================================================
# CLI
# ============================================================================

def main():
    parser = argparse.ArgumentParser(description='Citation verifier (CrossRef, OpenAlex, arXiv)')
    parser.add_argument('bib', help='Path to .bib file')
    parser.add_argument('--json', action='store_true', help='Emit JSON to stdout')
    parser.add_argument('--update-provenance', action='store_true',
                        help='Write %% verified: lines and add doi/eprint fields where resolved')
    parser.add_argument('--skip-existing', action='store_true', default=True,
                        help='Skip entries that already have provenance (default on)')
    args = parser.parse_args()

    if not os.path.exists(args.bib):
        print(f'FAIL: bib file not found: {args.bib}', file=sys.stderr)
        sys.exit(1)

    entries = parse_bib(args.bib)
    results = []
    for entry in entries:
        if entry['has_provenance'] and args.skip_existing:
            results.append({'key': entry['key'], 'status': 'SKIP', 'source': 'pre-recorded',
                            'message': entry['provenance_line']})
            continue
        status, source, msg = verify(entry)
        results.append({'key': entry['key'], 'status': status, 'source': source, 'message': msg})

    counts = {'PASS': 0, 'WARN': 0, 'FAIL': 0, 'SKIP': 0}
    for r in results:
        counts[r['status']] += 1

    if args.update_provenance:
        n = update_bib(args.bib, entries, results)
        if not args.json:
            print(f'Inserted {n} % verified: lines (and added doi/eprint fields where resolved)')

    if args.json:
        print(json.dumps({'summary': counts, 'results': results}, indent=2))
    else:
        for r in results:
            print(f"  [{r['status']:>4}] {r['key']:30s} {r['source']:35s} {r['message']}")
        print(f"\nSummary: {counts}")

    sys.exit(0 if counts['FAIL'] == 0 else 1)


if __name__ == '__main__':
    main()
