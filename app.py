import gradio as gr
import subprocess
import sys
import os

# Set the port for Gradio
port = int(os.environ.get('PORT', 7860))

# Function to run your Flask app
def run_flask():
    # Import your Flask app
    from backend.app import app
    return app

# Create Gradio interface
def launch():
    # This will launch your Flask app
    # Gradio will handle the web interface
    print("🚀 Starting Quantum Traffic Optimizer...")
    print("🌍 Running on Hugging Face Spaces")
    
    # Your app is already running via Flask
    # Gradio just needs to host it

# Launch the app
if __name__ == "__main__":
    # Run the Flask app
    from backend.app import app
    app.run(host='0.0.0.0', port=port, debug=False)

