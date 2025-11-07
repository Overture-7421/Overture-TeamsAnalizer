#!/usr/bin/env python3
"""
Create a default robot image for tier list export
"""

from PIL import Image, ImageDraw, ImageFont
import base64
import io
import os

def create_default_robot_image(team_number, size=(150, 150)):
    """Create a default robot image with team number"""
    # Create a new image with a robot-like background
    img = Image.new('RGB', size, color='#2E3440')  # Dark background
    draw = ImageDraw.Draw(img)
    
    # Draw a simple robot shape
    # Robot body (rectangle)
    body_width = size[0] * 0.6
    body_height = size[1] * 0.4
    body_x = (size[0] - body_width) / 2
    body_y = size[1] * 0.35
    
    draw.rectangle([body_x, body_y, body_x + body_width, body_y + body_height], 
                  fill='#5E81AC', outline='#88C0D0', width=2)
    
    # Robot head (smaller rectangle on top)
    head_width = size[0] * 0.4
    head_height = size[1] * 0.25
    head_x = (size[0] - head_width) / 2
    head_y = size[1] * 0.15
    
    draw.rectangle([head_x, head_y, head_x + head_width, head_y + head_height], 
                  fill='#81A1C1', outline='#88C0D0', width=2)
    
    # Robot eyes (small circles)
    eye_radius = 3
    left_eye_x = head_x + head_width * 0.25
    right_eye_x = head_x + head_width * 0.75
    eye_y = head_y + head_height * 0.4
    
    draw.ellipse([left_eye_x - eye_radius, eye_y - eye_radius, 
                 left_eye_x + eye_radius, eye_y + eye_radius], fill='#ECEFF4')
    draw.ellipse([right_eye_x - eye_radius, eye_y - eye_radius, 
                 right_eye_x + eye_radius, eye_y + eye_radius], fill='#ECEFF4')
    
    # Robot arms (small rectangles on sides)
    arm_width = size[0] * 0.08
    arm_height = size[1] * 0.3
    left_arm_x = body_x - arm_width - 2
    right_arm_x = body_x + body_width + 2
    arm_y = body_y + 10
    
    draw.rectangle([left_arm_x, arm_y, left_arm_x + arm_width, arm_y + arm_height], 
                  fill='#5E81AC', outline='#88C0D0', width=1)
    draw.rectangle([right_arm_x, arm_y, right_arm_x + arm_width, arm_y + arm_height], 
                  fill='#5E81AC', outline='#88C0D0', width=1)
    
    # Team number text
    try:
        # Try to use a nice font
        font_size = max(16, size[0] // 8)
        font = ImageFont.truetype("arial.ttf", font_size)
    except:
        # Fallback to default font
        font = ImageFont.load_default()
    
    # Get text dimensions
    text = str(team_number)
    bbox = draw.textbbox((0, 0), text, font=font)
    text_width = bbox[2] - bbox[0]
    text_height = bbox[3] - bbox[1]
    
    # Center text in robot body
    text_x = (size[0] - text_width) / 2
    text_y = body_y + (body_height - text_height) / 2
    
    draw.text((text_x, text_y), text, fill='#ECEFF4', font=font)
    
    return img

def image_to_base64(img):
    """Convert PIL Image to base64 string"""
    buffer = io.BytesIO()
    img.save(buffer, format='PNG')
    img_data = buffer.getvalue()
    return base64.b64encode(img_data).decode('utf-8')

def load_team_image(team_number, images_folder=None):
    """Load team image from folder or create default"""
    if images_folder and os.path.exists(images_folder):
        # Look for image files with team number
        for ext in ['.png', '.jpg', '.jpeg', '.gif', '.bmp']:
            img_path = os.path.join(images_folder, f"{team_number}{ext}")
            if os.path.exists(img_path):
                try:
                    img = Image.open(img_path)
                    # Resize to standard size
                    img = img.resize((150, 150), Image.Resampling.LANCZOS)
                    return image_to_base64(img)
                except Exception as e:
                    print(f"Error loading image for team {team_number}: {e}")
    
    # Create default image
    default_img = create_default_robot_image(team_number)
    return image_to_base64(default_img)

if __name__ == "__main__":
    # Test the function
    test_img = create_default_robot_image("1234")
    test_img.show()
    print("Default image created successfully!")
