// Renders index.html to MP4 frame by frame.
// Usage: node render.js [out.mp4] [--fps 30] [--stills 1,20,60] [--page index.html] [--audio narration.mp3]
// Needs: Playwright (Chromium) and ffmpeg on PATH. GSAP is served from node_modules when present.
const fs = require('fs');
const path = require('path');
const os = require('os');
const { spawn } = require('child_process');
const { chromium } = require('playwright');

const args = process.argv.slice(2);
const opt = (name, def) => { const i = args.indexOf(name); return i >= 0 ? args[i + 1] : def; };
const out = args[0] && !args[0].startsWith('--') ? args[0] : path.join(__dirname, 'road-to-the-crown.mp4');
const fps = +opt('--fps', 30);
const stills = opt('--stills', '');
const gsapLocal = opt('--gsap', '');
const pageFile = opt('--page', 'index.html');
const audio = opt('--audio', '');

(async () => {
  const src = fs.readFileSync(path.join(__dirname, pageFile), 'utf8');
  const tmp = fs.mkdtempSync(path.join(os.tmpdir(), 'crown-'));
  const page_ = path.join(tmp, 'page.html');
  fs.writeFileSync(page_, '<!doctype html><html><head><meta charset="utf-8"></head><body>' + src + '</body></html>');

  const browser = await chromium.launch();
  const page = await browser.newPage({ viewport: { width: 1920, height: 1920 }, deviceScaleFactor: 1 });
  if (gsapLocal) await page.route(/cdnjs\.cloudflare\.com\/.*gsap\.min\.js/, r => r.fulfill({ path: gsapLocal, contentType: 'text/javascript' }));
  await page.goto('file://' + page_ + '?render');
  await page.waitForFunction(() => window.__duration > 0);
  await page.evaluate(() => document.fonts.ready);
  const duration = await page.evaluate(() => window.__duration);
  const stage = await page.$('#stage');

  if (stills) {
    for (const s of stills.split(',').map(Number)) {
      await page.evaluate(t => window.__seek(t), s);
      await stage.screenshot({ path: path.join(path.dirname(out), 'still-' + s + '.png') });
    }
    await browser.close();
    return;
  }

  const audioArgs = audio ? ['-i', path.resolve(__dirname, audio), '-c:a', 'aac', '-b:a', '192k'] : [];
  const ff = spawn('ffmpeg', ['-y', '-f', 'image2pipe', '-framerate', String(fps), '-c:v', 'png', '-i', '-', ...audioArgs,
    '-c:v', 'libx264', '-preset', 'medium', '-crf', '18', '-pix_fmt', 'yuv420p', '-movflags', '+faststart', out],
    { stdio: ['pipe', 'ignore', 'inherit'] });
  const frames = Math.ceil(duration * fps);
  for (let f = 0; f < frames; f++) {
    await page.evaluate(t => window.__seek(t), f / fps);
    const buf = await stage.screenshot({ type: 'png' });
    if (!ff.stdin.write(buf)) await new Promise(r => ff.stdin.once('drain', r));
    if (f % 150 === 0) console.log('frame ' + f + '/' + frames);
  }
  ff.stdin.end();
  await new Promise(r => ff.on('close', r));
  await browser.close();
  console.log('wrote ' + out + ' (' + duration.toFixed(1) + 's)');
})();
