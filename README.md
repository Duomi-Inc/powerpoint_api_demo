# PowerPoint Generation API Guide

This guide provides comprehensive documentation for using the PowerPoint Generation API to create presentations programmatically.

## Table of Contents

- [Overview](#overview)
- [Authentication](#authentication)
- [Template Management](#template-management)
- [Presentation Generation](#presentation-generation)
  - [Single Slide Generation](#single-slide-generation)
  - [Deck Generation (Multiple Slides)](#deck-generation-multiple-slides)
- [Slide Data Schema](#slide-data-schema)
  - [Basic Structure](#basic-structure)
  - [Content Blocks](#content-blocks)
  - [Tables](#tables)
  - [Logo Cells](#logo-cells)
  - [Text Formatting](#text-formatting)
- [Generation Options](#generation-options)
- [Error Handling](#error-handling)
- [Complete Examples](#complete-examples)
- [Template Styling Inheritance](#template-styling-inheritance)
- [Best Practices](#best-practices)

---

## Overview

The PowerPoint Generation API allows you to:

1. **Upload and manage templates** - Upload PowerPoint templates (.pptx) and analyze them for available placeholders
2. **Generate single slides** - Create a slide from a template slide with your data
3. **Generate full decks** - Create complete presentations with multiple slides asynchronously

All operations are scoped to an organization for multi-tenancy.

---

## Authentication

All API requests require the `X-API-Key` header for authentication:

```
X-API-Key: your-api-key
```

The API key determines which organization you belong to. All operations are automatically scoped to your organization based on the API key.

**Note:** The `org_name` field in request bodies is optional. If provided, it must match your API key's organization (otherwise you'll receive a 403 error). If omitted, the API automatically uses your API key's organization.

---

## Template Management

Before generating presentations, you need to upload and analyze templates.

### Upload a Template

**Step 1: Initiate Upload**

```http
POST /api/v1/templates
Content-Type: application/json
X-API-Key: your-api-key

{
  "filename": "quarterly-report.pptx",
  "file_size": 1048576,
  "metadata": {
    "category": "reports",
    "tags": ["quarterly", "financial"],
    "description": "Quarterly report template"
  }
}
```

**Response:**
```json
{
  "template_id": "tmpl_abc123",
  "upload_url": "https://storage.example.com/signed-url...",
  "expires_in": 3600,
  "status": "pending",
  "upload_method": "signed_url",
  "max_file_size": 10485760,
  "allowed_extensions": [".pptx"]
}
```

**Step 2: Upload file to the signed URL**

Upload your .pptx file directly to the provided `upload_url`.

**Step 3: Confirm Upload**

```http
POST /api/v1/templates/{template_id}/upload/confirm
X-API-Key: your-api-key
```

### Analyze Template

After upload, analyze the template to discover available slides and placeholders:

```http
POST /api/v1/templates/{template_id}/analysis
X-API-Key: your-api-key
Content-Type: application/json

{
  "options": {
    "parse_master_template_layout": true,
    "parse_slides": true,
    "include_placeholder_positions": true,
    "include_table_details": true
  }
}
```

**Response (202 Accepted):**
```json
{
  "analysis_id": "ana_xyz789",
  "status": "processing",
  "started_at": "2024-01-15T10:30:00Z"
}
```

### Get Analysis Results

```http
GET /api/v1/templates/{template_id}/analysis
X-API-Key: your-api-key
```

The response includes discovered slides with their `slide_id` values, which you'll use for generation.

---

## Presentation Generation

### Single Slide Generation

Generate a single slide synchronously. Useful for quick previews or individual slides.

```http
POST /api/v1/presentations/generate
X-API-Key: your-api-key
Content-Type: application/json

{
  "template_slide_id": "slide_abc123",
  "slide_data": {
    "title": "Q4 Revenue Summary",
    "subtitle": "Financial Performance Overview"
  },
  "options": {
    "auto_paginate_tables": true
  }
}
```

**Response:**
```json
{
  "presentation_id": "pres_def456",
  "status": "completed",
  "template_slide_id": "slide_abc123",
  "pages_generated": 1,
  "file_size": 245760,
  "download_url": "https://storage.example.com/download...",
  "download_url_expires_in": 3600,
  "created_at": "2024-01-15T10:35:00Z"
}
```

### Deck Generation (Multiple Slides)

Generate a complete presentation with multiple slides asynchronously.

**Step 1: Start Generation**

```http
POST /api/v1/presentations/generate-deck
X-API-Key: your-api-key
Content-Type: application/json

{
  "slides": [
    {
      "template_slide_id": "slide_title",
      "slide_data": {
        "title": "Q4 2024 Report",
        "subtitle": "Company Performance Review"
      }
    },
    {
      "template_slide_id": "slide_content",
      "slide_data": {
        "title": "Key Highlights",
        "content": {
          "blocks": [
            {
              "type": "text",
              "text": {
                "header": "Achievements",
                "bullets": [
                  "Revenue increased 25% YoY",
                  "Customer base grew to 10,000+",
                  "Launched 3 new products"
                ]
              }
            }
          ]
        }
      }
    },
    {
      "template_slide_id": "slide_table",
      "slide_data": {
        "title": "Regional Performance",
        "content": {
          "blocks": [
            {
              "type": "table",
              "table": {
                "table": {
                  "rows": [
                    {"is_header": true, "cells": [{"value": "Region"}, {"value": "Revenue"}, {"value": "Growth"}]},
                    {"cells": [{"value": "North"}, {"value": "$2.5M"}, {"value": "+15%"}]},
                    {"cells": [{"value": "South"}, {"value": "$1.8M"}, {"value": "+22%"}]},
                    {"cells": [{"value": "East"}, {"value": "$3.1M"}, {"value": "+18%"}]},
                    {"cells": [{"value": "West"}, {"value": "$2.9M"}, {"value": "+12%"}]}
                  ]
                }
              }
            }
          ]
        }
      },
      "options": {
        "auto_paginate_tables": true,
        "table_min_font_size": 8
      }
    }
  ],
  "options": {
    "auto_paginate_tables": true,
    "allow_textbox_reposition": false
  }
}
```

**Response (202 Accepted):**
```json
{
  "generation_id": "gen_ghi789",
  "status": "pending",
  "message": "Generation started. Poll status URL for progress.",
  "status_url": "https://api.example.com/api/v1/presentations/gen_ghi789/status",
  "created_at": "2024-01-15T10:40:00Z"
}
```

**Step 2: Poll for Status**

```http
GET /api/v1/presentations/{generation_id}/status
X-API-Key: your-api-key
```

**Response (In Progress):**
```json
{
  "generation_id": "gen_ghi789",
  "status": "processing",
  "progress": 45,
  "current_step": "Generating slide 2 of 3",
  "message": null,
  "total_slides_requested": 3,
  "total_pages_generated": 1,
  "slide_results": null,
  "created_at": "2024-01-15T10:40:00Z",
  "started_at": "2024-01-15T10:40:01Z"
}
```

**Response (Completed):**
```json
{
  "generation_id": "gen_ghi789",
  "status": "completed",
  "progress": 100,
  "current_step": null,
  "message": "Generated 4 pages from 3/3 slides",
  "total_slides_requested": 3,
  "total_pages_generated": 4,
  "slide_results": [
    {"slide_index": 0, "template_slide_id": "slide_title", "pages_generated": 1, "status": "completed"},
    {"slide_index": 1, "template_slide_id": "slide_content", "pages_generated": 1, "status": "completed"},
    {"slide_index": 2, "template_slide_id": "slide_table", "pages_generated": 2, "status": "completed"}
  ],
  "file_size": 512000,
  "download_url": "https://storage.example.com/download...",
  "download_url_expires_in": 3600,
  "created_at": "2024-01-15T10:40:00Z",
  "started_at": "2024-01-15T10:40:01Z",
  "completed_at": "2024-01-15T10:40:15Z"
}
```

### Generation Status Values

| Status | Description |
|--------|-------------|
| `pending` | Generation request queued |
| `processing` | Generation in progress |
| `completed` | All slides generated successfully |
| `partial` | Some slides generated, some failed |
| `failed` | Generation failed completely |

### Download Generated Presentation

```http
GET /api/v1/presentations/{generation_id}/download
X-API-Key: your-api-key
```

Returns the .pptx file as a binary stream.

---

## Slide Data Schema

### Basic Structure

The `slide_data` object supports these top-level fields:

```json
{
  "title": "Slide Title",
  "subtitle": "Slide Subtitle",
  "header": "Header text",
  "footer": "Footer text",
  "content": { ... },
  "slide_format": { ... }
}
```

| Field | Type | Description |
|-------|------|-------------|
| `title` | string | Main slide title |
| `subtitle` | string | Subtitle (for title slides or falls back to body) |
| `header` | string | Header area text |
| `footer` | string | Footer area text |
| `content` | Column or Column[] | Main content area |
| `slide_format` | SlideFormat | Text formatting options |

### Content Blocks

Content is organized in columns, each containing blocks:

```json
{
  "content": {
    "blocks": [
      {"type": "text", "text": { ... }},
      {"type": "table", "table": { ... }}
    ]
  }
}
```

For multi-column layouts:

```json
{
  "content": [
    {
      "header": "Column 1",
      "blocks": [{"type": "text", "text": {"bullets": ["Point 1"]}}]
    },
    {
      "header": "Column 2",
      "blocks": [{"type": "text", "text": {"bullets": ["Point 2"]}}]
    }
  ]
}
```

### Block Types

#### Text Block

Text blocks support headers, paragraphs, and bullet points:

```json
{
  "type": "text",
  "text": {
    "header": "Section Header",
    "text": "Main paragraph text",
    "bullets": [
      "First bullet point",
      "Second bullet point",
      "Third bullet point"
    ],
    "header_format": {"font_size": 14, "bold": true},
    "text_format": {"font_size": 12},
    "bullets_format": {"font_size": 11}
  }
}
```

All fields are optional - use any combination:

```json
// Just bullets
{"type": "text", "text": {"bullets": ["Point 1", "Point 2"]}}

// Header + bullets
{"type": "text", "text": {"header": "Key Points", "bullets": ["Point 1"]}}

// Text followed by bullets
{"type": "text", "text": {"text": "Summary:", "bullets": ["Item 1", "Item 2"]}}
```

#### Table Block

Tables support headers, formatting, and conditional styling:

```json
{
  "type": "table",
  "table": {
    "table": {
      "rows": [
        {
          "is_header": true,
          "cells": [
            {"value": "Product"},
            {"value": "Q1"},
            {"value": "Q2"},
            {"value": "Q3"},
            {"value": "Q4"}
          ]
        },
        {
          "cells": [
            {"value": "Widget A"},
            {"value": "$100K"},
            {"value": "$120K"},
            {"value": "$115K"},
            {"value": "$140K"}
          ]
        },
        {
          "cells": [
            {"value": "Widget B"},
            {"value": "$80K"},
            {"value": "$95K"},
            {"value": "$110K"},
            {"value": "$125K"}
          ]
        }
      ],
      "table_format": {
        "header_row": {
          "text": {"bold": true, "color": "#FFFFFF"},
          "cell": {"background_color": "#4472C4"}
        },
        "default": {
          "text": {"font_size": 11}
        }
      },
      "column_configs": [
        {"column_index": 0, "is_header": true}
      ]
    },
    "caption": "Quarterly Revenue by Product"
  }
}
```

### Tables

#### Cell Values

Cells can contain simple text or structured paragraphs:

```json
// Simple text
{"value": "Hello World"}

// Multiple paragraphs with bullets
{
  "value": [
    {"text": "Main point", "is_bullet": false},
    {"text": ["Sub-item 1", "Sub-item 2"], "is_bullet": true, "depth": 1}
  ]
}
```

#### Table Format

Apply formatting to different parts of the table:

```json
{
  "table_format": {
    "default": {
      "text": {"font_name": "Arial", "font_size": 10}
    },
    "header_row": {
      "text": {"bold": true, "font_size": 12, "color": "#FFFFFF"},
      "cell": {"background_color": "#2E75B6"}
    },
    "header_column": {
      "text": {"bold": true},
      "cell": {"background_color": "#D6DCE5"}
    },
    "header_intersection": {
      "text": {"bold": true, "color": "#FFFFFF"},
      "cell": {"background_color": "#1F4E79"}
    }
  }
}
```

#### Conditional Formatting

Apply styles based on cell values:

```json
{
  "format_templates": {
    "performance": {
      "rules": [
        {
          "condition": {"field": "value", "operator": "less_than", "value": 50},
          "cell": {"background_color": "#FF6B6B"}
        },
        {
          "condition": {"field": "value", "operator": "greater_than_or_equal", "value": 80},
          "cell": {"background_color": "#51CF66"}
        }
      ]
    }
  },
  "rows": [
    {"cells": [{"value": "Score: 45", "format_template": "performance"}]}
  ]
}
```

**Available Operators:**
- `equals`, `not_equals`
- `contains`, `not_contains`
- `greater_than`, `less_than`
- `greater_than_or_equal`, `less_than_or_equal`

#### Column Configuration

Configure column-level settings:

```json
{
  "column_configs": [
    {
      "column_index": 0,
      "type": "body",
      "is_header": true,
      "format_template": "custom_style"
    },
    {
      "column_index": 3,
      "type": "highlight",
      "background_color": "#FFF3CD"
    }
  ]
}
```

### Logo Cells

Table cells can display company logos automatically fetched from domain names. This is useful for creating expert networks, customer lists, or partner directories with visual branding.

#### Basic Usage

Set `is_logo: true` on a cell and provide a domain name as the value:

```json
{
  "cells": [
    {"value": "stripe.com", "is_logo": true},
    {"value": "John Smith"},
    {"value": "Partner"}
  ]
}
```

The API will automatically fetch the company logo from the domain and display it in the cell.

#### Logo Cell Properties

| Property | Type | Description |
|----------|------|-------------|
| `value` | string | Domain name (e.g., "stripe.com", "github.com") |
| `is_logo` | boolean | Set to `true` to fetch and display logo |

#### Text Fallback

For anonymized entries or when you don't want to show a logo, set `is_logo: false`:

```json
{
  "cells": [
    {"value": "Big Tech #1", "is_logo": false},
    {"value": "Anonymous Expert"},
    {"value": "Partner"}
  ]
}
```

#### Complete Logo Table Example

```json
{
  "type": "table",
  "table": {
    "table": {
      "table_format": {
        "default": {"text": {"font_size": 11}},
        "header_row": {"text": {"bold": true, "font_size": 12}}
      },
      "format_templates": {
        "expert_name": {"text": {"bold": true}},
        "expert_title": {"text": {"italic": false}}
      },
      "rows": [
        {
          "is_header": true,
          "cells": [
            {"value": "Company"},
            {"value": "Expert"},
            {"value": "Relevancy"}
          ]
        },
        {
          "cells": [
            {"value": "stripe.com", "is_logo": true},
            {
              "value": [
                {"text": "Sarah Chen", "format_template": "expert_name"},
                {"text": "VP of Revenue Operations", "format_template": "expert_title"}
              ]
            },
            {"value": "Partner"}
          ]
        },
        {
          "cells": [
            {"value": "github.com", "is_logo": true},
            {
              "value": [
                {"text": "Michael Rodriguez", "format_template": "expert_name"},
                {"text": "Director of Sales", "format_template": "expert_title"}
              ]
            },
            {"value": "Partner + Advertiser"}
          ]
        },
        {
          "cells": [
            {"value": "Enterprise Tech #1", "is_logo": false},
            {
              "value": [
                {"text": "David Kim", "format_template": "expert_name"},
                {"text": "Senior Manager", "format_template": "expert_title"}
              ]
            },
            {"value": "Partner"}
          ]
        }
      ]
    }
  }
}
```

#### Supported Domains

The logo fetcher supports most company domains. The domain should be:
- A valid domain name (e.g., "stripe.com", "notion.so")
- Without protocol prefix (no "https://")
- The company's primary domain for best logo resolution

### Text Formatting

#### TextFormat Object

```json
{
  "font_name": "Arial",
  "font_size": 12,
  "bold": true,
  "italic": false,
  "color": "#333333",
  "alignment": "left",
  "line_spacing": 1.2
}
```

| Property | Type | Description |
|----------|------|-------------|
| `font_name` | string | Font family (e.g., "Arial", "Calibri") |
| `font_size` | integer | Size in points |
| `bold` | boolean | Bold text |
| `italic` | boolean | Italic text |
| `color` | string | Hex color code (e.g., "#000000") |
| `alignment` | string | "left", "center", "right" |
| `line_spacing` | float | Line spacing multiplier |

#### Slide-Level Formatting

Apply consistent formatting across the slide:

```json
{
  "slide_format": {
    "title": {"font_name": "Arial", "font_size": 28, "bold": true},
    "subtitle": {"font_size": 18, "italic": true},
    "body": {"font_size": 14},
    "textbox": {
      "header": {"font_size": 12, "bold": true},
      "text": {"font_size": 10},
      "bullets": {"font_size": 10}
    }
  }
}
```

---

## Generation Options

Options control how slides are generated:

```json
{
  "options": {
    "auto_paginate_tables": true,
    "allow_textbox_reposition": false,
    "table_min_font_size": 9,
    "textbox_min_font_size": 8,
    "show_slide_numbers": true,
    "footer_text": "Confidential",
    "footer_font_size": 8,
    "footer_font_name": "Arial"
  }
}
```

| Option | Type | Default | Description |
|--------|------|---------|-------------|
| `auto_paginate_tables` | boolean | `true` | Automatically split large tables across multiple slides. **Note:** Only supported for table-only content. For slides with both table and textbox content, use `false`. |
| `allow_textbox_reposition` | boolean | `false` | Allow textboxes below tables to move down for more table space |
| `table_min_font_size` | integer | 9 | Minimum font size for table content (6-72) |
| `textbox_min_font_size` | integer | 8 | Minimum font size for textbox content (6-72) |
| `show_slide_numbers` | boolean | `false` | Display slide page numbers on generated slides |
| `footer_text` | string | `null` | Footer text to display on all slides |
| `footer_font_size` | integer | 8 | Font size for footer text |
| `footer_font_name` | string | `null` | Font name for footer (inherits from template if not specified) |

**Important:** When a slide contains both a table and text content (e.g., a textbox with bullets), you must set `auto_paginate_tables: false`. The system will then use single-page optimization to fit both elements on one slide by adjusting font sizes as needed.

### Per-Slide Options

Override deck-level options for specific slides:

```json
{
  "slides": [
    {
      "template_slide_id": "slide_123",
      "slide_data": { ... },
      "options": {
        "auto_paginate_tables": false,
        "table_min_font_size": 7
      }
    }
  ],
  "options": {
    "auto_paginate_tables": true
  }
}
```

---

## Error Handling

### Error Response Format

```json
{
  "detail": "Error message describing what went wrong"
}
```

### Common HTTP Status Codes

| Code | Description |
|------|-------------|
| 200 | Success |
| 202 | Accepted (async operation started) |
| 400 | Bad Request - Invalid input data |
| 403 | Forbidden - Template doesn't belong to your organization |
| 404 | Not Found - Resource doesn't exist |
| 500 | Internal Server Error |

### Generation Errors

When generation fails, the status response includes error details:

```json
{
  "status": "failed",
  "error": {
    "code": "GENERATION_FAILED",
    "message": "Template slide 'slide_xyz' not found"
  }
}
```

### Partial Success

Some slides may succeed while others fail:

```json
{
  "status": "partial",
  "message": "Generated 2 pages from 2/3 slides",
  "slide_results": [
    {"slide_index": 0, "status": "completed", "pages_generated": 1},
    {"slide_index": 1, "status": "completed", "pages_generated": 1},
    {"slide_index": 2, "status": "failed", "error": "Slide index out of range"}
  ]
}
```

---

## Complete Examples

### Example 1: Title Slide

```json
{
  "template_slide_id": "slide_title",
  "slide_data": {
    "title": "Annual Strategy Review",
    "subtitle": "Fiscal Year 2024",
    "slide_format": {
      "title": {"font_size": 36, "bold": true},
      "subtitle": {"font_size": 20, "italic": true}
    }
  }
}
```

### Example 2: Bullet Points Slide

```json
{
  "template_slide_id": "slide_content",
  "slide_data": {
    "title": "Strategic Priorities",
    "content": {
      "blocks": [
        {
          "type": "text",
          "text": {
            "header": "Focus Areas for 2024",
            "bullets": [
              "Expand market presence in APAC region",
              "Launch next-generation product line",
              "Achieve 40% improvement in operational efficiency",
              "Strengthen customer success program"
            ],
            "header_format": {"bold": true, "font_size": 14},
            "bullets_format": {"font_size": 12}
          }
        }
      ]
    }
  }
}
```

### Example 3: Two-Column Comparison

```json
{
  "template_slide_id": "slide_two_column",
  "slide_data": {
    "title": "Before vs After Implementation",
    "content": [
      {
        "header": "Before",
        "blocks": [
          {
            "type": "text",
            "text": {
              "bullets": [
                "Manual data entry",
                "3-day processing time",
                "15% error rate",
                "Limited visibility"
              ]
            }
          }
        ]
      },
      {
        "header": "After",
        "blocks": [
          {
            "type": "text",
            "text": {
              "bullets": [
                "Automated workflows",
                "Real-time processing",
                "0.1% error rate",
                "Full transparency"
              ]
            }
          }
        ]
      }
    ]
  }
}
```

### Example 4: Data Table with Formatting

```json
{
  "template_slide_id": "slide_table",
  "slide_data": {
    "title": "Quarterly Performance Metrics",
    "content": {
      "blocks": [
        {
          "type": "table",
          "table": {
            "table": {
              "table_format": {
                "header_row": {
                  "text": {"bold": true, "font_size": 11, "color": "#FFFFFF"},
                  "cell": {"background_color": "#2E75B6"}
                },
                "header_column": {
                  "text": {"bold": true},
                  "cell": {"background_color": "#D6DCE5"}
                },
                "default": {
                  "text": {"font_size": 10, "font_name": "Arial"}
                }
              },
              "rows": [
                {
                  "is_header": true,
                  "cells": [
                    {"value": "Metric"},
                    {"value": "Q1"},
                    {"value": "Q2"},
                    {"value": "Q3"},
                    {"value": "Q4"},
                    {"value": "YoY Change"}
                  ]
                },
                {
                  "cells": [
                    {"value": "Revenue ($M)"},
                    {"value": "12.5"},
                    {"value": "14.2"},
                    {"value": "13.8"},
                    {"value": "16.1"},
                    {"value": "+18%"}
                  ]
                },
                {
                  "cells": [
                    {"value": "Customers"},
                    {"value": "1,250"},
                    {"value": "1,480"},
                    {"value": "1,620"},
                    {"value": "1,890"},
                    {"value": "+32%"}
                  ]
                },
                {
                  "cells": [
                    {"value": "NPS Score"},
                    {"value": "72"},
                    {"value": "75"},
                    {"value": "78"},
                    {"value": "82"},
                    {"value": "+10 pts"}
                  ]
                }
              ],
              "column_configs": [
                {"column_index": 0, "is_header": true}
              ]
            }
          }
        }
      ]
    }
  },
  "options": {
    "auto_paginate_tables": true,
    "table_min_font_size": 9
  }
}
```

### Example 5: Logo Page (Expert Network)

```json
{
  "template_slide_id": "slide_table",
  "slide_data": {
    "title": "Expert Network: Customer Insights",
    "content": {
      "blocks": [
        {
          "type": "table",
          "table": {
            "table": {
              "table_format": {
                "default": {"text": {"font_size": 11}},
                "header_row": {"text": {"bold": true, "font_size": 12}}
              },
              "format_templates": {
                "expert_name": {"text": {"bold": true}},
                "expert_title": {"text": {"italic": false}}
              },
              "rows": [
                {
                  "is_header": true,
                  "cells": [
                    {"value": "Company"},
                    {"value": "Expert"},
                    {"value": "Relevancy"}
                  ]
                },
                {
                  "cells": [
                    {"value": "stripe.com", "is_logo": true},
                    {
                      "value": [
                        {"text": "Sarah Chen", "format_template": "expert_name"},
                        {"text": "VP of Revenue Operations", "format_template": "expert_title"}
                      ]
                    },
                    {"value": "Partner"}
                  ]
                },
                {
                  "cells": [
                    {"value": "github.com", "is_logo": true},
                    {
                      "value": [
                        {"text": "Michael Rodriguez", "format_template": "expert_name"},
                        {"text": "Director of Sales Enablement", "format_template": "expert_title"}
                      ]
                    },
                    {"value": "Partner + Advertiser"}
                  ]
                },
                {
                  "cells": [
                    {"value": "notion.so", "is_logo": true},
                    {
                      "value": [
                        {"text": "Emily Watson", "format_template": "expert_name"},
                        {"text": "Head of GTM Strategy", "format_template": "expert_title"}
                      ]
                    },
                    {"value": "Partner"}
                  ]
                },
                {
                  "cells": [
                    {"value": "Big Tech #1", "is_logo": false},
                    {
                      "value": [
                        {"text": "David Kim", "format_template": "expert_name"},
                        {"text": "Senior Manager, Sales Ops", "format_template": "expert_title"}
                      ]
                    },
                    {"value": "Partner + Advertiser"}
                  ]
                }
              ]
            }
          }
        }
      ]
    }
  },
  "options": {
    "auto_paginate_tables": true,
    "table_min_font_size": 11
  }
}
```

### Example 6: Complete Deck Generation

```json
{
  "slides": [
    {
      "template_slide_id": "slide_title",
      "slide_data": {
        "title": "Q4 2024 Business Review",
        "subtitle": "Executive Summary"
      }
    },
    {
      "template_slide_id": "slide_agenda",
      "slide_data": {
        "title": "Agenda",
        "content": {
          "blocks": [
            {
              "type": "text",
              "text": {
                "bullets": [
                  "Financial Performance",
                  "Customer Growth",
                  "Product Updates",
                  "2025 Outlook"
                ]
              }
            }
          ]
        }
      }
    },
    {
      "template_slide_id": "slide_kpi",
      "slide_data": {
        "title": "Key Performance Indicators",
        "content": {
          "blocks": [
            {
              "type": "table",
              "table": {
                "table": {
                  "rows": [
                    {"is_header": true, "cells": [{"value": "KPI"}, {"value": "Target"}, {"value": "Actual"}, {"value": "Status"}]},
                    {"cells": [{"value": "Revenue"}, {"value": "$50M"}, {"value": "$56.6M"}, {"value": "Exceeded"}]},
                    {"cells": [{"value": "Gross Margin"}, {"value": "70%"}, {"value": "72%"}, {"value": "Exceeded"}]},
                    {"cells": [{"value": "Customer Count"}, {"value": "2,000"}, {"value": "1,890"}, {"value": "On Track"}]},
                    {"cells": [{"value": "NPS"}, {"value": "75"}, {"value": "82"}, {"value": "Exceeded"}]}
                  ]
                }
              }
            }
          ]
        }
      }
    },
    {
      "template_slide_id": "slide_content",
      "slide_data": {
        "title": "2025 Strategic Priorities",
        "content": {
          "blocks": [
            {
              "type": "text",
              "text": {
                "header": "Growth Initiatives",
                "bullets": [
                  "Expand enterprise sales team by 50%",
                  "Launch in 3 new international markets",
                  "Release next-gen platform (v3.0)"
                ]
              }
            },
            {
              "type": "text",
              "text": {
                "header": "Operational Excellence",
                "bullets": [
                  "Achieve SOC 2 Type II certification",
                  "Reduce customer onboarding time by 40%",
                  "Implement AI-powered support automation"
                ]
              }
            }
          ]
        }
      }
    }
  ],
  "options": {
    "auto_paginate_tables": true,
    "allow_textbox_reposition": false,
    "table_min_font_size": 9
  }
}
```

---

## Template Styling Inheritance

The API supports **automatic styling inheritance** from your PowerPoint template. When you omit font properties in your JSON data, the generated slides will inherit styling (font name, font size, colors, etc.) directly from the template's placeholder formatting.

### How It Works

When generating slides:
1. **Explicit styles in JSON take precedence** - If you specify `font_name`, `font_size`, etc., those values are used
2. **Omitted styles inherit from template** - If you don't specify a style property, the template's placeholder formatting is preserved

### Benefits

- **Brand consistency** - Use your corporate templates and maintain their styling without re-specifying fonts in every API call
- **Simplified JSON payloads** - Only include the data and structural formatting (bold, colors, conditional rules)
- **Easy template switching** - Change templates without modifying your data payloads

### Example: With vs Without Font Specifications

**With explicit fonts (overrides template):**
```json
{
  "table_format": {
    "default": {
      "text": {
        "font_name": "Arial",
        "font_size": 11
      }
    },
    "header_row": {
      "text": {
        "font_name": "Arial",
        "bold": true,
        "font_size": 12
      }
    }
  }
}
```

**Without fonts (inherits from template):**
```json
{
  "table_format": {
    "header_row": {
      "text": {
        "bold": true
      }
    }
  }
}
```

In the second example, `font_name` and `font_size` are inherited from whatever is defined in the PowerPoint template's table placeholder.

### Demo Files

This demo includes the following files:

| File | Description |
|------|-------------|
| `demo_data_fake.json` | Sample deck with **logo pages** (inherits fonts from template) |
| `template_v3.pptx` | Template with 3 slide layouts (table, table+textbox, logo page) |

To run the demo:
1. Run `python demo_api.py` to execute the end-to-end demo
2. The generated deck will inherit fonts from the template and include logo pages

---

## Best Practices

1. **Analyze templates first** - Always analyze templates to discover available `slide_id` values before generating

2. **Use per-slide options wisely** - Override deck-level options only when specific slides need different behavior

3. **Handle table pagination** - When `auto_paginate_tables` is enabled, `pages_generated` may exceed 1 for data-heavy slides

4. **Poll efficiently** - When using deck generation, poll the status endpoint at reasonable intervals (e.g., every 2-5 seconds)

5. **Check partial success** - Always check `slide_results` to identify which slides succeeded or failed

6. **Use format templates** - Define reusable `format_templates` for consistent styling across tables

7. **Match content to templates** - Ensure your content structure matches what the template slide expects (title placeholders, body placeholders, table placeholders, etc.)

8. **Leverage template styling inheritance** - For brand consistency, omit font specifications in your JSON and let the template define the look and feel
