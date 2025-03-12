from abc import ABC, abstractmethod
from diffusers import (
    StableDiffusionXLControlNetPipeline,
    ControlNetModel,
    AutoencoderKL,
    DPMSolverMultistepScheduler,
)
from typing import Dict, Any
from PIL import Image, ImageFilter
from Logger import log_to_file
from config import pipeline_config, processing_config, RequestModel
from utils import *



class I_TextureGenerator(ABC):
    """Orchestrator interface for texture generation"""

    @abstractmethod
    def generate_textures(
        self,
        user_images: Image.Image,   # ID-mapped perspective images
        user_masks: Image.Image,    # ID-mapped masks (must match images)
        user_config: Dict[str, Any],           # Configuration options
    ) -> Dict[str, Image.Image]:  # Generated PBR textures
        """Generates PBR textures from identified input images, masks, and optional depth maps."""
        pass


class PBRTextureGenerator(I_TextureGenerator):
    """PBR texture generation using SDXL & Material Synthesis LoRA & ControlNet"""

    def __init__(self, **kwargs):
        self.controlnet_conditioning_scale = (
            pipeline_config.controlnet_conditioning_scale
        )
        if kwargs.get("init", False):
            (
                self.generator,
                self.vae,
                self.controlnet,
                self.pipe_controlnet,
            ) = self._setup_pipeline()

    def _setup_pipeline(self) -> tuple:
        # VAE setup
        set_seed(randomize=True)

        generator = torch.Generator(device=pipeline_config.device)
        
        print(f"dtype: {pipeline_config.precision}")
        print(f"vae checkpoint: {pipeline_config.vae_checkpoint}")
        
        vae = AutoencoderKL.from_pretrained(
            pipeline_config.vae_checkpoint, torch_dtype=pipeline_config.precision
        ).to(pipeline_config.device)

        # ControlNet setup
        controlnet_canny = ControlNetModel.from_pretrained(
            pipeline_config.controlnet_checkpoint, torch_dtype=pipeline_config.precision
        ).to(pipeline_config.device)

        # Inpainting Albedo Pipeline Setup
        pipe = StableDiffusionXLControlNetPipeline.from_pretrained(
            pipeline_config.pipeline_checkpoint,
            controlnet=controlnet_canny,
            vae=vae,
            torch_dtype=pipeline_config.precision,
            variant="fp16" if pipeline_config.precision == torch.float16 else None,
        ).to(pipeline_config.device)

        pipe.scheduler = DPMSolverMultistepScheduler.from_config(
            pipe.scheduler.config, use_karras_sigmas=True
        )

        pipe.load_lora_weights(
            pipeline_config.lora_weights_path,
            weight_name=pipeline_config.lora_weights_name,
        )

        pipe.controlnet.to(memory_format=torch.channels_last)

        scale_and_apply_lora_weights_inplace(pipe, pipeline_config.rank)

        # for _, module in pipe.unet.named_modules():
        #     module.register_forward_hook(detect_nan_hook)

        self._optimize_pipeline(pipe)

        return (
            generator,
            vae,
            controlnet_canny,
            pipe,
        )

    def _optimize_pipeline(self, pipe: StableDiffusionXLControlNetPipeline) -> None:
        pipe.enable_model_cpu_offload()
        # pipe.vae = AutoencoderKL.from_pretrained(pipeline_config.vae_checkpoint, torch_dtype=pipeline_config.precision).to(pipeline_config.device)
        # pipe.enable_xformers_memory_efficient_attention()
        pipe.enable_vae_tiling()
        # pipe.unet = torch.compile(pipe.unet, mode="max-autotune")

    def _process_batch(self) -> dict[str, Image.Image]:

        maps_list = sorted(list(self.maps))
        batch_size = processing_config.batch_size  # Process up to 4 at a time
        num_batches = (
            len(maps_list) + batch_size - 1
        ) // batch_size  # Compute total batches

        for i in range(num_batches):
            batch_maps = maps_list[
                i * batch_size : (i + 1) * batch_size
            ]  # Extract batch
            print(f"Processing batch {i+1}/{num_batches}: {batch_maps}")

            # Prepare batched inputs
            batch_prompts = [self.prompts[map_] for map_ in batch_maps]
            batch_negative_prompts = [negativePrompts[map_] for map_ in batch_maps]
            batch_images = [self.image_canny_pil] * len(
                batch_maps
            )  # Same input image for all

            # Process batch in parallel
            generated_maps = self.pipe_controlnet(
                prompt=batch_prompts,
                negative_prompt=batch_negative_prompts,
                controlnet_conditioning_scale=self.controlnet_conditioning_scale,
                image=batch_images,  # Pass as a batch
                num_inference_steps=self.sample_steps,
                generator=self.generator,
                guidance_scale=self.guidance_scale,
            )

            # Save results
            for idx, map_ in enumerate(batch_maps):
                output_path = os.path.join("output", f"{map_}.png")
                generated_maps.images[idx].save(output_path)
                self.images[map_] = generated_maps.images[idx]

            print(f"Batch {i+1}/{num_batches} completed!\n")
        return self.images

    def generate_textures(
        self,
        user_image: Image.Image,  # 1024x1024
        user_mask: Image.Image,  # 1024x1024
        user_cofig: dict,
    ) -> dict[str, Image.Image]:

        # setup necessary pipeline and processing config

        self.maps = user_cofig.maps
        self.sample_steps = user_cofig.sample_steps
        self.guidance_scale = user_cofig.guidance_scale
        self.prompts = update_user_prompt(user_cofig.prompt)
        self.resolutions = [user_cofig.width, user_cofig.height]
        self.images = {}

        # Convert user mask to canny edge map to guide the inpainted albedo
        canny_mask = mask_to_canny(user_mask)

        
        # Step 1: Generate "an" inpainted base texture
        base_img = self.pipe_controlnet(
            width=self.resolutions[0],
            height=self.resolutions[1],
            prompt=self.prompts["albedo"],
            negative_prompt=negativePrompts["albedo"],
            controlnet_conditioning_scale=0.8,
            image=canny_mask,
            num_inference_steps=self.sample_steps,
            generator=self.generator,
            guidance_scale=self.sample_steps - 1,
        ).images[0]

        # get edges from albedo to guide the remained of PBR texture generation
        image_canny_pil = color_to_canny(base_img)

        # Generate the albedo map using the inpainted base color texture as a guide
        color_image = self.pipe_controlnet(
            width=self.resolutions[0],
            height=self.resolutions[1],
            prompt=self.prompts["albedo"],
            negative_prompt=negativePrompts["albedo"],
            controlnet_conditioning_scale=0.99,
            image=image_canny_pil,
            num_inference_steps=self.sample_steps,
            generator=self.generator,
            guidance_scale=self.sample_steps,
        ).images[0]

        self.images["albedo"] = Image.composite(
            color_image,  # outputted according to user size preference
            resize_to_target(user_image, (self.resolutions[0], self.resolutions[1])),
            resize_to_target(
                user_mask, (self.resolutions[0], self.resolutions[1])
            ).convert("L"),
        )

        # Smoothen the albedo image before converting to canny edges
        smoothed_albedo = self.images["albedo"].filter(ImageFilter.MedianFilter(size=3))
        self.image_canny_pil = color_to_canny(smoothed_albedo)

        self.maps.discard("albedo")  # no ned to process it again

        # Generate the other maps using the inpainted albedo and Canny edge map as guides
        if not user_cofig.batch:
            for map_ in self.maps:
                print(f"Generating {map_} map.\n")
                print(f"Prompt: {self.prompts[map_]}\n")

                generated_map = self.pipe_controlnet(
                    width=self.resolutions[0],
                    height=self.resolutions[1],
                    prompt=self.prompts[map_],
                    negative_prompt=negativePrompts[map_],
                    controlnet_conditioning_scale=self.controlnet_conditioning_scale,
                    image=self.image_canny_pil,
                    num_inference_steps=self.sample_steps,
                    generator=self.generator,
                    guidance_scale=self.guidance_scale,
                )

                self.images[map_] = generated_map.images[0]
        else:
            self.images = self._process_batch()
        return self.images


if __name__ == "__main__":

    args = parse_args()
    user_image_path = args.image
    user_mask_path = args.mask
    prompt = args.prompt
    maps = set(args.maps.split(","))

    try:
        w, h = pipeline_config.width, pipeline_config.height
        user_image = Image.open(user_image_path).convert("RGB").resize((w, h))
        user_mask = Image.open(user_mask_path).convert("L").resize((w, h))
    except Exception as e:
        log_to_file.log("error", f"Error reading image/mask: {e}")
        raise e

    config = RequestModel(prompt=prompt, maps=maps)
    texture_synthesis = PBRTextureGenerator(init=True)
    images = texture_synthesis.generate_textures(
        user_cofig=config,
        user_image=user_image,
        user_mask=user_mask,
    )

    output_dir = args.output_dir
    os.makedirs(output_dir, exist_ok=True)

    for name, image in images.items():
        output_path = os.path.join(output_dir, f"{name}.png")
        image.save(output_path)
        print(f"Saved {name} map to {output_path}")
