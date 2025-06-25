
You'll need a workspace of 30-40 GiBs to setup SDXL.

Set up environment:
```apt-get update```


Cd into workspace
```python -m venv ./lora-env && source ./lora-env/bin/activate```

Git clone this repo
```https://github.com/mohbenaicha/pbr-texture-generator.git``` 

Setup requirements
```pip install -r requirements.txt```

Download dog-god's models (.safetensors) into ```src/model_weights```. You can get them from here: https://huggingface.co/dog-god/texture-synthesis-sdxl-lora/tree/main


Now ```cd src```

**UI Usage:**

1. In a terminal, run the server: `python server.py`
2. In another terminal, run the UI: `python main.py`
3. Load an image, inpaint if you like
4. Enter a prompt if inpainting, if not, just enter a space
5. Generate textures; generated textures will appear on the right a panel

**CLI Usage:**
```
python orchestrator.py --prompt "a top-down view of bricked surface" --mask ./inpaint_mask.jpg --image ./inpaint_img.jpg --output_dir "./output"
```

Args:
--user_image: path to image file
--user_mask: path to file
--prompt: the prompt for the material - this can handle one material at a time (like "a brown brick wall" or "green alligator scales" or "a metal sheet")

**Images outputted in:** ```"src/output"```
- albedo: base color map
- normal, roughness, ambient occlusion, height: necessary for PBR in that order
- metal: generated, can be used or ignored
- specular: if using specular PBR workflow