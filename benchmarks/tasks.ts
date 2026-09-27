export interface Case { name: string; args: unknown[]; expected?: unknown; raises?: string; functionName?: string }
export interface CodingTask {
  id: string; objective: string; initial: string; requirements: string; source: string;
  functionName: string; cases: Case[];
}
export const tasks: CodingTask[] = [
  {
    id: 'invoice', objective: 'Fix the invoice CSV parser. Preserve exact decimal text and obey the input validation requirements.',
    initial: 'Implement parse_invoices(text) in solver.py. Input is CSV with a required id;amount header. Return dictionaries with id and amount strings. Preserve decimal precision and handle quoted CSV fields. Further requirements will be supplied before implementation.',
    requirements: 'Use semicolon-separated CSV with the exact header id;amount. Trim spaces around both fields. Normalize a comma decimal separator to a dot but otherwise preserve the amount text, including signs, leading zeros and trailing zeros. Accept only an optional + or - followed by digits, optionally followed by one dot or comma and more digits. Reject NaN, infinities, exponents, currency symbols, empty fields and records with anything other than two fields with ValueError. Skip physically blank lines. Quoted identifiers may contain semicolons. Empty input and a wrong header raise ValueError. Header-only input returns an empty list.',
    source: 'def parse_invoices(text):\n    lines = text.splitlines()[1:]\n    return [{"id": x.split(";")[0], "amount": str(float(x.split(";")[1]))} for x in lines]\n',
    functionName: 'parse_invoices',
    cases: [
      { name: 'precision', args: ['id;amount\nA;123.00\n'], expected: [{ id: 'A', amount: '123.00' }] },
      { name: 'comma-negative', args: ['id;amount\nB;-0002,500\n'], expected: [{ id: 'B', amount: '-0002.500' }] },
      { name: 'plus', args: ['id;amount\nC;+04.00'], expected: [{ id: 'C', amount: '+04.00' }] },
      { name: 'quoted-id', args: ['id;amount\n"A;B";9,20'], expected: [{ id: 'A;B', amount: '9.20' }] },
      { name: 'spaces-blank', args: ['id;amount\n\n A ; 0.000 \n\n'], expected: [{ id: 'A', amount: '0.000' }] },
      { name: 'header-only', args: ['id;amount\n'], expected: [] },
      ...['', 'x;y\nA;1', 'id;amount\nA;NaN', 'id;amount\nA;1e2', 'id;amount\nA;', 'id;amount\n;2', 'id;amount\nA;1;extra', 'id;amount\nA;Infinity', 'id;amount\nA;$2', 'id;amount\nA;1.2.3'].map((s, i) => ({ name: `invalid-${i}`, args: [s], raises: 'ValueError' })),
    ],
  },
  {
    id: 'retry', objective: 'Implement bounded HTTP retry scheduling with method safety and Retry-After support.',
    initial: 'Implement retry_delays(statuses, method="GET", idempotency_key=None, retry_after=None) in solver.py. Return integer delays in milliseconds before retries, processing statuses in order. Do not perform requests or sleep. Further requirements will follow.',
    requirements: 'Only status 429 and 503 are retryable. Stop at any other status. At most three total attempts, therefore at most two delays. GET, HEAD, PUT, DELETE and OPTIONS can retry; POST can retry only with a nonempty idempotency key. Method matching is case-insensitive. Other methods never retry. Before first retry wait 100ms, before second 200ms. retry_after is an optional list aligned with statuses; missing entries are ignored. A finite nonnegative numeric seconds value overrides only when larger than the default delay; round it up to milliseconds, then cap at 1000ms. Ignore invalid, negative and infinite values; numeric strings count as invalid. Return [] on an empty status list. A final retryable status still schedules the next attempt if the attempt budget permits it.',
    source: 'def retry_delays(statuses, method="GET", idempotency_key=None, retry_after=None):\n    return [100 for status in statuses if status >= 400]\n',
    functionName: 'retry_delays',
    cases: [
      { name: 'empty', args: [[]], expected: [] },
      { name: 'success-stop', args: [[200, 503]], expected: [] },
      { name: 'ordinary', args: [[503, 429, 200]], expected: [100, 200] },
      { name: 'budget', args: [[503, 503, 503, 503]], expected: [100, 200] },
      { name: '401-stop', args: [[503, 401, 503]], expected: [100] },
      { name: '500-no', args: [[500]], expected: [] },
      { name: 'post-no', args: [[503], 'POST'], expected: [] },
      { name: 'post-key', args: [[503, 429], 'post', 'key'], expected: [100, 200] },
      { name: 'empty-key', args: [[503], 'POST', ''], expected: [] },
      { name: 'patch-no', args: [[503], 'PATCH', 'key'], expected: [] },
      { name: 'head', args: [[429], 'head'], expected: [100] },
      { name: 'retry-after', args: [[503, 429], 'GET', null, [0.2001, 5]], expected: [201, 1000] },
      { name: 'small-after', args: [[503, 503], 'GET', null, [0.01, 0]], expected: [100, 200] },
      { name: 'invalid-after', args: [[503, 429], 'PUT', null, [-1, '2']], expected: [100, 200] },
      { name: 'short-after', args: [[503, 429], 'DELETE', null, [0.5]], expected: [500, 200] },
      { name: 'none-after', args: [[503], 'OPTIONS', null, [null]], expected: [100] },
    ],
  },
  {
    id: 'paths', objective: 'Normalize archive member paths and reject paths that can escape the archive root.',
    initial: 'Implement normalize_members(paths) in solver.py. Return normalized relative path strings for archive members, maintaining order. Both slash styles can appear in the input. Further edge-case requirements will follow.',
    requirements: 'Treat backslashes as separators. Remove empty segments and dot segments, resolve internal .. segments, but raise ValueError if a .. would escape root. Reject paths starting with either slash style, UNC paths, any ASCII drive prefix such as C: even if drive-relative, NUL characters and paths that normalize to empty. Preserve Unicode and spaces in component names. Strip trailing separators through normalization. Deduplicate normalized paths while keeping first occurrence order. Reject the entire call on any invalid member. Empty input returns [].',
    source: 'def normalize_members(paths):\n    return [p.replace("\\\\", "/").lstrip("/") for p in paths]\n',
    functionName: 'normalize_members',
    cases: [
      { name: 'empty-list', args: [[]], expected: [] },
      { name: 'dots', args: [['a//./b/']], expected: ['a/b'] },
      { name: 'internal-parent', args: [['a/b/../c']], expected: ['a/c'] },
      { name: 'backslash', args: [['a\\b\\c']], expected: ['a/b/c'] },
      { name: 'dedup', args: [['a/b', 'a//b', 'c', 'a/./b']], expected: ['a/b', 'c'] },
      { name: 'unicode-spaces', args: [['資料/é x.txt']], expected: ['資料/é x.txt'] },
      ...['../x', 'a/../../x', '/etc/x', '\\etc\\x', '\\\\server\\x', 'C:relative', 'd:/absolute', 'x\u0000y', '.', 'a/..'].map((s, i) => ({ name: `reject-${i}`, args: [[s]], raises: 'ValueError' })),
    ],
  },
];
