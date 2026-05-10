const { chromium } = require('playwright');
(async () => {
  const browser = await chromium.launch({
    executablePath: 'C:/Users/59705/AppData/Local/ms-playwright/chromium-1217/chrome-win64/chrome.exe',
    args: ['--no-sandbox', '--disable-setuid-sandbox', '--disable-dev-shm-usage']
  });
  const page = await browser.newPage();
  await page.setViewportSize({ width: 1280, height: 800 });
  const errors = [];
  page.on('console', msg => { if (msg.type() === 'error') errors.push(msg.text()); });
  page.on('pageerror', err => errors.push('PAGE ERROR: ' + err.message));
  await page.goto('http://127.0.0.1:8081/pc-admin/login.html', { waitUntil: 'domcontentloaded', timeout: 15000 });
  await new Promise(r => setTimeout(r, 2000));
  // Try to get past login
  await page.evaluate(() => {
    try { localStorage.setItem('nw_admin_demo_session', '1'); } catch(e) {}
  });
  await page.goto('http://127.0.0.1:8081/pc-admin/index.html', { waitUntil: 'domcontentloaded', timeout: 15000 });
  await new Promise(r => setTimeout(r, 3000));
  await page.screenshot({ path: 'C:/Users/59705/AppData/Local/Temp/pc_ui_check.png', fullPage: false });
  console.log('Screenshot saved');
  if (errors.length) console.log('Errors:', errors.slice(0, 5).join('\n'));
  await browser.close();
})().catch(e => { console.error('FAIL:', e.message); process.exit(1); });
