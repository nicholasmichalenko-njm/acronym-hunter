"""Run a script with OpenCV swapped out for imgops (side-by-side exploration only).
Usage: python tools/no_opencv_run.py tools/evaluate.py [args...]"""
import os, runpy, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import cvshim
sys.modules["cv2"] = cvshim
script = sys.argv[1]
sys.argv = sys.argv[1:]
runpy.run_path(script, run_name="__main__")
