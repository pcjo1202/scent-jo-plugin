(() => {
  const result = { colors: new Set(), fonts: new Set(), fontSizes: new Set(), spacing: new Set(), borderRadii: new Set(), shadows: new Set(), transitions: new Set(), zIndices: new Set() };

  const allElements = document.querySelectorAll('*');

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
