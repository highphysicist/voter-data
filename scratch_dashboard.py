import streamlit as st
import json
import os
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from collections import defaultdict
import re
import numpy as np


def load_collective_data(collectives_dir: str = "collectives"):
    """
    Load all collective data from the directory
    """
    collective_files = {}
    collective_metadata = {}

    for filename in os.listdir(collectives_dir):
        if filename.startswith("collective_number_") and filename.endswith(".json"):
            filepath = os.path.join(collectives_dir, filename)

            with open(filepath, 'r', encoding='utf-8') as f:
                data = json.load(f)

            collective_num = data['metadata']['collective_number']
            collective_files[collective_num] = data
            collective_metadata[collective_num] = data['metadata']

    return collective_files, collective_metadata


def extract_gender_from_card(card):
    """
    Extract gender from a voter card by checking individual textboxes
    """
    raw_content = card.get('raw_content', [])

    # Check each textbox individually for exact matches
    for textbox in raw_content:
        textbox = textbox.strip()

        # Exact matches for gender indicators
        if textbox == 'पन':  # Exact match for garbled "पुरुष" (Male)
            return 'Male'
        elif textbox == 'सद':  # Exact match for garbled "स्त्री" (Female)
            return 'Female'

    # If no gender indicator found in any individual textbox
    return 'Other'


def extract_age_from_card(card):
    """
    Extract age from a voter card using the pattern:
    Last 4 textboxes: [gender_value, age_value, "वय :", "लपग  :"]
    The number right before "वय :" contains the age
    """
    raw_content = card.get('raw_content', [])

    # Look for the pattern in the last few textboxes
    if len(raw_content) >= 4:
        # Check the last 4 textboxes for our pattern
        last_four = raw_content[-4:]

        # Pattern: [gender_value, age_value, "वय :", "लपग  :"]
        if last_four[2] == "वय :" and last_four[3] == "लपग  :":
            age_text = last_four[1].strip()

            # Try to extract numeric age
            try:
                age = int(age_text)
                if 10 <= age <= 120:  # Reasonable age range for voters
                    return age
            except (ValueError, TypeError):
                pass

    # Alternative: Search for "वय :" pattern anywhere in the content
    for i, textbox in enumerate(raw_content):
        if textbox == "वय :" and i > 0:
            # The previous textbox should contain the age
            age_text = raw_content[i - 1].strip()
            try:
                age = int(age_text)
                if 10 <= age <= 120:
                    return age
            except (ValueError, TypeError):
                pass

    return None  # Age not found


def analyze_gender_distribution(collective_data):
    """
    Analyze gender distribution for a collective
    """
    gender_counts = {'Male': 0, 'Female': 0, 'Other': 0}
    total_voters = 0

    # Process all pages in the collective
    for page_num, cards in collective_data['pages'].items():
        for card in cards:
            gender = extract_gender_from_card(card)
            gender_counts[gender] += 1
            total_voters += 1

    return gender_counts, total_voters


def analyze_age_distribution(collective_data):
    """
    Analyze age distribution for a collective
    """
    ages = []
    age_extraction_stats = {'success': 0, 'failed': 0}

    # Process all pages in the collective
    for page_num, cards in collective_data['pages'].items():
        for card in cards:
            age = extract_age_from_card(card)
            if age is not None:
                ages.append(age)
                age_extraction_stats['success'] += 1
            else:
                age_extraction_stats['failed'] += 1

    return ages, age_extraction_stats


def create_gender_pie_chart(gender_counts, collective_number):
    """
    Create a pie chart for gender distribution
    """
    if sum(gender_counts.values()) == 0:
        return None

    # Prepare data for plotting
    genders = list(gender_counts.keys())
    counts = list(gender_counts.values())

    df = pd.DataFrame({
        'Gender': genders,
        'Count': counts
    })

    # Create pie chart
    fig = px.pie(df, values='Count', names='Gender',
                 title=f'Gender Distribution - Collective {collective_number}',
                 color_discrete_map={'Male': '#1f77b4', 'Female': '#ff7f0e', 'Other': '#2ca02c'})

    fig.update_traces(textposition='inside', textinfo='percent+label')
    return fig


def create_age_histogram(ages, collective_number):
    """
    Create a histogram for age distribution
    """
    if not ages:
        return None

    # Create histogram
    fig = px.histogram(x=ages,
                       title=f'Age Distribution - Collective {collective_number}',
                       labels={'x': 'Age', 'y': 'Number of Voters'},
                       nbins=20)

    fig.update_layout(
        xaxis_title="Age",
        yaxis_title="Number of Voters",
        showlegend=False
    )

    return fig


def create_age_box_plot(ages, collective_number):
    """
    Create a box plot for age distribution
    """
    if not ages:
        return None

    fig = px.box(x=ages,
                 title=f'Age Statistics - Collective {collective_number}',
                 labels={'x': 'Age'})

    fig.update_layout(showlegend=False)
    return fig


def create_gender_table(gender_counts, collective_number):
    """
    Create a table showing gender distribution
    """
    if sum(gender_counts.values()) == 0:
        return None

    total = sum(gender_counts.values())

    table_data = []
    for gender, count in gender_counts.items():
        percentage = (count / total) * 100 if total > 0 else 0
        table_data.append({
            'Gender': gender,
            'Count': count,
            'Percentage': f'{percentage:.1f}%'
        })

    df = pd.DataFrame(table_data)
    return df


def create_age_statistics_table(ages, collective_number):
    """
    Create a table showing age statistics
    """
    if not ages:
        return None

    stats_data = {
        'Statistic': ['Total Samples', 'Mean Age', 'Median Age', 'Minimum Age', 'Maximum Age', 'Standard Deviation'],
        'Value': [
            len(ages),
            f"{np.mean(ages):.1f}",
            f"{np.median(ages):.1f}",
            f"{np.min(ages)}",
            f"{np.max(ages)}",
            f"{np.std(ages):.1f}"
        ]
    }

    df = pd.DataFrame(stats_data)
    return df


def calculate_total_gender_distribution(collective_files):
    """
    Calculate total gender distribution across all collectives
    """
    total_gender_counts = {'Male': 0, 'Female': 0, 'Other': 0}
    collective_gender_data = {}

    for collective_num, collective_data in collective_files.items():
        gender_counts, total_voters = analyze_gender_distribution(collective_data)
        collective_gender_data[collective_num] = gender_counts

        # Add to total
        for gender, count in gender_counts.items():
            total_gender_counts[gender] += count

    return total_gender_counts, collective_gender_data


def calculate_total_age_distribution(collective_files):
    """
    Calculate total age distribution across all collectives
    """
    all_ages = []
    collective_age_data = {}
    age_extraction_stats = {'total_success': 0, 'total_failed': 0}

    for collective_num, collective_data in collective_files.items():
        ages, stats = analyze_age_distribution(collective_data)
        collective_age_data[collective_num] = ages
        all_ages.extend(ages)
        age_extraction_stats['total_success'] += stats['success']
        age_extraction_stats['total_failed'] += stats['failed']

    return all_ages, collective_age_data, age_extraction_stats


def debug_age_detection(collective_files, sample_collective="1"):
    """
    Debug function to show sample age detection
    """
    st.sidebar.markdown("---")
    st.sidebar.subheader("🔍 Age Detection Debug")

    if sample_collective in collective_files:
        collective_data = collective_files[sample_collective]
        sample_cards = []

        # Get first few cards from first page
        for page_num, cards in collective_data['pages'].items():
            sample_cards.extend(cards[:2])  # First 2 cards from each page
            if len(sample_cards) >= 3:
                break

        st.sidebar.write("Sample age detection:")
        for i, card in enumerate(sample_cards[:2]):
            raw_content = card.get('raw_content', [])
            detected_age = extract_age_from_card(card)

            st.sidebar.write(f"Card {i + 1}:")
            st.sidebar.write(f"  Last 4: {raw_content[-4:] if len(raw_content) >= 4 else 'Not enough textboxes'}")
            st.sidebar.write(f"  Detected Age: {detected_age}")
            st.sidebar.write("---")


def extract_age_gender_pairs(collective_data):
    """
    Returns list of dicts with age & gender together
    """
    rows = []

    for page_num, cards in collective_data['pages'].items():
        for card in cards:
            age = extract_age_from_card(card)
            gender = extract_gender_from_card(card)

            if age is not None:
                rows.append({
                    "Age": age,
                    "Gender": gender
                })

    return pd.DataFrame(rows)


def filter_ages(ages, min_age=None, max_age=None):
    """
    Filter ages based on optional min/max bounds
    """
    filtered = ages
    if min_age is not None:
        filtered = [a for a in filtered if a >= min_age]
    if max_age is not None:
        filtered = [a for a in filtered if a <= max_age]
    return filtered

def aggregate_collective_data(collective_files, collective_ids):
    """
    Combine multiple collectives into a single synthetic collective
    """
    combined = {"pages": {}}
    page_counter = 0

    for cid in collective_ids:
        for _, cards in collective_files[cid]["pages"].items():
            combined["pages"][str(page_counter)] = cards
            page_counter += 1

    return combined


def aggregate_metadata(collective_metadata, collective_ids):
    return {
        "pages": sum((collective_metadata[c]["pages"] for c in collective_ids), []),
        "total_voters": sum(collective_metadata[c]["total_voters"] for c in collective_ids)
    }

def main():
    """
    Main Streamlit dashboard with multiple tabs
    """
    st.set_page_config(
        page_title="Voter Demographic Analysis",
        page_icon="📊",
        layout="wide"
    )

    st.title("🏛️ Voter Demographic Analysis by Collective")
    st.markdown("---")

    # Load collective data
    collectives_dir = "collectives"

    if not os.path.exists(collectives_dir):
        st.error(f"❌ Collectives directory '{collectives_dir}' not found!")
        st.info("Please make sure the collective JSON files are generated first.")
        return

    collective_files, collective_metadata = load_collective_data(collectives_dir)

    if not collective_files:
        st.error("❌ No collective files found!")
        return

    st.success(f"✅ Loaded {len(collective_files)} collectives")

    # Calculate total distributions
    total_gender_counts, collective_gender_data = calculate_total_gender_distribution(collective_files)
    all_ages, collective_age_data, age_stats = calculate_total_age_distribution(collective_files)

    # Sidebar for collective selection
    st.sidebar.title("📋 Navigation")

    # Collective selector
    collective_numbers = sorted(collective_files.keys(), key=lambda x: int(x))
    st.sidebar.markdown("### 🧩 Collective Selection")

    collective_options = ["All"] + collective_numbers

    selected_collectives = st.sidebar.multiselect(
        "Select Collectives:",
        options=collective_options,
        default=["All"]
    )

    if "All" in selected_collectives:
        active_collectives = collective_numbers
    else:
        active_collectives = selected_collectives

    active_collective_data = aggregate_collective_data(
        collective_files,
        active_collectives
    )

    active_metadata = aggregate_metadata(
        collective_metadata,
        active_collectives
    )

    collective_label = (
        "All Collectives"
        if active_collectives == collective_numbers
        else f"Collectives: {', '.join(active_collectives)}"
    )

    # Debug sections
    # debug_age_detection(collective_files, active_collectives)

    # Display total statistics in sidebar
    st.sidebar.markdown("---")
    st.sidebar.subheader("📈 Overall Statistics")

    total_voters = sum(total_gender_counts.values())
    st.sidebar.metric("Total Voters", total_voters)
    st.sidebar.metric("Total Collectives", len(collective_files))
    st.sidebar.metric("Age Samples", age_stats['total_success'])
    st.sidebar.metric("Age Extraction Rate",
                      f"{(age_stats['total_success'] / (age_stats['total_success'] + age_stats['total_failed']) * 100):.1f}%")

    # Create tabs

    tab1, tab2, tab3 = st.tabs([
        "🎭 Gender Analysis",
        "📅 Age Analysis",
        "👥 Age + Gender Analysis"
    ])

    with tab1:
        # Gender Analysis Tab
        col1, col2 = st.columns([2, 1])

        with col1:
            st.subheader(f"{collective_label} - Gender Analysis")

            # Get collective metadata
            metadata = active_metadata
            collective_data = active_collective_data

            # Display collective info
            st.write(f"**Pages:** {metadata['pages']}")
            st.write(f"**Total Voters:** {metadata['total_voters']}")

            # Analyze gender distribution for selected collective
            gender_counts, total_voters = analyze_gender_distribution(collective_data)

            # Create and display pie chart
            fig = create_gender_pie_chart(gender_counts, collective_label)
            if fig:
                st.plotly_chart(fig, use_container_width=True)
            else:
                st.warning("No gender data available for this collective")

        with col2:
            st.subheader("Gender Distribution Table")

            # Create and display table
            table_df = create_gender_table(gender_counts, collective_label)
            if table_df is not None:
                st.dataframe(table_df, use_container_width=True)

                # Display summary metrics
                male_count = gender_counts.get('Male', 0)
                female_count = gender_counts.get('Female', 0)
                other_count = gender_counts.get('Other', 0)
                total = sum(gender_counts.values())

                col1_metric, col2_metric, col3_metric = st.columns(3)
                with col1_metric:
                    st.metric("Male", male_count)
                with col2_metric:
                    st.metric("Female", female_count)
                with col3_metric:
                    st.metric("Other", other_count)

    with tab2:
        # Age Analysis Tab
        col1, col2 = st.columns([2, 1])

        with col1:
            st.subheader(f"{collective_label} - Age Analysis")

            # Get collective metadata
            metadata = active_metadata
            collective_data = active_collective_data

            # Analyze age distribution for selected collective
            ages, age_stats_collective = analyze_age_distribution(collective_data)

            # Display age extraction stats
            st.write(
                f"**Age Samples:** {len(ages)} / {age_stats_collective['success'] + age_stats_collective['failed']} "
                f"({(age_stats_collective['success'] / (age_stats_collective['success'] + age_stats_collective['failed']) * 100):.1f}% success rate)")

            # ---- Age Filters ----
            st.markdown("### 🔎 Age Filters")

            min_age = st.number_input(
                "Age ≥",
                min_value=0,
                max_value=120,
                value=0,
                step=1
            )

            max_age = st.number_input(
                "Age ≤",
                min_value=0,
                max_value=120,
                value=120,
                step=1
            )

            filtered_ages = filter_ages(ages, min_age=min_age, max_age=max_age)

            if filtered_ages:
                # Create and display age histogram
                hist_fig = create_age_histogram(filtered_ages, collective_label)
                st.plotly_chart(hist_fig, use_container_width=True)

                # Create and display box plot
                box_fig = create_age_box_plot(filtered_ages, collective_label)
                st.plotly_chart(box_fig, use_container_width=True)
            else:
                st.warning("No age data available for this query")

        with col2:
            st.subheader("Age Statistics")

            if ages:
                # Create and display age statistics table
                stats_table = create_age_statistics_table(ages, collective_label)
                st.dataframe(stats_table, use_container_width=True)

                # Display key metrics
                st.metric("Average Age", f"{np.mean(ages):.1f}")
                st.metric("Median Age", f"{np.median(ages):.1f}")
                st.metric("Age Range", f"{np.min(ages)} - {np.max(ages)}")
            else:
                st.info("No age statistics available")

    with tab3:
        st.subheader(f"{collective_label} - Age & Gender Analysis")

        df_ag = extract_age_gender_pairs(active_collective_data)

        if df_ag.empty:
            st.warning("No combined age & gender data youavailable")
        else:
            # ---- Filters ----
            st.markdown("### 🔎 Filters")

            selected_genders = st.multiselect(
                "Gender",
                options=sorted(df_ag["Gender"].unique()),
                default=list(df_ag["Gender"].unique())
            )

            min_age = st.slider("Minimum Age", 0, 120, 0)
            max_age = st.slider("Maximum Age", 0, 120, 120)

            df_filtered = df_ag[
                (df_ag["Gender"].isin(selected_genders)) &
                (df_ag["Age"] >= min_age) &
                (df_ag["Age"] <= max_age)
                ]

            # ---- Visualizations ----
            col1, col2 = st.columns(2)

            with col1:
                st.markdown("#### Age Distribution by Gender")
                fig_hist = px.histogram(
                    df_filtered,
                    x="Age",
                    color="Gender",
                    barmode="overlay",
                    nbins=20
                )
                st.plotly_chart(fig_hist, use_container_width=True)

            with col2:
                st.markdown("#### Age Statistics by Gender")
                fig_box = px.box(
                    df_filtered,
                    x="Gender",
                    y="Age"
                )
                st.plotly_chart(fig_box, use_container_width=True)

            # ---- Table ----
            st.markdown("### 📋 Filtered Data Summary")
            summary = (
                df_filtered
                .groupby("Gender")["Age"]
                .agg(["count", "mean", "median", "min", "max"])
                .round(1)
                .reset_index()
            )

            st.dataframe(summary, use_container_width=True)

    # Collective comparison section (across both tabs)
    st.markdown("---")
    st.subheader("📊 Collective Comparison")

    # Create comparison table for both gender and age
    comparison_data = []
    for collective_num in collective_numbers:
        gender_data = collective_gender_data[collective_num]
        age_data = collective_age_data[collective_num]
        total_voters = sum(gender_data.values())

        if total_voters > 0 and age_data:
            comparison_data.append({
                'Collective': collective_num,
                'Male': gender_data['Male'],
                'Female': gender_data['Female'],
                'Other': gender_data['Other'],
                'Total Voters': total_voters,
                'Age Samples': len(age_data),
                'Avg Age': f"{np.mean(age_data):.1f}" if age_data else "N/A",
                'Median Age': f"{np.median(age_data):.1f}" if age_data else "N/A"
            })

    if comparison_data:
        comparison_df = pd.DataFrame(comparison_data)
        st.dataframe(comparison_df, use_container_width=True)


if __name__ == "__main__":
    main()