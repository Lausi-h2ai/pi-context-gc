import test from 'node:test';
import assert from 'node:assert/strict';
import { stripRoutinePassed } from '../src/heuristic-filter.js';
test('heuristic removes routine status but preserves diagnostic-bearing passes and multiline details',()=>{
 const text='PASSED ordinary check\nFAILED target\n  input: x\nexpected: y\nPASSED with WARNING about drift\nPASSED expected details\n{"level":"error"}\n';
 assert.equal(stripRoutinePassed(text),'FAILED target\n  input: x\nexpected: y\nPASSED with WARNING about drift\nPASSED expected details\n{"level":"error"}\n');
});
test('heuristic preserves non-status logs exactly',()=>{
 const text='{"event":"probe","healthy":true}\ntrace\nlast line';
 assert.equal(stripRoutinePassed(text),text);
});
