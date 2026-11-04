import { observeVisibility } from "./motion.mjs";
const menuToggle = document.querySelector(".menu-toggle");
const mobileNav = document.getElementById("mobile-nav");
function setMenu(open) {
  menuToggle.setAttribute("aria-expanded", String(open));
  menuToggle.setAttribute(
    "aria-label",
    open ? "Close navigation" : "Open navigation",
  );
  mobileNav.hidden = !open;
}
menuToggle.addEventListener("click", () =>
  setMenu(menuToggle.getAttribute("aria-expanded") !== "true"),
);
mobileNav.addEventListener("click", (event) => {
  if (event.target.closest("a")) setMenu(false);
});
document.addEventListener("keydown", (event) => {
  if (event.key === "Escape" && !mobileNav.hidden) {
    setMenu(false);
    menuToggle.focus();
  }
});
const desktop = window.matchMedia("(min-width: 701px)");
desktop.addEventListener("change", () => {
  if (desktop.matches) setMenu(false);
});

// Original Framer motion values, reproduced with the browser animation API.
// No Framer runtime or third-party animation dependency is required.
const reducedMotion = window.matchMedia("(prefers-reduced-motion: reduce)");
const runningAnimations = new Set();
function springFrames(
  from,
  to,
  { stiffness = 350, damping = 60, mass = 1 } = {},
) {
  const frames = [];
  const rate = damping / (2 * mass);
  const discriminant = rate * rate - stiffness / mass;
  const duration = 1800;
  for (let time = 0; time <= duration; time += 20) {
    const seconds = time / 1000;
    let remainder;
    if (discriminant > 0) {
      const root = Math.sqrt(discriminant);
      const r1 = -rate + root;
      const r2 = -rate - root;
      remainder =
        (-r2 * Math.exp(r1 * seconds) + r1 * Math.exp(r2 * seconds)) /
        (r1 - r2);
    } else {
      const frequency = Math.sqrt(-discriminant);
      remainder = frequency
        ? Math.exp(-rate * seconds) *
          (Math.cos(frequency * seconds) +
            (rate / frequency) * Math.sin(frequency * seconds))
        : Math.exp(-rate * seconds) * (1 + rate * seconds);
    }
    const progress = time === duration ? 1 : 1 - remainder;
    frames.push(from(progress, to));
  }
  return frames;
}
function spring(element, frame, delay = 0, settings = {}, paused = false) {
  if (reducedMotion.matches) return;
  const animation = element.animate(springFrames(frame, null, settings), {
    duration: 1800,
    delay,
    fill: "both",
    easing: "linear",
  });
  if (paused) {
    animation.pause();
    animation.currentTime = 0;
  }
  runningAnimations.add(animation);
  animation.finished
    .then(() => runningAnimations.delete(animation))
    .catch(() => runningAnimations.delete(animation));
  return animation;
}
const heroArt = document.querySelector(".hero-art");
spring(heroArt, (p) => ({
  opacity: p,
  transform: `translateX(${300 * (1 - p)}px) scale(${0.8 + 0.2 * p})`,
}));
spring(
  document.querySelector(".portfolio-card"),
  (p) => ({ opacity: p, transform: `translateY(${50 * (1 - p)}px)` }),
  700,
);

const phoneTilt = document.querySelector(".phone-tilt");
const phoneScene = document.querySelector(".phone-scene");
const phoneAnimation = spring(
  phoneTilt,
  (p) => ({
    transform: `perspective(1200px) rotateX(${30 * (1 - p)}deg)`,
  }),
  0,
  { stiffness: 200, damping: 60, mass: 1.2 },
  true,
);
observeVisibility(phoneScene, (visible) => {
  if (reducedMotion.matches || !phoneAnimation) return;
  // Reverse from the current frame instead of snapping to an endpoint.
  phoneAnimation.playbackRate = visible ? 1 : -1;
  phoneAnimation.play();
});

document.querySelectorAll(".step").forEach((step) => {
  const animation = spring(
    step,
    (p) => ({
      opacity: p,
      transform: `translateY(${50 * (1 - p)}px)`,
    }),
    200,
    {},
    true,
  );
  observeVisibility(
    step.parentElement,
    (visible) => {
      if (visible && !reducedMotion.matches) animation?.play();
    },
    { once: true },
  );
});
const coinAnimation = spring(
  document.querySelector(".solana-coin"),
  (p) => ({
    opacity: p,
    transform: `translateY(${50 * (1 - p)}px) rotate(-4deg)`,
  }),
  1000,
  {},
  true,
);
observeVisibility(
  phoneScene,
  (visible) => {
    if (reducedMotion.matches || !coinAnimation) return;
    if (visible) coinAnimation.play();
    else {
      // Reset only after the stationary scene has fully left the viewport.
      coinAnimation.pause();
      coinAnimation.currentTime = 0;
    }
  },
  { exitThreshold: 0 },
);

function sizePartnerLoop() {
  // The original ticker's speed is 60px/s, independent of viewport width.
  const group = document.querySelector(".partner-group");
  document.querySelector(".partner-track").style.animationDuration =
    `${group.getBoundingClientRect().width / 60}s`;
}
new ResizeObserver(sizePartnerLoop).observe(
  document.querySelector(".partner-window"),
);
sizePartnerLoop();
reducedMotion.addEventListener("change", () => {
  if (reducedMotion.matches) {
    runningAnimations.forEach((animation) => animation.cancel());
    phoneAnimation?.cancel();
    coinAnimation?.cancel();
  }
});

// Keep native details semantics and animate the FAQ's height and answer reveal.
const faqAnimations = new WeakMap();
document.querySelectorAll(".faq-list details").forEach((details) => {
  const summary = details.querySelector("summary");
  summary.addEventListener("click", (event) => {
    if (reducedMotion.matches) return;
    event.preventDefault();
    const previous = faqAnimations.get(details);
    const opening = previous ? !previous.opening : !details.open;
    const start = details.getBoundingClientRect().height;
    previous?.animation.cancel();
    details.style.height = "auto";
    details.open = true;
    const end = opening
      ? details.getBoundingClientRect().height
      : summary.getBoundingClientRect().height;
    const animation = details.animate(
      [{ height: `${start}px` }, { height: `${end}px` }],
      { duration: 280, easing: "cubic-bezier(.22,1,.36,1)" },
    );
    faqAnimations.set(details, { animation, opening });
    if (opening)
      details.querySelector("p").animate(
        [
          { opacity: 0, transform: "translateY(6px)" },
          { opacity: 1, transform: "translateY(0)" },
        ],
        { duration: 280, easing: "ease-out" },
      );
    animation.onfinish = () => {
      details.open = opening;
      details.style.height = "";
      faqAnimations.delete(details);
    };
  });
});

const tickerPause = document.querySelector(".ticker-pause");
const partnerTrack = document.querySelector(".partner-track");
tickerPause.addEventListener("click", () => {
  const paused = tickerPause.getAttribute("aria-pressed") !== "true";
  tickerPause.setAttribute("aria-pressed", String(paused));
  tickerPause.setAttribute(
    "aria-label",
    paused ? "Resume partner animation" : "Pause partner animation",
  );
  tickerPause.textContent = paused ? "▶" : "Ⅱ";
  partnerTrack.dataset.paused = String(paused);
});
