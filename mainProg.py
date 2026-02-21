from __future__ import print_function, division
import argparse
import sys
import time

import cv2
import mediapipe as mp

from mediapipe.tasks import python
from mediapipe.tasks.python import vision

# import your serial/motor helpers
from mySerCommLibrary import *  # forward(), stop(), grab(), get_distance(), handshake()

# Global variables to calculate FPS
COUNTER, FPS = 0, 0
START_TIME = time.time()


def run(model: str, max_results: int, score_threshold: float,
        camera_id: int, width: int, height: int,
        bottle_score_threshold: float = 0.6,
        grab_distance_cm: float = 12.0) -> None:
  """Continuously run inference on images acquired from the camera
     and control the robot."""

  global COUNTER, FPS, START_TIME

  # Start capturing video input from the camera
  cap = cv2.VideoCapture(camera_id)
  cap.set(cv2.CAP_PROP_FRAME_WIDTH, width)
  cap.set(cv2.CAP_PROP_FRAME_HEIGHT, height)

  if not cap.isOpened():
    sys.exit("ERROR: Could not open camera with id {}. Try a different --cameraId.".format(camera_id))

  # Visualization parameters
  row_size = 50  # pixels
  left_margin = 24  # pixels
  text_color = (0, 0, 0)  # black
  font_size = 1
  font_thickness = 1
  fps_avg_frame_count = 10

  # Label box parameters
  label_text_color = (0, 0, 0)  # black
  label_background_color = (255, 255, 255)  # white
  label_font_size = 1
  label_thickness = 2
  label_width = 50  # pixels
  label_rect_size = 16  # pixels
  label_margin = 40
  label_padding_width = 600  # pixels

  classification_frame = None
  classification_result_list = []

  # ----- distance sampling state -----
  last_distance_cm = None
  last_distance_sample_time = 0.0
  DIST_SAMPLE_PERIOD = 0.15  # seconds between distance samples

  def safe_get_distance():
    """Call get_distance() but handle errors and invalid (999-like) placeholders."""
    try:
      d = float(get_distance())
    except Exception:
      return None

    # Many ultrasonic libs use huge or 0 values for "no echo"
    if d <= 0 or d >= 900:  # treat 999 etc as invalid
      return None
    return d

  # ---------- decide what to do with each classification ----------
  def dealWithResult(category_name, score, current_distance_cm):
      """
      Robot logic:
      - If we see 'Bottle' with score >= bottle_score_threshold:
          - If distance is valid and close enough: stop and grab.
          - Else: move forward.
      - If we do NOT see a confident bottle: stop.
      """
      print("Class:", category_name, "score:", score,
            "dist:", ("None" if current_distance_cm is None else round(current_distance_cm, 1)))

      if category_name == "Bottle" and score >= bottle_score_threshold:
          # We have a bottle detection
          if current_distance_cm is not None and current_distance_cm <= grab_distance_cm:
              print("Bottle close (", current_distance_cm,
                    "cm ) -> stop and grab, then exit loop")
              stop()
              grab()
              # Returning True signals "we are done"
              return True
          else:
              # Not close enough yet: move forward
              forward()
              return False
      else:
          # No confident bottle: stop
          stop()
          return False

  def save_result(result: vision.ImageClassifierResult,
                  unused_output_image: mp.Image,
                  timestamp_ms: int):
      nonlocal classification_result_list
      global FPS, COUNTER, START_TIME

      # Calculate the FPS
      if COUNTER % fps_avg_frame_count == 0:
          FPS = fps_avg_frame_count / (time.time() - START_TIME)
          START_TIME = time.time()

      classification_result_list.append(result)
      COUNTER += 1

  # Initialize the image classification model
  base_options = python.BaseOptions(model_asset_path=model)
  options = vision.ImageClassifierOptions(
      base_options=base_options,
      running_mode=vision.RunningMode.LIVE_STREAM,
      max_results=max_results,
      score_threshold=score_threshold,
      result_callback=save_result)
  classifier = vision.ImageClassifier.create_from_options(options)

  try:
    done = False

    # Continuously capture images from the camera and run inference
    while cap.isOpened() and not done:
      success, image = cap.read()
      if not success:
        sys.exit(
            "ERROR: Unable to read from webcam. Please verify your webcam settings."
        )

      # Sample ultrasonic distance at a lower rate to avoid blocking every frame
      now = time.time()
      if now - last_distance_sample_time >= DIST_SAMPLE_PERIOD:
        last_distance_sample_time = now
        d = safe_get_distance()
        last_distance_cm = d  # can be None

      # Convert the image from BGR to RGB as required by the TFLite model.
      rgb_image = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
      mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb_image)

      # Run image classifier using the model.
      classifier.classify_async(mp_image, time.time_ns() // 1_000_000)

      # Show the FPS
      fps_text = "FPS = {:.1f}".format(FPS)
      text_location = (left_margin, row_size)
      current_frame = image
      cv2.putText(current_frame, fps_text, text_location, cv2.FONT_HERSHEY_DUPLEX,
                  font_size, text_color, font_thickness, cv2.LINE_AA)

      # Initialize the origin coordinates of the label.
      legend_x = current_frame.shape[1] + label_margin
      legend_y = current_frame.shape[0] // label_width + label_margin

      # Expand the frame to show the labels.
      current_frame = cv2.copyMakeBorder(current_frame, 0, 0, 0,
                                         label_padding_width,
                                         cv2.BORDER_CONSTANT, None,
                                         label_background_color)

      # Show the labels on right-side frame and control robot
      if classification_result_list:
        # Use the latest result only
        result = classification_result_list[-1]
        if result.classifications:
          cats = result.classifications[0].categories
          if cats:
            top_cat = cats[0]
            category_name = top_cat.category_name
            score = round(top_cat.score, 2)

            # control the robot with this result + current distance
            should_quit = dealWithResult(category_name, score, last_distance_cm)
            if should_quit:
              done = True

            # display label
            result_text = category_name + " (" + str(score) + ")"
            label_location = (legend_x + label_rect_size + label_margin,
                              legend_y + label_margin)
            cv2.putText(current_frame, result_text, label_location,
                        cv2.FONT_HERSHEY_DUPLEX, label_font_size,
                        label_text_color, label_thickness, cv2.LINE_AA)
            legend_y += (label_rect_size + label_margin)

        classification_frame = current_frame
        classification_result_list.clear()
      else:
        classification_frame = current_frame

      if classification_frame is not None:
          cv2.imshow("image_classification", classification_frame)

      # Stop the program if the ESC key is pressed.
      if cv2.waitKey(1) == 27:
          break

  finally:
    # Make sure we stop the robot when quitting
    stop()
    classifier.close()
    cap.release()
    cv2.destroyAllWindows()


def main():
  parser = argparse.ArgumentParser(
      formatter_class=argparse.ArgumentDefaultsHelpFormatter)
  parser.add_argument(
      "--model",
      help="Name of image classification model.",
      required=False,
      default="model.tflite")
  parser.add_argument(
      "--maxResults",
      help="Max number of classification results.",
      required=False,
      default=1)
  parser.add_argument(
      "--scoreThreshold",
      help="The score threshold of classification results.",
      required=False,
      type=float,
      default=0.0)
  parser.add_argument(
      "--cameraId", help="Id of camera.", required=False, default=0)
  parser.add_argument(
      "--frameWidth",
      help="Width of frame to capture from camera.",
      required=False,
      default=640)
  parser.add_argument(
      "--frameHeight",
      help="Height of frame to capture from camera.",
      required=False,
      default=480)
  parser.add_argument(
      "--bottleScore",
      help="Score threshold to move toward bottle.",
      required=False,
      type=float,
      default=0.6)
  parser.add_argument(
      "--grabDistance",
      help="Distance in cm to trigger grab.",
      required=False,
      type=float,
      default=12.0)

  args = parser.parse_args()

  # handshake with the robot before starting
  handshake()

  run(args.model,
      int(args.maxResults),
      args.scoreThreshold,
      int(args.cameraId),
      int(args.frameWidth),
      int(args.frameHeight),
      bottle_score_threshold=float(args.bottleScore),
      grab_distance_cm=float(args.grabDistance))


if __name__ == "__main__":
  main()
