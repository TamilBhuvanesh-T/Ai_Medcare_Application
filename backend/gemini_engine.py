import google.generativeai as genai
import os

genai.configure(api_key=os.getenv("AIzaSyAXfFQdXiJ1g9Si3orQ-yhzhSVyVV80x_w"))

def run_gemini(prompt):
    model = genai.GenerativeModel("gemini-2.5-flash")
    response = model.generate_content(prompt)
    print("gemini is running")
    return response.text