import { createHash } from 'node:crypto';
import { mkdirSync, writeFileSync } from 'node:fs';
import { join } from 'node:path';
import type { ExtensionFactory } from '@earendil-works/pi-coding-agent';
import type { AggressiveFilterObservation } from './aggressive-filter.js';
/** Preserve non-status lines and status lines containing diagnostic markers. */
export function stripRoutinePassed(text: string): string {
  return text.split(/(?<=\n)/).filter(line => !/^PASSED\b/.test(line) || /\b(?:fail(?:ed|ure)?|error|warning|expected|actual|assert(?:ion)?)\b/i.test(line)).join('');
}
export function heuristicFilter(directory: string, observe: (e: AggressiveFilterObservation)=>void): ExtensionFactory {
  return pi => { pi.on('tool_result', async event => {
    if(event.isError || event.toolName!=='read' || event.content.some(c=>c.type!=='text')) return;
    const original=event.content.map(c=>c.type==='text'?c.text:'').join('\n');
    const kept=stripRoutinePassed(original);
    if(kept===original) return;
    mkdirSync(directory,{recursive:true});
    const archive=join(directory,createHash('sha256').update(original).digest('hex')+'.txt');
    writeFileSync(archive,original);
    const filtered=`[Full tool result archived at ${archive}; routine passing status lines omitted.]\n${kept}`;
    if(filtered.length>=original.length) return;
    observe({toolName:event.toolName,toolCallId:event.toolCallId,originalCharacters:original.length,retainedCharacters:filtered.length,changed:true,archive,decisions:[]});
    return {content:[{type:'text',text:filtered}]};
  }); };
}
