---
name: Quant.ML Terminal
colors:
  surface: '#fdf8f8'
  surface-dim: '#ddd9d8'
  surface-bright: '#fdf8f8'
  surface-container-lowest: '#ffffff'
  surface-container-low: '#f7f3f2'
  surface-container: '#f1edec'
  surface-container-high: '#ebe7e6'
  surface-container-highest: '#e5e2e1'
  on-surface: '#1c1b1b'
  on-surface-variant: '#444748'
  inverse-surface: '#313030'
  inverse-on-surface: '#f4f0ef'
  outline: '#747878'
  outline-variant: '#c4c7c7'
  surface-tint: '#5f5e5e'
  primary: '#000000'
  on-primary: '#ffffff'
  primary-container: '#1c1b1b'
  on-primary-container: '#858383'
  inverse-primary: '#c8c6c5'
  secondary: '#3d683d'
  on-secondary: '#ffffff'
  secondary-container: '#bbecb5'
  on-secondary-container: '#416d41'
  tertiary: '#000000'
  on-tertiary: '#ffffff'
  tertiary-container: '#1c1b1a'
  on-tertiary-container: '#868382'
  error: '#ba1a1a'
  on-error: '#ffffff'
  error-container: '#ffdad6'
  on-error-container: '#93000a'
  primary-fixed: '#e5e2e1'
  primary-fixed-dim: '#c8c6c5'
  on-primary-fixed: '#1c1b1b'
  on-primary-fixed-variant: '#474746'
  secondary-fixed: '#beefb8'
  secondary-fixed-dim: '#a2d39e'
  on-secondary-fixed: '#002105'
  on-secondary-fixed-variant: '#255027'
  tertiary-fixed: '#e6e2df'
  tertiary-fixed-dim: '#cac6c4'
  on-tertiary-fixed: '#1c1b1a'
  on-tertiary-fixed-variant: '#484645'
  background: '#fdf8f8'
  on-background: '#1c1b1b'
  surface-variant: '#e5e2e1'
typography:
  display-lg:
    fontFamily: Playfair Display
    fontSize: 48px
    fontWeight: '700'
    lineHeight: '1.1'
    letterSpacing: -0.02em
  headline-md:
    fontFamily: Playfair Display
    fontSize: 32px
    fontWeight: '600'
    lineHeight: '1.2'
  headline-sm:
    fontFamily: Playfair Display
    fontSize: 24px
    fontWeight: '600'
    lineHeight: '1.3'
  body-lg:
    fontFamily: Plus Jakarta Sans
    fontSize: 18px
    fontWeight: '400'
    lineHeight: '1.6'
  body-md:
    fontFamily: Plus Jakarta Sans
    fontSize: 16px
    fontWeight: '400'
    lineHeight: '1.5'
  data-lg:
    fontFamily: JetBrains Mono
    fontSize: 20px
    fontWeight: '500'
    lineHeight: '1.2'
    letterSpacing: -0.01em
  data-md:
    fontFamily: JetBrains Mono
    fontSize: 14px
    fontWeight: '500'
    lineHeight: '1.4'
  label-caps:
    fontFamily: Plus Jakarta Sans
    fontSize: 12px
    fontWeight: '700'
    lineHeight: '1'
    letterSpacing: 0.08em
spacing:
  unit: 4px
  gutter: 24px
  margin-page: 40px
  container-padding: 24px
  stack-sm: 8px
  stack-md: 16px
  stack-lg: 32px
---

## Brand & Style

The design system embodies the intersection of elite financial journalism and high-frequency algorithmic trading. It moves away from the typical "dashboard" aesthetic, instead adopting a "Digital Broadsheet" persona—light, airy, and profoundly authoritative. 

The visual direction combines **Minimalism** with **Modern Editorial** influences. It prioritizes the "ink-on-paper" feel, emphasizing legibility, intentional asymmetry, and razor-sharp data visualization. The emotional response is one of calm confidence; the UI does not scream for attention but rewards focused analysis with high-contrast clarity and sophisticated structure.

## Colors

The palette is rooted in a "Paper & Ink" philosophy. The base surface is a creamy off-white, reducing the harsh eye strain of pure digital white while maintaining a premium, physical feel.

- **Surface & Containers:** The background uses the warm off-white (#FAF9F6). Containers use pure white (#FFFFFF) to create subtle lift, defined not by heavy shadows but by ultra-thin 1px borders at 6% opacity.
- **Typography:** Deep ink blue-black (#1A1A1A) provides maximum contrast for headlines, while a warm slate grey (#666660) handles secondary metadata.
- **Functional Accents:** Sage green is the primary brand accent, used for high-confidence signals. Standard financial indicators use Forest Green for growth, Crimson for risk, and Ochre for transitionary states.

## Typography

This design system employs a three-tier typographic strategy to separate narrative, interaction, and raw data.

1.  **Editorial Layer (Playfair Display):** Used for primary headlines and section titles. It provides the "sophisticated" anchor and mimics high-end financial news publications.
2.  **Interface Layer (Plus Jakarta Sans):** A modern geometric sans-serif used for navigation, inputs, and general UI text. It ensures the platform feels like a high-performance tool, not just a document.
3.  **Precision Layer (JetBrains Mono):** All numerical data, tickers, and technical values must use this monospaced font. This ensures that columns of numbers align perfectly for rapid scanning and visual comparison.

## Layout & Spacing

The layout philosophy utilizes an **Asymmetric Grid** to break the monotony of standard SaaS dashboards. 

- **Grid System:** A 12-column layout where primary content (charts, feeds) often spans 7 or 8 columns, while supplemental data (order books, watchlists) occupies the remaining space in a staggered, vertical column.
- **Rhythm:** We use a 4px baseline grid. Spacing is generous to allow the "airy" feel, using 24px as the standard gutter between high-level modules.
- **Responsibility:** On mobile, the asymmetric tiers collapse into a singular vertical flow, but maintain the "ink-on-paper" high-contrast headers to preserve brand identity.

## Elevation & Depth

In keeping with the editorial aesthetic, depth is achieved through **Tonal Layering** and **Line-work** rather than traditional drop shadows.

- **Levels:** Level 0 is the creamy canvas. Level 1 is the pure white container. 
- **Borders:** Containers are defined by 1px solid borders (`#000000` at 6% opacity). No rounded corners are used on major structural containers to reinforce the "terminal" precision.
- **Subtle Overlays:** When modals or dropdowns are required, use a high-radius background blur (Glassmorphism) with a 20% opacity white tint and a slightly darker 1px border.
- **Interaction:** Hover states should be indicated by a subtle shift in background color (from white to the off-white base) or a weight change in typography, rather than a shadow "lift."

## Shapes

The shape language is **Sharp (0)**. 

To maintain the high-performance terminal feel and the "printed" editorial aesthetic, rounded corners are eliminated from structural elements. This creates a sense of mathematical precision and allows data-dense modules to sit flush against one another without awkward negative space at the corners. Small UI elements like checkboxes may use a micro-radius (2px) if necessary for platform accessibility, but buttons and cards must remain sharp.

## Components

- **Buttons:** Primary buttons are deep charcoal (#1A1A1A) with white text, sharp corners, and 12px horizontal padding. Secondary buttons are outlined with 1px borders.
- **Data Tables:** Use 1px horizontal dividers only. Headers are `label-caps` in warm slate grey. Data cells use `data-md` in JetBrains Mono.
- **Inputs:** Underlined style (bottom-border only) to mimic a physical ledger. Labels should float above the line in a small sans-serif.
- **Chips/Status:** Use a light tint of the status color (e.g., 10% Forest Green) as a background with the full-strength color for the text. No borders on chips.
- **Charts:** Use thin 0.5px grid lines in the border-subtle color. Data lines should be 2px thick with no smoothing (maintain the "raw" data look).
- **Theme Toggle:** A prominent, visible toggle in the top-right navigation using a "Sun/Moon" icon set with a labeled "LIGHT / DARK" text toggle for instant accessibility.