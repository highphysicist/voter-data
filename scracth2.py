import json
import os
import re
from collections import defaultdict
import shutil


def create_collective_files_from_voter_json(voter_json_path: str, header_mapping_path: str,
                                            output_dir: str = "collectives"):
    """
    Create collective files from the voter.json cards data
    """
    print("🎯 CREATING COLLECTIVE FILES FROM VOTER.JSON CARDS")
    print("=" * 60)

    # Load the data
    with open(voter_json_path, 'r', encoding='utf-8') as f:
        voter_data = json.load(f)

    with open(header_mapping_path, 'r', encoding='utf-8') as f:
        header_mapping = json.load(f)

    # Create output directory
    if os.path.exists(output_dir):
        shutil.rmtree(output_dir)
    os.makedirs(output_dir)

    print(f"📁 Output directory: {output_dir}")

    # Get the cards data
    cards_data = voter_data.get('cards', {})
    page_assignments = header_mapping.get('page_assignments', {})

    print(f"📊 Found {len(cards_data)} pages with card data")


    # Organize cards by collective
    collective_cards = defaultdict(lambda: defaultdict(list))
    collective_stats = defaultdict(lambda: {'total_cards': 0, 'total_voters': 0, 'pages': set()})

    # Process each page
    for page_num_str, page_cards in cards_data.items():
        page_num = int(page_num_str)
        collective = page_assignments.get(str(page_num), "UNASSIGNED")

        if collective != "UNASSIGNED":
            collective_cards[collective][page_num] = page_cards
            collective_stats[collective]['total_cards'] += len(page_cards)
            collective_stats[collective]['total_voters'] += len(page_cards)  # Each card = 1 voter
            collective_stats[collective]['pages'].add(page_num)

            print(f"✅ Page {page_num} → {collective}: {len(page_cards)} cards")
        else:
            print(f"❌ Page {page_num}: No collective assignment")

    # Create individual collective files
    collective_files = {}

    for collective, page_cards_dict in collective_cards.items():
        # Extract collective number from "भभग क.X"
        collective_number = extract_collective_number(collective)

        if collective_number:
            filename = f"collective_number_{collective_number}.json"
            filepath = os.path.join(output_dir, filename)

            collective_data = {
                'metadata': {
                    'collective_name': collective,
                    'collective_number': collective_number,
                    'total_pages': len(page_cards_dict),
                    'total_cards': collective_stats[collective]['total_cards'],
                    'total_voters': collective_stats[collective]['total_voters'],
                    'pages': sorted(list(collective_stats[collective]['pages'])),
                    'file_generated': True
                },
                'pages': page_cards_dict  # This contains {page_num: [cards_array]}
            }

            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(collective_data, f, indent=2, ensure_ascii=False)

            collective_files[collective] = filepath

            stats = collective_stats[collective]
            print(f"✅ Created: {filename}")
            print(f"   📄 Pages: {stats['pages']}")
            print(f"   🃏 Cards: {stats['total_cards']}")
            print(f"   👥 Voters: {stats['total_voters']}")

    # Handle unassigned pages (if any)
    unassigned_pages = {}
    for page_num_str in cards_data.keys():
        page_num = int(page_num_str)
        if page_assignments.get(str(page_num)) == "UNASSIGNED":
            unassigned_pages[page_num] = cards_data[page_num_str]

    if unassigned_pages:
        unassigned_file = os.path.join(output_dir, "unassigned_collective.json")
        unassigned_data = {
            'metadata': {
                'collective_name': 'UNASSIGNED',
                'total_pages': len(unassigned_pages),
                'total_cards': sum(len(cards) for cards in unassigned_pages.values()),
                'total_voters': sum(len(cards) for cards in unassigned_pages.values()),
                'pages': sorted(unassigned_pages.keys()),
                'note': 'Pages without proper header assignment'
            },
            'pages': unassigned_pages
        }

        with open(unassigned_file, 'w', encoding='utf-8') as f:
            json.dump(unassigned_data, f, indent=2, ensure_ascii=False)

        print(f"⚠️  Created: unassigned_collective.json with {len(unassigned_pages)} pages")

    return {
        'collective_files': collective_files,
        'collective_stats': collective_stats,
        'total_cards': sum(len(cards) for page_cards in cards_data.values() for cards in [page_cards]),
        'total_pages': len(cards_data)
    }


def extract_collective_number(collective_header):
    """
    Extract the number from "भभग क.X" pattern
    """
    pattern = r'भभग क\.(\d+)'
    match = re.search(pattern, collective_header)

    if match:
        return match.group(1)

    # Try alternative patterns
    alt_patterns = [
        r'क\.(\d+)',
        r'भभग\s*(\d+)',
        r'(\d+)'
    ]

    for pattern in alt_patterns:
        match = re.search(pattern, collective_header)
        if match:
            return match.group(1)

    return None


def generate_collective_summary(analysis_result, output_dir: str = "collectives"):
    """
    Generate a comprehensive summary file
    """
    summary_file = os.path.join(output_dir, "collectives_summary.json")

    summary = {
        'metadata': {
            'total_collectives': len(analysis_result['collective_stats']),
            'total_pages_processed': analysis_result['total_pages'],
            'total_cards_processed': analysis_result['total_cards'],
            'total_voters_processed': analysis_result['total_cards'],  # 1 card = 1 voter
            'analysis_complete': True
        },
        'collectives': {
            collective: {
                'collective_number': extract_collective_number(collective),
                'pages': sorted(list(stats['pages'])),
                'total_cards': stats['total_cards'],
                'total_voters': stats['total_voters'],
                'file': f"collective_number_{extract_collective_number(collective)}.json"
            }
            for collective, stats in analysis_result['collective_stats'].items()
        }
    }

    with open(summary_file, 'w', encoding='utf-8') as f:
        json.dump(summary, f, indent=2, ensure_ascii=False)

    print(f"\n📊 Summary saved to: {summary_file}")

    # Print final statistics
    print(f"\n🎯 FINAL STATISTICS:")
    print("=" * 40)
    print(f"Total collectives created: {len(analysis_result['collective_stats'])}")
    print(f"Total pages processed: {analysis_result['total_pages']}")
    print(f"Total cards/voters: {analysis_result['total_cards']}")

    if analysis_result['collective_stats']:
        # Show collective details
        for collective, stats in analysis_result['collective_stats'].items():
            collective_num = extract_collective_number(collective)
            print(
                f"  🏷️  Collective {collective_num}: {stats['total_voters']} voters across {len(stats['pages'])} pages")


# Main execution
if __name__ == "__main__":
    VOTER_JSON_PATH = "voter_data_master_final_139.json"
    HEADER_MAPPING_PATH = "comprehensive_header_mapping.json"

    print("🚀 CREATING COLLECTIVE FILES")
    print("=" * 60)

    # Create the collective files
    analysis_result = create_collective_files_from_voter_json(VOTER_JSON_PATH, HEADER_MAPPING_PATH)

    # Generate summary
    generate_collective_summary(analysis_result)

    print(f"\n✅ TASK COMPLETED SUCCESSFULLY!")
    print("=" * 60)
    print(f"""
    Created individual collective files in ./collectives/:

    Each collective_number_X.json contains:
    - Metadata about the collective
    - All pages that belong to that collective  
    - All voter cards from those pages
    - Ready for demographic analysis!

    Now we can analyze each collective separately! 🎯
    """)