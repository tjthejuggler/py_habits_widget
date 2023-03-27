import os
import cv2
from PIL import Image
import numpy as np

def hsv_adjustment(image, h_shift, s_scale, v_scale):
    bgr_image, alpha_channel = image[:, :, :3], image[:, :, 3]

    hsv_image = cv2.cvtColor(bgr_image, cv2.COLOR_BGR2HSV)
    h, s, v = cv2.split(hsv_image)

    h = (h + h_shift) % 180
    s = np.clip(s * s_scale, 0, 255).astype(np.uint8)
    v = np.clip(v * v_scale, 0, 255).astype(np.uint8)

    adjusted_hsv_image = cv2.merge([h, s, v])
    adjusted_bgr_image = cv2.cvtColor(adjusted_hsv_image, cv2.COLOR_HSV2BGR)
    adjusted_bgra_image = cv2.merge([adjusted_bgr_image, alpha_channel])

    return adjusted_bgra_image

def batch_process(input_folder, output_folder, h_shift, s_scale, v_scale):
    if not os.path.exists(output_folder):
        os.makedirs(output_folder)

    for file_name in os.listdir(input_folder):
        if file_name.endswith('.png'):
            input_file_path = os.path.join(input_folder, file_name)
            output_file_path = os.path.join(output_folder, file_name)

            image = cv2.imread(input_file_path, cv2.IMREAD_UNCHANGED)

            adjusted_image = hsv_adjustment(image, h_shift, s_scale, v_scale)

            cv2.imwrite(output_file_path, adjusted_image)
            print(f"Processed {input_file_path} -> {output_file_path}")

if __name__ == "__main__":
    input_folder = './drawable'
    output_folder = './shift_test_output'
    h_shift = 62  # Hue shift value (0-180), e.g., 10
    s_scale = 1.2  # Saturation scale factor, e.g., 1.5 for a 50% increase
    v_scale = 0.95  # Value (brightness) scale factor, e.g., 0.8 for a 20% decrease

    batch_process(input_folder, output_folder, h_shift, s_scale, v_scale)


#50 from bluewhitepearlhd is nice