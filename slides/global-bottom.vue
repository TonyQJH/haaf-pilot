<script setup>
import { computed } from 'vue'

// Slides that use the dark KDD background (class `kdd-dark` in slides.md).
// The footer is a DOM sibling of the slide, not a child, so it cannot inherit
// the slide's colour scheme — we hide it on those pages instead.
// Update this list if the deck order changes; worst case is a cosmetic
// footer on a dark slide.
const DARK_PAGES = [1, 14, 15]

const nav = $slidev.nav
const hidden = computed(() => DARK_PAGES.includes(nav.currentPage))
</script>

<template>
  <footer v-if="!hidden" class="deck-footer">
    <div class="deck-footer-left">
      <img src="/KDD26-Logo4-black.png" alt="" class="deck-footer-logo">
      <span class="deck-footer-sep">|</span>
      <span>Beyond Benchmark Islands &nbsp;·&nbsp; Agent4IR Workshop</span>
    </div>
    <div class="deck-footer-right">
      {{ nav.currentPage }} / {{ nav.total }}
    </div>
  </footer>
</template>

<style scoped>
.deck-footer {
  position: absolute;
  bottom: 0;
  left: 0;
  right: 0;
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 0 1.6rem 0.5rem 1.6rem;
  font-size: 0.62rem;
  letter-spacing: 0.02em;
  color: var(--muted, #55676A);
  pointer-events: none;
}

.deck-footer-left {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  opacity: 0.72;
}

.deck-footer-logo {
  height: 13px;
  width: auto;
}

.deck-footer-sep {
  opacity: 0.4;
}

.deck-footer-right {
  font-variant-numeric: tabular-nums;
  opacity: 0.6;
}

:global(html.dark) .deck-footer-logo {
  filter: brightness(0) invert(1);
  opacity: 0.8;
}
</style>
