import streamlit as st
import streamlit.components.v1 as components
import os

st.set_page_config(
    page_title="AlcheMix — Alchemy Graph Game",
    page_icon="🧪",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# Hide Streamlit header/footer for immersive gameplay
hide_st_style = """
<style>
#MainMenu {visibility: hidden;}
footer {visibility: hidden;}
header {visibility: hidden;}
.block-container {
    padding: 0rem !important;
}
iframe {
    display: block;
    border: none;
    height: 100vh;
    width: 100vw;
}
</style>
"""
st.markdown(hide_st_style, unsafe_allow_html=True)

def compile_game():
    # Load raw assets
    html_path = "index.html"
    css_path = "index.css"
    data_path = "frontend_data.js"
    app_path = "app.js"
    
    if not (os.path.exists(html_path) and os.path.exists(css_path) and os.path.exists(data_path) and os.path.exists(app_path)):
        st.error("Error: Game asset files (index.html, index.css, frontend_data.js, app.js) are missing from the folder.")
        return None
        
    with open(html_path, "r", encoding="utf-8") as f:
        html = f.read()
        
    with open(css_path, "r", encoding="utf-8") as f:
        css = f.read()
        
    with open(data_path, "r", encoding="utf-8") as f:
        data = f.read()
        
    with open(app_path, "r", encoding="utf-8") as f:
        app_js = f.read()
        
    # Inline the CSS
    css_link = '<link rel="stylesheet" href="index.css">'
    inline_css = f"<style>\n{css}\n</style>"
    html = html.replace(css_link, inline_css)
    
    # Inline the frontend data script
    data_script = '<script src="frontend_data.js"></script>'
    inline_data = f"<script>\n{data}\n</script>"
    html = html.replace(data_script, inline_data)
    
    # Inline the game app logic script
    app_script = '<script src="app.js"></script>'
    inline_app = f"<script>\n{app_js}\n</script>"
    html = html.replace(app_script, inline_app)
    
    return html

import threading
import uvicorn
import socket

def is_port_open(port):
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        return s.connect_ex(('127.0.0.1', port)) != 0

def start_backend_api():
    if is_port_open(8000):
        try:
            from api import app
            thread = threading.Thread(
                target=uvicorn.run,
                args=(app,),
                kwargs={"host": "127.0.0.1", "port": 8000, "log_level": "warning"},
                daemon=True
            )
            thread.start()
            print("FastAPI backend server started on port 8000.")
        except Exception as e:
            print(f"Error starting background API server: {e}")
    else:
        print("Port 8000 is in use, assuming backend API server is already running.")

def main():
    start_backend_api()
    compiled_html = compile_game()
    if compiled_html:
        # Serve the single-page application inside the iframe
        components.html(compiled_html, height=850, scrolling=True)

if __name__ == "__main__":
    main()
