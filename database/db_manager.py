import sqlite3
import os
from datetime import datetime, timedelta
import pytz

# Define Indonesian Western Time timezone
WIB = pytz.timezone('Asia/Jakarta')

class DBManager:
    def __init__(self):
        # Create database directory if it doesn't exist
        db_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data")
        os.makedirs(db_dir, exist_ok=True)
        
        # Connect to the database
        self.db_path = os.path.join(db_dir, "pydomoro.db")
        self.conn = sqlite3.connect(self.db_path)
        self.cursor = self.conn.cursor()
        self.create_tables()

    def create_tables(self):
        # Create focus_sessions table
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS focus_sessions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                activity_type TEXT NOT NULL,
                start_time TIMESTAMP NOT NULL,
                end_time TIMESTAMP,
                duration_minutes REAL,
                completed BOOLEAN DEFAULT FALSE
            )
        ''')
        
        # Create timer_state table for persistence
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS timer_state (
                id INTEGER PRIMARY KEY,
                mode TEXT NOT NULL,
                activity_type TEXT NOT NULL,
                start_time TIMESTAMP,
                elapsed_time_seconds REAL,
                duration_minutes REAL,
                paused BOOLEAN DEFAULT FALSE,
                session_id INTEGER,
                updated_at TIMESTAMP NOT NULL
            )
        ''')
        self.conn.commit()

    def start_session(self, activity_type):
        current_time = datetime.now(WIB)
        self.cursor.execute(
            "INSERT INTO focus_sessions (activity_type, start_time) VALUES (?, ?)",
            (activity_type, current_time)
        )
        self.conn.commit()
        return self.cursor.lastrowid

    def end_session(self, session_id, completed=True):
        end_time = datetime.now(WIB)
        
        # Get the start time
        self.cursor.execute("SELECT start_time FROM focus_sessions WHERE id = ?", (session_id,))
        start_time_str = self.cursor.fetchone()[0]
        
        if isinstance(start_time_str, str):
            start_time = datetime.fromisoformat(start_time_str.replace('Z', '+00:00'))
        else:
            start_time = start_time_str
            
        # Calculate duration in minutes
        duration = (end_time - start_time).total_seconds() / 60
        
        # Update the session record
        self.cursor.execute(
            "UPDATE focus_sessions SET end_time = ?, duration_minutes = ?, completed = ? WHERE id = ?",
            (end_time, duration, completed, session_id)
        )
        self.conn.commit()

    def get_sessions_by_period(self, period_type, date=None):
        """
        Get sessions based on period type (day, week, month, year)
        """
        if date is None:
            date = datetime.now(WIB)
            
        if period_type == 'day':
            start_date = datetime(date.year, date.month, date.day, 0, 0, 0)
            end_date = datetime(date.year, date.month, date.day, 23, 59, 59)
        elif period_type == 'week':
            # Start of week (Monday)
            start_date = date - timedelta(days=date.weekday())
            start_date = datetime(start_date.year, start_date.month, start_date.day, 0, 0, 0)
            # End of week (Sunday)
            end_date = start_date + timedelta(days=6, hours=23, minutes=59, seconds=59)
        elif period_type == 'month':
            start_date = datetime(date.year, date.month, 1, 0, 0, 0)
            # Find the last day of the month
            if date.month == 12:
                end_date = datetime(date.year + 1, 1, 1, 0, 0, 0)
            else:
                end_date = datetime(date.year, date.month + 1, 1, 0, 0, 0)
            end_date = end_date - timedelta(seconds=1)
        elif period_type == 'year':
            start_date = datetime(date.year, 1, 1, 0, 0, 0)
            end_date = datetime(date.year, 12, 31, 23, 59, 59)
            
        self.cursor.execute(
            """
            SELECT activity_type, start_time, end_time, duration_minutes 
            FROM focus_sessions 
            WHERE start_time BETWEEN ? AND ? AND completed = 1
            ORDER BY start_time
            """,
            (start_date, end_date)
        )
        return self.cursor.fetchall()

    def get_total_focus_time(self, period_type, date=None):
        """
        Get total focus time for a given period
        """
        sessions = self.get_sessions_by_period(period_type, date)
        return sum(session[3] for session in sessions if session[3] is not None)

    def get_activity_distribution(self, period_type, date=None):
        """
        Get distribution of time by activity type for a given period
        """
        sessions = self.get_sessions_by_period(period_type, date)
        distribution = {}
        for session in sessions:
            activity_type = session[0]
            duration = session[3] or 0
            if activity_type in distribution:
                distribution[activity_type] += duration
            else:
                distribution[activity_type] = duration
        return distribution

    def get_focus_vs_nonfocus_time(self):
        """
        Calculate the focus time vs. non-focus time for today (from 00:00 to current time)
        Returns a tuple of (focus_minutes, nonfocus_minutes)
        """
        # Get today's date range
        today = datetime.now(WIB)
        start_date = datetime(today.year, today.month, today.day, 0, 0, 0, tzinfo=WIB)
        
        # Calculate total elapsed minutes since midnight
        elapsed_minutes = (today - start_date).total_seconds() / 60
        
        # Get focus time for today
        focus_minutes = self.get_total_focus_time('day', today)
        
        # Calculate non-focus time
        nonfocus_minutes = max(0, elapsed_minutes - focus_minutes)
        
        return (focus_minutes, nonfocus_minutes)

    def backup_database(self):
        """
        Creates a backup of the database with timestamp.
        Returns the path to the backup file.
        """
        import shutil
        from datetime import datetime
        
        # Generate a timestamp for the backup filename in WIB timezone
        timestamp = datetime.now(WIB).strftime("%Y%m%d_%H%M%S")
        backup_filename = f"pydomoro_backup_{timestamp}.db"
        
        # Close the current connection to ensure all data is saved
        self.conn.commit()
        self.conn.close()
        
        # Create a copy of the database file
        backup_path = os.path.join(os.path.dirname(self.db_path), backup_filename)
        shutil.copy2(self.db_path, backup_path)
        
        # Reconnect to the database
        self.conn = sqlite3.connect(self.db_path)
        self.cursor = self.conn.cursor()
        
        return backup_path

    def list_backup_files(self):
        """
        List all available backup files in the data directory
        Returns a list of paths to backup files, sorted newest first
        """
        data_dir = os.path.dirname(self.db_path)
        backup_files = []
        
        for filename in os.listdir(data_dir):
            if filename.startswith("pydomoro_backup_") and filename.endswith(".db"):
                backup_path = os.path.join(data_dir, filename)
                backup_files.append(backup_path)
        
        # Sort by modification time, newest first
        backup_files.sort(key=lambda x: os.path.getmtime(x), reverse=True)
        return backup_files

    def restore_database(self, backup_path):
        """
        Restore the database from a backup file
        Returns a tuple (success, message)
        """
        import shutil
        
        try:
            # Verify the backup file exists
            if not os.path.exists(backup_path):
                return (False, f"Backup file not found: {backup_path}")
                
            # Close the current connection
            self.conn.close()
            
            # Create a backup of the current database before restoring
            current_backup = self.db_path + ".before_restore"
            shutil.copy2(self.db_path, current_backup)
            
            # Restore the backup file
            shutil.copy2(backup_path, self.db_path)
            
            # Reconnect to the database
            self.conn = sqlite3.connect(self.db_path)
            self.cursor = self.conn.cursor()
            
            return (True, f"Database restored successfully from {os.path.basename(backup_path)}")
            
        except Exception as e:
            # Try to reconnect to the original database
            try:
                self.conn = sqlite3.connect(self.db_path)
                self.cursor = self.conn.cursor()
            except:
                pass
                
            return (False, f"Failed to restore database: {str(e)}")
            
    def save_uploaded_backup(self, uploaded_file):
        """
        Save an uploaded backup file and return its path
        """
        import shutil
        
        # Generate a timestamp for the backup filename
        timestamp = datetime.now(WIB).strftime("%Y%m%d_%H%M%S")
        backup_filename = f"pydomoro_backup_{timestamp}_uploaded.db"
        
        # Save the uploaded file
        data_dir = os.path.dirname(self.db_path)
        backup_path = os.path.join(data_dir, backup_filename)
        
        # Write the uploaded file to disk
        with open(backup_path, "wb") as f:
            f.write(uploaded_file.read())
            
        return backup_path
        
    def save_timer_state(self, timer, mode, activity_type, duration_minutes, session_id):
        """
        Save the current timer state to the database for persistence
        """
        current_time = datetime.now(WIB)
        
        # Clear any existing timer state
        self.cursor.execute("DELETE FROM timer_state")
        
        # Insert new timer state
        self.cursor.execute(
            """
            INSERT INTO timer_state 
            (mode, activity_type, start_time, elapsed_time_seconds, duration_minutes, 
             paused, session_id, updated_at) 
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                mode, 
                activity_type, 
                timer.start_time, 
                timer.elapsed_time, 
                duration_minutes, 
                timer.paused, 
                session_id, 
                current_time
            )
        )
        self.conn.commit()
        
    def get_timer_state(self):
        """
        Retrieve the saved timer state from the database
        Returns None if no timer state is saved
        """
        self.cursor.execute("SELECT * FROM timer_state LIMIT 1")
        row = self.cursor.fetchone()
        
        if not row:
            return None
            
        return {
            "mode": row[1],
            "activity_type": row[2],
            "start_time": row[3],
            "elapsed_time_seconds": row[4],
            "duration_minutes": row[5],
            "paused": bool(row[6]),
            "session_id": row[7],
            "updated_at": row[8]
        }
        
    def clear_timer_state(self):
        """
        Clear the saved timer state from the database
        """
        self.cursor.execute("DELETE FROM timer_state")
        self.conn.commit()

    def __del__(self):
        if hasattr(self, 'conn') and self.conn:
            self.conn.close()