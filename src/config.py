from pydantic import BaseModel, Field, field_validator
from typing import Set, Optional
import torch
import base64
from utils import TorchDtypeWrapper, TorchDeviceWrapper


class PipelineConfig(BaseModel):
    width: int = Field(1024, ge=256, le=2048, description="Width of the output image")
    height: int = Field(1024, ge=256, le=2048, description="Height of the output image")
    sample_steps: int = Field(11, ge=1, le=50, description="Number of sampling steps")
    guidance_scale: int = Field(8, ge=1, le=15, description="Guidance scale")
    controlnet_conditioning_scale: float = Field(
        0.99, ge=0, le=1.0, description="Strength of ControlNet conditioning"
    )
    precision: TorchDtypeWrapper = TorchDtypeWrapper(
        torch.float16
    ).dtype  # TODO probably better to use field validator...
    device: TorchDeviceWrapper = TorchDeviceWrapper(
        torch.device("cuda" if torch.cuda.is_available() else "cpu")
    ).device  # TODO probably better to use field validator...
    rank: float = 9.7
    vae_checkpoint: str = (
        "madebyollin/sdxl-vae-fp16-fix"
        if precision == torch.float16
        else "stabilityai/sdxl-vae"
    )
    small_vae_ec_checkpoint: str = (
        "madebyollin/taesdxl"  # doesn't see to be compatible with SDXL 1.0
    )
    controlnet_checkpoint: str = "diffusers/controlnet-canny-sdxl-1.0"
    control_lora_path: str = "stabilityai/control-lora"
    control_lora_name: str = "control-LoRAs-rank256/control-lora-canny-rank256.safetensors"
    pipeline_checkpoint: str = "stabilityai/stable-diffusion-xl-base-1.0"
    lora_weights_path: str = "./model_weights"
    lora_weights_name: str = "texture-synthesis-topdown-base-condensed.safetensors"


class ProcessingConfig(BaseModel):
    user_image: Optional[str] = Field(None, description="Base64 encoded user image")
    user_mask: Optional[str] = Field(None, description="Base64 encoded user mask")
    maps: Set[str] = Field(
        default_factory=lambda: {
            "specular",
            "albedo",
            "rough",
            "metal",
            "height",
            "normal",
            "ambientocl",
        },
        description="Set of texture maps, any number of the following: specular, albedo, rough, metal, height, normal, ambientocl",
    )
    batch: bool = False
    batch_size: int = 3
    prompt: str = ""

    # Validate that the maps field contains valid map names
    @field_validator("maps")
    def validate_maps(cls, v):
        allowed_maps = {
            "specular",
            "albedo",
            "rough",
            "metal",
            "height",
            "normal",
            "ambientocl",
        }
        invalid_maps = set(v) - allowed_maps
        if invalid_maps:
            raise ValueError(
                f"Invalid maps: {invalid_maps}. Allowed maps are: {allowed_maps}"
            )
        return v

    # Validate that the user_image and user_mask fields contain valid Base64 strings
    @field_validator("user_image", "user_mask")
    @classmethod
    def validate_base64(cls, v):
        """Ensure the field contains a valid Base64-encoded string"""
        try:
            base64.b64decode(v, validate=True)  # Check if it's valid Base64
        except Exception:
            raise ValueError("Invalid Base64 string")
        return v  # Return unchanged if valid


class RequestModel(PipelineConfig, ProcessingConfig):
    pass


class EndpointConfig(BaseModel):
    host: str = "127.0.0.1"
    port: int = 5000
    log_level: str = "info"
    endpoint: str = "/generate-textures/"


pipeline_config = PipelineConfig()
processing_config = ProcessingConfig()
endpoint_config = EndpointConfig()
