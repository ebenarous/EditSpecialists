# Adapted from https://github.com/huggingface/diffusers/blob/main/src/diffusers/pipelines/stable_diffusion/pipeline_stable_diffusion_instruct_pix2pix.py

from typing import List, Optional, Tuple, Union, Dict, Any, Callable
import torch
import PIL.Image

from diffusers import StableDiffusionInstructPix2PixPipeline
from diffusers.pipelines.stable_diffusion.pipeline_stable_diffusion import (
    rescale_noise_cfg,
)
from diffusers.callbacks import MultiPipelineCallbacks, PipelineCallback
from diffusers.utils import deprecate
from diffusers import EulerAncestralDiscreteScheduler
from diffusers.schedulers.scheduling_ddim import DDIMScheduler


# Copied from diffusers.pipelines.stable_diffusion.pipeline_stable_diffusion_img2img.preprocess

from .eulerancestral_withlogprob import eulerancestral_step_with_logprob
from .ddim_with_logprob import ddim_step_with_logprob


def instruct_pix2pix_pipeline_with_logprob(
    self: StableDiffusionInstructPix2PixPipeline,
    prompt: Union[str, List[str]] = None,
    image: torch.Tensor = None,
    style_image: torch.Tensor = None,
    num_inference_steps: int = 100,
    guidance_scale: float = 7.5,
    image_guidance_scale: float = 1.5,
    style_image_guidance_scale: float = 3.0,
    negative_prompt: Optional[Union[str, List[str]]] = None,
    num_images_per_prompt: Optional[int] = 1,
    eta: float = 0.0,
    generator: Optional[Union[torch.Generator, List[torch.Generator]]] = None,
    latents: Optional[torch.Tensor] = None,
    prompt_embeds: Optional[torch.Tensor] = None,
    negative_prompt_embeds: Optional[torch.Tensor] = None,
    output_type: Optional[str] = "pil",
    return_dict: bool = True,
    callback_on_step_end: Optional[
        Union[Callable[[int, int, Dict], None], PipelineCallback, MultiPipelineCallbacks]
    ] = None,
    callback_on_step_end_tensor_inputs: List[str] = ["latents"],
    cross_attention_kwargs: Optional[Dict[str, Any]] = None,
    guidance_rescale: float = 0.0,
    **kwargs,
):
    r"""
    The call function to the pipeline for generation.

    Args:
        prompt (`str` or `List[str]`, *optional*):
            The prompt or prompts to guide image generation. If not defined, you need to pass `prompt_embeds`.
        image (`torch.Tensor`):
            image latents as tensor representing an image batch to be repainted according to `prompt`
        num_inference_steps (`int`, *optional*, defaults to 100):
            The number of denoising steps. More denoising steps usually lead to a higher quality image at the
            expense of slower inference.
        guidance_scale (`float`, *optional*, defaults to 7.5):
            A higher guidance scale value encourages the model to generate images closely linked to the text
            `prompt` at the expense of lower image quality. Guidance scale is enabled when `guidance_scale > 1`.
        image_guidance_scale (`float`, *optional*, defaults to 1.5):
            Push the generated image towards the initial `image`. Image guidance scale is enabled by setting
            `image_guidance_scale > 1`. Higher image guidance scale encourages generated images that are closely
            linked to the source `image`, usually at the expense of lower image quality. This pipeline requires a
            value of at least `1`.
        negative_prompt (`str` or `List[str]`, *optional*):
            The prompt or prompts to guide what to not include in image generation. If not defined, you need to
            pass `negative_prompt_embeds` instead. Ignored when not using guidance (`guidance_scale < 1`).
        num_images_per_prompt (`int`, *optional*, defaults to 1):
            The number of images to generate per prompt.
        eta (`float`, *optional*, defaults to 0.0):
            Corresponds to parameter eta (η) from the [DDIM](https://arxiv.org/abs/2010.02502) paper. Only applies
            to the [`~schedulers.DDIMScheduler`], and is ignored in other schedulers.
        generator (`torch.Generator`, *optional*):
            A [`torch.Generator`](https://pytorch.org/docs/stable/generated/torch.Generator.html) to make
            generation deterministic.
        latents (`torch.Tensor`, *optional*):
            Pre-generated noisy latents sampled from a Gaussian distribution, to be used as inputs for image
            generation. Can be used to tweak the same generation with different prompts. If not provided, a latents
            tensor is generated by sampling using the supplied random `generator`.
        prompt_embeds (`torch.Tensor`, *optional*):
            Pre-generated text embeddings. Can be used to easily tweak text inputs (prompt weighting). If not
            provided, text embeddings are generated from the `prompt` input argument.
        negative_prompt_embeds (`torch.Tensor`, *optional*):
            Pre-generated negative text embeddings. Can be used to easily tweak text inputs (prompt weighting). If
            not provided, `negative_prompt_embeds` are generated from the `negative_prompt` input argument.
        ip_adapter_image: (`PipelineImageInput`, *optional*):
            Optional image input to work with IP Adapters.
        output_type (`str`, *optional*, defaults to `"pil"`):
            The output format of the generated image. Choose between `PIL.Image` or `np.array`.
        return_dict (`bool`, *optional*, defaults to `True`):
            Whether or not to return a [`~pipelines.stable_diffusion.StableDiffusionPipelineOutput`] instead of a
            plain tuple.
        callback_on_step_end (`Callable`, `PipelineCallback`, `MultiPipelineCallbacks`, *optional*):
            A function or a subclass of `PipelineCallback` or `MultiPipelineCallbacks` that is called at the end of
            each denoising step during the inference. with the following arguments: `callback_on_step_end(self:
            DiffusionPipeline, step: int, timestep: int, callback_kwargs: Dict)`. `callback_kwargs` will include a
            list of all tensors as specified by `callback_on_step_end_tensor_inputs`.
        callback_on_step_end_tensor_inputs (`List`, *optional*):
            The list of tensor inputs for the `callback_on_step_end` function. The tensors specified in the list
            will be passed as `callback_kwargs` argument. You will only be able to include variables listed in the
            `._callback_tensor_inputs` attribute of your pipeline class.
        cross_attention_kwargs (`dict`, *optional*):
            A kwargs dictionary that if specified is passed along to the [`AttentionProcessor`] as defined in
            [`self.processor`](https://github.com/huggingface/diffusers/blob/main/src/diffusers/models/attention_processor.py).
        guidance_rescale (`float`, *optional*, defaults to 0.7):
            Guidance rescale factor proposed by [Common Diffusion Noise Schedules and Sample Steps are
            Flawed](https://arxiv.org/pdf/2305.08891.pdf) `guidance_scale` is defined as `φ` in equation 16. of
            [Common Diffusion Noise Schedules and Sample Steps are Flawed](https://arxiv.org/pdf/2305.08891.pdf).
            Guidance rescale factor should fix overexposure when using zero terminal SNR.
    Returns:
        [`~pipelines.stable_diffusion.StableDiffusionPipelineOutput`] or `tuple`:
            If `return_dict` is `True`, [`~pipelines.stable_diffusion.StableDiffusionPipelineOutput`] is returned,
            otherwise a `tuple` is returned where the first element is a list with the generated images and the
            second element is a list of `bool`s indicating whether the corresponding generated image contains
            "not-safe-for-work" (nsfw) content.
    """

    callback = kwargs.pop("callback", None)
    callback_steps = kwargs.pop("callback_steps", None)

    if callback is not None:
        deprecate(
            "callback",
            "1.0.0",
            "Passing `callback` as an input argument to `__call__` is deprecated, consider use `callback_on_step_end`",
        )
    if callback_steps is not None:
        deprecate(
            "callback_steps",
            "1.0.0",
            "Passing `callback_steps` as an input argument to `__call__` is deprecated, consider use `callback_on_step_end`",
        )

    if isinstance(callback_on_step_end, (PipelineCallback, MultiPipelineCallbacks)):
        callback_on_step_end_tensor_inputs = callback_on_step_end.tensor_inputs

    # 0. Check inputs
    self.check_inputs(
        prompt,
        callback_steps,
        negative_prompt,
        prompt_embeds,
        negative_prompt_embeds,
        callback_on_step_end_tensor_inputs,
    ) # TODO: callback_steps is messy, leaving aside for now, see https://github.com/huggingface/diffusers/blob/main/src/diffusers/pipelines/stable_diffusion/pipeline_stable_diffusion_instruct_pix2pix.py
    self._guidance_scale = guidance_scale
    self._image_guidance_scale = image_guidance_scale

    device = self._execution_device

    if image is None:
        raise ValueError("`image` input cannot be undefined.")
    if style_image is None:
        raise ValueError("`edit_image` input cannot be undefined.")

    # 1. Define call parameters
    if prompt is not None and isinstance(prompt, str):
        batch_size = 1
    elif prompt is not None and isinstance(prompt, list):
        batch_size = len(prompt)
    else:
        batch_size = prompt_embeds.shape[0]

    device = self._execution_device

    # 2. Encode input prompt
    prompt_embeds = self._encode_prompt(
        prompt,
        device,
        num_images_per_prompt,
        self.do_classifier_free_guidance,
        negative_prompt,
        prompt_embeds=prompt_embeds,
        negative_prompt_embeds=negative_prompt_embeds,
    )
    prompt_embeds = torch.cat([prompt_embeds, prompt_embeds[2*batch_size:]]) # append negative_prompt_embed
    
    # 3. Preprocess images
    image = self.image_processor.preprocess(image)
    style_image = self.image_processor.preprocess(style_image)

    # 4. set timesteps
    self.scheduler.set_timesteps(num_inference_steps, device=device)
    timesteps = self.scheduler.timesteps

    # 5. Prepare Image latents
    image_latents = self.prepare_image_latents(
        image,
        batch_size,
        num_images_per_prompt,
        prompt_embeds.dtype,
        device,
        self.do_classifier_free_guidance,
    )
    image_latents = torch.cat([image_latents, image_latents[:batch_size]], dim=0) # append image_latent
    style_image_latents = prepare_style_image_latents(
        self,
        style_image,
        batch_size,
        num_images_per_prompt,
        prompt_embeds.dtype,
        device,
        self.do_classifier_free_guidance,
        prompt_embeddings=prompt_embeds.chunk(4)[0],
        input_image=image_latents.chunk(4)[0],
    )

    height, width = image_latents.shape[-2:]
    height = height * self.vae_scale_factor
    width = width * self.vae_scale_factor

    # 6. Prepare latent variables
    num_channels_latents = self.vae.config.latent_channels
    latents = self.prepare_latents(
        batch_size * num_images_per_prompt,
        num_channels_latents,
        height,
        width,
        prompt_embeds.dtype,
        device,
        generator,
        latents,
    )

    # 7. Check that shapes of latents and image match the UNet channels
    num_channels_image = image_latents.shape[1]
    if num_channels_latents + num_channels_image != self.unet.config.in_channels:
        raise ValueError(
            f"Incorrect configuration settings! The config of `pipeline.unet`: {self.unet.config} expects"
            f" {self.unet.config.in_channels} but received `num_channels_latents`: {num_channels_latents} +"
            f" `num_channels_image`: {num_channels_image} "
            f" = {num_channels_latents+num_channels_image}. Please verify the config of"
            " `pipeline.unet` or your `image` input."
        )

    # 8. Prepare extra step kwargs. TODO: Logic should ideally just be moved out of the pipeline
    extra_step_kwargs = self.prepare_extra_step_kwargs(generator, eta)
    added_cond_kwargs = None

    # 9. Denoising loop
    num_warmup_steps = len(timesteps) - num_inference_steps * self.scheduler.order
    self._num_timesteps = len(timesteps)
    all_latents = [latents]
    all_log_probs = []
    with self.progress_bar(total=num_inference_steps) as progress_bar:
        for i, t in enumerate(timesteps):
            # Expand the latents if we are doing classifier free guidance. 
            # Expand 4 times because guidance is applied for both the text, input image and style image
            latent_model_input = torch.cat([latents] * 4) if self.do_classifier_free_guidance else latents

            # concat latents, image_latents, and style_image_latents in the channel dimension
            scaled_latent_model_input = self.scheduler.scale_model_input(latent_model_input, t)
            scaled_latent_model_input = torch.cat([scaled_latent_model_input, image_latents, style_image_latents], dim=1)

            # predict the noise residual
            noise_pred = self.unet(
                scaled_latent_model_input,
                t,
                encoder_hidden_states=prompt_embeds,
                added_cond_kwargs=added_cond_kwargs,
                cross_attention_kwargs=cross_attention_kwargs,
                return_dict=False,
            )[0]

            # perform guidance
            if self.do_classifier_free_guidance:
                noise_pred_text, noise_pred_image, noise_pred_uncond, noise_pred_image_style = noise_pred.chunk(4)
                noise_pred = (
                    noise_pred_uncond
                    + self.image_guidance_scale * (noise_pred_image - noise_pred_uncond)
                    + style_image_guidance_scale * (noise_pred_image_style - noise_pred_image)
                    + self.guidance_scale * (noise_pred_text - noise_pred_image_style)
                )

                if guidance_rescale > 0.0:
                    # Based on 3.4. in https://arxiv.org/pdf/2305.08891.pdf
                    noise_pred = rescale_noise_cfg(noise_pred, noise_pred_text, guidance_rescale=guidance_rescale)

            # compute the previous noisy sample x_t -> x_t-1
            if isinstance(self.scheduler, EulerAncestralDiscreteScheduler):
                latents, log_prob = eulerancestral_step_with_logprob(self.scheduler, noise_pred, t, latents) 
            elif isinstance(self.scheduler, DDIMScheduler):
                latents, log_prob = ddim_step_with_logprob(self.scheduler, noise_pred, t, latents, **extra_step_kwargs) 
            else:
                raise ValueError("Scheduler should be one of DDIMScheduler or EulerAncestralDiscreteScheduler")
            all_latents.append(latents)
            all_log_probs.append(log_prob)
            
            if callback_on_step_end is not None:
                callback_kwargs = {}
                for k in callback_on_step_end_tensor_inputs:
                    callback_kwargs[k] = locals()[k]
                callback_outputs = callback_on_step_end(self, i, t, callback_kwargs)

                latents = callback_outputs.pop("latents", latents)
                prompt_embeds = callback_outputs.pop("prompt_embeds", prompt_embeds)
                negative_prompt_embeds = callback_outputs.pop("negative_prompt_embeds", negative_prompt_embeds)
                image_latents = callback_outputs.pop("image_latents", image_latents)

            # call the callback, if provided
            if i == len(timesteps) - 1 or ((i + 1) > num_warmup_steps and (i + 1) % self.scheduler.order == 0):
                progress_bar.update()
                if callback is not None and i % callback_steps == 0:
                    step_idx = i // getattr(self.scheduler, "order", 1)
                    callback(step_idx, t, latents)

    if not output_type == "latent":
        image = self.vae.decode(latents / self.vae.config.scaling_factor, return_dict=False)[0]
        image, has_nsfw_concept = self.run_safety_checker(image, device, prompt_embeds.dtype)
    else:
        image = latents
        has_nsfw_concept = None

    if has_nsfw_concept is None:
        do_denormalize = [True] * image.shape[0]
    else:
        do_denormalize = [not has_nsfw for has_nsfw in has_nsfw_concept]

    image = self.image_processor.postprocess(image, output_type=output_type, do_denormalize=do_denormalize)

    # Offload all models
    self.maybe_free_model_hooks()

    if not return_dict:
        return (image, has_nsfw_concept)

    return image, has_nsfw_concept, all_latents, all_log_probs



def prepare_style_image_latents(
    self, style_image, batch_size, num_images_per_prompt, dtype, device, do_classifier_free_guidance, prompt_embeddings, input_image
    ):
    if not isinstance(style_image, (torch.Tensor, PIL.Image.Image, list)):
        raise ValueError(
            f"`style_image` has to be of type `torch.Tensor`, `PIL.Image.Image` or list but is {type(style_image)}"
        )

    style_image = style_image.to(device=device, dtype=dtype)

    batch_size = batch_size * num_images_per_prompt

    if style_image.shape[1] == 4:
        style_image_latents = style_image
    else:
        style_image_latents = retrieve_latents(self.vae.encode(style_image), sample_mode="argmax")

    if batch_size > style_image_latents.shape[0] and batch_size % style_image_latents.shape[0] == 0:
        # expand style_image_latents for batch_size
        deprecation_message = (
            f"You have passed {batch_size} text prompts (`prompt`), but only {style_image_latents.shape[0]} initial"
            " images (`image`). Initial images are now duplicating to match the number of text prompts. Note"
            " that this behavior is deprecated and will be removed in a version 1.0.0. Please make sure to update"
            " your script to pass as many initial images as text prompts to suppress this warning."
        )
        deprecate("len(prompt) != len(image)", "1.0.0", deprecation_message, standard_warn=False)
        additional_image_per_prompt = batch_size // style_image_latents.shape[0]
        style_image_latents = torch.cat([style_image_latents] * additional_image_per_prompt, dim=0)
    elif batch_size > style_image_latents.shape[0] and batch_size % style_image_latents.shape[0] != 0:
        raise ValueError(
            f"Cannot duplicate `image` of batch size {style_image_latents.shape[0]} to {batch_size} text prompts."
        )
    else:
        style_image_latents = torch.cat([style_image_latents], dim=0)

    # Apply Cross-Attention before feeding to the UNet conv_in layer
    style_image_latents = torch.cat([style_image_latents, input_image], 1)
    style_image_latents = self.ca_preconv(vae_images=style_image_latents, text_embedding=prompt_embeddings)

    if do_classifier_free_guidance:
        uncond_image_latents = torch.zeros_like(style_image_latents)
        style_image_latents = torch.cat([style_image_latents, uncond_image_latents, uncond_image_latents, style_image_latents], dim=0)

    return style_image_latents

# Copied from diffusers.pipelines.stable_diffusion.pipeline_stable_diffusion_img2img.retrieve_latents
def retrieve_latents(
    encoder_output: torch.Tensor, generator: Optional[torch.Generator] = None, sample_mode: str = "sample"
):
    if hasattr(encoder_output, "latent_dist") and sample_mode == "sample":
        return encoder_output.latent_dist.sample(generator)
    elif hasattr(encoder_output, "latent_dist") and sample_mode == "argmax":
        return encoder_output.latent_dist.mode()
    elif hasattr(encoder_output, "latents"):
        return encoder_output.latents
    else:
        raise AttributeError("Could not access latents of provided encoder_output")
