# Noah Hub UI Style Guide (for Agents)

## 1) Core principles
- Build UI with **Tailwind utility classes** and the existing **`ui/*` primitives** (Radix/shadcn-style components) instead of creating bespoke styling.
- Use the project’s **design tokens** (`bg-background`, `text-foreground`, `border-border`, `ring-ring`, `bg-primary`, etc.) so both **light** and **dark** modes look correct.
- Keep compositions consistent: headings, spacing, cards, tables, dialogs, tooltips, and form controls should “feel like” the existing screens.

## 2) Styling system (Tailwind + tokens)
### 2.1 Use the global theme tokens
The app’s color/spacing theme is defined in `app/app/globals.css` using CSS variables and then mapped to Tailwind colors (e.g. `bg-background`, `text-primary-foreground`, `border-border`, `ring-ring`). Example tokens:
```12:46:app/app/globals.css
:root {
  --background: oklch(0.97 0.01 95);
  --foreground: oklch(0.25 0 0);
  --primary: oklch(0.45 0.18 275);
  --border: oklch(0.92 0 0);
  --ring: oklch(0.55 0.2 275);
  --radius: 0.5rem;
}
```

**Rule:** Prefer semantic classes over raw colors:
- Background/text: `bg-background`, `text-foreground`, `bg-card`, `text-card-foreground`
- Accents: `bg-primary`, `text-primary-foreground`, `bg-accent`, `text-accent-foreground`
- Surfaces/muted: `bg-muted`, `text-muted-foreground`
- Borders/rings: `border-border`, `outline-ring/50`, focus rings are usually handled by primitives

### 2.2 Dark mode
Dark mode is driven by the `.dark` variant and mapped tokens.
**Rule:** Don’t hard-code light-only colors. Use `dark:*` where needed, but most styling should come from tokens already.

## 3) Typography
### 3.1 Fonts
- Body font is Merriweather; `p`, `button`, `a` use Merriweather Sans by default in `globals.css`:
```126:133:app/app/globals.css
body {
  @apply bg-background text-foreground;
  font-family: var(--font-merriweather);
}

p, button, a {
  font-family: var(--font-merriweather-sans);
}
```

**Rule:** For normal text, don’t change fonts manually—use the existing defaults or follow patterns used in primitives/pages.

### 3.2 MDX content
If you render markdown/MDX, prefer the existing MDX editor styles (the `.mdx-editor` section in `globals.css`) to ensure consistent headings/links/lists.

## 4) Layout & spacing
### 4.1 Page containers
Screens commonly use Tailwind container patterns like:
- `container mx-auto px-4 md:px-6`
- vertical rhythm with `space-y-*` / horizontal with `gap-*`

A good example is the header:
```83:85:app/app/components/nav.tsx
<header className="sticky top-0 z-40 w-full border-b bg-white dark:bg-background">
  <div className="container mx-auto px-4 md:px-6 flex h-16 items-center justify-between">
```

**Rule:** Use `px-4 md:px-6`-style paddings and `space-y-4` section stacking to match the UI’s density.

### 4.2 Cards as the “default section”
Use `Card` and its subcomponents; the primitive sets the consistent surface:
```5:15:app/app/components/ui/card.tsx
className={cn(
  "bg-card text-card-foreground flex flex-col gap-6 rounded-xl border py-6 shadow-sm",
  className
)}
```

## 5) Use existing UI primitives (required)
Import from the existing `ui/*` components (these already encode the visual language and interaction states).

### 5.1 Buttons
Use `Button` variants/sizes instead of recreating button styles:
```7:35:app/app/components/ui/button.tsx
variants: {
  variant: {
    default: "bg-primary text-primary-foreground ...",
    destructive: "bg-destructive ...",
    outline: "border bg-background ...",
    secondary: "bg-secondary text-secondary-foreground ...",
    ghost: "hover:bg-accent hover:text-accent-foreground ...",
    link: "text-primary underline-offset-4 hover:underline",
  },
  size: {
    default: "h-9 px-4 py-2 ...",
    sm: "h-8 rounded-md ...",
    lg: "h-10 rounded-md ...",
    icon: "size-9",
  },
}
```

**Rule:** For icon-only actions, prefer `size="icon"` and always set an `aria-label`.

### 5.2 Inputs / labels / textareas
Use:
- `Input`
- `Textarea`
- `Label`

Don’t re-style borders/rings manually—primitives already include consistent focus ring behavior.

### 5.3 Selects
Use `Select`, `SelectTrigger`, `SelectContent`, `SelectItem`. Keep trigger height/spacing consistent by not overriding core layout too aggressively.

### 5.4 Badges, Alerts, Tables
- `Badge` for status tags.
- `Alert` with `AlertTitle` + `AlertDescription`.
- `Table` wrappers + `TableHead/TableRow/TableCell` etc. for consistent row hover/borders.

### 5.5 Dialogs, Tooltips, Scroll areas, Separators
Prefer:
- `Dialog` (with default overlay/content styling)
- `Tooltip` (`TooltipContent` uses `bg-muted text-foreground` by default)
- `ScrollArea` for internal scrolling sections
- `Separator` for section dividers

Example tooltip base styling:
```49:56:app/app/components/ui/tooltip.tsx
className={cn(
  "bg-muted text-foreground shadow-lg ... rounded-md px-3 py-1.5 text-xs ..."
)}
```

## 6) ClassName conventions
### 6.1 Use `cn()` for conditional classes
Compose className strings with `cn`:
- `cn` is defined in `app/app/lib/utils.tsx` via `clsx` + `tailwind-merge`.

**Rule:** Don’t concatenate long conditional ternaries without `cn`—it prevents conflicting Tailwind classes.

### 6.2 Prefer semantic tokens over utility re-invention
Good:
- `text-muted-foreground`, `bg-card`, `border-border`, `hover:bg-accent`
Avoid (unless matching an existing outlier file exactly):
- hard-coded `#rrggbb`
- `border-gray-200`-style one-offs (unless you’re using an existing component that already does)

## 7) Interaction states & accessibility
- Focus rings should come from primitives (don’t remove them).
- Hover/focus should use the token-driven classes from components (e.g. `focus-visible:ring-ring/50`, `hover:bg-accent` patterns already exist).
- Icon buttons must have `aria-label`.
- When using tooltips for long labels, keep tooltip content readable and max width constrained (use patterns like `max-w-md` where the codebase does so).

## 8) “Do / Don’t” checklist
**Do**
- Use `ui/*` primitives for: buttons, inputs, selects, cards, tables, dialogs, tooltips, alerts, badges.
- Use token classes (`bg-background`, `text-foreground`, `border-border`, `ring-ring`, `bg-primary`, etc.).
- Use layout spacing patterns (`container mx-auto px-4 md:px-6`, `space-y-4`, `gap-4`, `rounded-xl`).

**Don’t**
- Don’t invent new color palettes/styles for standard controls.
- Don’t bypass primitives to mimic their look with custom CSS.
- Don’t forget dark mode—avoid light-only backgrounds/text.

## 9) Quick examples (copy the pattern)
### 9.1 Card section with header content
```tsx
<Card>
  <CardHeader>
    <CardTitle>Title</CardTitle>
    <CardDescription>Short supporting text.</CardDescription>
  </CardHeader>
  <CardContent>
    {/* content */}
  </CardContent>
</Card>
```

### 9.2 Form row layout
```tsx
<div className="flex flex-col gap-1">
  <label className="text-sm font-medium">Field label</label>
  <Input placeholder="Type here..." />
</div>
```

### 9.3 Table
```tsx
<Table>
  <TableHeader>
    <TableRow>
      <TableHead>Column</TableHead>
      <TableHead className="w-[120px]">Actions</TableHead>
    </TableRow>
  </TableHeader>
  <TableBody>
    <TableRow>
      <TableCell>Value</TableCell>
      <TableCell>
        <Button variant="ghost" size="sm">Action</Button>
      </TableCell>
    </TableRow>
  </TableBody>
</Table>
```

---

If you want, tell me which “main surface” you care about most (dash pages, onboarding, tables-heavy screens, or forms), and I can tailor this guide with more concrete layout examples from those specific areas of the `@app/` UI.