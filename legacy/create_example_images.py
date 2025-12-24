#!/usr/bin/env python3
"""
Create example robot images for testing
"""

from default_robot_image import create_default_robot_image
import os

def create_example_images():
    """Create some example robot images"""
    example_dir = "example_robot_images"
    
    # Create example images for different team numbers
    team_numbers = ["1234", "5678", "9999", "3333", "4567"]
    
    for team_num in team_numbers:
        img = create_default_robot_image(team_num)
        img_path = os.path.join(example_dir, f"{team_num}.png")
        img.save(img_path)
        print(f"Created image: {img_path}")

if __name__ == "__main__":
    create_example_images()
    print("Example robot images created successfully!")
