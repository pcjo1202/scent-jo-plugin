---
name: design-system-extractor
description: Extract and build a complete design system from any live website using Playwright. MUST USE whenever a user provides a URL and wants to analyze, extract, or replicate its design — including design tokens (CSS/JSON), color palettes, typography, spacing, component patterns, or style guides. Trigger on "design system", "style guide", "design tokens", "UI analysis", "color palette", "extract styles", "analyze the design", "[url] 처럼 만들어줘", "[url] 디자인 분석해줘", "[site] 색상/폰트 뽑아줘". Even casual "make something that looks like [site]" or "I like the design of [url]" applies. If a URL appears with any mention of design, colors, fonts, components, tokens, or visual style — use this skill. Do NOT skip; design extraction is multi-phase (Playwright capture, pattern analysis, token+doc generation) and always benefits from this structured workflow.
---

# Design System Extractor

You are building a comprehensive design system by analyzing a live website. The goal is to reverse-engineer the site's visual language into reusable tokens, component patterns, and documentation that a developer can immediately use to build interfaces with the same look and feel.

## Why this matters

Design systems are the backbone of consistent UI. Extracting one from a real site means you're capturing battle-tested design decisions — color relationships that actually work together, spacing rhythms that feel natural, typography scales that maintain hierarchy. This isn't about pixel-perfect copying; it's about understanding the *system* behind the visuals.

## Before You Start

1. **Confirm the target URL** — If the user hasn't provided one, ask for it before doing anything else.
2. **Check Playwright availability** — This skill depends on the Playwright MCP tools (`mcp__playwright__*`). If they're not available, inform the user and fall back to analyzing the site using your training knowledge, but clearly note that the results are approximations rather than live extractions.
3. **Clarify scope** — Does the user want the full system (tokens + components + guide), or just specific parts? Default to full extraction unless told otherwise.

## Overview

The process has three phases:
1. **Capture** — Visit the site, take screenshots, and extract raw CSS/DOM data
2. **Analyze** — Identify patterns, deduplicate values, and organize into a coherent system
3. **Generate** — Produce design tokens, component documentation, and usage guides

## Phase 1: Capture

### Screenshot Capture

Use the Playwright MCP tools to visit the target URL and capture the overall visual design.

1. `mcp__playwright__browser_navigate` — Navigate to the URL. If the page takes long to load (SPA with heavy JS), use `mcp__playwright__browser_wait_for` to wait for key elements before proceeding.
2. `mcp__playwright__browser_take_screenshot` — Take a full-page screenshot to understand the overall layout and visual hierarchy.
3. Take viewport-sized screenshots of key sections (hero, navigation, content areas, footer) by scrolling or using element-targeted screenshots.
4. If the site has distinct pages (about, pricing, etc.), navigate to 2-3 additional pages for broader coverage.

The screenshots give you the *feeling* of the design — the gestalt that raw CSS values can't capture. Look at them carefully before diving into the data.

### DOM/CSS Extraction

Use `mcp__playwright__browser_evaluate` to run JavaScript on the page and extract concrete values. This is where precision matters.

Run the token extraction script from `scripts/extract-tokens.js` on the page. This script collects colors, fonts, font sizes, spacing, border radii, shadows, transitions, z-indices, and CSS custom properties from `:root`.

Then run the component extraction script from `scripts/extract-components.js` to gather styling data for buttons, cards, inputs, navigation, and headings.

### Additional Data Points

Also check for:
- **Favicon / brand assets**: Look at `<link rel="icon">` and OpenGraph meta tags for brand colors
- **Media queries**: Check for breakpoint patterns in stylesheets
- **Icon system**: Are they using SVG inline, icon fonts (Font Awesome, Material Icons), or image sprites?

### Handling Common Issues

- **SPA / slow-loading sites**: Use `mcp__playwright__browser_wait_for` with a selector for the main content container before extracting. Some sites render content dynamically — wait for at least the hero section to appear.
- **Login-required sites**: If a login wall blocks access, inform the user and ask for credentials or an alternative public URL. Do not attempt to bypass authentication.
- **CORS-blocked stylesheets**: The extraction script already has try/catch for this. When external stylesheets are blocked, note which ones couldn't be read and rely more heavily on computed styles (which are always available).
- **Cookie consent banners**: Dismiss them via `mcp__playwright__browser_click` if possible, as they can obscure screenshots and affect layout measurements.

## Phase 2: Analyze

Now you have raw data and visual context. Time to find the system. Use `mcp__playwright__browser_evaluate` to run analysis scripts directly in the browser, or process the extracted data yourself.

### Color Analysis

1. **Convert all colors to a common format** — Use HSL for grouping. Run a script via `browser_evaluate` to convert all extracted RGB/RGBA values to HSL:
   ```javascript
   // Convert rgb(r, g, b) strings to {h, s, l} objects for clustering
   ```
2. **Cluster similar colors** — Colors within 5% lightness and 10 hue degrees of each other are likely the same semantic color. Group them and pick the most frequently used value as the representative.
3. **Identify roles**:
   - **Primary**: The dominant brand color (usually on CTAs and key UI elements)
   - **Secondary**: Supporting brand color
   - **Neutral/Gray**: The grayscale palette used for text, borders, backgrounds
   - **Success/Warning/Error/Info**: Semantic colors (look for greens, yellows, reds, blues in context)
   - **Background**: Page and section backgrounds
   - **Surface**: Card and container backgrounds
4. **Build a scale** for each color family (50-900 steps). Generate intermediate steps by adjusting lightness in HSL space if the site only uses a few shades.

Refer to the screenshots to validate — does the primary color you identified actually *feel* like the dominant brand color?

### Typography Analysis

1. **Font families**: Usually 1-2 families (heading + body). Note the font stack. Check which fonts are loaded via `document.fonts` API.
2. **Type scale**: Map the extracted font sizes into a coherent scale. Look for a ratio (1.2 minor third, 1.25 major third, 1.333 perfect fourth, etc.). Discard outlier sizes that appear only once.
3. **Font weights**: Typically 400 (regular), 500 (medium), 600 (semibold), 700 (bold)
4. **Line heights**: Usually 1.2-1.4 for headings, 1.5-1.75 for body text
5. **Letter spacing**: Note any tracking adjustments, especially on headings or uppercase text

### Spacing Analysis

1. **Find the base unit** — Most design systems use a 4px or 8px base. Look at the most frequently occurring spacing values for the pattern.
2. **Build a scale**: Map extracted values to a consistent set (4, 8, 12, 16, 20, 24, 32, 40, 48, 64, 80, 96, etc.). Round nearby values to the nearest scale step.
3. **Identify patterns**: Section padding, card padding, element gaps — these reveal the grid and rhythm.

### Component Pattern Analysis

From the extracted component data and screenshots:

1. **Buttons**: Variants (primary, secondary, ghost, outline), sizes, states
2. **Cards**: Structure, elevation (shadow), padding, border treatment
3. **Navigation**: Layout pattern, active state indicators, responsive behavior
4. **Form elements**: Input styles, labels, validation states
5. **Layout**: Grid system, max-width, responsive breakpoints
6. **Icons**: Style (outlined, filled, rounded), size scale, color usage
7. **Animations**: Transition durations, easing functions, common patterns

## Phase 3: Generate

Create the following output files in the user's project:

### 1. Design Tokens (`design-tokens/tokens.css`)

```css
:root {
  /* Color Tokens */
  --color-primary-50: ...;
  --color-primary-100: ...;
  /* ... full scale ... */

  /* Semantic Tokens */
  --color-bg-primary: var(--color-neutral-50);
  --color-text-primary: var(--color-neutral-900);
  /* ... */

  /* Typography */
  --font-family-heading: ...;
  --font-family-body: ...;
  --font-size-xs: ...;
  /* ... full scale ... */

  /* Spacing */
  --space-1: 4px;
  --space-2: 8px;
  /* ... */

  /* Border Radius */
  --radius-sm: ...;
  --radius-md: ...;
  --radius-lg: ...;
  --radius-full: 9999px;

  /* Shadows */
  --shadow-sm: ...;
  --shadow-md: ...;
  --shadow-lg: ...;

  /* Transitions */
  --transition-fast: ...;
  --transition-normal: ...;
  --transition-slow: ...;

  /* Z-Index */
  --z-dropdown: ...;
  --z-sticky: ...;
  --z-modal: ...;
  --z-toast: ...;

  /* Breakpoints (as reference, not usable in CSS vars) */
  /* sm: 640px, md: 768px, lg: 1024px, xl: 1280px */
}
```

### 2. Design Tokens JSON (`design-tokens/tokens.json`)

A machine-readable version following the [Design Tokens Format](https://design-tokens.github.io/community-group/format/) structure:

```json
{
  "color": {
    "primary": {
      "50": { "$value": "#...", "$type": "color" },
      ...
    }
  },
  "typography": { ... },
  "spacing": { ... }
}
```

### 3. Component Reference (`design-system/components.md`)

For each identified component, document:
- Visual appearance (describe with reference to tokens)
- HTML structure pattern
- CSS using the design tokens
- Variants and states
- Usage guidelines

### 4. Design System Guide (`design-system/guide.md`)

A comprehensive document covering:

```markdown
# [Site Name] Design System

## Brand Overview
Brief description of the visual language and design philosophy.

## Color System
Color palette with swatches, usage guidelines, accessibility notes (contrast ratios).

## Typography
Type scale, font families, usage hierarchy.

## Spacing & Layout
Spacing scale, grid system, responsive breakpoints.

## Components
Overview with links to detailed component docs.

## Iconography
Icon style, sizes, usage.

## Motion & Animation
Transition patterns, easing functions.

## Do's and Don'ts
Key design principles observed from the site.
```

## Important Considerations

### Accessibility
- Calculate and report contrast ratios for text/background combinations
- Flag any combinations that fail WCAG AA (4.5:1 for normal text, 3:1 for large text)
- Note the site's apparent accessibility patterns (focus styles, aria usage)

### Responsive Design
- Document observed breakpoints
- Note how components adapt across screen sizes (if you visited the site at multiple viewport widths)

### Naming Conventions
- Use semantic names over visual names (e.g., `--color-primary` not `--color-blue`)
- Follow existing conventions if the site's CSS custom properties reveal a naming scheme
- Keep names framework-agnostic where possible

### What NOT to do
- Don't copy proprietary assets (logos, icons, images) — describe the style instead
- Don't assume frameworks — output vanilla CSS tokens that work anywhere
- Don't over-extract — if there are 47 slightly different grays, consolidate to a rational scale
- Don't skip the screenshot analysis — raw CSS values without visual context lead to disconnected design systems

## Workflow Summary

1. Confirm the target URL with the user (if not already provided)
2. Check Playwright MCP availability; fall back gracefully if unavailable
3. Navigate to the site with `mcp__playwright__browser_navigate`, capture screenshots with `mcp__playwright__browser_take_screenshot`
4. Extract DOM/CSS data via `mcp__playwright__browser_evaluate` using the bundled scripts
5. Analyze and cluster the raw data into a coherent system
6. Generate all output files (tokens.css, tokens.json, components.md, guide.md)
7. Present a summary to the user with key findings and any notable design decisions
8. Ask if they want adjustments (e.g., different naming, additional pages to analyze, specific components to focus on)
