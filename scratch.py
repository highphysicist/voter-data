from fontTools.ttLib import TTFont
import os


def analyze_marathi_font(ttf_path):
    """
    COMPREHENSIVE TTF FONT ANALYSIS
    Extracts all character mappings and glyph information that might reveal the encoding pattern
    """
    try:
        font = TTFont(ttf_path)
        print("🎯 FONT ANALYSIS STARTED")
        print("=" * 70)

        # 1. FONT BASIC INFORMATION
        print("\n📋 FONT METADATA:")
        print("-" * 40)
        name_records = {}
        for name_record in font['name'].names:
            if name_record.string:
                name_str = str(name_record.string, 'utf-8', errors='ignore')
                name_records[name_record.nameID] = name_str
                print(f"Name ID {name_record.nameID}: {name_str}")

        # 2. CHARACTER MAPPING TABLES (Most Important)
        print(f"\n🔤 CHARACTER MAPPING TABLES (cmap):")
        print("-" * 40)

        all_mappings = {}

        for cmap_table in font['cmap'].tables:
            print(f"\nPlatform: {cmap_table.platformID}, Encoding: {cmap_table.platEncID}")
            print(f"Format: {cmap_table.format}")

            table_mappings = {}
            for unicode_val, glyph_name in cmap_table.cmap.items():
                # Convert to character if possible
                try:
                    char = chr(unicode_val)
                except:
                    char = "<?>"

                table_mappings[glyph_name] = {
                    'unicode': unicode_val,
                    'unicode_hex': hex(unicode_val),
                    'character': char
                }

            all_mappings[cmap_table.format] = table_mappings

            # Show first 20 mappings from this table
            count = 0
            for glyph_name, mapping in list(table_mappings.items())[:20]:
                print(f"  Glyph: {glyph_name:20} → Unicode: {mapping['unicode_hex']} → Char: {mapping['character']}")
                count += 1
            if len(table_mappings) > 20:
                print(f"  ... and {len(table_mappings) - 20} more mappings")

        # 3. GLYPH NAMES ANALYSIS (Look for Roman patterns)
        print(f"\n🔍 GLYPH NAMES ANALYSIS:")
        print("-" * 40)

        glyph_set = font.getGlyphSet()
        glyph_names = list(glyph_set.keys())

        print(f"Total glyphs: {len(glyph_names)}")

        # Look for glyphs with Roman-sounding names
        roman_pattern_glyphs = []
        for glyph_name in glyph_names:
            lower_name = glyph_name.lower()
            # Common Roman transliteration patterns
            if (any(char in lower_name for char in ['a', 'e', 'i', 'o', 'u']) and
                    any(part in lower_name for part in ['ka', 'kha', 'ga', 'gha', 'cha', 'chha', 'ja', 'jha',
                                                        'ta', 'tha', 'da', 'dha', 'na', 'pa', 'pha', 'ba', 'bha',
                                                        'ma', 'ya', 'ra', 'la', 'va', 'sha', 'ssa', 'sa', 'ha'])):
                roman_pattern_glyphs.append(glyph_name)

        print(f"\nGlyphs with possible Roman patterns: {len(roman_pattern_glyphs)}")
        for glyph_name in roman_pattern_glyphs[:30]:  # Show first 30
            print(f"  {glyph_name}")

        # 4. CREATE POTENTIAL MAPPING TABLE
        print(f"\n🗺️ POTENTIAL ROMAN TO DEVANAGARI MAPPING:")
        print("-" * 40)

        # Common Marathi Roman transliterations to look for
        common_mappings = {
            'a': 'अ', 'aa': 'आ', 'i': 'इ', 'ee': 'ई', 'u': 'उ', 'oo': 'ऊ',
            'e': 'ए', 'ai': 'ऐ', 'o': 'ओ', 'au': 'औ',
            'ka': 'क', 'kha': 'ख', 'ga': 'ग', 'gha': 'घ',
            'cha': 'च', 'chha': 'छ', 'ja': 'ज', 'jha': 'झ',
            'ta': 'त', 'tha': 'थ', 'da': 'द', 'dha': 'ध', 'na': 'न',
            'pa': 'प', 'pha': 'फ', 'ba': 'ब', 'bha': 'भ', 'ma': 'म',
            'ya': 'य', 'ra': 'र', 'la': 'ल', 'va': 'व',
            'sha': 'श', 'ssa': 'ष', 'sa': 'स', 'ha': 'ह'
        }

        found_mappings = {}
        for roman, devanagari in common_mappings.items():
            # Look for glyph names that match Roman patterns
            matching_glyphs = [name for name in glyph_names if roman in name.lower()]
            if matching_glyphs:
                found_mappings[roman] = {
                    'devanagari': devanagari,
                    'matching_glyphs': matching_glyphs[:3]  # First 3 matches
                }

        for roman, data in found_mappings.items():
            print(f"  {roman:8} → {data['devanagari']}  (Glyphs: {', '.join(data['matching_glyphs'][:2])})")

        # 5. FONT TABLE INFO
        print(f"\n📊 FONT TABLE OVERVIEW:")
        print("-" * 40)
        for table_tag in font.keys():
            table = font[table_tag]
            print(f"  {table_tag}: {type(table).__name__}")

        font.close()

        print(f"\n✅ ANALYSIS COMPLETE")
        print("=" * 70)

        return {
            'name_records': name_records,
            'mappings': all_mappings,
            'glyph_count': len(glyph_names),
            'roman_pattern_glyphs': roman_pattern_glyphs,
            'found_mappings': found_mappings
        }

    except Exception as e:
        print(f"❌ ERROR: {e}")
        return None


def extract_complete_mapping_table(ttf_path):
    """
    Extract a complete mapping table from the font
    """
    print(f"\n🎯 EXTRACTING COMPLETE MAPPING TABLE")
    print("=" * 70)

    font = TTFont(ttf_path)

    # Get the primary Unicode mapping table
    for cmap_table in font['cmap'].tables:
        if cmap_table.isUnicode():
            print(f"\nUsing Unicode table (Platform {cmap_table.platformID}):")
            print("-" * 50)

            mapping_list = []
            for unicode_val, glyph_name in cmap_table.cmap.items():
                if unicode_val >= 0x0900:  # Devanagari Unicode block
                    try:
                        char = chr(unicode_val)
                        mapping_list.append((glyph_name, unicode_val, char))
                    except:
                        continue

            # Sort by Unicode value
            mapping_list.sort(key=lambda x: x[1])

            print(f"{'Glyph Name':<25} {'Unicode':<10} {'Character':<10}")
            print("-" * 50)
            for glyph_name, unicode_val, char in mapping_list[:50]:  # First 50
                print(f"{glyph_name:<25} {hex(unicode_val):<10} {char:<10}")

            if len(mapping_list) > 50:
                print(f"... and {len(mapping_list) - 50} more mappings")

            break

    font.close()


# MAIN EXECUTION
if __name__ == "__main__":
    ttf_file_path = "SakalBharati Normal.ttf"  # Change this to your TTF file path

    if not os.path.exists(ttf_file_path):
        print(f"❌ TTF file not found: {ttf_file_path}")
        print("Please update the 'ttf_file_path' variable with the correct path to your TTF file")
    else:
        print(f"🔍 Analyzing font: {ttf_file_path}")
        print("This will reveal the character mapping patterns...")
        print()

        # Run comprehensive analysis
        results = analyze_marathi_font(ttf_file_path)

        if results:
            # Extract complete mapping table
            extract_complete_mapping_table(ttf_file_path)

            print(f"\n💡 NEXT STEPS:")
            print("- Look for Roman-sounding glyph names in the output")
            print("- Check if glyph names match the patterns from your PDF")
            print("- The mapping table should reveal the encoding scheme")