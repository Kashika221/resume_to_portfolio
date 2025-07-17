import pdfplumber
import os
from dotenv import load_dotenv
from groq import Groq
from langchain_groq import ChatGroq
from typing import List
import json
from pydantic import BaseModel
from flask import Flask, render_template

load_dotenv()

client = Groq(
    api_key = os.getenv("GROQ_API_KEY"),
)

class Project(BaseModel):
    project_name : str
    about_project : str
    skills_used : list[str]

class Experience(BaseModel):
    Position_name : str
    Company_name : str
    skills_used : list[str]

class Education(BaseModel):
    Institute_name : str
    Degree_name : str
    marks : str

class Candidate(BaseModel):
    name : str
    Education : List[Education]
    Projects : List[Project]
    Experience : List[Experience]
    Skills : List[str]
    Contact_Info : dict

with pdfplumber.open("Kashika7Resume.pdf") as pdf:
    first_page = pdf.pages[0]
    content = first_page.extract_text(x_tolerance=3, x_tolerance_ratio=None, y_tolerance=3, layout=False, x_density=7.25, y_density=13, line_dir_render=None, char_dir_render=None)

def get_all_info(info: str) -> Candidate:
    chat_completion = client.chat.completions.create(
        messages = [
            {
                "role" : "system",
                "content" : "You are a resume parser that extracts information from resume.\n"
                f" The JSON object must use the schema: {json.dumps(Candidate.model_json_schema(), indent=2)}",
            },
            {
                "role" : "user",
                "content" : f"use this {info}",
            },
        ],
        model = "llama-3.3-70b-versatile",
        temperature = 0,
        stream = False,
        response_format = {"type": "json_object"},
    )
    return Candidate.model_validate_json(chat_completion.choices[0].message.content)

info = get_all_info(content)
candidate_name = info.name

skill_list = []
for skill in info.Skills:
    skill_list.append(skill)

education_json = []
for edu in info.Education:
    temp = {"Institute_name" : edu.Institute_name, "Degree_name" : edu.Degree_name, "Marks" : edu.marks}
    education_json.append(temp)

experience_json = []
for exp in info.Experience:
    temp = {"Company" : exp.Company_name, "Position" : exp.Position_name, "Skills" : list(exp.skills_used)}
    experience_json.append(temp)

project_json = []
for project in info.Projects:
    temp = {"title" : project.project_name, "desc" : project.about_project, "tech" : list(project.skills_used)}
    project_json.append(temp)

contact_json = info.Contact_Info

print(education_json)

app = Flask(__name__)

@app.route("/")
def home():
    data = {
        "name" : candidate_name,
        "education" : education_json,
        "Contact_Info" : contact_json,
        "skills" : skill_list,
        "projects" : project_json,
        "Experience" : experience_json
    }
    return render_template("index.html", **data)

app.run(debug = True)