import pdfplumber
import os
from dotenv import load_dotenv
from groq import Groq
from typing import List
import json
from pydantic import BaseModel
from flask import Flask, request, jsonify
from flask_cors import CORS
import uuid
import traceback

# Load environment variables
load_dotenv()

# Debug environment loading
print("=== ENVIRONMENT DEBUG ===")
print(f"Current working directory: {os.getcwd()}")
print(f".env file exists: {os.path.exists('.env')}")

if os.path.exists('.env'):
    with open('.env', 'r') as f:
        env_content = f.read()
        print(f".env file content: {env_content}")

groq_api_key = os.getenv("GROQ_API_KEY")
print(f"GROQ_API_KEY loaded: {groq_api_key is not None}")
if groq_api_key:
    print(f"API Key first 10 chars: {groq_api_key[:10]}...")
    print(f"API Key length: {len(groq_api_key)}")
else:
    print("ERROR: GROQ_API_KEY is None!")

# Test GROQ client initialization
try:
    client = Groq(api_key=groq_api_key)
    print("GROQ client initialized successfully")
except Exception as e:
    print(f"ERROR initializing GROQ client: {e}")
    client = None

print("=== END ENVIRONMENT DEBUG ===\n")

class Project(BaseModel):
    project_name: str
    about_project: str
    skills_used: list[str]

class Achivements(BaseModel):
    Achivement_name: str
    institute_name: str
    about: str

class Experience(BaseModel):
    Position_name: str
    Company_name: str
    skills_used: list[str]

class Education(BaseModel):
    Institute_name: str
    Degree_name: str
    marks: str

class Position_of_Responsibility(BaseModel):
    Position_name: str
    Society_name: str
    Description: str

class Candidate(BaseModel):
    name: str
    Education: List[Education]
    Projects: List[Project]
    Experience: List[Experience]
    Achivements: List[Achivements]
    Skills: List[str]
    Position_of_Responsibility: List[Position_of_Responsibility]
    Contact_Info: dict

def test_groq_connection():
    """Test GROQ API connection with a simple request"""
    try:
        print("Testing GROQ API connection...")
        if not client:
            raise Exception("GROQ client not initialized")
            
        response = client.chat.completions.create(
            messages=[
                {"role": "user", "content": "Say 'Hello, GROQ API is working!'"}
            ],
            model="llama-3.3-70b-versatile",
            temperature=0,
        )
        print(f"GROQ API test successful: {response.choices[0].message.content}")
        return True
    except Exception as e:
        print(f"GROQ API test failed: {e}")
        print(f"Full error: {traceback.format_exc()}")
        return False

def get_all_info(info: str) -> Candidate:
    try:
        print(f"=== STARTING AI PROCESSING ===")
        print(f"Input text length: {len(info)}")
        print(f"Input text preview: {info[:200]}...")
        
        if not client:
            raise Exception("GROQ client not initialized")
        
        print("Sending request to GROQ API...")
        chat_completion = client.chat.completions.create(
            messages=[
                {
                    "role": "system",
                    "content": "You are a resume parser that extracts information from resume.\n"
                    f" The JSON object must use the schema: {json.dumps(Candidate.model_json_schema(), indent=2)}",
                },
                {
                    "role": "user",
                    "content": f"use this {info}",
                },
            ],
            model="llama-3.3-70b-versatile",
            temperature=0,
            stream=False,
            response_format={"type": "json_object"},
        )
        print("GROQ API response received successfully")
        print(f"Response content: {chat_completion.choices[0].message.content[:200]}...")
        
        result = Candidate.model_validate_json(chat_completion.choices[0].message.content)
        print("Pydantic validation successful")
        return result
        
    except Exception as e:
        print(f"ERROR in get_all_info: {str(e)}")
        print(f"Full traceback: {traceback.format_exc()}")
        raise e

app = Flask(__name__)
CORS(app)

# Create uploads directory if it doesn't exist
UPLOAD_FOLDER = 'uploads'
if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)
    print(f"Created uploads directory: {UPLOAD_FOLDER}")

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
ALLOWED_EXTENSIONS = {'pdf'}

def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@app.route('/health', methods=['GET'])
def health_check():
    return jsonify({'status': 'healthy', 'message': 'Resume parser is running'})

@app.route('/test-groq', methods=['GET'])
def test_groq_endpoint():
    """Test endpoint to check GROQ API connectivity"""
    success = test_groq_connection()
    if success:
        return jsonify({'status': 'success', 'message': 'GROQ API is working'})
    else:
        return jsonify({'status': 'error', 'message': 'GROQ API connection failed'}), 500

@app.route('/', methods=['POST'])
def upload_pdf():
    print("\n" + "="*50)
    print("NEW UPLOAD REQUEST RECEIVED")
    print("="*50)
    
    try:
        # Step 1: Check file in request
        print("STEP 1: Checking file in request...")
        if 'file' not in request.files:
            print("❌ ERROR: No file part in request")
            return jsonify({'error': 'No file part'}), 400
        print("✅ File part found in request")
        
        # Step 2: Get file object
        print("STEP 2: Getting file object...")
        file = request.files['file']
        print(f"✅ File object retrieved: {file.filename}")
        print(f"   File size: {file.content_length if hasattr(file, 'content_length') else 'Unknown'}")
        print(f"   File type: {file.content_type}")

        if file.filename == '':
            print("❌ ERROR: No file selected")
            return jsonify({'error': 'No selected file'}), 400

        if not file or not allowed_file(file.filename):
            print(f"❌ ERROR: Invalid file type for {file.filename}")
            return jsonify({'error': 'Invalid file type. Only PDF files are allowed.'}), 400

        # Step 3: Save file
        print("STEP 3: Saving file...")
        unique_filename = f"{uuid.uuid4()}_{file.filename}"
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], unique_filename)
        print(f"   Saving to: {filepath}")
        
        try:
            file.save(filepath)
            file_exists = os.path.exists(filepath)
            file_size = os.path.getsize(filepath) if file_exists else 0
            print(f"✅ File saved successfully: {file_exists}")
            print(f"   File size on disk: {file_size} bytes")
            
            if file_size == 0:
                print("❌ ERROR: Saved file is empty!")
                return jsonify({'error': 'Uploaded file is empty'}), 400
            
            # Step 4: Process PDF
            print("STEP 4: Processing PDF...")
            try:
                with pdfplumber.open(filepath) as pdf:
                    print(f"✅ PDF opened successfully")
                    print(f"   Number of pages: {len(pdf.pages)}")
                    
                    if len(pdf.pages) == 0:
                        print("❌ ERROR: PDF has no pages")
                        return jsonify({'error': 'PDF file has no pages'}), 400
                    
                    first_page = pdf.pages[0]
                    print("   Extracting text from first page...")
                    
                    content = first_page.extract_text(
                        x_tolerance=3, 
                        x_tolerance_ratio=None, 
                        y_tolerance=3, 
                        layout=False, 
                        x_density=7.25, 
                        y_density=13, 
                        line_dir_render=None, 
                        char_dir_render=None
                    )
                    
                    print(f"✅ Text extraction completed")
                    print(f"   Extracted text length: {len(content) if content else 0}")
                    
                    if not content or len(content.strip()) == 0:
                        print("❌ ERROR: No text extracted from PDF")
                        print("   This might be a scanned PDF or image-based PDF")
                        return jsonify({'error': 'Could not extract text from PDF. Please ensure it\'s a text-based PDF, not a scanned image.'}), 400
                    
                    print(f"   First 200 characters: {repr(content[:200])}")
                    
            except Exception as pdf_error:
                print(f"❌ ERROR in PDF processing: {pdf_error}")
                print(f"   Full traceback: {traceback.format_exc()}")
                return jsonify({'error': f'PDF processing failed: {str(pdf_error)}'}), 400
            
            # Step 5: AI Processing
            print("STEP 5: Starting AI processing...")
            try:
                info = get_all_info(content)
                print("✅ AI processing completed successfully")
                
                # Step 6: Build response
                print("STEP 6: Building response...")
                candidate_name = info.name
                print(f"   Candidate name: {candidate_name}")

                skill_list = [skill for skill in info.Skills]
                education_json = [{
                    "Institute_name": edu.Institute_name, 
                    "Degree_name": edu.Degree_name, 
                    "Marks": edu.marks
                } for edu in info.Education]
                
                experience_json = [{
                    "Company": exp.Company_name, 
                    "Position": exp.Position_name, 
                    "Skills": list(exp.skills_used)
                } for exp in info.Experience]
                
                achievement_json = [{
                    "achievement_name": achievement.Achivement_name, 
                    "institute_name": achievement.institute_name, 
                    "description": achievement.about
                } for achievement in info.Achivements]
                
                position_of_responsibility_json = [{
                    "position_name": responsibility.Position_name, 
                    "soc_name": responsibility.Society_name, 
                    "description": responsibility.Description
                } for responsibility in info.Position_of_Responsibility]
                
                project_json = [{
                    "title": project.project_name, 
                    "desc": project.about_project, 
                    "tech": list(project.skills_used)
                } for project in info.Projects]

                data = {
                    "name": candidate_name,
                    "education": education_json,
                    "Contact_Info": info.Contact_Info,
                    "skills": skill_list,
                    "projects": project_json,
                    "Experience": experience_json,
                    "Achievements": achievement_json,
                    "Position_of_responsibility": position_of_responsibility_json
                }
                
                print("✅ Response data structure created successfully")
                print(f"   Response keys: {list(data.keys())}")
                print("✅ REQUEST COMPLETED SUCCESSFULLY")
                return jsonify(data)
                
            except Exception as ai_error:
                print(f"❌ ERROR in AI processing: {ai_error}")
                print(f"   Full traceback: {traceback.format_exc()}")
                return jsonify({'error': f'AI processing failed: {str(ai_error)}'}), 500
            
        finally:
            # Cleanup
            if os.path.exists(filepath):
                os.remove(filepath)
                print(f"🧹 Cleaned up file: {unique_filename}")
                
    except Exception as e:
        print(f"\n❌ UNEXPECTED ERROR OCCURRED")
        print(f"Error type: {type(e).__name__}")
        print(f"Error message: {str(e)}")
        print(f"Full traceback:")
        print(traceback.format_exc())
        print("="*50)
        
        return jsonify({'error': f'Unexpected error: {str(e)}'}), 500

if __name__ == '__main__':
    print("\n" + "="*50)
    print("STARTING FLASK SERVER")
    print("="*50)
    print(f"Upload folder: {UPLOAD_FOLDER}")
    print(f"GROQ API Key configured: {'Yes' if groq_api_key else 'No'}")
    
    # Test GROQ connection on startup
    if groq_api_key:
        test_groq_connection()
    
    print("="*50)
    print("SERVER READY - Listening on http://localhost:5000")
    print("Test endpoints:")
    print("  - Health: http://localhost:5000/health")
    print("  - GROQ Test: http://localhost:5000/test-groq")
    print("="*50)
    
    app.run(debug=True, host='0.0.0.0', port=5000)
