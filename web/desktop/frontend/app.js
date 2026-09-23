const games = {
  "saina-onsen": { title: "狭稻温泉乡杀人事件", path: "games/saina-onsen/index.html" },
  birthday: { title: "诞生纪念日事件", path: "games/birthday/index.html" },
  "operation-check-2": { title: "运行测试事件Ⅱ", path: "games/operation-check-2/index.html" }
};

const library = document.querySelector("#library");
const playerShell = document.querySelector("#player-shell");
const frame = document.querySelector("#game-frame");
const loading = document.querySelector("#loading");
const homeButton = document.querySelector("#home-button");

function showLibrary() {
  frame.src = "about:blank";
  playerShell.hidden = true;
  library.hidden = false;
  homeButton.hidden = true;
  document.title = "癸生川网页番外汉化";
}

function launch(gameId) {
  const game = games[gameId];
  if (!game) return;
  library.hidden = true;
  playerShell.hidden = false;
  homeButton.hidden = false;
  loading.hidden = false;
  frame.src = game.path;
  document.title = `${game.title} · 癸生川网页番外`;
}

frame.addEventListener("load", () => {
  loading.hidden = true;
  frame.focus();
});

document.addEventListener("click", async (event) => {
  const releaseLink = event.target.closest('[data-release]');
  if (releaseLink && window.__TAURI_INTERNALS__) {
    event.preventDefault();
    const status = document.querySelector('#link-status');
    status.hidden = true;
    try {
      await window.__TAURI_INTERNALS__.invoke('open_release_post', { gameId: releaseLink.dataset.release });
    } catch (error) {
      status.textContent = '无法打开浏览器，请稍后重试。';
      status.hidden = false;
      console.error(error);
    }
    return;
  }
  const gameButton = event.target.closest("[data-game]");
  if (gameButton) launch(gameButton.dataset.game);
  if (event.target.closest('[data-action="home"]')) showLibrary();
});

window.addEventListener("keydown", (event) => {
  if (event.altKey && event.key === "ArrowLeft") {
    event.preventDefault();
    showLibrary();
  }
});
