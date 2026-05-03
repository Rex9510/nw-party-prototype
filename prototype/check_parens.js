const fs = require('fs');
const html = fs.readFileSync('mobile_v2.html', 'utf-8');
const scriptMatch = html.match(/<script type="text\/babel">([\s\S]*?)<\/script>/);
if (!scriptMatch) { console.log('No script found'); process.exit(1); }
const js = scriptMatch[1];

let balance = 0;
let inStr = null;
let escape = false;
let lineNum = 1;
let maxBalance = 0;
let firstStuckLine = 0;

for (let i = 0; i < js.length; i++) {
  const ch = js[i];
  if (escape) { escape = false; continue; }
  if (inStr) {
    if (ch === '\\') { escape = true; continue; }
    if (ch === inStr) { inStr = null; }
    continue;
  }
  if (ch === '"' || ch === "'" || ch === '`') { inStr = ch; continue; }
  if (ch === '(') {
    balance++;
    if (maxBalance === 0) { firstStuckLine = lineNum; }
    maxBalance = Math.max(maxBalance, balance);
    continue;
  }
  if (ch === ')') {
    balance--;
    if (balance === 0) { maxBalance = 0; }
    continue;
  }
  if (ch === '\n') lineNum++;
}

console.log('Final balance:', balance);
console.log('Max balance seen:', maxBalance);
console.log('First line where balance went non-zero:', firstStuckLine);
