# LVGL UI Inspiration Notes

Source analyzed: `~/lvgl/examples` (`/home/sobik/lvgl/examples`)

## Coverage Snapshot

- `widgets`: 113 examples
- `styles`: 21 examples
- `layouts`: 12 examples
- `scroll`: 9 examples
- `others`: 30 examples
- `libs`: 32 examples

The best visual inspiration does not come only from the basic widget demos.
The strongest reusable UI ideas come from combining:

- `widgets/menu`
- `widgets/list`
- `widgets/win`
- `widgets/tabview`
- `widgets/tileview`
- `styles`
- `scroll`
- `layouts/flex`
- `layouts/grid`
- `others/file_explorer`
- `others/gridnav`

## High-Value UI Patterns

### 1. Sectioned settings and drill-down navigation

Examples:

- `~/lvgl/examples/widgets/menu/lv_example_menu_5.c`
- `~/lvgl/examples/widgets/dropdown/lv_example_dropdown_3.c`

Patterns to borrow:

- Root page with grouped sections instead of one flat list
- Icons plus labels for faster scanning
- Deep pages that reuse the same visual shell
- Inline controls like sliders and switches inside the same menu system
- Long labels that scroll instead of hard-clipping

How this maps to CalSci:

- Build settings and tools as grouped pages
- Use a narrow header and one main content region
- Keep one selected row visually strong
- Use a thin right-side scrollbar as a persistent depth cue

### 2. Selectable list rows with action rail

Examples:

- `~/lvgl/examples/widgets/list/lv_example_list_2.c`
- `~/lvgl/examples/scroll/lv_example_scroll_9.c`

Patterns to borrow:

- Checked state on a selected list item
- Secondary column or companion pane for actions
- Reordering and recentering the focused row
- Card-like panels with shadows and grouped controls

How this maps to CalSci:

- Use one strong active row
- Pair the main list with a smaller action strip or bottom status line
- Let left/right change focus zone while up/down scrolls rows

### 3. Framed windows, sheets, and overlays

Examples:

- `~/lvgl/examples/widgets/win/lv_example_win_1.c`
- `~/lvgl/examples/widgets/msgbox/lv_example_msgbox_3.c`
- `~/lvgl/examples/styles/lv_example_style_20.c`

Patterns to borrow:

- Title bar plus content region
- Scrollable content inside a framed shell
- Modal overlays with dim or blur treatment
- Clear separation between background context and foreground task

How this maps to CalSci:

- Use window framing for editors, viewers, and confirmations
- Dim the background for destructive actions or detail popups
- Prefer one centered sheet over full-screen replacement when context matters

### 4. Strong card composition

Examples:

- `~/lvgl/examples/styles/lv_example_style_12.c`
- `~/lvgl/examples/styles/lv_example_style_21.c`

Patterns to borrow:

- Rounded cards
- Shadowed layers
- Image/avatar plus text plus call-to-action
- Grid-based composition inside a compact tile
- Gradient CTA buttons

How this maps to CalSci:

- On monochrome displays, keep the card idea but replace color and shadow with:
  - bold borders
  - inverted selected states
  - spacing hierarchy
  - corner radius only where it reads clearly

### 5. Navigation as layout, not decoration

Examples:

- `~/lvgl/examples/widgets/tabview/lv_example_tabview_2.c`
- `~/lvgl/examples/widgets/tileview/lv_example_tileview_1.c`
- `~/lvgl/examples/others/gridnav/lv_example_gridnav_5.c`

Patterns to borrow:

- Left-rail tabs
- L-shaped tile navigation
- Direction-locked movement
- Multi-zone focus systems

How this maps to CalSci:

- Treat keypad navigation as first-class UI architecture
- Design screens with obvious directional affordances
- Build screen zones that map cleanly to up/down/left/right

### 6. Custom-drawn controls and expressive states

Examples:

- `~/lvgl/examples/widgets/keyboard/lv_example_keyboard_3.c`
- `~/lvgl/examples/widgets/buttonmatrix/lv_example_buttonmatrix_3.c`

Patterns to borrow:

- Per-button visual customization
- Strong active, pressed, and checked states
- Pagination controls
- Matrix layouts with intentionally grouped buttons

How this maps to CalSci:

- Good fit for keypad overlays, launchers, and compact command palettes
- Use button matrices for:
  - pagers
  - mode pickers
  - category selectors
  - shortcut dashboards

### 7. Data and utility screens

Examples:

- `~/lvgl/examples/widgets/chart/lv_example_chart_8.c`
- `~/lvgl/examples/widgets/calendar/lv_example_calendar_2.c`
- `~/lvgl/examples/others/file_explorer/lv_example_file_explorer_3.c`

Patterns to borrow:

- Data surfaces with minimal chrome
- Dense table/file-browser presentation
- Live-updating visualizations
- Header tools attached directly to content

How this maps to CalSci:

- Use for logs, measurements, app launchers, and storage views
- Prefer compact headers and high information density

### 8. Gradients, transforms, and motion accents

Examples:

- `~/lvgl/examples/grad/lv_example_grad_4.c`
- `~/lvgl/examples/anim/lv_example_anim_timeline_1.c`
- `~/lvgl/examples/styles/lv_example_style_21.c`

Patterns to borrow:

- Animated scale and rotation
- Gradient-backed surfaces
- Motion used to explain hierarchy or interaction

How this maps to CalSci:

- On small monochrome displays, motion matters more than color
- Favor:
  - slide-in pages
  - focus-follow scrolling
  - subtle selection growth
  - modal fade or dim transitions

## Design Direction To Reuse Going Forward

For future CalSci LVGL screens, the most promising combined recipe is:

1. `menu_5` structure
2. `list_2` selection treatment
3. `style_21` card composition
4. `tabview_2` or `tileview_1` for multi-zone navigation
5. `msgbox_3` and `style_20` for overlays
6. `gridnav_5` for keypad-friendly focus movement

## Best Fit For A 128x64 Or Similar Small Display

Keep:

- strong section headers
- one obvious selected row
- scroll position indicators
- narrow action rails
- page-based navigation
- compact cards
- modal confirmation layers

Avoid copying directly:

- heavy shadow usage
- desktop-sized padding
- multi-column data tables unless heavily simplified
- color-only affordances
- large decorative gradients

Adapt instead:

- use black/white inversion for selection
- use borders and spacing to replace shadow
- use icons sparingly and only when they improve scan speed
- use motion and focus rules to express structure

## Most Reusable Example Files

- `~/lvgl/examples/widgets/menu/lv_example_menu_5.c`
- `~/lvgl/examples/widgets/list/lv_example_list_2.c`
- `~/lvgl/examples/widgets/win/lv_example_win_1.c`
- `~/lvgl/examples/widgets/tabview/lv_example_tabview_2.c`
- `~/lvgl/examples/widgets/tileview/lv_example_tileview_1.c`
- `~/lvgl/examples/widgets/msgbox/lv_example_msgbox_3.c`
- `~/lvgl/examples/styles/lv_example_style_20.c`
- `~/lvgl/examples/styles/lv_example_style_21.c`
- `~/lvgl/examples/scroll/lv_example_scroll_9.c`
- `~/lvgl/examples/others/gridnav/lv_example_gridnav_5.c`

