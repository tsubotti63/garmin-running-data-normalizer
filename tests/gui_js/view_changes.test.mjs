// The records that changed since the output before (stage X7 of v2.3.0): the
// line of the normalization page under the result of its run (flow.mjs), the
// address that opens the view page on them, and the view of the view page
// (view_flow.mjs): why it cannot show, its lines, its lists, and its notes.
// The catalogs are those of the pages, so that the words checked are the
// words shown. Made-up names only.
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { test } from "node:test";

import * as flow from "../../src/garmin_running_data_normalizer/gui/static/flow.mjs";
import { translate } from "../../src/garmin_running_data_normalizer/gui/static/i18n.mjs";
import * as view from "../../src/garmin_running_data_normalizer/gui/static/view_flow.mjs";

const catalogs = Object.fromEntries(
  ["en", "ja"].map((language) => [
    language,
    JSON.parse(readFileSync(new URL(`../../src/garmin_running_data_normalizer/gui/static/i18n/${language}.json`, import.meta.url), "utf8")),
  ]),
);

// The words of a message, as the pages write them (view.mjs describe).
function words(message, language = "ja") {
  if (message === null || message === undefined) {
    return "";
  }
  if (typeof message.text === "string") {
    return message.text;
  }
  const params = { ...message.params };
  for (const [name, key] of Object.entries(message.keyParams ?? {})) {
    params[name] = typeof key === "string" ? translate(catalogs, language, key) : words(key, language);
  }
  return translate(catalogs, language, message.key, params);
}

// The numbers of the changes, as view/changes.py change_counts gives them.
function counts(fields = {}) {
  return {
    added: 0,
    removed: 0,
    changed: 0,
    shoes_changed: 0,
    unmatched: { before: 0, now: 0 },
    pairs: { added: 0, removed: 0, changed: 0 },
    names_unread: null,
    shoes_unread: null,
    ...fields,
  };
}

test("the numbers of the changes are said in their order, only those of 1 or more", () => {
  const all = counts({ added: 3, changed: 4, shoes_changed: 3, removed: 1, pairs: { added: 1, changed: 2, removed: 0 } });
  const { lines, changed } = flow.changeCountLines(all);
  assert.equal(changed, true);
  assert.deepEqual(
    lines.map((line) => words(line)),
    ["アクティビティ：新しく入った 3 回・値が変わった 4 回・靴が変わった 3 回・前回の出力にだけある 1 回。", "靴：新しい 1 足・変わった 2 足。"],
  );
  assert.deepEqual(
    lines.map((line) => words(line, "en")),
    ["Activities: 3 new, 4 with values changed, 3 with shoes changed, 1 in the output before only.", "Shoes: 1 new, 2 changed."],
  );
  // One part alone, and the shoes alone.
  assert.deepEqual(flow.changeCountLines(counts({ removed: 2 })).lines.map((line) => words(line)), ["アクティビティ：前回の出力にだけある 2 回。"]);
  assert.deepEqual(flow.changeCountLines(counts({ pairs: { added: 0, changed: 0, removed: 1 } })).lines.map((line) => words(line)), ["靴：前回の出力にだけある 1 足。"]);
});

test("no change is said, and the records that could not be matched and what was not read", () => {
  const none = flow.changeCountLines(counts());
  assert.equal(none.changed, false);
  assert.deepEqual(none.lines.map((line) => words(line)), ["前回の出力から変わった記録はありません。"]);
  // The records that could not be matched only: no change, with their numbers
  // (the checker's review of the plan of the making of X7, 3).
  const unmatched = flow.changeCountLines(counts({ unmatched: { before: 1, now: 2 } }));
  assert.equal(unmatched.changed, false);
  assert.deepEqual(unmatched.lines.map((line) => words(line)), [
    "前回の出力から変わった記録はありません。",
    "同じ記録か分からず、くらべられなかった記録：今の出力 2 回・前回の出力 1 回。",
  ]);
  assert.equal(words(unmatched.lines[1], "en"), "Records that could not be matched, and so were not compared: 2 in the output now, 1 in the output before.");
  // The names and the shoes that one output did not read are not compared.
  const unread = flow.changeCountLines(counts({ added: 1, names_unread: "before", shoes_unread: "both" }));
  assert.deepEqual(unread.lines.map((line) => words(line)), [
    "アクティビティ：新しく入った 1 回。",
    "前回の出力の名前は大きすぎて読まなかったので、名前はくらべていません。",
    "前回と今の出力の靴は大きすぎて読まなかったので、靴はくらべていません。",
  ]);
  assert.equal(words(unread.lines[2], "en"), "The shoes of both outputs were too large to read, so the shoes are not compared.");
  // Values of another form are not said.
  for (const odd of [null, undefined, {}, counts({ added: -1, changed: "2", names_unread: "other" })]) {
    assert.deepEqual(flow.changeCountLines(odd).lines.map((line) => words(line)), ["前回の出力から変わった記録はありません。"]);
  }
});

test("the fourth box says the changes while they are counted, when they are, and when they cannot be", () => {
  assert.deepEqual(flow.changeRecordsView(null), { lines: [], button: false });
  const counting = flow.changeRecordsView({ status: "counting" });
  assert.deepEqual([counting.lines.map((line) => words(line)), counting.button], [["前回の出力とくらべています…"], false]);
  const ready = flow.changeRecordsView({ status: "ready", answer: { ...counts({ added: 1 }), view: true } });
  assert.deepEqual([ready.lines.map((line) => words(line)), ready.button], [["アクティビティ：新しく入った 1 回。"], true]);
  // Not where the view page cannot show them (Codex's second read of the diff
  // of X7, 1): the numbers alone.
  for (const view of [false, undefined]) {
    const alone = flow.changeRecordsView({ status: "ready", answer: { ...counts({ added: 1 }), view } });
    assert.deepEqual([alone.lines.map((line) => words(line)), alone.button], [["アクティビティ：新しく入った 1 回。"], false]);
  }
  // No button without a change.
  const none = flow.changeRecordsView({ status: "ready", answer: { ...counts({ unmatched: { before: 0, now: 3 } }), view: true } });
  assert.equal(none.button, false);
  const failed = flow.changeRecordsView({ status: "failed", code: "HANDOFF_INVALID" });
  assert.deepEqual([failed.lines.map((line) => words(line)), failed.button], [["前回の出力とくらべられませんでした（コード HANDOFF_INVALID）。"], false]);
  assert.deepEqual(flow.changeRecordsView({ status: "failed", code: null }).lines.map((line) => words(line, "en")), ["Could not compare with the output before."]);
});

test("the view page opens on the changes by the fragment of its address", () => {
  assert.equal(flow.viewPageAddress("k", "auto", true, true), "/view#key=k&output=run&show=changes");
  // As before without them.
  assert.equal(flow.viewPageAddress("k", "auto", true), "/view#key=k&output=run");
  assert.equal(flow.viewPageAddress("k", "dark", false), "/view#key=k&theme=dark");
});

test("why the changes cannot show is said under the item of the menu", () => {
  assert.equal(view.changesWhy({ state: "ready", before: "older", reasons: [] }), null);
  // A reading of the output before that failed keeps the item.
  assert.equal(view.changesWhy({ state: "unreadable", before: "older", reasons: [] }), null);
  assert.equal(words(view.changesWhy({ state: "none", before: null, reasons: [] })), "前回の出力がありません。");
  assert.equal(words(view.changesWhy({ state: "not_remembered", before: null, reasons: [] })), "この出力は、覚えている出力の中にありません。");
  assert.equal(words(view.changesWhy({ state: "no_summary", before: "older", reasons: [] })), "出力の要約が読めません。");
  assert.equal(
    words(view.changesWhy({ state: "differs", before: "older", reasons: ["timezone"] })),
    "前回の出力（older）とは、日時に使うタイムゾーンが違います。",
  );
  assert.equal(
    words(view.changesWhy({ state: "differs", before: "older", reasons: ["how", "version"] }), "en"),
    "The output before (older) differs in how it was normalized (Snapshots, or this Export alone), the version of this app.",
  );
  for (const odd of [null, undefined, {}, { state: "differs", before: "older", reasons: ["other"] }, { state: "other" }]) {
    assert.equal(words(view.changesWhy(odd)), "前回の出力がありません。");
  }
  assert.deepEqual(view.changesAvailableFrom({ state: "unreadable", before: "older", reasons: [], code: "OUTPUT_CHANGED" }), { state: "ready", before: "older", reasons: [] });
  assert.deepEqual(view.changesAvailableFrom({ state: "differs", before: "older", reasons: ["how"] }), { state: "differs", before: "older", reasons: ["how"] });
});

test("the date and time of the lists has its year", () => {
  assert.equal(words(view.changesWhen({ day: "2025-06-28", datetime: "2025-06-28T15:00:00+09:00" }, "ja")), "2025/6/28（土）15:00");
  assert.equal(words(view.changesWhen({ day: "2025-06-28", datetime: "2025-06-28T15:00:00+09:00" }, "en"), "en"), "Sat 6/28/2025 15:00");
  // The date alone where the output has no time of the day.
  assert.equal(words(view.changesWhen({ day: "2024-08-05", datetime: null }, "ja")), "2024/8/5（月）");
  assert.equal(words(view.changesWhen({ day: null, datetime: null }, "ja")), "—");
});

// An answer of the view page, as /api/view/changes gives it.
function answer() {
  const shoesBefore = [
    { name: "Road A", day: "2025-01-01", number: null, begin: "2025-01-01", end: null, maximum: 800000 },
    { name: "Road A", day: "2023-01-01", number: null, begin: "2023-01-01", end: null, maximum: 800000 },
    { name: "Trail C", day: null, number: null, begin: "2023-01-01", end: null, maximum: 600000 },
  ];
  const shoesNow = [
    { name: "Road A", day: "2025-01-01", number: null, begin: "2025-01-01", end: null, maximum: 1000000 },
    { name: "Trail C", day: null, number: null, begin: "2023-01-01", end: "2025-06-30", maximum: 600000 },
    { name: "Road E", day: null, number: null, begin: "2025-06-25", end: null, maximum: 800000 },
  ];
  return {
    state: "ready",
    before: "garmin-run-all-before",
    now: "garmin-run-all-now",
    reasons: [],
    ...counts({ added: 1, changed: 1, shoes_changed: 1, removed: 1, pairs: { added: 1, changed: 1, removed: 1 } }),
    list_added: [
      { day: "2025-06-29", datetime: "2025-06-29T15:00:00+09:00", type: "running", name: "Morning 2", values: { dist: 9000, time: 3000, hr: null, mx: null, cad: null, asc: null }, shoes: [2], unknown: false },
    ],
    list_removed: [
      { day: "2025-06-11", datetime: "2025-06-11T06:00:00+09:00", type: "running", name: null, values: { dist: 5000, time: 2100, hr: null, mx: null, cad: null, asc: null }, shoes: [], unknown: false },
    ],
    list_changed: [
      {
        day: "2025-06-29",
        datetime: "2025-06-29T06:00:00+09:00",
        type: "running",
        name: "Pace",
        fields: [
          { field: "dist", before: 5000, now: 6234 },
          { field: "time", before: 2400, now: 2461 },
          { field: "type", before: "running", now: "trail_running" },
          { field: "shoes", before: { shoes: [0, 1], unknown: false }, now: { shoes: [1], unknown: true } },
        ],
      },
    ],
    list_shoes_changed: [
      { day: "2024-08-05", datetime: null, type: "treadmill_running", name: "Pace", before: { shoes: [], unknown: false }, now: { shoes: [0], unknown: false } },
    ],
    list_pairs: [
      { kind: "added", pair: 2, fields: [] },
      { kind: "changed", pair: 0, fields: [{ field: "maximum", before: 800000, now: 1000000 }] },
      { kind: "changed", pair: 1, fields: [{ field: "end", before: null, now: "2025-06-30" }] },
      { kind: "removed", before_pair: 1, fields: [] },
    ],
    shoes_before: shoesBefore,
    shoes_now: shoesNow,
    more: { added: 0, removed: 0, changed: 0, shoes_changed: 0, pairs: 0 },
  };
}

function cells(table, language = "ja") {
  return table.rows.map((row) => row.map((cell) => words(cell, language)));
}

test("the lists of the changes are those of the answer, written as the list of a period writes them", () => {
  const tables = view.changesTables(answer(), "ja");
  assert.deepEqual(
    tables.map((table) => [table.name, words(table.title)]),
    [
      ["added", "新しく入ったアクティビティ（1）"],
      ["changed", "値が変わったアクティビティ（1）"],
      ["shoes_changed", "靴が変わったアクティビティ（1）"],
      ["removed", "前回の出力にだけあるアクティビティ（1）"],
      ["pairs", "靴（3）"],
    ],
  );
  assert.deepEqual(tables[0].heads.map((head) => words(head)), ["日時", "名前", "種目", "距離", "時間", "靴"]);
  assert.deepEqual(cells(tables[0]), [["2025/6/29（日）15:00", "Morning 2", "ランニング", "9.0 km", "50:00", "Road E"]]);
  assert.deepEqual(tables[1].heads.map((head) => words(head)), ["日時", "名前", "変わった所", "前", "今"]);
  assert.deepEqual(cells(tables[1]), [
    ["2025/6/29（日）6:00", "Pace", "距離", "5.0 km", "6.2 km"],
    ["2025/6/29（日）6:00", "Pace", "時間", "40:00", "41:01"],
    ["2025/6/29（日）6:00", "Pace", "種目", "ランニング", "トレイルラン"],
    ["2025/6/29（日）6:00", "Pace", "靴", "Road A（使い始め 2025年1月1日）・Road A（使い始め 2023年1月1日）", "Trail C・靴か分からない"],
  ]);
  assert.deepEqual(cells(tables[2]), [["2024/8/5（月）", "Pace", "（靴なし）", "Road A（使い始め 2025年1月1日）"]]);
  // A name that the output does not have is a dash.
  assert.deepEqual(cells(tables[3])[0].slice(0, 2), ["2025/6/11（水）6:00", "—"]);
  assert.deepEqual(cells(tables[4]), [
    ["Road E", "新しい靴", "—", "2025年6月25日から"],
    ["Road A（使い始め 2025年1月1日）", "上限の距離", "800.0 km", "1,000.0 km"],
    ["Trail C", "使い終わり", "—", "2025年6月30日"],
    ["Road A（使い始め 2023年1月1日）", "前回の出力にだけある", "—", "—"],
  ]);
  assert.deepEqual(cells(view.changesTables(answer(), "en")[4], "en")[0], ["Road E", "New pair", "—", "from June 25, 2025"]);
});

test("lists without rows are left out, and the rows not shown are said", () => {
  const few = { ...answer(), ...counts({ added: 600 }), list_added: answer().list_added, more: { added: 599, removed: 0, changed: 0, shoes_changed: 0, pairs: 0 } };
  const tables = view.changesTables(few, "ja");
  assert.deepEqual(tables.map((table) => table.name), ["added"]);
  assert.equal(words(tables[0].title), "新しく入ったアクティビティ（600）");
  assert.equal(words(tables[0].more), "ほかに古い 599 回は出していません。");
  assert.equal(words(tables[0].more, "en"), "Older ones not shown: 599.");
  assert.deepEqual(view.changesTables({ state: "ready", ...counts() }, "ja"), []);
});

test("the lines and the notes of the view say the numbers, or why the outputs were not compared", () => {
  assert.deepEqual(view.changesLines(answer()).map((line) => words(line)), [
    "アクティビティ：新しく入った 1 回・値が変わった 1 回・靴が変わった 1 回・前回の出力にだけある 1 回。",
    "靴：新しい 1 足・変わった 1 足・前回の出力にだけある 1 足。",
  ]);
  assert.equal(words(view.changesOutputs(answer())), "前回の出力：garmin-run-all-before　今の出力：garmin-run-all-now（どちらもこのバージョン・同じ作り方・同じタイムゾーン）");
  assert.deepEqual(view.changesNotes(answer()).map((note) => words(note)), [
    "区切りの一覧の列（日時・名前・種目・距離・時間・平均心拍・最大心拍・ピッチ・総上昇量）と靴をくらべています。日付の無い記録と、今日より後の記録はくらべません。",
    "スナップショットで作った出力どうしでは、Garmin で消したランも残るので、前回の出力にだけある記録には出ません。",
    "id の無い記録は、値が変わると、前回の出力にだけある記録と、新しく入った記録に分かれて出ます。",
  ]);
  assert.deepEqual(view.changesLines({ state: "unreadable", before: "older", code: "OUTPUT_CHANGED" }).map((line) => words(line)), ["前回の出力（older）を読めませんでした（コード OUTPUT_CHANGED）。"]);
  assert.deepEqual(view.changesLines({ state: "none", before: null, reasons: [] }).map((line) => words(line)), ["前回の出力がありません。"]);
  assert.deepEqual(view.changesNotes({ state: "none" }), []);
});
