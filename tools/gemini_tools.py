"""
Gemini API tools for plant health analysis
"""
import base64
import json
from typing import Dict, Any, Optional
import google.generativeai as genai
from config import GEMINI_API_KEY, GEMINI_MODEL
import logging

logger = logging.getLogger(__name__)

class GeminiImageAnalyzer:
    """Tool for analyzing images using Gemini API"""

    def __init__(self):
        if not GEMINI_API_KEY:
            raise ValueError("GEMINI_API_KEY not found in environment variables")

        genai.configure(api_key=GEMINI_API_KEY)
        self.model = genai.GenerativeModel(GEMINI_MODEL)

    def analyze_image(self, image_data: str, prompt: str) -> Dict[str, Any]:
        """
        Analyze image using Gemini API

        Args:
            image_data: Base64 encoded image data
            prompt: Analysis prompt

        Returns:
            Dictionary containing analysis results
        """
        try:
            # Create image part from base64 data
            image_part = {
                "mime_type": "image/jpeg",  # Will be updated based on actual format
                "data": image_data
            }

            # Generate response
            response = self.model.generate_content([prompt, image_part])
            response.resolve()

            return {
                "success": True,
                "analysis": response.text,
                "usage": {
                    "prompt_tokens": response.usage_metadata.prompt_token_count,
                    "completion_tokens": response.usage_metadata.candidates_token_count,
                    "total_tokens": response.usage_metadata.total_token_count
                }
            }

        except Exception as e:
            logger.error(f"Error analyzing image: {str(e)}")
            return {
                "success": False,
                "error": str(e)
            }

    def analyze_plant_visual(self, image_data: str) -> Dict[str, Any]:
        """Analyze visual characteristics of a plant"""
        prompt = """
        Analyze this plant image and provide detailed information about its visual characteristics:

        1. Plant Type: What type of plant is this (flower, crop, herb, vegetable, etc.)?
        2. Color Analysis: Describe the colors of leaves, stems, flowers, and any variations
        3. Structure: Describe the overall structure, leaf shape, stem characteristics
        4. Texture: Describe leaf texture, surface characteristics
        5. Size Estimation: Estimate the relative size and growth stage
        6. Overall Appearance: General health appearance from visual inspection

        Provide specific, detailed observations for each category.
        """
        return self.analyze_image(image_data, prompt)

    def analyze_plant_diseases(self, image_data: str) -> Dict[str, Any]:
        """Analyze plant for diseases, pests, and damage"""
        prompt = """
        Carefully examine this plant image for any signs of diseases, pests, or damage:

        1. Disease Symptoms: Look for spots, discoloration, wilting, mold, rot, etc.
        2. Pest Damage: Check for insect bites, holes, webs, or visible pests
        3. Environmental Damage: Look for sunburn, frost damage, nutrient deficiencies
        4. Fungal Issues: Identify mold, mildew, or fungal growth
        5. Bacterial Problems: Check for soft rot, bacterial spots, or ooze
        6. Viral Symptoms: Look for mosaic patterns, yellowing, or stunting

        Provide specific observations and confidence levels for each category.
        """
        return self.analyze_image(image_data, prompt)

    def analyze_plant_growth(self, image_data: str) -> Dict[str, Any]:
        """Analyze plant growth stage and development"""
        prompt = """
        Analyze this plant's growth stage and development:

        1. Growth Stage: Determine if it's seedling, vegetative, flowering, fruiting, or mature
        2. Size Assessment: Estimate overall size and compare to typical for this plant type
        3. Development Progress: Assess how well-developed the plant appears
        4. Abnormalities: Note any developmental issues or irregularities
        5. Age Estimation: Estimate plant age based on size and development
        6. Growth Rate Indicators: Assess if growth appears normal or stunted

        Provide detailed observations with specific measurements where possible.
        """
        return self.analyze_image(image_data, prompt)

    def synthesize_health_analysis(self, analyses: Dict[str, Any]) -> Dict[str, Any]:
        """Synthesize multiple analyses into comprehensive health assessment"""
        # This would be called by the health synthesizer agent
        # to combine results from all other agents
        synthesis_prompt = f"""
        Based on the following analyses of a plant, provide a comprehensive health assessment:

        Visual Analysis: {analyses.get('visual', 'Not available')}
        Disease Analysis: {analyses.get('disease', 'Not available')}
        Growth Analysis: {analyses.get('growth', 'Not available')}

        Provide:
        1. Overall Health Status (Excellent/Good/Fair/Poor/Critical)
        2. Key Findings Summary
        3. Specific Issues Identified
        4. Recommended Actions
        5. Treatment Priority Level
        6. Follow-up Recommendations

        Be specific and actionable in your recommendations.
        """

        # This would typically use text-only analysis since we have the analysis results
        try:
            response = self.model.generate_content(synthesis_prompt)
            response.resolve()

            return {
                "success": True,
                "synthesis": response.text,
                "usage": {
                    "prompt_tokens": response.usage_metadata.prompt_token_count,
                    "completion_tokens": response.usage_metadata.candidates_token_count,
                    "total_tokens": response.usage_metadata.total_token_count
                }
            }
        except Exception as e:
            logger.error(f"Error synthesizing analysis: {str(e)}")
            return {
                "success": False,
                "error": str(e)
            }


# Utility functions for image processing
def encode_image_to_base64(image_path_or_url: str) -> str:
    """Encode image file or URL to base64 string"""
    try:
        if image_path_or_url.startswith(('http://', 'https://')):
            # Download image from URL
            import requests
            response = requests.get(image_path_or_url, timeout=30)
            response.raise_for_status()
            image_data = response.content
        else:
            # Read from local file
            with open(image_path_or_url, "rb") as image_file:
                image_data = image_file.read()

        return base64.b64encode(image_data).decode('utf-8')
    except requests.exceptions.RequestException as e:
        raise ValueError(f"Failed to download image from URL: {str(e)}")
    except Exception as e:
        raise ValueError(f"Failed to encode image: {str(e)}")


def validate_image_format(image_path: str) -> bool:
    """Validate if image format is supported"""
    from config import SUPPORTED_FORMATS
    import os

    ext = os.path.splitext(image_path)[1].lower().lstrip('.')
    return ext in SUPPORTED_FORMATS


def get_image_size_mb(image_path: str) -> float:
    """Get image file size in MB"""
    import os
    return os.path.getsize(image_path) / (1024 * 1024)
