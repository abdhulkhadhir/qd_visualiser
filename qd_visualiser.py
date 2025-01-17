# -*- coding: utf-8 -*-
"""
Created on Fri Nov 22 11:24:33 2024

@author: seyedhyd
"""

import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from datetime import datetime
import numpy as np
import time

def load_and_process_data(uploaded_file):
    """Load the CSV file without processing."""
    try:
        df = pd.read_csv(uploaded_file)
        return df
    except Exception as e:
        st.error(f"Error loading file: {str(e)}")
        return None

def process_selected_columns(df, column_config):
    """Process the dataframe with selected columns and filters."""
    try:
        # Rename columns according to selection
        df = df.rename(columns={
            column_config['datetime']: 'datetime',
            column_config['speed']: 'speed',
            column_config['occupancy']: 'occupancy'
        })
        
        # Convert datetime column
        df['datetime'] = pd.to_datetime(df['datetime'], errors='coerce')

        # Drop rows with invalid datetime
        df = df.dropna(subset=['datetime'])

        # Ensure datetime consistency
        if df['datetime'].dt.tz is not None:  # If timezone-aware
            start_datetime = pd.Timestamp(column_config['start_datetime']).tz_localize(df['datetime'].dt.tz)
            end_datetime = pd.Timestamp(column_config['end_datetime']).tz_localize(df['datetime'].dt.tz)
        else:  # If timezone-naive
            start_datetime = pd.Timestamp(column_config['start_datetime'])
            end_datetime = pd.Timestamp(column_config['end_datetime'])

        # Add flow column if selected
        if column_config.get('flow'):
            df = df.rename(columns={column_config['flow']: 'flow'})
        
        # Filter by detector if selected
        if column_config.get('detector') and column_config.get('selected_detector'):
            df = df[df[column_config['detector']] == column_config['selected_detector']]
        
        # Filter by date and time range
        df = df[(df['datetime'] >= start_datetime) & (df['datetime'] <= end_datetime)]
            
        return df
    except Exception as e:
        st.error(f"Error processing data: {str(e)}")
        return None

def create_fundamental_diagram(df, activation_thresholds, deactivation_thresholds, consecutive_intervals, activation_logic='AND', deactivation_logic='OR', current_index=None):
    """Create the fundamental diagram with color-coded points and configurable logic operators."""
    fig = go.Figure()
    max_occupancy = 100
    max_speed = 100

    # Add activation regions based on logic
    if activation_logic == 'AND':
        # Single region for AND condition
        x_activation = [activation_thresholds['occupancy'], max_occupancy]
        y_activation = [0, 0]
        y_activation2 = [activation_thresholds['speed'], activation_thresholds['speed']]

        fig.add_trace(go.Scatter(
            x=x_activation + x_activation[::-1],
            y=y_activation + y_activation2[::-1],
            fill='toself',
            fillcolor='rgba(255, 0, 0, 1)',
            line=dict(width=0),
            name='Activation Region (AND)',
            showlegend=True
        ))
    else:  # OR condition
        # Horizontal region for speed
        x_act_or = [0, max_occupancy, max_occupancy, activation_thresholds['occupancy'], activation_thresholds['occupancy'], 0]
        y_act_or = [0, 0, max_speed, max_speed, activation_thresholds['speed'], activation_thresholds['speed']]
        # x_speed = [0, max_occupancy]
        # y_speed = [0, 0]
        # y_speed2 = [activation_thresholds['speed'], activation_thresholds['speed']]

        fig.add_trace(go.Scatter(
            x=x_act_or,
            y=y_act_or,
            fill='toself',
            fillcolor='rgba(255, 0, 0, 1.0)',
            line=dict(width=0),
            name='Activation Region (OR)',
            showlegend=True
        ))

        # # Vertical region for occupancy
        # x_occupancy = [activation_thresholds['occupancy'], activation_thresholds['occupancy']]
        # y_occupancy = [0, 100]
        # x_occupancy2 = [50, 50]
        # y_occupancy2 = [0, 100]

        # fig.add_trace(go.Scatter(
        #     x=x_occupancy + x_occupancy2[::-1],
        #     y=y_occupancy + y_occupancy2[::-1],
        #     fill='toself',
        #     fillcolor='rgba(255, 0, 0, 0.5)',
        #     line=dict(width=0),
        #     showlegend=False
        # ))

    # Add deactivation regions based on logic
    if deactivation_logic == 'AND':
        # Single region for AND condition (complement of OR region)
        x_deact_and = [0, deactivation_thresholds['occupancy'],  deactivation_thresholds['occupancy'], 0]
        y_deact_and = [deactivation_thresholds['speed'], deactivation_thresholds['speed'], 
                   max_speed, max_speed]

        fig.add_trace(go.Scatter(
            x=x_deact_and,
            y=y_deact_and,
            fill='toself',
            fillcolor='rgba(0, 255, 0, 1.0)',
            line=dict(width=0),
            name='Deactivation Region (AND)',
            showlegend=True
        ))
    else:  # OR condition
        # Horizontal region
        x_deact_h = [0, max_occupancy]
        y_deact_h = [deactivation_thresholds['speed'], deactivation_thresholds['speed']]
        y_deact_h2 = [max_speed, max_speed]

        fig.add_trace(go.Scatter(
            x=x_deact_h + x_deact_h[::-1],
            y=y_deact_h + y_deact_h2[::-1],
            fill='toself',
            fillcolor='rgba(0, 255, 0, 1.0)',
            line=dict(width=0),
            name='Deactivation Region (OR)',
            showlegend=True
        ))

        # Vertical region
        x_deact_v = [0, deactivation_thresholds['occupancy']]
        y_deact_v = [0, 0]
        y_deact_v2 = [max_speed, max_speed]

        fig.add_trace(go.Scatter(
            x=x_deact_v + x_deact_v[::-1],
            y=y_deact_v + y_deact_v2[::-1],
            fill='toself',
            fillcolor='rgba(0, 255, 0, 1.0)',
            line=dict(width=0),
            showlegend=False
        ))

    # Add data points
    if len(df) > 0:
        # Update activation/deactivation conditions based on selected logic
        if activation_logic == 'AND':
            df['activation'] = (df['speed'] <= activation_thresholds['speed']) & \
                             (df['occupancy'] >= activation_thresholds['occupancy'])
        else:  # OR
            df['activation'] = (df['speed'] <= activation_thresholds['speed']) | \
                             (df['occupancy'] >= activation_thresholds['occupancy'])

        if deactivation_logic == 'AND':
            df['deactivation'] = (df['speed'] >= deactivation_thresholds['speed']) & \
                                (df['occupancy'] <= deactivation_thresholds['occupancy'])
        else:  # OR
            df['deactivation'] = (df['speed'] >= deactivation_thresholds['speed']) | \
                                (df['occupancy'] <= deactivation_thresholds['occupancy'])

        activation_streak = 0

        for idx in range(len(df)):
            if df['activation'].iloc[idx]:
                activation_streak += 1
                if activation_streak == 1:
                    color = 'yellow'
                elif activation_streak >= consecutive_intervals:
                    color = 'red'
                else:
                    color = 'yellow'
            elif df['deactivation'].iloc[idx]:
                activation_streak = 0
                color = 'green'
            else:
                activation_streak = 0
                color = 'green'

            size = 10
            opacity = 0.9 if idx == current_index else 0.6

            fig.add_trace(go.Scatter(
                x=[df['occupancy'].iloc[idx]],
                y=[df['speed'].iloc[idx]],
                mode='markers',
                marker=dict(
                    size=size,
                    color=color,
                    opacity=opacity
                ),
                name=f"Point {idx + 1}" if idx == current_index else None,
                showlegend=False
            ))

    # Update layout
    fig.update_layout(
        title='Speed-Occupancy Fundamental Diagram',
        xaxis_title='Occupancy (%)',
        yaxis_title='Speed (km/h)',
        xaxis_range=[0, 75],
        yaxis_range=[0, 100],
        height=600,
        showlegend=True
    )

    return fig

def main():
    st.set_page_config(page_title="Traffic Fundamental Diagram", layout="wide")
    
    st.title("Interactive Traffic Fundamental Diagram")
    
    # Sidebar for controls
    st.sidebar.header("Data Configuration")
    
    # File uploader
    uploaded_file = st.sidebar.file_uploader("Upload CSV file", type="csv")
    
    # Initialize session state
    if 'raw_df' not in st.session_state:
        st.session_state.raw_df = None
    if 'processed_df' not in st.session_state:
        st.session_state.processed_df = None
    if 'play' not in st.session_state:
        st.session_state.play = False
    if 'current_index' not in st.session_state:
        st.session_state.current_index = 0
    if 'animation_speed' not in st.session_state:
        st.session_state.animation_speed = 0.5  # Default animation speed in seconds

    # Process uploaded file
    if uploaded_file is not None:
        st.session_state.raw_df = load_and_process_data(uploaded_file)
    
    # Column selection and data processing
    if st.session_state.raw_df is not None:
        available_columns = st.session_state.raw_df.columns.tolist()
        
        st.sidebar.subheader("Column Selection")
        datetime_col = st.sidebar.selectbox(
            "Select DateTime column",
            available_columns,
            index=next((i for i, col in enumerate(available_columns) if 'time' in col.lower() or 'date' in col.lower()), 0)
        )
        
        speed_col = st.sidebar.selectbox(
            "Select Speed column",
            available_columns,
            index=next((i for i, col in enumerate(available_columns) if 'speed' in col.lower()), 0)
        )
        
        occupancy_col = st.sidebar.selectbox(
            "Select Occupancy column",
            available_columns,
            index=next((i for i, col in enumerate(available_columns) if 'occup' in col.lower()), 0)
        )
        
        flow_col = st.sidebar.selectbox(
            "Select Flow column (optional)",
            ['None'] + available_columns,
            index=next((i + 1 for i, col in enumerate(available_columns) if 'flow' in col.lower()), 0)
        )
        
        # Detector selection
        detector_col = st.sidebar.selectbox(
            "Select Detector column (optional)",
            ['None'] + available_columns,
            index=next((i + 1 for i, col in enumerate(available_columns) if 'detector' in col.lower() or 'id' in col.lower()), 0)
        )
        
        selected_detector = None
        if detector_col != 'None':
            selected_detector = st.sidebar.selectbox(
                "Select Detector",
                sorted(st.session_state.raw_df[detector_col].unique())
            )
        
        # Date and Time range selection
        st.sidebar.subheader("Date and Time Range Filter")
        
        # Convert to datetime for min/max values
        min_datetime = pd.to_datetime(st.session_state.raw_df[datetime_col].min())
        max_datetime = pd.to_datetime(st.session_state.raw_df[datetime_col].max())
        
        # Date and Time selection in columns
        col1, col2 = st.sidebar.columns(2)
        
        with col1:
            start_date = st.date_input(
                "Start Date",
                value=min_datetime.date(),
                min_value=min_datetime.date(),
                max_value=max_datetime.date()
            )
            
            start_time = st.time_input(
                "Start Time",
                value=min_datetime.time()
            )
        
        with col2:
            end_date = st.date_input(
                "End Date",
                value=max_datetime.date(),
                min_value=min_datetime.date(),
                max_value=max_datetime.date()
            )
            
            end_time = st.time_input(
                "End Time",
                value=max_datetime.time()
            )
      
        # Combine date and time into datetime objects
        start_datetime = pd.Timestamp.combine(start_date, start_time)
        end_datetime = pd.Timestamp.combine(end_date, end_time)
        
        # Add warning if end datetime is before start datetime
        if end_datetime < start_datetime:
            st.sidebar.warning("Warning: End datetime is before start datetime!")
        
        # Animation speed control
        st.sidebar.subheader("Animation Speed")
        st.session_state.animation_speed = st.sidebar.slider("Animation Speed (seconds)", min_value=0.1, max_value=5.0, value=0.5)
        
        # Threshold controls
        st.sidebar.header("Threshold Controls")
    
        # Add logic operator selection
        activation_logic = st.sidebar.selectbox(
            "Activation Logic",
            options=['AND', 'OR'],
            help="AND: Both conditions must be met; OR: Either condition must be met"
        )
        
        deactivation_logic = st.sidebar.selectbox(
            "Deactivation Logic",
            options=['OR', 'AND'],
            help="AND: Both conditions must be met; OR: Either condition must be met"
        )
        
        activation_speed = st.sidebar.number_input("Activation Speed (km/h)", 0.0, 80.0, 45.0)
        activation_occupancy = st.sidebar.number_input("Activation Occupancy (%)", 0.0, 50.0, 25.0)
        deactivation_speed = st.sidebar.number_input("Deactivation Speed (km/h)", 0.0, 80.0, 52.0)
        deactivation_occupancy = st.sidebar.number_input("Deactivation Occupancy (%)", 0.0, 50.0, 20.0)
    
        
        # Add Consecutive Intervals parameter
        consecutive_intervals = st.sidebar.number_input("Consecutive Intervals", value=4, min_value=1)
        
        # Process data with selected columns and filters
        column_config = {
            'datetime': datetime_col,
            'speed': speed_col,
            'occupancy': occupancy_col,
            'start_datetime': start_datetime,
            'end_datetime': end_datetime
        }
        if flow_col != 'None':
            column_config['flow'] = flow_col
        if detector_col != 'None':
            column_config['detector'] = detector_col
            column_config['selected_detector'] = selected_detector
        
        st.session_state.processed_df = process_selected_columns(
            st.session_state.raw_df,
            column_config
        )
        
        # Main content area
        col1, col2, col3 = st.columns([1, 2, 1])
        
        with col1:
            if st.button("Play/Pause"):
                st.session_state.play = not st.session_state.play
        
        with col2:
            if st.session_state.processed_df is not None:
                st.markdown(f"Showing point {st.session_state.current_index + 1} of {len(st.session_state.processed_df)}")
        
        with col3:
            if st.button("Reset"):
                st.session_state.current_index = 0
                st.session_state.play = False
        
        # Create and display the plot
        if st.session_state.processed_df is not None:
            fig = create_fundamental_diagram(
                st.session_state.processed_df.iloc[:st.session_state.current_index + 1],
                {'speed': activation_speed, 'occupancy': activation_occupancy},
                {'speed': deactivation_speed, 'occupancy': deactivation_occupancy},
                consecutive_intervals,
                activation_logic,
                deactivation_logic
            )
            st.plotly_chart(fig, use_container_width=True)
            
            # Animation logic
            if st.session_state.play:
                if st.session_state.current_index < len(st.session_state.processed_df) - 1:
                    time.sleep(st.session_state.animation_speed)
                    st.session_state.current_index += 1
                else:
                    st.session_state.play = False
                st.rerun()


if __name__ == "__main__":
    main()