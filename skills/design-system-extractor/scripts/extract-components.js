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
