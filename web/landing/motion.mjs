// Observe a stationary layout box, never the element whose transform is animated.
export function observeVisibility(
  target,
  onChange,
  { once = false, exitThreshold = 0.5 } = {},
) {
  let visible = false;
  let complete = false;
  const observer = new IntersectionObserver(
    (entries) => {
      for (const entry of entries) {
        if (complete) continue;
        const next = visible
          ? entry.isIntersecting &&
            (exitThreshold === 0
              ? entry.intersectionRatio > 0
              : entry.intersectionRatio >= exitThreshold)
          : entry.isIntersecting && entry.intersectionRatio >= 0.5;
        if (next === visible) continue;
        visible = next;
        onChange(visible);
        if (once && visible) {
          complete = true;
          observer.unobserve(target);
        }
      }
    },
    { threshold: [...new Set([0, exitThreshold, 0.5])] },
  );
  observer.observe(target);
  return observer;
}
