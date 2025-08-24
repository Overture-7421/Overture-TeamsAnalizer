#!/usr/bin/env python3
"""
Quick Setup Script for Alliance Simulator

This script helps users quickly set up the Alliance Simulator with the new CSV format
and provides interactive configuration options.
"""

import os
import sys
import json
from pathlib import Path

def check_dependencies():
    """Check if required dependencies are installed"""
    required_packages = ['streamlit', 'pandas', 'numpy', 'matplotlib']
    missing_packages = []
    
    for package in required_packages:
        try:
            __import__(package)
        except ImportError:
            missing_packages.append(package)
    
    if missing_packages:
        print(f"❌ Missing required packages: {', '.join(missing_packages)}")
        print("Install them with: pip install " + " ".join(missing_packages))
        return False
    
    print("✅ All required packages are installed")
    return True

def check_configuration():
    """Check if configuration file exists and is valid"""
    config_file = "columnsConfig.json"
    
    if not os.path.exists(config_file):
        print(f"⚠️  Configuration file {config_file} not found")
        create_default_config()
        return True
    
    try:
        with open(config_file, 'r') as f:
            config = json.load(f)
        
        required_keys = ['headers', 'column_configuration']
        if all(key in config for key in required_keys):
            print("✅ Configuration file is valid")
            return True
        else:
            print("⚠️  Configuration file is incomplete, creating new one")
            create_default_config()
            return True
            
    except json.JSONDecodeError:
        print("❌ Configuration file is corrupted, creating new one")
        create_default_config()
        return True

def create_default_config():
    """Create default configuration file"""
    default_config = {
        "version": "1.0",
        "timestamp": "auto-generated",
        "headers": [
            "Scouter Initials", "Match Number", "Robot", "Future Alliance", "Team Number",
            "Starting Position", "No Show", "Moved (Auto)", "Coral L1 (Auto)", "Coral L2 (Auto)",
            "Coral L3 (Auto)", "Coral L4 (Auto)", "Barge Algae (Auto)", "Processor Algae (Auto)",
            "Dislodged Algae (Auto)", "Foul (Auto)", "Dislodged Algae (Teleop)", "Pickup Location",
            "Coral L1 (Teleop)", "Coral L2 (Teleop)", "Coral L3 (Teleop)", "Coral L4 (Teleop)",
            "Barge Algae (Teleop)", "Processor Algae (Teleop)", "Crossed Field/Defense",
            "Tipped/Fell", "Touched Opposing Cage", "Died", "End Position", "Broke",
            "Defended", "Coral HP Mistake", "Yellow/Red Card"
        ],
        "column_configuration": {
            "numeric_for_overall": [
                "Coral L1 (Auto)", "Coral L2 (Auto)", "Coral L3 (Auto)", "Coral L4 (Auto)",
                "Barge Algae (Auto)", "Processor Algae (Auto)", "Dislodged Algae (Auto)",
                "Coral L1 (Teleop)", "Coral L2 (Teleop)", "Coral L3 (Teleop)", "Coral L4 (Teleop)",
                "Barge Algae (Teleop)", "Processor Algae (Teleop)"
            ],
            "stats_columns": [
                "No Show", "Moved (Auto)", "Coral L1 (Auto)", "Coral L2 (Auto)",
                "Coral L3 (Auto)", "Coral L4 (Auto)", "Barge Algae (Auto)", "Processor Algae (Auto)",
                "Dislodged Algae (Auto)", "Foul (Auto)", "Dislodged Algae (Teleop)", "Pickup Location",
                "Coral L1 (Teleop)", "Coral L2 (Teleop)", "Coral L3 (Teleop)", "Coral L4 (Teleop)",
                "Barge Algae (Teleop)", "Processor Algae (Teleop)", "Crossed Field/Defense",
                "Tipped/Fell", "Touched Opposing Cage", "Died", "End Position", "Broke",
                "Defended", "Coral HP Mistake", "Yellow/Red Card"
            ],
            "mode_boolean_columns": [
                "No Show", "Moved (Auto)", "Foul (Auto)", "Dislodged Algae (Teleop)",
                "Crossed Field/Defense", "Tipped/Fell", "Touched Opposing Cage", "Died",
                "Broke", "Defended", "Coral HP Mistake"
            ],
            "autonomous_columns": [
                "Moved (Auto)", "Coral L1 (Auto)", "Coral L2 (Auto)", "Coral L3 (Auto)",
                "Coral L4 (Auto)", "Barge Algae (Auto)", "Processor Algae (Auto)",
                "Dislodged Algae (Auto)", "Foul (Auto)"
            ],
            "teleop_columns": [
                "Dislodged Algae (Teleop)", "Coral L1 (Teleop)", "Coral L2 (Teleop)",
                "Coral L3 (Teleop)", "Coral L4 (Teleop)", "Barge Algae (Teleop)",
                "Processor Algae (Teleop)", "Crossed Field/Defense", "Defended", "Coral HP Mistake"
            ],
            "endgame_columns": ["Tipped/Fell", "Died"]
        },
        "robot_valuation": {
            "phase_weights": [0.2, 0.3, 0.5],
            "phase_names": ["Q1", "Q2", "Q3"]
        },
        "metadata": {
            "total_columns": 33,
            "description": "Alliance Simulator Column Configuration"
        }
    }
    
    with open("columnsConfig.json", 'w') as f:
        json.dump(default_config, f, indent=4)
    
    print("✅ Created default configuration file")

def convert_sample_data():
    """Convert sample data if available"""
    sample_files = ["test_data.csv", "sample_data.csv", "legacy_data.csv"]
    
    for sample_file in sample_files:
        if os.path.exists(sample_file):
            print(f"📄 Found sample data: {sample_file}")
            
            try:
                from csv_converter import convert_csv_file
                output_file = f"converted_{sample_file}"
                convert_csv_file(sample_file, output_file)
                print(f"✅ Converted {sample_file} to {output_file}")
            except Exception as e:
                print(f"⚠️  Could not convert {sample_file}: {e}")

def interactive_setup():
    """Interactive setup for first-time users"""
    print("\n" + "="*50)
    print("🤖 Alliance Simulator Quick Setup")
    print("="*50)
    
    print("\n1. Checking system requirements...")
    if not check_dependencies():
        return False
    
    print("\n2. Checking configuration...")
    check_configuration()
    
    print("\n3. Looking for sample data to convert...")
    convert_sample_data()
    
    print("\n4. Setup complete! 🎉")
    print("\nHow to proceed:")
    print("• For web interface: streamlit run streamlit_app.py")
    print("• For desktop app: python main.py")
    print("• For CSV conversion: python csv_converter.py input.csv output.csv")
    print("• For configuration: python config_manager.py")
    
    # Ask user what they want to do
    print("\nWhat would you like to do now?")
    print("1. Start web interface")
    print("2. Convert a CSV file")
    print("3. View configuration")
    print("4. Exit")
    
    choice = input("\nEnter your choice (1-4): ").strip()
    
    if choice == "1":
        print("\nStarting web interface...")
        os.system("streamlit run streamlit_app.py")
    elif choice == "2":
        csv_file = input("Enter path to CSV file: ").strip()
        if os.path.exists(csv_file):
            try:
                from csv_converter import convert_csv_file
                output_file = f"converted_{os.path.basename(csv_file)}"
                convert_csv_file(csv_file, output_file)
                print(f"✅ Converted to {output_file}")
            except Exception as e:
                print(f"❌ Error: {e}")
        else:
            print("❌ File not found")
    elif choice == "3":
        try:
            from config_manager import ConfigManager
            config = ConfigManager()
            column_config = config.get_column_config()
            print(f"\nCurrent configuration:")
            print(f"• Total columns: {len(column_config.headers)}")
            print(f"• Numeric columns: {len(column_config.numeric_for_overall)}")
            print(f"• Autonomous columns: {len(column_config.autonomous_columns)}")
            print(f"• Teleop columns: {len(column_config.teleop_columns)}")
            print(f"• Endgame columns: {len(column_config.endgame_columns)}")
        except Exception as e:
            print(f"❌ Error reading configuration: {e}")
    
    return True

def main():
    """Main setup function"""
    if len(sys.argv) > 1:
        if sys.argv[1] == "--check":
            print("Checking system...")
            check_dependencies()
            check_configuration()
        elif sys.argv[1] == "--config":
            create_default_config()
        elif sys.argv[1] == "--convert" and len(sys.argv) > 2:
            input_file = sys.argv[2]
            output_file = sys.argv[3] if len(sys.argv) > 3 else f"converted_{input_file}"
            try:
                from csv_converter import convert_csv_file
                convert_csv_file(input_file, output_file)
            except Exception as e:
                print(f"❌ Error: {e}")
        else:
            print("Usage:")
            print("  python setup.py                 # Interactive setup")
            print("  python setup.py --check         # Check system")
            print("  python setup.py --config        # Create default config")
            print("  python setup.py --convert file  # Convert CSV file")
    else:
        interactive_setup()

if __name__ == "__main__":
    main()