/**
 * Scholia Design System - Warm Terracotta Theme
 *
 * See DESIGN_SYSTEM.md for full documentation.
 */
export const theme = {
  colors: {
    // Backgrounds
    bg: '#fdfaf8',              // Main page background - warm off-white
    bgCard: '#ffffff',          // Card/surface background
    bgWarm: '#f9f3ef',          // Warm tinted sections, footer CTAs

    // Text hierarchy
    text: '#3d2f2a',            // Primary text - warm dark brown
    textSecondary: '#6b574f',   // Secondary text, descriptions
    textMuted: '#a08a80',       // Tertiary text, labels, placeholders

    // Borders
    border: '#e8dfd9',          // Subtle warm gray borders

    // Accent - Terracotta
    accent: '#c45d3a',          // Primary accent - terracotta
    accentLight: '#fce9e2',     // Light accent for backgrounds, badges
    accentWarm: '#a64b2d',      // Darker accent for text on light backgrounds

    // Button states
    buttonHover: '#2d211c',     // Darker brown for hover states

    // Semantic colors
    error: '#c44b3a',           // Error state (terracotta-tinted red)
    success: '#5a8a5c',         // Success state (muted green)
    warning: '#c49a3a',         // Warning state (warm amber)

    // Legacy/functional (for app-specific UI)
    highlight: 'rgba(196, 93, 58, 0.15)',  // Selection highlight (terracotta tint)
    highlightText: '#a64b2d',
    pdfBackground: '#525659',   // PDF viewer background (stays neutral)

    // Aliases for backward compatibility
    primary: '#c45d3a',
    primaryHover: '#a64b2d',
    background: '#fdfaf8',
    surface: '#ffffff',
  },
  spacing: {
    xs: '0.25rem',    // 4px
    sm: '0.5rem',     // 8px
    md: '0.75rem',    // 12px
    lg: '1rem',       // 16px
    xl: '1.5rem',     // 24px
    xxl: '2rem',      // 32px
    section: '4rem',  // 64px - vertical section padding
  },
  typography: {
    // Font families
    serif: "Georgia, 'Times New Roman', serif",
    sans: "'Lora', Georgia, serif",
    // Legacy alias
    fontFamily: "'Lora', Georgia, serif",
    fontSize: {
      xs: '0.6875rem',  // 11px - labels
      sm: '0.8125rem',  // 13px - buttons, small text
      base: '0.875rem', // 14px - body small
      md: '1rem',       // 16px - body
      lg: '1.0625rem',  // 17px - subtitle
      xl: '1.125rem',   // 18px - h3
      '2xl': '1.875rem', // 30px - h2
      '3xl': '3rem',    // 48px - h1
    },
    lineHeight: {
      tight: '1.15',
      normal: '1.6',
      relaxed: '1.7',
    },
    letterSpacing: {
      tight: '-0.02em',
      wide: '0.08em',
    }
  },
  layout: {
    leftPanelWidth: '300px',
    maxContentWidth: '1000px',
    maxNarrowWidth: '800px',
  },
  borderRadius: {
    sm: '4px',
    md: '6px',
    lg: '8px',
  },
  shadows: {
    subtle: '0 1px 3px rgba(0,0,0,0.04)',
  },
  transitions: {
    fast: '0.15s',
  }
};

/**
 * CSS custom properties string for injecting into components
 */
export const cssVariables = `
  --bg: ${theme.colors.bg};
  --bg-card: ${theme.colors.bgCard};
  --bg-warm: ${theme.colors.bgWarm};
  --text: ${theme.colors.text};
  --text-secondary: ${theme.colors.textSecondary};
  --text-muted: ${theme.colors.textMuted};
  --border: ${theme.colors.border};
  --accent: ${theme.colors.accent};
  --accent-light: ${theme.colors.accentLight};
  --accent-warm: ${theme.colors.accentWarm};
  --serif: ${theme.typography.serif};
  --sans: ${theme.typography.sans};
`;

/**
 * Google Fonts import URL
 */
export const googleFontsUrl = "https://fonts.googleapis.com/css2?family=Lora:ital,wght@0,400;0,500;0,600;0,700;1,400&display=swap";
