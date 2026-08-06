/**
 * Vercel Serverless Function: /api/submit-bid
 * 說明：C 專案 (測試用) 轉發登記投標意向至毅築標案管理系統 API 中繼點
 * 註：本 API Route 為 [測試用]，在後端保存 PANDORA_IMPORT_HMAC_SECRET 並計算 HMAC-SHA256 標頭轉發
 */

import crypto from 'node:crypto';

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

  // 轉換 payload 為標準契約格式（包含預算金額 budget，確保無多餘欄位影響簽章）
  const parseBudget = (val) => {
    if (val === undefined || val === null || val === '') return null;
    if (typeof val === 'number') return isNaN(val) ? null : val;
    const cleaned = String(val).replace(/[^0-9.]/g, '');
    const num = parseFloat(cleaned);
    return isNaN(num) ? null : num;
  };

  const cleanPayload = {
    tender_id: String(payload.tender_id).trim(),
    tender_name: String(payload.tender_name).trim(),
    agency_name: String(payload.agency_name).trim(),
    designer_name: String(payload.designer_name).trim(),
    budget: parseBudget(payload.budget)
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
        'x-pandora-signature': signature,
      },
      body: JSON.stringify(cleanPayload),
    });

    const result = await upstream.json().catch(() => ({ error: 'invalid_upstream_response' }));
    console.log('[submit-bid upstream response]:', upstream.status, JSON.stringify(result));
    return res.status(upstream.status).json(result);
  } catch (err) {
    console.error('[submit-bid upstream error]:', err.message);
    return res.status(500).json({
      error: 'upstream_connect_failed',
      message: err.message || '無法連線至毅築端點'
    });
  }
}
