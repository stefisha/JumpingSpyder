// fetchTweets.js
const { TwitterApi } = require('twitter-api-v2');
const fs = require('fs');
const path = require('path');
require('dotenv').config();

const twitterClient = new TwitterApi({
  appKey: process.env.TWITTER_API_KEY,
  appSecret: process.env.TWITTER_API_SECRET,
  accessToken: process.env.TWITTER_ACCESS_TOKEN,
  accessSecret: process.env.TWITTER_ACCESS_TOKEN_SECRET,
});

const storePath = path.join(__dirname, 'store.json');
const accounts = require('./accounts.json');

function loadLastSeenIds() {
  if (!fs.existsSync(storePath)) return {};
  return JSON.parse(fs.readFileSync(storePath, 'utf-8'));
}

function saveLastSeenIds(data) {
  fs.writeFileSync(storePath, JSON.stringify(data, null, 2));
}

async function fetchNewTweets() {
  const lastSeen = loadLastSeenIds();
  const results = [];

  for (const username of accounts) {
    try {
      const user = await twitterClient.v2.userByUsername(username);
      const userId = user.data.id;
      const timeline = await twitterClient.v2.userTimeline(userId, {
        max_results: 5,
        exclude: 'retweets,replies',
        'tweet.fields': ['created_at', 'text'],
      });

      const lastId = lastSeen[username] || '0';
      const newTweets = timeline.data?.data?.filter(t => t.id > lastId) || [];

      if (newTweets.length > 0) {
        lastSeen[username] = newTweets[0].id;
        results.push(...newTweets.map(tweet => ({ ...tweet, username })));
      }
    } catch (err) {
      console.error(`❌ Error fetching for ${username}:`, err);
    }
  }

  saveLastSeenIds(lastSeen);
  return results;
}

module.exports = { fetchNewTweets };