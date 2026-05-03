const fs = require('fs');
const html = fs.readFileSync('mobile_v2.html', 'utf-8');
const scriptMatch = html.match(/<script type="text\/babel">([\s\S]*?)<\/script>/);
const js = scriptMatch[1];

// Check curly braces
let bal = 0;
let inStr = null;
let esc = false;
for (let i = 0; i < js.length; i++) {
  const ch = js[i];
  if (esc) { esc = false; continue; }
  if (inStr) {
    if (ch === '\\') { esc = true; continue; }
    if (ch === inStr) inStr = null;
    continue;
  }
  if (ch === '"' || ch === "'" || ch === '`') { inStr = ch; continue; }
  if (ch === '{') bal++;
  if (ch === '}') bal--;
}
console.log('Curly brace balance:', bal);

// Check brackets
let bal2 = 0;
inStr = null;
esc = false;
for (let i = 0; i < js.length; i++) {
  const ch = js[i];
  if (esc) { esc = false; continue; }
  if (inStr) {
    if (ch === '\\') { esc = true; continue; }
    if (ch === inStr) inStr = null;
    continue;
  }
  if (ch === '"' || ch === "'" || ch === '`') { inStr = ch; continue; }
  if (ch === '[') bal2++;
  if (ch === ']') bal2--;
}
console.log('Bracket balance:', bal2);
