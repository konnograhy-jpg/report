/**
 * Vercel Serverless Function: /api/submit-bid
 * 說明：C 專案轉發登記投標意向至毅築標案管理系統 API 中繼點，
 *       並在登記成功 (201) 後，即時提取採購網明細、發送 Telegram 通知並建立 Google 日曆行程。
 */

import crypto from 'node:crypto';

const PCC_HOST_ALLOWLIST = new Set(['web.pcc.gov.tw']);
const REQUEST_TIMEOUT_MS = 5000;

/** 將預算字串或數字正規化為整數金額 */
function parseBudgetAmount(val) {
  if (val === undefined || val === null || val === '') return null;
  if (typeof val === 'number') return Number.isNaN(val) ? null : Math.round(val);
  const cleaned = String(val).replace(/[^0-9.]/g, '');
  const num = parseFloat(cleaned);
  return Number.isNaN(num) ? null : Math.round(num);
}

/** 驗證並過濾採購網明細連結，避免 SSRF */
function sanitizePccUrl(rawUrl) {
  if (typeof rawUrl !== 'string' || !rawUrl.trim()) return '';
  try {
    const parsed = new URL(rawUrl.trim());
    if ((parsed.protocol === 'https:' || parsed.protocol === 'http:') && PCC_HOST_ALLOWLIST.has(parsed.hostname)) {
      return parsed.toString();
    }
  } catch {
    return '';
  }
  return '';
}

/** 清除 HTML 標籤並壓縮空白 */
function stripHtml(html) {
  return html
    .replace(/<script[\s\S]*?<\/script>/gi, ' ')
    .replace(/<style[\s\S]*?<\/style>/gi, ' ')
    .replace(/<!--[\s\S]*?-->/g, ' ')
    .replace(/<[^>]+>/g, ' ')
    .replace(/&nbsp;/gi, ' ')
    .replace(/\s+/g, ' ')
    .trim();
}

/** 將民國日期時間 (如 115/11/18 12:00) 轉為西元與 ISO 格式 */
function parseRocDateTime(rocStr) {
  if (!rocStr) return null;
  const match = String(rocStr).match(/(\d{2,3})\/(\d{1,2})\/(\d{1,2})(?:\s+(\d{1,2}):(\d{2}))?/);
  if (!match) return null;

  const year = parseInt(match[1], 10) + 1911;
  const month = String(parseInt(match[2], 10)).padStart(2, '0');
  const day = String(parseInt(match[3], 10)).padStart(2, '0');
  const hour = match[4] ? String(parseInt(match[4], 10)).padStart(2, '0') : '09';
  const minute = match[5] ? String(parseInt(match[5], 10)).padStart(2, '0') : '00';
  const hasTime = Boolean(match[4]);

  return {
    roc: rocStr.trim(),
    shortLabel: `${month}/${day}${hasTime ? ` ${hour}:${minute}` : ''}`,
    display: `${year}/${month}/${day}${hasTime ? ` ${hour}:${minute}` : ''} (${rocStr.trim()})`,
    isoStart: `${year}-${month}-${day}T${hour}:${minute}:00+08:00`
  };
}

/** 計算指定分鐘數後的台北時區 ISO 字串 */
function addMinutesTaipei(isoStart, minutes) {
  const startMs = Date.parse(isoStart);
  const endDate = new Date(startMs + minutes * 60 * 1000);
  const fmt = new Intl.DateTimeFormat('sv-SE', {
    timeZone: 'Asia/Taipei',
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit',
    second: '2-digit'
  });
  return fmt.format(endDate).replace(' ', 'T') + '+08:00';
}

/** 從政府電子採購網招標公告明細頁提取地址、截標與開標時間 */
async function fetchPccTenderDetails(tenderUrl) {
  const safeUrl = sanitizePccUrl(tenderUrl);
  if (!safeUrl) return { ok: false, reason: 'no_valid_url' };

  try {
    const res = await fetch(safeUrl, {
      headers: {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
      },
      signal: AbortSignal.timeout(REQUEST_TIMEOUT_MS)
    });
    if (!res.ok) return { ok: false, reason: `http_${res.status}` };

    const html = await res.text();
    const cleanText = stripHtml(html);

    const addrMatch = cleanText.match(/機關地址\s+(.+?)(?:\s+聯絡人|\s+聯絡電話|$)/);
    const agencyAddress = addrMatch ? addrMatch[1].trim() : '';

    const deadlineMatch = cleanText.match(/截止投標\s+(\d{2,3}\/\d{1,2}\/\d{1,2}(?:\s+\d{1,2}:\d{2})?)/);
    const deadline = deadlineMatch ? parseRocDateTime(deadlineMatch[1]) : null;

    const openingMatch = cleanText.match(/開標時間\s+(\d{2,3}\/\d{1,2}\/\d{1,2}(?:\s+\d{1,2}:\d{2})?)/);
    const opening = openingMatch ? parseRocDateTime(openingMatch[1]) : null;

    const openLocMatch = cleanText.match(/開標地點\s+(.+?)(?:\s+是否須繳納押標金|\s+投標文字|$)/);
    const openingLocation = openLocMatch ? openLocMatch[1].trim() : '';

    const awardMatch = cleanText.match(/決標方式\s+(.+?)(?:\s+是否電子報價|\s+新增公告傳輸次數|\s+是否複數決標|$)/);
    const awardMethod = awardMatch ? awardMatch[1].trim() : '';

    const evalMatch = cleanText.match(/(?:評選時間|評選日期|評審時間|評審日期)\s+(\d{2,3}\/\d{1,2}\/\d{1,2}(?:\s+\d{1,2}:\d{2})?)/);
    const evaluation = evalMatch ? parseRocDateTime(evalMatch[1]) : null;

    return { ok: true, agencyAddress, deadline, opening, evaluation, awardMethod, openingLocation, url: safeUrl };
  } catch (err) {
    return { ok: false, reason: err.message || 'fetch_failed' };
  }
}

/** 跳脫 Telegram HTML 特殊字元 */
function escapeHtml(text) {
  return String(text || '')
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;');
}

/** 發送 Telegram 投標登記通知 */
async function sendTelegramBidNotice(bid, details) {
  const token = process.env.TELEGRAM_BOT_TOKEN;
  const chatId = process.env.TELEGRAM_CHAT_ID;
  if (!token || !chatId) return { ok: false, skipped: true, reason: 'missing_telegram_env' };

  const nowTaipei = new Intl.DateTimeFormat('zh-TW', {
    timeZone: 'Asia/Taipei',
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit',
    second: '2-digit',
    hour12: false
  }).format(new Date());

  const budgetText = bid.budget_amount !== null ? `NT$ ${bid.budget_amount.toLocaleString('en-US')}` : '未列出';
  const lines = [
    '🎯 <b>【C專案】標案投標意向登記通知</b>',
    '',
    `👤 <b>登記設計師：</b>${escapeHtml(bid.designer_name)}`,
    `🕒 <b>登記時間：</b>${escapeHtml(nowTaipei)}`,
    `🏢 <b>招標機關：</b>${escapeHtml(bid.agency_name)}`,
    `📍 <b>機關地址：</b>${escapeHtml(details.agencyAddress || '未取得')}`,
    `📄 <b>標案名稱：</b>${escapeHtml(bid.tender_name)}`,
    `🔖 <b>標案案號：</b><code>${escapeHtml(bid.tender_id)}</code>`,
    `💰 <b>預算金額：</b>${escapeHtml(budgetText)}`,
    `⏰ <b>截標時間：</b>${escapeHtml(details.deadline?.display || '未取得')}`,
    `🔔 <b>開標時間：</b>${escapeHtml(details.opening?.display || '未取得')}`
  ];

  if (details.evaluation) {
    lines.push(`🗓️ <b>評選時間：</b>${escapeHtml(details.evaluation.display)}`);
  }
  if (details.awardMethod) {
    lines.push(`📋 <b>決標方式：</b>${escapeHtml(details.awardMethod)}`);
  }
  if (details.openingLocation) {
    lines.push(`🏛️ <b>開標地點：</b>${escapeHtml(details.openingLocation)}`);
  }
  if (details.url) {
    lines.push(`🔗 <a href="${escapeHtml(details.url)}">查看政府電子採購網公告</a>`);
  }

  const res = await fetch(`https://api.telegram.org/bot${token}/sendMessage`, {
    method: 'POST',
    headers: { 'content-type': 'application/json' },
    body: JSON.stringify({
      chat_id: chatId,
      text: lines.join('\n'),
      parse_mode: 'HTML',
      disable_web_page_preview: true
    }),
    signal: AbortSignal.timeout(REQUEST_TIMEOUT_MS)
  });

  if (!res.ok) {
    const errBody = await res.text().catch(() => '');
    return { ok: false, status: res.status, reason: errBody.slice(0, 200) };
  }
  return { ok: true };
}

/** 取得 Google Service Account OAuth2 Access Token */
async function getGoogleAccessToken() {
  let clientEmail = process.env.GOOGLE_CLIENT_EMAIL || '';
  let privateKey = process.env.GOOGLE_PRIVATE_KEY || '';

  if ((!clientEmail || !privateKey) && process.env.GOOGLE_SERVICE_ACCOUNT_JSON) {
    const parsed = JSON.parse(process.env.GOOGLE_SERVICE_ACCOUNT_JSON);
    clientEmail = parsed.client_email || '';
    privateKey = parsed.private_key || '';
  }

  privateKey = privateKey.replace(/\\n/g, '\n');
  if (!clientEmail || !privateKey) return null;

  const now = Math.floor(Date.now() / 1000);
  const header = Buffer.from(JSON.stringify({ alg: 'RS256', typ: 'JWT' })).toString('base64url');
  const claim = Buffer.from(JSON.stringify({
    iss: clientEmail,
    scope: 'https://www.googleapis.com/auth/calendar.events',
    aud: 'https://oauth2.googleapis.com/token',
    exp: now + 3600,
    iat: now
  })).toString('base64url');

  const sig = crypto.createSign('RSA-SHA256').update(`${header}.${claim}`).sign(privateKey, 'base64url');
  const tokenRes = await fetch('https://oauth2.googleapis.com/token', {
    method: 'POST',
    headers: { 'content-type': 'application/x-www-form-urlencoded' },
    body: new URLSearchParams({
      grant_type: 'urn:ietf:params:oauth:grant-type:jwt-bearer',
      assertion: `${header}.${claim}.${sig}`
    }),
    signal: AbortSignal.timeout(REQUEST_TIMEOUT_MS)
  });

  const tokenData = await tokenRes.json().catch(() => ({}));
  return tokenData.access_token || null;
}

/** 解析環境變數中的設計師日曆對應表 */
function getTargetCalendarIds(designerName) {
  const targets = new Set();
  if (process.env.GOOGLE_CALENDAR_ID) {
    targets.add(process.env.GOOGLE_CALENDAR_ID.trim());
  }
  if (process.env.GOOGLE_DESIGNER_CALENDARS_JSON) {
    try {
      const map = JSON.parse(process.env.GOOGLE_DESIGNER_CALENDARS_JSON);
      const designerCalId = map?.[designerName];
      if (typeof designerCalId === 'string' && designerCalId.trim()) {
        targets.add(designerCalId.trim());
      }
    } catch (err) {
      console.warn('[submit-bid] 無法解析 GOOGLE_DESIGNER_CALENDARS_JSON:', err.message);
    }
  }
  return Array.from(targets);
}

/** 在建築師與對應設計師的 Google 日曆建立截標與開標行程 */
async function createGoogleCalendarEvents(bid, details) {
  const targetCalendarIds = getTargetCalendarIds(bid.designer_name);
  if (targetCalendarIds.length === 0) return { ok: false, skipped: true, reason: 'missing_calendar_id' };
  if (!details.deadline && !details.opening && !details.evaluation) {
    return { ok: false, skipped: true, reason: 'no_dates_extracted' };
  }

  const accessToken = await getGoogleAccessToken();
  if (!accessToken) return { ok: false, skipped: true, reason: 'missing_google_credentials' };

  const cleanTenderName = bid.tender_name.replace(/\s+/g, ' ').trim();
  const rawTitle = cleanTenderName.replace(/^\s*-?\s*[^\s<]+\s*<\s*/, '').trim();
  const shortName = rawTitle.startsWith(bid.agency_name)
    ? rawTitle.slice(bid.agency_name.length).trim().slice(0, 36) || rawTitle.slice(0, 36)
    : rawTitle.slice(0, 36);
  const cleanAddress = details.agencyAddress
    ? details.agencyAddress.replace(/\s+/g, '').replace(/^\d{3,6}/, '')
    : '';
  const mapLocation = [bid.agency_name, cleanAddress].filter(Boolean).join(' ');
  const baseDesc = [
    `⏰ 截標時間：${details.deadline?.display || '未取得'}`,
    `🔔 開標時間：${details.opening?.display || '未取得'}`,
    details.evaluation ? `🗓️ 評選時間：${details.evaluation.display}` : '',
    details.awardMethod ? `📋 決標方式：${details.awardMethod}` : '',
    details.openingLocation ? `🏛️ 開標地點：${details.openingLocation}` : '',
    `招標機關：${bid.agency_name}`,
    `機關地址：${cleanAddress || '未取得'}`,
    `標案名稱：${cleanTenderName}`,
    `標案案號：${bid.tender_id}`,
    details.url ? `採購網公告：${details.url}` : '',
    '評選資訊待gpt核實補充'
  ].filter(Boolean).join('\n');

  const pushEvent = async (calendarId, summary, isoStart, durationMins, location) => {
    const endpoint = `https://www.googleapis.com/calendar/v3/calendars/${encodeURIComponent(calendarId)}/events`;
    const res = await fetch(endpoint, {
      method: 'POST',
      headers: {
        Authorization: `Bearer ${accessToken}`,
        'Content-Type': 'application/json'
      },
      body: JSON.stringify({
        summary,
        location: location || undefined,
        description: baseDesc,
        start: { dateTime: isoStart, timeZone: 'Asia/Taipei' },
        end: { dateTime: addMinutesTaipei(isoStart, durationMins), timeZone: 'Asia/Taipei' }
      }),
      signal: AbortSignal.timeout(REQUEST_TIMEOUT_MS)
    });
    if (!res.ok) {
      const errText = await res.text().catch(() => '');
      throw new Error(`Calendar API ${res.status}: ${errText.slice(0, 150)}`);
    }
    return res.json();
  };

  const tasks = [];
  for (const calendarId of targetCalendarIds) {
    if (details.deadline) {
      tasks.push(pushEvent(
        calendarId,
        `【截標 ${details.deadline.shortLabel}】${bid.agency_name}｜${shortName} (${bid.designer_name})`,
        details.deadline.isoStart,
        30,
        mapLocation
      ));
    }
    if (details.opening) {
      tasks.push(pushEvent(
        calendarId,
        `【開標 ${details.opening.shortLabel}】${bid.agency_name}｜${shortName} (${bid.designer_name})`,
        details.opening.isoStart,
        60,
        mapLocation
      ));
    }
    if (details.evaluation) {
      tasks.push(pushEvent(
        calendarId,
        `【評選 ${details.evaluation.shortLabel}】${bid.agency_name}｜${shortName} (${bid.designer_name})`,
        details.evaluation.isoStart,
        60,
        mapLocation
      ));
    }
  }

  const results = await Promise.allSettled(tasks);
  const createdCount = results.filter((r) => r.status === 'fulfilled').length;
  const errors = results.filter((r) => r.status === 'rejected').map((r) => r.reason?.message);
  return { ok: createdCount > 0, createdCount, calendarsTargeted: targetCalendarIds.length, errors };
}

export default async function handler(req, res) {
  if (req.method !== 'POST') {
    return res.status(405).json({ error: 'method_not_allowed' });
  }

  const payload = req.body;
  const required = ['tender_id', 'tender_name', 'agency_name', 'designer_name'];

  if (!payload || required.some((key) => typeof payload[key] !== 'string' || !payload[key].trim())) {
    return res.status(400).json({ error: 'invalid_payload', message: '欄位驗證失敗' });
  }

  const secret = process.env.PANDORA_IMPORT_HMAC_SECRET;
  const endpoint = process.env.YIZHU_BID_INTAKE_URL || 'https://yizhu-bid-case-manager.vercel.app/api/external-bid-import';

  if (!secret) {
    return res.status(503).json({
      error: 'server_not_configured',
      message: '伺服器未設定 PANDORA_IMPORT_HMAC_SECRET 機密'
    });
  }

  const rawBudget = payload.budget_amount !== undefined ? payload.budget_amount : payload.budget;
  const cleanPayload = {
    tender_id: String(payload.tender_id).trim(),
    tender_name: String(payload.tender_name).trim(),
    agency_name: String(payload.agency_name).trim(),
    designer_name: String(payload.designer_name).trim(),
    budget_amount: parseBudgetAmount(rawBudget)
  };

  const signature = 'sha256=' + crypto
    .createHmac('sha256', secret)
    .update(JSON.stringify(cleanPayload))
    .digest('hex');

  try {
    const upstream = await fetch(endpoint, {
      method: 'POST',
      headers: {
        'content-type': 'application/json',
        'x-pandora-signature': signature
      },
      body: JSON.stringify(cleanPayload)
    });

    const result = await upstream.json().catch(() => ({ error: 'invalid_upstream_response' }));
    console.log('[submit-bid upstream response]:', upstream.status, JSON.stringify(result));

    if (upstream.status === 201) {
      const details = await fetchPccTenderDetails(payload.tender_url);
      const [tgResult, calResult] = await Promise.allSettled([
        sendTelegramBidNotice(cleanPayload, details),
        createGoogleCalendarEvents(cleanPayload, details)
      ]);

      return res.status(201).json({
        ...result,
        notifications: {
          pccDetails: details.ok,
          telegram: tgResult.status === 'fulfilled' ? tgResult.value : { ok: false, reason: tgResult.reason?.message },
          calendar: calResult.status === 'fulfilled' ? calResult.value : { ok: false, reason: calResult.reason?.message }
        }
      });
    }

    return res.status(upstream.status).json(result);
  } catch (err) {
    console.error('[submit-bid upstream error]:', err.message);
    return res.status(500).json({
      error: 'upstream_connect_failed',
      message: err.message || '無法連線至毅築端點'
    });
  }
}
