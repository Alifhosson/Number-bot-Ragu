const request = require('request');
const TelegramBot = require('node-telegram-bot-api');
const { parsePhoneNumberFromString } = require('libphonenumber-js');

// === CONFIG ===
const TELEGRAM_TOKEN = '7827515074:AAF5xMmdBQiG8FBmirtVoNwiHpK4QbWXzQU';
const CHAT_ID = '-4878231537';
const PANEL_URL = 'http://109.236.84.81/ints/agent/res/data_smscdr.php?fdate1=2025-10-06%2000:00:00&fdate2=2025-10-06%2023:59:59&iDisplayLength=25';
const HEADERS = {
  'Accept': 'application/json, text/javascript, */*; q=0.01',
  'Connection': 'keep-alive',
  'User-Agent': 'Mozilla/5.0',
  'Cookie': 'PHPSESSID=m0tdq3vf7tq5vs5epv3s3k2cge',
  'X-Requested-With': 'XMLHttpRequest'
};

const bot = new TelegramBot(TELEGRAM_TOKEN, { polling: true });

let lastId = null;

function getBDTime() {
  return new Date().toLocaleString('en-GB', { timeZone: 'Asia/Dhaka' });
}

function getFlagEmoji(countryCode) {
  if (!countryCode) return '';
  return countryCode
    .toUpperCase()
    .replace(/./g, char => String.fromCodePoint(127397 + char.charCodeAt()));
}

function getCountryInfo(phone) {
  try {
    const parsed = parsePhoneNumberFromString(`+${phone}`);
    if (parsed && parsed.country) {
      const countryNames = new Intl.DisplayNames(['en'], { type: 'region' });
      const countryName = countryNames.of(parsed.country);
      const flag = getFlagEmoji(parsed.country);
      return `${countryName} ${flag}`;
    }
  } catch (e) {}
  return 'Unknown 🌐';
}

function fetchSMS() {
  request({ url: PANEL_URL, headers: HEADERS }, async (error, response, body) => {
    if (error || response.statusCode !== 200) return console.error('Fetch error:', error);

    try {
      const data = JSON.parse(body);
      if (!data.aaData || data.aaData.length === 0) return;

      const latest = data.aaData[0];
      const smsId = latest[0];
      if (smsId === lastId) return;
      lastId = smsId;

      const number = latest[2] || 'N/A';
      const otpMatch = (latest[5] || '').match(/\d{4,10}/);
      const otp = otpMatch ? otpMatch[0] : 'N/A';
      const service = latest[3] || 'Unknown';
      const country = getCountryInfo(number);
      const time = getBDTime();
      const fullMsg = (latest[5] || 'No message').replace(/\n\s*\n/g, '\n');

      const finalMessage = `
📞 <b>𝙽𝚞𝚖𝚋𝚎𝚛:</b> <code>${number}</code>
🔑 <b>𝐘𝐨𝐮𝐫 𝐎𝐓𝐏:</b> <code>${otp}</code>
🌍 <b>𝙲𝚘𝚞𝚗𝚝𝚛𝚢:</b> ${country}
📱 <b>𝚂𝚎𝚛𝚟𝚒𝚌𝚎:</b> ${service}
⏰ <b>𝚃𝚒𝚖𝚎:</b> ${time}

💌 <b>Full Message:</b>
<pre>${fullMsg}</pre>
`;

      // === শুধু মেসেজ পাঠাবে, কোনো বাটন নয় ===
      await bot.sendMessage(CHAT_ID, finalMessage, { parse_mode: 'HTML' });

      console.log('✅ New SMS sent:', number);
    } catch (err) {
      console.error('Parse error:', err);
    }
  });
}

// প্রতি 10 সেকেন্ডে চেক করবে
setInterval(fetchSMS, 1000);
