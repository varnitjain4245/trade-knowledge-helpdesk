# Figma Design Engine — Strict Figma-Driven Frontend Implementation

This reference governs how the `trading-platform-coding` skill processes visual designs when building frontend user interfaces.

## 1. Core Principle — Figma is the Primary Source of Truth

When a Figma URL or design specification is provided in a task:
- **Figma is the primary authority**: `Figma > written prompt`. Written instructions supplement user intent, but visual layout, tokens, structure, and component styling are dictated by the Figma design.
- **Never invent design**: If Figma specifies a design, layout, color, font, or interaction, follow it strictly. Do not apply default or improvised styles when Figma specs are available.

## 2. Inaccessible or Missing Figma URL Protocol

If a task references UI work that requires a Figma design, but the Figma URL is missing, broken, or inaccessible:
1. **Pause before generating frontend code**: Clearly notify the user:
   > "A Figma design was requested or referenced for this UI implementation, but the URL is missing or inaccessible. Please provide a valid Figma URL or confirm if fallback design rules should be used."
2. **Do not guess the design**: Wait for user clarification or explicit fallback authorization before generating component markup or styles.

## 3. Design Token Extraction & Mapping

All design tokens extracted from Figma must be converted into structured, reusable code variables (e.g., CSS variables, Tailwind tokens, or theme constants). Never hardcode raw hex values or pixel numbers repeatedly in component files.

### Token Mapping Standards
- **Colors**: Convert Figma color styles (primary, surface, border, status badges, charts, dark/light modes) into semantic variables (e.g., `--color-bg-primary`, `--color-text-muted`, `--color-accent-buy`).
- **Typography**: Extract font families, font sizes, line heights, letter spacing, and font weights into design tokens (e.g., `--font-size-sm`, `--font-weight-semibold`, `--line-height-tight`).
- **Spacing & Layout**: Convert Figma auto-layout gaps, paddings, and margins into a consistent spacing scale (`--spacing-1`, `--spacing-2`, `--spacing-4`, `--spacing-6`).
- **Border Radius & Shadows**: Map corner radii and drop/inner shadow elevation levels into CSS tokens (`--radius-sm`, `--radius-md`, `--shadow-elevation-1`).
- **Breakpoints & Grid**: Extract responsive column grids and breakpoint thresholds (mobile, tablet, desktop, ultra-wide trading viewports).
- **Themes**: Support dark/light theme tokens directly if defined in Figma, using CSS variable toggles or theme providers.

## 4. Component & Variant Architecture

- **Reusable Components**: Map Figma main components and variants directly to modular UI components (e.g., React/Flutter components).
- **Zero Styling Duplication**: Share common styles via base design tokens and utility classes or styled primitives. Never copy-paste CSS rules across components.
- **Variants & States**: Ensure all component variants (default, hover, active, disabled, focus, loading, error, success) present in Figma are implemented with micro-animations where appropriate.
- **Icons & Assets**: Use the exact SVGs/icons specified in the Figma design system or SVGs extracted directly from design nodes.

## 5. Figma Compliance Checklist
Before declaring frontend UI work complete, verify:
- [ ] Colors match Figma tokens exactly (semantic variables used).
- [ ] Typography scale (font-family, size, weight, line-height) matches Figma text styles.
- [ ] Spacing, padding, and alignment match Figma auto-layout parameters.
- [ ] Border radius, borders, and shadow elevations match design specs.
- [ ] Component variants and interactive states (hover, focus, disabled) are fully represented.
- [ ] Responsive layout adapts correctly across target screen sizes.
- [ ] Light/Dark theme switching functions seamlessly if defined in design.
