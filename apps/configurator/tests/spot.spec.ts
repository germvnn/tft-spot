import { expect, test, type Page } from "@playwright/test";

const card = (apiName: string, name: string) => ({
  apiName,
  name,
  imageUrl: null,
  setNumber: 18,
});
const akali = { ...card("akali", "Akali"), cost: 1 };
const bow = card("bow", "Recurve Bow");
const augments = [
  { ...card("gold-a", "Gold Economy"), tier: 2, description: "Gain gold." },
  { ...card("gold-b", "Gold Combat"), tier: 2, description: "Gain power." },
  { ...card("gold-c", "Gold Items"), tier: 2, description: "Gain components." },
  { ...card("silver-a", "Silver Economy"), tier: 1, description: null },
  { ...card("prism-a", "Prismatic Economy"), tier: 3, description: null },
];
const catalog = {
  setNumbers: [18],
  champions: [
    akali,
    { ...card("two", "Two Cost"), cost: 2 },
    { ...card("three", "Three Cost"), cost: 3 },
    { ...card("four", "Four Cost"), cost: 4 },
    { ...card("five", "Five Cost"), cost: 5 },
    { ...card("zero", "Zero Cost"), cost: 0 },
  ],
  components: [bow],
  augments,
};
const legacyConfiguration = {
  schemaVersion: 1,
  sourceId: "comp",
  setNumber: 18,
  status: "ready",
  weights: { units: 40, components: 30, augments: 30 },
  components: [{ apiName: "bow", priority: "high" }],
  augments: [{ apiName: "gold-a", priority: "high" }],
  notes: "",
  updatedAt: null,
};
const workspace = {
  source: {
    sourceId: "comp",
    title: "Akali Direction",
    slug: "akali",
    set: 18,
    tier: "A",
    style: "Reroll",
    difficulty: "MEDIUM",
    mainChampion: akali,
    tips: [],
  },
  configuration: legacyConfiguration,
  earlyUnits: [{ ...akali, stars: 1, boardIndex: null, items: [] }],
  finalUnits: [{ ...akali, stars: 3, boardIndex: 1, items: [] }],
  components: [{ ...bow, requiredCount: 2 }],
  augments: [augments[0]],
  itemRecommendations: [],
};
const response = {
  skipped: [],
  recommendations: [
    {
      sourceId: "comp",
      title: "Akali Direction",
      eligible: true,
      score: 85,
      bestAugmentApiName: "gold-a",
      requiredAugmentApiName: null,
      mainChampion: akali,
      finalUnits: [akali],
      style: "Reroll",
      weights: { units: 40, components: 30, augments: 30 },
      evidence: {
        units: [{ apiName: "akali", copies: 2, points: 3 }],
        components: [
          { apiName: "bow", ownedCount: 1, matchedCount: 1, points: 0.75 },
        ],
      },
      variants: [
        {
          augmentApiName: "gold-a",
          eligible: true,
          reason: null,
          score: 85,
          dimensionScores: { units: 100, components: 75, augments: 75 },
          weightedContributions: {
            units: 40,
            components: 22.5,
            augments: 22.5,
          },
        },
      ],
    },
  ],
};

async function mockData(page: Page) {
  await page.route("**/api/spot-catalog", (route) =>
    route.fulfill({ json: catalog }),
  );
  await page.route("**/api/compositions", (route) =>
    route.fulfill({
      json: {
        compositions: [
          {
            sourceId: "comp",
            title: "Akali Direction",
            slug: "akali",
            position: 0,
            configured: true,
          },
        ],
      },
    }),
  );
  await page.route("**/api/compositions/comp", (route) =>
    route.fulfill({ json: workspace }),
  );
  await page.route("**/api/recommendations", (route) =>
    route.fulfill({ json: response }),
  );
}

test("counts mouse buttons, filters costs, submits spot and shows explained ranking", async ({
  page,
}) => {
  await mockData(page);
  const errors: string[] = [];
  page.on("pageerror", (error) => errors.push(error.message));
  await page.goto("/");
  await expect(
    page.getByRole("heading", { name: "Jaki masz spot?" }),
  ).toBeVisible();
  for (const name of ["Four Cost", "Five Cost", "Zero Cost"])
    await expect(
      page.getByRole("button", { name: new RegExp(`^${name}:`) }),
    ).toHaveCount(0);
  const unit = page.getByRole("button", { name: /^Akali:/ });
  await unit.click({ button: "right" });
  await expect(unit).toHaveAccessibleName("Akali: 0 kopii. Dodaj 1");
  await unit.click({ clickCount: 3 });
  await unit.click({ button: "right" });
  await expect(unit).toHaveAccessibleName("Akali: 2 kopii. Dodaj 1");
  await expect(unit.locator("..")).toHaveCSS(
    "border-top-color",
    "rgb(137, 148, 166)",
  );
  await expect(
    page.getByRole("button", { name: /^Two Cost:/ }).locator(".."),
  ).toHaveCSS("border-top-color", "rgb(89, 190, 136)");
  await expect(
    page.getByRole("button", { name: /^Three Cost:/ }).locator(".."),
  ).toHaveCSS("border-top-color", "rgb(91, 159, 240)");
  await page.getByRole("button", { name: /^Recurve Bow:/ }).click();
  await page.getByLabel("Augment 1", { exact: true }).selectOption("gold-a");
  await expect(
    page
      .getByLabel("Augment 2", { exact: true })
      .locator('option[value="gold-a"]'),
  ).toBeDisabled();
  const sent = page.waitForRequest("**/api/recommendations");
  await page.getByRole("button", { name: "Pokaż rekomendacje" }).click();
  expect((await sent).postDataJSON()).toEqual({
    setNumber: 18,
    offeredAugments: ["gold-a"],
    units: [{ apiName: "akali", stars: 1, count: 2 }],
    components: [{ apiName: "bow", count: 1 }],
  });
  await expect(
    page.getByRole("heading", { name: "Akali Direction" }),
  ).toBeVisible();
  await expect(page.locator(".result-score")).toContainText("85.0");
  await expect(page.locator(".result-reasons")).toContainText("Akali ×2");
  await expect(page.locator(".result-reasons")).toContainText(
    "Recurve Bow: wykorzystane 1/1",
  );
  await unit.click();
  await expect(page.locator(".spot-result")).toHaveCount(0);
  expect(errors).toEqual([]);
});

test("rarity dropdown filters options and clears previous rarity selection", async ({
  page,
}) => {
  await mockData(page);
  await page.goto("/");
  const selection = page.getByLabel("Augment 1", { exact: true });
  await selection.selectOption("gold-a");
  await page.getByLabel("Poziom augmentów", { exact: true }).selectOption("1");
  await expect(selection).toHaveValue("");
  await expect(selection.locator('option[value="gold-a"]')).toHaveCount(0);
  await selection.selectOption("silver-a");
  await page.getByLabel("Poziom augmentów", { exact: true }).selectOption("3");
  await selection.selectOption("prism-a");
  await expect(selection).toHaveValue("prism-a");
});

test("F5 and legacy configuration do not crash; tabs retain input and edits", async ({
  page,
}) => {
  await mockData(page);
  const errors: string[] = [];
  page.on("pageerror", (error) => errors.push(error.message));
  await page.goto("/");
  await page.getByRole("button", { name: /^Akali:/ }).click();
  await page.getByRole("link", { name: "Konfigurator", exact: true }).click();
  await expect(
    page.getByRole("checkbox", { name: "Core jednostka Akali" }),
  ).not.toBeChecked();
  await expect(page.getByLabel("Priorytet jednostki Akali")).toHaveCount(0);
  await page.getByRole("checkbox", { name: "Core jednostka Akali" }).check();
  await page.getByRole("link", { name: "Rekomendacje", exact: true }).click();
  await expect(
    page.getByRole("button", { name: /^Akali:/ }),
  ).toHaveAccessibleName("Akali: 1 kopii. Dodaj 1");
  await page.getByRole("link", { name: "Konfigurator", exact: true }).click();
  await expect(
    page.getByRole("checkbox", { name: "Core jednostka Akali" }),
  ).toBeChecked();
  await page.reload();
  await expect(
    page.getByRole("checkbox", { name: "Core jednostka Akali" }),
  ).not.toBeChecked();
  await page.getByRole("link", { name: "Rekomendacje", exact: true }).click();
  await page.reload();
  await expect(
    page.getByRole("heading", { name: "Jaki masz spot?" }),
  ).toBeVisible();
  expect(errors).toEqual([]);
});

test("mobile input fits viewport and server failure has a recovery action", async ({
  page,
}) => {
  await page.setViewportSize({ width: 390, height: 844 });
  await mockData(page);
  await page.route("**/api/spot-catalog", (route) =>
    route.fulfill({ status: 503, json: { detail: "Serwer niedostępny" } }),
  );
  await page.goto("/");
  await expect(page.getByRole("alert")).toContainText("Serwer niedostępny");
  await page.unroute("**/api/spot-catalog");
  await page.route("**/api/spot-catalog", (route) =>
    route.fulfill({ json: catalog }),
  );
  await page.getByRole("button", { name: "Spróbuj ponownie" }).click();
  await expect(page.getByRole("button", { name: /^Akali:/ })).toBeVisible();
  expect(
    await page.evaluate(
      () => document.documentElement.scrollWidth <= window.innerWidth,
    ),
  ).toBe(true);
});

test("core unit defaults to false and survives saving and refresh", async ({
  page,
}) => {
  await mockData(page);
  let savedWorkspace = structuredClone(workspace);
  await page.route("**/api/compositions/comp", (route) =>
    route.fulfill({ json: savedWorkspace }),
  );
  await page.route("**/api/compositions/comp/configuration", async (route) => {
    const configuration = route.request().postDataJSON();
    savedWorkspace = { ...savedWorkspace, configuration };
    await route.fulfill({ json: { configuration } });
  });
  await page.goto("/#configurator");
  const checkbox = page.getByRole("checkbox", { name: "Core jednostka Akali" });
  await expect(checkbox).not.toBeChecked();
  await checkbox.check();
  const request = page.waitForRequest("**/api/compositions/comp/configuration");
  await page
    .getByRole("button", { name: "Zapisz konfigurację", exact: true })
    .click();
  expect((await request).postDataJSON().units[0].core).toBe(true);
  await expect(page.getByRole("status")).toContainText("Zapisano konfigurację");
  await page.reload();
  await expect(checkbox).toBeChecked();
});

test("simulator generates fifty cases and persists a human review across refresh", async ({
  page,
}) => {
  await mockData(page);
  await page.route("**/api/compositions/comp", route => route.fulfill({ json: {
    ...workspace,
    finalUnits: [{ ...workspace.finalUnits[0], items: [bow, bow] }],
  } }));
  await page.route("**/api/compositions/other", route => route.fulfill({ json: {
    ...workspace,
    finalUnits: [{ ...workspace.finalUnits[0], name: "Other carry", items: [] }],
  } }));
  let generated = false;
  const run = {
    id: "00000000-0000-4000-8000-000000000001",
    seed: 42,
    count: 50,
    setNumber: 18,
    createdAt: "2026-09-08T12:00:00Z",
    scoringVersion: "stage-2-1-v2.2",
    entities: { akali, bow, "gold-a": augments[0] },
    cases: Array.from({ length: 50 }, (_, index) => ({
      id: index + 1,
      label: "Pełny opener",
      targetSourceId: "comp",
      targetTitle: "Akali Direction",
      spot: {
        units: [{ apiName: "akali", count: 4 }],
        components: [{ apiName: "bow", count: 3 }],
        offeredAugments: ["gold-a"],
      },
      rankings: [...response.recommendations, { ...response.recommendations[0], sourceId: "other", title: "Other direction" }].map((r) => ({
        ...r,
        evidence: { ...r.evidence, unitFit: { coreCount: 0, coreShare: 0 } },
      })),
      review: null as Record<string, unknown> | null,
      referenceReview: null,
      previousScores: null,
    })),
  };
  await page.route("**/api/simulator/runs", async (route) => {
    if (route.request().method() === "POST") {
      expect(route.request().postDataJSON()).toEqual({
        seed: 42,
        count: 50,
        setNumber: 18,
      });
      generated = true;
      await route.fulfill({ json: run });
    } else await route.fulfill({ json: { runs: generated ? [run] : [] } });
  });
  await page.route(`**/api/simulator/runs/${run.id}`, (route) =>
    route.fulfill({ json: run }),
  );
  await page.route(
    `**/api/simulator/runs/${run.id}/reviews/1`,
    async (route) => {
      run.cases[0].review = route.request().postDataJSON();
      await route.fulfill({ json: run.cases[0].review });
    },
  );
  await page.goto("/#simulator");
  await page.getByRole("button", { name: "Generuj serię" }).click();
  await expect(
    page.getByLabel("Przypadki symulacji").getByRole("button"),
  ).toHaveCount(50);
  const board = page.getByRole("region", { name: "Final composition" });
  await expect(board.getByText("Akali", { exact: true })).toBeVisible();
  await expect(board.getByTitle("Recurve Bow", { exact: true })).toHaveCount(2);
  await page.getByLabel("Oceniana kompozycja").selectOption("other");
  await expect(board.getByText("Other carry")).toBeVisible();
  await expect(board.getByText("Akali", { exact: true })).toHaveCount(0);
  await page.getByLabel("Oceniana kompozycja").selectOption("comp");
  await expect(board.getByText("Akali", { exact: true })).toBeVisible();
  await page.getByLabel("Ocena wyniku").selectOption("too_low");
  await page.getByLabel("Oczekiwane punkty jednostek").fill("35");
  await page.getByLabel("Komentarz do spotu").fill("Dobry opener");
  await page.getByRole("button", { name: "Zapisz i następny" }).click();
  await expect(
    page.getByRole("heading", { name: "#2 · Pełny opener" }),
  ).toBeVisible();
  expect(run.cases[0].review?.expectedUnitFit).toBe(87.5);
  await page.reload();
  await expect(page.getByLabel("Komentarz do spotu")).toHaveValue(
    "Dobry opener",
  );
  await expect(page.getByLabel("Oczekiwane punkty jednostek")).toHaveValue(
    "35",
  );
  await expect(
    page.getByText("1/50 ocenionych", { exact: true }),
  ).toBeVisible();
});
