import time
import threading
from datetime import datetime, timedelta
import pytz

# Define Indonesian Western Time timezone
WIB = pytz.timezone('Asia/Jakarta')

class Timer:
    def __init__(self):
        self.running = False
        self.paused = False
        self.start_time = None
        self.elapsed_time = 0
        self.target_time = None
        self.timer_thread = None
        self.callback = None
        self.stop_event = threading.Event()
        
    def start(self, duration_minutes=None, callback=None):
        """Start the timer, optionally with a target duration"""
        if self.running:
            return
            
        self.running = True
        self.paused = False
        self.start_time = datetime.now(WIB)
        
        if duration_minutes:
            self.target_time = self.start_time + timedelta(minutes=duration_minutes)
            self.callback = callback
            
            # Start a thread to check for target time
            self.stop_event.clear()
            self.timer_thread = threading.Thread(target=self._check_target)
            self.timer_thread.daemon = True
            self.timer_thread.start()
    
    def restore_from_state(self, timer_state, callback=None):
        """Restore timer from a saved state"""
        self.running = True
        self.paused = timer_state["paused"]
        self.elapsed_time = timer_state["elapsed_time_seconds"]
        
        # If the timer was not paused, calculate the new start_time 
        # by subtracting the elapsed time from the current time
        if not self.paused:
            if isinstance(timer_state["start_time"], str):
                self.start_time = datetime.fromisoformat(timer_state["start_time"].replace('Z', '+00:00'))
            else:
                self.start_time = timer_state["start_time"]
        else:
            self.start_time = datetime.now(WIB)
        
        # If we have a duration, set up the target time
        if timer_state["duration_minutes"]:
            duration_minutes = timer_state["duration_minutes"]
            
            # If not paused, calculate remaining time and set a new target
            if not self.paused:
                elapsed_seconds = self.elapsed_time
                if self.start_time:
                    elapsed_seconds += (datetime.now(WIB) - self.start_time).total_seconds()
                
                remaining_minutes = max(0, duration_minutes - (elapsed_seconds / 60))
                self.target_time = datetime.now(WIB) + timedelta(minutes=remaining_minutes)
            else:
                # If paused, set target based on the elapsed time
                remaining_minutes = max(0, duration_minutes - (self.elapsed_time / 60))
                self.target_time = datetime.now(WIB) + timedelta(minutes=remaining_minutes)
            
            self.callback = callback
            
            # Start a thread to check for target time
            if not self.paused:
                self.stop_event.clear()
                self.timer_thread = threading.Thread(target=self._check_target)
                self.timer_thread.daemon = True
                self.timer_thread.start()
    
    def _check_target(self):
        """Check if the target time has been reached"""
        while not self.stop_event.is_set():
            if self.running and not self.paused and datetime.now(WIB) >= self.target_time:
                if self.callback:
                    self.callback()
                break
            time.sleep(0.1)
    
    def pause(self):
        """Pause the timer"""
        if self.running and not self.paused:
            self.paused = True
            self.elapsed_time += (datetime.now(WIB) - self.start_time).total_seconds()
    
    def resume(self):
        """Resume the timer"""
        if self.running and self.paused:
            self.paused = False
            self.start_time = datetime.now(WIB)
    
    def stop(self):
        """Stop the timer"""
        if self.running:
            if not self.paused:
                self.elapsed_time += (datetime.now(WIB) - self.start_time).total_seconds()
            self.running = False
            self.paused = False
            
            if self.timer_thread:
                self.stop_event.set()
                self.timer_thread.join(timeout=1.0)
                
        return self.elapsed_time
    
    def reset(self):
        """Reset the timer"""
        was_running = self.running
        self.stop()
        self.elapsed_time = 0
        if was_running:
            self.start()
    
    def get_elapsed_time(self):
        """Get the elapsed time in seconds"""
        if not self.running:
            return self.elapsed_time
        
        if self.paused:
            return self.elapsed_time
            
        return self.elapsed_time + (datetime.now(WIB) - self.start_time).total_seconds()
    
    def get_remaining_time(self):
        """Get the remaining time if a target time was set"""
        if not self.target_time or not self.running:
            return 0
            
        if self.paused:
            remaining = (self.target_time - self.start_time).total_seconds() - self.elapsed_time
        else:
            remaining = (self.target_time - datetime.now(WIB)).total_seconds()
            
        return max(0, remaining)
    
    def get_formatted_time(self, seconds=None):
        """Format seconds as HH:MM:SS"""
        if seconds is None:
            if self.target_time and self.running:
                seconds = self.get_remaining_time()
            else:
                seconds = self.get_elapsed_time()
                
        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        seconds = int(seconds % 60)
        
        return f"{hours:02d}:{minutes:02d}:{seconds:02d}"