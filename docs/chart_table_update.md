# PowerPoint API Update: Chart + Table Two-Column Layout

## What's New

You can now create slides with a **chart on one side and a table on the other** — perfect for presenting data visualizations alongside supporting details or customer feedback.

---

## Data Format

### Two-Column Layout

Two-column slides use `content` as an **array** (instead of an object):

```json
{
  "slide_data": {
    "title": "Your Slide Title",
    "content": [
      {
        "header": "Left Column Header",
        "blocks": [
          {"type": "chart", "chart": {...}}
        ]
      },
      {
        "header": "Right Column Header",
        "blocks": [
          {"type": "table", "table": {...}}
        ]
      }
    ]
  }
}
```

### Key Difference

| Layout | `content` format |
|--------|------------------|
| Single column | `"content": {"blocks": [...]}` |
| Two columns | `"content": [{"header": "...", "blocks": [...]}, {...}]` |

---

## Chart Block Structure

```json
{
  "type": "chart",
  "chart": {
    "chart_type": "stacked_column",
    "categories": ["Q1", "Q2", "Q3", "Q4"],
    "series": [
      {"name": "Enterprise", "values": [12.5, 14.2, 15.8, 18.1], "color": "#2E75B6"},
      {"name": "Mid-Market", "values": [8.3, 9.1, 10.2, 11.5], "color": "#70AD47"},
      {"name": "SMB", "values": [4.2, 4.8, 5.1, 5.9], "color": "#FFC000"}
    ],
    "show_bar_labels": true,
    "value_axis_unit": "$M",
    "legend": {"position": "bottom"}
  }
}
```

---

## Chart Options

| Property | Description |
|----------|-------------|
| `chart_type` | `clustered_column`, `stacked_column`, `percent_stacked_column`, `clustered_bar`, `stacked_bar`, `percent_stacked_bar` |
| `categories` | X-axis labels |
| `series` | Array of `{name, values, color}` - color is optional hex code (e.g., `"#2E75B6"`) |
| `show_bar_labels` | Show values on bars |
| `value_axis_unit` | Unit label displayed **above** the Y-axis (e.g., "$M", "000s"). **Note:** Skipped for percent stacked charts. |
| `legend` | `{"position": "bottom"}` - options: `bottom`, `left`, `right`, `top`, `top_right` |

---

## Template Requirements

Your template needs a **4th slide layout** with:
- Left placeholder for chart
- Right placeholder for table
- Optional column headers

---

## Quick Start

See `demo_data_fake.json` for complete working examples:
- **Slide 3** ("ZoomInfo Copilot") - `percent_stacked_column` with `legend.position`
- **Slide 4** ("Quarterly Revenue") - `stacked_column` with custom `color` and `value_axis_unit`
