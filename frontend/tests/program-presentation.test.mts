import assert from "node:assert/strict";
import test from "node:test";

import {
  formatProgramCreatedAt,
  personalProgramArtwork,
  programPresentation,
} from "../lib/program-presentation.ts";

test("completed audio uses the green completed label", () => {
  assert.deepEqual(programPresentation("completed", true), {
    key: "completed",
    label: "已生成",
    playable: true,
  });
});

test("in-progress audio uses the amber generating label", () => {
  assert.deepEqual(programPresentation("generating", false), {
    key: "generating",
    label: "生成中",
    playable: false,
  });
});

test("text-ready audio failure uses the red failed label", () => {
  assert.deepEqual(programPresentation("text_ready", false), {
    key: "failed",
    label: "生成失败",
    playable: false,
  });
});

test("created time is displayed below the program title", () => {
  const localTime = new Date(2026, 7, 24, 15, 6).toISOString();
  assert.equal(formatProgramCreatedAt(localTime), "生成于 8月24日 15:06");
});

test("personal program covers rotate without adjacent duplicates", () => {
  const covers = Array.from({ length: 12 }, (_, index) => personalProgramArtwork(index));

  assert.equal(new Set(covers.slice(0, 6)).size, 6);
  assert.equal(covers[0], covers[6]);
  covers.slice(1).forEach((cover, index) => {
    assert.notEqual(cover, covers[index]);
  });
});
