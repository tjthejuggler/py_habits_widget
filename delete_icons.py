import os
import glob

# Change this to the path of your "icons" directory
icons_dir = './icons'

# Iterate through all subdirectories
for subdir in os.listdir(icons_dir):
    subdir_path = os.path.join(icons_dir, subdir)

    # Check if it's actually a directory
    if os.path.isdir(subdir_path):
        # Use a glob pattern to find all "_.png" files in the current subdirectory
        png_files = glob.glob(os.path.join(subdir_path, '*_.png'))

        # Delete each "_.png" file
        for png_file in png_files:
            os.remove(png_file)
            print(f'Deleted file: {png_file}')
