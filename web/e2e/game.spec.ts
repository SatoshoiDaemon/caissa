import { test, expect, type Page } from "@playwright/test";

async function register(page: Page, username: string) {
  await page.goto("/login");
  await page.getByRole("button", { name: "Criar conta" }).click();
  await page.getByLabel("Usuário").fill(username);
  await page.getByLabel("Senha").fill("a-test-password-for-caissa");
  await page.getByRole("button", { name: "Criar conta" }).click();
  await expect(page.getByRole("heading", { name: "Códigos de recuperação" })).toBeVisible();
  await page.getByRole("link", { name: "Ir para o lobby" }).click();
}

async function move(page: Page, from: string, to: string) {
  await page.locator('[data-square="' + from + '"]').click();
  const target = page.locator('[data-square="' + to + '"]');
  await expect(target).toHaveClass(/target/);
  await target.click();
}

test("two accounts play a classical checkmate, reconnect and review stored moves", async ({ browser }) => {
  const whiteContext = await browser.newContext();
  const blackContext = await browser.newContext({ viewport: { width: 390, height: 844 } });
  const white = await whiteContext.newPage();
  const black = await blackContext.newPage();
  const suffix = Date.now().toString(36);
  const whiteName = "white_" + suffix;
  const blackName = "black_" + suffix;

  try {
    await register(white, whiteName);
    await register(black, blackName);
    await white.getByLabel("Nome da sala").fill("Partida de verificação");
    await white.getByLabel("Relógio").selectOption("classical");
    await white.getByRole("button", { name: "Criar sala" }).click();
    await expect(white.getByText("Conectado", { exact: true })).toBeVisible();
    await expect(white.getByText("30:00", { exact: true })).toHaveCount(2);
    await black.goto(white.url());
    await black.getByLabel("Seu nome").fill(blackName);
    await black.getByRole("button", { name: "Entrar na sala" }).click();
    await expect(black.getByText("Conectado", { exact: true })).toBeVisible();
    await expect(white.getByRole("heading", { name: "Brancas jogam" })).toBeVisible();

    await move(white, "f2", "f3");
    await expect(black.getByText("1. f3")).toBeVisible();
    await black.reload();
    await expect(black.getByText("Conectado", { exact: true })).toBeVisible();
    await expect(black.getByText("1. f3")).toBeVisible();
    await move(black, "e7", "e5");
    await expect(white.getByText("2. e5")).toBeVisible();
    await move(white, "g2", "g4");
    await expect(black.getByText("3. g4")).toBeVisible();
    await move(black, "d8", "h4");
    await expect(white.getByRole("heading", { name: "Xeque-mate" })).toBeVisible();
    await expect(black.getByRole("heading", { name: "Xeque-mate" })).toBeVisible();

    await black.getByRole("navigation").getByRole("link", { name: blackName }).click();
    await expect(black.getByRole("heading", { name: "Histórico de partidas" })).toBeVisible();
    await expect(black.getByText("Vitória", { exact: true })).toBeVisible();
    await black.getByRole("link", { name: "Xeque-mate · classical" }).click();
    await black.getByRole("button", { name: "4. Qh4#" }).click();
    await expect(black.getByText("4 / 4")).toBeVisible();
    await black.getByLabel("Idioma").selectOption("en-US");
    await expect(black.getByRole("heading", { name: "Review game" })).toBeVisible();
  } finally {
    await Promise.allSettled([whiteContext.close(), blackContext.close()]);
  }
});

test("a guest plays locally with server-side validation", async ({ page }) => {
  await page.goto("/lobby");
  await page.getByLabel("Brancas", { exact: true }).fill("Alice");
  await page.getByLabel("Pretas", { exact: true }).fill("Bob");
  await page.getByRole("button", { name: "Iniciar partida local" }).click();
  await move(page, "e2", "e4");
  await expect(page.getByText("1. e4")).toBeVisible();
  await page.reload();
  await move(page, "e7", "e5");
  await expect(page.getByText("2. e5")).toBeVisible();
});
