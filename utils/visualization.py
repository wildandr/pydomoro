import pandas as pd
import matplotlib.pyplot as plt
import streamlit as st
from datetime import datetime, timedelta
import numpy as np

def create_daily_distribution_chart(sessions_data):
    """
    Create a chart showing distribution of focus time throughout the day
    """
    if not sessions_data:
        return None
        
    # Convert sessions data to DataFrame
    df = pd.DataFrame(sessions_data, columns=['activity_type', 'start_time', 'end_time', 'duration_minutes'])
    
    # Convert strings to datetime if needed
    for col in ['start_time', 'end_time']:
        if df[col].dtype == 'object':
            df[col] = pd.to_datetime(df[col])
    
    # Prepare 24-hour time slots
    hours = list(range(24))
    activity_types = df['activity_type'].unique()
    hour_data = {activity: [0] * 24 for activity in activity_types}
    
    # Distribute time into hourly buckets
    for _, session in df.iterrows():
        if pd.isna(session['end_time']) or pd.isna(session['start_time']):
            continue
            
        start = session['start_time']
        end = session['end_time']
        duration = session['duration_minutes']
        activity = session['activity_type']
        
        # Distribute the time across hours
        current_time = start
        while current_time < end:
            hour = current_time.hour
            next_hour = (current_time + timedelta(hours=1)).replace(minute=0, second=0, microsecond=0)
            
            # Time spent in this hour (in minutes)
            if next_hour > end:
                time_in_hour = (end - current_time).total_seconds() / 60
            else:
                time_in_hour = (next_hour - current_time).total_seconds() / 60
                
            hour_data[activity][hour] += time_in_hour
            current_time = next_hour
    
    # Create the stacked bar chart
    fig, ax = plt.subplots(figsize=(12, 6))
    bottom = np.zeros(24)
    
    for activity, values in hour_data.items():
        ax.bar(hours, values, bottom=bottom, label=activity)
        bottom += np.array(values)
    
    ax.set_title('Focus Time Distribution Throughout the Day')
    ax.set_xlabel('Hour of Day')
    ax.set_ylabel('Minutes')
    ax.set_xticks(hours)
    ax.set_xticklabels([f"{h:02d}" for h in hours])
    ax.legend()
    
    return fig

def create_activity_pie_chart(activity_distribution):
    """
    Create a pie chart showing distribution of activities
    """
    if not activity_distribution:
        return None
        
    # Using pixels instead of inches (200px)
    fig, ax = plt.subplots(figsize=(200/100, 200/100))  # 200px converted to inches (dpi=100)
    activities = list(activity_distribution.keys())
    minutes = list(activity_distribution.values())
    
    ax.pie(minutes, labels=activities, autopct='%1.1f%%', startangle=90)
    ax.axis('equal')
    ax.set_title('Focus Time by Activity')
    
    return fig

def create_period_comparison_chart(db_manager, period_type, periods=7):
    """
    Create a chart comparing focus time across multiple periods
    """
    today = datetime.now()
    
    if period_type == 'day':
        labels = [(today - timedelta(days=i)).strftime('%a %d') for i in range(periods-1, -1, -1)]
        dates = [(today - timedelta(days=i)) for i in range(periods-1, -1, -1)]
    elif period_type == 'week':
        labels = []
        dates = []
        for i in range(periods-1, -1, -1):
            start_of_week = today - timedelta(days=today.weekday() + 7*i)
            end_of_week = start_of_week + timedelta(days=6)
            labels.append(f"{start_of_week.strftime('%b %d')} - {end_of_week.strftime('%b %d')}")
            dates.append(start_of_week)
    elif period_type == 'month':
        labels = []
        dates = []
        for i in range(periods-1, -1, -1):
            month = (today.month - i - 1) % 12 + 1
            year = today.year - ((today.month - i - 1) // 12)
            labels.append(datetime(year, month, 1).strftime('%b %Y'))
            dates.append(datetime(year, month, 1))
    elif period_type == 'year':
        labels = [(today.year - i) for i in range(periods-1, -1, -1)]
        dates = [datetime(today.year - i, 1, 1) for i in range(periods-1, -1, -1)]
    
    # Get data for each period
    totals = []
    for date in dates:
        total = db_manager.get_total_focus_time(period_type, date)
        totals.append(total)
    
    # Create the bar chart
    fig, ax = plt.subplots(figsize=(12, 6))
    ax.bar(labels, totals)
    ax.set_title(f'Focus Time by {period_type.capitalize()}')
    ax.set_ylabel('Minutes')
    
    if period_type == 'day':
        ax.set_xlabel('Day')
    elif period_type == 'week':
        ax.set_xlabel('Week')
    elif period_type == 'month':
        ax.set_xlabel('Month')
    elif period_type == 'year':
        ax.set_xlabel('Year')
    
    plt.xticks(rotation=45)
    plt.tight_layout()
    
    return fig