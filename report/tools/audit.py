#!/usr/bin/env python3
"""Mechanical Pre-flight Protocol for the academic-paper skill.

Runs the five non-negotiable checks defined in SKILL.md and emits structured output.
Exit code 0 if all PASS, 1 if any FAIL. The protocol is intentionally mechanical so the
agent cannot fake the result by describing it.

Usage:
    python3 tools/audit.py                              # auto-detect main.tex, refs.bib
    python3 tools/audit.py --main main.tex --bib refs.bib
    python3 tools/audit.py --no-compile                 # skip latexmk for fast polling
    python3 tools/audit.py --json                       # JSON output for parsing

The five checks:
  1. Citation provenance: every .bib entry has a "% verified:" line.
  2. AI writing signs: the canonical grep produces < 5 hits.
  3. Em-dash absence: zero em-dashes in the manuscript.
  4. Contribution delivery: every \\ref{} in the contribution block resolves.
  5. Compile clean: latexmk finishes with zero errors.
"""

import argparse
import glob
import json
import os
import re
import subprocess
import sys


AI_GREP_REGEX = (
    r'delve|tapestry|intricate|multifaceted|navigate the (landscape|complexities|complex)|'
    r'in the realm of|in the landscape of|robust(ly)?|holistic|leverage|foster(ing)?|'
    r'underscore|showcase|garner|testament|encompass|exemplif|stands as a|marks a|serves as a|'
    r'pivotal|paramount|vibrant|enduring|groundbreaking|renowned|cutting-edge|paradigm shift|'
    r'game-changer|unprecedented|remarkable|striking|key (takeaway|insight|finding)|'
    r'valuable insight|broader implication|highlighting|emphasizing|ensuring (that )?|'
    r'reflecting (the|broader)|contributing to (the )?|cultivating|it is important to note|'
    r'it is worth (noting|pointing out|mentioning)|interestingly|notably|'
    r'it is widely (believed|held|accepted)|many (have argued|argue)|studies suggest|'
    r'the literature indicates|experts agree'
)


def detect_main_tex(cwd):
    if os.path.exists(os.path.join(cwd, 'main.tex')):
        return 'main.tex'
    for tex in sorted(glob.glob(os.path.join(cwd, '*.tex'))):
        try:
            with open(tex) as fh:
                head = fh.read(4000)
        except OSError:
            continue
        if '\\documentclass' in head:
            return os.path.basename(tex)
    return None


def detect_bib(cwd):
    if os.path.exists(os.path.join(cwd, 'refs.bib')):
        return 'refs.bib'
    bibs = glob.glob(os.path.join(cwd, '*.bib'))
    if len(bibs) == 1:
        return os.path.basename(bibs[0])
    if not bibs:
        return None
    bibs.sort(key=lambda p: os.path.getsize(p), reverse=True)
    return os.path.basename(bibs[0])


def check_citation_provenance(bib_path):
    if not bib_path or not os.path.exists(bib_path):
        return ('FAIL', f'.bib file not found: {bib_path}', {})
    with open(bib_path) as fh:
        text = fh.read()
    verified = len(re.findall(r'^%\s*verified:', text, flags=re.MULTILINE))
    entries = len(re.findall(r'^@\w+\s*\{', text, flags=re.MULTILINE))
    detail = {'verified_lines': verified, 'bib_entries': entries}
    if entries == 0:
        return ('FAIL', 'no .bib entries found', detail)
    if verified >= entries:
        return ('PASS', f'{verified} of {entries} entries verified', detail)
    return ('FAIL',
            f'{verified} of {entries} entries have % verified: provenance; '
            f'{entries - verified} missing. Run tools/bibverify.py.',
            detail)


def check_ai_signs(tex_path, threshold):
    if not os.path.exists(tex_path):
        return ('FAIL', f'.tex file not found: {tex_path}', {})
    try:
        out = subprocess.run(
            ['grep', '-niE', AI_GREP_REGEX, tex_path],
            capture_output=True, text=True, check=False
        )
    except FileNotFoundError:
        return ('FAIL', 'grep not available on this system', {})
    hits = out.stdout.splitlines() if out.stdout else []
    detail = {'count': len(hits), 'sample': hits[:5]}
    if len(hits) < threshold:
        return ('PASS', f'{len(hits)} AI-vocabulary hits (threshold {threshold})', detail)
    return ('FAIL',
            f'{len(hits)} AI-vocabulary hits exceed threshold {threshold}; '
            f'apply rules/ai-writing-signs.md section 8 (the cure)',
            detail)


def check_em_dashes(tex_path):
    if not os.path.exists(tex_path):
        return ('FAIL', f'.tex file not found: {tex_path}', {})
    with open(tex_path) as fh:
        text = fh.read()
    unicode_count = text.count('—')
    latex_count = len(re.findall(r'(?<!-)---(?!-)', text))
    total = unicode_count + latex_count
    detail = {'unicode_em_dashes': unicode_count, 'latex_em_dashes': latex_count}
    if total == 0:
        return ('PASS', 'no em-dashes found', detail)
    return ('FAIL',
            f'{total} em-dashes found ({unicode_count} unicode, {latex_count} latex); '
            f'replace with commas, periods, parentheses, or colons',
            detail)


CONTRIBUTION_PATTERNS = [
    # Prose framings (preferred; flows naturally without sectioning machinery)
    r'(?i)The contributions of this (paper|work|study)\s+are',
    r'(?i)Our contributions are',
    r'(?i)We make the following contributions',
    r'(?i)This (paper|work) makes the following contributions',
    r'(?i)The main contributions of this (paper|work) are',
    r'(?i)We summari[sz]e our contributions',
    # Header framings (legacy; not preferred but still detected)
    r'\\paragraph\*?\{Contributions?\}',
    r'\\subsection\*?\{Contributions?\}',
    r'\\section\*?\{Contributions?\}',
    r'\\textbf\{Contributions?\}',
]


def extract_contribution_block(tex_text):
    for pattern in CONTRIBUTION_PATTERNS:
        m = re.search(pattern, tex_text)
        if m:
            start = m.end()
            tail = tex_text[start:start + 4000]
            stop = re.search(r'\\(section|subsection|paragraph)\b', tail)
            return tail[: stop.start()] if stop else tail
    return None


def check_contribution_delivery(tex_path):
    if not os.path.exists(tex_path):
        return ('FAIL', f'.tex file not found: {tex_path}', {})
    with open(tex_path) as fh:
        text = fh.read()
    block = extract_contribution_block(text)
    if block is None:
        return ('FAIL',
                'no contribution paragraph found; expected \\paragraph{Contributions} '
                'or similar header in the introduction',
                {})
    promised = set()
    for rx in (r'\\(?:auto)?ref\{([^}]+)\}', r'\\Cref\{([^}]+)\}', r'\\cref\{([^}]+)\}'):
        for m in re.finditer(rx, block):
            promised.add(m.group(1))
    if not promised:
        return ('FAIL',
                'contribution paragraph contains no \\ref{} pointers to delivering '
                'sections/theorems/algorithms/tables',
                {'block_preview': block[:300]})
    missing = [k for k in promised if not re.search(r'\\label\{' + re.escape(k) + r'\}', text)]
    detail = {'promised_count': len(promised), 'promised': sorted(promised), 'missing': missing}
    if not missing:
        return ('PASS', f'all {len(promised)} promised \\ref{{}} pointers resolve', detail)
    return ('FAIL',
            f'{len(missing)} of {len(promised)} contribution pointers unresolved: {missing}',
            detail)


def check_compile(tex_path, build_dir, timeout):
    if not os.path.exists(tex_path):
        return ('FAIL', f'.tex file not found: {tex_path}', {})
    try:
        result = subprocess.run(
            ['latexmk', '-pdf', f'-outdir={build_dir}', '-interaction=nonstopmode', tex_path],
            capture_output=True, text=True, check=False, timeout=timeout
        )
    except FileNotFoundError:
        return ('FAIL', 'latexmk not available; install TeX Live or MacTeX', {})
    except subprocess.TimeoutExpired:
        return ('FAIL', f'latexmk timed out after {timeout}s', {})
    log = (result.stdout or '') + (result.stderr or '')
    error_markers = len(re.findall(r'^!\s', log, flags=re.MULTILINE))
    undefined_ref = len(re.findall(r'LaTeX Warning: Reference', log))
    undefined_cite = len(re.findall(r'LaTeX Warning: Citation', log))
    detail = {
        'returncode': result.returncode,
        'error_markers': error_markers,
        'undefined_refs': undefined_ref,
        'undefined_cites': undefined_cite,
    }
    if result.returncode == 0 and error_markers == 0 and undefined_ref == 0 and undefined_cite == 0:
        return ('PASS', 'compile clean', detail)
    return ('FAIL',
            f'returncode={result.returncode}, errors={error_markers}, '
            f'undefined refs={undefined_ref}, undefined cites={undefined_cite}',
            detail)


def main():
    parser = argparse.ArgumentParser(description='Pre-flight Protocol for academic-paper skill')
    parser.add_argument('--main', help='Main .tex file (default: auto-detect)')
    parser.add_argument('--bib', help='Bibliography .bib file (default: auto-detect)')
    parser.add_argument('--build', default='build', help='latexmk output dir (default: build)')
    parser.add_argument('--no-compile', action='store_true', help='Skip check 5 (latexmk)')
    parser.add_argument('--ai-threshold', type=int, default=10,
                        help='Max AI-vocabulary hits before FAIL (default: 10). '
                             'A few hits in technical prose are normal human writing; '
                             '10+ in a paper-length manuscript suggests LLM contamination.')
    parser.add_argument('--timeout', type=int, default=600, help='latexmk timeout in seconds')
    parser.add_argument('--json', action='store_true', help='Emit JSON to stdout')
    args = parser.parse_args()

    cwd = os.getcwd()
    main_tex = args.main or detect_main_tex(cwd)
    bib = args.bib or detect_bib(cwd)

    if main_tex is None:
        msg = 'no .tex file containing \\documentclass found in current directory'
        if args.json:
            print(json.dumps({'overall': 'FAIL', 'message': msg}))
        else:
            print(f'FAIL: {msg}', file=sys.stderr)
        sys.exit(1)

    checks = [
        ('1-citation-provenance', *check_citation_provenance(bib)),
        ('2-ai-writing-signs', *check_ai_signs(main_tex, args.ai_threshold)),
        ('3-em-dashes', *check_em_dashes(main_tex)),
        ('4-contribution-delivery', *check_contribution_delivery(main_tex)),
    ]
    if args.no_compile:
        checks.append(('5-compile', 'SKIP', 'skipped per --no-compile', {}))
    else:
        checks.append(('5-compile', *check_compile(main_tex, args.build, args.timeout)))

    failures = [c for c in checks if c[1] == 'FAIL']
    overall = 'PASS' if not failures else 'FAIL'

    result = {
        'overall': overall,
        'main_tex': main_tex,
        'bib': bib,
        'checks': [{'name': c[0], 'status': c[1], 'message': c[2], 'detail': c[3]} for c in checks],
    }

    if args.json:
        print(json.dumps(result, indent=2))
    else:
        print(f'Pre-flight Protocol on {main_tex} (bib: {bib or "n/a"})')
        print(f'Overall: {overall}')
        for c in checks:
            print(f'  [{c[1]:>4}] {c[0]}: {c[2]}')
        if failures:
            print('\nHALT: one or more pre-flight checks failed. Fix before proceeding.')

    sys.exit(0 if overall == 'PASS' else 1)


if __name__ == '__main__':
    main()
