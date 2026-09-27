import type { CodingTask } from './tasks.js';
export const tasks: CodingTask[] = [
  {
    id: 'intervals', functionName: 'merge_windows', objective: 'Repair merge_windows: validate integer half-open windows and merge overlapping but not touching intervals.',
    initial: 'Repair merge_windows(windows) in solver.py. Further contracts and diagnostics follow.',
    requirements: 'Input is a list of two-item lists containing integers (booleans are invalid). Reject malformed pairs, non-integers and start > end with ValueError. Ignore zero-length intervals. Return sorted two-item lists representing the union, merging strictly overlapping intervals but preserving touching intervals separately. Do not mutate the input. Negative endpoints are allowed. Empty input returns [].',
    source: 'def merge_windows(windows):\n    return sorted(windows)\n',
    cases: [
      {name:'empty',args:[[]],expected:[]}, {name:'overlap',args:[[[1,5],[3,8]]],expected:[[1,8]]},
      {name:'touch',args:[[[1,3],[3,5]]],expected:[[1,3],[3,5]]}, {name:'bridge',args:[[[5,9],[1,6],[2,3]]],expected:[[1,9]]},
      {name:'empty-window',args:[[[2,2],[-3,0]]],expected:[[-3,0]]}, {name:'duplicates',args:[[[1,4],[1,4]]],expected:[[1,4]]},
      {name:'nested',args:[[[0,10],[2,4],[10,11]]],expected:[[0,10],[10,11]]},
      ...[[[5,1]],[[true,2]],[[1.5,3]],[[1]],[[1,2,3]],[['1',3]],[null]].map((x,i)=>({name:`invalid-${i}`,args:[x],raises:'ValueError'})),
    ],
  },
  {
    id:'dependencies',functionName:'build_order',objective:'Repair deterministic dependency ordering with lexicographic ready-node selection and cycle rejection.',
    initial:'Repair build_order(graph) in solver.py. Contracts and diagnostics follow.',
    requirements:'graph maps string node names to lists of string prerequisite names. Include prerequisites absent as keys. Return a topological ordering: at each step select the lexicographically smallest currently ready node. Deduplicate repeated edges. Reject self cycles and any longer cycle with ValueError. Do not mutate graph or its lists. Empty graph returns []. Assume valid input types.',
    source:'def build_order(graph):\n    return sorted(graph)\n',
    cases:[
      {name:'empty',args:[{}],expected:[]}, {name:'missing-node',args:[{a:['z']}],expected:['z','a']},
      {name:'dynamic-ready',args:[{b:[],a:['b'],c:[]}],expected:['b','a','c']},
      {name:'duplicate',args:[{b:['a','a']}],expected:['a','b']},
      {name:'diamond',args:[{d:['b','c'],c:['a'],b:['a']}],expected:['a','b','c','d']},
      {name:'disconnected',args:[{z:[],b:['a'],x:['w']}],expected:['a','b','w','x','z']},
      {name:'self',args:[{a:['a']}],raises:'ValueError'}, {name:'cycle',args:[{a:['b'],b:['c'],c:['a']}],raises:'ValueError'},
      {name:'partial-cycle',args:[{x:[],a:['b'],b:['a']}],raises:'ValueError'},
      {name:'case-order',args:[{b:[],A:[],a:[]}],expected:['A','a','b']},
    ],
  },
  {
    id:'records',functionName:'decode_records',objective:'Repair escaped key-value record decoding, preserving escaped separators and rejecting malformed escape sequences.',
    initial:'Repair decode_records(text) in solver.py. Contracts and diagnostics follow.',
    requirements:'Decode records separated by unescaped semicolons; first unescaped equals sign separates key from value. Backslash escapes ONLY backslash, semicolon or equals; reject other escapes and a trailing backslash with ValueError. Ignore empty records including trailing separators. Keys must be nonempty after decoding; values may be empty. Preserve all whitespace. Later unescaped equals signs are part of the value. Return a list of [key,value] lists preserving duplicates and order. Nonempty records without an unescaped equals raise ValueError. Empty input returns [].',
    source:'def decode_records(text):\n    return [part.split("=") for part in text.split(";") if part]\n',
    cases:[
      {name:'empty',args:[''],expected:[]}, {name:'simple',args:['a=1;b=2'],expected:[['a','1'],['b','2']]},
      {name:'escaped-separator',args:['a=x\\;y;b=z'],expected:[['a','x;y'],['b','z']]},
      {name:'escaped-key',args:['a\\=b=c'],expected:[['a=b','c']]},
      {name:'backslash',args:['a=\\\\'],expected:[['a','\\']]},
      {name:'extra-equals',args:['a=b=c'],expected:[['a','b=c']]}, {name:'empty-records',args:[';;a=;;'],expected:[['a','']]},
      {name:'duplicate-space',args:[' a = x ; a =y'],expected:[[' a ',' x '],[' a ','y']]},
      ...['a','a\\=b','=x','a=\\q','a=x\\'].map((x,i)=>({name:`invalid-${i}`,args:[x],raises:'ValueError'})),
    ],
  },
];
export function diagnostic(task: CodingTask): string {
  if(task.id==='intervals') return Array.from({length:125},(_,i)=>`PASSED health probe ${i}: scheduler heartbeat stable; no interval data in this probe.`).join('\n')+'\nFAILED merge overlap: expected [[1,8]], actual [[1,5],[3,8]].\n';
  if(task.id==='dependencies') return Array.from({length:125},(_,i)=>JSON.stringify({level:'info',event:'cache_probe',sequence:i,healthy:true})).join('\n')+'\n'+JSON.stringify({level:'error',case:'missing prerequisite',expected:['z','a'],actual:['a']})+'\n';
  return Array.from({length:100},(_,i)=>`PASSED unrelated codec smoke ${i}: fixture accepted.`).join('\n')+'\nWARNING decoder contract example below is actionable; preserve the following block.\ninput: a=x\\;y;b=z\nexpected: [["a","x;y"],["b","z"]]\nactual: [["a","x\\"],["y"],["b","z"]]\n';
}
