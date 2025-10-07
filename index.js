const axios = require("axios").default;
const tough = require("tough-cookie");
const { wrapper } = require("axios-cookiejar-support");
const cheerio = require("cheerio");
const TelegramBot = require("node-telegram-bot-api");
const { parsePhoneNumberFromString } = require("libphonenumber-js");
const countryEmoji = require("country-emoji");

// === CONFIG ===
const TELEGRAM_TOKEN =
  process.env.TELEGRAM_TOKEN ||
  "8430148380:AAHCV_3hnek0GaZRlPl4tCtc2XNVGuU-L5U";

// multiple chat ids supported
const CHAT_IDS = (process.env.CHAT_IDS ||
  "-1002391889544,-1002789126504")
  .split(",")
  .map(id => id.trim());

const LOGIN_PAGE_URL = "http://109.236.84.81/ints/login";
const LOGIN_POST_URL = "http://109.236.84.81/ints/signin";
const API_URL =
  "http://109.236.84.81/ints/agent/res/data_smscdr.php?fdate1=2025-10-07%2000%3A00%3A00&fdate2=2025-10-07%2023%3A59%3A59&frange=&fclient=&fnum=&fcli=&fgdate=&fgmonth=&fgrange=&fgclient=&fgnumber=&fgcli=&fg=0&sEcho=1&iColumns=9&sColumns=%2C%2C%2C%2C%2C%2C%2C%2C%2C&iDisplayStart=0&iDisplayLength=25&mDataProp_0=0&sSearch_0=&bRegex_0=false&bSearchable_0=true&bSortable_0=true&mDataProp_1=1&sSearch_1=&bRegex_1=false&bSearchable_1=true&bSortable_1=true&mDataProp_2=2&sSearch_2=&bRegex_2=false&bSearchable_2=true&bSortable_2=true&mDataProp_3=3&sSearch_3=&bRegex_3=false&bSearchable_3=true&bSortable_3=true&mDataProp_4=4&sSearch_4=&bRegex_4=false&bSearchable_4=true&bSortable_4=true&mDataProp_5=5&sSearch_5=&bRegex_5=false&bSearchable_5=true&bSortable_5=true&mDataProp_6=6&sSearch_6=&bRegex_6=false&bSearchable_6=true&bSortable_6=true&mDataProp_7=7&sSearch_7=&bRegex_7=false&bSearchable_7=true&bSortable_7=true&mDataProp_8=8&sSearch_8=&bRegex_8=false&bSearchable_8=false&sSearch=&bRegex=false&iSortCol_0=0&sSortDir_0=desc&iSortingCols=1";

const USERNAME = process.env.SMS_USER || "Smartmethod";
const PASSWORD = process.env.SMS_PASS || "Smartmethod904";

// === INIT ===
const jar = new tough.CookieJar();
const client = wrapper(axios.create({ jar, withCredentials: true }));
const bot = new TelegramBot(TELEGRAM_TOKEN, { polling: false });

let lastId = null;

// === GLOBAL ERROR HANDLERS ===
process.on("uncaughtException", err => {
  console.error("Uncaught Exception:", err);
});
process.on("unhandledRejection", err => {
  console.error("Unhandled Rejection:", err);
});

// === OTP Extract ===
function extractOtp(text) {
  if (!text) return null;
  const m = text.match(/\b\d{3,4}(?:[-\s]?\d{2,4})\b/);
  return m ? m[0] : null;
}

// === Country detect ===
function getCountryInfo(number) {
  if (!number) return "Unknown 🌍";
  let s = String(number).trim().replace(/[^\d+]/g, "");
  if (s.startsWith("00")) s = "+" + s.slice(2);
  if (!s.startsWith("+")) s = "+" + s;

  try {
    const phone = parsePhoneNumberFromString(s);
    if (phone && phone.country) {
      const iso = phone.country;
      const name = countryEmoji.name(iso) || iso;
      const flag = countryEmoji.flag(iso) || "🌍";
      return `${name} ${flag}`;
    }
  } catch {
    return "Unknown 🌍";
  }
  return "Unknown 🌍";
}

// === Map API row ===
function mapRow(row) {
  return {
    id: row[0],
    date: row[0],
    number: row[2],
    cli: row[3],
    client: row[4],
    message: row[5],
    country: getCountryInfo(row[2]),
  };
}

// === Telegram Send ===
async function sendTelegramSMS(sms) {
  const otp = extractOtp(sms.message) || "N/A";
  const final = `<b>${sms.country} ${sms.cli} OTP Received...</b>

📞 <b>Number:</b> <code>${sms.number}</code>
🔑 <b>𝐘𝐨𝐮𝐫 𝐎𝐓𝐏:</b> <code>${otp}</code>
🌍 <b>𝐂𝐨𝐮𝐧𝐭𝐫𝐲:</b> ${sms.country}
📱 <b>𝐒𝐞𝐫𝐯𝐢𝐜𝐞:</b> ${sms.cli}
📆 <b>Date:</b> ${sms.date}

💬 <b>Full SMS:</b>
<pre>${sms.message}</pre>`;

  for (const chatId of CHAT_IDS) {
    try {
      await bot.sendMessage(chatId, final, { parse_mode: "HTML" });
      console.log(`✅ Sent to ${chatId}`);
    } catch (e) {
      console.error(`❌ Failed to send to ${chatId}:`, e.message);
    }
  }
}

// === Login + captcha ===
async function performLoginAndSaveCookies() {
  try {
    console.log("🔐 GET login page...");
    const getRes = await client.get(LOGIN_PAGE_URL, {
      headers: { "User-Agent": "Mozilla/5.0" },
    });
    const $ = cheerio.load(String(getRes.data || ""));

    // parse captcha
    let captchaAnswer = null;
    const bodyText = $("body").text();
    const qMatch = bodyText.match(/What is\s*([\-]?\d+)\s*([\+\-\*xX\/])\s*([\-]?\d+)/i);
    if (qMatch) {
      const a = Number(qMatch[1]),
        op = qMatch[2],
        b = Number(qMatch[3]);
      switch (op) {
        case "+":
          captchaAnswer = String(a + b);
          break;
        case "-":
          captchaAnswer = String(a - b);
          break;
        case "*":
        case "x":
        case "X":
          captchaAnswer = String(a * b);
          break;
        case "/":
          captchaAnswer = b !== 0 ? String(Math.floor(a / b)) : "0";
          break;
      }
      console.log("Detected captcha:", qMatch[0], "=>", captchaAnswer);
    }

    const formParams = new URLSearchParams();
    formParams.append("username", USERNAME);
    formParams.append("password", PASSWORD);
    if (captchaAnswer !== null) formParams.append("capt", captchaAnswer);

    $("form input[type=hidden]").each((i, el) => {
      const name = $(el).attr("name");
      const val = $(el).attr("value") || "";
      if (name && !["username", "password", "capt"].includes(name))
        formParams.append(name, val);
    });

    const postRes = await client.post(LOGIN_POST_URL, formParams.toString(), {
      headers: {
        "Content-Type": "application/x-www-form-urlencoded",
        "Origin": "http://109.236.84.81",
        "Referer": LOGIN_PAGE_URL,
        "User-Agent": "Mozilla/5.0",
      },
      maxRedirects: 0,
      validateStatus: s => s >= 200 && s < 400,
    });

    console.log("Login POST status:", postRes.status);
    const body = String(postRes.data || "");
    const looksLikeLoginPage = /<title>.*Login/i.test(body);
    if (
      (postRes.status === 302 || postRes.status === 303) &&
      !looksLikeLoginPage
    )
      return true;
    if (!looksLikeLoginPage && postRes.status === 200) return true;

    console.warn("❌ Login failed, got login page again.");
    return false;
  } catch (err) {
    console.error("Login error:", err.message);
    return false;
  }
}

// === Fetch SMS API ===
async function fetchSmsApi() {
  try {
    const res = await client.get(API_URL, {
      headers: {
        "User-Agent": "Mozilla/5.0",
        "X-Requested-With": "XMLHttpRequest",
        "Accept": "application/json, text/javascript, */*; q=0.01",
        "Referer": "http://109.236.84.81/ints/agent/SMSCDRReports",
      },
    });
    return res.data;
  } catch (e) {
    console.error("Fetch SMS API error:", e.message);
    return null;
  }
}

// === Worker ===
async function startWorker() {
  try {
    let ok = await performLoginAndSaveCookies();
    if (!ok) {
      console.error("Login failed — retrying in 30s...");
      setTimeout(startWorker, 30000);
      return;
    }

    const data = await fetchSmsApi();
    if (data && Array.isArray(data.aaData) && data.aaData.length > 0) {
      const latest = mapRow(data.aaData[0]);
      lastId = latest.id;
      await sendTelegramSMS(latest);
    } else {
      console.log("No SMS found initially.");
    }

    setInterval(async () => {
      try {
        const d = await fetchSmsApi();
        if (!d || !Array.isArray(d.aaData) || d.aaData.length === 0) return;
        const latest = mapRow(d.aaData[0]);
        if (latest.id !== lastId) {
          lastId = latest.id;
          await sendTelegramSMS(latest);
        }
      } catch (err) {
        console.error("Interval fetch error:", err.message);
      }
    }, 10000);
  } catch (err) {
    console.error("Worker error:", err);
    console.log("Retrying worker in 30s...");
    setTimeout(startWorker, 30000);
  }
}

// === Run ===
startWorker();
