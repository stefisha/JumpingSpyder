const { Telegraf } = require('telegraf');
require('dotenv').config();
const { getPublicKeyForUserId, checkBalance } = require('./solana/paymentGate');

const bot = new Telegraf(process.env.BOT_TOKEN);

// Shared responses
const responses = {
  start: "*Hi this is Jumpy 🕷️📊*\n\n" +
    "You're currently still in development.\n" +
    "Want to be the first to test out Jumpy when it goes live?\n" +
    "✨ Join our waitlist!\n\n",
    // "🚀 Here’s the [link](https://docs.google.com/forms/d/e/1FAIpQLSet7cXEsGpPuPCr0KrLxSlZdOudLLBZNqj-TQ1mB5G4eqhkjA/viewform)",

  get_signals: "*📡 Get Signals*\n\n" +
    "Signal tracking activated. You’ll now receive live trading signals from curated crypto sentiment sources.\n\n" +
    "To stop, use /stop or change settings (coming soon).",

  track_token: "*🕵️ Track Token*\n\n" +
    "Please type the token you'd like to track, e.g.:\n" +
    "`/track SOL`\n\n" +
    "We’ll send you real-time sentiment for that token.",

  help: "🙋 *Jumpy\\_Bot Help*\n\n" +
    "📡 *Get Signals* – Subscribe to real-time sentiment-based crypto alerts.\n" +
    "🕵️ *Track Token* – Focus alerts on a specific token.\n" +
    "🧪 *Feedback* – Send your thoughts, bugs, or roasts.\n" +
    "💸 *Is this free?* – During beta, yes — totally free. After launch, Basic access will be $5/month, and Premium (with sentiment analytics + auto-trading) will be $15/month.\n" +
    "🤖 *Where do the signals come from?* – We scan influencer accounts, trending crypto topics, and key project chatter on X.\n\n" +
    "Still have questions? Email us: support@jumpingspyder.com",

  feedback: "🧪 *Feedback*\n\n" +
    "We’re building fast — and your input makes it better.\n\n" +
    "Tell us what’s broken, what’s confusing, or what would make Jumpy\\_Bot better. Send feedback anytime here or email us at support@jumpingspyder.com.",

  settings: "⚙️ *Settings*\n\n" +
    "Coming soon: you’ll be able to configure alert frequency, add watchlists, choose signal sources, and manage trading preferences.\n\n" +
    "For now, stay tuned — or shoot us a feature request under Feedback."
};

// /start command
bot.start((ctx) => {
  ctx.telegram.sendMessage(ctx.chat.id, responses.start, {
    parse_mode: 'Markdown',
    reply_markup: {
      inline_keyboard: [
        [
            { text: '📡 Join waitlist', url: 'https://docs.google.com/forms/d/e/1FAIpQLSet7cXEsGpPuPCr0KrLxSlZdOudLLBZNqj-TQ1mB5G4eqhkjA/viewform' },
            { text: '🕵️ Follow us', url: 'https://x.com/jumpingspyd3r' }
        ],
        // [
        //   { text: '📡 Get Signals', callback_data: 'get_signals' },
        //   { text: '🕵️ Track Token', callback_data: 'track_token' }
        // ],
        // [
        //   { text: '🙋 Help', callback_data: 'help' },
        //   { text: '🧪 Feedback', callback_data: 'feedback' },
        //   { text: '⚙️ Settings', callback_data: 'settings' }
        // ]
      ]
    }
  });
});

// 📡 Get Signals
bot.command('getsignals', (ctx) => ctx.reply(responses.get_signals, { parse_mode: 'Markdown' }));
bot.action('get_signals', async (ctx) => {
  await ctx.answerCbQuery();
  await ctx.editMessageText(responses.get_signals, { parse_mode: 'Markdown' });
});

// 🕵️ Track Token
bot.command('track_token', (ctx) => ctx.reply(responses.track_token, { parse_mode: 'Markdown' }));
bot.action('track_token', async (ctx) => {
  await ctx.answerCbQuery();
  await ctx.editMessageText(responses.track_token, { parse_mode: 'Markdown' });
});

// 🙋 Help
bot.command('help', (ctx) => ctx.reply(responses.help, { parse_mode: 'Markdown' }));
bot.action('help', async (ctx) => {
  await ctx.answerCbQuery();
  await ctx.editMessageText(responses.help, { parse_mode: 'Markdown' });
});

// 🧪 Feedback
bot.command('feedback', (ctx) => ctx.reply(responses.feedback, { parse_mode: 'Markdown' }));
bot.action('feedback', async (ctx) => {
  await ctx.answerCbQuery();
  await ctx.editMessageText(responses.feedback, { parse_mode: 'Markdown' });
});

// ⚙️ Settings
bot.command('settings', (ctx) => ctx.reply(responses.settings, { parse_mode: 'Markdown' }));
bot.action('settings', async (ctx) => {
  await ctx.answerCbQuery();
  await ctx.editMessageText(responses.settings, { parse_mode: 'Markdown' });
});

// /subscribe command
bot.command('subscribe', async (ctx) => {
  const userId = ctx.from.id;
  const publicKey = getPublicKeyForUserId(userId);
  const balance = await checkBalance(publicKey);
  if (balance > 0.00001) {
    ctx.reply(`You are subscribed! You have ${balance} SOL on your public key: ${publicKey}`);
  } else {
    ctx.reply(`You are not subscribed! \nPlease top up your account with 0.01 SOL on your public key: ${publicKey}`);
  }
});

// subscribe action (for inline button)
bot.action('subscribe', async (ctx) => {
  const userId = ctx.from.id;
  const publicKey = getPublicKeyForUserId(userId);
  const balance = await checkBalance(publicKey);
  if (balance > 0.00001) {
    await ctx.answerCbQuery();
    await ctx.editMessageText(`You are subscribed! You have ${balance} SOL on your public key: ${publicKey}`);
  } else {
    await ctx.answerCbQuery();
    await ctx.editMessageText(`You are not subscribed! \nPlease top up your account with 0.01 SOL on your public key: ${publicKey}`);
  }
});

// /stop command
bot.command('stop', (ctx) => {
  ctx.reply('🚫 You have stopped receiving signals and notifications. You can /start again anytime.');
});

// stop action (for inline button)
bot.action('stop', async (ctx) => {
  await ctx.answerCbQuery();
  await ctx.editMessageText('🚫 You have stopped receiving signals and notifications. You can /start again anytime.');
});

// Fallback
bot.action(/.*/, async (ctx) => {
  await ctx.answerCbQuery();
  await ctx.editMessageText("🚧 Feature coming soon!", { parse_mode: 'Markdown' });
});

// Launch
bot.launch();
console.log("✅ Jumpy_Bot is running...");
