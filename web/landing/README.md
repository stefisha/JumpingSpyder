# JumpingSpyder original landing page

A faithful static recreation of the owner-supplied Framer landing page and screenshots. It preserves the original section order, marketing copy, phone visuals, partner-logo carousel, feature cards, FAQ answers, and footer. No frontend framework or build step is required.

## Preview

```sh
python3 -m http.server 8766 --bind 127.0.0.1 --directory web/landing
```

The editable files are `web/landing/index.html`, `web/landing/styles.css`, and `web/landing/app.js`. All artwork is served locally. The card background was removed with the built-in image editing tool; its transparent PNG is `web/landing/assets/solflare-card-cutout.png`. The supplied phone image is preserved as `web/landing/assets/jumpy-phone.png`.

Join Waitlist opens the owner-supplied Google Form: https://forms.gle/XivsuNZGuh3CKnFS7
Get the Alpha opens the original bot: https://t.me/jumpys_bot

The Solana Foundation/BLKN strip loops horizontally, as observed on the original site, pauses on hover, and becomes static when reduced motion is requested. The mobile menu supports Escape and closes after navigation. The six FAQ disclosures work with click and keyboard input.

## Scope

This is a recreation of the original marketing design, not evidence that its illustrative returns, delivery timing, historical accuracy, partnerships, trading controls, or Pro features have been newly validated. Backend capabilities and their verification remain documented separately in the JumpingSpyder repository. The original alpha delivered into one Telegram chat; individual delivery needs subscriber management and per-recipient state. This page implements navigation and external entry points, not those backend features.

The original Framer project was not edited. The website can be hosted independently from the Python worker.

Motion follows the recovered Framer source: the hero enters from 300px to the right at 0.8 scale; the portfolio enters from 50px below after 700ms; steps reveal after 200ms at a 50% visibility threshold; the How phone tilts from 30° to flat with perspective 1200px; the Solana coin reveals after 1000ms and repeats on re-entry. Spring damping, stiffness, and mass come from the original component source. The partner ticker travels at 60px/s. Reduced-motion preferences disable these effects. DM Sans is served locally; original responsive font presets use 44/50px mobile hero, 26/34px mobile section titles, and 16/25px body copy.
