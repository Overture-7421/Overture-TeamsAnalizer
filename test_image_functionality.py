#!/usr/bin/env python3
"""
Quick test for image functionality
"""

try:
    from PIL import Image, ImageDraw, ImageFont
    import base64
    import io
    print("✅ All imports successful")
    
    # Test creating a simple image
    img = Image.new('RGB', (100, 100), color='blue')
    print("✅ Image creation successful")
    
    # Test base64 conversion
    buffer = io.BytesIO()
    img.save(buffer, format='PNG')
    img_data = buffer.getvalue()
    b64_string = base64.b64encode(img_data).decode('utf-8')
    print(f"✅ Base64 conversion successful (length: {len(b64_string)})")
    
    print("🎉 All tests passed!")
    
except Exception as e:
    print(f"❌ Error: {e}")
    import traceback
    traceback.print_exc()
