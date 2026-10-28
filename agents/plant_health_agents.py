"""
CrewAI agents for plant health analysis system
"""
from crewai import Agent, Task, Crew, Process
from tools.gemini_tools import GeminiImageAnalyzer, encode_image_to_base64, validate_image_format, get_image_size_mb
from config import AGENT_CONFIGS, CREW_CONFIG, MAX_IMAGE_SIZE_MB
from typing import Dict, Any, Optional
import logging

logger = logging.getLogger(__name__)

class PlantHealthCrew:
    """CrewAI crew for comprehensive plant health analysis"""

    def __init__(self):
        self.gemini_analyzer = GeminiImageAnalyzer()
        self.agents = {}
        self.tasks = {}
        self._create_agents()
        self._create_tasks()

    def _create_agents(self):
        """Create simplified 2-agent system"""

        # Image Analysis Agent (combines preprocessing and visual analysis)
        self.agents['image_analyzer'] = Agent(
            **AGENT_CONFIGS['image_analyzer']
        )

        # Health Assessment Agent (combines disease detection, growth assessment, and synthesis)
        self.agents['health_assessor'] = Agent(
            **AGENT_CONFIGS['health_assessor']
        )

    def _create_tasks(self):
        """Create simplified 2-task system"""

        # Image Analysis Task (combines preprocessing and visual analysis)
        self.tasks['image_analysis'] = Task(
            description="""
            Analyze the plant image for visual characteristics and basic health indicators.

            Examine the image and provide:
            1. Plant type identification (if visible)
            2. Overall visual health assessment
            3. Color analysis of leaves, stems, flowers
            4. Structural characteristics and morphology
            5. Any obvious signs of problems (discoloration, spots, wilting)

            Focus on observable visual features that indicate plant health status.
            """,
            expected_output="Detailed visual analysis of plant appearance and basic health indicators",
            agent=self.agents['image_analyzer']
        )

        # Health Assessment Task (combines disease detection, growth assessment, and synthesis)
        self.tasks['health_assessment'] = Task(
            description="""
            Based on the visual analysis, provide a comprehensive plant health assessment.

            Analyze for:
            1. Disease symptoms (spots, discoloration, wilting, mold, rot)
            2. Pest damage (insect bites, holes, webs, visible pests)
            3. Growth stage and development status
            4. Environmental damage (sunburn, frost damage, nutrient deficiencies)
            5. Overall health status and severity assessment

            Provide:
            - Overall health rating (Excellent/Good/Fair/Poor/Critical)
            - Specific issues identified
            - Recommended actions and treatments
            - Follow-up recommendations

            Ensure recommendations are practical and prioritized by urgency.
            """,
            expected_output="Complete health assessment with diagnosis and treatment recommendations",
            agent=self.agents['health_assessor'],
            context=[self.tasks['image_analysis']]  # Depends on image analysis
        )

    def _create_image_validation_tool(self):
        """Create tool for image validation"""
        def validate_image(image_path: str) -> Dict[str, Any]:
            """Validate image format and size"""
            try:
                # Check format
                if not validate_image_format(image_path):
                    return {
                        "valid": False,
                        "error": f"Unsupported image format. Supported: {', '.join(['jpg', 'jpeg', 'png', 'webp'])}"
                    }

                # Check size
                size_mb = get_image_size_mb(image_path)
                if size_mb > MAX_IMAGE_SIZE_MB:
                    return {
                        "valid": False,
                        "error": f"Image too large ({size_mb:.1f}MB). Maximum: {MAX_IMAGE_SIZE_MB}MB"
                    }

                return {
                    "valid": True,
                    "size_mb": size_mb,
                    "format": image_path.split('.')[-1].lower()
                }

            except Exception as e:
                return {
                    "valid": False,
                    "error": f"Validation failed: {str(e)}"
                }

        # Create CrewAI tool
        from crewai import tool
        @tool("Image Validator")
        def image_validator(image_path: str) -> str:
            """Validate image format and size for plant analysis"""
            result = validate_image(image_path)
            return str(result)

        return image_validator

    def _create_image_encoding_tool(self):
        """Create tool for image encoding"""
        from crewai import tool
        @tool("Image Encoder")
        def image_encoder(image_path: str) -> str:
            """Encode image to base64 for API processing"""
            try:
                encoded = encode_image_to_base64(image_path)
                return encoded
            except Exception as e:
                return f"Encoding failed: {str(e)}"

        return image_encoder

    def _create_visual_analysis_tool(self):
        """Create tool for visual analysis"""
        from crewai import tool
        @tool("Visual Analyzer")
        def visual_analyzer(image_data: str) -> str:
            """Analyze visual characteristics of plant"""
            result = self.gemini_analyzer.analyze_plant_visual(image_data)
            if result["success"]:
                return result["analysis"]
            else:
                return f"Visual analysis failed: {result.get('error', 'Unknown error')}"

        return visual_analyzer

    def _create_disease_analysis_tool(self):
        """Create tool for disease analysis"""
        from crewai import tool
        @tool("Disease Detector")
        def disease_detector(image_data: str) -> str:
            """Detect diseases, pests, and damage in plant"""
            result = self.gemini_analyzer.analyze_plant_diseases(image_data)
            if result["success"]:
                return result["analysis"]
            else:
                return f"Disease analysis failed: {result.get('error', 'Unknown error')}"

        return disease_detector

    def _create_growth_analysis_tool(self):
        """Create tool for growth analysis"""
        from crewai import tool
        @tool("Growth Assessor")
        def growth_assessor(image_data: str) -> str:
            """Assess plant growth stage and development"""
            result = self.gemini_analyzer.analyze_plant_growth(image_data)
            if result["success"]:
                return result["analysis"]
            else:
                return f"Growth analysis failed: {result.get('error', 'Unknown error')}"

        return growth_assessor

    def _create_health_synthesis_tool(self):
        """Create tool for health synthesis"""
        from crewai import tool
        @tool("Health Synthesizer")
        def health_synthesizer(visual_analysis: str, disease_analysis: str, growth_analysis: str) -> str:
            """Synthesize all analyses into comprehensive health assessment"""
            analyses = {
                "visual": visual_analysis,
                "disease": disease_analysis,
                "growth": growth_analysis
            }
            result = self.gemini_analyzer.synthesize_health_analysis(analyses)
            if result["success"]:
                return result["synthesis"]
            else:
                return f"Health synthesis failed: {result.get('error', 'Unknown error')}"

        return health_synthesizer

    def analyze_plant_health(self, image_path: str) -> Dict[str, Any]:
        """
        Run complete plant health analysis using all agents

        Args:
            image_path: Path to plant image file

        Returns:
            Dictionary containing complete analysis results
        """
        try:
            # Create the crew
            crew = Crew(
                agents=list(self.agents.values()),
                tasks=list(self.tasks.values()),
                **CREW_CONFIG
            )

            # Prepare inputs
            inputs = {
                "image_path": image_path,
                "image_data": encode_image_to_base64(image_path)  # Pre-encode for agents
            }

            # Run the analysis
            logger.info("Starting plant health analysis...")
            result = crew.kickoff(inputs=inputs)

            logger.info("Plant health analysis completed successfully")
            return {
                "success": True,
                "result": str(result),
                "crew": crew
            }

        except Exception as e:
            logger.error(f"Plant health analysis failed: {str(e)}")
            return {
                "success": False,
                "error": str(e)
            }

    def get_agent_status(self) -> Dict[str, Any]:
        """Get status of all agents"""
        return {
            agent_name: {
                "role": agent.role,
                "goal": agent.goal,
                "status": "ready"
            }
            for agent_name, agent in self.agents.items()
        }
