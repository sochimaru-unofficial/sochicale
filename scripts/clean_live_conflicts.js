import fs from "fs";

const livePath = "./data/live.json";
const streamPath = "./data/streams.json";

function main() {
  // --- ファイル読込 ---
  const live = JSON.parse(fs.readFileSync(livePath, "utf8"));
  const streams = JSON.parse(fs.readFileSync(streamPath, "utf8"));

  // --- 各ID一覧作成 ---
  const streamIds = new Set([
    ...streams.live?.map(v => v.id) || [],
    ...streams.upcoming?.map(v => v.id) || [],
    ...streams.completed?.map(v => v.id) || [],
  ]);

  // --- live.completed から stream側に存在するものを削除 ---
  const beforeCount = live.completed.length;
  live.completed = live.completed.filter(v => !streamIds.has(v.id));
  const afterCount = live.completed.length;

  if (afterCount < beforeCount) {
    fs.writeFileSync(livePath, JSON.stringify(live, null, 2));
    console.log(`🧹 Removed ${beforeCount - afterCount} duplicated completed items from live.json`);
  } else {
    console.log("✅ No conflicts found between live.json and streams.json");
  }
}

main();
