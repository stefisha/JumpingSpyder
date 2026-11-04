import test from "node:test";
import assert from "node:assert/strict";
import { observeVisibility } from "../web/landing/motion.mjs";

class Observer {
  constructor(callback, options) {
    this.callback = callback;
    this.options = options;
  }
  observe(target) {
    this.target = target;
  }
  unobserve(target) {
    this.unobserved = target;
  }
  report(ratio) {
    this.callback([
      {
        target: this.target,
        intersectionRatio: ratio,
        isIntersecting: ratio > 0,
      },
    ]);
  }
}
globalThis.IntersectionObserver = Observer;

test("phone changes direction only across the actual 50% threshold", () => {
  const changes = [];
  const stationaryScene = {};
  const observer = observeVisibility(stationaryScene, (visible) =>
    changes.push(visible),
  );
  [0, 0.01, 0.49].forEach((ratio) => observer.report(ratio));
  assert.deepEqual(changes, []);
  [0.5, 0.5, 0.8, 0.5, 0.49, 0.2, 0.6].forEach((ratio) =>
    observer.report(ratio),
  );
  assert.deepEqual(changes, [true, false, true]);
  assert.equal(observer.target, stationaryScene);
});
test("steps play once after 50% visibility, rather than on first contact", () => {
  const changes = [];
  const target = {};
  const observer = observeVisibility(
    target,
    (visible) => changes.push(visible),
    { once: true },
  );
  observer.report(0.1);
  assert.equal(observer.unobserved, undefined);
  [0.5, 0, 1].forEach((ratio) => observer.report(ratio));
  assert.deepEqual(changes, [true]);
  assert.equal(observer.unobserved, target);
});
test("coin stays revealed below 50% and resets only after fully leaving", () => {
  const changes = [];
  const observer = observeVisibility({}, (visible) => changes.push(visible), {
    exitThreshold: 0,
  });
  [0.1, 0.5, 0.49, 0.01, 0.6, 0, 0.1, 0.5].forEach((ratio) =>
    observer.report(ratio),
  );
  assert.deepEqual(changes, [true, false, true]);
  assert.deepEqual(observer.options.threshold, [0, 0.5]);
});
