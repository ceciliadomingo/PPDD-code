import os
from PIL import Image


def crop_image(folder_path, pixels_to_crop, area_to_crop):
	default_dpi = 300  # Used if image has no DPI info
	for filename in os.listdir(folder_path):
		if filename.lower().endswith(".png"):
			file_path = os.path.join(folder_path, filename)
			
			with Image.open(file_path) as img:
				# Get DPI (fallback if not present)
				dpi = img.info.get("dpi", (default_dpi, default_dpi))[0]
				width, height = img.size
				
				# Prevent over-cropping
				if pixels_to_crop >= height and area_to_crop == "top":
					print(f"Skipping {filename} (crop larger than image height)")
					continue
				if pixels_to_crop >= width and area_to_crop == "right":
					print(f"Skipping {filename} (crop larger than image width)")
					continue
				if pixels_to_crop >= width and area_to_crop == "left":
					print(f"Skipping {filename} (crop larger than image width)")
					continue
				if pixels_to_crop >= height and area_to_crop == "bottom":
					print(f"Skipping {filename} (crop larger than image height)")
					continue
				
				# Crop (left, top, right, bottom)
				if area_to_crop == "top":
					cropped_img = img.crop((0, pixels_to_crop, width, height))
				elif area_to_crop == "right":
					cropped_img = img.crop((0, 0, width - pixels_to_crop, height))
				elif area_to_crop == "left":
					cropped_img = img.crop((pixels_to_crop, 0, width, height))
				elif area_to_crop == "bottom":
					cropped_img = img.crop((0, 0, width, height - pixels_to_crop))
				
				# Save (overwrite original)
				cropped_img.save(file_path, dpi=(dpi, dpi))
	print("Done!")



if __name__ == "__main__":
	# === SETTINGS ===
	folder_path = 'path/to/folder/with/screenshots'
	pixels_to_crop = 120
	area_to_crop = "top"  # Options: "top", "right", "left", "bottom"
	crop_image(folder_path, pixels_to_crop, area_to_crop)