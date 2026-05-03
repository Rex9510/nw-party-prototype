const fs = require('fs');
const html = fs.readFileSync('pc-admin/index.html', 'utf-8');
const scriptMatch = html.match(/<script type="text\/babel">([\s\S]*?)<\/script>/);
const js = scriptMatch[1];

// Check function declarations
const funcs = [...js.matchAll(/function\s+(\w+)Page/g)];
const counts = {};
funcs.forEach(m => { counts[m[1]] = (counts[m[1]] || 0) + 1; });
console.log('Function declaration counts:', JSON.stringify(counts));

// Check bracket balance (simplified - skip strings)
let bal = 0, bal2 = 0, bal3 = 0;
for (let i = 0; i < js.length; i++) {
  const ch = js[i];
  if (ch === '{') bal++;
  if (ch === '}') bal--;
  if (ch === '[') bal2++;
  if (ch === ']') bal2--;
  if (ch === '(') bal3++;
  if (ch === ')') bal3--;
}
console.log('Brace balance: {}=', bal, '[]=', bal2, '()=', bal3);
