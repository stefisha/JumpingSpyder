// validateSignal.js
const { OpenAI } = require('openai');
require('dotenv').config();

const openai = new OpenAI({ apiKey: process.env.OPENAI_API_KEY });

function buildPrompt(tweet) {
  return `You are an expert crypto analyst and quant trader bot.

Analyze the following tweet and respond in strict JSON format. Your job is to detect scams and generate actionable trading signals for crypto traders.

Tweet:
"${tweet}"

Respond with:

{
  "scam": true | false,
  "signal": "BUY" | "SELL" | "IGNORE",
  "token": "$XYZ",
  "confidence": 0-100,
  "expected_window": "Next 15–30 mins",
  "historical_accuracy": 0-100,
  "reason": "Concise summary of the signal and why it matters",
  "take_profit": "+15%",
  "stop_loss": "-5%",
  "action": "Buy via Jupiter | Raydium",
  "note": "GM = Get Moving! DYOR — not financial advice."
}`;
}

async function validateSignal(tweetText) {
  try {
    const res = await openai.chat.completions.create({
      model: 'gpt-4',
      temperature: 0,
      messages: [
        { role: 'user', content: buildPrompt(tweetText) }
      ]
    });

    const content = res.choices[0].message.content;
    const parsed = JSON.parse(content);
    return parsed;
  } catch (err) {
    console.error('❌ OpenAI validation error:', err);
    return null;
  }
}

module.exports = { validateSignal };