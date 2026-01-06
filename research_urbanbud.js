const playwright = require('playwright');

(async () => {
  const browser = await playwright.chromium.launch({ headless: true });
  const page = await browser.newPage();
  
  console.log('Visiting herbanbud.com...');
  await page.goto('https://herbanbud.com', { waitUntil: 'domcontentloaded', timeout: 60000 });
  await page.waitForTimeout(3000); // Wait for dynamic content
  
  console.log('\n=== PAGE TITLE ===');
  console.log(await page.title());
  
  console.log('\n=== MEGA MENU STRUCTURE ===');
  // Look for navigation/menu elements
  const menuItems = await page.$$eval('nav a, header a', links => 
    links.map(link => ({
      text: link.textContent.trim(),
      href: link.href
    })).filter(item => item.text)
  );
  console.log(JSON.stringify(menuItems.slice(0, 20), null, 2));
  
  console.log('\n=== MAIN LAYOUT SECTIONS ===');
  const sections = await page.$$eval('section, div[class*="section"]', sections => 
    sections.map(s => s.className).slice(0, 15)
  );
  console.log(JSON.stringify(sections, null, 2));
  
  console.log('\n=== PRODUCT STRUCTURE ===');
  const productElements = await page.$$eval('[class*="product"], [data-product]', products => 
    products.slice(0, 5).map(p => ({
      className: p.className,
      attributes: Array.from(p.attributes).map(attr => ({ name: attr.name, value: attr.value }))
    }))
  );
  console.log(JSON.stringify(productElements, null, 2));
  
  // Take screenshot
  await page.screenshot({ path: 'urbanbud_screenshot.png', fullPage: true });
  console.log('\n✓ Screenshot saved to urbanbud_screenshot.png');
  
  await browser.close();
})();

