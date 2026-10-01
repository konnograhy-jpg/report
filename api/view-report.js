// api/view-report.js
// 潘朵拉動態串流日報端點 (架構解耦：資料更新零 Deployment)

export default async function handler(req, res) {
  try {
    let filePath = req.query.path || 'tenders.html';

    // 移除前導斜線
    filePath = filePath.replace(/^\/+/, '');
    if (!filePath || filePath === 'index.html') {
      filePath = 'tenders.html';
    }

    // 安全檢查：嚴防路徑遍歷攻擊
    if (filePath.includes('..') || filePath.includes('\\')) {
      return res.status(400).send('Invalid path parameter');
    }

    // 串流目標：GitHub Raw main 分支最新日報
    const rawUrl = `https://raw.githubusercontent.com/konnograhy-jpg/report/main/boss/${filePath}`;

    const controller = new AbortController();
    const timeoutId = setTimeout(() => controller.abort(), 10000); // 10 秒逾時防護

    const response = await fetch(rawUrl, {
      signal: controller.signal,
      headers: {
        'User-Agent': 'Pandora-Dynamic-Viewer'
      }
    });
    clearTimeout(timeoutId);

    if (!response.ok) {
      if (response.status === 404) {
        res.setHeader('Content-Type', 'text/html; charset=utf-8');
        res.setHeader('X-Robots-Tag', 'noindex, nofollow, noarchive, nosnippet');
        return res.status(404).send(`
          <!DOCTYPE html>
          <html lang="zh-Hant">
          <head>
            <meta charset="utf-8">
            <title>找不到報告 - 404</title>
            <meta name="robots" content="noindex, nofollow, noarchive, nosnippet">
            <style>
              body { font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; background: #0a0f1e; color: #f1f5f9; text-align: center; padding: 80px 20px; }
              .card { max-width: 500px; margin: 0 auto; background: #111827; padding: 40px; border-radius: 16px; border: 1px solid rgba(255,255,255,0.1); }
              h1 { color: #f59e0b; margin-bottom: 16px; }
              p { color: #94a3b8; font-size: 14px; line-height: 1.6; margin-bottom: 24px; }
              a { display: inline-block; background: #3b82f6; color: #fff; text-decoration: none; padding: 10px 24px; border-radius: 8px; font-weight: 600; }
            </style>
          </head>
          <body>
            <div class="card">
              <h1>⚠️ 找不到指定報告</h1>
              <p>路徑 <code>boss/${filePath}</code> 不存在或尚未同步至 GitHub。<br>若剛完成爬蟲，請稍候數秒重新整理。</p>
              <a href="/boss/tenders.html">返回標案整理專區</a>
            </div>
          </body>
          </html>
        `);
      }
      return res.status(response.status).send(`Failed to fetch report from upstream (Status: ${response.status})`);
    }

    // 依據檔案副檔名給予正確 Content-Type
    let contentType = 'text/html; charset=utf-8';
    if (filePath.endsWith('.json')) contentType = 'application/json; charset=utf-8';
    else if (filePath.endsWith('.css')) contentType = 'text/css; charset=utf-8';
    else if (filePath.endsWith('.js')) contentType = 'application/javascript; charset=utf-8';
    else if (filePath.endsWith('.png')) contentType = 'image/png';
    else if (filePath.endsWith('.jpg') || filePath.endsWith('.jpeg')) contentType = 'image/jpeg';
    else if (filePath.endsWith('.svg')) contentType = 'image/svg+xml';

    res.setHeader('Content-Type', contentType);
    res.setHeader('X-Robots-Tag', 'noindex, nofollow, noarchive, nosnippet');

    // 快取控制：首頁短快取（即時感知新日報），歷史日報長快取（提升載入速度）
    if (filePath === 'tenders.html') {
      res.setHeader('Cache-Control', 'public, max-age=60, s-maxage=120, stale-while-revalidate=300');
    } else {
      res.setHeader('Cache-Control', 'public, max-age=3600, s-maxage=86400, stale-while-revalidate=86400');
    }

    // 二進位與文字格式串流
    if (contentType.startsWith('image/')) {
      const buffer = await response.arrayBuffer();
      return res.status(200).send(Buffer.from(buffer));
    } else {
      const content = await response.text();
      return res.status(200).send(content);
    }
  } catch (err) {
    console.error('view-report error:', err);
    res.setHeader('Content-Type', 'text/html; charset=utf-8');
    return res.status(500).send(`<h3>動態串流伺服器暫時無法連線: ${err.message}</h3>`);
  }
}
