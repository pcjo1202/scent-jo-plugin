---
name: design-system-extractor
description: Extract and build a complete design system from any live website. Use this skill whenever the user provides a URL and wants to analyze its design, extract design tokens, build a component library reference, create a style guide, or replicate a site's look and feel. Also trigger when the user mentions "design system", "style guide", "design tokens", or "UI analysis" in connection with a specific website or URL. Even if the user just says "make something that looks like [site]" or "I like the design of [url]", this skill applies.
---

# Design System Extractor

You are building a comprehensive design system by analyzing a live website. The goal is to reverse-engineer the site's visual language into reusable tokens, component patterns, and documentation that a developer can immediately use to build interfaces with the same look and feel.

## Why this matters

Design systems are the backbone of consistent UI. Extracting one from a real site means you're capturing battle-tested design decisions — color relationships that actually work together, spacing rhythms that feel natural, typography scales that maintain hierarchy. This isn't about pixel-perfect copying; it's about understanding the *system* behind the visuals.

## Overview

The process has three phases:
1. **Capture** — Visit the site, take screenshots, and extract raw CSS/DOM data
2. **Analyze** — Identify patterns, deduplicate values, and organize into a coherent system
3. **Generate** — Produce design tokens, component documentation, and usage guides

## Phase 1: Capture

### Screenshot Capture

Use Playwright to visit the target URL and capture the overall visual design.

1. Navigate to the URL
2. Take a full-page screenshot to understand the overall layout and visual hierarchy
3. Take viewport-sized screenshots of key sections (hero, navigation, content areas, footer)
4. If the site has distinct pages (about, pricing, etc.), visit 2-3 additional pages for broader coverage

The screenshots give you the *feeling* of the design — the gestalt that raw CSS values can't capture. Look at them carefully before diving into the data.

### DOM/CSS Extraction

Use Playwright's `browser_evaluate` to run JavaScript on the page and extract concrete values. This is where precision matters.

Run the following extraction script on the page:

```javascript
(() => {
  const result = { colors: new Set(), fonts: new Set(), fontSizes: new Set(), spacing: new Set(), borderRadii: new Set(), shadows: new Set(), transitions: new Set(), zIndices: new Set() };

  const allElements = document.querySelectorAll('*');
  const computed = [];

  allElements.forEach(el => {
    const style = window.getComputedStyle(el);

    // Colors
    ['color', 'backgroundColor', 'borderColor', 'outlineColor'].forEach(prop => {
      const val = style[prop];
      if (val && val !== 'rgba(0, 0, 0, 0)' && val !== 'transparent') result.colors.add(val);
    });

    // Typography
    result.fonts.add(style.fontFamily);
    result.fontSizes.add(style.fontSize);

    // Spacing (margin, padding)
    ['marginTop', 'marginRight', 'marginBottom', 'marginLeft', 'paddingTop', 'paddingRight', 'paddingBottom', 'paddingLeft', 'gap'].forEach(prop => {
      const val = style[prop];
      if (val && val !== '0px') result.spacing.add(val);
    });

    // Border radius
    const br = style.borderRadius;
    if (br && br !== '0px') result.borderRadii.add(br);

    // Box shadow
    const shadow = style.boxShadow;
    if (shadow && shadow !== 'none') result.shadows.add(shadow);

    // Transitions
    const transition = style.transition;
    if (transition && transition !== 'all 0s ease 0s') result.transitions.add(transition);

    // z-index
    const z = style.zIndex;
    if (z !== 'auto') result.zIndices.add(z);
  });

  // Convert Sets to sorted Arrays
  const output = {};
  for (const [key, val] of Object.entries(result)) {
    output[key] = [...val].sort();
  }

  // Also grab CSS custom properties from :root
  const rootStyles = getComputedStyle(document.documentElement);
  const cssVars = {};
  for (const sheet of document.styleSheets) {
    try {
      for (const rule of sheet.cssRules) {
        if (rule.selectorText === ':root' || rule.selectorText === 'html') {
          for (const prop of rule.style) {
            if (prop.startsWith('--')) {
              cssVars[prop] = rootStyles.getPropertyValue(prop).trim();
            }
          }
        }
      }
    } catch(e) {} // CORS stylesheets will throw
  }
  output.cssCustomProperties = cssVars;

  return JSON.stringify(output, null, 2);
})()
```

Also extract component-level information:

```javascript
(() => {
  // Identify interactive elements and their states
  const buttons = [...document.querySelectorAll('button, [role="button"], a.btn, .button, input[type="submit"]')];
  const cards = [...document.querySelectorAll('[class*="card"], [class*="Card"]')];
  const inputs = [...document.querySelectorAll('input, textarea, select')];
  const navs = [...document.querySelectorAll('nav, [role="navigation"]')];

  const getStyles = (el) => {
    const s = window.getComputedStyle(el);
    return {
      tag: el.tagName.toLowerCase(),
      classes: el.className,
      padding: s.padding,
      margin: s.margin,
      fontSize: s.fontSize,
      fontWeight: s.fontWeight,
      lineHeight: s.lineHeight,
      color: s.color,
      backgroundColor: s.backgroundColor,
      borderRadius: s.borderRadius,
      border: s.border,
      boxShadow: s.boxShadow,
      display: s.display,
      gap: s.gap,
      width: s.width,
      height: s.height,
    };
  };

  return JSON.stringify({
    buttons: buttons.slice(0, 10).map(getStyles),
    cards: cards.slice(0, 5).map(getStyles),
    inputs: inputs.slice(0, 5).map(getStyles),
    navs: navs.slice(0, 3).map(getStyles),
    headings: [...document.querySelectorAll('h1,h2,h3,h4,h5,h6')].slice(0, 10).map(getStyles),
  }, null, 2);
})()
```

### Additional Data Points

Also check for:
- **Favicon / brand assets**: Look at `<link rel="icon">` and OpenGraph meta tags for brand colors
- **Media queries**: Check for breakpoint patterns in stylesheets
- **Icon system**: Are they using SVG inline, icon fonts (Font Awesome, Material Icons), or image sprites?

## Phase 2: Analyze

Now you have raw data and visual context. Time to find the system.

### Color Analysis

1. **Convert all colors to a common format** (HSL is best for grouping)
2. **Cluster similar colors** — Colors within 5% lightness and 10 hue degrees of each other are likely the same semantic color
3. **Identify roles**:
   - **Primary**: The dominant brand color (usually on CTAs and key UI elements)
   - **Secondary**: Supporting brand color
   - **Neutral/Gray**: The grayscale palette used for text, borders, backgrounds
   - **Success/Warning/Error/Info**: Semantic colors (look for greens, yellows, reds, blues in context)
   - **Background**: Page and section backgrounds
   - **Surface**: Card and container backgrounds
4. **Build a scale** for each color family (50-900 or similar steps)

Refer to the screenshots to validate — does the primary color you identified actually *feel* like the dominant brand color?

### Typography Analysis

1. **Font families**: Usually 1-2 families (heading + body). Note the font stack.
2. **Type scale**: Map the extracted font sizes into a coherent scale. Look for a ratio (1.2 minor third, 1.25 major third, 1.333 perfect fourth, etc.)
3. **Font weights**: Typically 400 (regular), 500 (medium), 600 (semibold), 700 (bold)
4. **Line heights**: Usually 1.2-1.4 for headings, 1.5-1.75 for body text
5. **Letter spacing**: Note any tracking adjustments, especially on headings or uppercase text

### Spacing Analysis

1. **Find the base unit** — Most design systems use a 4px or 8px base
2. **Build a scale**: Map extracted values to a consistent set (4, 8, 12, 16, 20, 24, 32, 40, 48, 64, 80, 96, etc.)
3. **Identify patterns**: Section padding, card padding, element gaps

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

1. Ask the user for the target URL (if not already provided)
2. Navigate to the site with Playwright, capture screenshots
3. Extract DOM/CSS data via browser_evaluate
4. Analyze and cluster the raw data into a coherent system
5. Generate all output files
6. Present a summary to the user with key findings and any notable design decisions
7. Ask if they want adjustments (e.g., different naming, additional pages to analyze, specific components to focus on)
