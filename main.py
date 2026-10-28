"""
Main application for Plant Health Analysis System using CrewAI
"""
import logging
import sys
from pathlib import Path
from agents.plant_health_agents import PlantHealthCrew
from config import LOG_LEVEL, DEBUG

# Configure logging
logging.basicConfig(
    level=getattr(logging, LOG_LEVEL),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler('plant_health_analysis.log') if not DEBUG else logging.NullHandler()
    ]
)

logger = logging.getLogger(__name__)

def main():
    """Main function for command-line usage"""
    import argparse

    parser = argparse.ArgumentParser(description="Plant Health Analysis System")
    parser.add_argument("image_path", help="Path to plant image file or URL")
    parser.add_argument("--verbose", "-v", action="store_true", help="Enable verbose output")

    args = parser.parse_args()

    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)

    # Validate image input (file path or URL)
    image_input = args.image_path
    is_url = image_input.startswith(('http://', 'https://'))

    if is_url:
        # For URLs, we'll validate during download
        logger.info(f"Processing image from URL: {image_input}")
    else:
        # For file paths, validate existence
        image_path = Path(image_input)
        if not image_path.exists():
            logger.error(f"Image file not found: {image_path}")
            sys.exit(1)

        if not image_path.is_file():
            logger.error(f"Path is not a file: {image_path}")
            sys.exit(1)
        logger.info(f"Processing image from file: {image_input}")

    # Initialize the plant health crew
    logger.info("Initializing Plant Health Analysis Crew...")
    try:
        crew = PlantHealthCrew()
        logger.info("Crew initialized successfully")
    except Exception as e:
        logger.error(f"Failed to initialize crew: {str(e)}")
        sys.exit(1)

    # Run analysis
    logger.info(f"Starting analysis of plant image: {image_input}")
    print("\n🔍 Analyzing plant image... Please wait...")

    # Direct analysis approach for clarity
    from tools.gemini_tools import GeminiImageAnalyzer, encode_image_to_base64

    try:
        analyzer = GeminiImageAnalyzer()
        image_data = encode_image_to_base64(image_input)

        # Quick visual check first
        visual_result = analyzer.analyze_plant_visual(image_data)

        if "not a plant" in visual_result["analysis"].lower() or "rectangle" in visual_result["analysis"].lower():
            # Not a plant image - provide clear result
            analysis_result = f"""
❌ INVALID IMAGE TYPE

The provided image does not contain a plant. Analysis shows: {visual_result["analysis"]}

This system is designed for plant health analysis. Please provide an actual plant image.
"""
        else:
            # Continue with full analysis
            result = crew.analyze_plant_health(image_input)
            analysis_result = result["result"]

    except Exception as e:
        analysis_result = f"Analysis failed: {str(e)}"

    # Clear, structured output
    print("\n" + "="*80)
    print("🌿 PLANT HEALTH ANALYSIS COMPLETE")
    print("="*80)
    print(f"📁 Image: {image_input}")
    print(f"📅 Analysis Date: {__import__('datetime').datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("\n📋 ANALYSIS RESULTS:")
    print("-"*50)
    print(analysis_result)
    print("\n" + "="*80)
    print("✅ Analysis completed successfully!")
    print("="*80)

    # Save detailed results to file
    if is_url:
        # Extract filename from URL
        from urllib.parse import urlparse
        parsed_url = urlparse(image_input)
        filename = Path(parsed_url.path).stem or "url_image"
        output_file = f"plant_health_report_{filename}.txt"
        image_display = image_input
    else:
        output_file = f"plant_health_report_{image_path.stem}.txt"
        image_display = str(image_path)

    with open(output_file, 'w') as f:
        f.write("PLANT HEALTH ANALYSIS REPORT\n")
        f.write("="*50 + "\n\n")
        f.write(f"Image: {image_display}\n")
        f.write(f"Analysis Date: {__import__('datetime').datetime.now()}\n\n")
        f.write("RESULTS:\n")
        f.write("-"*20 + "\n")
        f.write(analysis_result)
    logger.info(f"Detailed report saved to: {output_file}")

if __name__ == "__main__":
    main()
