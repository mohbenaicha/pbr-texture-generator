import random
import numpy as np
import torch, cv2
from PIL import Image
from Logger import log_to_file
from PyQt5.QtGui import QImage
from fastapi import UploadFile
import io
import base64
from PyQt5.QtCore import QBuffer, QIODevice
import os, torch, argparse


def resize_to_target(image, target_size=(1024, 1024)) -> Image:
    """
    Resizes PIL Image
    Args:
        image (PIL.Image): Image to resize
        target_size (tuple): Target size to resize to
    Returns:
        PIL.Image: Resized image
    """
    if image.size == target_size:
        return image
    else:
        return image.resize(target_size, Image.LANCZOS)


def color_to_canny(init_image) -> Image:
    """
    Get edges for controlnet guidance using Canny edge detection algo
    Args:
        init_image (PIL.Image): Initial color image
    Returns:
        PIL.Image: Canny edge image
    """
    # Load color image, convert to guidance image through Canny edge detection
    initial_image_np = np.array(init_image)
    initial_image_gray = cv2.cvtColor(initial_image_np, cv2.COLOR_RGB2GRAY)

    # debug: canny edge detection
    initial_image_canny = cv2.Canny(initial_image_gray, 50, 100)

    initial_image_canny_rgb = cv2.cvtColor(initial_image_canny, cv2.COLOR_GRAY2RGB)
    log_to_file.log("info", f"Color to Canny edge conversion success.")
    return Image.fromarray(initial_image_canny_rgb)


def detect_nan_hook(module, input, output) -> None:
    """
    I nade this during debugging to detect if LoRA weights generate NaN latents.
    Could be useful if updates to Torch/HF/diffusers is made
    Args:
        module:
        input:
        output:
    Returns:
        None
    """
    found_nan = False
    if isinstance(output, tuple):
        for i, out in enumerate(output):
            if isinstance(out, torch.Tensor) and torch.isnan(out).any():
                found_nan = True
    elif isinstance(output, torch.Tensor) and torch.isnan(output).any():
        found_nan = True

    if found_nan:
        log_to_file.log("error", f"NaN detected in output after LoRA applied.")


def scale_and_apply_lora_weights(pipe, original_lora_weights, rank):
    """
    Key function for scaling LoRA weights to the appropriate scale.
    The author's provided model generates NaNs if defautls weights values are used.
    Args:
        pipe: HF SDXL pipeline
        original_lora_weights: original LoRA (pipe.unet) weight tensor
        rank: rank of model to scale down weights
    Returns:
        None
    """
    scale = 1 / rank
    for name, param in pipe.unet.named_parameters():
        if "lora" in name.lower():
            param.data = original_lora_weights[name] * scale
    log_to_file.log("info", f"LoRA weights scaled and applied successfully.")


def scale_and_apply_lora_weights_inplace(pipe, rank):
    """
    See: scale_and_apply_lora_weights
    Args:
        pipe: HF SDXL pipeline
        rank: rank of model to scale down weights
    Returns:
        None
    """
    scale = 1 / rank
    for name, param in pipe.unet.named_parameters():
        if "lora" in name.lower():
            param.data.mul_(scale)
    log_to_file.log("info", f"LoRA weights scaled and applied *inplace* successfully.")


def reset_lora_weights(pipe, original_lora_weights):
    """
    Finetuning utility function.
    Args:
        pipe: HF SDXL pipeline
        original_lora_weights: original LoRA (pipe.unet) weight tensor
    Returns:
        None
    """
    for name, param in pipe.unet.named_parameters():
        if "lora" in name.lower():
            param.data = original_lora_weights[name]
    log_to_file.log("info", f"LoRA weights reset successfully.")


def rescale(img) -> np.array:

    try:
        ar = np.array(img)
        mn = np.linalg.norm(np.min(ar))
        mx = np.linalg.norm(np.max(ar))
        if mx == mn:
            raise ValueError("Max and min values are the same, cannot rescale image.")
        norm = (ar - mn) * (1.0 / (mx - mn))
        log_to_file.log("info", f"Image rescaled successfully.")
        return norm
    except Exception as e:
        log_to_file.log("error", f"Rescale error: {e}")
        return np.array(img)  # Return the original image array in case of error


def create_mask(user_image, brush_strokes) -> np.array:
    mask = np.zeros(user_image.size, dtype=np.uint8)
    return mask


def save_image(image, path) -> None:
    image.save(path)


def mask_to_canny(
    mask, blur_radius=5, canny_threshold1=30, canny_threshold2=200
) -> Image:
    """
    Converts user's mask to canny edge image to guide albedo generation controlnet
    Args:
        mask: user's mask
        blur_radius: radius for Gaussian blur
        canny_threshold1: low threshold for Canny edge detection
        canny_threshold2: high threshold for Canny edge detection
    Returns:
        Image: Canny edge image
    """
    mask_np = np.array(mask)
    mask_inverted = cv2.bitwise_not(mask_np)
    blurred_mask = cv2.GaussianBlur(mask_inverted, (blur_radius, blur_radius), 0)
    mask_canny = cv2.Canny(blurred_mask, canny_threshold1, canny_threshold2)
    mask_canny_rgb = cv2.cvtColor(mask_canny, cv2.COLOR_GRAY2RGB)
    log_to_file.log("info", f"Mask to Canny edge conversion success.")
    return Image.fromarray(mask_canny_rgb)


def update_user_prompt(prompt):
    mapPrompts = {
        "albedo": f"an albedo map of {prompt}. VAR2, colormap, muted realistic colors",
        "rough": f"a roughness map of {prompt}. black and white, roughmap",
        "normal": f"a normal map of {prompt}. normal map",
        "ambientocl": f"an ambient occlusion map of {prompt}, black and white, ambmap",
        "metal": f"a metallic map of {prompt}, black and white, metalmap",
        "specular": f"a specular map of {prompt}, black and white, specmap",
        "height": f"a height map of {prompt}, grayscale, heighmap,black and white, heighmap",
    }
    return mapPrompts


negativePrompts = {
    "height": "weird, ugly, low quality, messed up, unrealistic, VAR1, blurry, low resolution",
    "albedo": "weird, ugly, low quality, messed up, unrealistic, VAR1, blurry, low resolution, garish colors, very vibrant",
    "rough": "weird, ugly, low quality, messed up, unrealistic, VAR1",
    "normal": "colormap",
    "specular": "weird, ugly, low quality, messed up, unrealistic, VAR1",
    "ambientocl": "weird, ugly, low quality, messed up, unrealistic, VAR1",
    "metal": "weird, ugly, low quality, messed up, unrealistic, VAR1",
}


def qimage_to_pil(qimage) -> Image:
    """Convert QImage to PIL Image"""
    qimage = qimage.convertToFormat(QImage.Format_RGBA8888)
    byte_data = qimage.bits().asstring(qimage.byteCount())
    pil_image = Image.frombytes("RGBA", (qimage.width(), qimage.height()), byte_data)
    log_to_file.log("info", f"QImage to PIL Image conversion success.")
    return pil_image


def pil_to_qimage(pil_image) -> QImage:
    """
    Converts a PIL Image to a QImage.
    Args:
        pil_image (PIL.Image.Image): The PIL Image to be converted.
    Returns:
        QImage: The converted QImage.
    """
    pil_image = pil_image.convert("RGBA")
    data = pil_image.tobytes("raw", "RGBA")
    qimage = QImage(data, pil_image.width, pil_image.height, QImage.Format_RGBA8888)
    log_to_file.log("info", f"PIL Image to QImage conversion success.")
    return qimage


def qimage_to_base64(image, format="PNG") -> str:
    """
    Convert QImage to Base64 string without intermediate QByteArray conversion
    Args:
        image (QImage): QImage to convert
        format (str): Image format to save
    Returns:
        str: Base64 encoded image
    """
    buffer = QBuffer()
    buffer.open(QIODevice.WriteOnly)
    image.save(buffer, format)  # Save QImage to buffer
    return base64.b64encode(buffer.data().data()).decode("utf-8")  # Convert to Base64


def set_seed(fixed_seed: int = 69420, randomize: bool = True): # seed was 1042
    """
    Set seed for reproducibility.
    Args:
        fixed_seed (int): Fixed seed value
        random (bool): Random seed if True
    """
    if randomize:
        seed = random.randint(0, 10000)
    else:
        seed = fixed_seed

    log_to_file.log("info", f"Random seed: {seed}")
    torch.manual_seed(seed)
    if torch.cuda.is_available():
        torch.cuda.manual_seed_all(seed)
    np.random.seed(seed)
    random.seed(seed)


async def process_uploaded_images(
    user_image: str, user_mask: str
) -> tuple[Image.Image, Image.Image]:
    """
    Decode and scale images to 1024x1024 and assign color space for SDXL pipeline.
    SDXL pipeline need RGB image and grayscale mask and 1024x1024 dims.
    Args:
        user_image: string representation of image byte code
        user_mask: string representation of mask byte code
    Returns:
        Tuple of user image and mask
    """
    from config import pipeline_config

    # Convert uploaded files to PIL images
    user_image = Image.open(io.BytesIO(base64.b64decode(user_image)))
    user_mask = Image.open(io.BytesIO(base64.b64decode(user_mask)))

    # Resize images to match processing requirements
    w, h = pipeline_config.width, pipeline_config.height
    user_image = resize_to_target(user_image, target_size=(w, h)).convert("RGB")
    user_mask = resize_to_target(user_mask, target_size=(w, h)).convert("L")

    return user_image, user_mask


def apply_stylesheet(obj) -> None:
    style_sheet = """
    QWidget {
        background-color: #2E2E2E;
        color: #FFFFFF;
        font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
        font-size: 16px;
        font-weight: bold;
    }
    QLineEdit, QSlider, QPushButton, QTabWidget::pane, QFrame {
        border-radius: 10px;
    }
    QLineEdit {
        background-color: #3E3E3E;
        color: #00FF00;
        padding: 5px;
        font-size: 16px;
        font-weight: bold;
    }
    QPushButton {
        background-color: #3E3E3E;
        color: #00FF00;
        padding: 10px;
        font-size: 16px;
        font-weight: bold;
    }
    QPushButton:hover {
        background-color: #5E5E5E;
    }
    QTabWidget::pane {
        border: 1px solid #3E3E3E;
    }
    QTabBar::tab {
        background: #3E3E3E;
        color: #00FF00;
        padding: 10px;
        border-top-left-radius: 10px;
        border-top-right-radius: 10px;
        font-size: 16px;
        font-weight: bold;
    }
    QTabBar::tab:selected {
        background: #5E5E5E;
    }
    QLabel {
        color: #00FF00;
        font-size: 16px;
        font-weight: bold;
    }
    """
    obj.setStyleSheet(style_sheet)
    log_to_file.log("info", f"Stylesheet applied successfully.")


class TorchDtypeWrapper:
    """
    Pydantic custom data type for Torch data types
    """

    def __init__(self, dtype: torch.dtype):
        self._dtype = dtype

    @property
    def dtype(self):
        return self._dtype

    @classmethod
    def __get_pydantic_core_schema__(cls, _, handler):
        return handler.generate_schema(str)


class TorchDeviceWrapper:
    """
    Pydantic custom data type for Torch devices
    """

    def __init__(self, device: torch.device):
        self._device = device

    @property
    def device(self):
        return self._device

    @classmethod
    def __get_pydantic_core_schema__(cls, _, handler):
        return handler.generate_schema(str)


def parse_args():
    """
    Parse command line arguments for texture synthesis orchestrator.py
    """
    parser = argparse.ArgumentParser(description="Texture Synthesis using ControlNet")
    parser.add_argument(
        "--image", type=str, required=True, help="Path to the user image"
    )
    parser.add_argument("--mask", type=str, required=True, help="Path to the user mask")
    parser.add_argument(
        "--prompt",
        type=str,
        required=True,
        help="Text prompt for texture synthesis",
    )
    parser.add_argument(
        "--output_dir",
        type=str,
        default="./output",
        help="Output directory for generated textures",
    )
    parser.add_argument(
        "--maps",
        default={"albedo", "normal"},
        type=str,
        required=False,
        help="Texture maps to generate",
    )
    return parser.parse_args()
