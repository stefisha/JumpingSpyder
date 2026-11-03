// sendSignal.js
const fetch = require('node-fetch');
require('dotenv').config();

function formatSignalAlert(signal, username) {
  return (
    `🕷️ *ALPHA DETECTED!*
` +
    `@${username} | \`${signal.token}\` | *${signal.signal} SIGNAL*

` +
    `📊 *Strength:* ${signal.confidence}%
` +
    `⏰ *Window:* ${signal.expected_window}
` +
    `📈 *Accuracy:* ${signal.historical_accuracy}%

` +
    `🚀 *Action:* ${signal.action}
` +
    `🎯 TP: ${signal.take_profit} | 🛑 SL: ${signal.stop_loss}

` +
    `💬 "${signal.reason}"
` +
    `📌 _${signal.note}_`
  );
}

async function sendSignalToTelegram(signal, username) {
  const msg = formatSignalAlert(signal, username);
  const url = `https://api.telegram.org/bot${process.env.BOT_TOKEN}/sendMessage`;

  const res = await fetch(url, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      chat_id: process.env.TELEGRAM_CHANNEL_ID,
      text: msg,
      parse_mode: 'Markdown'
    })
  });

  const json = await res.json();
  if (!json.ok) {
    console.error('❌ Telegram error:', json);
  }
}

module.exports = { sendSignalToTelegram };