import pdfplumber
import os
from dotenv import load_dotenv
from groq import Groq
import google.generativeai as genai
from typing import List
import json
from pydantic import BaseModel
from flask import Flask, request, jsonify, send_file
from flask_cors import CORS
import uuid
import traceback
import zipfile
import tempfile
from datetime import datetime

load_dotenv()

# Initialize APIs
groq_api_key = os.getenv("GROQ_API_KEY")
gemini_api_key = os.getenv("GEMINI_API_KEY")

if not groq_api_key:
    print("ERROR: GROQ_API_KEY not found!")
if not gemini_api_key:
    print("ERROR: GEMINI_API_KEY not found!")

groq_client = Groq(api_key=groq_api_key)
genai.configure(api_key=gemini_api_key)
gemini_model = genai.GenerativeModel('gemini-pro')

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

def get_all_info(info: str) -> Candidate:
    try:
        chat_completion = groq_client.chat.completions.create(
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
        return Candidate.model_validate_json(chat_completion.choices[0].message.content)
    except Exception as e:
        print(f"Error in resume parsing: {str(e)}")
        raise e

def generate_website_code(data, style="professional"):
    """Generate complete website code based on parsed resume data and selected style"""
    
    templates = {
        "professional": {
            "colors": {
                "primary": "#2563eb",
                "secondary": "#64748b",
                "accent": "#0f172a",
                "background": "#ffffff",
                "text": "#1e293b"
            },
            "fonts": "font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;",
            "style_class": "professional"
        },
        "futuristic": {
            "colors": {
                "primary": "#00d4ff",
                "secondary": "#7c3aed",
                "accent": "#ec4899",
                "background": "#0f0f23",
                "text": "#ffffff"
            },
            "fonts": "font-family: 'Orbitron', 'Courier New', monospace;",
            "style_class": "futuristic"
        },
        "playful": {
            "colors": {
                "primary": "#f59e0b",
                "secondary": "#ec4899",
                "accent": "#10b981",
                "background": "#fef3c7",
                "text": "#374151"
            },
            "fonts": "font-family: 'Poppins', 'Comic Sans MS', cursive;",
            "style_class": "playful"
        }
    }
    
    theme = templates.get(style, templates["professional"])
    
    # Generate HTML
    html_content = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{data['name']} - Portfolio</title>
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&family=Orbitron:wght@400;700;900&family=Poppins:wght@300;400;500;600;700&display=swap" rel="stylesheet">
    <link rel="stylesheet" href="styles.css">
</head>
<body class="{theme['style_class']}">
    <div class="container">
        <!-- Header Section -->
        <header class="header" id="header">
            <div class="profile-section">
                <div class="profile-image">
                    <div class="avatar">{data['name'][:2].upper()}</div>
                </div>
                <div class="profile-info">
                    <h1 class="name">{data['name']}</h1>
                    <p class="title">Software Developer</p>
                </div>
            </div>
            <nav class="navigation">
                <a href="#about" class="nav-link">About</a>
                <a href="#experience" class="nav-link">Experience</a>
                <a href="#projects" class="nav-link">Projects</a>
                <a href="#skills" class="nav-link">Skills</a>
                <a href="#contact" class="nav-link">Contact</a>
            </nav>
        </header>

        <!-- About Section -->
        <section class="section" id="about">
            <h2 class="section-title">About Me</h2>
            <div class="about-content">
                <p class="about-text">Passionate developer with expertise in modern technologies and a strong foundation in software development.</p>
            </div>
        </section>

        <!-- Experience Section -->
        <section class="section" id="experience">
            <h2 class="section-title">Experience</h2>
            <div class="experience-grid">
                {generate_experience_html(data.get('Experience', []))}
            </div>
        </section>

        <!-- Projects Section -->
        <section class="section" id="projects">
            <h2 class="section-title">Projects</h2>
            <div class="projects-grid">
                {generate_projects_html(data.get('projects', []))}
            </div>
        </section>

        <!-- Skills Section -->
        <section class="section" id="skills">
            <h2 class="section-title">Skills</h2>
            <div class="skills-grid">
                {generate_skills_html(data.get('skills', []))}
            </div>
        </section>

        <!-- Education Section -->
        <section class="section" id="education">
            <h2 class="section-title">Education</h2>
            <div class="education-grid">
                {generate_education_html(data.get('education', []))}
            </div>
        </section>

        <!-- Contact Section -->
        <section class="section" id="contact">
            <h2 class="section-title">Contact</h2>
            <div class="contact-grid">
                {generate_contact_html(data.get('Contact_Info', {}))}
            </div>
        </section>
    </div>

    <script src="script.js"></script>
</body>
</html>"""

    # Generate CSS
    css_content = generate_css_content(theme, style)
    
    # Generate JavaScript
    js_content = generate_js_content(style)
    
    return {
        "html": html_content,
        "css": css_content,
        "js": js_content
    }

def generate_experience_html(experiences):
    if not experiences:
        return "<p>No experience data available</p>"
    
    html = ""
    for exp in experiences:
        html += f"""
        <div class="experience-card" data-component="experience-card">
            <h3 class="company-name">{exp.get('Company', 'Unknown Company')}</h3>
            <p class="position">{exp.get('Position', 'Unknown Position')}</p>
            <div class="skills-used">
                {', '.join(exp.get('Skills', []))}
            </div>
        </div>
        """
    return html

def generate_projects_html(projects):
    if not projects:
        return "<p>No projects data available</p>"
    
    html = ""
    for project in projects:
        html += f"""
        <div class="project-card" data-component="project-card">
            <h3 class="project-title">{project.get('title', 'Untitled Project')}</h3>
            <p class="project-description">{project.get('desc', 'No description available')}</p>
            <div class="tech-stack">
                {', '.join(project.get('tech', []))}
            </div>
        </div>
        """
    return html

def generate_skills_html(skills):
    if not skills:
        return "<p>No skills data available</p>"
    
    html = ""
    for skill in skills:
        html += f'<div class="skill-tag" data-component="skill-tag">{skill}</div>'
    return html

def generate_education_html(education):
    if not education:
        return "<p>No education data available</p>"
    
    html = ""
    for edu in education:
        html += f"""
        <div class="education-card" data-component="education-card">
            <h3 class="institute-name">{edu.get('Institute_name', 'Unknown Institute')}</h3>
            <p class="degree">{edu.get('Degree_name', 'Unknown Degree')}</p>
            <p class="marks">Marks: {edu.get('Marks', 'N/A')}</p>
        </div>
        """
    return html

def generate_contact_html(contact_info):
    if not contact_info:
        return "<p>No contact information available</p>"
    
    html = ""
    for key, value in contact_info.items():
        html += f"""
        <div class="contact-item" data-component="contact-item">
            <strong>{key}:</strong> {value}
        </div>
        """
    return html

def generate_css_content(theme, style):
    base_css = f"""
/* Reset and Base Styles */
* {{
    margin: 0;
    padding: 0;
    box-sizing: border-box;
}}

body {{
    {theme['fonts']}
    background-color: {theme['colors']['background']};
    color: {theme['colors']['text']};
    line-height: 1.6;
    overflow-x: hidden;
}}

.container {{
    max-width: 1200px;
    margin: 0 auto;
    padding: 20px;
}}

/* Header Styles */
.header {{
    display: flex;
    justify-content: space-between;
    align-items: center;
    padding: 2rem 0;
    border-bottom: 2px solid {theme['colors']['primary']};
    margin-bottom: 3rem;
}}

.profile-section {{
    display: flex;
    align-items: center;
    gap: 1.5rem;
}}

.avatar {{
    width: 80px;
    height: 80px;
    background: linear-gradient(135deg, {theme['colors']['primary']}, {theme['colors']['secondary']});
    border-radius: 50%;
    display: flex;
    align-items: center;
    justify-content: center;
    font-size: 1.5rem;
    font-weight: bold;
    color: white;
}}

.name {{
    font-size: 2.5rem;
    font-weight: 700;
    color: {theme['colors']['primary']};
    margin-bottom: 0.5rem;
}}

.title {{
    font-size: 1.2rem;
    color: {theme['colors']['secondary']};
}}

.navigation {{
    display: flex;
    gap: 2rem;
}}

.nav-link {{
    text-decoration: none;
    color: {theme['colors']['text']};
    font-weight: 500;
    padding: 0.5rem 1rem;
    border-radius: 25px;
    transition: all 0.3s ease;
}}

.nav-link:hover {{
    background-color: {theme['colors']['primary']};
    color: white;
}}

/* Section Styles */
.section {{
    margin-bottom: 4rem;
    padding: 2rem;
    background: rgba(255, 255, 255, 0.05);
    border-radius: 15px;
    backdrop-filter: blur(10px);
    border: 1px solid rgba(255, 255, 255, 0.1);
}}

.section-title {{
    font-size: 2rem;
    font-weight: 600;
    color: {theme['colors']['primary']};
    margin-bottom: 2rem;
    text-align: center;
}}

/* Card Styles */
.experience-card, .project-card, .education-card {{
    background: rgba(255, 255, 255, 0.1);
    padding: 1.5rem;
    border-radius: 10px;
    margin-bottom: 1.5rem;
    border-left: 4px solid {theme['colors']['accent']};
    transition: transform 0.3s ease, box-shadow 0.3s ease;
    cursor: pointer;
}}

.experience-card:hover, .project-card:hover, .education-card:hover {{
    transform: translateY(-5px);
    box-shadow: 0 10px 25px rgba(0, 0, 0, 0.2);
}}

.company-name, .project-title, .institute-name {{
    font-size: 1.3rem;
    font-weight: 600;
    color: {theme['colors']['primary']};
    margin-bottom: 0.5rem;
}}

.position, .degree {{
    font-size: 1.1rem;
    color: {theme['colors']['secondary']};
    margin-bottom: 1rem;
}}

.skills-used, .tech-stack {{
    display: flex;
    flex-wrap: wrap;
    gap: 0.5rem;
    font-size: 0.9rem;
    color: {theme['colors']['accent']};
}}

/* Skills Grid */
.skills-grid {{
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(150px, 1fr));
    gap: 1rem;
}}

.skill-tag {{
    background: linear-gradient(135deg, {theme['colors']['primary']}, {theme['colors']['secondary']});
    color: white;
    padding: 0.8rem 1.2rem;
    border-radius: 25px;
    text-align: center;
    font-weight: 500;
    transition: transform 0.3s ease;
    cursor: pointer;
}}

.skill-tag:hover {{
    transform: scale(1.05);
}}

/* Contact Styles */
.contact-item {{
    background: rgba(255, 255, 255, 0.1);
    padding: 1rem;
    border-radius: 8px;
    margin-bottom: 1rem;
    border-left: 3px solid {theme['colors']['primary']};
}}

/* Responsive Design */
@media (max-width: 768px) {{
    .header {{
        flex-direction: column;
        gap: 2rem;
    }}
    
    .navigation {{
        flex-wrap: wrap;
        justify-content: center;
    }}
    
    .name {{
        font-size: 2rem;
    }}
    
    .section {{
        padding: 1rem;
    }}
}}
"""

    # Add style-specific CSS
    if style == "futuristic":
        base_css += f"""
/* Futuristic Animations */
@keyframes glow {{
    0%, 100% {{ box-shadow: 0 0 5px {theme['colors']['primary']}; }}
    50% {{ box-shadow: 0 0 20px {theme['colors']['primary']}, 0 0 30px {theme['colors']['accent']}; }}
}}

.avatar {{
    animation: glow 2s infinite;
}}

.section {{
    background: linear-gradient(135deg, rgba(0, 212, 255, 0.1), rgba(124, 58, 237, 0.1));
}}
"""
    elif style == "playful":
        base_css += f"""
/* Playful Animations */
@keyframes bounce {{
    0%, 20%, 50%, 80%, 100% {{ transform: translateY(0); }}
    40% {{ transform: translateY(-10px); }}
    60% {{ transform: translateY(-5px); }}
}}

.skill-tag:hover {{
    animation: bounce 0.6s;
}}

.section {{
    background: linear-gradient(45deg, rgba(245, 158, 11, 0.1), rgba(236, 72, 153, 0.1));
}}
"""

    return base_css

def generate_js_content(style):
    base_js = """
// Smooth scrolling for navigation links
document.querySelectorAll('.nav-link').forEach(link => {
    link.addEventListener('click', function(e) {
        e.preventDefault();
        const targetId = this.getAttribute('href');
        const targetSection = document.querySelector(targetId);
        if (targetSection) {
            targetSection.scrollIntoView({
                behavior: 'smooth',
                block: 'start'
            });
        }
    });
});

// Component selection for Gemini editing
let selectedComponent = null;

document.querySelectorAll('[data-component]').forEach(component => {
    component.addEventListener('click', function(e) {
        e.stopPropagation();
        
        // Remove previous selection
        if (selectedComponent) {
            selectedComponent.classList.remove('selected-component');
        }
        
        // Add selection to current component
        this.classList.add('selected-component');
        selectedComponent = this;
        
        // Show edit options
        showEditOptions(this);
    });
});

// Remove selection when clicking outside
document.addEventListener('click', function() {
    if (selectedComponent) {
        selectedComponent.classList.remove('selected-component');
        selectedComponent = null;
        hideEditOptions();
    }
});

function showEditOptions(component) {
    // Remove existing edit panel
    const existingPanel = document.querySelector('.edit-panel');
    if (existingPanel) {
        existingPanel.remove();
    }
    
    // Create edit panel
    const editPanel = document.createElement('div');
    editPanel.className = 'edit-panel';
    editPanel.innerHTML = `
        <div class="edit-panel-content">
            <h3>Edit Component</h3>
            <textarea id="edit-instructions" placeholder="Describe how you want to modify this component..."></textarea>
            <div class="edit-buttons">
                <button onclick="applyGeminiEdit()">Apply Changes</button>
                <button onclick="hideEditOptions()">Cancel</button>
            </div>
        </div>
    `;
    
    document.body.appendChild(editPanel);
}

function hideEditOptions() {
    const editPanel = document.querySelector('.edit-panel');
    if (editPanel) {
        editPanel.remove();
    }
}

async function applyGeminiEdit() {
    const instructions = document.getElementById('edit-instructions').value;
    if (!instructions || !selectedComponent) return;
    
    try {
        const response = await fetch('/modify-component', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                component_html: selectedComponent.outerHTML,
                instructions: instructions,
                component_type: selectedComponent.dataset.component
            })
        });
        
        const result = await response.json();
        if (result.success) {
            selectedComponent.outerHTML = result.modified_html;
            hideEditOptions();
            
            // Show success message
            showNotification('Component updated successfully!', 'success');
        } else {
            showNotification('Failed to update component: ' + result.error, 'error');
        }
    } catch (error) {
        showNotification('Error updating component: ' + error.message, 'error');
    }
}

function showNotification(message, type) {
    const notification = document.createElement('div');
    notification.className = `notification ${type}`;
    notification.textContent = message;
    document.body.appendChild(notification);
    
    setTimeout(() => {
        notification.remove();
    }, 3000);
}

// Add CSS for edit functionality
const editStyles = `
.selected-component {
    outline: 3px solid #00d4ff !important;
    outline-offset: 2px;
    position: relative;
}

.edit-panel {
    position: fixed;
    top: 50%;
    left: 50%;
    transform: translate(-50%, -50%);
    background: white;
    padding: 2rem;
    border-radius: 10px;
    box-shadow: 0 10px 30px rgba(0, 0, 0, 0.3);
    z-index: 1000;
    min-width: 400px;
}

.edit-panel-content h3 {
    margin-bottom: 1rem;
    color: #333;
}

.edit-panel textarea {
    width: 100%;
    height: 100px;
    margin-bottom: 1rem;
    padding: 0.5rem;
    border: 1px solid #ddd;
    border-radius: 5px;
    resize: vertical;
}

.edit-buttons {
    display: flex;
    gap: 1rem;
    justify-content: flex-end;
}

.edit-buttons button {
    padding: 0.5rem 1rem;
    border: none;
    border-radius: 5px;
    cursor: pointer;
    font-weight: 500;
}

.edit-buttons button:first-child {
    background: #00d4ff;
    color: white;
}

.edit-buttons button:last-child {
    background: #6b7280;
    color: white;
}

.notification {
    position: fixed;
    top: 20px;
    right: 20px;
    padding: 1rem 2rem;
    border-radius: 5px;
    color: white;
    font-weight: 500;
    z-index: 1001;
}

.notification.success {
    background: #10b981;
}

.notification.error {
    background: #ef4444;
}
`;

const styleSheet = document.createElement('style');
styleSheet.textContent = editStyles;
document.head.appendChild(styleSheet);
"""

    return base_js

app = Flask(__name__)
CORS(app)

# Create directories
UPLOAD_FOLDER = 'uploads'
GENERATED_FOLDER = 'generated_websites'
for folder in [UPLOAD_FOLDER, GENERATED_FOLDER]:
    if not os.path.exists(folder):
        os.makedirs(folder)

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['GENERATED_FOLDER'] = GENERATED_FOLDER
ALLOWED_EXTENSIONS = {'pdf'}

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@app.route('/health', methods=['GET'])
def health_check():
    return jsonify({'status': 'healthy', 'message': 'Resume parser is running'})

@app.route('/', methods=['POST'])
def upload_pdf():
    try:
        if 'file' not in request.files:
            return jsonify({'error': 'No file part'}), 400
        
        file = request.files['file']
        if file.filename == '' or not allowed_file(file.filename):
            return jsonify({'error': 'Invalid file'}), 400

        # Save and process file
        unique_filename = f"{uuid.uuid4()}_{file.filename}"
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], unique_filename)
        
        try:
            file.save(filepath)
            
            # Extract text from PDF
            with pdfplumber.open(filepath) as pdf:
                content = pdf.pages[0].extract_text()
            
            if not content:
                return jsonify({'error': 'Could not extract text from PDF'}), 400
            
            # Parse with GROQ
            info = get_all_info(content)
            
            # Convert to dict for website generation
            data = {
                "name": info.name,
                "education": [{"Institute_name": edu.Institute_name, "Degree_name": edu.Degree_name, "Marks": edu.marks} for edu in info.Education],
                "Contact_Info": info.Contact_Info,
                "skills": info.Skills,
                "projects": [{"title": p.project_name, "desc": p.about_project, "tech": p.skills_used} for p in info.Projects],
                "Experience": [{"Company": exp.Company_name, "Position": exp.Position_name, "Skills": exp.skills_used} for exp in info.Experience],
                "Achievements": [{"achievement_name": a.Achivement_name, "institute_name": a.institute_name, "description": a.about} for a in info.Achivements],
                "Position_of_responsibility": [{"position_name": p.Position_name, "soc_name": p.Society_name, "description": p.Description} for p in info.Position_of_Responsibility]
            }
            
            return jsonify({
                'success': True,
                'data': data,
                'message': 'Resume parsed successfully'
            })
            
        finally:
            if os.path.exists(filepath):
                os.remove(filepath)
                
    except Exception as e:
        print(f"Error: {str(e)}")
        return jsonify({'error': f'Failed to process resume: {str(e)}'}), 500

@app.route('/generate-website', methods=['POST'])
def generate_website():
    try:
        request_data = request.get_json()
        resume_data = request_data.get('data')
        style = request_data.get('style', 'professional')
        
        if not resume_data:
            return jsonify({'error': 'No resume data provided'}), 400
        
        # Generate website code
        website_code = generate_website_code(resume_data, style)
        
        # Create unique folder for this website
        website_id = str(uuid.uuid4())
        website_folder = os.path.join(app.config['GENERATED_FOLDER'], website_id)
        os.makedirs(website_folder)
        
        # Save files
        with open(os.path.join(website_folder, 'index.html'), 'w', encoding='utf-8') as f:
            f.write(website_code['html'])
        
        with open(os.path.join(website_folder, 'styles.css'), 'w', encoding='utf-8') as f:
            f.write(website_code['css'])
        
        with open(os.path.join(website_folder, 'script.js'), 'w', encoding='utf-8') as f:
            f.write(website_code['js'])
        
        return jsonify({
            'success': True,
            'website_id': website_id,
            'preview_url': f'/preview/{website_id}',
            'download_url': f'/download/{website_id}'
        })
        
    except Exception as e:
        print(f"Error generating website: {str(e)}")
        return jsonify({'error': f'Failed to generate website: {str(e)}'}), 500

@app.route('/modify-component', methods=['POST'])
def modify_component():
    try:
        request_data = request.get_json()
        component_html = request_data.get('component_html')
        instructions = request_data.get('instructions')
        component_type = request_data.get('component_type')
        
        if not all([component_html, instructions, component_type]):
            return jsonify({'error': 'Missing required data'}), 400
        
        # Use Gemini to modify the component
        prompt = f"""
        You are a web developer. I have an HTML component that I want to modify based on user instructions.
        
        Current HTML component:
        {component_html}
        
        Component type: {component_type}
        
        User instructions: {instructions}
        
        Please provide the modified HTML component that follows the user's instructions while maintaining the same structure and CSS classes. Only return the HTML code, no explanations.
        """
        
        response = gemini_model.generate_content(prompt)
        modified_html = response.text.strip()
        
        # Clean up the response (remove markdown formatting if present)
        if modified_html.startswith('\`\`\`html'):
            modified_html = modified_html[7:]
        if modified_html.endswith('\`\`\`'):
            modified_html = modified_html[:-3]
        
        return jsonify({
            'success': True,
            'modified_html': modified_html.strip()
        })
        
    except Exception as e:
        print(f"Error modifying component: {str(e)}")
        return jsonify({'error': f'Failed to modify component: {str(e)}'}), 500

@app.route('/preview/<website_id>')
def preview_website(website_id):
    try:
        website_folder = os.path.join(app.config['GENERATED_FOLDER'], website_id)
        index_path = os.path.join(website_folder, 'index.html')
        
        if not os.path.exists(index_path):
            return "Website not found", 404
        
        with open(index_path, 'r', encoding='utf-8') as f:
            return f.read()
            
    except Exception as e:
        return f"Error loading preview: {str(e)}", 500

@app.route('/download/<website_id>')
def download_website(website_id):
    try:
        website_folder = os.path.join(app.config['GENERATED_FOLDER'], website_id)
        
        if not os.path.exists(website_folder):
            return jsonify({'error': 'Website not found'}), 404
        
        # Create zip file
        zip_path = os.path.join(tempfile.gettempdir(), f'portfolio_{website_id}.zip')
        
        with zipfile.ZipFile(zip_path, 'w') as zipf:
            for file_name in ['index.html', 'styles.css', 'script.js']:
                file_path = os.path.join(website_folder, file_name)
                if os.path.exists(file_path):
                    zipf.write(file_path, file_name)
        
        return send_file(zip_path, as_attachment=True, download_name=f'portfolio_website.zip')
        
    except Exception as e:
        return jsonify({'error': f'Failed to create download: {str(e)}'}), 500

if __name__ == '__main__':
    print("Starting Portfolio Generator Server...")
    print(f"GROQ API configured: {'Yes' if groq_api_key else 'No'}")
    print(f"Gemini API configured: {'Yes' if gemini_api_key else 'No'}")
    app.run(debug=True, host='0.0.0.0', port=5000)
