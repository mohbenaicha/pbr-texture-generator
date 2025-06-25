# Inpainting LoRA - Texture Generator

This project provides both a React-based frontend and Python backend for SDXL-powered texture generation using inpainting techniques. This project relies heavily on a modified version of dog-god's SDXL wrapper called the **texture-synthesis-sdxl-lora** which is an experiemntal PBR texture LoRA.(https://huggingface.co/dog-god/texture-synthesis-sdxl-lora) 

You can read further about the challenges with using SDXL 1.0 with this LoRA: https://huggingface.co/dog-god/texture-synthesis-sdxl-lora/discussions

## System Requirements

You'll need a workspace of 30-40 GiBs to setup SDXL.

## Setup Instructions

### Environment Setup
```bash
apt-get update
python -m venv ./lora-env && source ./lora-env/bin/activate
```

### Backend Setup (Python Server)

1. **Install Python dependencies:**
   ```bash
   cd backend
   pip install -r requirements.txt
   ```

2. **Download dog-god's models (.safetensors) into `src/model_weights`**
   You can get them from here: https://huggingface.co/dog-god/texture-synthesis-sdxl-lora/tree/main

3. **Start the uvicorn server:**
   ```bash
   cd src
   python server.py
   ```
   The API server will be available at `http://localhost:5000`

### Frontend Setup (React)

1. **Install Node.js dependencies:**
   You need node to run the ReactJS app. If you don't want to work with JS, a Python front end does exist but has more primitive mask painting (see below):
   ```bash
   cd frontend
   npm install
   ```

2. **Start the development server:**
   
   ```bash
   npm start
   ```
   The React app will be available at `http://localhost:3000`

### Alternative Frontend Setup (Python/PyQt5)

If you prefer a Python-based GUI instead of React:

1. **Install additional Python dependencies:**
   ```bash
   pip install -r ui_requirements.txt
   ```

2. **Run the Python frontend:**
   ```bash
   python main.py
   ```

## Usage

### React Frontend Usage

1. Start the backend server: `python server.py`
2. Start the React frontend: `npm start`
3. Load an image using drag-and-drop
4. Paint masks using custom brushes (adjustable size, opacity, splat PNGs or upload your own)
5. Enter a prompt for the material you want to generate
6. Generate textures; results will appear in tabbed panels

### Python PyQt5 Frontend Usage

1. In a terminal, run the server: `python server.py`
2. In another terminal, run the UI: `python main.py`
3. Load an image, inpaint if you like
4. Enter a prompt if inpainting, if not, just enter a space
5. Generate textures; generated textures will appear on the right panel

### CLI Usage

For command-line texture generation:
```bash
python orchestrator.py --prompt "a top-down view of bricked surface" --mask ./inpaint_mask.jpg --image ./inpaint_img.jpg --output_dir "./output"
```

**CLI Arguments:**
- `--user_image`: path to image file
- `--user_mask`: path to mask file
- `--prompt`: the prompt for the material - this can handle one material at a time (like "a brown brick wall" or "green alligator scales" or "a metal sheet")

## Output

**Images are outputted in:** `"src/output"`
- **albedo**: base color map
- **normal, roughness, ambient occlusion, height**: can be used in classic or modern PBR
- **metal**: can be used or ignored based on metallic workflow or surface properties
- **specular**: if using specular PBR workflow

## Features

- Image upload (drag-and-drop)
- Mask painting with custom brushes (size, opacity, splat PNGs)
- Prompt input
- Texture generation and tabbed result display
- Support for PBR texture workflows

## Libraries

### Frontend
- React
- Fabric.js
- Material-UI
- Axios
- react-dropzone

### Backend
- FastAPI
- PyTorch, Diffusers, OpenCV
- Vision pipeline: stable diffusion, controlnet, LoRA

## Development Notes

- The React frontend communicates with the FastAPI backend via HTTP requests
- The Python frontend uses PyQt5 for a native desktop application experience
- Both frontends support the same core features: image upload, mask painting, and texture generation based on prompts
- React frontend supports better mask painting and scaling
- Make sure both frontend and backend are running simultaneously for full functionality