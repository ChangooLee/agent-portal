# AI Agent Portal UI Style Guide

> **Version**: 1.0 (2025-12-24)
> **Theme**: Black & White Modern Minimalist

---

## 1. Typography

### Font Family

All UI text uses Apple System Font stack. No external fonts are loaded for optimal performance.

```css
font-family: -apple-system, BlinkMacSystemFont, 'Apple SD Gothic Neo', 'SF Pro Display', system-ui, sans-serif;
```

### Font Weight

**Regular (400) only.** Bold text is globally disabled across the entire UI.

```css
/* Global override in tailwind.css */
.font-bold, .font-semibold, .font-extrabold, .font-black, .font-medium {
  font-weight: 400 !important;
}

h1, h2, h3, h4, h5, h6, strong, b {
  font-weight: 400 !important;
}
```

### Font Sizes

| Element | Size | Usage |
|---------|------|-------|
| H1 | 2rem (32px) | Page titles |
| H2 | 1.5rem (24px) | Section headers |
| H3 | 1.25rem (20px) | Subsection headers |
| Body | 1rem (16px) | Default text |
| Small | 0.875rem (14px) | Labels, captions |
| XSmall | 0.75rem (12px) | Badges, metadata |

---

## 2. Color Palette

### Primary Colors

| Color | Hex | Usage |
|-------|-----|-------|
| Black | `#000000` | Backgrounds, text |
| White | `#FFFFFF` | Text, backgrounds |
| Gray 950 | `#0a0a0f` | Primary dark background |
| Gray 900 | `#0d1117` | Secondary dark background |
| Gray 800 | `#1f2937` | Borders, dividers |
| Gray 400 | `#9CA3AF` | Secondary text |
| Gray 200 | `#E5E7EB` | Light borders |

### Accent Colors

| Color | Hex | Usage |
|-------|-----|-------|
| Indigo 500 | `#6366f1` | Primary accent, buttons |
| Blue 600 | `#2563eb` | Links, hover states |

---

## 3. Component Patterns

### Navigation Bar

- Background: `bg-gray-950`
- Border: `border-gray-800/50`
- Logo: Text only (no favicon), uppercase, letter-spacing: 0.15em

```svelte
<span class="text-sm tracking-[0.15em] uppercase text-white">
  AI AGENT PORTAL
</span>
```

### Buttons

- Primary: `bg-white text-black hover:bg-gray-100`
- Secondary: `bg-transparent border border-gray-800 text-gray-300 hover:border-gray-600`
- No bold text, font-weight: 400

### Cards

- Background: `bg-gray-900/50` or `bg-gray-800/60`
- Border: `border border-gray-800` or `border-gray-700/50`
- Rounded: `rounded-xl` or `rounded-2xl`

### Inputs

- Background: `bg-transparent` or `bg-gray-800`
- Border: `border border-gray-800`
- Focus: `focus:ring-1 focus:ring-gray-600`
- Placeholder: `placeholder-gray-600`

---

## 4. Login & Splash Screens

### Login Screen

- Full black background (`#000000`)
- Centered form layout
- Minimal styling with white text
- No hero section, no animated gradients

### Splash Screen

- Black background (`#000000`)
- Simple white text logo: "AI Agent Portal"
- Subtitle: "Enterprise Agentic AI Platform"
- No progress bar, no animations

---

## 5. Dark Mode

The UI is designed primarily for dark mode. Light mode styles are available but dark mode is the default.

```css
.dark {
  --text-primary: #F9FAFB;
  --text-secondary: #E5E7EB;
  --bg-primary: #0f172a;
  --bg-secondary: #1e293b;
  --border-color: #374151;
}
```

---

## 6. Design Principles

1. **Minimalism**: Clean, uncluttered interfaces with ample whitespace
2. **Contrast**: High contrast between text and background for readability
3. **Consistency**: Uniform styling across all pages and components
4. **Performance**: System fonts only, no external font loading
5. **Accessibility**: Sufficient color contrast, focus states for keyboard navigation

---

## 7. Implementation Files

| File | Purpose |
|------|---------|
| `webui/tailwind.config.js` | Font family, color definitions |
| `webui/src/tailwind.css` | Global overrides, CSS variables |
| `webui/src/app.css` | Base styles |
| `webui/src/app.html` | Splash screen |
| `webui/src/routes/auth/+page.svelte` | Login screen |
| `webui/src/lib/components/layout/TopNavbar.svelte` | Navigation bar |

---

**Last Updated**: 2025-12-24

