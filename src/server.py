import base64
from fastapi import FastAPI
from fastapi.responses import JSONResponse
import uvicorn
from PyQt5.QtCore import QBuffer, QIODevice
from orchestrator import PBRTextureGenerator
from config import RequestModel, endpoint_config
from utils import pil_to_qimage, process_uploaded_images
from Logger import log_to_file, server_logger

# Initialize FastAPI app
app = FastAPI()

# Setup texture generation orchestraitor
texture_synthesis = PBRTextureGenerator(init=True)

@app.post(endpoint_config.endpoint)
async def generate_textures(
    request: RequestModel,
):
    server_logger.debug("Request received")
    # Process uploaded images
    user_image, user_mask = await process_uploaded_images(
        request.user_image, request.user_mask
    )
    # Remove user_image and user_mask from request object
    del request.user_image
    del request.user_mask
    log_to_file.log("info", f"Request received: {request.model_dump()}")
    
    # Generate textures, returns a Dict[str, PIL.Image.Image]
    textures = texture_synthesis.generate_textures(
        user_image=user_image,
        user_mask=user_mask,
        user_cofig=request,  # passes all config parameters, even those not in the request
    )
    server_logger.info("Textures generated")
    # Convert images to byte format for response
    response_images = {}
    
    for name, img in textures.items():
        qimage = pil_to_qimage(img)
        buffer = QBuffer()
        buffer.open(QIODevice.WriteOnly)
        qimage.save(buffer, "PNG")
        # Save the image to the output folder
        output_path = f"./output/{name}.png"
        qimage.save(output_path, "PNG")
        img_bytes = buffer.data().data()
        img_base64 = base64.b64encode(img_bytes).decode("utf-8")
        response_images[name] = img_base64

    return JSONResponse(content=response_images)


if __name__ == "__main__":
    uvicorn.run(
        "server:app", port=endpoint_config.port, log_level="debug", reload=True
    )
