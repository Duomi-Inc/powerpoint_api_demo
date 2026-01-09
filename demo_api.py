#!/usr/bin/env python3
"""
PowerPoint Generation API - Demo Script

This script demonstrates how to use the PowerPoint Generation API to:
1. Upload and analyze templates
2. Generate single slides
3. Generate full presentation decks with multiple slides
4. Leverage template styling inheritance (fonts inherited from template)
5. Create logo pages with automatic company logo fetching

Prerequisites:
    pip install requests

Files included in this demo folder:
    - demo_data_fake.json: Sample deck with logo pages (inherits fonts from template)
    - template_v3.pptx: PowerPoint template with 3 slide layouts
    - README.md: Complete API documentation

Usage:
    1. Set your API_KEY and BASE_URL below
    2. Run: python demo_api.py

Template Styling Inheritance:
    When you omit font_name/font_size in your JSON data, the API will inherit
    styling from the template's placeholders.

Logo Pages:
    Use "is_logo": true in table cells to automatically fetch company logos
    from domain names. See demo_logo_slide() for examples.
"""

import json
import os
import time
from typing import Optional

import requests

# ============================================================================
# CONFIGURATION - UPDATE THESE VALUES
# ============================================================================

# Your API key (obtain from your organization admin)
API_KEY = "replace_with_your_api_key"

# Production API base URL
BASE_URL = "https://powerpoint-api-gateway-36twek8d.uc.gateway.dev/api/v1"

# Request headers - API key is required for all authenticated requests
HEADERS = {
    "X-API-Key": API_KEY,
    "Content-Type": "application/json"
}


# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

def make_request(method: str, endpoint: str, json_data: dict = None, stream: bool = False):
    """
    Make an authenticated API request.

    All API calls require the X-API-Key header. The API key determines which
    organization you belong to - all resources are automatically scoped to
    your organization.

    Args:
        method: HTTP method (GET, POST, PUT, DELETE)
        endpoint: API endpoint path (e.g., '/templates')
        json_data: Optional JSON body for POST/PUT requests
        stream: If True, return response for streaming (used for file downloads)

    Returns:
        Response JSON or response object if streaming

    Raises:
        requests.HTTPError: If the request fails (4xx or 5xx status)
    """
    url = f"{BASE_URL}{endpoint}"

    response = requests.request(
        method=method,
        url=url,
        headers=HEADERS,
        json=json_data,
        stream=stream
    )

    # Raise exception for error status codes (4xx, 5xx)
    response.raise_for_status()

    if stream:
        return response
    return response.json()


def poll_until_complete(endpoint: str, check_interval: int = 3, max_attempts: int = 60):
    """
    Poll an async endpoint until the operation completes.

    Many API operations are asynchronous (template analysis, deck generation).
    This helper polls the status endpoint until completion.

    Args:
        endpoint: The status endpoint to poll (e.g., '/presentations/{id}/status')
        check_interval: Seconds between polls (default: 3)
        max_attempts: Maximum polling attempts (default: 60 = 3 minutes)

    Returns:
        Final status response with download URL on success

    Raises:
        TimeoutError: If operation doesn't complete within max_attempts
    """
    for attempt in range(max_attempts):
        status = make_request("GET", endpoint)

        # Terminal states: completed, partial, failed
        if status["status"] in ["completed", "partial", "failed"]:
            return status

        # Show progress while waiting
        progress = status.get("progress", 0)
        step = status.get("current_step", "Processing...")
        print(f"  [{progress}%] {step}")

        time.sleep(check_interval)

    raise TimeoutError(f"Operation did not complete after {max_attempts * check_interval}s")


# ============================================================================
# TEMPLATE MANAGEMENT
# ============================================================================

def upload_template(file_path: str, metadata: dict = None) -> dict:
    """
    Upload a PowerPoint template file (.pptx).

    Templates are the foundation for generation. Each template contains slides
    with placeholders (title, body, table, etc.) that get populated with your data.

    Upload is a 3-step process:
        1. Initiate upload - request a signed URL from the API
        2. Upload file - PUT the file directly to cloud storage
        3. Confirm upload - tell the API the upload is complete

    After upload, you must analyze the template to discover available slides.

    Args:
        file_path: Path to your .pptx template file
        metadata: Optional metadata dict with:
            - category: string (e.g., "reports", "sales")
            - tags: list of strings
            - description: string

    Returns:
        dict with template_id and upload details

    Example:
        >>> result = upload_template(
        ...     "my_template.pptx",
        ...     metadata={"category": "quarterly", "tags": ["finance"]}
        ... )
        >>> print(result["template_id"])
        'tmpl_abc123xyz'
    """
    filename = os.path.basename(file_path)
    file_size = os.path.getsize(file_path)

    print(f"Uploading template: {filename} ({file_size:,} bytes)")

    # Step 1: Initiate upload - get signed URL
    # The signed URL allows direct upload to cloud storage
    init_response = make_request("POST", "/templates", {
        "filename": filename,
        "file_size": file_size,
        "metadata": metadata or {}
    })

    template_id = init_response["template_id"]
    upload_url = init_response["upload_url"]
    print(f"  Template ID: {template_id}")

    # Step 2: Upload file to signed URL
    # This goes directly to cloud storage, not through the API
    print("  Uploading to storage...")
    with open(file_path, "rb") as f:
        upload_response = requests.put(
            upload_url,
            data=f,
            headers={
                "Content-Type": "application/vnd.openxmlformats-officedocument.presentationml.presentation"
            }
        )
        upload_response.raise_for_status()

    # Step 3: Confirm upload
    # This triggers the API to validate the file
    print("  Confirming upload...")
    make_request("POST", f"/templates/{template_id}/upload/confirm")

    print("  Upload complete!")
    return init_response


def analyze_template(template_id: str) -> dict:
    """
    Analyze a template to discover slides and placeholders.

    Analysis extracts:
        - Available slides with their slide_id values
        - Placeholder types and positions (title, body, table, etc.)
        - Table placeholder dimensions
        - Master slide layouts

    You MUST analyze a template before generating from it.
    The slide_id values from analysis are used in generation requests.

    This is an async operation - we start analysis and poll for results.

    Args:
        template_id: The template_id from upload_template()

    Returns:
        dict with slides array containing:
            - slide_id: ID to use in generation
            - name: Slide name
            - placeholders: List of placeholder info

    Example:
        >>> analysis = analyze_template("tmpl_abc123xyz")
        >>> for slide in analysis["slides"]:
        ...     print(f"{slide['slide_id']}: {slide['name']}")
        'slide_1': 'Title Slide'
        'slide_2': 'Content with Table'
    """
    print(f"Analyzing template: {template_id}")

    # Start analysis with all options enabled for full details
    analysis_options = {
        "options": {
            "parse_master_template_layout": True,   # Include master slide info
            "parse_slides": True,                   # Parse each slide
            "include_placeholder_positions": True,  # Include X/Y positions
            "include_table_details": True           # Include table dimensions
        }
    }

    # Initiate async analysis
    make_request("POST", f"/templates/{template_id}/analysis", analysis_options)

    # Poll until complete
    print("  Processing...")
    result = poll_until_complete(f"/templates/{template_id}/analysis")

    # Slides are in results.slides
    results = result.get("results", {})
    slides = results.get("slides", [])
    print(f"  Found {len(slides)} slide(s):")
    for slide in slides:
        slide_id = slide.get("slideId", "unknown")
        slide_num = slide.get("slideNumber", "?")
        print(f"    - {slide_id} (slide #{slide_num})")

    return result


def list_templates() -> list:
    """
    List all templates in your organization.

    Returns all uploaded templates with their metadata and analysis status.

    Returns:
        List of template dicts with id, filename, status, etc.

    Example:
        >>> templates = list_templates()
        >>> for t in templates:
        ...     print(f"{t['template_id']}: {t['filename']} ({t['status']})")
    """
    response = make_request("GET", "/templates")
    return response.get("templates", [])


# ============================================================================
# PRESENTATION GENERATION
# ============================================================================

def generate_single_slide(
    template_slide_id: str,
    slide_data: dict,
    options: dict = None,
    output_path: Optional[str] = None
) -> dict:
    """
    Generate a single slide synchronously.

    Use this for:
        - Quick previews during development
        - Testing slide data before full deck generation
        - Generating individual slides on-demand

    The response includes a download URL for the generated .pptx file.

    Args:
        template_slide_id: The slide_id from template analysis
        slide_data: Content to populate the slide with:
            - title: string
            - subtitle: string
            - content: dict with blocks array
            - slide_format: formatting options
        options: Generation options:
            - auto_paginate_tables: bool (split large tables across slides).
                Note: Only supported for table-only content. For slides with
                both table and textbox, use False for single-page optimization.
            - table_min_font_size: int (minimum font for table text)
            - allow_textbox_reposition: bool (let textboxes move for tables)
        output_path: Optional path to save the .pptx file

    Returns:
        dict with status, download_url, pages_generated, etc.

    Example:
        >>> result = generate_single_slide(
        ...     template_slide_id="slide_1",
        ...     slide_data={"title": "Hello World", "subtitle": "Demo"},
        ...     output_path="output.pptx"
        ... )
        >>> print(f"Generated {result['pages_generated']} page(s)")
    """
    print(f"Generating single slide from: {template_slide_id}")

    request_body = {
        "template_slide_id": template_slide_id,
        "slide_data": slide_data
    }

    if options:
        request_body["options"] = options

    result = make_request("POST", "/presentations/generate", request_body)

    pages = result.get("pages_generated", 1)
    print(f"  Generated {pages} page(s)")

    # Download the file if output path specified
    if output_path and result.get("download_url"):
        download_file(result["download_url"], output_path)

    return result


def generate_deck(
    slides: list,
    options: dict = None,
    output_path: Optional[str] = None
) -> dict:
    """
    Generate a full presentation deck with multiple slides.

    This is an ASYNC operation:
        1. Start generation - returns a generation_id immediately
        2. Poll status - check progress until complete
        3. Download - get the final .pptx file

    Large tables can automatically paginate across multiple slides when
    using table-only content. For slides with both table and textbox content,
    set auto_paginate_tables=False to use single-page optimization instead.
    Each slide can have its own options to override deck-level settings.

    Args:
        slides: List of slide specifications, each containing:
            - template_slide_id: Which template slide to use
            - slide_data: Content for the slide (title, content, etc.)
            - options: (optional) Per-slide generation options
        options: Deck-level generation options (apply to all slides unless overridden)
        output_path: Optional path to save the generated .pptx

    Returns:
        Final status dict with:
            - status: "completed", "partial", or "failed"
            - total_pages_generated: int
            - slide_results: array with per-slide status
            - download_url: URL to download the .pptx

    Example:
        >>> result = generate_deck(
        ...     slides=[
        ...         {"template_slide_id": "slide_1", "slide_data": {"title": "Title"}},
        ...         {"template_slide_id": "slide_2", "slide_data": {"title": "Data", "content": {...}}}
        ...     ],
        ...     options={"auto_paginate_tables": True},
        ...     output_path="my_deck.pptx"
        ... )
    """
    print(f"Generating deck with {len(slides)} slide(s)...")

    request_body = {"slides": slides}
    if options:
        request_body["options"] = options

    # Start async generation
    init_response = make_request("POST", "/presentations/generate-deck", request_body)
    generation_id = init_response["generation_id"]
    print(f"  Generation ID: {generation_id}")

    # Poll until complete
    result = poll_until_complete(f"/presentations/{generation_id}/status")

    # Print summary
    print(f"\nGeneration complete!")
    print(f"  Status: {result['status']}")
    print(f"  Total pages: {result['total_pages_generated']}")

    # Show per-slide results
    if result.get("slide_results"):
        print("  Slide results:")
        for sr in result["slide_results"]:
            icon = "OK" if sr["status"] == "completed" else "FAILED"
            print(f"    [{icon}] Slide {sr['slide_index']}: {sr['pages_generated']} page(s)")

    # Download if output path specified
    if output_path and result.get("download_url"):
        download_file(result["download_url"], output_path)

    return result


def download_file(url: str, output_path: str):
    """
    Download a file from a URL (or generation ID).

    The API provides signed download URLs that expire after a set time
    (typically 1 hour). Use this to save the generated .pptx file.

    Args:
        url: Download URL from generation response, or generation_id
        output_path: Local path to save the file
    """
    # If it looks like an ID instead of URL, use the download endpoint
    if not url.startswith("http"):
        response = make_request("GET", f"/presentations/{url}/download", stream=True)
    else:
        response = requests.get(url, stream=True)
        response.raise_for_status()

    with open(output_path, "wb") as f:
        for chunk in response.iter_content(chunk_size=8192):
            f.write(chunk)

    print(f"  Downloaded: {output_path}")


# ============================================================================
# DEMO FUNCTIONS
# ============================================================================

def demo_list_templates():
    """Demo: List all templates in your organization."""
    print("\n" + "=" * 60)
    print("DEMO: List Templates")
    print("=" * 60)

    templates = list_templates()

    if not templates:
        print("No templates found. Upload one first!")
        return

    print(f"Found {len(templates)} template(s):")
    for t in templates:
        status = t.get("status", "unknown")
        print(f"  {t['template_id']}: {t['filename']} [{status}]")


def demo_upload_and_analyze():
    """Demo: Upload the included template and analyze it."""
    print("\n" + "=" * 60)
    print("DEMO: Upload and Analyze Template")
    print("=" * 60)

    # Use the included example template
    template_path = os.path.join(os.path.dirname(__file__), "example_table_templates.pptx")

    if not os.path.exists(template_path):
        print(f"Template not found: {template_path}")
        return None

    # Upload
    upload_result = upload_template(
        template_path,
        metadata={
            "category": "demo",
            "tags": ["tables", "example"],
            "description": "Demo template with table layouts"
        }
    )

    template_id = upload_result["template_id"]

    # Analyze
    analysis = analyze_template(template_id)

    return template_id, analysis


def demo_generate_from_sample_data():
    """
    Demo: Generate a deck using the included demo_data_fake.json.

    This demonstrates:
        - Multi-slide generation
        - Table formatting with conditional styling
        - Text blocks with bullets
        - Logo pages with company logos
        - Per-slide options

    NOTE: You must first upload and analyze a template, then update
    the template_slide_id values in demo_data_fake.json to match your template's
    slide IDs. Or use run_end_to_end_demo() which handles this automatically.
    """
    print("\n" + "=" * 60)
    print("DEMO: Generate Deck from Sample Data")
    print("=" * 60)

    # Load the sample data
    data_path = os.path.join(os.path.dirname(__file__), "demo_data_fake.json")

    if not os.path.exists(data_path):
        print(f"Demo data not found: {data_path}")
        return None

    with open(data_path, "r") as f:
        deck_request = json.load(f)

    # Check if template_slide_id is provided (required for this standalone function)
    first_slide = deck_request["slides"][0]
    if "template_slide_id" not in first_slide or not first_slide["template_slide_id"]:
        print("\n  WARNING: demo_data_fake.json requires template_slide_id for each slide!")
        print("  Use run_end_to_end_demo() which handles this automatically")
        return None

    # Generate the deck
    result = generate_deck(
        slides=deck_request["slides"],
        options=deck_request.get("options"),
        output_path="demo_output.pptx"
    )

    return result


def demo_simple_slide():
    """
    Demo: Generate a simple single slide.

    This is a minimal example showing the basic slide data structure.
    Replace 'YOUR_SLIDE_ID' with an actual slide ID from your template.
    """
    print("\n" + "=" * 60)
    print("DEMO: Simple Single Slide")
    print("=" * 60)

    # Simple slide with title and bullets
    slide_data = {
        "title": "API Demo Slide",
        "content": {
            "blocks": [
                {
                    "type": "text",
                    "text": {
                        "header": "Key Features",
                        "bullets": [
                            "Easy template management",
                            "Flexible content formatting",
                            "Table auto-pagination",
                            "Conditional styling support"
                        ]
                    }
                }
            ]
        }
    }

    print("\nSlide data:")
    print(json.dumps(slide_data, indent=2))

    print("\nTo generate this slide, call:")
    print('  generate_single_slide("YOUR_SLIDE_ID", slide_data, output_path="simple.pptx")')


def demo_template_styling_inheritance():
    """
    Demo: Template Styling Inheritance.

    This demonstrates the API's ability to inherit styling from templates.
    When you omit font specifications (font_name, font_size) in your JSON data,
    the generated slides will use the fonts defined in the PowerPoint template.

    Benefits:
        - Brand consistency without specifying fonts in every API call
        - Simplified JSON payloads - only include data and structural formatting
        - Easy template switching without modifying data payloads

    Files used:
        - demo_data_fake.json: Data WITHOUT font specifications
        - template_v3.pptx: Template with custom styling
    """
    print("\n" + "=" * 60)
    print("DEMO: Template Styling Inheritance")
    print("=" * 60)
    print("\nThis demo shows how omitting font specifications in your JSON")
    print("allows the generated slides to inherit styling from the template.")

    # Show comparison
    print("\n--- WITH explicit fonts (overrides template) ---")
    print("""
{
  "table_format": {
    "default": {
      "text": {
        "font_name": "Arial",   // <-- Explicit font
        "font_size": 11
      }
    }
  }
}
""")

    print("--- WITHOUT fonts (inherits from template) ---")
    print("""
{
  "table_format": {
    "header_row": {
      "text": {
        "bold": true           // <-- Only structural formatting
      }
    }
  }
}
""")

    print("To generate with template styling inheritance:")
    print("  1. Upload template_v3.pptx")
    print("  2. Use demo_data_fake.json for slide data (no font specs)")
    print("  3. Fonts will match the template's placeholder formatting")
    print("\nRun: run_template_inheritance_demo()")


def demo_table_slide():
    """
    Demo: Generate a slide with a formatted table.

    This shows:
        - Table structure with headers
        - Table formatting (header row, default styles)
        - Conditional formatting with rules
        - Column configurations
    """
    print("\n" + "=" * 60)
    print("DEMO: Table Slide with Conditional Formatting")
    print("=" * 60)

    slide_data = {
        "title": "Q4 Performance by Region",
        "content": {
            "blocks": [
                {
                    "type": "table",
                    "table": {
                        "table": {
                            # Table formatting
                            "table_format": {
                                # Default style for all cells
                                "default": {
                                    "text": {"font_name": "Arial", "font_size": 10}
                                },
                                # Header row style (first row with is_header: true)
                                "header_row": {
                                    "text": {"bold": True, "color": "#FFFFFF"},
                                    "cell": {"background_color": "#2E75B6"}
                                },
                                # First column style
                                "header_column": {
                                    "text": {"bold": True}
                                }
                            },
                            # Conditional formatting templates
                            "format_templates": {
                                "growth_status": {
                                    "rules": [
                                        {
                                            "condition": {
                                                "field": "value",
                                                "operator": "contains",
                                                "value": "+"
                                            },
                                            "cell": {"background_color": "#C6EFCE"}  # Green
                                        },
                                        {
                                            "condition": {
                                                "field": "value",
                                                "operator": "contains",
                                                "value": "-"
                                            },
                                            "cell": {"background_color": "#FFC7CE"}  # Red
                                        }
                                    ]
                                }
                            },
                            # Apply format template to column 3 (Growth column)
                            "column_configs": [
                                {"column_index": 0, "is_header": True},
                                {"column_index": 3, "format_template": "growth_status"}
                            ],
                            # Table data
                            "rows": [
                                {
                                    "is_header": True,
                                    "cells": [
                                        {"value": "Region"},
                                        {"value": "Revenue"},
                                        {"value": "Target"},
                                        {"value": "Growth"}
                                    ]
                                },
                                {
                                    "cells": [
                                        {"value": "North America"},
                                        {"value": "$4.2M"},
                                        {"value": "$4.0M"},
                                        {"value": "+5%"}
                                    ]
                                },
                                {
                                    "cells": [
                                        {"value": "Europe"},
                                        {"value": "$2.8M"},
                                        {"value": "$3.0M"},
                                        {"value": "-7%"}
                                    ]
                                },
                                {
                                    "cells": [
                                        {"value": "Asia Pacific"},
                                        {"value": "$1.9M"},
                                        {"value": "$1.5M"},
                                        {"value": "+27%"}
                                    ]
                                }
                            ]
                        }
                    }
                }
            ]
        }
    }

    print("\nTable slide data structure:")
    print(json.dumps(slide_data, indent=2))

    print("\nTo generate this slide, call:")
    print('  generate_single_slide("YOUR_SLIDE_ID", slide_data, output_path="table.pptx")')


def demo_logo_slide():
    """
    Demo: Generate a slide with company logos.

    This shows the logo page feature:
        - Cells with "is_logo": true automatically fetch company logos
        - The value should be a domain name (e.g., "stripe.com", "github.com")
        - Logos are fetched and displayed in the table cell
        - Non-logo cells (is_logo: false or omitted) display text normally

    Logo cells support:
        - Domain-based logo fetching (e.g., "stripe.com")
        - Fallback to text if logo cannot be fetched
        - Automatic sizing within the cell
    """
    print("\n" + "=" * 60)
    print("DEMO: Logo Slide with Company Logos")
    print("=" * 60)

    slide_data = {
        "title": "Expert Network: Customer Insights",
        "content": {
            "blocks": [
                {
                    "type": "table",
                    "table": {
                        "table": {
                            "table_format": {
                                "default": {"text": {"font_size": 11}},
                                "header_row": {"text": {"bold": True, "font_size": 12}}
                            },
                            "format_templates": {
                                "expert_name": {"text": {"bold": True}},
                                "expert_title": {"text": {"bold": False, "italic": False}}
                            },
                            "rows": [
                                {
                                    "is_header": True,
                                    "cells": [
                                        {"value": "Company"},
                                        {"value": "Expert"},
                                        {"value": "Relevancy"}
                                    ]
                                },
                                {
                                    "cells": [
                                        # Logo cell - fetches logo from stripe.com
                                        {"value": "stripe.com", "is_logo": True},
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
                                        # Logo cell - fetches logo from github.com
                                        {"value": "github.com", "is_logo": True},
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
                                        # Non-logo cell - displays as text (for anonymized entries)
                                        {"value": "Big Tech #1", "is_logo": False},
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
    }

    print("\nLogo slide data structure:")
    print(json.dumps(slide_data, indent=2))

    print("\nKey points about logo cells:")
    print('  - Set "is_logo": true to fetch logo from domain')
    print('  - Value should be a domain name (e.g., "stripe.com")')
    print('  - Set "is_logo": false for text-only cells (anonymized)')
    print("\nTo generate this slide, call:")
    print('  generate_single_slide("YOUR_SLIDE_ID", slide_data, output_path="logos.pptx")')


def demo_footer_and_slide_numbers():
    """
    Demo: Footer Text and Slide Numbers.

    This demonstrates deck-level options for adding:
        - Footer text on all slides
        - Slide page numbers

    These options are set at the deck level in the "options" object.
    """
    print("\n" + "=" * 60)
    print("DEMO: Footer and Slide Numbers")
    print("=" * 60)
    print("\nYou can add footer text and slide numbers to all generated slides")
    print("using deck-level options.")

    print("\n--- Deck Options Example ---")
    options_example = {
        "options": {
            "auto_paginate_tables": True,
            "table_min_font_size": 9,
            "show_slide_numbers": True,
            "footer_text": "Confidential - Internal Use Only",
            "footer_font_size": 8,
            "footer_font_name": "Arial"
        }
    }
    print(json.dumps(options_example, indent=2))

    print("\n--- Available Footer/Slide Number Options ---")
    print("| Option             | Type    | Default | Description")
    print("|--------------------|---------|---------|---------------------------------")
    print("| show_slide_numbers | boolean | false   | Display page numbers on slides")
    print("| footer_text        | string  | null    | Footer text for all slides")
    print("| footer_font_size   | integer | 8       | Font size for footer text")
    print("| footer_font_name   | string  | null    | Font name (inherits from template)")

    print("\n--- Usage in generate_deck() ---")
    print("""
result = generate_deck(
    slides=[...],
    options={
        "show_slide_numbers": True,
        "footer_text": "Q4 2024 Report - Confidential",
        "footer_font_size": 8,
        "footer_font_name": "Arial"
    },
    output_path="deck_with_footer.pptx"
)
""")
    print("See demo_data_fake.json for a complete example with these options.")


# ============================================================================
# END-TO-END DEMOS
# ============================================================================

def run_template_inheritance_demo():
    """
    Run a demo showcasing template styling inheritance:
    1. Upload template_v3.pptx (with custom styling)
    2. Generate a deck using demo_data_fake.json (no font specs)
    3. The output will inherit fonts from the template

    This demonstrates that when you omit font_name/font_size in your JSON,
    the generated slides use whatever fonts are defined in the template.
    """
    print("=" * 60)
    print("TEMPLATE STYLING INHERITANCE DEMO")
    print("=" * 60)

    # Step 1: Upload the template
    print("\n[Step 1/4] Uploading template with custom styling...")
    template_path = os.path.join(os.path.dirname(__file__), "template_v3.pptx")

    if not os.path.exists(template_path):
        print(f"ERROR: Template not found: {template_path}")
        print("Make sure template_v3.pptx is in the demo folder.")
        return None

    upload_result = upload_template(
        template_path,
        metadata={
            "category": "demo",
            "tags": ["styling", "inheritance", "v2"],
            "description": "Template with custom placeholder styling for inheritance demo"
        }
    )
    template_id = upload_result["template_id"]

    # Step 2: Analyze template
    print("\n[Step 2/4] Analyzing template...")
    analysis = analyze_template(template_id)

    results = analysis.get("results", {})
    slides_info = results.get("slides", [])
    if not slides_info:
        print("ERROR: No slides found in template analysis")
        return None

    first_slide_id = slides_info[0]["slideId"]
    second_slide_id = slides_info[1]["slideId"] if len(slides_info) > 1 else first_slide_id
    third_slide_id = slides_info[2]["slideId"] if len(slides_info) > 2 else first_slide_id
    print(f"\n  Template slide IDs:")
    print(f"    - Slide 0 (table only): {first_slide_id}")
    print(f"    - Slide 1 (table + textbox): {second_slide_id}")
    print(f"    - Slide 2 (logo page): {third_slide_id}")

    # Step 3: Load demo data WITHOUT font specifications
    print("\n[Step 3/4] Loading demo_data_fake.json (no font specs)...")
    data_path = os.path.join(os.path.dirname(__file__), "demo_data_fake.json")

    if not os.path.exists(data_path):
        print(f"ERROR: Data file not found: {data_path}")
        print("Make sure demo_data_fake.json is in the demo folder.")
        return None

    with open(data_path, "r") as f:
        deck_request = json.load(f)

    # Assign template slides based on content type
    def has_logo_cells(slide_data):
        blocks = slide_data.get("slide_data", {}).get("content", {}).get("blocks", [])
        for block in blocks:
            if block.get("type") == "table":
                rows = block.get("table", {}).get("table", {}).get("rows", [])
                for row in rows:
                    for cell in row.get("cells", []):
                        if cell.get("is_logo") is True:
                            return True
        return False

    for i, slide in enumerate(deck_request["slides"]):
        blocks = slide.get("slide_data", {}).get("content", {}).get("blocks", [])
        has_text_block = any(b.get("type") == "text" for b in blocks)
        is_logo_slide = has_logo_cells(slide)

        if is_logo_slide:
            slide["template_slide_id"] = third_slide_id
        elif has_text_block:
            slide["template_slide_id"] = second_slide_id
        else:
            slide["template_slide_id"] = first_slide_id

    print(f"  Prepared {len(deck_request['slides'])} slide(s)")
    print("  Note: JSON data does NOT specify font_name or font_size")
    print("  Fonts will be inherited from the template's placeholders")

    # Step 4: Generate the deck
    print("\n[Step 4/4] Generating presentation...")
    output_path = os.path.join(os.path.dirname(__file__), "demo_output_inherited_styling.pptx")

    result = generate_deck(
        slides=deck_request["slides"],
        options=deck_request.get("options"),
        output_path=output_path
    )

    print("\n" + "=" * 60)
    print("TEMPLATE INHERITANCE DEMO COMPLETE!")
    print("=" * 60)
    print(f"\nGenerated presentation: {output_path}")
    print(f"Total pages: {result.get('total_pages_generated', 'N/A')}")
    print(f"Status: {result.get('status', 'N/A')}")
    print("\nOpen the file to verify fonts match the template's styling,")
    print("not the default Arial that would be used if fonts were explicit.")

    return result


def run_end_to_end_demo():
    """
    Run a complete end-to-end demo:
    1. Upload the sample template
    2. Analyze it to get slide IDs
    3. Generate a presentation using demo_data_fake.json (with logo pages)
    4. Download the result

    This demo includes:
        - Multi-slide generation with pagination
        - Conditional formatting (NPS, criticality, outlook)
        - Logo pages with automatic company logo fetching
        - Mixed content cells (bullets + quotes)

    This is the quickest way to test the full API workflow.
    """
    print("=" * 60)
    print("END-TO-END DEMO (with Logo Pages)")
    print("=" * 60)

    # Step 1: Upload template
    print("\n[Step 1/4] Uploading template...")
    template_path = os.path.join(os.path.dirname(__file__), "template_v3.pptx")

    if not os.path.exists(template_path):
        print(f"ERROR: Template not found: {template_path}")
        return None

    upload_result = upload_template(
        template_path,
        metadata={
            "category": "demo",
            "tags": ["tables", "example", "logos"],
            "description": "Demo template with table layouts and logo pages"
        }
    )
    template_id = upload_result["template_id"]

    # Step 2: Analyze template
    print("\n[Step 2/4] Analyzing template...")
    analysis = analyze_template(template_id)

    # Slides are nested under 'results.slides' in the analysis response
    results = analysis.get("results", {})
    slides_info = results.get("slides", [])
    if not slides_info:
        print("ERROR: No slides found in template analysis")
        return None

    # Get slide IDs from analysis (key is 'slideId' not 'slide_id')
    first_slide_id = slides_info[0]["slideId"]  # Template slide index 0 (table only)
    second_slide_id = slides_info[1]["slideId"] if len(slides_info) > 1 else first_slide_id  # Template slide index 1 (table + textbox)
    third_slide_id = slides_info[2]["slideId"] if len(slides_info) > 2 else first_slide_id  # Template slide index 2 (logo page)
    print(f"\n  Template slide IDs:")
    print(f"    - Slide 0 (table only): {first_slide_id}")
    print(f"    - Slide 1 (table + textbox): {second_slide_id}")
    print(f"    - Slide 2 (logo page): {third_slide_id}")

    # Step 3: Load demo data and update slide IDs
    print("\n[Step 3/4] Preparing slide data...")
    # Use demo data with logo pages
    data_path = os.path.join(os.path.dirname(__file__), "demo_data_fake.json")

    if not os.path.exists(data_path):
        # Fall back to basic demo data if not found
        print(f"  Demo data not found, falling back to demo_data.json")
        data_path = os.path.join(os.path.dirname(__file__), "demo_data.json")

    with open(data_path, "r") as f:
        deck_request = json.load(f)

    # Assign template slides to demo data based on content type:
    # - Slides with table + textbox (commentary) -> Template slide 1 (second_slide_id)
    # - Slides with logo cells -> Template slide 2 (third_slide_id)
    # - Slides with table only -> Template slide 0 (first_slide_id)
    num_slides = len(deck_request["slides"])
    print(f"  Loaded {num_slides} slide(s) from demo data")

    def has_logo_cells(slide_data):
        """Check if any table cell has is_logo: true"""
        blocks = slide_data.get("slide_data", {}).get("content", {}).get("blocks", [])
        for block in blocks:
            if block.get("type") == "table":
                rows = block.get("table", {}).get("table", {}).get("rows", [])
                for row in rows:
                    for cell in row.get("cells", []):
                        if cell.get("is_logo") is True:
                            return True
        return False

    for i, slide in enumerate(deck_request["slides"]):
        blocks = slide.get("slide_data", {}).get("content", {}).get("blocks", [])
        has_text_block = any(b.get("type") == "text" for b in blocks)
        is_logo_slide = has_logo_cells(slide)

        if is_logo_slide:
            slide["template_slide_id"] = third_slide_id  # Logo page template
            print(f"    - Slide {i} (logo page) -> Template slide 2")
        elif has_text_block:
            slide["template_slide_id"] = second_slide_id  # Table + textbox template
            print(f"    - Slide {i} (table + text) -> Template slide 1")
        else:
            slide["template_slide_id"] = first_slide_id   # Table only template
            print(f"    - Slide {i} (table only) -> Template slide 0")

    print("\n  Note: Slide 2 contains logo cells (is_logo: true) that will")
    print("        fetch company logos from domains like stripe.com, github.com")

    # Step 4: Generate the deck
    print("\n[Step 4/4] Generating presentation...")
    output_path = os.path.join(os.path.dirname(__file__), "demo_output.pptx")

    result = generate_deck(
        slides=deck_request["slides"],
        options=deck_request.get("options"),
        output_path=output_path
    )

    print("\n" + "=" * 60)
    print("DEMO COMPLETE!")
    print("=" * 60)
    print(f"\nGenerated presentation: {output_path}")
    print(f"Total pages: {result.get('total_pages_generated', 'N/A')}")
    print(f"Status: {result.get('status', 'N/A')}")

    print("\nFeatures demonstrated:")
    print("  - Multi-slide generation with pagination")
    print("  - Conditional formatting (NPS, criticality, outlook)")
    print("  - Logo pages with automatic company logo fetching")
    print("  - Mixed content cells (bullets + quotes)")

    return result


# ============================================================================
# MAIN
# ============================================================================

if __name__ == "__main__":
    print("=" * 60)
    print("PowerPoint Generation API - Demo Script")
    print("=" * 60)
    print(f"\nAPI Base URL: {BASE_URL}")
    print(f"API Key: {'*' * 8}...{API_KEY[-4:] if len(API_KEY) > 4 else '****'}")
    print("\nIncluded files:")
    print("  - demo_data_fake.json: Sample deck with logo pages (inherits fonts)")
    print("  - template_v3.pptx: Template with 3 slide layouts")
    print("  - README.md: Complete API documentation")
    print("\n" + "-" * 60)
    print("Available demo functions:")
    print("-" * 60)
    print("  demo_list_templates()           - List templates in your org")
    print("  demo_upload_and_analyze()       - Upload & analyze the sample template")
    print("  demo_generate_from_sample_data()- Generate deck from demo_data_fake.json")
    print("  demo_simple_slide()             - Show simple slide data structure")
    print("  demo_table_slide()              - Show table slide with formatting")
    print("  demo_logo_slide()               - Show logo page with company logos")
    print("  demo_template_styling_inheritance() - Explain template styling inheritance")
    print("  demo_footer_and_slide_numbers() - Show footer & page number options")
    print("-" * 60)
    print("End-to-end demos:")
    print("-" * 60)
    print("  run_end_to_end_demo()           - Full demo with logo pages")
    print("  run_template_inheritance_demo() - Full demo with inherited styling")
    print("-" * 60)
    print("\nQuickstart:")
    print("  1. Update API_KEY and BASE_URL at the top of this file")
    print("  2. Run: run_end_to_end_demo()  OR  run_template_inheritance_demo()")
    print()

    # Run the end-to-end demo (now includes logo pages by default)
    run_end_to_end_demo()
    run_template_inheritance_demo()