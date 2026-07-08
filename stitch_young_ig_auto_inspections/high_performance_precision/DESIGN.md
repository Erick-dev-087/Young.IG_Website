---
name: High-Performance Precision
colors:
  surface: '#131313'
  surface-dim: '#131313'
  surface-bright: '#393939'
  surface-container-lowest: '#0e0e0e'
  surface-container-low: '#1c1b1b'
  surface-container: '#201f1f'
  surface-container-high: '#2a2a2a'
  surface-container-highest: '#353534'
  on-surface: '#e5e2e1'
  on-surface-variant: '#ccc7aa'
  inverse-surface: '#e5e2e1'
  inverse-on-surface: '#313030'
  outline: '#969177'
  outline-variant: '#4a4731'
  surface-tint: '#d9c900'
  primary: '#ffffff'
  on-primary: '#363100'
  primary-container: '#f7e600'
  on-primary-container: '#6e6600'
  inverse-primary: '#686000'
  secondary: '#ffb4ab'
  on-secondary: '#690006'
  secondary-container: '#ce0217'
  on-secondary-container: '#ffdcd8'
  tertiary: '#ffffff'
  on-tertiary: '#303030'
  tertiary-container: '#e2e2e2'
  on-tertiary-container: '#646464'
  error: '#ffb4ab'
  on-error: '#690005'
  error-container: '#93000a'
  on-error-container: '#ffdad6'
  primary-fixed: '#f7e600'
  primary-fixed-dim: '#d9c900'
  on-primary-fixed: '#1f1c00'
  on-primary-fixed-variant: '#4e4800'
  secondary-fixed: '#ffdad6'
  secondary-fixed-dim: '#ffb4ab'
  on-secondary-fixed: '#410002'
  on-secondary-fixed-variant: '#93000d'
  tertiary-fixed: '#e2e2e2'
  tertiary-fixed-dim: '#c6c6c6'
  on-tertiary-fixed: '#1b1b1b'
  on-tertiary-fixed-variant: '#474747'
  background: '#131313'
  on-background: '#e5e2e1'
  surface-variant: '#353534'
typography:
  display-lg:
    fontFamily: Sora
    fontSize: 48px
    fontWeight: '800'
    lineHeight: 56px
    letterSpacing: -0.02em
  headline-lg:
    fontFamily: Sora
    fontSize: 32px
    fontWeight: '700'
    lineHeight: 40px
  headline-md:
    fontFamily: Sora
    fontSize: 24px
    fontWeight: '600'
    lineHeight: 32px
  body-lg:
    fontFamily: Inter
    fontSize: 18px
    fontWeight: '400'
    lineHeight: 28px
  body-md:
    fontFamily: Inter
    fontSize: 16px
    fontWeight: '400'
    lineHeight: 24px
  label-caps:
    fontFamily: JetBrains Mono
    fontSize: 12px
    fontWeight: '700'
    lineHeight: 16px
    letterSpacing: 0.1em
  data-point:
    fontFamily: JetBrains Mono
    fontSize: 14px
    fontWeight: '500'
    lineHeight: 20px
rounded:
  sm: 0.125rem
  DEFAULT: 0.25rem
  md: 0.375rem
  lg: 0.5rem
  xl: 0.75rem
  full: 9999px
spacing:
  base: 8px
  xs: 4px
  sm: 12px
  md: 24px
  lg: 48px
  xl: 80px
  gutter: 24px
  margin-mobile: 16px
  margin-desktop: 64px
---

## Brand & Style

This design system is built for an audience that values engineering excellence and absolute transparency. The brand personality is **technical, authoritative, and high-performance**, echoing the precision of modern automotive diagnostics. 

The aesthetic is a hybrid of **Corporate Modern** and **Tactile Industrial**. It utilizes deep obsidian surfaces contrasted with high-visibility safety colors to evoke the feeling of a premium car dashboard or a high-end garage diagnostic tool. The goal is to instill immediate trust through a "data-first" visual language, where information is presented with surgical clarity. The UI should feel like an extension of the vehicle's own instrumentation—responsive, durable, and highly functional.

## Colors

The palette is rooted in the high-contrast environment of automotive performance. 
- **Primary (Yellow):** Used for critical calls to action, active states, and highlights. It represents energy and high visibility.
- **Secondary (Red):** Reserved for alerts, stop-status, and branding accents. It provides a "rev-counter" intensity to the layout.
- **Background/Neutral:** A "Deep Obsidian" (`#121212`) base serves as the tarmac, providing a low-glare environment that makes the yellow and red elements pop without causing eye strain.
- **Functional Grays:** Used for secondary text and borders to maintain a sophisticated, technical feel rather than a pure black-and-white contrast.

## Typography

The typography strategy focuses on "legibility under speed." 
- **Sora** (Headlines) provides a wide, geometric stance that feels modern and industrial. Its bold weights are used for impact and brand presence.
- **Inter** (Body) offers a neutral, highly readable foundation for technical reports and long-form content.
- **JetBrains Mono** (Labels & Data) is introduced for technical specifications, VIN numbers, and sensor readings. The monospaced nature emphasizes the "solution" and "data-driven" aspect of the brand, mimicking diagnostic code and readout displays.

## Layout & Spacing

The layout utilizes a **12-column fluid grid** for desktop and a **4-column grid** for mobile. The spacing rhythm is strictly based on an 8px base unit to ensure a mathematical, engineered feel.

- **Desktop:** Large margins provide a "premium gallery" feel for car imagery. Content is often organized in modular dashboard-style widgets.
- **Mobile:** Margins tighten to 16px. Technical data should be stacked in clear, full-width rows to ensure ease of reading during on-site inspections.
- **Density:** The design maintains a "Medium-High" density, allowing for significant data visualization (gauges, charts, checklists) without feeling cluttered.

## Elevation & Depth

Hierarchy is established through **Tonal Layering** and **Subtle Inner Glows** rather than heavy drop shadows.

- **Level 0 (Background):** Pure Obsidian (`#121212`).
- **Level 1 (Cards/Containers):** Elevated Gray (`#1E1E1E`). These should have a very subtle 1px border (`#2A2A2A`) to define their edges against the dark background.
- **Depth:** Instead of traditional shadows, use "backlit" effects for active elements. An active card might have a very faint yellow outer glow (5% opacity) to suggest it is powered on.
- **Glassmorphism:** Use sparingly for navigation bars or overlays to maintain context of the car imagery behind the UI, with a heavy background blur (20px).

## Shapes

The shape language is **Technical and Precise**. 
- A "Soft" corner radius (4px) is the standard for cards and inputs, providing a machined look that avoids the "toy-like" feel of overly rounded corners.
- Buttons use the same 4px radius, but specific "Status Chips" may use a Pill-shape (3) to differentiate them from actionable elements.
- Icons should follow a linear, stroke-based style (2px weight) to match the technical typography.

## Components

- **Buttons:** Primary buttons are Solid Yellow with Black text. No gradients. Secondary buttons are outlined in Yellow or Red. The "hover" state should involve a subtle brightness increase rather than a color shift.
- **Input Fields:** Dark background with a bottom-border only or a very subtle ghost-border. When focused, the border turns Yellow. Labels use the `label-caps` typography style.
- **Status Chips:** Use high-contrast backgrounds (Red for 'Fail', Yellow for 'Warning', Green for 'Pass') with bold, all-caps monospaced text.
- **Data Gauges:** Radial or horizontal progress bars that mimic car instrument clusters are preferred for visualizing "Engine Health" or "Body Condition" scores.
- **Inspection Cards:** Large cards containing a hero image of the car part, a technical title, and a JetBrains Mono "ID Number" or "Timestamp" in the top right corner.
- **Checklists:** Use custom checkboxes that look like mechanical toggles or "LED" indicators (Green when checked, Dark Gray when off).