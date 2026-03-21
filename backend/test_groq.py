import os
os.environ["GROQ_API_KEY"] = "your_groq_key_here"

from gemini_processor import extract_program_info

result = extract_program_info(
    title="POSHAN Abhiyaan - National Nutrition Mission",
    body="The government launched POSHAN Abhiyaan to reduce stunting, wasting and anaemia among children under 6 and pregnant women. The scheme provides IFA supplementation, deworming and take home rations through anganwadi centres. Budget allocation is Rs 9046 crore.",
    ministry="Ministry of Women and Child Development (MoWCD)",
    source_url="https://pib.gov.in/test"
)

print("RESULT:", result)