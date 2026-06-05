from google.genai import types

# Trying to see what Content needs
try:
    content = types.Content(
        role="user",
        parts=[types.Part.from_text(text="hello")]
    )
    print("Content created successfully:", content)
except Exception as e:
    print("Error creating content:", e)
