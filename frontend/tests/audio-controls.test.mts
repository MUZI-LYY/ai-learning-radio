import assert from "node:assert/strict";
import test from "node:test";

import { AUDIO_JUMP_SECONDS } from "../lib/audio-controls.ts";

test("audio jump controls move five seconds at a time", () => {
  assert.equal(AUDIO_JUMP_SECONDS, 5);
});
