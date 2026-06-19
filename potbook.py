import streamlit as st
import requests
from bs4 import BeautifulSoup
import pandas as pd
from datetime import datetime

# ==========================================
# 1. PAGE CONFIGURATION
# ==========================================
st.set_page_config(page_title="Matrix Dashboard", page_icon="📊", layout="wide")

# Create the two main tabs
tab1, tab2 = st.tabs(["Results", "Selector"])

# ==========================================
# 2. TAB 1: LIVE MARKET RESULTS
# ==========================================
with tab1:
    # The clean display sequence sequence order
    TARGET_MARKETS = [
        "SRIDEVI",
        "TIME BAZAR",
        "MILAN DAY",
        "RAJDHANI DAY",
        "KALYAN",
        "SRIDEVI NIGHT",
        "MAIN BAZAR",
        "MILAN NIGHT",
        "RAJDHANI NIGHT",
        "DESAWAR",
        "SHRI GANESH",
        "FARIDABAD",
        "GHAZIABAD",
        "GALI",
    ]

    def convert_to_24h(time_str):
        """Helper function to cleanly convert '04:02 PM' to '16:02'"""
        try:
            cleaned_time = " ".join(time_str.strip().split())
            in_time = datetime.strptime(cleaned_time, "%I:%M %p")
            return in_time.strftime("%H:%M")
        except Exception:
            return "N/A"

    def fetch_live_data():
        """Fetches data from the first source: dpbossss.boston"""
        url = "https://dpbossss.boston/"
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        }
        try:
            response = requests.get(url, headers=headers, timeout=15)
            if response.status_code != 200:
                st.error(
                    f"Failed to fetch primary data. Status code: {response.status_code}"
                )
                return []

            soup = BeautifulSoup(response.text, "html.parser")
            market_headers = soup.find_all("h4")
            extracted_data = []

            for h4 in market_headers:
                market_name = h4.text.strip().upper()

                matched_base = None
                for target in sorted(TARGET_MARKETS, key=len, reverse=True):
                    if target == market_name:
                        matched_base = target
                        break

                    if target in market_name:
                        if "NIGHT" in market_name and "NIGHT" not in target:
                            continue
                        if "DAY" in market_name and "NIGHT" in target:
                            continue
                        if "MORNING" in market_name and "MORNING" not in target:
                            continue

                        matched_base = target
                        break

                if matched_base:
                    block = h4.parent
                    span_tag = block.find("span")
                    p_tag = block.find("p")

                    if not span_tag or not p_tag:
                        continue

                    result_numbers = span_tag.text.strip()
                    time_parts = p_tag.text.strip().split()

                    open_24h, close_24h = "N/A", "N/A"
                    if len(time_parts) >= 4:
                        raw_open = f"{time_parts[0]} {time_parts[1]}"
                        raw_close = f"{time_parts[2]} {time_parts[3]}"
                        open_24h = convert_to_24h(raw_open)
                        close_24h = convert_to_24h(raw_close)

                    extracted_data.append(
                        {
                            "Market Name": matched_base,
                            "Live Digits / Result": result_numbers,
                            "Open Time": open_24h,
                            "Close Time": close_24h,
                        }
                    )
            return extracted_data
        except Exception as e:
            st.error(f"An error occurred fetching primary data: {e}")
            return []

    def fetch_satta_data():
        """Fetches data from the second source: satta-king-up.com"""
        url = "https://satta-king-up.com/desawar/satta-result-chart/ds/"
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        }

        target_satta_markets = [
            "DESAWAR",
            "SHRI GANESH",
            "FARIDABAD",
            "GHAZIABAD",
            "GALI",
        ]
        extracted_data = []

        try:
            response = requests.get(url, headers=headers, timeout=15)
            if response.status_code != 200:
                st.error(
                    f"Failed to fetch secondary Satta data. Status: {response.status_code}"
                )
                return []

            soup = BeautifulSoup(response.text, "html.parser")
            rows = soup.find_all("tr", class_=lambda c: c and "game-result" in c)

            for row in rows:
                name_tag = row.find("h3", class_="game-name")
                if not name_tag:
                    continue

                market_name = name_tag.text.strip().upper()

                if market_name in target_satta_markets:
                    time_tag = row.find("h3", class_="game-time")
                    today_tag = row.find("td", class_="today-number")

                    raw_time = (
                        time_tag.text.replace("at", "").strip() if time_tag else "N/A"
                    )
                    time_24h = convert_to_24h(raw_time) if raw_time != "N/A" else "N/A"
                    today_number = today_tag.text.strip() if today_tag else "XX"

                    extracted_data.append(
                        {
                            "Market Name": market_name,
                            "Live Digits / Result": today_number,
                            "Open Time": "N/A",
                            "Close Time": time_24h,
                        }
                    )

            return extracted_data
        except Exception as e:
            st.error(f"Secondary Satta scraper error: {e}")
            return []

    # Layout for refresh button
    col_space, col_btn = st.columns([5, 1])
    with col_btn:
        refresh_triggered = st.button(
            "🔄 Refresh Table", use_container_width=True, key="market_refresh_btn"
        )

    # Combine data from both scrapers
    if refresh_triggered or "cached_table_data" not in st.session_state:
        with st.spinner("Fetching latest updates from all sources..."):
            dpboss_data = fetch_live_data()
            satta_data = fetch_satta_data()

            combined_data = dpboss_data + satta_data

            st.session_state["cached_table_data"] = combined_data
            st.session_state["last_updated_time"] = datetime.now().strftime(
                "%I:%M:%S %p"
            )

    if "last_updated_time" in st.session_state:
        st.info(
            f"Last successfully updated at: **{st.session_state['last_updated_time']}**"
        )

    live_rows = st.session_state.get("cached_table_data", [])

    if isinstance(live_rows, list) and len(live_rows) > 0:
        df = pd.DataFrame(live_rows)
        df = df.drop_duplicates(subset=["Market Name"], keep="first")

        df["Market Name"] = pd.Categorical(
            df["Market Name"], categories=TARGET_MARKETS, ordered=True
        )
        df = df.sort_values("Market Name").reset_index(drop=True)

        st.dataframe(df, use_container_width=True, hide_index=True)
    else:
        st.warning("Waiting for data. Click 'Refresh Table' to pull live feeds.")


# ==========================================
# 3. TAB 2: NUMBER SELECTOR
# ==========================================
with tab2:
    # Initialize selector session states if not present
    if "first_digit_filter" not in st.session_state:
        st.session_state.first_digit_filter = {"odd": False, "even": False}
    if "second_digit_filter" not in st.session_state:
        st.session_state.second_digit_filter = {"odd": False, "even": False}
    if "range_filter" not in st.session_state:
        st.session_state.range_filter = {"below_mid": False, "above_mid": False}

    def get_first_digit(num):
        return (num // 10) % 10

    def get_second_digit(num):
        return num % 10

    def matches_filters(num, first_filter, second_filter, range_filter, quad_filter):
        # 1. Check Tens Digit (Opening)
        first_d = get_first_digit(num)
        if first_filter["odd"] or first_filter["even"]:
            first_matches = False
            if first_filter["odd"] and first_d % 2 == 1:
                first_matches = True
            if first_filter["even"] and first_d % 2 == 0:
                first_matches = True
            if not first_matches:
                return False

        # 2. Check Last Digit (Closing)
        second_d = get_second_digit(num)
        if second_filter["odd"] or second_filter["even"]:
            second_matches = False
            if second_filter["odd"] and second_d % 2 == 1:
                second_matches = True
            if second_filter["even"] and second_d % 2 == 0:
                second_matches = True
            if not second_matches:
                return False

        # 3. Check Partition (Range)
        if range_filter["below_mid"] or range_filter["above_mid"]:
            range_matches = False
            if range_filter["below_mid"] and num < 50:
                range_matches = True
            if range_filter["above_mid"] and num >= 50:
                range_matches = True
            if not range_matches:
                return False

        # 4. Check Quadrant
        if quad_filter["q1"] or quad_filter["q2"] or quad_filter["q3"] or quad_filter["q4"]:
            quad_matches = False
            if quad_filter["q1"] and 0 <= num <= 24:
                quad_matches = True
            if quad_filter["q2"] and 25 <= num <= 49:
                quad_matches = True
            if quad_filter["q3"] and 50 <= num <= 74:
                quad_matches = True
            if quad_filter["q4"] and 75 <= num <= 99:
                quad_matches = True
            if not quad_matches:
                return False

        return True

    # Two columns inside Tab 2
    left_col, right_col = st.columns([1.1, 0.9], gap="medium")

    with right_col:
        if st.button(
            "🔄 Reset All Filters", use_container_width=False, key="selector_reset_btn"
        ):
            st.session_state.first_choice = "All"
            st.session_state.second_choice = "All"
            st.session_state.range_choice = "All"
            st.session_state.quadrant_choice = "All"
            st.rerun()

        st.divider()

        st.write("**Partition**")
        range_choice = st.radio(
            "Range",
            ["All", "BM", "AM"],
            key="range_choice",
            horizontal=True,
            label_visibility="collapsed",
        )
        below_mid = range_choice == "BM"
        above_mid = range_choice == "AM"

        # NEW FEATURE: Quadrant
        st.write("**Quadrant**")
        quadrant_choice = st.radio(
            "Quadrant",
            ["All", "Q1", "Q2", "Q3", "Q4"],
            key="quadrant_choice",
            horizontal=True,
            label_visibility="collapsed",
            help="Q1: 00-24 | Q2: 25-49 | Q3: 50-74 | Q4: 75-99"
        )
        q1_active = quadrant_choice == "Q1"
        q2_active = quadrant_choice == "Q2"
        q3_active = quadrant_choice == "Q3"
        q4_active = quadrant_choice == "Q4"

        st.write("**Closing**")
        second_choice = st.radio(
            "Last Digit",
            ["A", "O", "E"],
            key="second_choice",
            horizontal=True,
            label_visibility="collapsed",
        )
        second_odd = second_choice == "O"
        second_even = second_choice == "E"

        st.write("**Opening**")
        first_choice = st.radio(
            "Tens Digit",
            ["A", "O", "E"],
            key="first_choice",
            horizontal=True,
            label_visibility="collapsed",
        )
        first_odd = first_choice == "O"
        first_even = first_choice == "E"

        # Construct filter dictionaries
        first_digit_filter = {"odd": first_odd, "even": first_even}
        second_digit_filter = {"odd": second_odd, "even": second_even}
        range_filter = {"below_mid": below_mid, "above_mid": above_mid}
        quad_filter = {
            "q1": q1_active,
            "q2": q2_active,
            "q3": q3_active,
            "q4": q4_active
        }

        all_numbers = list(range(0, 100))
        filtered_numbers = [
            num
            for num in all_numbers
            if matches_filters(
                num, first_digit_filter, second_digit_filter, range_filter, quad_filter
            )
        ]

        st.divider()
        result_text = ", ".join([f"{num:02d}" for num in filtered_numbers])
        st.info(f"{result_text if filtered_numbers else 'Select filters'}")
        st.divider()

        col1, col2, col3 = st.columns(3)
        col1.metric("Total", 100)
        col2.metric("Match", len(filtered_numbers))
        col3.metric("Out", 100 - len(filtered_numbers))

    with left_col:
        # Check if ANY filter is active
        has_active_filters = (
            first_odd or first_even or 
            second_odd or second_even or 
            below_mid or above_mid or 
            q1_active or q2_active or q3_active or q4_active
        )

        grid_html = """
    <style>
    .number-grid {
        display: grid;
        grid-template-columns: repeat(10, 1fr);
        gap: 4px;
        padding: 10px;
        background-color: #f0f0f0;
        border-radius: 8px;
        max-width: 500px;
    }
    .number-cell {
        aspect-ratio: 1;
        display: flex;
        align-items: center;
        justify-content: center;
        font-size: 12px;
        font-weight: bold;
        border-radius: 4px;
        transition: all 0.3s ease;
        min-height: 40px;
    }
    .number-cell.active {
        background-color: #00d084;
        color: white;
        box-shadow: 0 0 10px rgba(0, 208, 132, 0.5);
    }
    .number-cell.inactive {
        background-color: #d0d0d0;
        color: #808080;
        opacity: 0.4;
    }
    .number-cell.default {
        background-color: #4a90e2;
        color: white;
    }
    </style>
    <div class="number-grid">
    """
        for num in range(100):
            if has_active_filters:
                cell_class = (
                    "number-cell active"
                    if num in filtered_numbers
                    else "number-cell inactive"
                )
            else:
                cell_class = "number-cell default"
            grid_html += f'<div class="{cell_class}">{num:02d}</div>'

        grid_html += "</div>"
        st.markdown(grid_html, unsafe_allow_html=True)