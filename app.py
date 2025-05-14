import streamlit as st
import sys
import os
import time
import threading
from datetime import datetime, timedelta
import pandas as pd
import pytz

# Define Indonesian Western Time timezone
WIB = pytz.timezone('Asia/Jakarta')

# Add the current directory to the path so modules can be imported
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from utils.timer import Timer
from database.db_manager import DBManager
from utils.visualization import create_daily_distribution_chart, create_activity_pie_chart, create_period_comparison_chart

st.set_page_config(
    page_title="PyDomoro - Pomodoro Timer",
    page_icon="⏱️",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# Apply custom CSS
with open(os.path.join(os.path.dirname(__file__), "styles/style.css")) as f:
    st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)

# Initialize session state variables
if 'timer' not in st.session_state:
    st.session_state.timer = Timer()
if 'mode' not in st.session_state:
    st.session_state.mode = 'timer'
if 'activity_type' not in st.session_state:
    st.session_state.activity_type = 'Work'
if 'duration_minutes' not in st.session_state:
    st.session_state.duration_minutes = 25
if 'session_id' not in st.session_state:
    st.session_state.session_id = None
if 'timer_completed' not in st.session_state:
    st.session_state.timer_completed = False
if 'timer_restored' not in st.session_state:
    st.session_state.timer_restored = False

# Database manager instance
db = DBManager()

# Function to restore timer state from database
def restore_timer_state():
    """Restore timer state from database if available"""
    if st.session_state.timer_restored:
        return
        
    timer_state = db.get_timer_state()
    if timer_state:
        # Set session variables from saved state
        st.session_state.mode = timer_state["mode"]
        st.session_state.activity_type = timer_state["activity_type"]
        st.session_state.duration_minutes = timer_state["duration_minutes"]
        st.session_state.session_id = timer_state["session_id"]
        
        # Restore timer with callback for notification
        st.session_state.timer.restore_from_state(timer_state, callback=timer_callback)
        
        # Mark as restored to avoid restoring multiple times
        st.session_state.timer_restored = True

# Functions for notification
def play_notification():
    """Play notification sound when timer completes"""
    try:
        sound_file = os.path.join(os.path.dirname(__file__), "assets/notification.mp3")
        # Try to use playsound if available
        try:
            from playsound import playsound
            threading.Thread(target=playsound, args=(sound_file,), daemon=True).start()
        except ImportError:
            # Fallback if playsound is not installed
            threading.Thread(target=lambda: print("Notification sound played"), daemon=True).start()
    except Exception as e:
        st.error(f"Could not play notification sound: {str(e)}")

def timer_callback():
    """Callback function when timer completes"""
    play_notification()
    st.session_state.timer_completed = True
    
    # End the session in database
    if st.session_state.session_id:
        db.end_session(st.session_state.session_id)
        st.session_state.session_id = None
        
    # Clear timer state from database
    db.clear_timer_state()

# Create tabs for navigation
tab1, tab2 = st.tabs(["🏠 Dashboard", "🎯 Focus Timer"])

# Try to restore timer state
restore_timer_state()

# Tab 1: Dashboard (Home)
with tab1:
    st.title("🏠 Focus Dashboard")
    
    # Period selection
    col1, col2 = st.columns([3, 1])
    with col1:
        period_type = st.radio(
            "Select time period:",
            options=["day", "week", "month", "year"],
            horizontal=True
        )
    
    # Determine date range based on period type
    today = datetime.now(WIB)
    if period_type == "day":
        period_label = today.strftime("%A, %B %d, %Y")
    elif period_type == "week":
        start_of_week = today - timedelta(days=today.weekday())
        end_of_week = start_of_week + timedelta(days=6)
        period_label = f"{start_of_week.strftime('%b %d')} - {end_of_week.strftime('%b %d, %Y')}"
    elif period_type == "month":
        period_label = today.strftime("%B %Y")
    else:  # year
        period_label = today.strftime("%Y")
    
    # Display current period
    st.subheader(f"Showing data for: {period_label}")
    
    # Get focus statistics
    total_focus_time = db.get_total_focus_time(period_type)
    activity_distribution = db.get_activity_distribution(period_type)
    
    # Display statistics
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.metric(
            "Total Focus Time",
            f"{total_focus_time:.1f} min",
            delta=None
        )
    
    with col2:
        # Average focus time per day
        if period_type == "day":
            avg_focus = total_focus_time
            st.metric("Average Focus/Day", f"{avg_focus:.1f} min")
        elif period_type == "week":
            avg_focus = total_focus_time / 7
            st.metric("Average Focus/Day", f"{avg_focus:.1f} min")
        elif period_type == "month":
            # Approximate days in month
            days_in_month = 30  # Simplified
            avg_focus = total_focus_time / days_in_month
            st.metric("Average Focus/Day", f"{avg_focus:.1f} min")
        else:  # year
            avg_focus = total_focus_time / 365
            st.metric("Average Focus/Day", f"{avg_focus:.1f} min")
    
    with col3:
        # Most focused activity
        if activity_distribution:
            most_focused = max(activity_distribution.items(), key=lambda x: x[1]) if activity_distribution else (None, 0)
            st.metric(
                "Most Focused Activity",
                most_focused[0] if most_focused[0] else "None",
                f"{most_focused[1]:.1f} min" if most_focused[1] else "0 min"
            )
        else:
            st.metric("Most Focused Activity", "None", "0 min")
    
    # Visualizations section
    st.header("📊 Visualizations")
    
    # Create tabs for different visualizations
    viz_tab1, viz_tab2, viz_tab3 = st.tabs(["Time Distribution", "Activity Breakdown", "Trends"])
    
    # Tab 1: Time Distribution
    with viz_tab1:
        st.subheader(f"Focus Time Distribution ({period_type.capitalize()})")
        sessions = db.get_sessions_by_period(period_type)
        
        if sessions:
            fig = create_daily_distribution_chart(sessions)
            if fig:
                st.pyplot(fig)
            else:
                st.info("Not enough data to generate time distribution chart.")
        else:
            st.info("No focus sessions recorded for this period.")
    
    # Tab 2: Activity Breakdown
    with viz_tab2:
        st.subheader(f"Activity Distribution ({period_type.capitalize()})")
        
        if activity_distribution:
            # Create two columns for chart and table
            col1, col2 = st.columns([1, 1])
            
            # Column 1: Pie Chart
            with col1:
                # Get focus vs non-focus data for today
                focus_nonfocus = db.get_focus_vs_nonfocus_time() if period_type == "day" else None
                fig = create_activity_pie_chart(activity_distribution, focus_nonfocus)
                if fig:
                    st.pyplot(fig)
            
            # Column 2: Activity Details Table
            with col2:
                st.subheader("Activity Details")
                activity_data = []
                for activity, minutes in activity_distribution.items():
                    activity_data.append({
                        "Activity": activity,
                        "Time (min)": round(minutes, 1),
                        "Percentage": round(minutes / total_focus_time * 100, 1) if total_focus_time > 0 else 0
                    })
                
                activity_df = pd.DataFrame(activity_data)
                st.dataframe(activity_df, use_container_width=True)
        else:
            st.info("No activities recorded for this period.")
    
    # Tab 3: Trends
    with viz_tab3:
        st.subheader(f"Focus Time Trends")
        
        # Number of periods to compare depends on the selected period type
        if period_type == "day":
            periods = 7  # Last 7 days
        elif period_type == "week":
            periods = 4  # Last 4 weeks
        elif period_type == "month":
            periods = 6  # Last 6 months
        else:
            periods = 3  # Last 3 years
        
        fig = create_period_comparison_chart(db, period_type, periods)
        if fig:
            st.pyplot(fig)
        else:
            st.info(f"Not enough data to show trends for {periods} {period_type}s.")
            
            
            # Add backup button in a new section below the statistics
    st.divider()
    
    # Backup Database Section
    st.subheader("💾 Database Management")
    
    # Organize buttons in two columns
    col1, col2 = st.columns(2)
    
    # Backup Button
    with col1:
        if st.button("📥 Backup Database", use_container_width=True):
            try:
                backup_path = db.backup_database()
                
                # Read the backup file for download
                with open(backup_path, "rb") as file:
                    backup_data = file.read()
                
                # Create a download button for the backup file
                filename = os.path.basename(backup_path)
                st.download_button(
                    label="Download Backup",
                    data=backup_data,
                    file_name=filename,
                    mime="application/octet-stream",
                    key="download_backup"
                )
                
                st.success(f"Database backup created successfully! Click the download button to save it.")
            except Exception as e:
                st.error(f"Failed to create backup: {str(e)}")
    
    # Restore Button
    with col2:
        st.subheader("Restore Database")
        
        # File uploader for custom backup files
        uploaded_file = st.file_uploader("Upload a backup file", type=["db"])
        
        # Option for using existing backups
        st.write("Or select from existing backups:")
        
        # Get list of backup files
        backup_files = db.list_backup_files()
        
        if backup_files or uploaded_file:
            # Extract filenames for display
            if backup_files:
                backup_filenames = [os.path.basename(path) for path in backup_files]
                
                # Create a selectbox for choosing backup files
                selected_backup = st.selectbox(
                    "Select a backup to restore",
                    options=backup_filenames,
                    format_func=lambda x: x.replace("pydomoro_backup_", "").replace(".db", " ")
                )
            
            # Get the full path of the selected backup
            selected_backup_path = next((path for path in backup_files if os.path.basename(path) == selected_backup), None) if backup_files else None
            
            if st.button("🔄 Restore Database", use_container_width=True):
                if uploaded_file:
                    # Save the uploaded file first
                    uploaded_path = db.save_uploaded_backup(uploaded_file)
                    success, message = db.restore_database(uploaded_path)
                    if success:
                        st.success(f"{message}")
                    else:
                        st.error(f"{message}")
                elif selected_backup_path:
                    success, message = db.restore_database(selected_backup_path)
                    if success:
                        st.success(f"{message}")
                    else:
                        st.error(f"{message}")
                else:
                    st.error("No backup file selected or uploaded")
        else:
            st.info("No backup files available for restore")

# Tab 2: Focus Timer
with tab2:
    st.title("🎯 Focus Time")
    
    # Activity type selection
    activity_types = ["Work", "Study", "Class", "Other"]
    selected_activity = st.selectbox(
        "Select activity type:",
        options=activity_types,
        index=activity_types.index(st.session_state.activity_type) if st.session_state.activity_type in activity_types else 0
    )
    st.session_state.activity_type = selected_activity
    
    # Mode selection: Timer or Stopwatch
    col1, col2 = st.columns(2)
    with col1:
        if st.button("⏱️ Timer", 
                    use_container_width=True, 
                    type="primary" if st.session_state.mode == "timer" else "secondary"):
            st.session_state.mode = "timer"
            st.rerun()
            
    with col2:
        if st.button("⏲️ Stopwatch", 
                    use_container_width=True, 
                    type="primary" if st.session_state.mode == "stopwatch" else "secondary"):
            st.session_state.mode = "stopwatch"
            st.rerun()
            
    
    
    st.divider()
    
    # Timer mode
    if st.session_state.mode == "timer":
        col1, col2 = st.columns([3, 1])
        
        with col1:
            duration = st.slider(
                "Duration (minutes):",
                min_value=1,
                max_value=120,
                value=st.session_state.duration_minutes,
                step=1
            )
            st.session_state.duration_minutes = duration
        
        # Timer display
        time_display = st.empty()
        
        # Timer controls
        col1, col2, col3 = st.columns(3)
        
        with col1:
            start_button = st.button(
                "▶️ Start", 
                key="timer_start",
                use_container_width=True,
                disabled=st.session_state.timer.running and not st.session_state.timer.paused
            )
        
        with col2:
            pause_resume_button = st.button(
                "⏸️ Pause" if st.session_state.timer.running and not st.session_state.timer.paused else "⏯️ Resume",
                key="timer_pause",
                use_container_width=True,
                disabled=not st.session_state.timer.running
            )
        
        with col3:
            stop_button = st.button(
                "⏹️ Stop",
                key="timer_stop",
                use_container_width=True,
                disabled=not st.session_state.timer.running
            )
        
        # Timer notification
        if st.session_state.timer_completed:
            st.success("Timer completed! Time to take a break.")
            if st.button("Dismiss"):
                st.session_state.timer_completed = False
                st.rerun()

        # Handle button actions
        if start_button:
            # First check if there's already a timer state in the database
            existing_state = db.get_timer_state()
            if existing_state:
                st.warning("You already have an active timer session. Please stop it first.")
                st.rerun()
                
            # Store in database
            st.session_state.session_id = db.start_session(st.session_state.activity_type)
            # Start timer with callback for notification
            st.session_state.timer.start(
                duration_minutes=st.session_state.duration_minutes,
                callback=timer_callback
            )
            
            # Save timer state for persistence
            db.save_timer_state(
                st.session_state.timer,
                st.session_state.mode,
                st.session_state.activity_type,
                st.session_state.duration_minutes,
                st.session_state.session_id
            )
            st.rerun()
            
        if pause_resume_button:
            if st.session_state.timer.paused:
                st.session_state.timer.resume()
            else:
                st.session_state.timer.pause()
                
            # Update timer state in database
            db.save_timer_state(
                st.session_state.timer,
                st.session_state.mode,
                st.session_state.activity_type,
                st.session_state.duration_minutes,
                st.session_state.session_id
            )
            st.rerun()
            
        if stop_button:
            elapsed_time = st.session_state.timer.stop()
            if st.session_state.session_id:
                db.end_session(st.session_state.session_id)
                st.session_state.session_id = None
            st.session_state.timer = Timer()  # Reset timer
            
            # Clear timer state from database
            db.clear_timer_state()
            st.rerun()
        
        # Display time
        if st.session_state.timer.running:
            while st.session_state.timer.running:
                # Display remaining time for timer mode
                remaining_seconds = st.session_state.timer.get_remaining_time()
                formatted_time = st.session_state.timer.get_formatted_time(remaining_seconds)
                time_display.markdown(f"<h1 style='text-align: center;'>{formatted_time}</h1>", unsafe_allow_html=True)
                
                # Display progress bar
                progress = 1 - (remaining_seconds / (st.session_state.duration_minutes * 60))
                st.progress(min(1.0, max(0.0, progress)))
                
                # Check if timer completed
                if st.session_state.timer_completed:
                    break
                    
                time.sleep(0.1)
        else:
            # Display the duration when not running
            formatted_time = st.session_state.timer.get_formatted_time(st.session_state.duration_minutes * 60)
            time_display.markdown(f"<h1 style='text-align: center;'>{formatted_time}</h1>", unsafe_allow_html=True)
            st.progress(0.0)
    
    # Stopwatch mode
    else:
        # Stopwatch display
        time_display = st.empty()
        
        # Stopwatch controls
        col1, col2, col3 = st.columns(3)
        
        with col1:
            start_button = st.button(
                "▶️ Start", 
                key="stopwatch_start",
                use_container_width=True,
                disabled=st.session_state.timer.running and not st.session_state.timer.paused
            )
        
        with col2:
            pause_resume_button = st.button(
                "⏸️ Pause" if st.session_state.timer.running and not st.session_state.timer.paused else "⏯️ Resume",
                key="stopwatch_pause",
                use_container_width=True,
                disabled=not st.session_state.timer.running
            )
        
        with col3:
            stop_button = st.button(
                "⏹️ Stop",
                key="stopwatch_stop",
                use_container_width=True,
                disabled=not st.session_state.timer.running
            )
        
        # Handle button actions
        if start_button:
            # First check if there's already a timer state in the database
            existing_state = db.get_timer_state()
            if existing_state:
                st.warning("You already have an active timer session. Please stop it first.")
                st.rerun()
                
            # Store in database
            st.session_state.session_id = db.start_session(st.session_state.activity_type)
            # Start timer (stopwatch mode, no duration)
            st.session_state.timer.start()
            
            # Save timer state for persistence
            db.save_timer_state(
                st.session_state.timer,
                st.session_state.mode,
                st.session_state.activity_type,
                None,  # No duration for stopwatch
                st.session_state.session_id
            )
            st.rerun()
            
        if pause_resume_button:
            if st.session_state.timer.paused:
                st.session_state.timer.resume()
            else:
                st.session_state.timer.pause()
                
            # Update timer state in database
            db.save_timer_state(
                st.session_state.timer,
                st.session_state.mode,
                st.session_state.activity_type,
                None,  # No duration for stopwatch
                st.session_state.session_id
            )
            st.rerun()
            
        if stop_button:
            elapsed_time = st.session_state.timer.stop()
            if st.session_state.session_id:
                db.end_session(st.session_state.session_id)
                st.session_state.session_id = None
            st.session_state.timer = Timer()  # Reset timer
            
            # Clear timer state from database
            db.clear_timer_state()
            st.rerun()
        
        # Display time
        if st.session_state.timer.running:
            while st.session_state.timer.running:
                # Display elapsed time for stopwatch mode
                elapsed_seconds = st.session_state.timer.get_elapsed_time()
                formatted_time = st.session_state.timer.get_formatted_time(elapsed_seconds)
                time_display.markdown(f"<h1 style='text-align: center;'>{formatted_time}</h1>", unsafe_allow_html=True)
                time.sleep(0.1)
        else:
            # Display 00:00:00 when not running
            time_display.markdown("<h1 style='text-align: center;'>00:00:00</h1>", unsafe_allow_html=True)

