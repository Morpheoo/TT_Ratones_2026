import streamlit as st
import cv2
import tempfile
import os
import pandas as pd
from src.analysis.detector import RodentDetector
from src.analysis.behavior import BehaviorAnalyzer
from src.database.manager import db_manager, Video, AnalysisResult
from src.ui.visuals import plot_heatmap, plot_trajectory

# Page Config
st.set_page_config(
    page_title="TT Ratones 2026 - EPM Analysis",
    page_icon="🐁",
    layout="wide",
    initial_sidebar_state="expanded"
)

def save_uploaded_file(uploaded_file):
    try:
        with tempfile.NamedTemporaryFile(delete=False, suffix='.mp4') as tmp_file:
            tmp_file.write(uploaded_file.getvalue())
            return tmp_file.name
    except Exception as e:
        st.error(f"Error saving file: {e}")
        return None

def process_video(video_path):
    detector = RodentDetector()
    analyzer = BehaviorAnalyzer()
    
    cap = cv2.VideoCapture(video_path)
    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    fps = cap.get(cv2.CAP_PROP_FPS)
    
    st_frame = st.empty()
    progress_bar = st.progress(0)
    
    trajectories = []
    speeds = []
    
    frame_idx = 0
    
    while cap.isOpened():
        ret, frame = cap.read()
        if not ret:
            break
            
        # Process every Nth frame for performance
        if frame_idx % 2 == 0:
            detections = detector.detect(frame)
            
            # Draw detections
            for d in detections:
                box = d['box']
                x1, y1, x2, y2 = map(int, box)
                cv2.rectangle(frame, (x1, y1), (x2, y2), (0, 255, 0), 2)
                trajectories.append(d['center'])
            
            # Show processed video
            frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            st_frame.image(frame, channels="RGB", use_container_width=True)
            
        progress_bar.progress(min(frame_idx / total_frames, 1.0))
        frame_idx += 1
        
    cap.release()
    progress_bar.empty()
    
    # Analyze results
    total_dist, avg_speed, calculated_speeds = analyzer.calculate_metrics(trajectories)
    behavior_stats = analyzer.classify_behaviors(calculated_speeds)
    
    return {
        "trajectories": trajectories,
        "total_distance": total_dist,
        "avg_speed": avg_speed,
        "behavior_stats": behavior_stats
    }

def main():
    st.title("🐁 TT Ratones 2026: EPM Behavior Analysis")
    st.markdown("### Automated analysis of rodent behavior in Elevated Plus Maze")
    
    with st.sidebar:
        st.header("Project Controls")
        nav_mode = st.radio("Navigation", ["Upload & Analyze", "History / Database", "Settings"])
        
    if nav_mode == "Upload & Analyze":
        st.subheader("Upload Experiment Video")
        uploaded_video = st.file_uploader("Choose a video file...", type=["mp4", "avi", "mov"])
        
        if uploaded_video is not None:
            st.video(uploaded_video)
            
            if st.button("Start Analysis"):
                with st.spinner("Processing video... This may take a while based on GPU availability."):
                    tfile = save_uploaded_file(uploaded_video)
                    if tfile:
                        results = process_video(tfile)
                        st.success("Analysis Complete!")
                        
                        # Display Metrics
                        col1, col2, col3 = st.columns(3)
                        col1.metric("Total Distance", f"{results['total_distance']:.2f} px")
                        col2.metric("Avg Speed", f"{results['avg_speed']:.2f} px/s")
                        immobility = results['behavior_stats'].get('immobility_percentage', 0)
                        col3.metric("Immobility %", f"{immobility:.1f}%")
                        
                        # Display Visuals
                        tab1, tab2 = st.tabs(["Trajectory", "Heatmap"])
                        
                        with tab1:
                            fig_traj = plot_trajectory(results['trajectories'])
                            if fig_traj:
                                st.pyplot(fig_traj)
                        
                        with tab2:
                            fig_heat = plot_heatmap(results['trajectories'])
                            if fig_heat:
                                st.pyplot(fig_heat)

                        # Save to DB (Quick Stub)
                        # session = db_manager.get_session()
                        # ... save logic here ...
                        # session.close()
                        
                        os.unlink(tfile) # Cleanup

    elif nav_mode == "History / Database":
        st.info("Database History feature coming soon.")
        
    elif nav_mode == "Settings":
        st.write("Configuration parameters.")

if __name__ == "__main__":
    main()
