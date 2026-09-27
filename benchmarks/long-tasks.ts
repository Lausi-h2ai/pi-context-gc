import { tasks, type CodingTask } from './tasks.js';

const sections = tasks.map(task => `## ${task.functionName}\n${task.initial}\n\nContract: ${task.requirements}`);

/** One maintenance task that requires all three functions, not three isolated fixes. */
export const longTask: CodingTask = {
  id: 'suite',
  objective: 'Repair the invoice parser, HTTP retry scheduler, and archive path normalizer to their documented contracts.',
  initial: 'Repair all three functions in solver.py: parse_invoices, retry_delays, and normalize_members. You will receive their contracts, diagnostics, and implementation steps before editing. Do not inspect or edit files until asked.',
  requirements: sections.join('\n\n') + '\n',
  source: tasks.map(task => task.source).join('\n'),
  functionName: tasks[0].functionName,
  cases: tasks.flatMap(task => task.cases.map(test => ({ ...test, name: `${task.id}/${test.name}`, functionName: task.functionName }))),
};

const views = [
  'Interface review: check argument handling, return values and exact output representations.',
  'Validation review: reject malformed values explicitly at the stated boundary.',
  'Ordering review: preserve input order wherever the contract requires it.',
  'Formatting review: do not normalize text beyond the contract’s specified transformations.',
  'Boundary review: empty inputs, final elements and exhausted budgets need intentional behavior.',
  'Implementation review: use Python standard library facilities and avoid observable side effects.',
];

/** Long but task-relevant stable reference, intentionally read before noisy logs. */
export function longGuide(): string {
  const contract = sections.join('\n\n');
  return `# Maintenance reference for the three-function solver\n\n${contract}\n\n`
    + views.map((view, i) => `# Review section ${i + 1}\n${view}\n\n${contract}\n`).join('\n');
}

export const logFailures = [
  'FAILED invoice precision: expected amount 123.00 but got 123.0',
  'FAILED retry method safety: expected zero retries after HTTP 401, got one retry',
  'FAILED archive traversal: expected ValueError for ../secret, got secret',
];

export function longDiagnostic(index: number): string {
  const passed = Array.from({ length: 130 }, (_, i) =>
    `PASSED unrelated regression group ${index}-${i}: fixture processed successfully; no new actionable findings.`).join('\n');
  return `${passed}\n${logFailures[index]}.\n`;
}
