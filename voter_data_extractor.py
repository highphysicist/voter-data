import fitz  # PyMuPDF
import json
import re
from typing import Dict, List, Any
from collections import defaultdict


def extract_complete_page_data(pdf_path: str, page_num: int) -> Dict[str, Any]:
    """
    Complete end-to-end extraction for one page
    """
    doc = fitz.open(pdf_path)
    page = doc.load_page(page_num - 1)

    # STEP 1: Get all rectangles (lines and photos)
    drawings = page.get_drawings()
    rectangles_data = []
    for drawing in drawings:
        rect = drawing['rect']
        width = rect.x1 - rect.x0
        height = rect.y1 - rect.y0
        rectangles_data.append({
            'x0': rect.x0, 'y0': rect.y0,
            'x1': rect.x1, 'y1': rect.y1,
            'width': width, 'height': height,
            'area': width * height
        })

    # STEP 2: Get all text spans
    page_dict = page.get_text("dict")
    all_text_spans = []
    for block in page_dict.get("blocks", []):
        for line in block.get("lines", []):
            for span in line.get("spans", []):
                text = span.get("text", "").strip()
                if text:
                    all_text_spans.append({
                        "text": text,
                        "x0": span["bbox"][0], "y0": span["bbox"][1],
                        "x1": span["bbox"][2], "y1": span["bbox"][3],
                        "center_x": (span["bbox"][0] + span["bbox"][2]) / 2,
                        "center_y": (span["bbox"][1] + span["bbox"][3]) / 2
                    })

    doc.close()

    # STEP 3: Detect grid from rectangles
    grid_data = detect_grid_from_rectangles(rectangles_data)

    # STEP 4: Classify text spans into header, footer, and cards
    classification_result = classify_text_spans(all_text_spans, grid_data)

    # STEP 5: Create final card data with raw content
    final_cards = create_final_cards(classification_result['card_assignments'], grid_data['all_grid_cells'])

    return {
        'page_number': page_num,
        'header': [span['text'] for span in classification_result['header_spans']],
        'footer': [span['text'] for span in classification_result['footer_spans']],
        'cards': final_cards,
        'total_cards': len(final_cards),
        'unassigned_spans': [span['text'] for span in classification_result['unassigned_spans']]
    }


def detect_grid_from_rectangles(rectangles_data):
    """
    Detect the main grid from rectangle data
    """
    # Separate by type
    horizontal_lines = []
    vertical_lines = []

    for rect in rectangles_data:
        if rect['area'] == 0:  # It's a line
            if rect['width'] > 0 and rect['height'] == 0:
                # Horizontal line
                horizontal_lines.append({
                    'y': rect['y0'],
                    'x0': rect['x0'],
                    'x1': rect['x1'],
                    'width': rect['width']
                })
            elif rect['width'] == 0 and rect['height'] > 0:
                # Vertical line
                vertical_lines.append({
                    'x': rect['x0'],
                    'y0': rect['y0'],
                    'y1': rect['y1'],
                    'height': rect['height']
                })

    # Identify the footer separator (longest horizontal line at bottom)
    horizontal_lines.sort(key=lambda l: l['y'])
    footer_separator = None
    if horizontal_lines and horizontal_lines[-1]['width'] > 500:
        footer_separator = horizontal_lines.pop()

    # Cluster horizontal lines by y-position to find the main grid
    horizontal_clusters = defaultdict(list)
    for line in horizontal_lines:
        if 100 < line['width'] < 200:  # Main grid horizontal lines (186.1)
            y_key = round(line['y'])
            horizontal_clusters[y_key].append(line)

    # Get the main horizontal grid lines
    main_horizontal = []
    for y, lines in horizontal_clusters.items():
        if len(lines) >= 1:
            x0 = min(line['x0'] for line in lines)
            x1 = max(line['x1'] for line in lines)
            main_horizontal.append({'y': y, 'x0': x0, 'x1': x1})

    main_horizontal.sort(key=lambda l: l['y'])

    # Cluster vertical lines by x-position
    vertical_clusters = defaultdict(list)
    for line in vertical_lines:
        if line['height'] > 50:  # Main grid vertical lines (70.3-70.4)
            x_key = round(line['x'])
            vertical_clusters[x_key].append(line)

    # Get the main vertical grid lines
    main_vertical = []
    for x, lines in vertical_clusters.items():
        if len(lines) >= 1:
            y0 = min(line['y0'] for line in lines)
            y1 = max(line['y1'] for line in lines)
            main_vertical.append({'x': x, 'y0': y0, 'y1': y1})

    main_vertical.sort(key=lambda l: l['x'])

    # Create all possible grid cells
    all_grid_cells = []
    if len(main_horizontal) >= 2 and len(main_vertical) >= 2:
        rows = len(main_horizontal) - 1
        columns = len(main_vertical) - 1

        for row in range(rows):
            for col in range(columns):
                cell_x0 = main_vertical[col]['x']
                cell_y0 = main_horizontal[row]['y']
                cell_x1 = main_vertical[col + 1]['x']
                cell_y1 = main_horizontal[row + 1]['y']

                all_grid_cells.append({
                    'cell_id': row * columns + col,
                    'bbox': (cell_x0, cell_y0, cell_x1, cell_y1),
                    'row': row + 1,
                    'col': col + 1
                })

    return {
        'all_grid_cells': all_grid_cells,
        'main_horizontal': main_horizontal,
        'main_vertical': main_vertical,
        'footer_separator': footer_separator
    }


def classify_text_spans(all_text_spans, grid_data):
    """
    Classify text spans into header, footer, and grid cells
    """
    header_spans = []
    footer_spans = []
    unassigned_spans = []
    card_assignments = defaultdict(list)

    if not grid_data['all_grid_cells']:
        return {
            'header_spans': all_text_spans,
            'footer_spans': [],
            'unassigned_spans': [],
            'card_assignments': {}
        }

    # Get grid boundaries
    first_card_top = grid_data['all_grid_cells'][0]['bbox'][1]
    last_card_bottom = grid_data['all_grid_cells'][-1]['bbox'][3]

    for span in all_text_spans:
        assigned = False

        # Check if span belongs to a grid cell (lenient boundaries)
        for cell in grid_data['all_grid_cells']:
            cell_x0, cell_y0, cell_x1, cell_y1 = cell['bbox']
            if (cell_x0 - 2 <= span['center_x'] <= cell_x1 + 2 and
                    cell_y0 - 2 <= span['center_y'] <= cell_y1 + 2):
                card_assignments[cell['cell_id']].append(span)
                assigned = True
                break

        if not assigned:
            # Lenient header/footer boundaries
            if span['y1'] < first_card_top:
                header_spans.append(span)
            elif span['y0'] > last_card_bottom:
                footer_spans.append(span)
            else:
                unassigned_spans.append(span)

    return {
        'header_spans': header_spans,
        'footer_spans': footer_spans,
        'unassigned_spans': unassigned_spans,
        'card_assignments': card_assignments
    }


def create_final_cards(card_assignments, all_grid_cells):
    """
    Create final card data from assigned text spans
    """
    final_cards = []

    for cell in all_grid_cells:
        spans_in_cell = card_assignments.get(cell['cell_id'], [])

        # Only create card if it has significant content (at least 3 text spans)
        if len(spans_in_cell) >= 3:
            spans_sorted = sorted(spans_in_cell, key=lambda x: (x['y0'], x['x0']))
            raw_texts = [span['text'] for span in spans_sorted]

            # Extract EPIC and Part number
            epic, part, _ = extract_epic_part(' '.join(raw_texts))

            final_cards.append({
                'card_number': len(final_cards) + 1,
                'bbox': cell['bbox'],
                'row': cell['row'],
                'col': cell['col'],
                'raw_content': raw_texts,
                'epic_number': epic,
                'part_number': part,
                'text_spans_count': len(spans_in_cell)
            })

    return final_cards


def extract_epic_part(text: str) -> tuple:
    """Extract EPIC number and part number"""
    pattern = r'([A-Z]{3}\d{7})\s+(\d+/\d+/\d+)'
    match = re.search(pattern, text)
    if match:
        epic = match.group(1)
        part = match.group(2)
        return epic, part, None
    return None, None, None


def process_entire_pdf(pdf_path: str, start_page: int, end_page: int) -> Dict[str, Any]:
    """
    Process entire PDF and create master JSON
    """
    master_data = {
        'headers': {},
        'footers': {},
        'cards': {},
        'unassigned': {},
        'summary': {
            'total_pages_processed': 0,
            'total_cards_found': 0,
            'pages_with_cards': 0,
            'pages_without_cards': 0
        }
    }

    print(f"📚 Processing PDF: {pdf_path}")
    print(f"📄 Pages: {start_page} to {end_page}")
    print("=" * 50)

    for page_num in range(start_page, end_page + 1):
        try:
            print(f"Processing page {page_num}...", end=" ")

            # Extract data for current page
            page_data = extract_complete_page_data(pdf_path, page_num)

            # Add to master data with page number as key
            master_data['headers'][str(page_num)] = page_data['header']
            master_data['footers'][str(page_num)] = page_data['footer']
            master_data['cards'][str(page_num)] = page_data['cards']
            master_data['unassigned'][str(page_num)] = page_data['unassigned_spans']

            # Update summary
            master_data['summary']['total_pages_processed'] += 1
            master_data['summary']['total_cards_found'] += page_data['total_cards']

            if page_data['total_cards'] > 0:
                master_data['summary']['pages_with_cards'] += 1
            else:
                master_data['summary']['pages_without_cards'] += 1

            print(f"✅ {page_data['total_cards']} cards")

        except Exception as e:
            print(f"❌ Error on page {page_num}: {str(e)}")
            # Add empty data for failed pages
            master_data['headers'][str(page_num)] = []
            master_data['footers'][str(page_num)] = []
            master_data['cards'][str(page_num)] = []
            master_data['unassigned'][str(page_num)] = []

    return master_data


def save_master_json(master_data: Dict[str, Any], output_file: str):
    """Save master JSON file"""
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(master_data, f, indent=2, ensure_ascii=False)

    print(f"\n💾 Master JSON saved to: {output_file}")


# Main execution for entire PDF
if __name__ == "__main__":
    PDF_PATH = "DraftList_Ward_139.pdf"
    START_PAGE = 9  # Page 9 (1-based indexing)
    END_PAGE = 4086  # Page 4086 (1-based indexing) - second last page

    print("🚀 Starting complete PDF processing...")

    # Process entire PDF
    master_data = process_entire_pdf(PDF_PATH, START_PAGE, END_PAGE)

    # Save master JSON
    save_master_json(master_data, "voter_data_master_final_139.json")

    # Print final summary
    summary = master_data['summary']
    print(f"\n📊 FINAL SUMMARY:")
    print(f"Total pages processed: {summary['total_pages_processed']}")
    print(f"Total cards found: {summary['total_cards_found']}")
    print(f"Pages with cards: {summary['pages_with_cards']}")
    print(f"Pages without cards: {summary['pages_without_cards']}")
    print(f"Average cards per page: {summary['total_cards_found'] / summary['total_pages_processed']:.1f}")

    # Show sample from first processed page
    first_page = str(START_PAGE)
    if first_page in master_data['cards'] and master_data['cards'][first_page]:
        sample_cards = master_data['cards'][first_page][:2]
        print(f"\n📋 Sample from page {first_page}:")
        for card in sample_cards:
            print(f"  Card {card['card_number']} (R{card['row']}C{card['col']}): {card['epic_number'] or 'No EPIC'}")