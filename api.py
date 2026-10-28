"""
Enhanced FastAPI web interface for Plant Health Analysis System with process visualization
"""
import logging
import tempfile
import os
import json
import asyncio
from pathlib import Path
from typing import Optional, Dict, Any, List
from datetime import datetime
from fastapi import FastAPI, File, UploadFile, HTTPException, BackgroundTasks, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
import uvicorn

from agents.plant_health_agents import PlantHealthCrew
from config import DEBUG

# Configure logging
logging.basicConfig(level=logging.INFO if not DEBUG else logging.DEBUG)
logger = logging.getLogger(__name__)

# Create FastAPI app
app = FastAPI(
    title="Plant Health Analysis System",
    description="AI-powered plant health analysis using CrewAI and Gemini API",
    version="1.0.0"
)

# Global crew instance (initialized on first use)
crew_instance = None

def get_crew() -> PlantHealthCrew:
    """Get or create the plant health crew instance"""
    global crew_instance
    if crew_instance is None:
        logger.info("Initializing Plant Health Crew...")
        crew_instance = PlantHealthCrew()
        logger.info("Crew initialized successfully")
    return crew_instance

# Pydantic models for API responses
class HealthAnalysisRequest(BaseModel):
    image_path: str

class HealthAnalysisResponse(BaseModel):
    success: bool
    result: Optional[str] = None
    error: Optional[str] = None
    report_file: Optional[str] = None

class AgentStatusResponse(BaseModel):
    agents: dict

# Routes
@app.get("/", response_class=HTMLResponse)
async def root():
    """Serve the enhanced web interface with process visualization"""
    html_content = """
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Plant Health Analysis System - Process Visualization</title>
        <style>
            * {
                margin: 0;
                padding: 0;
                box-sizing: border-box;
            }

            body {
                font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                min-height: 100vh;
                color: #333;
            }

            .container {
                max-width: 1200px;
                margin: 0 auto;
                padding: 20px;
            }

            .header {
                text-align: center;
                color: white;
                margin-bottom: 30px;
            }

            .header h1 {
                font-size: 2.5em;
                margin-bottom: 10px;
                text-shadow: 2px 2px 4px rgba(0,0,0,0.3);
            }

            .header p {
                font-size: 1.2em;
                opacity: 0.9;
            }

            .main-content {
                display: grid;
                grid-template-columns: 1fr;
                gap: 30px;
            }

            @media (min-width: 768px) {
                .main-content {
                    grid-template-columns: 1fr 1fr;
                }
            }

            .panel {
                background: white;
                border-radius: 15px;
                padding: 25px;
                box-shadow: 0 10px 30px rgba(0,0,0,0.2);
                transition: transform 0.3s ease;
            }

            .panel:hover {
                transform: translateY(-5px);
            }

            .upload-panel {
                order: 1;
            }

            .process-panel {
                order: 2;
            }

            .results-panel {
                order: 3;
                grid-column: 1 / -1;
            }

            .panel h2 {
                color: #2e7d32;
                margin-bottom: 20px;
                font-size: 1.5em;
                display: flex;
                align-items: center;
                gap: 10px;
            }

            /* Upload Section */
            .upload-zone {
                border: 3px dashed #4caf50;
                border-radius: 10px;
                padding: 40px;
                text-align: center;
                background: linear-gradient(135deg, #f5f7fa 0%, #c3cfe2 100%);
                transition: all 0.3s ease;
                cursor: pointer;
                position: relative;
                overflow: hidden;
            }

            .upload-zone:hover {
                border-color: #45a049;
                background: linear-gradient(135deg, #e8f5e8 0%, #d4edda 100%);
                transform: scale(1.02);
            }

            .upload-zone.dragover {
                border-color: #007bff;
                background: linear-gradient(135deg, #e3f2fd 0%, #bbdefb 100%);
            }

            .upload-icon {
                font-size: 3em;
                color: #4caf50;
                margin-bottom: 15px;
            }

            .upload-text {
                font-size: 1.1em;
                color: #666;
                margin-bottom: 10px;
            }

            .upload-subtext {
                font-size: 0.9em;
                color: #888;
            }

            #imageInput {
                position: absolute;
                top: 0;
                left: 0;
                width: 100%;
                height: 100%;
                opacity: 0;
                cursor: pointer;
            }

            .image-preview {
                margin-top: 20px;
                display: none;
            }

            .image-preview img {
                max-width: 100%;
                max-height: 200px;
                border-radius: 10px;
                box-shadow: 0 5px 15px rgba(0,0,0,0.2);
            }

            .analyze-btn {
                background: linear-gradient(135deg, #4caf50 0%, #45a049 100%);
                color: white;
                border: none;
                padding: 15px 30px;
                border-radius: 25px;
                font-size: 1.1em;
                cursor: pointer;
                transition: all 0.3s ease;
                margin-top: 20px;
                box-shadow: 0 4px 15px rgba(76, 175, 80, 0.3);
            }

            .analyze-btn:hover:not(:disabled) {
                transform: translateY(-2px);
                box-shadow: 0 6px 20px rgba(76, 175, 80, 0.4);
            }

            .analyze-btn:disabled {
                background: #cccccc;
                cursor: not-allowed;
                box-shadow: none;
            }

            /* Process Visualization */
            .process-flow {
                display: flex;
                flex-direction: column;
                gap: 15px;
            }

            @media (min-width: 768px) {
                .process-flow {
                    flex-direction: row;
                    overflow-x: auto;
                    padding-bottom: 10px;
                }
            }

            .agent-step {
                background: #f8f9fa;
                border: 2px solid #e9ecef;
                border-radius: 10px;
                padding: 15px;
                text-align: center;
                transition: all 0.3s ease;
                min-width: 150px;
                position: relative;
            }

            .agent-step.active {
                border-color: #007bff;
                background: linear-gradient(135deg, #e3f2fd 0%, #bbdefb 100%);
                transform: scale(1.05);
                box-shadow: 0 5px 15px rgba(0,123,255,0.3);
            }

            .agent-step.completed {
                border-color: #28a745;
                background: linear-gradient(135deg, #d4edda 0%, #c3e6cb 100%);
            }

            .agent-step.error {
                border-color: #dc3545;
                background: linear-gradient(135deg, #f8d7da 0%, #f5c6cb 100%);
            }

            .agent-icon {
                font-size: 2em;
                margin-bottom: 10px;
            }

            .agent-name {
                font-weight: bold;
                font-size: 0.9em;
                margin-bottom: 5px;
                color: #495057;
            }

            .agent-desc {
                font-size: 0.8em;
                color: #6c757d;
                margin-bottom: 10px;
            }

            .agent-status {
                font-size: 0.8em;
                padding: 3px 8px;
                border-radius: 12px;
                font-weight: bold;
            }

            .status-waiting {
                background: #e9ecef;
                color: #495057;
            }

            .status-active {
                background: #cce5ff;
                color: #004085;
                animation: pulse 2s infinite;
            }

            .status-completed {
                background: #d4edda;
                color: #155724;
            }

            .status-error {
                background: #f8d7da;
                color: #721c24;
            }

            @keyframes pulse {
                0% { opacity: 1; }
                50% { opacity: 0.7; }
                100% { opacity: 1; }
            }

            .progress-bar {
                width: 100%;
                height: 8px;
                background: #e9ecef;
                border-radius: 4px;
                overflow: hidden;
                margin-top: 10px;
            }

            .progress-fill {
                height: 100%;
                background: linear-gradient(90deg, #007bff 0%, #28a745 100%);
                width: 0%;
                transition: width 0.5s ease;
                border-radius: 4px;
            }

            /* Results Section */
            .results-container {
                display: none;
            }

            .result-card {
                background: #f8f9fa;
                border-left: 4px solid #28a745;
                border-radius: 8px;
                padding: 20px;
                margin-bottom: 15px;
            }

            .result-card.error {
                border-left-color: #dc3545;
                background: #f8d7da;
            }

            .result-header {
                display: flex;
                justify-content: space-between;
                align-items: center;
                margin-bottom: 10px;
            }

            .result-title {
                font-weight: bold;
                color: #495057;
            }

            .result-time {
                font-size: 0.8em;
                color: #6c757d;
            }

            .result-content {
                white-space: pre-wrap;
                font-family: 'Courier New', monospace;
                font-size: 0.9em;
                color: #495057;
                background: white;
                padding: 15px;
                border-radius: 5px;
                border: 1px solid #e9ecef;
                max-height: 300px;
                overflow-y: auto;
            }

            /* Loading States */
            .loading-overlay {
                position: fixed;
                top: 0;
                left: 0;
                width: 100%;
                height: 100%;
                background: rgba(0,0,0,0.7);
                display: none;
                justify-content: center;
                align-items: center;
                z-index: 1000;
            }

            .loading-content {
                background: white;
                padding: 40px;
                border-radius: 15px;
                text-align: center;
                box-shadow: 0 10px 30px rgba(0,0,0,0.3);
            }

            .loading-spinner {
                width: 50px;
                height: 50px;
                border: 5px solid #f3f3f3;
                border-top: 5px solid #4caf50;
                border-radius: 50%;
                animation: spin 1s linear infinite;
                margin: 0 auto 20px;
            }

            .loading-text {
                font-size: 1.2em;
                color: #333;
                margin-bottom: 10px;
            }

            .loading-subtext {
                color: #666;
            }

            /* Responsive Design */
            @media (max-width: 768px) {
                .container {
                    padding: 10px;
                }

                .header h1 {
                    font-size: 2em;
                }

                .process-flow {
                    flex-direction: column;
                }

                .agent-step {
                    min-width: auto;
                }
            }

            /* Animations */
            @keyframes fadeIn {
                from { opacity: 0; transform: translateY(20px); }
                to { opacity: 1; transform: translateY(0); }
            }

            .panel {
                animation: fadeIn 0.5s ease;
            }

            /* Connection lines between agents */
            .agent-connector {
                display: none;
            }

            @media (min-width: 768px) {
                .agent-connector {
                    display: block;
                    position: absolute;
                    top: 50%;
                    right: -15px;
                    width: 30px;
                    height: 2px;
                    background: #007bff;
                    z-index: 1;
                }

                .agent-step:last-child .agent-connector {
                    display: none;
                }
            }
        </style>
    </head>
    <body>
        <div class="container">
            <div class="header">
                <h1>🌱 Plant Health Analysis System</h1>
                <p>AI-Powered Plant Health Analysis with Process Visualization</p>
            </div>

            <div class="main-content">
                <!-- Upload Panel -->
                <div class="panel upload-panel">
                    <h2>📤 Upload Plant Image</h2>
                    <div class="upload-zone" id="uploadZone">
                        <div class="upload-icon">📷</div>
                        <div class="upload-text">Drag & drop your plant image here</div>
                        <div class="upload-subtext">or click to browse (JPG, PNG, WebP - Max 10MB)</div>
                        <input type="file" id="imageInput" accept="image/*">
                    </div>
                    <div class="image-preview" id="imagePreview">
                        <img id="previewImg" alt="Image preview">
                    </div>
                    <button class="analyze-btn" id="analyzeBtn" disabled>🔍 Analyze Plant Health</button>
                </div>

                <!-- Process Visualization Panel -->
                <div class="panel process-panel">
                    <h2>🔄 Analysis Process</h2>
                    <div class="process-flow" id="processFlow">
                        <div class="agent-step" data-agent="preprocessor">
                            <div class="agent-icon">🔍</div>
                            <div class="agent-name">Image Processor</div>
                            <div class="agent-desc">Validates & prepares images</div>
                            <div class="agent-status status-waiting">Waiting</div>
                            <div class="progress-bar">
                                <div class="progress-fill"></div>
                            </div>
                        </div>
                        <div class="agent-connector"></div>

                        <div class="agent-step" data-agent="visual_analyst">
                            <div class="agent-icon">👁️</div>
                            <div class="agent-name">Visual Analyst</div>
                            <div class="agent-desc">Analyzes appearance & characteristics</div>
                            <div class="agent-status status-waiting">Waiting</div>
                            <div class="progress-bar">
                                <div class="progress-fill"></div>
                            </div>
                        </div>
                        <div class="agent-connector"></div>

                        <div class="agent-step" data-agent="disease_detector">
                            <div class="agent-icon">🦠</div>
                            <div class="agent-name">Disease Detector</div>
                            <div class="agent-desc">Identifies diseases & pests</div>
                            <div class="agent-status status-waiting">Waiting</div>
                            <div class="progress-bar">
                                <div class="progress-fill"></div>
                            </div>
                        </div>
                        <div class="agent-connector"></div>

                        <div class="agent-step" data-agent="growth_assessor">
                            <div class="agent-icon">📈</div>
                            <div class="agent-name">Growth Assessor</div>
                            <div class="agent-desc">Evaluates growth & development</div>
                            <div class="agent-status status-waiting">Waiting</div>
                            <div class="progress-bar">
                                <div class="progress-fill"></div>
                            </div>
                        </div>
                        <div class="agent-connector"></div>

                        <div class="agent-step" data-agent="health_synthesizer">
                            <div class="agent-icon">🏥</div>
                            <div class="agent-name">Health Synthesizer</div>
                            <div class="agent-desc">Combines findings into diagnosis</div>
                            <div class="agent-status status-waiting">Waiting</div>
                            <div class="progress-bar">
                                <div class="progress-fill"></div>
                            </div>
                        </div>
                    </div>
                </div>

                <!-- Results Panel -->
                <div class="panel results-panel">
                    <h2>📊 Analysis Results</h2>
                    <div class="results-container" id="resultsContainer">
                        <div class="result-card" id="finalResult">
                            <div class="result-header">
                                <div class="result-title">Plant Health Report</div>
                                <div class="result-time" id="resultTime">-</div>
                            </div>
                            <div class="result-content" id="resultContent">
                                Upload an image and click "Analyze Plant Health" to begin the analysis process.
                            </div>
                        </div>
                    </div>
                </div>
            </div>
        </div>

        <!-- Loading Overlay -->
        <div class="loading-overlay" id="loadingOverlay">
            <div class="loading-content">
                <div class="loading-spinner"></div>
                <div class="loading-text">Analyzing Plant Health...</div>
                <div class="loading-subtext">This may take 1-2 minutes</div>
            </div>
        </div>

        <script>
            // Global variables
            let selectedFile = null;
            let analysisInProgress = false;

            // DOM elements
            const uploadZone = document.getElementById('uploadZone');
            const imageInput = document.getElementById('imageInput');
            const imagePreview = document.getElementById('imagePreview');
            const previewImg = document.getElementById('previewImg');
            const analyzeBtn = document.getElementById('analyzeBtn');
            const loadingOverlay = document.getElementById('loadingOverlay');
            const resultsContainer = document.getElementById('resultsContainer');
            const resultContent = document.getElementById('resultContent');
            const resultTime = document.getElementById('resultTime');
            const finalResult = document.getElementById('finalResult');

            // Agent steps
            const agentSteps = {
                preprocessor: document.querySelector('[data-agent="preprocessor"]'),
                visual_analyst: document.querySelector('[data-agent="visual_analyst"]'),
                disease_detector: document.querySelector('[data-agent="disease_detector"]'),
                growth_assessor: document.querySelector('[data-agent="growth_assessor"]'),
                health_synthesizer: document.querySelector('[data-agent="health_synthesizer"]')
            };

            // Upload functionality
            uploadZone.addEventListener('click', () => {
                imageInput.click();
            });

            uploadZone.addEventListener('dragover', (e) => {
                e.preventDefault();
                uploadZone.classList.add('dragover');
            });

            uploadZone.addEventListener('dragleave', () => {
                uploadZone.classList.remove('dragover');
            });

            uploadZone.addEventListener('drop', (e) => {
                e.preventDefault();
                uploadZone.classList.remove('dragover');
                const files = e.dataTransfer.files;
                if (files.length > 0) {
                    handleFileSelect(files[0]);
                }
            });

            imageInput.addEventListener('change', (e) => {
                if (e.target.files.length > 0) {
                    handleFileSelect(e.target.files[0]);
                }
            });

            function handleFileSelect(file) {
                if (!file.type.startsWith('image/')) {
                    alert('Please select an image file');
                    return;
                }

                if (file.size > 10 * 1024 * 1024) { // 10MB limit
                    alert('File size must be less than 10MB');
                    return;
                }

                selectedFile = file;

                // Show preview
                const reader = new FileReader();
                reader.onload = (e) => {
                    previewImg.src = e.target.result;
                    imagePreview.style.display = 'block';
                };
                reader.readAsDataURL(file);

                // Enable analyze button
                analyzeBtn.disabled = false;
                analyzeBtn.textContent = '🔍 Analyze Plant Health';
            }

            // Analysis functionality
            analyzeBtn.addEventListener('click', async () => {
                if (!selectedFile || analysisInProgress) return;

                analysisInProgress = true;
                analyzeBtn.disabled = true;
                analyzeBtn.textContent = '🔄 Analyzing...';

                // Show loading overlay
                loadingOverlay.style.display = 'flex';

                // Reset agent states
                resetAgentStates();

                // Start analysis process
                try {
                    await simulateAnalysisProcess();

                    // Create form data and send to server
                    const formData = new FormData();
                    formData.append('file', selectedFile);

                    const response = await fetch('/api/analyze', {
                        method: 'POST',
                        body: formData
                    });

                    const data = await response.json();

                    // Hide loading
                    loadingOverlay.style.display = 'none';

                    // Show results
                    resultsContainer.style.display = 'block';

                    if (data.success) {
                        finalResult.classList.remove('error');
                        resultContent.textContent = data.result;
                        resultTime.textContent = new Date().toLocaleString();

                        // Mark all agents as completed
                        Object.values(agentSteps).forEach(step => {
                            setAgentStatus(step, 'completed');
                        });
                    } else {
                        finalResult.classList.add('error');
                        resultContent.textContent = `❌ Analysis Failed: ${data.error || 'Unknown error'}`;
                        resultTime.textContent = new Date().toLocaleString();

                        // Mark final agent as error
                        setAgentStatus(agentSteps.health_synthesizer, 'error');
                    }

                } catch (error) {
                    loadingOverlay.style.display = 'none';
                    resultsContainer.style.display = 'block';
                    finalResult.classList.add('error');
                    resultContent.textContent = `❌ Error: ${error.message}`;
                    resultTime.textContent = new Date().toLocaleString();

                    // Mark current agent as error
                    setAgentStatus(Object.values(agentSteps).find(step =>
                        step.querySelector('.agent-status').textContent === 'Active'), 'error');
                } finally {
                    analysisInProgress = false;
                    analyzeBtn.disabled = false;
                    analyzeBtn.textContent = '🔍 Analyze Plant Health';
                }
            });

            async function simulateAnalysisProcess() {
                const agents = Object.values(agentSteps);
                const delays = [1000, 2000, 1500, 1800, 1200]; // Simulated processing times

                for (let i = 0; i < agents.length; i++) {
                    setAgentStatus(agents[i], 'active');

                    // Animate progress bar
                    const progressFill = agents[i].querySelector('.progress-fill');
                    progressFill.style.width = '0%';
                    await new Promise(resolve => setTimeout(resolve, 100));
                    progressFill.style.width = '100%';

                    await new Promise(resolve => setTimeout(resolve, delays[i]));

                    if (i < agents.length - 1) {
                        setAgentStatus(agents[i], 'completed');
                    }
                }
            }

            function setAgentStatus(agentElement, status) {
                const statusElement = agentElement.querySelector('.agent-status');
                const progressFill = agentElement.querySelector('.progress-fill');

                // Remove all status classes
                agentElement.classList.remove('active', 'completed', 'error');
                statusElement.classList.remove('status-waiting', 'status-active', 'status-completed', 'status-error');

                // Add new status
                switch (status) {
                    case 'active':
                        agentElement.classList.add('active');
                        statusElement.classList.add('status-active');
                        statusElement.textContent = 'Active';
                        progressFill.style.width = '50%';
                        break;
                    case 'completed':
                        agentElement.classList.add('completed');
                        statusElement.classList.add('status-completed');
                        statusElement.textContent = 'Completed';
                        progressFill.style.width = '100%';
                        break;
                    case 'error':
                        agentElement.classList.add('error');
                        statusElement.classList.add('status-error');
                        statusElement.textContent = 'Error';
                        progressFill.style.width = '100%';
                        break;
                    default:
                        statusElement.classList.add('status-waiting');
                        statusElement.textContent = 'Waiting';
                        progressFill.style.width = '0%';
                }
            }

            function resetAgentStates() {
                Object.values(agentSteps).forEach(agent => {
                    setAgentStatus(agent, 'waiting');
                });
            }

            // Initialize
            resetAgentStates();
        </script>
    </body>
    </html>
    """
    return HTMLResponse(content=html_content)

@app.post("/api/analyze", response_model=HealthAnalysisResponse)
async def analyze_plant_health(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...)
):
    """Analyze plant health from uploaded image"""
    try:
        # Validate file type
        if not file.content_type.startswith('image/'):
            raise HTTPException(status_code=400, detail="File must be an image")

        # Save uploaded file temporarily
        with tempfile.NamedTemporaryFile(delete=False, suffix=Path(file.filename).suffix) as temp_file:
            content = await file.read()
            temp_file.write(content)
            temp_file_path = temp_file.name

        try:
            # Get crew instance
            crew = get_crew()

            # Run analysis
            logger.info(f"Starting analysis for uploaded file: {file.filename}")
            result = crew.analyze_plant_health(temp_file_path)

            if result["success"]:
                # Save report file
                report_filename = f"plant_health_report_{Path(file.filename).stem}.txt"
                report_path = f"reports/{report_filename}"

                # Ensure reports directory exists
                os.makedirs("reports", exist_ok=True)

                with open(report_path, 'w') as f:
                    f.write("PLANT HEALTH ANALYSIS REPORT\n")
                    f.write("="*50 + "\n\n")
                    f.write(f"Image: {file.filename}\n")
                    f.write(f"Analysis Date: {__import__('datetime').datetime.now()}\n\n")
                    f.write("RESULTS:\n")
                    f.write("-"*20 + "\n")
                    f.write(result["result"])

                # Clean up temp file in background
                background_tasks.add_task(os.unlink, temp_file_path)

                return HealthAnalysisResponse(
                    success=True,
                    result=result["result"],
                    report_file=report_path
                )
            else:
                # Clean up temp file
                os.unlink(temp_file_path)
                raise HTTPException(status_code=500, detail=result.get("error", "Analysis failed"))

        except Exception as e:
            # Clean up temp file
            if os.path.exists(temp_file_path):
                os.unlink(temp_file_path)
            raise e

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Analysis error: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")

@app.get("/api/status", response_model=AgentStatusResponse)
async def get_agent_status():
    """Get status of all agents"""
    try:
        crew = get_crew()
        agents = crew.get_agent_status()
        return AgentStatusResponse(agents=agents)
    except Exception as e:
        logger.error(f"Status error: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to get agent status: {str(e)}")

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy", "service": "Plant Health Analysis System"}

if __name__ == "__main__":
    print("🌱 Plant Health Analysis System")
    print("📊 Process Visualization Interface")
    print("=" * 50)
    print("🚀 Starting server on http://localhost:8000")
    print("📱 Open your browser and navigate to the URL above")
    print("=" * 50)

    uvicorn.run(
        "api:app",
        host="localhost",
        port=8000,
        reload=DEBUG,
        log_level="info" if not DEBUG else "debug"
    )
