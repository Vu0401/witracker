import streamlit as st
from datetime import date
from crawl import scrape_articles
from util import save_to_word

# Page config
st.set_page_config(page_title="WiTracker", page_icon="🚀", layout="wide")

# Initialize session state
if 'fetching' not in st.session_state:
    st.session_state.fetching = False  # Trạng thái ban đầu: chưa nhấn

# Sidebar
st.sidebar.title("🔍 WiTracker")
st.sidebar.markdown("**Enter your credentials to fetch news:**")

# Input fields with consistent styling
with st.sidebar:
    st.write("test")
    print("test log")
    username = st.text_input("Username", placeholder="Enter your username")
    password = st.text_input("Password", type="password", placeholder="Enter your password")
    selected_date = st.date_input("Select Date", value=date.today(), help="Choose the date to fetch news from")
    max_articles = st.number_input(
        "Max Articles",
        min_value=1,
        value=10,
        step=1,
        help="Set the maximum number of articles to fetch"
    )

    # Fetch News button với disabled dựa trên trạng thái
    fetch_button = st.button(
        "📡 Fetch News",
        disabled=st.session_state.fetching,
        use_container_width=True  # Nút full-width cho đẹp
    )

if fetch_button and not st.session_state.fetching:
    if username and password:
        st.session_state.fetching = True  # Đánh dấu đang xử lý
        progress_container = st.empty()
        
        with st.spinner("Fetching news..."):
            def progress_callback(message):
                progress_container.write(f"🔔 {message}")

            formatted_date = selected_date.strftime("%d/%m/%Y")
            progress_container.write(f"📅 Fetching news for {formatted_date}...")

            list_of_summarized_docs = scrape_articles(
                username, password, formatted_date, max_articles=max_articles, progress_callback=progress_callback
            )

        if list_of_summarized_docs is None:
            st.error("❌ An error occurred while fetching news!")
        elif not list_of_summarized_docs:
            st.warning("⚠ No news found for the selected date!")
        else:
            word_buffer = save_to_word(list_of_summarized_docs, formatted_date)
            st.success("✅ News successfully fetched!")
            st.download_button(
                label="📥 Download Report",
                data=word_buffer,
                file_name=f"News_Report_{selected_date.strftime('%d-%m-%Y')}.docx",
                mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                use_container_width=True  # Nút download full-width
            )
        
        st.session_state.fetching = False  # Hoàn tất, bật lại nút
    else:
        st.error("❌ Please enter both Username and Password!")
