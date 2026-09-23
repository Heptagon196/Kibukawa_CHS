import { cpSync, existsSync, mkdirSync, readFileSync, rmSync, writeFileSync } from "node:fs";
import { dirname, join, resolve } from "node:path";
import { fileURLToPath } from "node:url";

const desktopRoot = resolve(dirname(fileURLToPath(import.meta.url)), "..");
const webRoot = resolve(desktopRoot, "..");
const outputRoot = join(desktopRoot, "dist");

const games = [
  { id: "saina-onsen", title: "狭稻温泉乡杀人事件" },
  { id: "birthday", title: "诞生纪念日事件" },
  { id: "operation-check-2", title: "运行测试事件Ⅱ" }
];

const missing = games.filter(({ id }) => !existsSync(join(webRoot, id, "build", "index.html")));
if (missing.length) {
  const names = missing.map(({ title, id }) => `- ${title}: web/${id}/build/index.html`).join("\n");
  throw new Error(
    `缺少桌面应用所需的网页构建：\n${names}\n\n` +
      "请先在仓库根目录下载原作资源并运行 web/README.md 中的三个构建命令。"
  );
}

rmSync(outputRoot, { recursive: true, force: true });
mkdirSync(outputRoot, { recursive: true });
cpSync(join(desktopRoot, "frontend"), outputRoot, { recursive: true });

for (const game of games) {
  cpSync(join(webRoot, game.id, "build"), join(outputRoot, "games", game.id), {
    recursive: true
  });
}

const packageInfo = JSON.parse(readFileSync(join(desktopRoot, "package.json"), "utf8"));
writeFileSync(
  join(outputRoot, "build-info.json"),
  `${JSON.stringify({ version: packageInfo.version, games }, null, 2)}\n`,
  "utf8"
);

console.log(`Prepared ${games.length} games in ${outputRoot}`);
