// cron.js
const { fetchNewTweets } = require('./xscanner/fetchTweets');
const { validateSignal } = require('./ai/validateSignal');
const { sendSignalToTelegram } = require('./utils/sendSignal');

(async () => {
  console.log('🔁 Running cron: Checking for new tweets...');
  const tweets = await fetchNewTweets();

  for (const tweet of tweets) {
    const result = await validateSignal(tweet.text);

    if (!result || result.scam || result.signal === 'IGNORE') {
      console.log(`⏩ Ignored tweet from @${tweet.username}`);
      continue;
    }

    await sendSignalToTelegram(result, tweet.username);
    await new Promise(res => setTimeout(res, 1500)); // avoid Telegram flood
  }

  console.log('✅ Cron finished.');
})();