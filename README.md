# 🌱 Plant Health Analysis System

AI-powered plant health analysis using CrewAI and Google Gemini API. This system employs 5 specialized AI agents working together to analyze plant images and provide comprehensive health assessments.

## 🤖 AI Agents

The system uses 5 specialized AI agents that collaborate sequentially:

1. **🔍 Image Preprocessing Agent** - Validates and prepares plant images
2. **👁️ Visual Analysis Agent** - Analyzes plant appearance and characteristics
3. **🦠 Disease Detection Agent** - Identifies diseases, pests, and damage
4. **📈 Growth Assessment Agent** - Evaluates growth stage and development
5. **🏥 Health Synthesis Agent** - Combines all findings into final diagnosis

## 🚀 Quick Start

### Prerequisites

- Python 3.8+
- Google Gemini API key

### Installation

1. **Clone and setup:**

   ```bash
   git clone <repository-url>
   cd plant-health-analysis
   pip install -r requirements.txt
   ```

2. **Configure API key:**

   ```bash
   # Edit .env file
   GEMINI_API_KEY=your_actual_gemini_api_key_here
   ```

3. **Run the web interface:**
   ```bash
   python api.py
   ```
   Open http://localhost:8000 in your browser

### Alternative: Command Line Usage

```bash
python main.py path/to/plant/image.jpg
```

## 📋 Usage

### Web Interface

1. Open http://localhost:8000
2. Upload a clear photo of your plant
3. Click "Analyze Plant Health"
4. View the comprehensive health report

### API Usage

```python
from agents.plant_health_agents import PlantHealthCrew

# Initialize crew
crew = PlantHealthCrew()

# Analyze plant
result = crew.analyze_plant_health("path/to/plant.jpg")
print(result["result"])
```

## 🔧 Configuration

### Environment Variables (.env)

```bash
# Gemini API Configuration
GEMINI_API_KEY=your_gemini_api_key_here

# Application Settings
DEBUG=True
LOG_LEVEL=INFO

# Image Processing Settings
MAX_IMAGE_SIZE_MB=10
SUPPORTED_FORMATS=jpg,jpeg,png,webp

# CrewAI Settings
CREW_VERBOSE=True
```

### Supported Image Formats

- JPEG/JPG
- PNG
- WebP

Maximum file size: 10MB (configurable)

## 🏗️ Architecture

### CrewAI Framework

The system leverages CrewAI for multi-agent orchestration:

- **Sequential Processing**: Agents work in order (preprocessing → analysis → synthesis)
- **Tool Integration**: Each agent uses specialized tools powered by Gemini API
- **Memory Management**: Agents share context and build upon each other's findings
- **Error Handling**: Built-in retry mechanisms and graceful failure handling

### Gemini API Integration

- **Image Analysis**: Multimodal capabilities for plant image understanding
- **Specialized Prompts**: Each agent uses tailored prompts for specific analysis types
- **Structured Output**: Consistent data handling across all agents

## 📊 Sample Output

```
PLANT HEALTH ANALYSIS REPORT
==================================================

Overall Health Status: GOOD

Key Findings Summary:
- Plant appears to be a healthy tomato seedling
- No visible signs of disease or pest damage
- Growth stage appropriate for age

Specific Issues Identified:
- Minor nutrient deficiency indicated by slight yellowing
- Soil moisture appears adequate

Recommended Actions:
1. Apply balanced fertilizer with emphasis on nitrogen
2. Ensure consistent watering schedule
3. Monitor for early blight symptoms

Treatment Priority Level: LOW
Follow-up Recommendations: Reassess in 2 weeks
```

## 🧪 Testing

### Run Tests

```bash
# Create test directory with sample images
mkdir test_images

# Run basic functionality test
python -c "from agents.plant_health_agents import PlantHealthCrew; print('✅ Import successful')"

# Test agent initialization
python -c "from agents.plant_health_agents import PlantHealthCrew; crew = PlantHealthCrew(); print('✅ Crew initialization successful')"
```

### Sample Test Images

For testing, use clear photos of:

- Healthy plants
- Plants with visible diseases
- Different growth stages
- Various plant types (flowers, vegetables, herbs)

## 🔍 Troubleshooting

### Common Issues

1. **API Key Error**

   ```
   ValueError: GEMINI_API_KEY environment variable is required
   ```

   Solution: Add your Gemini API key to the `.env` file

2. **Image Format Error**

   ```
   Unsupported image format
   ```

   Solution: Use JPG, PNG, or WebP formats

3. **Large File Error**
   ```
   Image too large
   ```
   Solution: Reduce image size or adjust `MAX_IMAGE_SIZE_MB` in config

### Logs

Check the log file for detailed error information:

- `plant_health_analysis.log` (production)
- Console output (debug mode)

## 📈 Performance

- **Analysis Time**: 30-90 seconds per image (depending on complexity)
- **API Limits**: Respects Gemini API rate limits
- **Memory Usage**: Optimized for typical plant images
- **Concurrent Users**: Single-threaded design (can be scaled)

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Add tests for new functionality
4. Ensure all tests pass
5. Submit a pull request

## 📄 License

This project is licensed under the MIT License - see the LICENSE file for details.

## 🙏 Acknowledgments

- **CrewAI**: Multi-agent orchestration framework
- **Google Gemini**: Advanced multimodal AI capabilities
- **FastAPI**: Modern web framework
- **Pydantic**: Data validation and settings management

## 📞 Support

For issues and questions:

1. Check the troubleshooting section
2. Review the logs for error details
3. Open an issue on GitHub with:
   - Error messages
   - System information
   - Sample image (if applicable)
