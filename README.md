# PyDomoro - A Pomodoro System using Streamlit

## Overview
This project implements a Pomodoro system using Streamlit, designed to help users manage their focus time effectively. The application allows users to track their focused activities, visualize their time distribution, and receive notifications when their focus sessions end.

## Features
- **Focus Timer Tab**: 
  - Timer and stopwatch functionalities.
  - Dropdown menu to select activities (Work, Study, Class).
  - Start, pause, and stop buttons for the timer.
  - Notifications when the timer ends.
  - Automatic tracking of focus sessions.

- **Dashboard Tab**:
  - Overview of focus time distribution
  - View statistics by day, week, month, or year
  - Interactive visualizations and charts
  - Activity breakdown and trends analysis

## Installation

1. Create a virtual environment:
   ```
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

2. Install requirements:
   ```
   pip install -r requirements.txt
   ```

3. Run the application:
   ```
   streamlit run app.py
   ```

## Usage

1. Use the "Focus Timer" tab
   - Select your activity type (Work, Study, Class)
   - Choose between Timer or Stopwatch mode
   - For Timer mode, set your desired duration
   - Use the controls to start, pause, or stop your focus session

2. View your statistics on the "Dashboard" tab
   - Select the time period (day, week, month, year)
   - See your total focus time and average statistics
   - Explore the visualizations to understand your focus patterns

## Database

The application uses SQLite to store your focus sessions. The database file is created automatically in the `data` directory.

## Project Structure
```
pydomoro
├── app.py                  # Main application file (single-page)
├── database
│   ├── __init__.py
│   └── db_manager.py       # Database operations
├── utils
│   ├── __init__.py
│   ├── timer.py            # Timer functionality
│   └── visualization.py    # Charts and visualizations
├── styles
│   └── style.css           # Custom styling
├── assets
│   └── notification.mp3    # Sound notification
├── data
│   └── pydomoro.db         # SQLite database
├── requirements.txt
└── README.md
```

## Installation
1. Clone the repository:
   ```
   git clone <repository-url>
   cd pydomoro
   ```

2. Install the required dependencies:
   ```
   pip install -r requirements.txt
   ```

## Usage
To run the application, execute the following command:
```
streamlit run app.py
```

## Dependencies
- Streamlit
- SQLite (for database management)
- Other necessary libraries as specified in `requirements.txt`

## Contributing
Contributions are welcome! Please feel free to submit a pull request or open an issue for any suggestions or improvements.

## License
This project is licensed under the MIT License. See the LICENSE file for more details.