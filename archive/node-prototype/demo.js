// demo.js
const { fetchNewTweets } = require('./xscanner/fetchTweets');
const { validateSignal } = require('./ai/validateSignal');
const { sendSignalToTelegram } = require('./utils/sendSignal');

(async () => {
  console.log('🧪 [demo] Manual run started.');

  const tweets = await fetchNewTweets();

  if (tweets.length === 0) {
    console.log('📭 No new tweets found.');
    return;
  }

  for (const tweet of tweets) {
    console.log(`🔍 Checking @${tweet.username}: "${tweet.text.slice(0, 50)}..."`);
    const result = await validateSignal(tweet.text);

    if (!result || result.scam || result.signal === 'IGNORE') {
      console.log(`⏩ Ignored tweet from @${tweet.username}`);
      continue;
    }

    console.log(`📡 Forwarding ${result.signal} for ${result.token} from @${tweet.username}`);
    await sendSignalToTelegram(result, tweet.username);
    await new Promise((res) => setTimeout(res, 1500));
  }

  console.log('✅ [demo] Finished.');
})();
