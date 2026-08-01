const crypto = require("crypto");
const fs = require("fs");
const path = require("path");

const bubblewrapRoot = path.join(
  process.env.APPDATA,
  "npm",
  "node_modules",
  "@bubblewrap",
  "cli",
  "dist",
  "lib"
);
const { init } = require(path.join(bubblewrapRoot, "cmds", "init.js"));

const targetDirectory = path.resolve("android");
const password = crypto.randomBytes(24).toString("base64url");

class FriendaryPrompt {
  printMessage(message) {
    if (message) process.stdout.write(`${String(message)}\n`);
  }

  async promptInput(message, defaultValue, validator) {
    const label = String(message);
    const answers = [
      ["Domain:", "zzz8247.mycafe24.com"],
      ["URL path:", "/"],
      ["Application name:", "Friendary"],
      ["Short name:", "Friendary"],
      ["Application ID:", "com.friendary.app"],
      ["Starting version code", "1"],
      ["Status bar color:", "#6d28d9"],
      ["Splash screen color:", "#fffaf5"],
      ["Icon URL:", "https://zzz8247.mycafe24.com/static/icons/friendary-app-icon-512.png"],
      ["Maskable icon URL:", "https://zzz8247.mycafe24.com/static/icons/friendary-app-icon-512.png"],
      ["Monochrome icon URL:", ""],
      ["Key store location:", path.join("android", "friendary-upload-key.jks")],
      ["Key name:", "friendary"],
      ["First and Last names", "Friendary"],
      ["Organizational Unit", "Friendary"],
      ["Organization", "Friendary"],
      ["Country", "KR"],
    ];
    const match = answers.find(([prefix]) => label.includes(prefix));
    const value = match ? match[1] : defaultValue;
    process.stdout.write(`${label} ${value ?? ""}\n`);
    return (await validator(String(value ?? ""))).unwrap();
  }

  async promptChoice(message, choices, defaultValue, validator) {
    const label = String(message);
    const value = label.includes("Orientation") ? "portrait" : defaultValue;
    process.stdout.write(`${label} ${value}\n`);
    return (await validator(value)).unwrap();
  }

  async promptConfirm(message, defaultValue) {
    const label = String(message);
    let value = defaultValue;
    if (label.includes("Play Billing") || label.includes("geolocation")) value = false;
    if (label.includes("create one now") || label.includes("does not exist")) value = true;
    process.stdout.write(`${label} ${value}\n`);
    return value;
  }

  async promptPassword(message, validator) {
    process.stdout.write(`${String(message)} [generated securely]\n`);
    return (await validator(password)).unwrap();
  }
}

async function main() {
  const config = JSON.parse(
    fs.readFileSync(path.join(process.env.USERPROFILE, ".bubblewrap", "config.json"), "utf8")
  );
  await init(
    {
      manifest: "https://zzz8247.mycafe24.com/static/manifest.webmanifest",
      directory: targetDirectory,
    },
    config,
    new FriendaryPrompt()
  );
  const credentialsPath = path.join(targetDirectory, "signing-credentials.txt");
  if (!fs.existsSync(credentialsPath)) {
    fs.writeFileSync(
      credentialsPath,
      `Friendary Android upload key\nAlias: friendary\nPassword: ${password}\n`,
      { encoding: "utf8", mode: 0o600 }
    );
  }
}

main().catch((error) => {
  console.error(error);
  process.exitCode = 1;
});
